"""Test different approaches to get Windows info"""
import terminator
import asyncio
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

async def test_approaches():
    desktop = terminator.Desktop()

    print("=" * 80)
    print("Testing Different Approaches to Get Window Info")
    print("=" * 80)

    # Approach 1: Use get_current_window with await
    print("\n1. Testing await desktop.get_current_window()...")
    try:
        window = await desktop.get_current_window()
        print(f"   [OK] Window: {window}")
        print(f"   [OK] Type: {type(window)}")
        if isinstance(window, dict):
            print(f"   [OK] Keys: {list(window.keys())}")
            for key, value in window.items():
                print(f"        - {key}: {value}")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

    # Approach 2: Use locator to find focused window
    print("\n2. Testing desktop.locator('role:Window')...")
    try:
        windows = await desktop.locator("role:Window").all()
        print(f"   [OK] Found {len(windows)} windows")

        # Find focused window
        for i, win in enumerate(windows[:10]):
            try:
                if win.is_focused():
                    print(f"   [OK] Focused window #{i}: {win.name()}")
                    print(f"   [OK] Window object: {win}")

                    # Try to get children
                    children = win.children()
                    print(f"   [OK] Window has {len(children)} children")

                    # Try to capture
                    try:
                        screenshot = win.capture()
                        print(f"   [OK] Screenshot captured: {type(screenshot)}")
                    except Exception as ce:
                        print(f"   [FAIL] Could not capture: {ce}")

                    break
            except Exception as e:
                print(f"   [FAIL] Error checking window {i}: {e}")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

    # Approach 3: Use root and traverse
    print("\n3. Testing desktop.root() traversal...")
    try:
        root = desktop.root()
        print(f"   [OK] Root: {root.role()}")

        def find_focused(elem, depth=0, max_depth=3):
            if depth > max_depth:
                return None
            try:
                if elem.is_focused():
                    return elem
                for child in elem.children():
                    result = find_focused(child, depth + 1, max_depth)
                    if result:
                        return result
            except:
                pass
            return None

        focused = find_focused(root)
        if focused:
            print(f"   [OK] Found focused element: {focused.role()} - {focused.name()}")
        else:
            print("   [FAIL] Could not find focused element")

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

    # Approach 4: Try get_all_applications_tree
    print("\n4. Testing desktop.get_all_applications_tree()...")
    try:
        tree = await desktop.get_all_applications_tree()
        print(f"   [OK] Tree type: {type(tree)}")
        if isinstance(tree, str):
            print(f"   [OK] Tree length: {len(tree)} chars")
            print(f"   [OK] First 500 chars:\n{tree[:500]}")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

    # Approach 5: Use get_current_application
    print("\n5. Testing desktop.get_current_application()...")
    try:
        app = desktop.get_current_application()
        print(f"   [OK] App: {app}")
        print(f"   [OK] Type: {type(app)}")
        if app:
            print(f"   [OK] App name: {app.name()}")

            # Try to get windows for this app
            windows = desktop.windows_for_application(app.name())
            print(f"   [OK] Windows for app: {len(windows)}")
            for i, win in enumerate(windows[:3]):
                print(f"        Window {i}: {win.name()}")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_approaches())
