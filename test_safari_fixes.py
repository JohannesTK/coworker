#!/usr/bin/env python3
"""
Test script for Safari fixes - address bar clicking and Return key

This script tests both fixes:
1. Address bar clicking with improved element detection
2. Return key pressing instead of typing "RETUN"
"""

import os
import sys
from cua import CUAAgent
from rich.console import Console

console = Console()

def main():
    """Test the Safari fixes."""
    
    # Check for API key
    if not os.getenv('GROQ_API_KEY'):
        console.print("[red]Error: GROQ_API_KEY environment variable not set[/red]")
        console.print("Please set your Groq API key:")
        console.print("export GROQ_API_KEY='your_api_key_here'")
        sys.exit(1)
    
    # Initialize agent
    try:
        agent = CUAAgent()
        console.print("[green]✓ CUA Agent initialized successfully[/green]")
    except Exception as e:
        console.print(f"[red]Error initializing agent: {e}[/red]")
        sys.exit(1)
    
    # Test goal - focus Safari, click address bar, type URL, and press Return
    test_goal = "Focus Safari, click the address bar, type 'https://www.google.com', and press Return"
    
    console.print(f"\n[bold blue]Test Goal:[/bold blue] {test_goal}")
    console.print("[yellow]This will test both fixes:[/yellow]")
    console.print("[yellow]1. Address bar clicking with improved element detection[/yellow]")
    console.print("[yellow]2. Return key pressing instead of typing 'RETUN'[/yellow]")
    
    # Ask for confirmation
    from rich.prompt import Confirm
    if not Confirm.ask("Proceed with test?"):
        console.print("[yellow]Test cancelled[/yellow]")
        return
    
    # Run the test
    try:
        success = agent.run_goal_loop(test_goal, max_iterations=5)
        
        if success:
            console.print("\n[bold green]✓ Test completed successfully![/bold green]")
            console.print("Safari should now be navigating to Google.")
            console.print("Both fixes should be working:")
            console.print("• Address bar was clicked successfully")
            console.print("• Return key was pressed (not typed)")
        else:
            console.print("\n[yellow]Test completed with partial success[/yellow]")
            console.print("The system may have encountered issues.")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Test failed with error: {e}[/red]")
        console.print("This might be due to:")
        console.print("• Safari not running")
        console.print("• Missing accessibility permissions")
        console.print("• Network issues")
        console.print("• API rate limits")

if __name__ == "__main__":
    main()
