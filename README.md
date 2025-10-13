# Coworker - AI Productivity Assistant

> Your expert AI assistant for knowledge work. Like Cursor for your entire desktop.

Coworker is an intelligent AI agent that monitors your desktop activity, understands your workflow, and proactively suggests high-impact actions to save you time and boost productivity.

**🖥️ Cross-Platform Support:** Windows ✅ | macOS ✅ | Linux (experimental)

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your OpenAI API key
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# 3. Run once to test
python agent.py once

# 4. Use triggered mode (press Ctrl+G on Windows, Cmd+G on macOS)
python agent.py triggered
```

**First time?** Grant accessibility permissions on macOS: `python check_permissions.py --open-settings`

## Features

- **🔍 Intelligent Desktop Observation**: Captures full desktop context using locator-based window detection
  - **Windows**: UI Automation API - Full support ✅
  - **macOS**: Accessibility API - Full support ✅
  - **Linux**: AT-SPI - Experimental
  - Extracts accessibility trees, captures screenshots, performs OCR
- **🤖 GPT-4o Powered Analysis**: Advanced AI reasoning to predict goals and recommend actions
- **📸 OCR Support**: Extracts text from screen content (2000+ chars typical)
- **🧠 Memory & Learning**: Remembers your preferences, goals, and task history
- **⚡ Three Modes**:
  - **Continuous**: Auto-monitor every 30s
  - **Triggered**: On-demand with hotkey (Ctrl+G / Cmd+G)
  - **Once**: Single analysis and exit
- **🎯 High-Impact Recommendations**: 3 contextual, actionable suggestions with clear reasoning
- **💾 Context Management**: Automatic summarization to prevent context overflow (128K tokens)

## Installation

### 1. Install Python Dependencies

```bash
cd coworker
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root with your OpenAI API key:

```bash
OPENAI_API_KEY=your-api-key-here
```

**⚠️ Security Note**: Never commit `.env` to version control. It's already in `.gitignore`.

### 3. Platform-Specific Setup

#### Windows 🪟

**No special permissions required!** Windows UI Automation API works out of the box.

