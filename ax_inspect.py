import argparse
import json
import time
import re
import sys
from typing import Any, Dict, List, Optional, Set

import Foundation
import AppKit
import Quartz

# Pull a minimal set from ApplicationServices via PyObjC
from ApplicationServices import (  # type: ignore
    AXUIElementCreateSystemWide,
    AXUIElementCreateApplication,
    AXUIElementCopyAttributeValue,
    AXUIElementCopyAttributeValues,
    AXUIElementGetTypeID,
    AXValueGetType,
    AXValueGetValue,
    kAXErrorSuccess,
    kAXChildrenAttribute,
    kAXVisibleChildrenAttribute,
    kAXRoleAttribute,
    kAXTitleAttribute,
    kAXValueAttribute,
    kAXDescriptionAttribute,
    kAXEnabledAttribute,
    kAXPositionAttribute,
    kAXSizeAttribute,
    kAXRoleDescriptionAttribute,
    kAXFocusedApplicationAttribute,
    kAXFocusedWindowAttribute,
    kAXFocusedUIElementAttribute,
    kAXWindowsAttribute,
    kAXValueCGSizeType,
    kAXValueCGPointType,
    kAXValueCFRangeType,
)

# -----------------------------
# Fast helpers for CF/AX values
# -----------------------------

def _cf_to_py(val: Any):
    """Convert common CF types to Python."""
    if val is None:
        return None

    # CF primitives
    try:
        tid = Foundation.CFGetTypeID(val)  # type: ignore
        if tid == Foundation.CFStringGetTypeID():  # type: ignore
            return str(val)
        if tid == Foundation.CFBooleanGetTypeID():  # type: ignore
            return bool(val)
        if tid == Foundation.CFNumberGetTypeID():  # type: ignore
            # Try int first, then float
            ok_i, i_val = Foundation.CFNumberGetValue(val, Foundation.kCFNumberIntType, None)  # type: ignore
            if ok_i:
                return int(i_val)
            ok_f, f_val = Foundation.CFNumberGetValue(val, Foundation.kCFNumberDoubleType, None)  # type: ignore
            if ok_f:
                return float(f_val)
            return None
        if tid == Foundation.CFArrayGetTypeID():  # type: ignore
            return [ _cf_to_py(x) for x in val ]
        if tid == AXUIElementGetTypeID():
            return val  # keep AX elements as is
    except Exception:
        pass

    # AXValue (CGPoint/CGSize/CFRange) often presents as NSValue; try via AXValueGetType + description()
    try:
        ax_t = AXValueGetType(val)
        # Parse "{x=..., y=...}" or "{width=..., height=...}"
        desc = getattr(val, "description", None)
        if callable(desc):
            s = desc()
            m = re.search(r"\{.*\}", s)
            if m:
                s_inner = m.group()
                if ax_t == kAXValueCGPointType:
                    p = Foundation.NSPointFromString(s_inner)  # type: ignore
                    return {"x": float(getattr(p, "x", 0.0)), "y": float(getattr(p, "y", 0.0))}
                if ax_t == kAXValueCGSizeType:
                    sz = Foundation.NSSizeFromString(s_inner)  # type: ignore
                    return {"width": float(getattr(sz, "width", 0.0)), "height": float(getattr(sz, "height", 0.0))}
                if ax_t == kAXValueCFRangeType:
                    r = Foundation.NSRangeFromString(s_inner)  # type: ignore
                    return {"location": int(getattr(r, "location", 0)), "length": int(getattr(r, "length", 0))}
    except Exception:
        pass

    return None

def ax_attr(elem, attr_name: str):
    """Fetch a single AX attribute (fast path, no exceptions)."""
    try:
        err, val = AXUIElementCopyAttributeValue(elem, attr_name, None)
        if err == kAXErrorSuccess:
            # Children and a few others can be NSArray; convert shallowly
            if isinstance(val, Foundation.NSArray):  # type: ignore
                return [_cf_to_py(x) for x in val]
            return _cf_to_py(val)
    except Exception:
        pass
    return None

