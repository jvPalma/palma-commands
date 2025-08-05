"""
Watch Controller - Main coordination logic for watch mode.

Manages the watch loop, integrates with GitHub client, and coordinates
between caching, diff detection, and live display systems.
"""

import asyncio
import signal
import sys
import queue
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
logging.getLogger().setLevel(logging.WARNING)  # Reduce noise

from rich.console import Console

from .watch_types import WatchConfig, WatchState, ModeChangeCommand
from .pr_cache import PRStateCache
from .diff_engine import DiffEngine
from .live_manager import LiveDisplayManager
from .spinner_manager import SpinnerManager
from .runtime_modes import RuntimeModeManager
from .keyboard_handler import KeyboardHandler


class WatchController:
    """
    Main controller for enhanced watch mode functionality.
    
    Coordinates between GitHub data fetching, caching, change detection,
    live display updates, keyboard input handling, and countdown timer display.
    """
    
    def __init__(self, console: Console, config: WatchConfig):
        self.console = console
        self.config = config
        self.cache = PRStateCache(config)
        self.diff_engine = DiffEngine()
        
        # Initialize enhanced components
        self.spinner_manager = SpinnerManager(config.interval)
        self.runtime_modes: Optional[RuntimeModeManager] = None  # Will be initialized with modes
        self.keyboard_handler: Optional[KeyboardHandler] = None
        self.command_queue: queue.Queue = queue.Queue()
        
        # Initialize live manager with enhanced components
        self.live_manager = LiveDisplayManager(
            console, config, self.spinner_manager, self.runtime_modes
        )
        
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self._shutdown_requested = False
        
        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()
    
    async def start_watch_mode(self, fetch_prs_func, options: Dict[str, Any]) -> None:
        """
        Start enhanced watch mode with the given PR fetching function and options.
        
        Args:
            fetch_prs_func: Function to fetch PRs (should return list of PullRequest objects)
            options: Options dictionary for PR fetching
        """
        if self.is_running:
            self.logger.warning("Watch mode already running")
            return
        
        self.is_running = True
        self._shutdown_requested = False
        
        try:
            # Initialize runtime mode manager with current display modes
            all_modes = self._extract_display_modes(options)
            # RuntimeModeManager only supports specific features
            supported_features = {"checks", "reviews", "labels"}
            runtime_modes = {k: v for k, v in all_modes.items() if k in supported_features}
            
            self.runtime_modes = RuntimeModeManager(runtime_modes)
            
            # Update live manager with runtime modes
            self.live_manager.runtime_modes = self.runtime_modes
            
            # Initialize keyboard handler
            self.keyboard_handler = KeyboardHandler(self.runtime_modes, self.command_queue)
            
            self.console.print("🔧 Starting Enhanced PRS Watch Mode...", style="blue")
            self.console.print(f"Update interval: {self.config.interval} seconds", style="dim")
            self.console.print("Keyboard shortcuts: c/r/l to cycle modes, Ctrl+C to stop\n", style="dim")
            
            # Start live display
            self.live_manager.start_live_display()
            
            # Start keyboard handler
            self.keyboard_handler.start()
            
            # Main watch loop with countdown
            await self._watch_loop_with_countdown(fetch_prs_func, options)
            
        except KeyboardInterrupt:
            self.console.print("\n🛑 Watch mode stopped by user", style="yellow")
        except Exception as e:
            self.logger.error(f"Error in watch mode: {e}")
            self.console.print(f"\n❌ Watch mode error: {e}", style="red")
        finally:
            await self._shutdown()
    
    async def _watch_loop(self, fetch_prs_func, options: Dict[str, Any]) -> None:
        """Main watch loop that fetches and displays PR updates."""
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while not self._shutdown_requested:
            try:
                # Update status to connecting
                self.live_manager.update_status("connecting")
                
                # Fetch PR data
                pr_data = await self._fetch_prs_with_timeout(fetch_prs_func, options)
                
                if pr_data is not None:
                    try:
                        # Successful fetch - unpack the tuple
                        prs, display_modes = pr_data
                        consecutive_errors = 0
                        
                        # Detect changes
                        changeset = self.cache.detect_changes(prs)
                        
                        # Log changes if any
                        if changeset.has_changes():
                            self.logger.info(f"Detected changes: {len(changeset.changes)} updates, "
                                           f"{len(changeset.new_prs)} new, {len(changeset.removed_prs)} removed")
                        
                        # Extract proper display modes (the fetch function returns its own modes)
                        extracted_modes = self._extract_display_modes(options)
                        
                        # Update display
                        self.live_manager.update_display(prs, extracted_modes, changeset)
                        
                    except Exception as e:
                        self.logger.error(f"Error processing PR data: {e}")
                        consecutive_errors += 1
                    
                else:
                    # Fetch failed
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        raise Exception(f"Failed to fetch PRs {consecutive_errors} times in a row")
                
                # Wait for next update
                await self._wait_for_next_update()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                error_msg = str(e)
                self.logger.error(f"Error in watch loop (attempt {consecutive_errors}): {error_msg}")
                self.live_manager.update_status("error", error_msg)
                
                if consecutive_errors >= max_consecutive_errors:
                    raise Exception(f"Too many consecutive errors: {error_msg}")
                
                # Wait before retrying (exponential backoff)
                wait_time = min(60, 5 * (2 ** (consecutive_errors - 1)))
                await asyncio.sleep(wait_time)
    
    async def _fetch_prs_with_timeout(self, fetch_func, options: Dict[str, Any], timeout: int = 30):
        """Fetch PRs with timeout handling."""
        try:
            # Create timeout task
            timeout_task = asyncio.create_task(asyncio.sleep(timeout))
            
            # Create fetch task - properly handle sync function
            def sync_wrapper():
                return fetch_func(options)
            
            # run_in_executor returns a Future, not a coroutine, so we don't need create_task
            fetch_future = asyncio.get_event_loop().run_in_executor(None, sync_wrapper)
            
            # Wait for first to complete
            done, pending = await asyncio.wait(
                [fetch_future, timeout_task], 
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Check if fetch completed
            if fetch_future in done:
                result = fetch_future.result()
                self.logger.debug(f"Fetch completed successfully, got {len(result[0]) if result and len(result) > 0 else 0} PRs")
                return result
            else:
                self.logger.warning(f"PR fetch timed out after {timeout} seconds")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching PRs: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def _watch_loop_with_countdown(self, fetch_prs_func, options: Dict[str, Any]) -> None:
        """Enhanced watch loop with countdown timer and keyboard handling."""
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while not self._shutdown_requested:
            try:
                # Update status to connecting
                self.live_manager.update_status("connecting")
                
                # Reset spinner countdown
                self.spinner_manager.reset_countdown()
                
                # Fetch PR data
                pr_data = await self._fetch_prs_with_timeout(fetch_prs_func, options)
                
                if pr_data is not None:
                    try:
                        # Successful fetch - unpack the tuple
                        prs, display_modes = pr_data
                        consecutive_errors = 0
                        
                        # Detect changes
                        changeset = self.cache.detect_changes(prs)
                        
                        # Log changes if any
                        if changeset.has_changes():
                            self.logger.info(f"Detected changes: {len(changeset.changes)} updates, "
                                           f"{len(changeset.new_prs)} new, {len(changeset.removed_prs)} removed")
                        
                        # Get current display modes from runtime manager
                        current_modes = self.runtime_modes.get_current_modes() if self.runtime_modes else self._extract_display_modes(options)
                        
                        # Store data for countdown loop to display (avoids concurrent updates)
                        self._last_prs = prs
                        self._last_modes = current_modes
                        self._last_changeset = changeset
                        
                    except Exception as e:
                        self.logger.error(f"Error processing PR data: {e}")
                        consecutive_errors += 1
                    
                else:
                    # Fetch failed
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        raise Exception(f"Failed to fetch PRs {consecutive_errors} times in a row")
                
                # Wait for next update with countdown and keyboard processing
                await self._wait_with_countdown_and_keyboard()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                error_msg = str(e)
                self.logger.error(f"Error in enhanced watch loop (attempt {consecutive_errors}): {error_msg}")
                self.live_manager.update_status("error", error_msg)
                
                if consecutive_errors >= max_consecutive_errors:
                    raise Exception(f"Too many consecutive errors: {error_msg}")
                
                # Wait before retrying (exponential backoff)
                wait_time = min(60, 5 * (2 ** (consecutive_errors - 1)))
                await asyncio.sleep(wait_time)
    
    async def _wait_with_countdown_and_keyboard(self) -> None:
        """Wait for next update while handling countdown display and keyboard input."""
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + self.config.interval
        
        while not self._shutdown_requested:
            current_time = asyncio.get_event_loop().time()
            remaining_seconds = max(0, int(end_time - current_time))
            
            if remaining_seconds <= 0:
                break
            
            # Process keyboard commands and check if display update is needed
            mode_changed = await self._process_keyboard_commands()
            
            # Single consolidated display update per loop iteration
            if self.runtime_modes and hasattr(self, '_last_prs') and hasattr(self, '_last_modes'):
                try:
                    current_modes = self.runtime_modes.get_current_modes()
                    changeset = getattr(self, '_last_changeset', None)
                    # Use full update_display to ensure consistency
                    self.live_manager.update_display(
                        self._last_prs, current_modes, changeset, remaining_seconds
                    )
                except Exception as e:
                    self.logger.error(f"Error updating display: {e}")
            
            # Sleep briefly before next update
            await asyncio.sleep(1.0)  # Update countdown every second to reduce flickering
    
    async def _process_keyboard_commands(self) -> bool:
        """
        Process keyboard commands from the command queue.
        
        Returns:
            bool: True if a display update is needed, False otherwise
        """
        if not self.command_queue:
            return False
        
        display_update_needed = False
        
        try:
            while not self.command_queue.empty():
                try:
                    command_type, command_data = self.command_queue.get_nowait()
                    
                    if command_type == 'quit':
                        self._shutdown_requested = True
                        return False
                    
                    elif command_type == 'mode_change' and isinstance(command_data, ModeChangeCommand):
                        # Handle mode change - don't update display here, just flag it
                        if self.runtime_modes:
                            # Mode was already changed by the keyboard handler
                            display_update_needed = True
                            self.logger.info(f"Mode changed: {command_data.feature} -> {command_data.new_mode}")
                    
                except queue.Empty:
                    break
                except Exception as e:
                    self.logger.error(f"Error processing keyboard command: {e}")
        
        except Exception as e:
            self.logger.error(f"Error in keyboard command processing: {e}")
        
        return display_update_needed
    
    async def _wait_for_next_update(self) -> None:
        """Wait for the next update interval (legacy method)."""
        try:
            await asyncio.sleep(self.config.interval)
        except asyncio.CancelledError:
            pass
    
    def _extract_display_modes(self, options: Dict[str, Any]) -> Dict[str, str]:
        """Extract display modes from options dictionary."""
        # Default modes
        display_modes = {
            "checks": "short",
            "reviews": "short", 
            "labels": "short",
            "pr_url": "none",
            "branch": "none",
            "author": "short"
        }
        
        # Override with options if provided
        for key in display_modes:
            if key in options and options[key] is not None:
                display_modes[key] = options[key]
        
        return display_modes
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown")
            self._shutdown_requested = True
        
        # Handle common termination signals
        for sig in [signal.SIGINT, signal.SIGTERM]:
            try:
                signal.signal(sig, signal_handler)
            except ValueError:
                # Signal not supported on this platform
                pass
    
    async def _shutdown(self) -> None:
        """Perform graceful shutdown."""
        self.is_running = False
        
        try:
            # Stop keyboard handler
            if self.keyboard_handler:
                self.keyboard_handler.stop()
                self.keyboard_handler = None
            
            # Stop spinner manager
            if self.spinner_manager:
                self.spinner_manager.stop_progress()
            
            # Stop live display
            self.live_manager.stop_live_display()
            
            # Clear cache to free memory
            self.cache.clear_cache()
            
            # Clear command queue
            while not self.command_queue.empty():
                try:
                    self.command_queue.get_nowait()
                except queue.Empty:
                    break
            
            self.logger.info("Enhanced watch mode shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def stop(self) -> None:
        """Request shutdown of watch mode."""
        self._shutdown_requested = True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get watch mode statistics."""
        cache_stats = self.cache.get_cache_stats()
        watch_state = self.live_manager.get_watch_state()
        
        return {
            "is_running": self.is_running,
            "update_count": watch_state.update_count,
            "last_update": watch_state.last_update,
            "connection_status": watch_state.connection_status,
            "cache_stats": cache_stats,
            "config": {
                "interval": self.config.interval,
                "show_update_time": self.config.show_update_time,
                "highlight_changes": self.config.highlight_changes
            }
        }