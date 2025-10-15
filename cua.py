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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
    
    def capture_desktop_state(self) -> Dict[str, Any]:
        """Capture current desktop state."""
        return collect_state(
            max_depth=4,
            max_children=100,
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
            # Use reduced parameters for safety
            state = collect_state(
                max_depth=2,  # Reduced depth
                max_children=50,  # Reduced children
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
                        -- Strategy 1: Try description first
                        set targetElement to first UI element whose role is "{element_role}" and description contains "{element_description}"
                        click targetElement
                        return "success"
                    on error
                        try
                            -- Strategy 2: Try title
                            set targetElement to first UI element whose role is "{element_role}" and name contains "{element_title}"
                            click targetElement
                            return "success"
                        on error
                            try
                                -- Strategy 3: Try just role (less specific)
                                set targetElement to first UI element whose role is "{element_role}"
                                click targetElement
                                return "success"
                            on error
                                try
                                    -- Strategy 4: Try description without role
                                    set targetElement to first UI element whose description contains "{element_description}"
                                    click targetElement
                                    return "success"
                                on error
                                    return "Element not found"
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
        
        # Create a simple assessment prompt
        summary = self._create_desktop_summary(current_state)
        
        prompt = f"""
GOAL: {goal}

CURRENT DESKTOP STATE:
{summary}

EXECUTED ACTIONS: {len(self.executed_actions)}

Assess the progress towards the goal on a scale of 0.0 to 1.0, where:
- 0.0 = No progress made
- 0.5 = Some progress, but goal not achieved
- 1.0 = Goal completely achieved

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
                    # Execute action with timeout protection
                    success = self.execute_action(step)
                    if not success:
                        console.print(f"[red]Failed to execute step {i+1}[/red]")
                        continue
                    
                    # Small delay between actions
                    time.sleep(0.5)
                    
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
