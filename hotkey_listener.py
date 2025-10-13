"""Global hotkey listener for triggered mode"""
import asyncio
from typing import Callable, Optional
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from config import HOTKEY, IS_WINDOWS, IS_MACOS


class HotkeyListener:
    """Listens for global hotkey (Ctrl+G on Windows, Cmd+G on macOS) to trigger agent"""

    def __init__(self, callback: Callable):
        """
        Initialize hotkey listener.

        Args:
            callback: Async function to call when hotkey is pressed
        """
        self.callback = callback
        self.listener: Optional[keyboard.Listener] = None
        self.current_keys = set()
        self.loop = None

        # Parse hotkey string (e.g., "cmd+g")
        parts = HOTKEY.lower().split('+')
        self.modifiers = set()
        self.key = None

        for part in parts:
            part = part.strip()
            if part in ['cmd', 'command']:
                self.modifiers.add(Key.cmd)
            elif part in ['ctrl', 'control']:
                self.modifiers.add(Key.ctrl)
            elif part in ['alt', 'option']:
                self.modifiers.add(Key.alt)
            elif part in ['shift']:
                self.modifiers.add(Key.shift)
            else:
                # Regular key
                self.key = KeyCode.from_char(part)

    def start(self, loop: asyncio.AbstractEventLoop):
        """Start listening for hotkey"""
        self.loop = loop

        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()
        print(f"[Hotkey] Listening for {HOTKEY.upper()} to trigger agent...")

    def stop(self):
        """Stop listening"""
        if self.listener:
            self.listener.stop()
            print("[Hotkey] Stopped listening")

    def _on_press(self, key):
        """Handle key press"""
        self.current_keys.add(key)
        self._check_hotkey()

    def _on_release(self, key):
        """Handle key release"""
        if key in self.current_keys:
            self.current_keys.remove(key)

    def _check_hotkey(self):
        """Check if hotkey combination is pressed"""
        # Check if all modifiers are pressed
        modifiers_pressed = all(mod in self.current_keys for mod in self.modifiers)

        # Check if the main key is pressed
        key_pressed = self.key in self.current_keys

        if modifiers_pressed and key_pressed:
            print(f"\n[Hotkey] {HOTKEY.upper()} detected! Triggering agent...\n")

            # Call the callback in the event loop
            if self.loop and self.callback:
                asyncio.run_coroutine_threadsafe(self.callback(), self.loop)

            # Clear keys to avoid repeated triggers
            self.current_keys.clear()
