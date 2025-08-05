"""
Cross-platform keyboard input handler for enhanced watch mode.

Provides background keyboard monitoring to capture mode change commands
without blocking the main application loop.
"""

import threading
import queue
import sys
import select
import tty
import termios
from typing import Optional
from datetime import datetime

from .runtime_modes import RuntimeModeManager
from .watch_types import ModeChangeCommand


class KeyboardHandler:
    """
    Background keyboard input handler for runtime mode changes.
    
    Runs in a separate thread to monitor keyboard input and generate
    mode change commands when specific keys are pressed:
    - 'c': Cycle checks verbosity mode
    - 'r': Cycle reviews verbosity mode  
    - 'l': Cycle labels verbosity mode
    - 'q': Quit watch mode
    """
    
    # Key mappings to features
    KEY_MAPPINGS = {
        'c': 'checks',
        'r': 'reviews', 
        'l': 'labels'
    }
    
    def __init__(self, mode_manager: RuntimeModeManager, command_queue: queue.Queue):
        """
        Initialize the keyboard handler.
        
        Args:
            mode_manager: The runtime mode manager to use for cycling modes
            command_queue: Queue to send commands to the main thread
        """
        self.mode_manager = mode_manager
        self.command_queue = command_queue
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._original_settings = None
        self._is_windows = sys.platform.startswith('win')
    
    def start(self) -> None:
        """Start the keyboard monitoring thread."""
        if self._thread is not None and self._thread.is_alive():
            return  # Already running
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._keyboard_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        """Stop the keyboard monitoring thread and clean up."""
        if self._thread is None:
            return
        
        self._stop_event.set()
        
        # Restore terminal settings if we modified them
        if self._original_settings is not None and not self._is_windows:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._original_settings)
            except (termios.error, OSError):
                pass  # Ignore errors during cleanup
            self._original_settings = None
        
        # Wait for thread to finish (with timeout)
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)
        
        self._thread = None
    
    def is_running(self) -> bool:
        """Check if the keyboard handler is currently running."""
        return self._thread is not None and self._thread.is_alive()
    
    def _keyboard_loop(self) -> None:
        """Main keyboard monitoring loop running in background thread."""
        if self._is_windows:
            self._keyboard_loop_windows()
        else:
            self._keyboard_loop_unix()
    
    def _keyboard_loop_unix(self) -> None:
        """Unix/Linux keyboard monitoring implementation."""
        try:
            # Set terminal to raw mode for single character input
            self._original_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
            
            while not self._stop_event.is_set():
                # Check if input is available (non-blocking)
                if select.select([sys.stdin], [], [], 0.1)[0]:  # 100ms timeout
                    try:
                        char = sys.stdin.read(1).lower()
                        self._process_key(char)
                    except (OSError, IOError):
                        # Handle terminal issues gracefully
                        break
        
        except (termios.error, OSError) as e:
            # Terminal setup failed, fall back to line-based input
            self._keyboard_loop_fallback()
        
        finally:
            # Restore terminal settings
            if self._original_settings is not None:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._original_settings)
                except (termios.error, OSError):
                    pass
    
    def _keyboard_loop_windows(self) -> None:
        """Windows keyboard monitoring implementation."""
        try:
            import msvcrt
            
            while not self._stop_event.is_set():
                if msvcrt.kbhit():
                    char = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                    self._process_key(char)
                else:
                    # Sleep briefly to avoid busy waiting
                    self._stop_event.wait(0.1)
        
        except ImportError:
            # msvcrt not available, fall back to line input
            self._keyboard_loop_fallback()
    
    def _keyboard_loop_fallback(self) -> None:
        """
        Fallback keyboard input for systems where raw input is not available.
        
        This uses line-based input which requires pressing Enter after each key,
        but provides basic functionality across all platforms.
        """
        while not self._stop_event.is_set():
            try:
                # Use select to check for input availability with timeout
                if sys.stdin in select.select([sys.stdin], [], [], 1.0)[0]:
                    line = sys.stdin.readline().strip().lower()
                    if line:
                        # Process the first character of the line
                        self._process_key(line[0])
            except (OSError, IOError, KeyboardInterrupt):
                break
    
    def _process_key(self, char: str) -> None:
        """
        Process a pressed key and generate appropriate commands.
        
        Args:
            char: The character that was pressed
        """
        # Handle Ctrl+C (ASCII 3) in raw mode
        if ord(char) == 3:  # Ctrl+C
            try:
                self.command_queue.put(('quit', None), timeout=0.1)
            except queue.Full:
                pass  # Queue full, skip this command
            return
        
        # Ensure lowercase for consistent processing
        char = char.lower()
        
        if char == 'q':
            # Special quit command
            try:
                self.command_queue.put(('quit', None), timeout=0.1)
            except queue.Full:
                pass  # Queue full, skip this command
            return
        
        if char in self.KEY_MAPPINGS:
            feature = self.KEY_MAPPINGS[char]
            try:
                # Cycle the mode
                new_mode = self.mode_manager.cycle_mode(feature)
                
                # Create and queue the command
                command = ModeChangeCommand(
                    feature=feature,
                    new_mode=new_mode,
                    timestamp=datetime.now().isoformat()
                )
                
                self.command_queue.put(('mode_change', command), timeout=0.1)
                
            except (ValueError, queue.Full):
                # Invalid feature or queue full, skip this command
                pass
    
    def get_help_text(self) -> str:
        """Get help text describing available keyboard commands."""
        return (
            "Keyboard Commands:\n"
            "  c - Cycle checks verbosity mode\n"
            "  r - Cycle reviews verbosity mode\n"
            "  l - Cycle labels verbosity mode\n"
            "  q - Quit watch mode\n"
            "  Ctrl+C - Quit watch mode"
        )
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()