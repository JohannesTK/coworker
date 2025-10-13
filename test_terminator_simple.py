"""Test script to diagnose Terminator API on Windows"""
import terminator
import asyncio
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

async def test_terminator():
    desktop = terminator.Desktop()

    print("=" * 80)
    print("Testing Terminator Desktop API on Windows")
    print("=" * 80)

    # Test 1: Get focused element
    print("\n1. Testing focused_element()...")
    try:
        elem = desktop.focused_element()
        print(f"   [OK] Focused element: {elem}")
        print(f"   [OK] Element role: {elem.role()}")
        print(f"   [OK] Element name: {elem.name()}")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 2: Get window from element
    print("\n2. Testing element.window()...")
    try:
        elem = desktop.focused_element()
        window = elem.window()
        if window:
            print(f"   [OK] Window object: {window}")
            print(f"   [OK] Window name: {window.name()}")
            print(f"   [OK] Window PID: {window.process_id()}")
        else:
            print("   [FAIL] window() returned None")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 3: Get application
    print("\n3. Testing element.application()...")
    try:
        elem = desktop.focused_element()
        app = elem.application()
        if app:
            print(f"   [OK] Application object: {app}")
            print(f"   [OK] Application name: {app.name()}")
        else:
            print("   [FAIL] application() returned None")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 4: Try alternative - get current window
    print("\n4. Testing desktop.get_current_window()...")
    try:
        window = desktop.get_current_window()
        if window:
            print(f"   [OK] Current window: {window}")
            print(f"   [OK] Window keys: {window.keys() if hasattr(window, 'keys') else 'N/A'}")
        else:
            print("   [FAIL] get_current_window() returned None")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 5: Try to get window tree
    print("\n5. Testing desktop.get_window_tree()...")
    try:
        elem = desktop.focused_element()
        window = elem.window()
        if window:
            pid = window.process_id()
            title = window.name()
            print(f"   Attempting get_window_tree(pid={pid}, title='{title}')...")
            tree = desktop.get_window_tree(pid=pid, title=title if title else None)
            print(f"   [OK] Tree root: {tree}")
            print(f"   [OK] Tree role: {tree.attributes.role}")
            print(f"   [OK] Tree children: {len(tree.children)}")
            # Show first few children
            for i, child in enumerate(tree.children[:3]):
                print(f"   [OK]   Child {i}: {child.attributes.role} - {child.attributes.name}")
        else:
            print("   [FAIL] No window available for tree test")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 6: Try element children directly
    print("\n6. Testing element.children()...")
    try:
        elem = desktop.focused_element()
        children = elem.children()
        print(f"   [OK] Children count: {len(children)}")
        for i, child in enumerate(children[:5]):
            try:
                print(f"   [OK] Child {i}: {child.role()} - {child.name()}")
            except Exception as ce:
                print(f"   [FAIL] Child {i}: Could not access - {ce}")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 7: Try screenshot
    print("\n7. Testing window.capture()...")
    try:
        elem = desktop.focused_element()
        window = elem.window()
        if window:
            screenshot = window.capture()
            print(f"   [OK] Screenshot: {screenshot}")
            print(f"   [OK] Screenshot type: {type(screenshot)}")
        else:
            print("   [FAIL] No window available for screenshot")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 8: Alternative approach - use root element
    print("\n8. Testing desktop.root()...")
    try:
        root = desktop.root()
        print(f"   [OK] Root element: {root}")
        print(f"   [OK] Root role: {root.role()}")
        print(f"   [OK] Root children: {len(root.children())}")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_terminator())
