#!/usr/bin/env python3
"""
Computer Use Agent (CUA) - Goal-driven desktop automation

A sophisticated agent that:
1. Takes user goals via CLI
2. Captures desktop state using Accessibility APIs
3. Uses GPT-OSS-120B for multi-step reasoning and planning
4. Executes actions on the desktop
5. Observes changes and iterates until goal completion
"""

import json
import time
import sys
import os
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import subprocess
import pyautogui
from pynput import mouse, keyboard
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
import typer
from pydantic import BaseModel

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, continue without it
    pass

# Import our desktop monitoring module
from ax_inspect import collect_state, cleanup_foundation_resources

# Import OpenAI client for Groq API
try:
    from openai import OpenAI
except ImportError:
    print("Error: openai library not found. Install it with: pip install openai")
    sys.exit(1)

console = Console()
app = typer.Typer(help="Computer Use Agent - Goal-driven desktop automation")


class ActionType(str, Enum):
    """Types of actions the agent can execute."""
    CLICK = "click"
    CLICK_ELEMENT = "click_element"
    TYPE = "type"
    SCROLL = "scroll"
    DRAG = "drag"
    KEY_COMBO = "key_combo"
    PRESS_KEY = "press_key"
    WAIT = "wait"
    FOCUS_WINDOW = "focus_window"
    OPEN_APP = "open_app"
    SEARCH = "search"


@dataclass
class Action:
    """Represents an action to be executed."""
    type: ActionType
    description: str
    parameters: Dict[str, Any]
    confidence: float = 1.0
    reasoning: str = ""


@dataclass
class Plan:
    """Represents a multi-step plan."""
    goal: str
    steps: List[Action]
    reasoning: str
    confidence: float
    estimated_time: int  # seconds


@dataclass
class Observation:
    """Represents an observation of the desktop state."""
    timestamp: float
    desktop_state: Dict[str, Any]
    changes_detected: List[str]
    goal_progress: float  # 0.0 to 1.0


class CUAAgent:
    """Computer Use Agent - Main agent class."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("Groq API key not provided. Set GROQ_API_KEY environment variable.")
        
        # Initialize OpenAI client with Groq endpoint
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        
        # Agent state
        self.current_goal = ""
        self.current_plan: Optional[Plan] = None
        self.observations: List[Observation] = []
        self.executed_actions: List[Action] = []
        
        # Configure pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
        
        # Check permissions
        self._check_permissions()
        
        # Clean up any existing accessibility resources
        self._cleanup_resources()
    
    def _check_permissions(self):
        """Check if the application has necessary permissions."""
        console.print("[blue]Checking permissions...[/blue]")
        
        # Test AppleScript accessibility
        try:
            script = '''
            tell application "System Events"
                get name of first process
            end tell
            '''
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                console.print("[red]❌ AppleScript accessibility permission denied[/red]")
                console.print("[yellow]Please grant Terminal accessibility permissions in System Preferences > Security & Privacy > Privacy > Accessibility[/yellow]")
                raise PermissionError("AppleScript accessibility permission required")
            else:
                console.print("[green]✓ AppleScript accessibility permission granted[/green]")
        except subprocess.TimeoutExpired:
            console.print("[red]❌ AppleScript timeout - permission may be denied[/red]")
            raise PermissionError("AppleScript accessibility permission required")
        except Exception as e:
            console.print(f"[red]❌ Permission check failed: {e}[/red]")
            raise PermissionError("AppleScript accessibility permission required")
        
        # Test pyautogui (optional)
        try:
            # Try to get screen size
            screen_size = pyautogui.size()
            console.print(f"[green]✓ PyAutoGUI working (screen: {screen_size})[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ PyAutoGUI may not work: {e}[/yellow]")
            console.print("[yellow]PyAutoGUI requires additional permissions but AppleScript will be used as fallback[/yellow]")
    
    def _cleanup_resources(self):
        """Clean up accessibility resources between runs."""
        try:
            # Import cleanup function
            from ax_inspect import cleanup_foundation_resources
            cleanup_foundation_resources()
            
            # Small delay to let system settle
            time.sleep(0.5)
            
        except Exception as e:
            console.print(f"[yellow]Cleanup warning: {e}[/yellow]")
    
    def _log_active_window_tree(self, desktop_state: Dict[str, Any]) -> None:
        """Log the accessibility tree of the active/frontmost window."""
        try:
            windows = desktop_state.get('windows', [])
            frontmost_pid = desktop_state.get('meta', {}).get('frontmost_pid')
            menubar_items = desktop_state.get('menubar_items', [])
            
            # Determine active app from menubar
            active_app_from_menubar = None
            if menubar_items:
                # Debug: show all menubar items
                console.print(f"[blue]Menubar items: {[item.get('title', '') for item in menubar_items[:5]]}[/blue]")
                # The first menubar item is usually the app name
                first_item = menubar_items[0] if menubar_items else {}
                active_app_from_menubar = first_item.get('title', '')
            else:
                console.print("[yellow]No menubar items found[/yellow]")
            
            console.print(f"[blue]Active app (from menubar): {active_app_from_menubar}[/blue]")
            console.print(f"[blue]Frontmost PID: {frontmost_pid}[/blue]")
            
            # Find Calculator window first (priority for Calculator tasks)
            calculator_window = None
            for window in windows:
                if 'Calculator' in window.get('owner', '') and window.get('z_index', 0) > 0:
                    calculator_window = window
                    break
            
            # Find the frontmost window
            frontmost_window = None
            for window in windows:
                if window.get('pid') == frontmost_pid and window.get('z_index', 0) > 0:
                    frontmost_window = window
                    break
            
            # Determine which window to treat as "active" - prioritize Calculator if visible
            active_window = calculator_window if calculator_window else frontmost_window
            
            if active_window:
                window_name = active_window.get('name', 'Unknown')
                window_owner = active_window.get('owner', 'Unknown')
                ax_tree = active_window.get('ax_tree', {})
                
                if calculator_window and calculator_window == active_window:
                    console.print(f"[green]Calculator is active: {window_owner} - {window_name}[/green]")
                else:
                    console.print(f"[blue]Active window: {window_owner} - {window_name}[/blue]")
                
                if ax_tree:
                    console.print("[blue]Active window tree structure:[/blue]")
                    self._debug_tree_structure(ax_tree, max_depth=8)  # Increased depth to see Calculator buttons
                else:
                    console.print("[yellow]No accessibility tree for active window[/yellow]")
            else:
                console.print("[yellow]No active window found[/yellow]")
            
            # Log frontmost window info for debugging
            if frontmost_window and frontmost_window != active_window:
                fm_name = frontmost_window.get('name', 'Unknown')
                fm_owner = frontmost_window.get('owner', 'Unknown')
                console.print(f"[dim]Frontmost window: {fm_owner} - {fm_name}[/dim]")
                
        except Exception as e:
            console.print(f"[yellow]Error logging active window tree: {e}[/yellow]")
    
    def _debug_tree_structure(self, ax_tree: Dict[str, Any], max_depth: int = 3) -> None:
        """Debug helper to show tree structure."""
        
        def traverse(node, depth=0):
            if depth > max_depth:
                return
            
            node_title = node.get('title', '')
            node_description = node.get('description', '')
            node_value = node.get('value', '')
            node_role = node.get('role', '')
            children = node.get('children', [])
            
            indent = "  " * depth
            element_info = f"{node_role}"
            if node_title:
                element_info += f" '{node_title}'"
            if node_description:
                element_info += f" (desc: '{node_description}')"
            if node_value:
                element_info += f" (value: '{node_value}')"
            
            console.print(f"[dim]{indent}{element_info} ({len(children)} children)[/dim]")
            
            for child in children:
                traverse(child, depth + 1)
        
        traverse(ax_tree)
    
    def _verify_ui_ready(self, goal: str, desktop_state: Dict[str, Any]) -> bool:
        """Use LLM to verify if the UI is ready for the next action."""
        try:
            summary = self._create_desktop_summary(desktop_state)
            
            prompt = f"""
