# Coworker - AI Productivity Assistant

> Your expert AI assistant for knowledge work. Like Cursor for your entire desktop.

Coworker is an intelligent AI agent that monitors your desktop activity, understands your workflow, and proactively suggests high-impact actions to save you time and boost productivity.

## Features

- **🔍 Intelligent Desktop Observation**: Monitors focused windows via macOS Accessibility APIs
- **🤖 GPT-4o Powered Analysis**: Advanced AI reasoning to predict goals and recommend actions
- **📸 OCR Support**: Extracts text from screen content for better understanding
- **🧠 Memory & Learning**: Remembers your preferences, goals, and task history
- **⚡ Two Modes**: Continuous monitoring or triggered on-demand (CMD+G)
- **🎯 High-Impact Recommendations**: 3 actionable suggestions with clear reasoning
- **💾 Context Management**: Automatic summarization to prevent context overflow

## Installation

### 1. Install Python Dependencies

```bash
cd coworker
pip install -r requirements.txt
```

### 2. Configure Environment

The `.env` file is already configured with your OpenAI API key.

### 3. Grant Accessibility Permissions ⚠️ IMPORTANT

On macOS, you **MUST** grant accessibility permissions for the agent to work.

**Quick Setup** - Run the permission checker:

```bash
python check_permissions.py --open-settings
```

This will:
- ✅ Check if permissions are granted
- 🔓 Open System Settings to the Accessibility panel automatically
- 📋 Guide you through the setup process

**Manual Setup** (if needed):

1. Open **System Settings** → **Privacy & Security** → **Accessibility**
2. Click the **+** button or unlock to make changes
3. Add your terminal app:
   - **Terminal.app** (if using default Terminal)
   - **iTerm.app** (if using iTerm2)
   - **Warp** (if using Warp)
4. Toggle the switch to **ON**
5. **Restart your terminal** after granting permissions

**Note**: macOS does NOT allow programmatic granting of accessibility permissions for security reasons. The script can only open System Settings - you must manually approve the permission.

## Usage

### Continuous Mode (Default)

Monitors your desktop continuously with automatic observations:

```bash
source venv/bin/activate
python agent.py continuous
# or simply
python agent.py
```

### Triggered Mode (Recommended for First Use)

Wait for CMD+G hotkey to trigger analysis on-demand:

```bash
source venv/bin/activate
python agent.py triggered
```

Press **CMD+G** anytime to analyze your current desktop state and get recommendations.

**Note**: Make sure you have a window focused (browser, editor, etc.) when pressing CMD+G.

### One-Time Analysis

Run a single analysis and exit (interactive mode):

```bash
source venv/bin/activate
python agent.py once
```

## How It Works

1. **Observe**: Captures current desktop state (focused window, accessibility tree, OCR text)
2. **Analyze**: GPT-5 analyzes the context using memory of past actions and preferences
3. **Recommend**: Generates 3 high-impact action suggestions with clear reasoning
4. **Execute**: You choose an action, and Coworker executes it automatically
5. **Learn**: Saves results to memory for future improvement

## Example Workflow

```
╔═══════════════════════════════════════════════════════════════╗
║                    COWORKER AI AGENT                          ║
║          Your Expert Productivity Assistant                   ║
╚═══════════════════════════════════════════════════════════════╝

OBSERVING DESKTOP STATE
================================================================================
Focused App: Safari
Focused Window: GitHub - Project Repository

[Accessibility tree and OCR text displayed...]

LLM ANALYSIS (Streaming)
================================================================================
{
  "predicted_goal": "Review pull request and provide feedback",
  "recommendations": [
    {
      "id": 1,
      "title": "Extract PR changes into Notes",
      "description": "Copy PR diff to notes for detailed review",
      "impact": "high",
      ...
    }
  ]
}

SELECT ACTION
================================================================================
Choose an action to execute (or 0 to skip):
  1 - Extract PR changes into Notes
  2 - Open related Jira ticket
  3 - Schedule code review meeting
  0 - Skip / Do nothing

Enter your choice (0-3): 1

EXECUTING ACTION: Extract PR changes into Notes
================================================================================
✓ Result: Extracted PR diff and created new note

```

## Configuration

Edit `config.py` to customize:

- **Model**: Change to `o1-preview`, `o1-mini`, or other models
- **Observation interval** for continuous mode (default: 30s)
- **Max context tokens** (currently 128,000 for GPT-4o)
- **OCR settings** (enable/disable)
- **Action timeout** (default: 30s)
- **Hotkey combination** (default: cmd+g)

## Memory & Context

Coworker maintains:

- **Task History** (`data/task_history.jsonl`): Your past actions and results
- **Preferences** (`data/preferences.json`): Learned app preferences and workflow patterns
- **Goals** (`data/goals.json`): Predicted and completed goals
- **Context Summaries** (`data/context_summaries.jsonl`): Automatic summaries when context gets large

Memory is automatically managed and summarized when approaching the 128K token limit.

## Supported Actions

- `click` - Click UI elements by selector
- `type` - Type text into focused fields
- `press_key` - Press keyboard shortcuts
- `open_application` - Launch applications
- `open_url` - Open URLs in browser
- `execute_script` - Run JavaScript in browser
- `composite` - Multi-step actions

## Use Cases

Perfect for knowledge workers who:

- Manage emails (Gmail, Outlook, Apple Mail)
- Schedule meetings (Google Calendar, Outlook)
- Research and browse (Safari, Chrome, Firefox)
- Take notes (Notion, Obsidian, Apple Notes)
- Communicate (Slack, Discord, Teams)
- Write documents (Google Docs, Word, VS Code)

## Troubleshooting

### "Accessibility permissions not granted"
- Go to System Preferences → Security & Privacy → Privacy → Accessibility
- Add and enable your terminal app

### "OPENAI_API_KEY not set"
- Check that `.env` file exists in the coworker directory
- Verify the API key is valid

### OCR not working
- Ensure Pillow is installed: `pip install Pillow`
- Check that screenshots are being captured (debug output)

### Hotkey not responding
- Verify the hotkey combination in `config.py`
- Check that pynput has proper permissions

## Architecture

```
agent.py              # Main orchestrator
├── desktop_observer  # Captures desktop state + OCR
├── llm_client        # GPT-5 API with streaming
├── memory            # Context & preference management
├── action_executor   # Executes actions via terminator
└── hotkey_listener   # Global hotkey detection
```

## Contributing

This is a personal productivity tool. Feel free to fork and customize for your needs!

## License

MIT

## Credits

Built using:
- [Terminator](https://github.com/mediar-ai/terminator) - Desktop automation framework
- OpenAI GPT-5 - Language model
- macOS Accessibility APIs

---

**Made with ❤️ for knowledge workers who want to be more productive**
