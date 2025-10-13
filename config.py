"""Configuration settings for Coworker AI Agent"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Memory file paths
TASK_HISTORY_FILE = DATA_DIR / "task_history.jsonl"
PREFERENCES_FILE = DATA_DIR / "preferences.json"
GOALS_FILE = DATA_DIR / "goals.json"
CONTEXT_SUMMARIES_FILE = DATA_DIR / "context_summaries.jsonl"

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o"  # Latest GPT-4o model (128k context)
OPENAI_REASONING_EFFORT = "low"  # Note: reasoning_effort only works with o1 models
OPENAI_MAX_TOKENS = 4000  # Max tokens for response
OPENAI_TEMPERATURE = 0.7

# Validate critical settings
if not OPENAI_API_KEY:
    import sys
    print("ERROR: OPENAI_API_KEY not set in .env file")
    print("Please add your OpenAI API key to the .env file")
    sys.exit(1)

# Context management
MAX_CONTEXT_TOKENS = 128000  # GPT-4o max context length
SUMMARIZE_THRESHOLD = 0.8  # Summarize when 80% full (~100k tokens)
MAX_HISTORY_ITEMS = 50  # Max items to keep in context before summarizing

# Agent settings
CONTINUOUS_MODE_INTERVAL = 30  # seconds between observations in continuous mode
OBSERVATION_DEPTH = 3  # How deep to traverse accessibility tree
HOTKEY = "cmd+g"  # Hotkey for triggered mode

# Action settings
ACTION_CONFIRMATION_REQUIRED = True
ACTION_TIMEOUT = 30  # seconds

# Desktop observation settings
CAPTURE_SCREENSHOTS = True
USE_OCR = True
FOCUS_WINDOW_ONLY = True

# Logging settings
LOG_LEVEL = "INFO"
LOG_TO_FILE = True
LOG_FILE = DATA_DIR / "coworker.log"

# Terminal UI settings
TERMINAL_WIDTH = 120
SHOW_TIMESTAMPS = True
STREAM_OUTPUT = True