GOAL: {goal}

CURRENT DESKTOP STATE:
{summary}

EXECUTED ACTIONS: {len(self.executed_actions)}

Analyze the current desktop state and determine if the UI is ready for the next action. Look for:

1. **App Launch State**: If an app was recently launched, is it fully loaded and ready?
2. **Active App Detection**: Check the menubar to see which app is actually active (this is more reliable than window focus)
3. **UI Elements**: Are the expected UI elements (buttons, fields, etc.) visible and accessible?
4. **Loading Indicators**: Are there any loading spinners, progress bars, or other indicators that suggest the UI is still settling?
5. **Race Conditions**: Does the accessibility tree look incomplete or missing expected elements?
6. **Target App Visibility**: For Calculator tasks, is the Calculator window visible even if not active?

Respond with only "READY" if the UI is ready for the next action, or "WAIT" if it needs more time to settle.

Examples:
- App just launched but accessibility tree is empty → WAIT
- Menubar shows Calculator is active → READY
- Window focused but buttons not visible → WAIT  
- All expected elements present and accessible → READY
- Loading indicators visible → WAIT
- Calculator visible but Terminal still active → READY (can proceed with Calculator)
"""

            response = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip().upper()
            return result == "READY"
            
        except Exception as e:
            console.print(f"[yellow]UI verification failed: {e}[/yellow]")
            return True  # Default to ready if verification fails
    
    def _wait_for_ui_ready(self, goal: str, max_wait: float = 5.0) -> bool:
        """Wait for UI to be ready, checking periodically."""
        console.print("[blue]Verifying UI is ready...[/blue]")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                # Capture current state
                current_state = self._safe_capture_desktop_state()
                
                # Log active window tree for debugging
                self._log_active_window_tree(current_state)
                
                # Check if UI is ready
                if self._verify_ui_ready(goal, current_state):
                    console.print("[green]UI is ready[/green]")
                    return True
                
                console.print("[yellow]UI not ready, waiting...[/yellow]")
                time.sleep(1.0)
                
            except Exception as e:
                console.print(f"[yellow]UI verification error: {e}[/yellow]")
                time.sleep(1.0)
        
        console.print("[yellow]UI verification timeout, proceeding anyway[/yellow]")
        return False
    
    def capture_desktop_state(self) -> Dict[str, Any]:
        """Capture current desktop state."""
        return collect_state(
            max_depth=10,  # Increased depth to reach Calculator buttons
            max_children=500,  # Increased children limit to capture all Calculator buttons
            include_menubar=True,
            include_dock=True,
            include_helpers=False
        )
    
    def _safe_capture_desktop_state(self) -> Dict[str, Any]:
        """Safely capture desktop state with timeout and error handling."""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Desktop state capture timed out")
        
        # Set timeout for desktop capture
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)  # 10 second timeout
        
        try:
            # Use moderate parameters for safety but still useful
            state = collect_state(
                max_depth=8,  # Increased depth to reach Calculator buttons
                max_children=300,  # Increased children limit to capture Calculator buttons
                include_menubar=False,  # Skip menubar
                include_dock=False,  # Skip dock
                include_helpers=False
            )
            signal.alarm(0)  # Cancel timeout
            return state
            
        except TimeoutError:
            signal.alarm(0)  # Cancel timeout
            console.print("[yellow]Desktop capture timed out, using minimal state[/yellow]")
            return {"success": False, "error": "timeout"}
            
        except Exception as e:
            signal.alarm(0)  # Cancel timeout
            console.print(f"[yellow]Desktop capture failed: {e}[/yellow]")
            return {"success": False, "error": str(e)}
    
    def create_plan(self, goal: str, desktop_state: Dict[str, Any]) -> Plan:
        """Create a multi-step plan using GPT-OSS-120B."""
        
        # Create desktop summary
        summary = self._create_desktop_summary(desktop_state)
        
        prompt = f"""
