"""Desktop state observation with OCR support"""
import asyncio
from datetime import datetime
from typing import Dict, Optional
import terminator

from config import (
    OBSERVATION_DEPTH,
    CAPTURE_SCREENSHOTS,
    USE_OCR,
    FOCUS_WINDOW_ONLY
)


class DesktopObserver:
    """Observes desktop state and extracts information"""

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

        window = None  # Initialize to avoid UnboundLocalError

        try:
            # Get focused window
            focused_element = self.desktop.focused_element()

            # Get window and app info
            try:
                window = focused_element.window()
                if window:
                    window_name = window.name()
                    state["focused_window"] = window_name if window_name else "Untitled"
            except Exception as e:
                print(f"[Observer] Could not get window: {e}")
                window = None

            try:
                app = focused_element.application()
                if app:
                    app_name = app.name()
                    state["focused_app"] = app_name if app_name else "Unknown"
            except Exception as e:
                print(f"[Observer] Could not get application: {e}")

            # Get accessibility tree for focused window
            if FOCUS_WINDOW_ONLY and window is not None:
                try:
                    # Get the process ID and window tree
                    if window:
                        pid = window.process_id()
                        window_title = state["focused_window"]

                        # Get the UI tree for this window
                        tree = self.desktop.get_window_tree(
                            pid=pid,
                            title=window_title if window_title != "Untitled" else None
                        )

                        state["accessibility_tree"] = self._format_ui_tree(tree)
                except Exception as e:
                    print(f"[Observer] Could not get window tree: {e}")
                    # Fallback: just get focused element children
                    try:
                        children = focused_element.children()
                        state["accessibility_tree"] = f"Focused Element: {focused_element.role()}\n"
                        for i, child in enumerate(children[:10]):
                            try:
                                role = child.role()
                                name = child.name() or ""
                                state["accessibility_tree"] += f"  - {role}: {name}\n"
                            except Exception:
                                # Skip children that can't be accessed
                                continue
                    except Exception as e2:
                        print(f"[Observer] Fallback also failed: {e2}")
                        state["accessibility_tree"] = f"Could not retrieve accessibility tree: {e}"

            # Capture screenshot and perform OCR
            if CAPTURE_SCREENSHOTS and window is not None:
                try:
                    # Capture the focused window
                    if window:
                        screenshot = window.capture()
                        state["screenshot"] = screenshot

                        # Perform OCR if enabled
                        if USE_OCR:
                            try:
                                ocr_result = await self.desktop.ocr_screenshot(screenshot)
                                state["ocr_text"] = ocr_result.strip() if ocr_result else "No text detected"
                            except Exception as e:
                                print(f"[Observer] OCR failed: {e}")
                                state["ocr_text"] = f"OCR failed: {e}"
                except Exception as e:
                    print(f"[Observer] Screenshot capture failed: {e}")

        except Exception as e:
            print(f"[Observer] Error during observation: {e}")
            state["accessibility_tree"] = f"Observation error: {e}"

        return state

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