def ax_children(elem, limit: int):
    """Fetch children with a hard cap to limit traversal cost."""
    try:
        err, arr = AXUIElementCopyAttributeValues(elem, kAXChildrenAttribute, 0, limit, None)
        if err == kAXErrorSuccess and arr:
            if isinstance(arr, Foundation.NSArray):  # type: ignore
                return list(arr)
            return arr
    except Exception:
        pass

    # Fallback to visible children if no regular children were returned
    try:
        err, arr = AXUIElementCopyAttributeValues(elem, kAXVisibleChildrenAttribute, 0, limit, None)
        if err == kAXErrorSuccess and arr:
            if isinstance(arr, Foundation.NSArray):  # type: ignore
                return list(arr)
            return arr
    except Exception:
        pass
    return []

# -----------------------------
# Window enumeration (z-order)
# -----------------------------

def list_onscreen_windows() -> List[Dict[str, Any]]:
    """Return windows on screen, enriched with z-index and bounds (fast)."""
    # All on-screen
    on_screen = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID
    )
    # Z-order: later in the list are "higher" => reverse enumerate
    z_map = { w.get('kCGWindowNumber'): i for i, w in enumerate(on_screen[::-1]) }

    all_info = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionAll,
        Quartz.kCGNullWindowID
    )

    out = []
    for w in all_info:
        if not w.get('kCGWindowIsOnscreen', False):
            continue
        wid = w.get('kCGWindowNumber')
        bounds = w.get('kCGWindowBounds') or {}
        out.append({
            "id": int(wid) if wid is not None else -1,
            "owner": w.get('kCGWindowOwnerName', '') or '',
            "name": w.get('kCGWindowName', '') or '',
            "pid": int(w.get('kCGWindowOwnerPID', 0)),
            "layer": int(w.get('kCGWindowLayer', 0)),
            "opacity": float(w.get('kCGWindowAlpha', 1.0)),
            "z_index": z_map.get(wid, -1),
            "bounds": {
                "x": int(bounds.get('X', 0)),
                "y": int(bounds.get('Y', 0)),
                "width": int(bounds.get('Width', 0)),
                "height": int(bounds.get('Height', 0)),
            }
        })
    # Sort by z (back->front)
    out.sort(key=lambda d: d["z_index"])
    return out

# -----------------------------
# App metadata & focus markers
# -----------------------------

def frontmost_app_pid() -> Optional[int]:
    app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
    return int(app.processIdentifier()) if app else None

def focused_handles():
    """Return (focused_app_elem, focused_window_elem, focused_ui_elem) (AX refs or None)."""
    sys_wide = AXUIElementCreateSystemWide()
    f_app = ax_attr(sys_wide, kAXFocusedApplicationAttribute)
    f_win = None
    f_ui  = None
    if f_app:
        f_win = ax_attr(f_app, kAXFocusedWindowAttribute)
        f_ui  = ax_attr(f_app, kAXFocusedUIElementAttribute)
    return f_app, f_win, f_ui

def ax_ref_id(ax_ref) -> Optional[int]:
    """Stable-ish integer id for AX elements (based on PyObjC's object id)."""
    if ax_ref is None:
        return None
    try:
        # pyobjc exposes __pyobjc_object__ sometimes, but id() is fine as a session id
        return int(id(ax_ref))
    except Exception:
        return None

# -----------------------------
# Tree serialization (fast path)
# -----------------------------

