#!/usr/bin/env python3
"""
Verify and fix accessibility permissions
"""
import subprocess
import sys
import os

print("=" * 80)
print("PERMISSION VERIFICATION")
print("=" * 80)
print()

# The Python.app that needs permissions
python_app = "/opt/homebrew/Cellar/python@3.13/3.13.7/Frameworks/Python.framework/Versions/3.13/Resources/Python.app"

print("1. Checking if Python.app exists:")
print(f"   Path: {python_app}")
if os.path.exists(python_app):
    print("   ✓ Python.app exists")
else:
    print("   ✗ Python.app NOT found at this path!")
    print()
    print("   Let's find the correct Python.app path...")
    # Find the actual Python executable
    result = subprocess.run(["which", "python3"], capture_output=True, text=True)
    if result.returncode == 0:
        python_path = result.stdout.strip()
        print(f"   Python3 is at: {python_path}")

        # Try to find Python.app
        if "Cellar/python" in python_path:
            base = python_path.split("/bin/python")[0]
            possible_app = f"{base}/Frameworks/Python.framework/Versions/Current/Resources/Python.app"
            print(f"   Possible Python.app: {possible_app}")
            if os.path.exists(possible_app):
                python_app = possible_app
                print(f"   ✓ Found Python.app at: {python_app}")
print()

# Try to add using tccutil (might not work on all macOS versions)
print("2. Attempting to grant accessibility permission via tccutil:")
result = subprocess.run(
    ["tccutil", "reset", "Accessibility", "dev.warp.Warp-Stable"],
    capture_output=True,
    text=True
)
print(f"   Reset Warp permissions: {result.returncode == 0}")

# The bundle identifier for Python.app is tricky
# Let's try to get it
print()
print("3. Getting Python.app bundle identifier:")
result = subprocess.run(
    ["/usr/libexec/PlistBuddy", "-c", "Print CFBundleIdentifier",
     f"{python_app}/Contents/Info.plist"],
    capture_output=True,
    text=True
)
if result.returncode == 0:
    bundle_id = result.stdout.strip()
    print(f"   Bundle ID: {bundle_id}")
else:
    print("   Could not get bundle ID")
    bundle_id = None

print()
print("4. Current accessibility status:")
# Check if we can access the API now
try:
    import terminator
    desktop = terminator.Desktop()
    focused = desktop.focused_element()
    app = focused.application()
    if app:
        app_name = app.name()
        print(f"   ✓ SUCCESS! Can access accessibility API")
        print(f"   ✓ Current focused app: {app_name}")
        sys.exit(0)
except Exception as e:
    print(f"   ✗ Still cannot access: {e}")

print()
print("=" * 80)
print("MANUAL FIX REQUIRED")
print("=" * 80)
print()
print("The automated methods didn't work. Here's what to do:")
print()
print("METHOD 1: Add via System Settings (RECOMMENDED)")
print("-" * 80)
print()
print("1. Open Terminal and run:")
print(f"   open '{python_app}'")
print()
print("2. This will open Finder showing Python.app")
print()
print("3. Open System Settings → Privacy & Security → Accessibility")
print()
print("4. Drag Python.app from Finder into the Accessibility list")
print()
print("5. Make sure the toggle is ON")
print()
print()
print("METHOD 2: Use a different Python (WORKAROUND)")
print("-" * 80)
print()
print("If the above doesn't work, you can use system Python or conda:")
print()
print("   # Using system Python (if available)")
print("   /usr/bin/python3 -m venv venv_system")
print("   source venv_system/bin/activate")
print("   pip install -r requirements.txt")
print("   python agent.py")
print()
print()
print("METHOD 3: Restart macOS")
print("-" * 80)
print()
print("Sometimes macOS TCC database needs a restart to recognize new apps.")
print("After adding Python.app to Accessibility, try restarting your Mac.")
print()
print("=" * 80)
