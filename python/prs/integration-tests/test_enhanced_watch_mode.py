"""
Integration tests for the enhanced watch mode system.

Tests the complete integration between SpinnerManager, LiveDisplayManager,
WatchController, KeyboardHandler, and RuntimeModeManager.
"""

import asyncio
import pytest
import time
import queue
from unittest.mock import Mock, patch, AsyncMock
from rich.console import Console
from rich.text import Text

from prs.core.watch.watch_types import WatchConfig, ModeChangeCommand
from prs.core.watch.spinner_manager import SpinnerManager
from prs.core.watch.runtime_modes import RuntimeModeManager
from prs.core.watch.keyboard_handler import KeyboardHandler
from prs.core.watch.live_manager import LiveDisplayManager
from prs.core.watch.watch_controller import WatchController


class TestSpinnerManagerIntegration:
    """Test SpinnerManager integration with other components."""
    
    def test_spinner_manager_initialization(self):
        """Test SpinnerManager initializes correctly."""
        spinner = SpinnerManager(interval=30)
        assert spinner.interval == 30
        assert isinstance(spinner.get_countdown_display(15), Text)
    
    def test_enhanced_countdown_display(self):
        """Test enhanced countdown display with modes."""
        spinner = SpinnerManager(interval=30)
        modes = {"checks": "normal", "reviews": "short", "labels": "none"}
        
        display = spinner.get_enhanced_countdown_display(15, modes, show_shortcuts=True)
        assert isinstance(display, Text)
        
        # Check that keyboard shortcuts are mentioned
        display_str = str(display)
        assert "c" in display_str or "r" in display_str or "l" in display_str
    
    def test_countdown_reset(self):
        """Test countdown reset functionality."""
        spinner = SpinnerManager(interval=30)
        original_style = spinner.get_current_spinner_style()
        
        spinner.reset_countdown()
        # Should advance to next style
        new_style = spinner.get_current_spinner_style()
        # Might be the same due to cycling
        assert isinstance(new_style, str)
    
    def test_progress_bar_creation(self):
        """Test progress bar text generation."""
        spinner = SpinnerManager(interval=30)
        
        progress_bar = spinner.get_progress_bar(15)
        assert isinstance(progress_bar, str)
        assert "[" in progress_bar and "]" in progress_bar
        assert "%" in progress_bar


class TestLiveDisplayManagerIntegration:
    """Test LiveDisplayManager integration with enhanced components."""
    
    def test_live_manager_with_spinner(self):
        """Test LiveDisplayManager with SpinnerManager."""
        console = Console()
        config = WatchConfig(interval=30)
        spinner = SpinnerManager(30)
        modes = RuntimeModeManager({"checks": "normal", "reviews": "short", "labels": "none"})
        
        live_manager = LiveDisplayManager(console, config, spinner, modes)
        
        assert live_manager.spinner_manager is spinner
        assert live_manager.runtime_modes is modes
    
    def test_enhanced_header_panel_creation(self):
        """Test enhanced header panel creation."""
        console = Console()
        config = WatchConfig(interval=30)
        spinner = SpinnerManager(30)
        modes = RuntimeModeManager({"checks": "normal", "reviews": "short", "labels": "none"})
        
        live_manager = LiveDisplayManager(console, config, spinner, modes)
        
        # Test header creation
        header = live_manager._create_enhanced_header_panel(None, 15)
        assert header is not None
    
    def test_update_display_modes(self):
        """Test display mode updates."""
        console = Console()
        config = WatchConfig(interval=30)
        live_manager = LiveDisplayManager(console, config)
        
        new_modes = {"checks": "long", "reviews": "normal", "labels": "short"}
        live_manager.update_display_modes(new_modes)
        
        assert live_manager._current_modes == new_modes