def serialize_element(elem,
                      depth: int,
                      max_depth: int,
                      max_children: int,
                      seen: Set[int]) -> Optional[Dict[str, Any]]:
    """Serialize minimal info for an AX element with strict traversal limits."""
    if elem is None:
        return None

    # Cycle guard
    elem_id = ax_ref_id(elem)
    if elem_id and elem_id in seen:
        return None
    if elem_id:
        seen.add(elem_id)

    role   = ax_attr(elem, kAXRoleAttribute)
    title  = ax_attr(elem, kAXTitleAttribute)
    value  = ax_attr(elem, kAXValueAttribute)
    desc   = ax_attr(elem, kAXDescriptionAttribute)
    rdesc  = ax_attr(elem, kAXRoleDescriptionAttribute)
    en     = ax_attr(elem, kAXEnabledAttribute)
    
    # Check if this element is focused (has focus)
    focused = ax_attr(elem, kAXFocusedUIElementAttribute)
    is_focused = (focused is not None and ax_ref_id(focused) == elem_id)

    # position/size
    pos    = ax_attr(elem, kAXPositionAttribute)  # dict {x,y}
    size   = ax_attr(elem, kAXSizeAttribute)      # dict {width,height}

    # Determine if this is a text input field
    is_text_field = role in ["AXTextField", "AXTextArea", "AXStaticText", "AXText"] or \
                   (role == "AXGroup" and value and isinstance(value, str))
    
    node = {
        "ax_id": elem_id,
        "role": role or "",
        "title": title or "",
        "value": value if isinstance(value, (str, int, float, bool)) else (str(value) if value is not None else ""),
        "description": desc or "",
        "role_description": rdesc or "",
        "enabled": bool(en) if en is not None else None,
        "position": pos,
        "size": size,
        "is_focused": is_focused,
        "is_text_field": is_text_field,
        "children": [],
    }

    if depth >= max_depth:
        return node

    kids = ax_children(elem, max_children)
    if kids:
        out_children = []
        # Keep traversal small and predictable
        for child in kids[:max_children]:
            ch = serialize_element(child, depth+1, max_depth, max_children, seen)
            if ch:
                out_children.append(ch)
        node["children"] = out_children

    return node

# -----------------------------
# Menubar & Dock (optional)
# -----------------------------

def get_menubar_items_for_pid(pid: int, max_items: int = 30) -> List[Dict[str, Any]]:
    try:
        app_elem = AXUIElementCreateApplication(pid)
        menubar = ax_attr(app_elem, "AXMenuBar")
        if not menubar:
            return []
        children = ax_children(menubar, max_items)
        out = []
        for i, item in enumerate(children[:max_items]):
            ttl = ax_attr(item, kAXTitleAttribute) or ""
            pos = ax_attr(item, kAXPositionAttribute)
            sz  = ax_attr(item, kAXSizeAttribute)
            out.append({
                "index": i,
                "title": ttl,
                "position": pos,
                "size": sz,
            })
        return out
    except Exception:
        return []

def get_dock_items(max_items: int = 60) -> List[Dict[str, Any]]:
    # Find Dock app by bundle id
    try:
        for app in AppKit.NSWorkspace.sharedWorkspace().runningApplications():
            if app.bundleIdentifier() == "com.apple.dock":
                dock_pid = int(app.processIdentifier())
                dock_elem = AXUIElementCreateApplication(dock_pid)
                # Dock's AX structure is deep; keep it tiny for speed
                items = []
                children = ax_children(dock_elem, max_items)
                for ch in children[:max_items]:
                    role = ax_attr(ch, kAXRoleAttribute) or ""
                    title = ax_attr(ch, kAXTitleAttribute) or ""
                    pos = ax_attr(ch, kAXPositionAttribute)
                    sz  = ax_attr(ch, kAXSizeAttribute)
                    items.append({
                        "role": role, "title": title, "position": pos, "size": sz
                    })
                return items
        return []
    except Exception:
        return []

# -----------------------------
# Cleanup utilities
# -----------------------------

def cleanup_foundation_resources():
    """Clean up Foundation resources to prevent accumulation."""
    try:
        # Force garbage collection to clean up any accumulated objects
        import gc
        gc.collect()
        
        # Additional cleanup for PyObjC objects
        try:
            # Clear any cached Foundation objects
            Foundation.NSProcessInfo.processInfo()._release()
        except:
            pass
            
    except Exception:
        pass

# -----------------------------
# Application filtering
# -----------------------------

