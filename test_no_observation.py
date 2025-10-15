#!/usr/bin/env python3
"""
Test script for CUA without observation phase

This script tests the CUA system with observation disabled to avoid crashes.
"""

import os
import sys
from cua import CUAAgent
from rich.console import Console

console = Console()

def main():
    """Test the CUA system without observation."""
    
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
    
    # Test goal - focus Safari and click address bar (no observation)
    test_goal = "Focus Safari and click on the address bar"
    
    console.print(f"\n[bold blue]Test Goal:[/bold blue] {test_goal}")
    console.print("[yellow]This will test the CUA system with observation disabled.[/yellow]")
    console.print("[yellow]This should prevent the Python rocket crash.[/yellow]")
    
    # Ask for confirmation
    from rich.prompt import Confirm
    if not Confirm.ask("Proceed with test?"):
        console.print("[yellow]Test cancelled[/yellow]")
        return
    
    # Run the test
    try:
        success = agent.run_goal_loop(test_goal, max_iterations=3, skip_observation=True)
        
        if success:
            console.print("\n[bold green]✓ Test completed successfully![/bold green]")
            console.print("The CUA system worked without observation phase.")
            console.print("No Python rocket crash occurred.")
        else:
            console.print("\n[yellow]Test completed with partial success[/yellow]")
            console.print("The system may have encountered issues.")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Test failed with error: {e}[/red]")
        console.print("This might be due to:")
        console.print("• Missing accessibility permissions")
        console.print("• Network issues")
        console.print("• API rate limits")

if __name__ == "__main__":
    main()
