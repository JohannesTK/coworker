import terminator
import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test():
    d = terminator.Desktop()
    tree = await d.get_all_applications_tree()
    print(f'Tree type: {type(tree)}')
    print(f'Tree length: {len(tree) if tree else 0}')
    if tree:
        print(f'First 1000 chars:\n{tree[:1000]}')

asyncio.run(test())
