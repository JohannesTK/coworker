#!/usr/bin/env python3
"""
Demo script for Computer Use Agent (CUA)

This script demonstrates the CUA system with a simple example.
"""

import os
import sys
from cua import CUAAgent
from rich.console import Console

console = Console()

def main():
    """Run a simple demo of the CUA system."""
    
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
    
    # Demo goal
    demo_goal = "Open Safari and navigate to https://www.python.org"
    
    console.print(f"\n[bold blue]Demo Goal:[/bold blue] {demo_goal}")
    console.print("[yellow]This will demonstrate the CUA system capabilities.[/yellow]")
    
    # Ask for confirmation
    from rich.prompt import Confirm
    if not Confirm.ask("Proceed with demo?"):
        console.print("[yellow]Demo cancelled[/yellow]")
        return
    
    # Run the demo
    try:
        success = agent.run_goal_loop(demo_goal, max_iterations=5)
        
        if success:
            console.print("\n[bold green]✓ Demo completed successfully![/bold green]")
            console.print("The CUA system successfully:")
            console.print("• Captured desktop state")
            console.print("• Created an execution plan")
            console.print("• Executed actions")
            console.print("• Observed changes")
            console.print("• Achieved the goal")
        else:
            console.print("\n[yellow]Demo completed with partial success[/yellow]")
            console.print("The system made progress but may not have fully achieved the goal.")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Demo failed with error: {e}[/red]")
        console.print("This might be due to:")
        console.print("• Missing accessibility permissions")
        console.print("• Network issues")
        console.print("• API rate limits")
        console.print("• System configuration issues")

if __name__ == "__main__":
    main()
