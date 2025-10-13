"""Desktop state observation with OCR support"""
import asyncio
from datetime import datetime
from typing import Dict, Optional
import terminator

from config import (
    OBSERVATION_DEPTH,
    CAPTURE_SCREENSHOTS,
    USE_OCR,
    FOCUS_WINDOW_ONLY,
    IS_WINDOWS,
    IS_MACOS
)


class DesktopObserver:
    """
    Observes desktop state and extracts information.

    Cross-platform support:
    - Windows: Uses UI Automation API (best support)
    - macOS: Uses Accessibility API (partial support)
    - Linux: Uses AT-SPI (experimental)
    """

    def __init__(self):
        self.desktop = terminator.Desktop()

    def _format_ui_tree(self, node: terminator.UINode, depth: int = 0, max_depth: int = OBSERVATION_DEPTH) -> str:
        """Format UI tree as text with indentation"""
        if depth > max_depth:
            return ""

        lines = []
        indent = "  " * depth

        # Format current node
        attrs = node.attributes
        role = attrs.role if attrs.role else "unknown"
        name = attrs.name if attrs.name else ""
        value = attrs.value if attrs.value else ""

        node_str = f"{indent}{role}"
        if name:
            node_str += f" '{name}'"
        if value and value != name:
            node_str += f" = '{value[:50]}'"  # Truncate long values

        lines.append(node_str)

        # Format children
        for child in node.children[:20]:  # Limit children to avoid huge trees
            child_str = self._format_ui_tree(child, depth + 1, max_depth)
            if child_str:
                lines.append(child_str)

        if len(node.children) > 20:
            lines.append(f"{indent}  ... ({len(node.children) - 20} more children)")

        return "\n".join(lines)

    async def observe(self) -> Dict:
        """
        Observe current desktop state.

        Returns:
            Dict with keys:
                - focused_window: str
                - focused_app: str
                - timestamp: str
                - accessibility_tree: str
                - ocr_text: str
                - screenshot: Optional[ScreenshotResult]
        """
        state = {
            "focused_window": "unknown",
            "focused_app": "unknown",
            "timestamp": datetime.now().isoformat(),
            "accessibility_tree": "",
            "ocr_text": "",
            "screenshot": None
        }

        try:
            # Platform-specific observation approaches
            if IS_WINDOWS:
                await self._observe_windows(state)
            else:
                await self._observe_macos_linux(state)

        except Exception as e:
            print(f"[Observer] Error during observation: {e}")
            import traceback
            traceback.print_exc()
            state["accessibility_tree"] = f"Observation error: {e}"

        return state

    async def _observe_windows(self, state: Dict):
        """Windows-specific observation using UI Automation API"""
        try:
            # Get focused element for app info
            focused_element = self.desktop.focused_element()

            # Get application name
            try:
                app = focused_element.application()
                if app:
                    app_name = app.name()
                    state["focused_app"] = app_name if app_name else "Unknown"
            except Exception as e:
                print(f"[Observer] Could not get application (Windows UI Automation): {e}")

            # Try to get current window info (async)
            try:
                window_info = await self.desktop.get_current_window()
                if window_info and isinstance(window_info, dict):
                    state["focused_window"] = window_info.get("title", "unknown")
                    print(f"[Observer] Current window: {state['focused_window']}")
            except Exception as e:
                print(f"[Observer] get_current_window failed: {e}")

            # Get full accessibility tree (Windows approach)
            try:
                tree_data = await self.desktop.get_all_applications_tree()
                if tree_data:
                    # tree_data is a list of dicts, convert to readable string
                    import json
                    if isinstance(tree_data, list):
                        # Format as JSON string
                        tree_str = json.dumps(tree_data, indent=2)
                        # Truncate if too large
                        state["accessibility_tree"] = tree_str if len(tree_str) < 10000 else tree_str[:10000] + "\n... (truncated)"
                        print(f"[Observer] Got accessibility tree: {len(tree_str)} chars ({len(tree_data)} root elements)")
                    else:
                        state["accessibility_tree"] = str(tree_data)
                        print(f"[Observer] Got accessibility tree: {len(str(tree_data))} chars")
            except Exception as e:
                print(f"[Observer] get_all_applications_tree failed: {e}")
                # Fallback: try to get focused window tree using locator
                try:
                    windows = await self.desktop.locator("role:Window").all()
                    for window in windows:
                        if window.is_focused():
                            state["focused_window"] = window.name()
                            # Get children of focused window
                            children = window.children()
                            tree_lines = [f"Focused Window: {window.name()}"]
                            for i, child in enumerate(children[:20]):
                                try:
                                    tree_lines.append(f"  {child.role()}: {child.name()}")
                                except:
                                    pass
                            state["accessibility_tree"] = "\n".join(tree_lines)
                            print(f"[Observer] Got window tree via locator: {len(children)} children")

                            # Try to capture screenshot
                            if CAPTURE_SCREENSHOTS:
                                try:
                                    screenshot = window.capture()
                                    state["screenshot"] = screenshot
                                    print(f"[Observer] Captured screenshot")

                                    # Perform OCR
                                    if USE_OCR and screenshot:
                                        try:
                                            ocr_result = await self.desktop.ocr_screenshot(screenshot)
                                            state["ocr_text"] = ocr_result.strip() if ocr_result else "No text detected"
                                            print(f"[Observer] OCR extracted: {len(state['ocr_text'])} chars")
                                        except Exception as ocr_e:
                                            print(f"[Observer] OCR failed: {ocr_e}")
                                            state["ocr_text"] = f"OCR failed: {ocr_e}"
                                except Exception as cap_e:
                                    print(f"[Observer] Screenshot capture failed: {cap_e}")
                            break
                except Exception as loc_e:
                    print(f"[Observer] Locator fallback failed: {loc_e}")

        except Exception as e:
            print(f"[Observer] Windows observation error: {e}")
            import traceback
            traceback.print_exc()

    async def _observe_macos_linux(self, state: Dict):
        """macOS/Linux observation using Accessibility API"""
        try:
            # Get focused element for app info
            focused_element = self.desktop.focused_element()

            # Get application name
            try:
                app = focused_element.application()
                if app:
                    app_name = app.name()
                    state["focused_app"] = app_name if app_name else "Unknown"
            except Exception as e:
                platform_note = " (macOS Accessibility)" if IS_MACOS else ""
                print(f"[Observer] Could not get application{platform_note}: {e}")

            # Try to get current window info (async)
            try:
                window_info = await self.desktop.get_current_window()
                if window_info and isinstance(window_info, dict):
                    state["focused_window"] = window_info.get("title", "unknown")
                    print(f"[Observer] Current window: {state['focused_window']}")
            except Exception as e:
                print(f"[Observer] get_current_window failed: {e}")

            # Try to get accessibility tree using get_all_applications_tree (cross-platform)
            try:
                tree_data = await self.desktop.get_all_applications_tree()
                if tree_data:
                    # tree_data might be a list of dicts or string depending on platform
                    import json
                    if isinstance(tree_data, list):
                        # Format as JSON string
                        tree_str = json.dumps(tree_data, indent=2)
                        # Truncate if too large
                        state["accessibility_tree"] = tree_str if len(tree_str) < 10000 else tree_str[:10000] + "\n... (truncated)"
                        print(f"[Observer] Got accessibility tree: {len(tree_str)} chars ({len(tree_data)} root elements)")
                    elif isinstance(tree_data, str):
                        state["accessibility_tree"] = tree_data if len(tree_data) < 10000 else tree_data[:10000] + "\n... (truncated)"
                        print(f"[Observer] Got accessibility tree: {len(tree_data)} chars")
                    else:
                        state["accessibility_tree"] = str(tree_data)
                        print(f"[Observer] Got accessibility tree: {len(str(tree_data))} chars")
            except Exception as e:
                print(f"[Observer] get_all_applications_tree failed: {e}")
                # Fallback: try to get focused window tree using locator (same as Windows)
                try:
                    windows = await self.desktop.locator("role:Window").all()
                    focused_found = False
                    for window in windows:
                        try:
                            if window.is_focused():
                                focused_found = True
                                state["focused_window"] = window.name()
                                # Get children of focused window
                                children = window.children()
                                tree_lines = [f"Focused Window: {window.name()}"]
                                for i, child in enumerate(children[:20]):
                                    try:
                                        tree_lines.append(f"  {child.role()}: {child.name()}")
                                    except:
                                        pass
                                state["accessibility_tree"] = "\n".join(tree_lines)
                                print(f"[Observer] Got window tree via locator: {len(children)} children")

                                # Try to capture screenshot
                                if CAPTURE_SCREENSHOTS:
                                    try:
                                        screenshot = window.capture()
                                        state["screenshot"] = screenshot
                                        print(f"[Observer] Captured screenshot")

                                        # Perform OCR
                                        if USE_OCR and screenshot:
                                            try:
                                                ocr_result = await self.desktop.ocr_screenshot(screenshot)
                                                state["ocr_text"] = ocr_result.strip() if ocr_result else "No text detected"
                                                print(f"[Observer] OCR extracted: {len(state['ocr_text'])} chars")
                                            except Exception as ocr_e:
                                                print(f"[Observer] OCR failed: {ocr_e}")
                                                state["ocr_text"] = f"OCR failed: {ocr_e}"
                                    except Exception as cap_e:
                                        print(f"[Observer] Screenshot capture failed: {cap_e}")
                                break
                        except Exception as win_e:
                            # Skip windows that can't be accessed
                            continue

                    if not focused_found:
                        print(f"[Observer] Could not find focused window via locator")
                        # Last resort: try focused_element children
                        try:
                            children = focused_element.children()
                            state["accessibility_tree"] = f"Focused Element: {focused_element.role()}\n"
                            for i, child in enumerate(children[:10]):
                                try:
                                    role = child.role()
                                    name = child.name() or ""
                                    state["accessibility_tree"] += f"  - {role}: {name}\n"
                                except Exception:
                                    continue
                            print(f"[Observer] Got focused element children: {len(children)}")
                        except Exception as e3:
                            print(f"[Observer] Focused element children failed: {e3}")

                except Exception as loc_e:
                    print(f"[Observer] Locator fallback failed: {loc_e}")
                    import traceback
                    traceback.print_exc()

        except Exception as e:
            print(f"[Observer] macOS/Linux observation error: {e}")
            import traceback
            traceback.print_exc()

    def format_state_for_display(self, state: Dict) -> str:
        """Format state for terminal display"""
        lines = [
            "=" * 80,
            f"Desktop State - {state['timestamp']}",
            "=" * 80,
            f"Focused App: {state['focused_app']}",
            f"Focused Window: {state['focused_window']}",
            "",
            "Accessibility Tree:",
            "-" * 80,
            state['accessibility_tree'][:2000] + "..." if len(state['accessibility_tree']) > 2000 else state['accessibility_tree'],
            "",
            "OCR Text (Visible Content):",
            "-" * 80,
            state['ocr_text'][:1000] + "..." if len(state['ocr_text']) > 1000 else state['ocr_text'],
            "=" * 80,
        ]
        return "\n".join(lines)