# Apps to ignore in task analysis (helper/background apps)
IGNORED_APPS = {
    "com.grammarly.desktop",           # Grammarly Desktop
    "com.chatgpthelper",               # ChatGPT Helper
    "com.adguard.safari",              # AdGuard
    "com.ollama",                      # Ollama
    "com.viber.osx",                   # Rakuten Viber (if you want to ignore)
    "com.apple.dock",                  # Dock
    "com.apple.finder",                # Finder (desktop)
    "com.apple.controlcenter",         # Control Center
    "com.apple.systemuiserver",        # System UI Server
    "com.apple.spotlight",             # Spotlight
    "com.apple.textinputmenuagent",    # Text Input Menu Agent
    "com.magnet",                      # Magnet
    "com.apple.passwords",             # Passwords Menu Bar Extra
}

def should_ignore_app(bundle_id: str, app_name: str) -> bool:
    """Check if an app should be ignored in task analysis."""
    if not bundle_id:
        return False
    
    # Check bundle ID
    if bundle_id in IGNORED_APPS:
        return True
    
    # Check app name patterns
    ignored_patterns = [
        "grammarly", "chatgpt", "helper", "adguard", "ollama", 
        "dock", "control center", "spotlight", "passwords"
    ]
    
    app_name_lower = app_name.lower()
    for pattern in ignored_patterns:
        if pattern in app_name_lower:
            return True
    
    return False

def extract_focused_text_content(ax_tree: Dict[str, Any]) -> Optional[str]:
    """Extract text content from focused text fields in the AX tree."""
    if not ax_tree:
        return None
    
    # Check if this element is a focused text field
    if ax_tree.get("is_focused") and ax_tree.get("is_text_field"):
        value = ax_tree.get("value", "")
        if value and isinstance(value, str) and len(value.strip()) > 0:
            return value.strip()
    
    # Recursively check children
    children = ax_tree.get("children", [])
    for child in children:
        focused_text = extract_focused_text_content(child)
        if focused_text:
            return focused_text
    
    return None

# -----------------------------
# Main collection
# -----------------------------