**Optional**: To inspect UI elements for debugging, install:
- [Accessibility Insights for Windows](https://accessibilityinsights.io/downloads/) - Recommended
- [Inspect.exe](https://learn.microsoft.com/en-us/windows/win32/winauto/inspect-objects) - Comes with Windows SDK

#### macOS 🍎

You **MUST** grant accessibility permissions for the agent to work.

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

**Windows:**
```powershell
.\venv\Scripts\activate
python agent.py continuous
# or simply
python agent.py
```

**macOS/Linux:**
```bash
source venv/bin/activate
python agent.py continuous
# or simply
python agent.py
```

### Triggered Mode (Recommended for First Use)

Wait for hotkey to trigger analysis on-demand:

**Windows:**
```powershell
.\venv\Scripts\activate
python agent.py triggered
```
Press **Ctrl+G** anytime to analyze your current desktop state and get recommendations.

**macOS/Linux:**
```bash
source venv/bin/activate
python agent.py triggered
```
Press **Cmd+G** anytime to analyze your current desktop state and get recommendations.

**Note**: Make sure you have a window focused (browser, editor, etc.) when pressing the hotkey.

### One-Time Analysis

Run a single analysis and exit (interactive mode):

**Windows:**
```powershell
.\venv\Scripts\activate
python agent.py once
```

**macOS/Linux:**
```bash
source venv/bin/activate
python agent.py once
```

## How It Works

1. **Observe**: Captures current desktop state using platform-specific APIs
   - Uses `desktop.locator("role:Window")` to find focused windows
   - Extracts accessibility tree via `get_all_applications_tree()`
   - Captures screenshots and performs OCR on visible content
   - Works reliably on both Windows and macOS
2. **Analyze**: GPT-4o analyzes the context using memory of past actions and preferences
3. **Recommend**: Generates 3 high-impact action suggestions with clear reasoning
4. **Execute**: You choose an action, and Coworker executes it automatically
5. **Learn**: Saves results to memory for future improvement

## Example Workflow

**Real example from testing:**

```
===============================================================================
                          COWORKER AI AGENT
              Your Expert Productivity Assistant
===============================================================================

Initializing Coworker AI Agent on Windows...
[OK] Using Windows UI Automation API
[OK] All components initialized

================================================================================
OBSERVING DESKTOP STATE
================================================================================
[Observer] Current window: tutorial https://github.com/mediar-ai/terminator...
[Observer] Got window tree via locator: 3 children
[Observer] Captured screenshot
[Observer] OCR extracted: 2363 chars

Observation took: 36.08s

================================================================================
Desktop State
================================================================================
Focused App: Visual Studio Code
Focused Window: tutorial https://github.com/mediar-ai/terminator/tree/main...

Accessibility Tree:
--------------------------------------------------------------------------------
Focused Window: tutorial https://github.com/mediar-ai/terminator...
  Pane: None
  Pane: None
  Pane: tutorial https://github.com/mediar-ai/terminator...

OCR Text (Visible Content):
--------------------------------------------------------------------------------
O terminator/docs/mcp-tools at main X
O mediar-ai/terminator: AI-powered X
Q tutorial https://github.com/mediar-ai/terminator/tree/main
Bing Q tutorial https://github.com/mediar-ai/terminator/tree/main
ALL SEARCH IMAGES VIDEOS MAPS NEWS
GitHub - mediar-ai/terminator: Parse your desktop like...
[... 2,363 chars total]

================================================================================
LLM ANALYSIS (Streaming)
================================================================================
Predicted Goal: "The user is researching and setting up a desktop automation
SDK using the Terminator library on GitHub."

Context Summary: "The user is viewing the Terminator library documentation on
GitHub in Microsoft Edge and has Visual Studio Code open, likely for setting
up or analyzing the code from the repository."

RECOMMENDATIONS
================================================================================

🔴 [1] Clone the Terminator repository to local machine
   Impact: HIGH
   Description: Clone the repository to your local machine to facilitate code
   exploration and potential modifications or testing.
   Reasoning: Cloning the repository locally allows you to explore the codebase
   in detail, make changes, and test functionality directly within VS Code.

🟡 [2] Open Terminator README in Visual Studio Code
   Impact: MEDIUM
   Description: Open the README.md file from the cloned repository to understand
   the setup and usage instructions.

🟢 [3] Bookmark the Terminator GitHub page
   Impact: LOW
   Description: Add the GitHub page to your bookmarks for easy access.

SELECT ACTION
================================================================================
Choose an action to execute (or 0 to skip):
  1 - Clone the Terminator repository to local machine
  2 - Open Terminator README in Visual Studio Code
  3 - Bookmark the Terminator GitHub page
  0 - Skip / Do nothing

Enter your choice (0-3):
```

**Notice**: The AI perfectly understood that I was viewing the Terminator GitHub repo and suggested highly contextual actions!

## Configuration

Edit `config.py` to customize:

- **Model**: Change to `o1-preview`, `o1-mini`, or other models
- **Observation interval** for continuous mode (default: 30s)
- **Max context tokens** (currently 128,000 for GPT-4o)
- **OCR settings** (enable/disable)
- **Action timeout** (default: 30s)
- **Hotkey combination** (auto-detected: Ctrl+G on Windows, Cmd+G on macOS)

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

### Observation Not Working (Empty Tree/OCR)

**Symptoms**: Accessibility tree is empty, no OCR text captured

✅ **Fixed in latest version!** The desktop observer now uses a locator-based approach that works on both Windows and macOS.

**To verify it's working**, look for these debug messages:
```
[Observer] Got window tree via locator: X children
[Observer] Captured screenshot
[Observer] OCR extracted: X chars
```

If you still see issues:
1. Update Terminator: `pip install --upgrade terminator`
2. Check you have the latest code from [desktop_observer.py](desktop_observer.py)
3. See [MACOS_WINDOWS_FIX.md](MACOS_WINDOWS_FIX.md) for technical details

### Windows-Specific Issues

#### "Could not get window" errors
- Ensure the target application is running and has focus
- Some UWP apps may have limited UI Automation support
- Try running as administrator for system-level apps

#### Hotkey not working
- Check that no other application is using Ctrl+G
- Verify pynput is installed: `pip install pynput`
- Some security software may block global hotkeys

#### Slow observation (>60s)
- Normal: First run scans all apps (~30-40s)
- If consistently slow, consider using "triggered" mode instead of "continuous"

### macOS-Specific Issues

#### "Accessibility permissions not granted"
- Go to System Preferences → Security & Privacy → Privacy → Accessibility
- Add and enable your terminal app
- **Restart terminal** after granting permissions (critical!)

#### Hotkey not responding
- Verify Cmd+G is not used by another app
- Check that pynput has proper permissions
- Try running: `python -c "from pynput import keyboard; print('OK')"`

#### Observation hangs or times out
- Check Accessibility permissions are properly granted
- Try closing some apps to reduce observation scope
- Use "once" mode for testing: `python agent.py once`

### Cross-Platform Issues

#### "OPENAI_API_KEY not set"
- Check that `.env` file exists in the coworker directory
- Verify the API key is valid and has credits
- Format: `OPENAI_API_KEY=sk-...`

#### OCR not working
- Ensure Pillow is installed: `pip install Pillow`
- Check debug output shows: `[Observer] Captured screenshot`
- OCR requires screenshot capture to work

#### Terminator library errors
- Update terminator: `pip install --upgrade terminator`
- Check platform support in [Terminator docs](https://github.com/mediar-ai/terminator)
- Try: `python -c "import terminator; print('OK')"`

#### "JSON serializable" errors
- Update to latest code - this was fixed in the locator-based rewrite
- The issue was with tree data format handling

## Architecture

```
agent.py              # Main orchestrator (async event loop)
├── desktop_observer  # Desktop state capture (locator-based)
│   ├── _observe_windows()      # Windows UI Automation
│   └── _observe_macos_linux()  # macOS Accessibility API
├── llm_client        # GPT-4o API with streaming responses
├── memory            # Context & preference management (128K tokens)
├── action_executor   # Executes actions via Terminator
└── hotkey_listener   # Global hotkey detection (platform-aware)

Key Technologies:
- Terminator: Desktop automation framework (locator-based)
- OpenAI GPT-4o: Language model for analysis
- Platform APIs: UI Automation (Windows), Accessibility (macOS)
```

## Recent Updates

### v2.0 - Cross-Platform Desktop Observation Fix (Latest)

✅ **Complete rewrite of desktop observation** to fix empty accessibility trees and OCR on both Windows and macOS:

- **New locator-based approach**: Uses `desktop.locator("role:Window")` instead of `focused_element().window()`
- **Works on both platforms**: Windows and macOS now both capture full context
- **Better fallbacks**: Multi-layer fallback strategy ensures observation always succeeds
- **JSON tree handling**: Properly handles `get_all_applications_tree()` response format
- **Performance**: ~35s observation time with full context capture

See [MACOS_WINDOWS_FIX.md](MACOS_WINDOWS_FIX.md) for technical details.

### v1.0 - Windows Support Added

✅ Platform detection, Windows hotkey (Ctrl+G), console encoding fixes

## Contributing

This is a personal productivity tool. Feel free to fork and customize for your needs!

## License

MIT

## Credits

Built using:
- [Terminator](https://github.com/mediar-ai/terminator) - Cross-platform desktop automation framework
- OpenAI GPT-4o - Language model
- Platform accessibility APIs (Windows UI Automation, macOS Accessibility, Linux AT-SPI)

---

**Made with ❤️ for knowledge workers who want to be more productive**
