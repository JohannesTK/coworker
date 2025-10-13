# Coworker - Quick Start Guide

Get up and running in under 2 minutes!

## Prerequisites

- macOS (currently required)
- Python 3.8+
- OpenAI API key

## Setup Steps

### 1. Clone/Download (Already Done! ✓)

You already have the coworker directory set up.

### 2. Install Dependencies

```bash
cd coworker
source venv/bin/activate
# Dependencies already installed!
```

### 3. Check Permissions

**IMPORTANT**: Run this first to check/grant accessibility permissions:

```bash
python check_permissions.py --open-settings
```

This will:
- Check if you have the required permissions
- Open System Settings if needed
- Guide you through the setup

**What to do when System Settings opens:**
1. Click the 🔒 lock icon and enter your password
2. Click the **+** button
3. Navigate to `/Applications/Utilities/Terminal.app` (or your terminal)
4. Click "Open"
5. Make sure the toggle is **ON** (blue)
6. **Quit and restart your terminal** (important!)

### 4. Run the Agent!

**Option A: Triggered Mode (Recommended First Time)**

```bash
python agent.py triggered
```

- Press **CMD+G** anytime to trigger analysis
- Make sure you have a window focused (browser, editor, etc.)

**Option B: Continuous Mode**

```bash
python agent.py continuous
```

- Automatically analyzes every 30 seconds
- Press Ctrl+C to stop

**Option C: One-Time**

```bash
python agent.py once
```

- Runs once and exits
- Good for testing

## Common Issues

### "Accessibility permissions not granted"

**Solution**: Run `python check_permissions.py --open-settings` and follow the instructions.

### "OPENAI_API_KEY not set"

**Solution**: Check that `.env` file exists in the coworker directory with your API key.

### "Element not found" errors

**Solution**:
1. Make sure you have a window focused (click on a browser/editor window)
2. Try running `python check_permissions.py` to verify permissions
3. Restart your terminal after granting permissions

### No recommendations appear

**Solution**:
1. Check that your OpenAI API key is valid
2. Ensure you have an internet connection
3. Check the terminal output for error messages

## What to Expect

When everything is working correctly:

```
================================================================================
OBSERVING DESKTOP STATE
================================================================================

⏱️  Observation took: 1.2s

Focused App: Safari
Focused Window: GitHub - coworker

[Accessibility tree shown...]

================================================================================
LLM ANALYSIS (Streaming)
================================================================================

[⏱️  First token: 0.8s] {
  "predicted_goal": "Reviewing code in GitHub repository",
  "recommendations": [...]
}

⏱️  LLM response took: 3.5s (total)

================================================================================
RECOMMENDATIONS
================================================================================

🎯 Predicted Goal: Reviewing code in GitHub repository

🔴 [1] Extract code snippet to notes
   Impact: HIGH
   ...

🟡 [2] Open related pull request
   Impact: MEDIUM
   ...

🟢 [3] Search documentation for API reference
   Impact: LOW
   ...

SELECT ACTION
================================================================================
Choose an action to execute (or 0 to skip):
  1 - Extract code snippet to notes
  2 - Open related pull request
  3 - Search documentation for API reference
  0 - Skip / Do nothing

Enter your choice (0-3):
```

## Next Steps

1. ✅ Grant accessibility permissions
2. ✅ Run the agent
3. ✅ Try pressing CMD+G in different apps
4. ✅ Watch how it learns your preferences
5. ✅ Customize `config.py` to your needs

## Getting Help

- Check `README.md` for full documentation
- Run `python check_permissions.py` to diagnose issues
- Review error messages in the terminal

Happy automating! 🤖
