# Computer Use Agent (CUA)

A sophisticated goal-driven desktop automation agent that uses GPT-OSS-120B via Groq API for multi-step reasoning and planning on macOS.

## 🚀 Features

- **Goal-driven automation**: Specify what you want to achieve, not how to do it
- **Multi-step reasoning**: Uses GPT-OSS-120B for complex task planning
- **Real-time observation**: Monitors desktop changes and adapts plans
- **macOS integration**: Leverages Accessibility APIs for precise control
- **Rich CLI interface**: Beautiful terminal interface with progress tracking
- **Crash prevention**: Safe observation mode to prevent Python rocket crashes

## 📋 Prerequisites

- macOS 10.14 or later
- Python 3.8+
- Groq API key
- Accessibility permissions for Terminal/Python

## 🛠 Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd cue
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**
```bash
export GROQ_API_KEY="your_groq_api_key_here"
```

4. **Grant accessibility permissions:**
   - Go to System Preferences > Security & Privacy > Privacy > Accessibility
   - Add Terminal (or your Python interpreter) to the list
   - Enable the checkbox

## 🎯 Usage

### Interactive Mode
```bash
python cua.py interactive
```

### Single Goal Mode
```bash
python cua.py run "Open Safari and navigate to GitHub"
```

### Advanced Options
```bash
# Skip observation to prevent crashes
python cua.py run "Create a new document in Pages" --skip-observation

# Limit iterations
python cua.py run "Open Safari and navigate to GitHub" --max-iterations 5

# Use custom API key
python cua.py run "Focus Safari and click address bar" --api-key "your_key"
```

## 🔧 How It Works

```
User Goal → Desktop Capture → AI Planning → Action Execution → Observation → Iteration
```

1. **Goal Input**: User specifies what they want to achieve
2. **Desktop Capture**: Agent captures current desktop state using Accessibility APIs
3. **AI Planning**: GPT-OSS-120B creates a multi-step execution plan
4. **Action Execution**: Agent executes actions (clicks, typing, etc.)
5. **Observation**: Agent observes changes and assesses progress
6. **Iteration**: Repeats until goal is achieved or max iterations reached

## 🎮 Supported Actions

- **click**: Click on UI elements using coordinates
- **click_element**: Click on UI elements using accessibility properties
- **type**: Type text into focused fields
- **scroll**: Scroll in windows or areas
- **drag**: Drag elements from one location to another
- **key_combo**: Execute keyboard shortcuts (e.g., Cmd+C, Cmd+V)
- **press_key**: Press a single key (e.g., return, enter, space, tab)
- **wait**: Wait for a specified duration
- **focus_window**: Focus on a specific window
- **open_app**: Launch applications
- **search**: Perform searches

## 📝 Examples

### Web Browsing
```bash
python cua.py run "Open Safari, go to GitHub, and search for 'python automation'"
```

### Document Creation
```bash
python cua.py run "Open Pages and create a new document titled 'Meeting Notes'"
```

### File Management
```bash
python cua.py run "Open Finder, navigate to Documents, and create a new folder called 'Projects'"
```

### Safe Mode (No Observation)
```bash
python cua.py run "Focus Safari and click address bar" --skip-observation
```

## 🧪 Testing

### Test Scripts
```bash
# Test basic functionality
python test_cua.py

# Test address bar clicking
python test_safari_address.py

# Test without observation (crash prevention)
python test_no_observation.py

# Test both fixes (address bar + return key)
python test_safari_fixes.py
```

## ⚙️ Configuration

### Environment Variables
- `GROQ_API_KEY`: Your Groq API key (required)
- `CUDA_DEBUG`: Enable debug mode (optional)

### CLI Options
- `--max-iterations, -i`: Maximum number of iterations (default: 10)
- `--skip-observation, -s`: Skip observation phase to avoid crashes
- `--api-key, -k`: Override API key from environment

## 🛡 Safety Features

- **Failsafe**: Move mouse to top-left corner to abort
- **Confirmation**: Plans are shown and confirmed before execution
- **Progress Tracking**: Real-time progress assessment
- **Error Handling**: Graceful handling of execution failures
- **Timeout Protection**: Prevents hanging operations
- **Crash Prevention**: Safe observation mode

## 🐛 Troubleshooting

### Common Issues

1. **Python Rocket Crash**
   - **Solution**: Use `--skip-observation` flag
   - **Cause**: Accessibility API resource exhaustion

2. **Accessibility Permissions**
   - **Solution**: Grant Terminal accessibility permissions
   - **Location**: System Preferences > Security & Privacy > Privacy > Accessibility

3. **API Key Issues**
   - **Solution**: Set `GROQ_API_KEY` environment variable
   - **Test**: `echo $GROQ_API_KEY`

4. **Address Bar Clicking**
   - **Solution**: Use `click_element` with role "text field" and description "smart search field"
   - **Fallback**: Multiple detection strategies implemented

5. **Return Key Typing "RETUN"**
   - **Solution**: Use `press_key` action with key "return"
   - **Implementation**: Uses key code 36 instead of keystroke

### Debug Mode
```bash
export CUDA_DEBUG=1
python cua.py run "your goal"
```

## 🏗 Architecture

### Core Components
- **CUAAgent**: Main agent class
- **ActionType**: Enum of supported actions
- **Plan**: Multi-step execution plan
- **Observation**: Desktop state changes

### Key Methods
- `capture_desktop_state()`: Capture current desktop state
- `create_plan()`: Generate execution plan using AI
- `execute_action()`: Execute individual actions
- `observe_changes()`: Detect desktop changes
- `assess_goal_progress()`: Evaluate progress

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Groq for providing the GPT-OSS-120B API
- macOS Accessibility APIs for desktop automation
- Rich library for beautiful CLI interfaces
- PyObjC for macOS integration

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section
2. Try the test scripts
3. Use `--skip-observation` for stability
4. Check accessibility permissions
5. Verify API key configuration

---

**Note**: This is a prototype system. Use with caution and always test in a safe environment.

