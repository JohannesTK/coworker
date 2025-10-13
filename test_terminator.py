"""Test script to diagnose Terminator API on Windows"""
import terminator
import asyncio

async def test_terminator():
    desktop = terminator.Desktop()

    print("=" * 80)
    print("Testing Terminator Desktop API on Windows")
    print("=" * 80)

    # Test 1: Get focused element
    print("\n1. Testing focused_element()...")
    try:
        elem = desktop.focused_element()
        print(f"   ✓ Focused element: {elem}")
        print(f"   ✓ Element role: {elem.role()}")
        print(f"   ✓ Element name: {elem.name()}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 2: Get window from element
    print("\n2. Testing element.window()...")
    try:
        elem = desktop.focused_element()
        window = elem.window()
        if window:
            print(f"   ✓ Window object: {window}")
            print(f"   ✓ Window name: {window.name()}")
            print(f"   ✓ Window PID: {window.process_id()}")
        else:
            print("   ✗ window() returned None")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 3: Get application
    print("\n3. Testing element.application()...")
    try:
        elem = desktop.focused_element()
        app = elem.application()
        if app:
            print(f"   ✓ Application object: {app}")
            print(f"   ✓ Application name: {app.name()}")
        else:
            print("   ✗ application() returned None")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 4: Try alternative - get current window
    print("\n4. Testing desktop.get_current_window()...")
    try:
        window = desktop.get_current_window()
        if window:
            print(f"   ✓ Current window: {window}")
            print(f"   ✓ Window name: {window.get('title', 'N/A')}")
            print(f"   ✓ Window app: {window.get('app', 'N/A')}")
        else:
            print("   ✗ get_current_window() returned None")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 5: Try to get window tree
    print("\n5. Testing desktop.get_window_tree()...")
    try:
        elem = desktop.focused_element()
        window = elem.window()
        if window:
            pid = window.process_id()
            title = window.name()
            print(f"   Attempting get_window_tree(pid={pid}, title='{title}')...")
            tree = desktop.get_window_tree(pid=pid, title=title)
            print(f"   ✓ Tree root: {tree}")
            print(f"   ✓ Tree role: {tree.attributes.role}")
            print(f"   ✓ Tree children: {len(tree.children)}")
        else:
            print("   ✗ No window available for tree test")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 6: Try element children directly
    print("\n6. Testing element.children()...")
    try:
        elem = desktop.focused_element()
        children = elem.children()
        print(f"   ✓ Children count: {len(children)}")
        for i, child in enumerate(children[:5]):
            try:
                print(f"   ✓ Child {i}: {child.role()} - {child.name()}")
            except:
                print(f"   ✗ Child {i}: Could not access")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 7: Try screenshot
    print("\n7. Testing window.capture()...")
    try:
        elem = desktop.focused_element()
        window = elem.window()
        if window:
            screenshot = window.capture()
            print(f"   ✓ Screenshot: {screenshot}")
            print(f"   ✓ Screenshot type: {type(screenshot)}")
        else:
            print("   ✗ No window available for screenshot")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 8: Alternative approach - use root element
    print("\n8. Testing desktop.root()...")
    try:
        root = desktop.root()
        print(f"   ✓ Root element: {root}")
        print(f"   ✓ Root role: {root.role()}")
        print(f"   ✓ Root children: {len(root.children())}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_terminator())
