#!/usr/bin/env python3
"""
Permission checker and setup helper for Coworker AI Agent

Checks accessibility permissions and guides the user through setup.
"""
import sys
import subprocess
import platform
import argparse

def check_accessibility_permissions():
    """Check if accessibility permissions are granted"""
    print("🔍 Checking accessibility permissions...\n")

    try:
        import terminator

        # Try to create a desktop instance
        desktop = terminator.Desktop()

        # Try to get focused element (this will fail if no permissions)
        try:
            focused = desktop.focused_element()
            app = focused.application()
            app_name = app.name() if app else "Unknown"

            print("✅ Accessibility permissions are GRANTED!")
            print(f"✅ Successfully accessed focused app: {app_name}")
            print(f"✅ Focused element role: {focused.role()}\n")
            return True

        except Exception as e:
            error_msg = str(e)

            if "kAXErrorCannotComplete" in error_msg or "accessibility error" in error_msg.lower():
                print("❌ Accessibility permissions are NOT granted")
                print(f"   Error: {error_msg}\n")
                return False
            elif "PermissionDenied" in error_msg or "not granted" in error_msg.lower():
                print("❌ Accessibility permissions are NOT granted")
                print(f"   Error: {error_msg}\n")
                return False
            else:
                print(f"⚠️  Unexpected error: {error_msg}")
                print("   This might indicate a different issue.\n")
                return False

    except ImportError:
        print("❌ terminator library not installed")
        print("   Run: pip install terminator\n")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}\n")
        return False

def open_accessibility_settings():
    """
    Open System Settings to Accessibility panel.

    Note: macOS does NOT allow programmatic granting of accessibility permissions
    for security reasons. We can only open the settings panel.
    """
    print("📱 Opening System Settings → Privacy & Security → Accessibility...\n")

    if platform.system() != "Darwin":
        print("⚠️  This script is designed for macOS only.")
        return False

    try:
        # Open System Settings to Privacy & Security > Accessibility
        # This uses the x-apple.systempreferences URL scheme
        subprocess.run([
            "open",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
        ], check=True)

        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to open System Settings: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def get_terminal_app_path():
    """Try to detect which terminal app is being used"""
    try:
        # Get the parent process (the terminal)
        import psutil
        import os

        current_process = psutil.Process(os.getpid())
        parent = current_process.parent()

        if parent:
            parent_name = parent.name()
            parent_exe = parent.exe()

            # Common terminal apps
            terminal_apps = {
                "Terminal": "/Applications/Utilities/Terminal.app",
                "iTerm2": "/Applications/iTerm.app",
                "iTerm": "/Applications/iTerm.app",
                "Warp": "/Applications/Warp.app",
                "Alacritty": "/Applications/Alacritty.app",
                "kitty": "/Applications/kitty.app",
            }

            for name, path in terminal_apps.items():
                if name.lower() in parent_name.lower():
                    return name, path

            return parent_name, parent_exe

    except ImportError:
        print("   (Install psutil to detect terminal app: pip install psutil)")
        return "Terminal", "/Applications/Utilities/Terminal.app"
    except Exception:
        pass

    return "Terminal", "/Applications/Utilities/Terminal.app"

def print_instructions():
    """Print step-by-step instructions for granting permissions"""
    terminal_name, terminal_path = get_terminal_app_path()

    print("=" * 80)
    print("📋 HOW TO GRANT ACCESSIBILITY PERMISSIONS")
    print("=" * 80)
    print()
    print("macOS requires manual permission granting for security reasons.")
    print("Follow these steps:")
    print()
    print("1. System Settings should now be open to the Accessibility panel")
    print("   (If not, go to: System Settings → Privacy & Security → Accessibility)")
    print()
    print("2. Click the 🔒 lock icon at the bottom and enter your password")
    print()
    print(f"3. Click the [+] button and navigate to:")
    print(f"   {terminal_path}")
    print(f"   (Your terminal app: {terminal_name})")
    print()
    print("4. Select the app and click 'Open'")
    print()
    print("5. Make sure the toggle switch is ON (blue) ✅")
    print()
    print("6. IMPORTANT: Restart your terminal app completely")
    print("   - Quit the terminal (Cmd+Q)")
    print("   - Reopen it")
    print()
    print("7. Run this script again to verify:")
    print("   python check_permissions.py")
    print()
    print("=" * 80)
    print()

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Check and setup accessibility permissions for Coworker AI Agent"
    )
    parser.add_argument(
        "--open-settings",
        action="store_true",
        help="Automatically open System Settings (skip prompt)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output (just check status)"
    )
    args = parser.parse_args()

    if not args.quiet:
        print()
        print("╔" + "═" * 78 + "╗")
        print("║" + " " * 78 + "║")
        print("║" + "        COWORKER PERMISSION CHECKER".center(78) + "║")
        print("║" + " " * 78 + "║")
        print("╚" + "═" * 78 + "╝")
        print()

    # Check permissions
    has_permissions = check_accessibility_permissions()

    if has_permissions:
        if not args.quiet:
            print("🎉 All set! You can now run the Coworker agent:")
            print()
            print("   python agent.py triggered    # Press CMD+G to trigger")
            print("   python agent.py continuous   # Auto-monitor every 30s")
            print("   python agent.py once         # Run once and exit")
            print()
        return 0

    # Permissions not granted
    if not args.quiet:
        print("⚠️  Accessibility permissions are required for Coworker to work.")
        print()

    # Handle opening settings
    should_open = args.open_settings

    if not should_open and not args.quiet:
        # Ask if user wants to open settings (interactive mode only)
        try:
            response = input("Would you like to open System Settings now? (y/n): ").strip().lower()
            should_open = response in ['y', 'yes']
        except (KeyboardInterrupt, EOFError):
            print("\n\nSetup cancelled.\n")
            return 1

    if should_open:
        opened = open_accessibility_settings()

        if opened:
            if not args.quiet:
                print("✅ System Settings opened!\n")
                print_instructions()
        else:
            if not args.quiet:
                print("\n❌ Could not open System Settings automatically.")
                print("   Please open it manually:")
                print("   System Settings → Privacy & Security → Accessibility\n")
                print_instructions()
    else:
        if not args.quiet:
            print("\n📝 When you're ready, manually grant permissions:")
            print("   System Settings → Privacy & Security → Accessibility\n")
            print_instructions()

    return 1

if __name__ == "__main__":
    sys.exit(main())
