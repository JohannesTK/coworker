#!/usr/bin/env python3
"""
Diagnostic script to understand accessibility permission issues
"""
import os
import sys
import subprocess

print("=" * 80)
print("PERMISSION DIAGNOSTICS")
print("=" * 80)
print()

# 1. Check what process we're running under
print("1. Current Process Information:")
print(f"   PID: {os.getpid()}")
print(f"   Parent PID: {os.getppid()}")
print(f"   Python executable: {sys.executable}")
print()

# 2. Get parent process info
try:
    import psutil
    current = psutil.Process(os.getpid())
    print("2. Process Tree:")

    process = current
    depth = 0
    while process and depth < 5:
        try:
            print(f"   {'  ' * depth}→ {process.name()} (PID: {process.pid})")
            print(f"   {'  ' * depth}  Executable: {process.exe()}")
            process = process.parent()
            depth += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            break
    print()
except ImportError:
    print("2. psutil not installed - skipping process tree")
    print()

# 3. Check which apps have accessibility permissions
print("3. Apps with Accessibility Permissions:")
result = subprocess.run(
    ["sqlite3",
     "/Library/Application Support/com.apple.TCC/TCC.db",
     "SELECT client FROM access WHERE service='kTCCServiceAccessibility' AND allowed=1;"],
    capture_output=True,
    text=True
)

if result.returncode == 0 and result.stdout:
    apps = result.stdout.strip().split('\n')
    for app in apps:
        print(f"   ✓ {app}")
else:
    # Try user TCC database
    user_tcc = os.path.expanduser("~/Library/Application Support/com.apple.TCC/TCC.db")
    result = subprocess.run(
        ["sqlite3",
         user_tcc,
         "SELECT client FROM access WHERE service='kTCCServiceAccessibility' AND allowed=1;"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0 and result.stdout:
        apps = result.stdout.strip().split('\n')
        for app in apps:
            print(f"   ✓ {app}")
    else:
        print("   Could not read TCC database (this is normal)")
print()

# 4. Try to access accessibility API
print("4. Testing Accessibility API Access:")
try:
    import terminator
    print("   Attempting to create Desktop instance...")
    desktop = terminator.Desktop()
    print("   ✓ Desktop created")

    print("   Attempting to get focused element...")
    focused = desktop.focused_element()
    print("   ✓ Got focused element")

    print("   Attempting to get application...")
    app = focused.application()
    if app:
        app_name = app.name()
        print(f"   ✓ Got application: {app_name}")

    print()
    print("🎉 SUCCESS! Accessibility permissions are working!")

except Exception as e:
    print(f"   ✗ Error: {e}")
    print()
    print("❌ Accessibility permissions NOT working")
    print()

    # 5. Provide specific guidance
    print("5. Troubleshooting Steps:")
    print()
    print("   The error suggests that the accessibility API cannot be accessed.")
    print("   This usually means:")
    print()
    print("   Option A: Warp needs to be added to Accessibility")
    print("   → System Settings → Privacy & Security → Accessibility")
    print("   → Click + and add: /Applications/Warp.app")
    print()
    print("   Option B: If Warp is already there, try:")
    print("   1. Remove Warp from the list (click - button)")
    print("   2. Add it back (click + button)")
    print("   3. Make sure toggle is ON")
    print("   4. Completely quit and restart Warp (Cmd+Q)")
    print()
    print("   Option C: Try running Python directly:")
    print("   → Add Python itself to Accessibility:")
    print(f"   → {sys.executable}")
    print()
    print("   Option D: System Integrity Protection (SIP) might be interfering")
    print("   → Check SIP status: csrutil status")
    print()

print("=" * 80)
