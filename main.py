#!/usr/bin/env python3
"""
Desktop Task Analyzer CLI

Monitors the user's desktop for 5 seconds and uses Groq API to suggest 
3 potential tasks the user might be trying to complete.
"""

import argparse
import json
import time
import sys
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

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


@dataclass
class TaskSuggestion:
    """Represents a task suggestion from the AI analysis."""
    title: str
    description: str
    confidence: float
    reasoning: str


class GroqAPIClient:
    """Client for interacting with Groq API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("Groq API key not provided. Set GROQ_API_KEY environment variable.")
        
        # Initialize OpenAI client with Groq endpoint
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1"
        )
    
    def analyze_desktop_state(self, desktop_data: Dict[str, Any]) -> List[TaskSuggestion]:
        """
        Analyze desktop state and return task suggestions.
        
        Args:
            desktop_data: Desktop state data from ax_inspect
            
        Returns:
            List of TaskSuggestion objects
        """
        # Prepare a concise summary of the desktop state for the AI
        summary = self._create_desktop_summary(desktop_data)
        
        # Create the prompt for task analysis
        prompt = f"""
You are an AI assistant that analyzes desktop activity to understand what tasks a user might be working on.

Based on the following desktop state information, suggest 3 potential tasks the user might be trying to complete. Consider:
- Active applications and their windows
- Window titles and content
- File names visible on desktop
- Application focus and z-order
- Recent activity patterns
- **IMPORTANT**: If "Currently Typing" is shown, this indicates the user is actively typing in a text field - this is a strong signal of their current task

Desktop State Summary:
{summary}

Please provide exactly 3 task suggestions in the following JSON format:
{{
    "tasks": [
        {{
            "title": "Brief task title",
            "description": "Detailed description of what the user might be trying to accomplish",
            "confidence": 0.85,
            "reasoning": "Explanation of why this task is likely based on the desktop state"
        }}
    ]
}}

