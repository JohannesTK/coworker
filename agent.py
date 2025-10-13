#!/usr/bin/env python3
"""
Coworker - AI Productivity Assistant for Knowledge Workers

Main agent orchestrator that coordinates observation, LLM reasoning, and action execution.
"""
import asyncio
import sys
import time
from datetime import datetime
from typing import Optional

from desktop_observer import DesktopObserver
from llm_client import LLMClient
from memory import MemoryManager
from action_executor import ActionExecutor
from hotkey_listener import HotkeyListener
from config import CONTINUOUS_MODE_INTERVAL, HOTKEY


class CoworkerAgent:
    """Main agent orchestrator"""

    def __init__(self):
        print("Initializing Coworker AI Agent...")
        self.observer = DesktopObserver()
        self.llm = LLMClient()
        self.memory = MemoryManager()
        self.executor = ActionExecutor()
        self.hotkey_listener: Optional[HotkeyListener] = None
        self.running = False
        print("✓ All components initialized\n")

    async def analyze_and_recommend(self):
        """Main observation -> analysis -> recommendation flow"""
        try:
            pipeline_start = time.time()

            print("=" * 80)
            print("OBSERVING DESKTOP STATE")
            print("=" * 80)

            # 1. Observe desktop state
            obs_start = time.time()
            desktop_state = await self.observer.observe()
            obs_duration = time.time() - obs_start

            print(f"\n⏱️  Observation took: {obs_duration:.2f}s")

            # Display state to terminal
            state_display = self.observer.format_state_for_display(desktop_state)
            print(state_display)

            # 2. Prepare memory context
            print("\n" + "=" * 80)
            print("LOADING MEMORY CONTEXT")
            print("=" * 80)

            mem_start = time.time()
            memory_context = {
                "task_history": self.memory.format_task_history(limit=10),
                "preferences": self.memory.format_preferences(),
                "goals": self.memory.format_goals(),
                "history_count": len(self.memory.get_recent_tasks())
            }
            mem_duration = time.time() - mem_start

            # Show context stats
            stats = self.memory.get_context_stats()
            print(f"Context: {stats['total_tokens']:,} / {stats['max_tokens']:,} tokens ({stats['usage_percent']:.1f}%)")
            print(f"Task history: {stats['task_count']} items")
            print(f"⏱️  Memory loading took: {mem_duration:.3f}s\n")

            # 3. Get LLM recommendations (streaming)
            print("=" * 80)
            print("LLM ANALYSIS (Streaming)")
            print("=" * 80)
            print()

            llm_start = time.time()
            stream = self.llm.get_recommendations(desktop_state, memory_context, stream=True)

            # Print streaming output
            full_response = ""
            first_token_time = None
            async for chunk in stream:
                if first_token_time is None:
                    first_token_time = time.time()
                    ttft = first_token_time - llm_start
                    print(f"[⏱️  First token: {ttft:.2f}s] ", end='', flush=True)
                print(chunk, end='', flush=True)
                full_response += chunk

            llm_duration = time.time() - llm_start
            print(f"\n\n⏱️  LLM response took: {llm_duration:.2f}s (total)")
            print()

            # Parse the response
            import json
            parse_start = time.time()
            try:
                recommendations = json.loads(full_response)
            except json.JSONDecodeError as e:
                print(f"[Agent] Failed to parse LLM response: {e}")
                return
            parse_duration = time.time() - parse_start

            # 4. Display recommendations
            print("=" * 80)
            print("RECOMMENDATIONS")
            print("=" * 80)
            print(f"⏱️  Parsing took: {parse_duration:.3f}s\n")
            print(f"\n🎯 Predicted Goal: {recommendations.get('predicted_goal', 'Unknown')}\n")
            print(f"📝 Context Summary: {recommendations.get('context_summary', 'N/A')}\n")

            recs = recommendations.get('recommendations', [])
            if not recs:
                print("No recommendations available.\n")
                return

            # Display each recommendation
            for rec in recs:
                impact_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec.get('impact', 'low'), "⚪")
                print(f"{impact_emoji} [{rec.get('id')}] {rec.get('title', 'Untitled')}")
                print(f"   Impact: {rec.get('impact', 'unknown').upper()}")
                print(f"   Description: {rec.get('description', 'N/A')}")
                print(f"   Reasoning: {rec.get('reasoning', 'N/A')}")
                print(f"   Action: {rec.get('action', {}).get('type', 'unknown')}")
                print()

            if recommendations.get('workflow_insights'):
                print(f"💡 Workflow Insights: {recommendations['workflow_insights']}\n")

            # Save predicted goal to memory
            predicted_goal = recommendations.get('predicted_goal', 'Unknown')
            self.memory.add_goal(predicted_goal)

            # 5. User confirmation
            print("=" * 80)
            print("SELECT ACTION")
            print("=" * 80)
            print("Choose an action to execute (or 0 to skip):")
            for rec in recs:
                print(f"  {rec.get('id')} - {rec.get('title')}")
            print("  0 - Skip / Do nothing")
            print()

            # Get user input
            try:
                choice = input("Enter your choice (0-3): ").strip()
                choice_num = int(choice)

                if choice_num == 0:
                    print("\n[Agent] No action taken.\n")
                    return

                # Find selected recommendation
                selected_rec = next((r for r in recs if r.get('id') == choice_num), None)
                if not selected_rec:
                    print(f"\n[Agent] Invalid choice: {choice_num}\n")
                    return

                # 6. Execute action
                print("\n" + "=" * 80)
                print(f"EXECUTING ACTION: {selected_rec.get('title')}")
                print("=" * 80)
                print()

                action = selected_rec.get('action', {})

                # Validate action
                is_valid, error = self.executor.validate_action(action)
                if not is_valid:
                    print(f"[Agent] Invalid action: {error}\n")
                    return

                # Execute
                exec_start = time.time()
                result = await self.executor.execute(action)
                exec_duration = time.time() - exec_start

                print(f"\n✓ Result: {result}")
                print(f"⏱️  Execution took: {exec_duration:.2f}s\n")

                # 7. Save to memory
                save_start = time.time()
                self.memory.add_task(
                    action=action,
                    result=result,
                    predicted_goal=predicted_goal
                )
                save_duration = time.time() - save_start
                print(f"⏱️  Memory save took: {save_duration:.3f}s")

                # Update preferences based on action
                if 'application:' in action.get('target', ''):
                    app_name = action['target'].split('application:')[1].split('>>')[0].strip()
                    self.memory.update_preferences(f'apps.{app_name}', True)

            except ValueError:
                print(f"\n[Agent] Invalid input. Please enter a number.\n")
            except KeyboardInterrupt:
                print("\n\n[Agent] Interrupted by user.\n")

            # Total pipeline time
            pipeline_duration = time.time() - pipeline_start
            print("\n" + "=" * 80)
            print(f"⏱️  TOTAL PIPELINE TIME: {pipeline_duration:.2f}s")
            print("=" * 80 + "\n")

        except Exception as e:
            print(f"\n[Agent] Error during analysis: {e}\n")
            import traceback
            traceback.print_exc()

    async def continuous_mode(self):
        """Run agent in continuous monitoring mode"""
        print(f"\n🔄 Starting continuous mode (interval: {CONTINUOUS_MODE_INTERVAL}s)")
        print("Press Ctrl+C to stop\n")

        try:
            while self.running:
                await self.analyze_and_recommend()

                if self.running:
                    print(f"Waiting {CONTINUOUS_MODE_INTERVAL}s before next observation...\n")
                    await asyncio.sleep(CONTINUOUS_MODE_INTERVAL)
        except KeyboardInterrupt:
            print("\n\n[Agent] Continuous mode stopped by user.\n")

    async def triggered_mode(self):
        """Run agent in triggered mode (hotkey-activated)"""
        print(f"\n⌨️  Starting triggered mode")
        print(f"Press {HOTKEY.upper()} to trigger analysis")
        print("Press Ctrl+C to stop\n")

        try:
            # Keep the event loop running
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n\n[Agent] Triggered mode stopped by user.\n")

    async def run(self, mode: str = "continuous"):
        """
        Run the agent.

        Args:
            mode: "continuous" or "triggered"
        """
        self.running = True

        try:
            if mode == "continuous":
                await self.continuous_mode()
            elif mode == "triggered":
                # Set up hotkey listener
                loop = asyncio.get_event_loop()
                self.hotkey_listener = HotkeyListener(callback=self.analyze_and_recommend)
                self.hotkey_listener.start(loop)

                await self.triggered_mode()
            else:
                print(f"[Agent] Unknown mode: {mode}")
        finally:
            self.running = False
            if self.hotkey_listener:
                self.hotkey_listener.stop()

    async def run_once(self):
        """Run analysis once and exit"""
        await self.analyze_and_recommend()


async def main():
    """Main entry point"""
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║                          COWORKER AI AGENT                                ║
║                                                                           ║
║              Your Expert Productivity Assistant                          ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)

    # Parse command line arguments
    mode = "continuous"
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ["continuous", "c"]:
            mode = "continuous"
        elif arg in ["triggered", "t", "hotkey"]:
            mode = "triggered"
        elif arg in ["once", "o"]:
            mode = "once"
        else:
            print(f"Usage: python agent.py [continuous|triggered|once]")
            print(f"  continuous (default) - Monitor desktop continuously")
            print(f"  triggered - Wait for CMD+G hotkey")
            print(f"  once - Run once and exit")
            return

    # Create and run agent
    agent = CoworkerAgent()

    if mode == "once":
        await agent.run_once()
    else:
        await agent.run(mode)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nCoworker Agent stopped. Goodbye!\n")
