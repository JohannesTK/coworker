"""Memory management for Coworker AI Agent"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import tiktoken

from config import (
    TASK_HISTORY_FILE,
    PREFERENCES_FILE,
    GOALS_FILE,
    CONTEXT_SUMMARIES_FILE,
    MAX_CONTEXT_TOKENS,
    SUMMARIZE_THRESHOLD,
    MAX_HISTORY_ITEMS,
)


class MemoryManager:
    """Manages agent memory, context, and automatic summarization"""

    def __init__(self):
        self.encoding = tiktoken.encoding_for_model("gpt-4o")
        self._ensure_files_exist()

    def _ensure_files_exist(self):
        """Create memory files if they don't exist"""
        if not TASK_HISTORY_FILE.exists():
            TASK_HISTORY_FILE.touch()

        if not PREFERENCES_FILE.exists():
            self._save_json(PREFERENCES_FILE, {
                "apps": {},
                "workflows": {},
                "time_preferences": {},
                "communication_style": "professional"
            })

        if not GOALS_FILE.exists():
            self._save_json(GOALS_FILE, {
                "current_goals": [],
                "completed_goals": [],
                "recurring_patterns": []
            })

        if not CONTEXT_SUMMARIES_FILE.exists():
            CONTEXT_SUMMARIES_FILE.touch()

    def _load_json(self, file_path: Path) -> Dict:
        """Load JSON file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_json(self, file_path: Path, data: Dict):
        """Save JSON file"""
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _append_jsonl(self, file_path: Path, data: Dict):
        """Append to JSONL file"""
        with open(file_path, 'a') as f:
            f.write(json.dumps(data) + '\n')

    def _read_jsonl(self, file_path: Path, limit: Optional[int] = None) -> List[Dict]:
        """Read JSONL file"""
        lines = []
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        lines.append(json.loads(line))

            if limit:
                return lines[-limit:]
            return lines
        except FileNotFoundError:
            return []

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))

    def add_task(self, action: Dict, result: str, predicted_goal: str):
        """Add completed task to history"""
        task = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result,
            "predicted_goal": predicted_goal
        }
        self._append_jsonl(TASK_HISTORY_FILE, task)

        # Check if summarization is needed
        self._check_and_summarize()

    def get_recent_tasks(self, limit: int = MAX_HISTORY_ITEMS) -> List[Dict]:
        """Get recent task history"""
        return self._read_jsonl(TASK_HISTORY_FILE, limit=limit)

    def format_task_history(self, limit: int = 10) -> str:
        """Format task history for prompt"""
        tasks = self.get_recent_tasks(limit)
        if not tasks:
            return "No recent tasks"

        formatted = []
        for i, task in enumerate(tasks[-limit:], 1):
            timestamp = task.get('timestamp', 'unknown')
            action_type = task.get('action', {}).get('type', 'unknown')
            result = task.get('result', 'unknown')
            goal = task.get('predicted_goal', 'unknown')

            formatted.append(
                f"{i}. [{timestamp}] {action_type} - Goal: {goal} - Result: {result}"
            )

        return "\n".join(formatted)

    def update_preferences(self, key: str, value: Any):
        """Update user preferences"""
        prefs = self._load_json(PREFERENCES_FILE)

        # Support nested keys like "apps.Safari"
        keys = key.split('.')
        current = prefs
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value
        self._save_json(PREFERENCES_FILE, prefs)

    def get_preferences(self) -> Dict:
        """Get all preferences"""
        return self._load_json(PREFERENCES_FILE)

    def format_preferences(self) -> str:
        """Format preferences for prompt"""
        prefs = self.get_preferences()
        if not prefs or all(not v for v in prefs.values()):
            return "No learned preferences yet"

        formatted = []
        for category, items in prefs.items():
            if items:
                formatted.append(f"**{category.title()}**: {json.dumps(items, indent=2)}")

        return "\n".join(formatted) if formatted else "No learned preferences yet"

    def add_goal(self, goal: str, confidence: float = 0.8):
        """Add or update predicted goal"""
        goals_data = self._load_json(GOALS_FILE)

        # Add to current goals if not already there
        current_goals = goals_data.get('current_goals', [])

        # Check if goal already exists
        existing = next((g for g in current_goals if g['goal'] == goal), None)
        if existing:
            existing['last_seen'] = datetime.now().isoformat()
            existing['confidence'] = max(existing['confidence'], confidence)
            existing['occurrences'] += 1
        else:
            current_goals.append({
                'goal': goal,
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'confidence': confidence,
                'occurrences': 1
            })

        goals_data['current_goals'] = current_goals
        self._save_json(GOALS_FILE, goals_data)

    def complete_goal(self, goal: str):
        """Mark a goal as completed"""
        goals_data = self._load_json(GOALS_FILE)
        current_goals = goals_data.get('current_goals', [])
        completed_goals = goals_data.get('completed_goals', [])

        # Find and remove from current (avoid modifying list while iterating)
        goal_to_complete = None
        for g in current_goals:
            if g['goal'] == goal:
                goal_to_complete = g
                break

        if goal_to_complete:
            goal_to_complete['completed_at'] = datetime.now().isoformat()
            completed_goals.append(goal_to_complete)
            current_goals.remove(goal_to_complete)

        goals_data['current_goals'] = current_goals
        goals_data['completed_goals'] = completed_goals
        self._save_json(GOALS_FILE, goals_data)

    def get_goals(self) -> Dict:
        """Get goals data"""
        return self._load_json(GOALS_FILE)

    def format_goals(self) -> str:
        """Format goals for prompt"""
        goals_data = self.get_goals()
        current = goals_data.get('current_goals', [])

        if not current:
            return "No active goals predicted yet"

        formatted = []
        for g in current[-5:]:  # Last 5 goals
            goal = g['goal']
            confidence = g['confidence']
            occurrences = g['occurrences']
            formatted.append(f"- {goal} (confidence: {confidence:.0%}, seen {occurrences}x)")

        return "\n".join(formatted)

    def _check_and_summarize(self):
        """Check if context needs summarization and trigger if needed"""
        # Count total tokens in context
        tasks = self.get_recent_tasks()
        prefs = self.format_preferences()
        goals = self.format_goals()

        total_text = json.dumps(tasks) + prefs + goals
        total_tokens = self.count_tokens(total_text)

        threshold_tokens = int(MAX_CONTEXT_TOKENS * SUMMARIZE_THRESHOLD)

        if total_tokens > threshold_tokens:
            print(f"\n[Memory] Context size ({total_tokens} tokens) exceeds threshold. Triggering summarization...")
            self._summarize_history()

    def _summarize_history(self):
        """Summarize old history to free up context space"""
        tasks = self.get_recent_tasks()

        if len(tasks) <= MAX_HISTORY_ITEMS:
            return

        # Take oldest half for summarization
        to_summarize = tasks[:len(tasks)//2]
        to_keep = tasks[len(tasks)//2:]

        # Create summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "period_start": to_summarize[0]['timestamp'] if to_summarize else None,
            "period_end": to_summarize[-1]['timestamp'] if to_summarize else None,
            "task_count": len(to_summarize),
            "action_types": {},
            "common_goals": [],
            "apps_used": set()
        }

        # Analyze tasks
        for task in to_summarize:
            action_type = task.get('action', {}).get('type', 'unknown')
            summary['action_types'][action_type] = summary['action_types'].get(action_type, 0) + 1

            goal = task.get('predicted_goal', '')
            if goal and goal not in summary['common_goals']:
                summary['common_goals'].append(goal)

            target = task.get('action', {}).get('target', '')
            if 'application:' in target:
                app = target.split('application:')[1].split('>>')[0].strip()
                summary['apps_used'].add(app)

        summary['apps_used'] = list(summary['apps_used'])

        # Save summary
        self._append_jsonl(CONTEXT_SUMMARIES_FILE, summary)

        # Rewrite history file with only recent tasks
        TASK_HISTORY_FILE.unlink()
        TASK_HISTORY_FILE.touch()
        for task in to_keep:
            self._append_jsonl(TASK_HISTORY_FILE, task)

        print(f"[Memory] Summarized {len(to_summarize)} tasks. Keeping {len(to_keep)} recent tasks.")

    def get_context_stats(self) -> Dict[str, int]:
        """Get current context statistics"""
        tasks = self.get_recent_tasks()
        prefs = self.format_preferences()
        goals = self.format_goals()

        total_text = json.dumps(tasks) + prefs + goals
        total_tokens = self.count_tokens(total_text)

        return {
            "total_tokens": total_tokens,
            "max_tokens": MAX_CONTEXT_TOKENS,
            "usage_percent": (total_tokens / MAX_CONTEXT_TOKENS) * 100,
            "task_count": len(tasks)
        }
