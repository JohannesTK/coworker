"""Action execution for Coworker AI Agent"""
import asyncio
from typing import Dict, Any
import terminator

from config import ACTION_TIMEOUT


class ActionExecutor:
    """Executes actions on the desktop"""

    def __init__(self):
        self.desktop = terminator.Desktop()

    async def execute(self, action: Dict[str, Any]) -> str:
        """
        Execute an action.

        Args:
            action: Action dict with type, target, value, steps

        Returns:
            Result message string
        """
        action_type = action.get("type", "unknown")

        try:
            if action_type == "click":
                return await self._execute_click(action)
            elif action_type == "type":
                return await self._execute_type(action)
            elif action_type == "press_key":
                return await self._execute_press_key(action)
            elif action_type == "open_application":
                return await self._execute_open_application(action)
            elif action_type == "open_url":
                return await self._execute_open_url(action)
            elif action_type == "execute_script":
                return await self._execute_script(action)
            elif action_type == "composite":
                return await self._execute_composite(action)
            elif action_type == "none":
                return "No action required"
            else:
                return f"Unknown action type: {action_type}"
        except Exception as e:
            return f"Error executing {action_type}: {str(e)}"

    async def _execute_click(self, action: Dict) -> str:
        """Execute click action"""
        target = action.get("target", "")
        if not target:
            return "No target specified for click"

        try:
            # Find element
            locator = self.desktop.locator(target)
            element = await asyncio.wait_for(
                locator.first(),
                timeout=ACTION_TIMEOUT
            )

            # Click it
            result = element.click()
            return f"Clicked element: {target} (method: {result.method})"
        except asyncio.TimeoutError:
            return f"Timeout: Could not find element: {target}"
        except Exception as e:
            return f"Click failed: {str(e)}"

    async def _execute_type(self, action: Dict) -> str:
        """Execute type action"""
        text = action.get("value", "")
        target = action.get("target", "")

        if not text:
            return "No text specified for typing"

        try:
            if target:
                # Type into specific element
                locator = self.desktop.locator(target)
                element = await asyncio.wait_for(
                    locator.first(),
                    timeout=ACTION_TIMEOUT
                )
                element.type_text(text)
                return f"Typed text into {target}: '{text[:50]}...'"
            else:
                # Type into focused element
                focused = self.desktop.focused_element()
                focused.type_text(text)
                return f"Typed text: '{text[:50]}...'"
        except asyncio.TimeoutError:
            return f"Timeout: Could not find element: {target}"
        except Exception as e:
            return f"Type failed: {str(e)}"

    async def _execute_press_key(self, action: Dict) -> str:
        """Execute press key action"""
        key = action.get("value", "")
        if not key:
            return "No key specified"

        try:
            await self.desktop.press_key(key)
            return f"Pressed key: {key}"
        except Exception as e:
            return f"Press key failed: {str(e)}"

    async def _execute_open_application(self, action: Dict) -> str:
        """Execute open application action"""
        app_name = action.get("target", "") or action.get("value", "")
        if not app_name:
            return "No application name specified"

        try:
            self.desktop.open_application(app_name)
            return f"Opened application: {app_name}"
        except Exception as e:
            return f"Open application failed: {str(e)}"

    async def _execute_open_url(self, action: Dict) -> str:
        """Execute open URL action"""
        url = action.get("value", "")
        if not url:
            return "No URL specified"

        try:
            self.desktop.open_url(url)
            return f"Opened URL: {url}"
        except Exception as e:
            return f"Open URL failed: {str(e)}"

    async def _execute_script(self, action: Dict) -> str:
        """Execute JavaScript in browser"""
        script = action.get("value", "")
        if not script:
            return "No script specified"

        try:
            result = await self.desktop.execute_browser_script(script)
            return f"Executed script. Result: {result[:100]}..."
        except Exception as e:
            return f"Script execution failed: {str(e)}"

    async def _execute_composite(self, action: Dict) -> str:
        """Execute composite action (multiple steps)"""
        steps = action.get("steps", [])
        if not steps:
            return "No steps specified for composite action"

        results = []
        for i, step in enumerate(steps, 1):
            print(f"  [Executor] Step {i}/{len(steps)}: {step.get('type', 'unknown')}")
            result = await self.execute(step)
            results.append(f"Step {i}: {result}")

            # Small delay between steps
            await asyncio.sleep(0.5)

        return "\n".join(results)

    def validate_action(self, action: Dict) -> tuple[bool, str]:
        """
        Validate an action before execution.

        Returns:
            (is_valid, error_message)
        """
        action_type = action.get("type")
        if not action_type:
            return False, "Action type not specified"

        required_fields = {
            "click": ["target"],
            "type": ["value"],
            "press_key": ["value"],
            "open_application": ["target"],
            "open_url": ["value"],
            "execute_script": ["value"],
            "composite": ["steps"]
        }

        if action_type in required_fields:
            for field in required_fields[action_type]:
                if not action.get(field):
                    return False, f"Required field '{field}' missing for action type '{action_type}'"

        return True, "Valid"
