"""Quick test of navigation features."""
import asyncio
from pathlib import Path
from agent import CodeAgent

async def quick_test():
    # Use small test folder for faster init
    agent = CodeAgent(Path('.'))
    
    print("Initializing...")
    await agent.initialize()
    
    print("\n1. Symbol search for 'CodeAgent':")
    symbols = agent.search_symbols('CodeAgent')
    print(f"   Found {len(symbols)} symbols")
    for s in symbols[:3]:
        print(f"   - {s.name} in {s.file}:{s.range.start.line}")
    
    if symbols:
        print(f"\n2. Find references to '{symbols[0].name}':")
        refs = await agent.find_references(
            symbols[0].file, 
            symbols[0].range.start.line, 
            symbols[0].range.start.column
        )
        print(f"   Found {len(refs.references)} references")
        
        print(f"\n3. Go-to-definition at agent.py line 50, col 15:")
        defs = await agent.go_to_definition('agent.py', 50, 15)
        print(f"   Found {len(defs.definitions)} definitions")
        if defs.symbol:
            print(f"   Symbol: {defs.symbol.name}")

asyncio.run(quick_test())