Focus on actionable, specific tasks rather than generic activities. Consider the context of applications, files, and window titles.
"""

        try:
            # Make API call to Groq
            response = self._make_groq_request(prompt)
            
            # Parse the response
            tasks = self._parse_task_response(response)
            
            return tasks
            
        except Exception as e:
            print(f"Error analyzing desktop state: {e}", file=sys.stderr)
            # Return fallback suggestions
            return self._get_fallback_suggestions(desktop_data)
    
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
        
        # Visible windows
        windows = desktop_data.get('windows', [])
        visible_windows = [w for w in windows if w.get('z_index', 0) > 0 and w.get('owner') not in ['Window Server', 'Dock', 'Control Centre']]
        
        if visible_windows:
            window_info = []
            for window in visible_windows[:5]:  # Limit to top 5 windows
                name = window.get('name', 'Untitled')
                owner = window.get('owner', 'Unknown')
                if name and name != 'Untitled':
                    window_info.append(f"{owner}: {name}")
                else:
                    window_info.append(owner)
            summary_parts.append(f"Visible Windows: {', '.join(window_info)}")
        
        # Desktop files (from Finder window)
        desktop_files = []
        for window in windows:
            if window.get('owner') == 'Finder' and 'ax_tree' in window:
                ax_tree = window['ax_tree']
                if 'children' in ax_tree:
                    for child in ax_tree['children']:
                        if child.get('role') == 'AXScrollArea' and 'children' in child:
                            for desktop_item in child['children']:
                                if desktop_item.get('role') == 'AXGroup' and 'children' in desktop_item:
                                    for file_item in desktop_item['children']:
                                        if file_item.get('role') == 'AXImage':
                                            title = file_item.get('title', '')
                                            if title:
                                                desktop_files.append(title)
        
        if desktop_files:
            summary_parts.append(f"Desktop Files: {', '.join(desktop_files[:10])}")  # Limit to 10 files
        
        # Add focused text content if available
        focused_text = desktop_data.get('meta', {}).get('focused_text_content')
        if focused_text:
            # Truncate long text to avoid overwhelming the AI
            truncated_text = focused_text[:200] + "..." if len(focused_text) > 200 else focused_text
            summary_parts.append(f"Currently Typing: \"{truncated_text}\"")
        
        return '\n'.join(summary_parts) if summary_parts else "No significant desktop activity detected"
    
    def _make_groq_request(self, prompt: str) -> str:
        """Make a request to Groq API using OpenAI client."""
        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"Groq API request failed: {e}")
    
    def _parse_task_response(self, response: str) -> List[TaskSuggestion]:
        """Parse the AI response and extract task suggestions."""
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                
                tasks = []
                for task_data in data.get('tasks', []):
                    tasks.append(TaskSuggestion(
                        title=task_data.get('title', 'Unknown Task'),
                        description=task_data.get('description', 'No description'),
                        confidence=float(task_data.get('confidence', 0.5)),
                        reasoning=task_data.get('reasoning', 'No reasoning provided')
                    ))
                
                return tasks
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            print(f"Error parsing AI response: {e}", file=sys.stderr)
            return self._get_fallback_suggestions({})
    
    def _get_fallback_suggestions(self, desktop_data: Dict[str, Any]) -> List[TaskSuggestion]:
        """Provide fallback suggestions when AI analysis fails."""
        suggestions = [
            TaskSuggestion(
                title="File Organization",
                description="Organize files on desktop or in Finder windows",
                confidence=0.6,
                reasoning="Multiple files visible on desktop suggest organization work"
            ),
            TaskSuggestion(
                title="Application Management",
                description="Switch between or manage multiple open applications",
                confidence=0.5,
                reasoning="Multiple applications are currently running"
            ),
            TaskSuggestion(
                title="Information Gathering",
                description="Research or gather information using web browser or applications",
                confidence=0.4,
                reasoning="Web browser and multiple applications suggest information gathering"
            )
        ]
        
        return suggestions


class DesktopTaskAnalyzer:
    """Main class for desktop task analysis."""
    
    def __init__(self, groq_api_key: Optional[str] = None):
        self.groq_client = GroqAPIClient(groq_api_key)
    
    def analyze_desktop(self, duration: int = 5, max_depth: int = 2, max_children: int = 40, include_helpers: bool = False) -> List[TaskSuggestion]:
        """
        Monitor desktop for specified duration and analyze potential tasks.
        
        Args:
            duration: Duration to monitor desktop (seconds)
            max_depth: Maximum depth for AX tree traversal
            max_children: Maximum children per node
            
        Returns:
            List of TaskSuggestion objects
        """
        print(f"🔍 Monitoring desktop for {duration} seconds...")
        
        # Collect initial desktop state
        initial_state = collect_state(
            max_depth=max_depth,
            max_children=max_children,
            include_menubar=False,
            include_dock=False,
            include_helpers=include_helpers
        )
        
        # Wait for specified duration
        time.sleep(duration)
        
        # Collect final desktop state
        final_state = collect_state(
            max_depth=max_depth,
            max_children=max_children,
            include_menubar=False,
            include_dock=False,
            include_helpers=include_helpers
        )
        
        print("📊 Analyzing desktop activity...")
        
        # Use the final state for analysis (most current)
        tasks = self.groq_client.analyze_desktop_state(final_state)
        
        return tasks
    
    def monitor_continuously(self, interval: int = 5, max_depth: int = 2, max_children: int = 40, no_pygui_delay: bool = False, include_helpers: bool = False):
        """
        Continuously monitor desktop every N seconds and provide task suggestions.
        
        Args:
            interval: Interval between monitoring cycles (seconds)
            max_depth: Maximum depth for AX tree traversal
            max_children: Maximum children per node
            no_pygui_delay: Skip additional delay to prevent PyGUI conflicts
        """
        print(f"🔄 Starting continuous desktop monitoring (every {interval} seconds)")
        print("Press Ctrl+C to stop monitoring")
        print("="*60)
        
        cycle_count = 0
        
        try:
            while True:
                cycle_count += 1
                print(f"\n⏰ Cycle {cycle_count} - {time.strftime('%H:%M:%S')}")
                
                # Collect desktop state
                desktop_state = collect_state(
                    max_depth=max_depth,
                    max_children=max_children,
                    include_menubar=False,
                    include_dock=False,
                    include_helpers=include_helpers
                )
                
                # Analyze and get suggestions
                tasks = self.groq_client.analyze_desktop_state(desktop_state)
                
                # Print results
                self.print_results(tasks)
                
                # Clean up Foundation resources to prevent accumulation
                cleanup_foundation_resources()
                
                # Wait for next cycle
                print(f"\n⏳ Waiting {interval} seconds until next analysis...")
                time.sleep(interval)
                
                # Additional delay to prevent PyGUI conflicts (unless disabled)
                if not no_pygui_delay:
                    time.sleep(2.0)  # Increased delay
                    
                # Force process cleanup to prevent PyGUI conflicts
                try:
                    import os
                    # Clear any cached process info
                    os.system('sync')  # Force disk sync
                except:
                    pass
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️  Stopped monitoring after {cycle_count} cycles")
            print("Thanks for using Desktop Task Analyzer!")
    
    def monitor_continuously_isolated(self, interval: int = 5, max_depth: int = 2, max_children: int = 40):
        """
        Continuously monitor desktop in isolated mode to prevent PyGUI conflicts.
        Uses subprocess to isolate each monitoring cycle.
        
        Args:
            interval: Interval between monitoring cycles (seconds)
            max_depth: Maximum depth for AX tree traversal
            max_children: Maximum children per node
        """
        print(f"🔄 Starting isolated continuous monitoring (every {interval} seconds)")
        print("Press Ctrl+C to stop monitoring")
        print("="*60)
        
        cycle_count = 0
        
        try:
            while True:
                cycle_count += 1
                print(f"\n⏰ Cycle {cycle_count} - {time.strftime('%H:%M:%S')}")
                
                try:
                    # Run monitoring in a subprocess to isolate from PyGUI
                    import subprocess
                    import sys
                    
                    # Create command to run single analysis
                    cmd = [
                        sys.executable, '-c', f'''
import sys
sys.path.insert(0, ".")
from ax_inspect import collect_state
from main import DesktopTaskAnalyzer, cleanup_foundation_resources
import json

# Initialize analyzer
analyzer = DesktopTaskAnalyzer()

# Collect desktop state
desktop_state = collect_state(
    max_depth={max_depth},
    max_children={max_children},
    include_menubar=False,
    include_dock=False,
    include_helpers=False
)

# Analyze and get suggestions
tasks = analyzer.groq_client.analyze_desktop_state(desktop_state)

# Clean up
cleanup_foundation_resources()

# Output results as JSON
print(json.dumps([{{"title": t.title, "description": t.description, "confidence": t.confidence, "reasoning": t.reasoning}} for t in tasks]))
'''
                    ]
                    
                    # Run subprocess
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        # Parse results
                        import json
                        tasks_data = json.loads(result.stdout.strip())
                        tasks = [TaskSuggestion(**task) for task in tasks_data]
                        
                        # Print results
                        self.print_results(tasks)
                    else:
                        print(f"❌ Subprocess failed: {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    print("⏰ Subprocess timed out")
                except Exception as e:
                    print(f"❌ Error in cycle {cycle_count}: {e}")
                
                # Wait for next cycle
                print(f"\n⏳ Waiting {interval} seconds until next analysis...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️  Stopped monitoring after {cycle_count} cycles")
            print("Thanks for using Desktop Task Analyzer!")
    
    def print_results(self, tasks: List[TaskSuggestion]):
        """Print task suggestions in a formatted way."""
        print("\n" + "="*60)
        print("🎯 POTENTIAL TASKS YOU MIGHT BE WORKING ON")
        print("="*60)
        
        for i, task in enumerate(tasks, 1):
            print(f"\n{i}. {task.title}")
            print(f"   📝 {task.description}")
            print(f"   🎯 Confidence: {task.confidence:.1%}")
            print(f"   💭 Reasoning: {task.reasoning}")
        
        print("\n" + "="*60)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze desktop activity and suggest potential tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Monitor for 5 seconds with default settings
  python main.py --duration 10      # Monitor for 10 seconds
  python main.py --continuous        # Run continuous monitoring every 5 seconds
  python main.py -c -d 10           # Run continuous monitoring every 10 seconds (safer)
  python main.py --continuous --isolated  # Use isolated mode to prevent PyGUI conflicts
  python main.py --include-helpers   # Include helper apps (Grammarly, ChatGPT Helper, etc.)
  python main.py --api-key YOUR_KEY # Use specific API key
  
Environment Variables:
  GROQ_API_KEY                      # Groq API key (required)
        """
    )
    
    parser.add_argument(
        '--duration', '-d',
        type=int,
        default=5,
        help='Duration to monitor desktop in seconds (default: 5)'
    )
    
    parser.add_argument(
        '--api-key', '-k',
        type=str,
        help='Groq API key (default: from GROQ_API_KEY env var)'
    )
    
    parser.add_argument(
        '--max-depth',
        type=int,
        default=4,
        help='Maximum depth for AX tree traversal (default: 2)'
    )
    
    parser.add_argument(
        '--max-children',
        type=int,
        default=100,
        help='Maximum children per node (default: 40)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--continuous', '-c',
        action='store_true',
        help='Run continuous monitoring every N seconds (default: 5)'
    )
    
    parser.add_argument(
        '--no-pygui-delay',
        action='store_true',
        help='Skip additional delay to prevent PyGUI conflicts (may cause rocket bouncing)'
    )
    
    parser.add_argument(
        '--isolated',
        action='store_true',
        help='Run monitoring in isolated mode to prevent PyGUI conflicts'
    )
    
    parser.add_argument(
        '--include-helpers',
        action='store_true',
        help='Include helper apps (Grammarly, ChatGPT Helper, etc.) in analysis'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize analyzer
        analyzer = DesktopTaskAnalyzer(args.api_key)
        
        # Apply safe mode settings if requested
        max_depth = args.max_depth
        max_children = args.max_children
        
        if args.continuous:
            if args.isolated:
                # Run in isolated mode to prevent PyGUI conflicts
                print("🛡️  Running in isolated mode to prevent PyGUI conflicts")
                analyzer.monitor_continuously_isolated(
                    interval=args.duration,
                    max_depth=max_depth,
                    max_children=max_children
                )
            else:
                # Run continuous monitoring
                analyzer.monitor_continuously(
                    interval=args.duration,
                    max_depth=max_depth,
                    max_children=max_children,
                    no_pygui_delay=args.no_pygui_delay,
                    include_helpers=args.include_helpers
                )
        else:
            # Analyze desktop once
            tasks = analyzer.analyze_desktop(
                duration=args.duration,
                max_depth=max_depth,
                max_children=max_children,
                include_helpers=args.include_helpers
            )
            
            # Print results
            analyzer.print_results(tasks)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Analysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
