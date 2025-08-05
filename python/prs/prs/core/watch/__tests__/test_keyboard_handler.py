"""
Unit tests for KeyboardHandler.
"""

import pytest
import queue
import threading
import time
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime

from ..keyboard_handler import KeyboardHandler
from ..runtime_modes import RuntimeModeManager
from ..watch_types import ModeChangeCommand


class TestKeyboardHandler:
    """Test cases for KeyboardHandler class."""
    
    @pytest.fixture
    def mode_manager(self):
        """Create a RuntimeModeManager for testing."""
        return RuntimeModeManager({"checks": "normal", "reviews": "short", "labels": "none"})
    
    @pytest.fixture
    def command_queue(self):
        """Create a command queue for testing."""
        return queue.Queue()
    
    @pytest.fixture
    def handler(self, mode_manager, command_queue):
        """Create a KeyboardHandler for testing."""
        return KeyboardHandler(mode_manager, command_queue)
    
    def test_init(self, mode_manager, command_queue):
        """Test KeyboardHandler initialization."""
        handler = KeyboardHandler(mode_manager, command_queue)
        
        assert handler.mode_manager == mode_manager
        assert handler.command_queue == command_queue
        assert not handler.is_running()
        assert handler._thread is None
    
    def test_key_mappings(self):
        """Test that key mappings are correct."""
        expected_mappings = {
            'c': 'checks',
            'r': 'reviews',
            'l': 'labels'
        }
        assert KeyboardHandler.KEY_MAPPINGS == expected_mappings
    
    def test_start_stop(self, handler):
        """Test starting and stopping the handler."""
        assert not handler.is_running()
        
        # Mock the keyboard loop to block until stop event is set
        def mock_keyboard_loop():
            handler._stop_event.wait()
        
        with patch.object(handler, '_keyboard_loop', side_effect=mock_keyboard_loop):
            handler.start()
            # Wait for thread to actually start
            for _ in range(50):  # Wait up to 0.5 seconds
                if handler.is_running():
                    break
                time.sleep(0.01)
            assert handler.is_running()
            
            handler.stop()
            assert not handler.is_running()
    
    def test_start_already_running(self, handler):
        """Test that starting an already running handler is a no-op."""
        def mock_keyboard_loop():
            handler._stop_event.wait()
        
        with patch.object(handler, '_keyboard_loop', side_effect=mock_keyboard_loop):
            handler.start()
            # Wait for thread to actually start
            for _ in range(50):
                if handler.is_running():
                    break
                time.sleep(0.01)
            thread1 = handler._thread
            
            handler.start()  # Should be no-op
            thread2 = handler._thread
            
            assert thread1 == thread2  # Same thread
            handler.stop()
    
    def test_stop_not_running(self, handler):
        """Test that stopping a non-running handler is safe."""
        # Should not raise any exceptions
        handler.stop()
        assert not handler.is_running()
    
    def test_process_key_mode_change(self, handler):
        """Test processing keys that trigger mode changes."""
        # Test 'c' key for checks
        handler._process_key('c')
        
        # Should have queued a mode change command
        assert not handler.command_queue.empty()
        cmd_type, command = handler.command_queue.get()
        
        assert cmd_type == 'mode_change'
        assert isinstance(command, ModeChangeCommand)
        assert command.feature == 'checks'
        assert command.new_mode == 'long'  # Cycled from 'normal' to 'long'
        assert command.timestamp  # Should have timestamp
    
    def test_process_key_quit(self, handler):
        """Test processing 'q' key for quit."""
        handler._process_key('q')
        
        # Should have queued a quit command
        assert not handler.command_queue.empty()
        cmd_type, command = handler.command_queue.get()
        
        assert cmd_type == 'quit'
        assert command is None
    
    def test_process_key_invalid(self, handler):
        """Test processing invalid keys."""
        initial_size = handler.command_queue.qsize()
        
        handler._process_key('x')  # Invalid key
        
        # Should not have queued anything
        assert handler.command_queue.qsize() == initial_size
    
    def test_process_key_case_insensitive(self, handler):
        """Test that key processing is case insensitive."""
        handler._process_key('C')  # Uppercase
        
        assert not handler.command_queue.empty()
        cmd_type, command = handler.command_queue.get()
        assert command.feature == 'checks'
    
    def test_process_key_queue_full(self, handler):
        """Test handling when command queue is full."""
        # Fill the queue
        small_queue = queue.Queue(maxsize=1)
        handler.command_queue = small_queue
        small_queue.put(('dummy', None))
        
        # This should not raise an exception even with full queue
        handler._process_key('c')
        
        # Queue should still be full (command was dropped)
        assert small_queue.full()
    
    @patch('sys.platform', 'win32')
    def test_keyboard_loop_windows_detection(self, handler):
        """Test that Windows platform is detected correctly."""
        handler._is_windows = True  # Force Windows mode
        
        with patch.object(handler, '_keyboard_loop_windows') as mock_windows:
            handler._keyboard_loop()
            mock_windows.assert_called_once()
    
    @patch('sys.platform', 'linux')
    def test_keyboard_loop_unix_detection(self, handler):
        """Test that Unix platform is detected correctly."""
        handler._is_windows = False  # Force Unix mode
        
        with patch.object(handler, '_keyboard_loop_unix') as mock_unix:
            handler._keyboard_loop()
            mock_unix.assert_called_once()
    
    @patch('prs.core.watch.keyboard_handler.termios.tcgetattr')
    @patch('prs.core.watch.keyboard_handler.termios.tcsetattr')
    @patch('prs.core.watch.keyboard_handler.tty.setraw')
    @patch('prs.core.watch.keyboard_handler.select.select')
    @patch('prs.core.watch.keyboard_handler.sys.stdin')
    def test_keyboard_loop_unix_success(self, mock_stdin, mock_select, mock_setraw, 
                                       mock_tcsetattr, mock_tcgetattr, handler):
        """Test successful Unix keyboard loop."""
        # Mock terminal settings
        mock_settings = MagicMock()
        mock_tcgetattr.return_value = mock_settings
        
        # Mock select to return input available once, then stop
        def select_side_effect(*args):
            if not handler._stop_event.is_set():
                handler._stop_event.set()  # Stop after first call
                return ([mock_stdin], [], [])
            return ([], [], [])
        
        mock_select.side_effect = select_side_effect
        
        # Mock stdin to return 'c' character
        mock_stdin.read.return_value = 'c'
        
        # Run the loop
        handler._keyboard_loop_unix()
        
        # Verify terminal operations
        mock_tcgetattr.assert_called()
        mock_setraw.assert_called()
        mock_tcsetattr.assert_called()
    
    @patch('prs.core.watch.keyboard_handler.termios.tcgetattr')
    def test_keyboard_loop_unix_fallback_on_error(self, mock_tcgetattr, handler):
        """Test Unix keyboard loop falls back on terminal errors."""
        # Mock terminal error
        mock_tcgetattr.side_effect = OSError("Terminal error")
        
        with patch.object(handler, '_keyboard_loop_fallback') as mock_fallback:
            handler._keyboard_loop_unix()
            mock_fallback.assert_called_once()
    
    @patch('prs.core.watch.keyboard_handler.select.select')
    @patch('prs.core.watch.keyboard_handler.sys.stdin')
    def test_keyboard_loop_fallback(self, mock_stdin, mock_select, handler):
        """Test fallback keyboard loop."""
        # Mock select to return input available once, then stop
        def select_side_effect(*args):
            if not handler._stop_event.is_set():
                handler._stop_event.set()  # Stop after first call
                return ([mock_stdin], [], [])
            return ([], [], [])
        
        mock_select.side_effect = select_side_effect
        
        # Mock stdin to return line with 'c'
        mock_stdin.readline.return_value = 'c\n'
        
        # Run the fallback loop
        handler._keyboard_loop_fallback()
        
        # Should have processed the 'c' key
        assert not handler.command_queue.empty()
    
    def test_get_help_text(self, handler):
        """Test help text generation."""
        help_text = handler.get_help_text()
        
        assert "Keyboard Commands:" in help_text
        assert "c - Cycle checks" in help_text
        assert "r - Cycle reviews" in help_text
        assert "l - Cycle labels" in help_text
        assert "q - Quit watch mode" in help_text
    
    def test_context_manager(self, handler):
        """Test using KeyboardHandler as context manager."""
        def mock_keyboard_loop():
            handler._stop_event.wait()
        
        with patch.object(handler, '_keyboard_loop', side_effect=mock_keyboard_loop):
            with handler as h:
                assert h == handler
                # Wait for thread to actually start
                for _ in range(50):
                    if handler.is_running():
                        break
                    time.sleep(0.01)
                assert handler.is_running()
            
            # Should be stopped after exiting context
            assert not handler.is_running()
    
    def test_multiple_key_processing(self, handler):
        """Test processing multiple keys in sequence."""
        keys = ['c', 'r', 'l', 'c']
        
        for key in keys:
            handler._process_key(key)
        
        # Should have 4 commands queued
        assert handler.command_queue.qsize() == 4
        
        # Verify command sequence
        commands = []
        while not handler.command_queue.empty():
            cmd_type, command = handler.command_queue.get()
            commands.append((cmd_type, command.feature if command else None))
        
        expected = [
            ('mode_change', 'checks'),
            ('mode_change', 'reviews'), 
            ('mode_change', 'labels'),
            ('mode_change', 'checks')
        ]
        assert commands == expected
    
    def test_thread_lifecycle(self, handler):
        """Test complete thread lifecycle."""
        def mock_keyboard_loop():
            handler._stop_event.wait()
        
        with patch.object(handler, '_keyboard_loop', side_effect=mock_keyboard_loop) as mock_loop:
            # Start handler
            handler.start()
            # Wait for thread to actually start
            for _ in range(50):
                if handler.is_running():
                    break
                time.sleep(0.01)
            assert handler.is_running()
            assert handler._thread.daemon  # Should be daemon thread
            
            # Stop handler
            handler.stop()
            mock_loop.assert_called_once()
            
            # Thread should be cleaned up
            assert not handler.is_running()
            assert handler._thread is None or not handler._thread.is_alive()
    
    @patch('prs.core.watch.keyboard_handler.termios.tcsetattr')
    def test_cleanup_terminal_settings(self, mock_tcsetattr, handler):
        """Test that terminal settings are restored on cleanup."""
        # Set up mock thread to simulate running state
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        handler._thread = mock_thread
        
        mock_settings = MagicMock()
        handler._original_settings = mock_settings
        handler._is_windows = False
        
        handler.stop()
        
        # Should have restored terminal settings
        mock_tcsetattr.assert_called_once()
    
    def test_thread_safety_stop_during_loop(self, handler):
        """Test stopping handler while loop is running."""
        with patch('select.select') as mock_select:
            # Mock select to block until stop event
            def select_mock(*args):
                handler._stop_event.wait(0.1)
                return ([], [], [])
            
            mock_select.side_effect = select_mock
            
            # Start handler
            handler.start()
            time.sleep(0.05)  # Let it start
            
            # Stop should complete quickly
            start_time = time.time()
            handler.stop()
            stop_time = time.time()
            
            # Should stop within reasonable time
            assert stop_time - start_time < 2.0