You are an advanced Computer Use Agent with access to macOS desktop automation capabilities.

GOAL: {goal}

CURRENT DESKTOP STATE:
{summary}

Based on the goal and current desktop state, create a detailed multi-step plan. You have access to these actions:
- click: Click on UI elements using coordinates (x, y)
- click_element: Click on UI elements using accessibility properties (role, title, description)
- type: Type text into focused fields
- scroll: Scroll in windows or areas
- drag: Drag elements from one location to another
- key_combo: Execute keyboard shortcuts (e.g., Cmd+C, Cmd+V)
- press_key: Press a single key (e.g., return, enter, space, tab)
- wait: Wait for a specified duration
- focus_window: Focus on a specific window
- open_app: Open an application
- search: Perform a search operation

IMPORTANT:
- Use focus_window to bring applications to front before interacting with them
- Prefer click_element over click for better reliability (use role and description)
- For Safari address bar, use click_element with role "text field" and description "smart search field"
- Use wait actions between steps to allow UI to settle
- Be specific about coordinates, text content, and parameters
- Consider the current desktop state and what's visible
- Break down complex tasks into smaller, executable steps
- Include reasoning for each step
- Estimate the time needed for each step

Respond with a JSON plan in this exact format:
{{
    "goal": "{goal}",
    "reasoning": "Detailed explanation of the approach and strategy",
    "confidence": 0.85,
    "estimated_time": 120,
    "steps": [
        {{
            "type": "focus_window",
            "description": "Bring Safari to the front",
            "parameters": {{"title": "Safari"}},
            "confidence": 0.9,
            "reasoning": "Need to focus Safari before interacting with it"
        }},
        {{
            "type": "wait",
            "description": "Wait for Safari to become active",
            "parameters": {{"duration": 1.0}},
            "confidence": 0.95,
            "reasoning": "Allow time for window focus to complete"
        }},
        {{
            "type": "click_element",
            "description": "Click on the Safari address bar",
            "parameters": {{"role": "text field", "description": "smart search field"}},
            "confidence": 0.9,
            "reasoning": "Need to focus the address bar to type the URL"
        }},
        {{
            "type": "type",
            "description": "Type the website URL",
            "parameters": {{"text": "https://example.com"}},
            "confidence": 0.95,
            "reasoning": "Entering the target website URL"
        }},
        {{
            "type": "press_key",
            "description": "Press Return to navigate",
            "parameters": {{"key": "return"}},
            "confidence": 0.95,
            "reasoning": "Submit the URL to navigate to the website"
        }}
    ]
}}
"""

        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent planning
                max_tokens=2000
            )
            
            plan_data = json.loads(response.choices[0].message.content)
            
            # Convert to Plan object
            steps = []
            for step_data in plan_data.get("steps", []):
                steps.append(Action(
                    type=ActionType(step_data["type"]),
                    description=step_data["description"],
                    parameters=step_data["parameters"],
                    confidence=step_data.get("confidence", 1.0),
                    reasoning=step_data.get("reasoning", "")
                ))
            
            return Plan(
                goal=plan_data["goal"],
                steps=steps,
                reasoning=plan_data["reasoning"],
                confidence=plan_data.get("confidence", 0.8),
                estimated_time=plan_data.get("estimated_time", 60)
            )
            
        except Exception as e:
            console.print(f"[red]Error creating plan: {e}[/red]")
            # Return a fallback plan
            return Plan(
                goal=goal,
                steps=[],
                reasoning="Failed to create plan due to API error",
                confidence=0.0,
                estimated_time=0
            )
    
    def execute_action(self, action: Action) -> bool:
        """Execute a single action."""
        try:
            console.print(f"[blue]Executing:[/blue] {action.description}")
            
            if action.type == ActionType.CLICK:
                x = action.parameters.get("x", 0)
                y = action.parameters.get("y", 0)
                button = action.parameters.get("button", "left")
                
                # Check if coordinates are valid
                if x <= 0 or y <= 0:
                    console.print(f"[yellow]Warning: Invalid coordinates ({x}, {y}), skipping click[/yellow]")
                    return False
                
                # Use AppleScript for more reliable clicking
                script = f'''
                tell application "System Events"
                    click at {{{x}, {y}}}
                end tell
                '''
                result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                if result.returncode != 0:
                    console.print(f"[yellow]AppleScript click failed, trying pyautogui fallback[/yellow]")
                    pyautogui.click(x, y, button=button)
                
            elif action.type == ActionType.CLICK_ELEMENT:
                # Click on a specific UI element using accessibility APIs
                element_role = action.parameters.get("role", "")
                element_title = action.parameters.get("title", "")
                element_description = action.parameters.get("description", "")
                
                # Use AppleScript to find and click the element with multiple strategies
                script = f'''
                tell application "System Events"
                    try
                        -- Strategy 1: Try description first (most specific)
                        set targetElement to first UI element whose description contains "{element_description}"
                        click targetElement
                        return "success"
                    on error
                        try
                            -- Strategy 2: Try title/name
                            set targetElement to first UI element whose name contains "{element_title}"
                            click targetElement
                            return "success"
                        on error
                            try
                                -- Strategy 3: Try role + description
                                set targetElement to first UI element whose role is "{element_role}" and description contains "{element_description}"
                                click targetElement
                                return "success"
                            on error
                                try
                                    -- Strategy 4: Try role + title
                                    set targetElement to first UI element whose role is "{element_role}" and name contains "{element_title}"
                                    click targetElement
                                    return "success"
                                on error
                                    try
                                        -- Strategy 5: Try just role (less specific)
                                        set targetElement to first UI element whose role is "{element_role}"
                                        click targetElement
                                        return "success"
                                    on error
                                        try
                                            -- Strategy 6: Try value attribute
                                            set targetElement to first UI element whose value contains "{element_title}"
                                            click targetElement
                                            return "success"
                                        on error
                                            try
                                                -- Strategy 7: Try any UI element with the text
                                                set targetElement to first UI element whose (description contains "{element_title}" or name contains "{element_title}" or value contains "{element_title}")
                                                click targetElement
                                                return "success"
                                            on error
                                                return "Element not found"
                                            end try
                                        end try
                                    end try
                                end try
                            end try
                        end try
                    end try
                end tell
                '''
                result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                if result.returncode != 0 or "Element not found" in result.stdout:
                    console.print(f"[yellow]Could not find element: {element_role} '{element_description or element_title}'[/yellow]")
                    console.print(f"[yellow]AppleScript output: {result.stdout.strip()}[/yellow]")
                    
                    # Try pyautogui fallback with coordinates
                    try:
                        # Get current desktop state to find coordinates
                        current_state = self._safe_capture_desktop_state()
                        windows = current_state.get('windows', [])
                        
                        # Look for the element in any visible window
                        # Prioritize Calculator window for Calculator-related actions
                        calculator_window = None
                        other_windows = []
                        
                        for window in windows:
                            if window.get('z_index', 0) > 0:  # Only visible windows
                                if 'Calculator' in window.get('owner', ''):
                                    calculator_window = window
                                else:
                                    other_windows.append(window)
                        
                        # Search Calculator window first if available
                        if calculator_window:
                            ax_tree = calculator_window.get('ax_tree', {})
                            if ax_tree:
                                element_coords = self._find_element_coordinates(ax_tree, element_title, element_description)
                                if element_coords:
                                    pyautogui.click(element_coords[0], element_coords[1])
                                    console.print(f"[green]Found element via coordinates in Calculator: {element_coords}[/green]")
                                    return True
                        
                        # Search other windows
                        for window in other_windows:
                            ax_tree = window.get('ax_tree', {})
                            if ax_tree:
                                element_coords = self._find_element_coordinates(ax_tree, element_title, element_description)
                                if element_coords:
                                    pyautogui.click(element_coords[0], element_coords[1])
                                    console.print(f"[green]Found element via coordinates: {element_coords}[/green]")
                                    return True
                    except Exception as e:
                        console.print(f"[yellow]Coordinate fallback failed: {e}[/yellow]")
                    
                    return False
                
            elif action.type == ActionType.TYPE:
                text = action.parameters.get("text", "")
                if text:
                    # Use AppleScript for typing
                    escaped_text = text.replace('"', '\\"')
                    script = f'''
                    tell application "System Events"
                        keystroke "{escaped_text}"
                    end tell
                    '''
                    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                    if result.returncode != 0:
                        console.print(f"[yellow]AppleScript typing failed, trying pyautogui fallback[/yellow]")
                        pyautogui.typewrite(text)
                
            elif action.type == ActionType.SCROLL:
                x = action.parameters.get("x", 0)
                y = action.parameters.get("y", 0)
                clicks = action.parameters.get("clicks", 3)
                
                # Use AppleScript for scrolling
                script = f'''
                tell application "System Events"
                    scroll {{{x}, {y}}} by {clicks}
                end tell
                '''
                result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                if result.returncode != 0:
                    console.print(f"[yellow]AppleScript scroll failed, trying pyautogui fallback[/yellow]")
                    pyautogui.scroll(clicks, x=x, y=y)
                
            elif action.type == ActionType.DRAG:
                start_x = action.parameters.get("start_x", 0)
                start_y = action.parameters.get("start_y", 0)
                end_x = action.parameters.get("end_x", 0)
                end_y = action.parameters.get("end_y", 0)
                duration = action.parameters.get("duration", 1.0)
                
                # Use AppleScript for dragging
                script = f'''
                tell application "System Events"
                    drag from {{{start_x}, {start_y}}} to {{{end_x}, {end_y}}}
                end tell
                '''
                result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                if result.returncode != 0:
                    console.print(f"[yellow]AppleScript drag failed, trying pyautogui fallback[/yellow]")
                    pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)
                
            elif action.type == ActionType.KEY_COMBO:
                keys = action.parameters.get("keys", [])
                if keys:
                    # Handle special keys properly
                    if keys == ["return"] or keys == ["enter"]:
                        # Use key code for Return key
                        script = '''
                        tell application "System Events"
                            key code 36
                        end tell
                        '''
                    else:
                        # Convert keys to AppleScript format
                        key_script = " + ".join([f'"{key}"' for key in keys])
                        script = f'''
                        tell application "System Events"
                            key down {key_script}
                            key up {key_script}
                        end tell
                        '''
                    
                    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                    if result.returncode != 0:
                        console.print(f"[yellow]AppleScript key combo failed, trying pyautogui fallback[/yellow]")
                        if keys == ["return"] or keys == ["enter"]:
                            pyautogui.press("enter")
                        else:
                            pyautogui.hotkey(*keys)
                
            elif action.type == ActionType.PRESS_KEY:
                key = action.parameters.get("key", "")
                if key:
                    # Handle special keys properly
                    if key.lower() in ["return", "enter"]:
                        script = '''
                        tell application "System Events"
                            key code 36
                        end tell
                        '''
                    elif key.lower() == "space":
                        script = '''
                        tell application "System Events"
                            key code 49
                        end tell
                        '''
                    elif key.lower() == "tab":
                        script = '''
                        tell application "System Events"
                            key code 48
                        end tell
                        '''
                    else:
                        # Use keystroke for other keys
                        script = f'''
                        tell application "System Events"
                            keystroke "{key}"
                        end tell
                        '''
                    
                    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                    if result.returncode != 0:
                        console.print(f"[yellow]AppleScript key press failed, trying pyautogui fallback[/yellow]")
                        pyautogui.press(key)
                
            elif action.type == ActionType.WAIT:
                duration = action.parameters.get("duration", 1.0)
                time.sleep(duration)
                
            elif action.type == ActionType.FOCUS_WINDOW:
                # Focus window by title or coordinates
                title = action.parameters.get("title", "")
                if title:
                    # Use AppleScript to focus window
                    script = f'''
                    tell application "{title}"
                        activate
                    end tell
                    '''
                    subprocess.run(["osascript", "-e", script])
                
            elif action.type == ActionType.OPEN_APP:
                app_name = action.parameters.get("app", "")
                if app_name:
                    subprocess.run(["open", "-a", app_name])
                    
            elif action.type == ActionType.SEARCH:
                query = action.parameters.get("query", "")
                # Open Spotlight and search using AppleScript
                script = f'''
                tell application "System Events"
                    key code 49 using command down
                    delay 0.5
                    keystroke "{query}"
                    delay 0.5
                    key code 36
                end tell
                '''
                result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                if result.returncode != 0:
                    console.print(f"[yellow]AppleScript search failed, trying pyautogui fallback[/yellow]")
                    pyautogui.hotkey("cmd", "space")
                    time.sleep(0.5)
                    pyautogui.typewrite(query)
                    time.sleep(0.5)
                    pyautogui.press("enter")
            
            # Record executed action
            self.executed_actions.append(action)
            return True
            
        except Exception as e:
            console.print(f"[red]Error executing action: {e}[/red]")
            console.print(f"[yellow]Action details: {action.type.value} - {action.description}[/yellow]")
            return False
    
    def observe_changes(self, previous_state: Dict[str, Any], current_state: Dict[str, Any]) -> List[str]:
        """Observe changes between desktop states."""
        changes = []
        
        # Compare window states
        prev_windows = {w.get("id"): w for w in previous_state.get("windows", [])}
        curr_windows = {w.get("id"): w for w in current_state.get("windows", [])}
        
        # Check for new windows
        for win_id, window in curr_windows.items():
            if win_id not in prev_windows:
                changes.append(f"New window opened: {window.get('name', 'Unknown')}")
        
        # Check for closed windows
        for win_id, window in prev_windows.items():
            if win_id not in curr_windows:
                changes.append(f"Window closed: {window.get('name', 'Unknown')}")
        
        # Check for focused text changes
        prev_text = previous_state.get("meta", {}).get("focused_text_content")
        curr_text = current_state.get("meta", {}).get("focused_text_content")
        
        if prev_text != curr_text:
            if curr_text:
                changes.append(f"Text input: {curr_text[:50]}...")
            else:
                changes.append("Text input cleared")
        
        return changes
    
    def assess_goal_progress(self, goal: str, current_state: Dict[str, Any]) -> float:
        """Assess progress towards the goal (0.0 to 1.0)."""
        
        # First try rule-based assessment
        rule_progress = self._assess_goal_progress_rules(goal, current_state)
        if rule_progress is not None:
            return rule_progress
        
        # Fall back to AI-based assessment
        summary = self._create_desktop_summary(current_state)
        
        prompt = f"""