def collect_state(max_depth: int,
                  max_children: int,
                  include_menubar: bool,
                  include_dock: bool,
                  include_helpers: bool = False) -> Dict[str, Any]:
    t0 = time.time()

    # N.B. NSWorkspace list is only updated when the runloop runs; tick it briefly
    # Skip runloop calls to avoid conflicts with PyGUI/other GUI frameworks
    # NSWorkspace should still work without explicit runloop calls
    pass

    front_pid = frontmost_app_pid()
    f_app, f_win, f_ui = focused_handles()
    f_app_id = ax_ref_id(f_app)
    f_win_id = ax_ref_id(f_win)
    f_ui_id  = ax_ref_id(f_ui)

    windows = list_onscreen_windows()

    # Group windows by PID for AX mapping
    pid_to_windows = {}
    for w in windows:
        pid_to_windows.setdefault(w["pid"], []).append(w)

    applications = []
    # Fast pass over running apps (ActivationPolicyRegular only, i.e., normal GUI apps)
    for app in AppKit.NSWorkspace.sharedWorkspace().runningApplications():
        try:
            if app.activationPolicy() != AppKit.NSApplicationActivationPolicyRegular:
                continue
            
            app_name = str(app.localizedName() or "")
            bundle_id = str(app.bundleIdentifier() or "")
            
            # Skip ignored apps (unless include_helpers is True)
            if not include_helpers and should_ignore_app(bundle_id, app_name):
                continue
                
            pid = int(app.processIdentifier())
            applications.append({
                "name": app_name,
                "bundle_id": bundle_id,
                "pid": pid,
                "active": bool(app.isActive()),
                "hidden": bool(app.isHidden()),
                "terminated": bool(app.isTerminated()),
                "window_ids": [w["id"] for w in pid_to_windows.get(pid, [])],
            })
        except Exception:
            continue

    # Build AX window trees per PID (strict caps)
    windows_out = []
    for pid, wins in pid_to_windows.items():
        # Skip windows from ignored apps
        app_info = next((app for app in applications if app["pid"] == pid), None)
        if not app_info:
            continue  # Skip if app was filtered out
            
        try:
            app_elem = AXUIElementCreateApplication(pid)
        except Exception:
            app_elem = None

        # Get AX windows (order typically top->back; may not match CGWindow z-order 1:1)
        ax_wins = []
        if app_elem:
            try:
                err, arr = AXUIElementCopyAttributeValue(app_elem, kAXWindowsAttribute, None)
                if err == kAXErrorSuccess and arr:
                    if isinstance(arr, Foundation.NSArray):  # type: ignore
                        ax_wins = list(arr)
                    else:
                        ax_wins = arr
            except Exception:
                ax_wins = []

        # Pair CG windows with AX windows by index (best-effort)
        for idx, cgwin in enumerate(wins):
            ax_tree = None
            seen: Set[int] = set()
            if idx < len(ax_wins):
                ax_tree = serialize_element(ax_wins[idx], 0, max_depth, max_children, seen)

            # Mark focus
            is_front_app = (pid == front_pid)
            is_focused_window = False
            if ax_tree and f_win_id:
                # If root ax_id equals focused window id
                is_focused_window = (ax_tree.get("ax_id") == f_win_id)

            windows_out.append({
                **cgwin,
                "frontmost_app": is_front_app,
                "focused_window": bool(is_focused_window),
                "ax_tree": ax_tree or {}
            })

    # Sort windows by z-order (topmost first)
    windows_out.sort(key=lambda w: w.get("z_index", 0), reverse=True)

    # Optionals
    menubar_items = []
    if include_menubar and front_pid:
        menubar_items = get_menubar_items_for_pid(front_pid)

    dock_items = []
    if include_dock:
        dock_items = get_dock_items()

    # Extract focused text content from all windows
    focused_text_content = None
    for window in windows_out:
        ax_tree = window.get("ax_tree", {})
        if ax_tree:
            text_content = extract_focused_text_content(ax_tree)
            if text_content:
                focused_text_content = text_content
                break  # Take the first focused text field found

    out = {
        "success": True,
        "meta": {
            "max_depth": max_depth,
            "max_children": max_children,
            "frontmost_pid": front_pid,
            "focused_app_ax_id": f_app_id,
            "focused_window_ax_id": f_win_id,
            "focused_ui_ax_id": f_ui_id,
            "focused_text_content": focused_text_content,
        },
        "applications": applications,
        "windows": windows_out,
        "menubar_items": menubar_items,
        "dock_items": dock_items,
        "elapsed_sec": round(time.time() - t0, 4),
    }
    
    # Clean up Foundation resources to prevent accumulation
    cleanup_foundation_resources()
    
    return out

# -----------------------------
# CLI
# -----------------------------

def main():
    ap = argparse.ArgumentParser(description="Enumerate macOS windows and AX trees, output JSON.")
    ap.add_argument("--max-depth", type=int, default=4, help="Max depth for AX traversal (default: 2)")
    ap.add_argument("--max-children", type=int, default=100, help="Cap children per node (default: 40)")
    ap.add_argument("--include-menubar", type=int, default=1, help="Include menubar scan for front app (0/1)")
    ap.add_argument("--include-dock", type=int, default=1, help="Include Dock scan (0/1)")
    ap.add_argument("--pretty", type=int, default=1, help="Pretty-print JSON (0/1)")
    args = ap.parse_args()

    # Quick permissions hint (avoid slow prompt unless needed)
    # If you get empty data, ensure: System Settings → Privacy & Security → Accessibility → allow your Python
    state = collect_state(
        max_depth=max(0, args.max_depth),
        max_children=max(1, args.max_children),
        include_menubar=bool(args.include_menubar),
        include_dock=bool(args.include_dock),
    )

    if args.pretty:
        print(json.dumps(state, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(state, separators=(",", ":"), ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