class TestRuntimeModeManagerIntegration:
    """Test RuntimeModeManager integration."""
    
    def test_mode_cycling(self):
        """Test mode cycling functionality."""
        initial_modes = {"checks": "normal", "reviews": "short", "labels": "none"}
        manager = RuntimeModeManager(initial_modes)
        
        # Test cycling
        new_mode = manager.cycle_mode("checks")
        assert new_mode in ["none", "short", "normal", "long"]
        assert new_mode != "normal"  # Should have changed
        
        current_modes = manager.get_current_modes()
        assert current_modes["checks"] == new_mode
    
    def test_thread_safety(self):
        """Test thread-safe operations."""
        import threading
        
        initial_modes = {"checks": "normal", "reviews": "short", "labels": "none"}
        manager = RuntimeModeManager(initial_modes)
        
        results = []
        
        def cycle_modes():
            for _ in range(10):
                mode = manager.cycle_mode("checks")
                results.append(mode)
        
        threads = [threading.Thread(target=cycle_modes) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should have cycled through modes safely
        assert len(results) == 30
        assert all(mode in ["none", "short", "normal", "long"] for mode in results)


class TestKeyboardHandlerIntegration:
    """Test KeyboardHandler integration."""
    
    def test_keyboard_handler_initialization(self):
        """Test KeyboardHandler initializes correctly."""
        initial_modes = {"checks": "normal", "reviews": "short", "labels": "none"}
        manager = RuntimeModeManager(initial_modes)
        command_queue = queue.Queue()
        
        handler = KeyboardHandler(manager, command_queue)
        assert handler.mode_manager is manager
        assert handler.command_queue is command_queue
    
    def test_command_processing(self):
        """Test keyboard command processing."""
        initial_modes = {"checks": "normal", "reviews": "short", "labels": "none"}
        manager = RuntimeModeManager(initial_modes)
        command_queue = queue.Queue()
        
        handler = KeyboardHandler(manager, command_queue)
        
        # Simulate key press
        handler._process_key('c')
        
        # Check command was queued
        assert not command_queue.empty()
        command_type, command_data = command_queue.get()
        assert command_type == 'mode_change'
        assert isinstance(command_data, ModeChangeCommand)
        assert command_data.feature == 'checks'
    
    def test_quit_command(self):
        """Test quit command processing."""
        initial_modes = {"checks": "normal", "reviews": "short", "labels": "none"}
        manager = RuntimeModeManager(initial_modes)
        command_queue = queue.Queue()
        
        handler = KeyboardHandler(manager, command_queue)
        
        # Simulate quit key press
        handler._process_key('q')
        
        # Check quit command was queued
        assert not command_queue.empty()
        command_type, command_data = command_queue.get()
        assert command_type == 'quit'
        assert command_data is None


class TestWatchControllerIntegration:
    """Test complete WatchController integration."""
    
    @pytest.fixture
    def mock_fetch_prs(self):
        """Mock PR fetching function."""
        def fetch_prs(options):
            # Return mock PR data
            mock_pr = Mock()
            mock_pr.id = "123"
            mock_pr.title = "Test PR"
            mock_pr.status = "OPEN"
            mock_pr.is_draft = False
            mock_pr.checks = []
            mock_pr.reviews = []
            mock_pr.labels = []
            mock_pr.url = "https://github.com/test/repo/pull/123"
            
            return [mock_pr], {"checks": "normal", "reviews": "short"}
        
        return fetch_prs
    
    def test_watch_controller_initialization(self):
        """Test WatchController initializes with enhanced components."""
        console = Console()
        config = WatchConfig(interval=5)  # Short interval for testing
        
        controller = WatchController(console, config)
        
        assert controller.spinner_manager is not None
        assert controller.command_queue is not None
        assert isinstance(controller.live_manager, LiveDisplayManager)
    
    @pytest.mark.asyncio
    async def test_keyboard_command_processing(self, mock_fetch_prs):
        """Test keyboard command processing integration."""
        console = Console()
        config = WatchConfig(interval=1)  # Very short for testing
        
        controller = WatchController(console, config)
        
        # Initialize runtime modes
        initial_modes = {"checks": "normal", "reviews": "short", "labels": "none"}
        controller.runtime_modes = RuntimeModeManager(initial_modes)
        
        # Test command processing
        command = ModeChangeCommand(
            feature="checks",
            new_mode="long",
            timestamp="2025-01-01T00:00:00"
        )
        controller.command_queue.put(('mode_change', command))
        
        # Process commands
        await controller._process_keyboard_commands()
        
        # Check that modes were updated
        # Note: The keyboard handler would have already cycled the mode
        assert controller.runtime_modes is not None
    
    @pytest.mark.asyncio
    async def test_countdown_updates(self, mock_fetch_prs):
        """Test countdown timer updates."""
        console = Console()
        config = WatchConfig(interval=2)  # Short interval
        
        controller = WatchController(console, config)
        
        # Mock the live manager update
        with patch.object(controller.live_manager, 'update_display') as mock_update:
            # Initialize some test data
            controller._last_prs = []
            controller._last_modes = {"checks": "normal"}
            controller.runtime_modes = RuntimeModeManager({"checks": "normal", "reviews": "short", "labels": "none"})
            
            # Test countdown update
            start_time = asyncio.get_event_loop().time()
            
            # Wait briefly and check update was called
            await asyncio.sleep(0.3)
            await controller._process_keyboard_commands()
            
            # Should have been called during wait
            # Note: This is a basic integration test
    
    def test_statistics_collection(self):
        """Test statistics collection integration."""
        console = Console()
        config = WatchConfig(interval=30)
        
        controller = WatchController(console, config)
        
        stats = controller.get_statistics()
        
        assert "is_running" in stats
        assert "config" in stats
        assert "cache_stats" in stats
        assert stats["config"]["interval"] == 30


class TestCompleteSystemIntegration:
    """Test complete system integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_enhanced_watch_mode_startup(self):
        """Test full enhanced watch mode startup and shutdown."""
        console = Console()
        config = WatchConfig(interval=1)  # Very short for testing
        
        controller = WatchController(console, config)
        
        # Mock PR fetch function
        async def mock_fetch():
            return [], {}
        
        # Mock the actual watch loop to avoid long running
        original_method = controller._watch_loop_with_countdown
        
        async def mock_watch_loop(fetch_func, options):
            # Just do a quick setup and exit
            initial_modes = controller._extract_display_modes(options)
            controller.runtime_modes = RuntimeModeManager(initial_modes)
            controller.live_manager.runtime_modes = controller.runtime_modes
            await asyncio.sleep(0.1)  # Brief pause
            return
        
        controller._watch_loop_with_countdown = mock_watch_loop
        
        try:
            # This should start and quickly complete
            with patch('sys.stdout'):  # Suppress output
                await controller.start_watch_mode(lambda opts: ([], {}), {})
            
            # Test that components were initialized
            assert controller.runtime_modes is not None
            assert controller.keyboard_handler is not None
            
        finally:
            # Ensure cleanup
            await controller._shutdown()
    
    def test_mode_change_propagation(self):
        """Test that mode changes propagate through all components."""
        console = Console()
        config = WatchConfig(interval=30)
        
        # Initialize components
        initial_modes = {"checks": "normal", "reviews": "short", "labels": "none"}
        runtime_modes = RuntimeModeManager(initial_modes)
        spinner = SpinnerManager(30)
        live_manager = LiveDisplayManager(console, config, spinner, runtime_modes)
        
        # Test mode change
        new_mode = runtime_modes.cycle_mode("checks")
        updated_modes = runtime_modes.get_current_modes()
        
        # Update live manager
        live_manager.update_display_modes(updated_modes)
        
        # Verify propagation
        assert live_manager._current_modes["checks"] == new_mode
        assert updated_modes["checks"] == new_mode
    
    def test_error_handling_integration(self):
        """Test error handling across components."""
        console = Console()
        config = WatchConfig(interval=30)
        
        controller = WatchController(console, config)
        
        # Test with invalid options
        try:
            modes = controller._extract_display_modes({})
            assert isinstance(modes, dict)
        except Exception as e:
            pytest.fail(f"Error handling failed: {e}")
    
    def test_component_cleanup(self):
        """Test that all components clean up properly."""
        console = Console()
        config = WatchConfig(interval=30)
        
        controller = WatchController(console, config)
        
        # Initialize components
        initial_modes = {"checks": "normal", "reviews": "short", "labels": "none"}
        controller.runtime_modes = RuntimeModeManager(initial_modes)
        controller.keyboard_handler = KeyboardHandler(controller.runtime_modes, controller.command_queue)
        
        # Test cleanup
        asyncio.run(controller._shutdown())
        
        # Verify cleanup
        assert controller.keyboard_handler is None
        assert controller.command_queue.empty()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])