GOAL: {goal}

CURRENT DESKTOP STATE:
{summary}

EXECUTED ACTIONS: {len(self.executed_actions)}

Analyze the current desktop state and determine if the goal has been achieved. Look for:
1. Visual indicators that the task is complete (results, confirmations, success messages)
2. UI elements that suggest the operation finished successfully
3. Changes in the interface that indicate completion
4. Any text or numbers that represent the expected outcome

Be strict about completion - only return 1.0 if the goal is clearly achieved with visible evidence.

Respond with only a number between 0.0 and 1.0.
"""

        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=10
            )
            
            progress_text = response.choices[0].message.content.strip()
            progress = float(progress_text)
            return max(0.0, min(1.0, progress))  # Clamp between 0.0 and 1.0
            
        except Exception:
            return 0.5  # Default moderate progress
    
    def _assess_goal_progress_rules(self, goal: str, current_state: Dict[str, Any]) -> Optional[float]:
        """Rule-based goal progress assessment for common patterns."""
        
        # Extract key information from desktop state
        windows = current_state.get('windows', [])
        visible_windows = [w for w in windows if w.get('z_index', 0) > 0]
        
        # Look for completion indicators in UI elements
        completion_indicators = []
        
        for window in visible_windows:
            ax_tree = window.get('ax_tree', {})
            if ax_tree:
                # Extract all text content from the window
                all_text = self._extract_all_text_content(ax_tree)
                completion_indicators.extend(all_text)
        
        # Check for common completion patterns
        goal_lower = goal.lower()
        
        # For calculation tasks - look for numeric results
        if any(word in goal_lower for word in ['calculate', 'compute', 'math', 'add', 'subtract', 'multiply', 'divide']):
            # Look for numeric results in the UI
            for text in completion_indicators:
                if text and any(char.isdigit() for char in text):
                    # If we see numbers, likely a calculation result
                    if len(self.executed_actions) >= 3:  # At least some actions executed
                        return 0.9
        
        # For app opening tasks
        if any(word in goal_lower for word in ['open', 'launch', 'start']):
            # Look for any new application window that appeared
            if len(self.executed_actions) >= 1:  # At least one action executed
                return 0.8
        
        # For navigation tasks
        if any(word in goal_lower for word in ['navigate', 'go to', 'visit', 'open']):
            url_indicators = ['http', 'www', '.com', '.org', '.net']
            for text in completion_indicators:
                if any(indicator in text.lower() for indicator in url_indicators):
                    return 0.9
        
        # For document creation/editing
        if any(word in goal_lower for word in ['create', 'write', 'edit', 'document']):
            text_fields = []
            for window in visible_windows:
                ax_tree = window.get('ax_tree', {})
                if ax_tree:
                    text_fields.extend(self._extract_text_fields(ax_tree))
            
            if text_fields and len(self.executed_actions) >= 2:
                return 0.8
        
        return None  # No rule matched, use AI assessment
    
    def _extract_all_text_content(self, ax_tree: Dict[str, Any]) -> List[str]:
        """Extract all text content from accessibility tree."""
        texts = []
        
        def traverse(node):
            # Extract text from various sources
            for key in ['title', 'description', 'value', 'help']:
                if key in node and node[key]:
                    texts.append(str(node[key]))
            
            # Traverse children
            children = node.get('children', [])
            for child in children:
                traverse(child)
        
        traverse(ax_tree)
        return [t for t in texts if t and t.strip()]
    
    def _extract_text_fields(self, ax_tree: Dict[str, Any]) -> List[str]:
        """Extract text from text input fields."""
        text_fields = []
        
        def traverse(node):
            role = node.get('role', '')
            if role in ['AXTextField', 'AXTextArea', 'AXStaticText']:
                value = node.get('value', '') or node.get('title', '')
                if value:
                    text_fields.append(str(value))
            
            children = node.get('children', [])
            for child in children:
                traverse(child)
        
        traverse(ax_tree)
        return text_fields
    
    
    def _find_element_coordinates(self, ax_tree: Dict[str, Any], title: str, description: str) -> Optional[tuple]:
        """Find coordinates of a UI element in the accessibility tree."""
        
        def traverse(node):
            # Check if this node matches our criteria
            node_title = node.get('title', '')
            node_description = node.get('description', '')
            node_value = node.get('value', '')
            node_role = node.get('role', '')
            
            # Debug: print matching elements
            if (title and title in node_title) or (description and description in node_description) or (title and title in node_value):
                console.print(f"[green]Found matching element: role='{node_role}', title='{node_title}', desc='{node_description}', value='{node_value}'[/green]")
                
                # Get position if available
                position = node.get('position')
                size = node.get('size')
                
                console.print(f"[blue]Position data: position={position}, size={size}[/blue]")
                
                if position and isinstance(position, dict) and 'x' in position and 'y' in position:
                    x = position['x']
                    y = position['y']
                    
                    # Add half the size to get center coordinates
                    if size and isinstance(size, dict) and 'width' in size and 'height' in size:
                        x += size['width'] // 2
                        y += size['height'] // 2
                    
                    console.print(f"[green]Calculated center coordinates: ({x}, {y})[/green]")
                    return (x, y)
                else:
                    console.print(f"[yellow]No valid position data for element[/yellow]")
            
            # Traverse children
            children = node.get('children', [])
            for child in children:
                result = traverse(child)
                if result:
                    return result
            
            return None
        
        return traverse(ax_tree)
    
    def _create_desktop_summary(self, desktop_data: Dict[str, Any]) -> str:
        """Create a concise summary of desktop state for AI analysis."""
        summary_parts = []
        
        # Active applications
        active_apps = [app for app in desktop_data.get('applications', []) if app.get('active', False)]
        if active_apps:
            summary_parts.append(f"Active Applications: {', '.join([app['name'] for app in active_apps])}")
        
        # Frontmost application
        frontmost_pid = desktop_data.get('meta', {}).get('frontmost_pid')
        if frontmost_pid:
            frontmost_app = next((app for app in desktop_data.get('applications', []) if app['pid'] == frontmost_pid), None)
            if frontmost_app:
                summary_parts.append(f"Frontmost Application: {frontmost_app['name']}")
        
        # Visible windows with UI elements
        windows = desktop_data.get('windows', [])
        visible_windows = [w for w in windows if w.get('z_index', 0) > 0 and w.get('owner') not in ['Window Server', 'Dock', 'Control Centre']]
        
        if visible_windows:
            window_info = []
            for window in visible_windows[:3]:  # Limit to top 3 windows
                name = window.get('name', 'Untitled')
                owner = window.get('owner', 'Unknown')
                if name and name != 'Untitled':
                    window_info.append(f"{owner}: {name}")
                else:
                    window_info.append(owner)
                
                # Add key UI elements from the window
                ax_tree = window.get('ax_tree', {})
                if ax_tree:
                    key_elements = self._extract_key_elements(ax_tree)
                    if key_elements:
                        window_info.append(f"  Key elements: {', '.join(key_elements)}")
            
            summary_parts.append(f"Visible Windows: {', '.join(window_info)}")
        
        # Add focused text content if available
        focused_text = desktop_data.get('meta', {}).get('focused_text_content')
        if focused_text:
            truncated_text = focused_text[:200] + "..." if len(focused_text) > 200 else focused_text
            summary_parts.append(f"Currently Typing: \"{truncated_text}\"")
        
        return '\n'.join(summary_parts) if summary_parts else "No significant desktop activity detected"
    
    def _extract_key_elements(self, ax_tree: Dict[str, Any], max_depth: int = 2) -> List[str]:
        """Extract key UI elements from the accessibility tree."""
        elements = []
        
        def traverse(node, depth=0):
            if depth > max_depth:
                return
            
            role = node.get('role', '')
            title = node.get('title', '')
            description = node.get('description', '')
            value = node.get('value', '')
            
            # Look for important UI elements
            if role in ['AXTextField', 'AXTextArea', 'AXButton', 'AXLink', 'AXStaticText']:
                if description:
                    elements.append(f"{role}: '{description}'")
                elif title:
                    elements.append(f"{role}: '{title}'")
                elif value and isinstance(value, str) and len(value) < 50:
                    elements.append(f"{role}: '{value}'")
            
            # Recursively check children
            for child in node.get('children', []):
                traverse(child, depth + 1)
        
        traverse(ax_tree)
        return elements[:5]  # Limit to 5 key elements
    
    def run_goal_loop(self, goal: str, max_iterations: int = 10, skip_observation: bool = False) -> bool:
        """Run the main goal execution loop."""
        self.current_goal = goal
        
        console.print(Panel(f"[bold green]Goal:[/bold green] {goal}", title="Computer Use Agent"))
        
        # Initial observation
        console.print("[blue]Capturing initial desktop state...[/blue]")
        initial_state = self.capture_desktop_state()
        self.observations.append(Observation(
            timestamp=time.time(),
            desktop_state=initial_state,
            changes_detected=[],
            goal_progress=0.0
        ))
        
        for iteration in range(max_iterations):
            console.print(f"\n[bold]Iteration {iteration + 1}/{max_iterations}[/bold]")
            
            # Create or update plan
            current_state = self.observations[-1].desktop_state
            if not self.current_plan or iteration == 0:
                console.print("[blue]Creating execution plan...[/blue]")
                self.current_plan = self.create_plan(goal, current_state)
                
                # Display plan
                plan_table = Table(title="Execution Plan")
                plan_table.add_column("Step", style="cyan")
                plan_table.add_column("Action", style="magenta")
                plan_table.add_column("Description", style="white")
                plan_table.add_column("Confidence", style="green")
                
                for i, step in enumerate(self.current_plan.steps, 1):
                    plan_table.add_row(
                        str(i),
                        step.type.value,
                        step.description,
                        f"{step.confidence:.1%}"
                    )
                
                console.print(plan_table)
                console.print(f"[blue]Reasoning:[/blue] {self.current_plan.reasoning}")
                console.print(f"[blue]Estimated time:[/blue] {self.current_plan.estimated_time}s")
                
                # Ask for confirmation
                if not Confirm.ask("Proceed with this plan?"):
                    console.print("[yellow]Plan cancelled by user[/yellow]")
                    return False
            
            # Execute plan steps
            console.print("[blue]Executing plan steps...[/blue]")
            for i, step in enumerate(self.current_plan.steps):
                console.print(f"[cyan]Step {i+1}/{len(self.current_plan.steps)}:[/cyan] {step.description}")
                
                try:
                    # Wait for UI to be ready before executing action
                    if step.type in [ActionType.OPEN_APP, ActionType.FOCUS_WINDOW]:
                        self._wait_for_ui_ready(goal, max_wait=3.0)
                    
                    # Execute action with timeout protection
                    success = self.execute_action(step)
                    if not success:
                        console.print(f"[red]Failed to execute step {i+1}[/red]")
                        continue
                    
                    # Small delay between actions
                    time.sleep(0.5)
                    
                    # Refresh desktop state after each action (except last one)
                    if i < len(self.current_plan.steps) - 1:
                        console.print("[dim]Refreshing desktop state...[/dim]")
                        try:
                            # Quick cleanup before state refresh
                            self._cleanup_resources()
                            
                            # Quick state refresh to see UI changes
                            new_state = self._safe_capture_desktop_state()
                            
                            # Log active window tree
                            self._log_active_window_tree(new_state)
                            
                            # Verify UI is ready for next action
                            if not self._verify_ui_ready(goal, new_state):
                                console.print("[yellow]UI not ready, waiting briefly...[/yellow]")
                                time.sleep(1.0)
                            
                            # Update current state for next action
                            current_state = new_state
                        except Exception as e:
                            console.print(f"[dim]State refresh failed: {e}[/dim]")
                            # Continue with previous state
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]Execution interrupted by user[/yellow]")
                    return False
                except Exception as e:
                    console.print(f"[red]Unexpected error in step {i+1}: {e}[/red]")
                    console.print("[yellow]Continuing with next step...[/yellow]")
                    continue
            
            # Observe changes (with safety measures)
            if skip_observation:
                console.print("[yellow]Skipping observation phase[/yellow]")
                # Record minimal observation
                self.observations.append(Observation(
                    timestamp=time.time(),
                    desktop_state=current_state,  # Use previous state
                    changes_detected=["Observation skipped"],
                    goal_progress=0.7  # Assume good progress
                ))
                changes = ["Observation skipped"]
                progress = 0.7
            else:
                console.print("[blue]Observing changes...[/blue]")
                time.sleep(1.0)  # Wait for UI to update
                
                try:
                    # Use timeout protection for desktop state capture
                    new_state = self._safe_capture_desktop_state()
                    
                    # Log active window tree during observation
                    self._log_active_window_tree(new_state)
                    
                    # Detect changes
                    changes = self.observe_changes(current_state, new_state)
                    
                    # Assess progress
                    progress = self.assess_goal_progress(goal, new_state)
                    
                    # Record observation
                    self.observations.append(Observation(
                        timestamp=time.time(),
                        desktop_state=new_state,
                        changes_detected=changes,
                        goal_progress=progress
                    ))
                    
                except Exception as e:
                    console.print(f"[yellow]Observation failed: {e}[/yellow]")
                    console.print("[yellow]Continuing with next iteration...[/yellow]")
                    
                    # Record minimal observation
                    self.observations.append(Observation(
                        timestamp=time.time(),
                        desktop_state=current_state,  # Use previous state
                        changes_detected=["Observation failed"],
                        goal_progress=0.5  # Default moderate progress
                    ))
                    changes = ["Observation failed"]
                    progress = 0.5
            
            # Display progress
            console.print(f"[green]Progress: {progress:.1%}[/green]")
            if changes:
                console.print("[blue]Changes detected:[/blue]")
                for change in changes:
                    console.print(f"  • {change}")
            
            # Check if goal is achieved
            if progress >= 0.9:
                console.print("[bold green]Goal achieved![/bold green]")
                return True
            
            # Clean up resources
            cleanup_foundation_resources()
            
            # Additional cleanup between iterations
            self._cleanup_resources()
        
        console.print("[yellow]Maximum iterations reached. Goal may not be fully achieved.[/yellow]")
        return False


@app.command()
def run(
    goal: str = typer.Argument(..., help="The goal to achieve"),
    max_iterations: int = typer.Option(10, "--max-iterations", "-i", help="Maximum number of iterations"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="Groq API key"),
    skip_observation: bool = typer.Option(False, "--skip-observation", "-s", help="Skip observation phase to avoid crashes")
):
    """Run the Computer Use Agent with a specific goal."""
    try:
        agent = CUAAgent(api_key)
        success = agent.run_goal_loop(goal, max_iterations, skip_observation)
        
        if success:
            console.print("[bold green]✓ Goal completed successfully![/bold green]")
        else:
            console.print("[bold red]✗ Goal not completed[/bold red]")
        
        # Final cleanup
        try:
            agent._cleanup_resources()
        except:
            pass
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def interactive():
    """Run the Computer Use Agent in interactive mode."""
    try:
        agent = CUAAgent()
        
        console.print(Panel(
            "[bold blue]Computer Use Agent - Interactive Mode[/bold blue]\n"
            "Enter goals and the agent will help you achieve them using desktop automation.",
            title="Welcome"
        ))
        
        while True:
            goal = Prompt.ask("\n[bold]Enter your goal[/bold] (or 'quit' to exit)")
            
            if goal.lower() in ['quit', 'exit', 'q']:
                break
            
            if not goal.strip():
                continue
            
            success = agent.run_goal_loop(goal)
            
            if success:
                console.print("[bold green]✓ Goal completed![/bold green]")
            else:
                console.print("[bold yellow]Goal not fully completed[/bold yellow]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
