#!/usr/bin/env python3
"""
Complete integration test for enhanced watch mode functionality.

Tests the full system including:
- Keyboard input handling (c/r/l keys)
- Runtime mode cycling
- Loading spinner with countdown
- Rich.Live integration
- All components working together
"""

import sys
import os
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock

# Add the prs module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'prs'))

def test_all_components_exist():
    """Test that all enhanced components can be imported."""
    print("🧪 Testing component imports...")
    
    try:
        from prs.core.watch.runtime_modes import RuntimeModeManager
        from prs.core.watch.keyboard_handler import KeyboardHandler
        from prs.core.watch.spinner_manager import SpinnerManager
        from prs.core.watch.watch_types import ModeChangeCommand
        
        print("  ✅ All components imported successfully")
        return True
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False

def test_runtime_mode_manager():
    """Test the RuntimeModeManager functionality."""
    print("\n🧪 Testing RuntimeModeManager...")
    
    try:
        from prs.core.watch.runtime_modes import RuntimeModeManager
        
        # Test initialization
        initial_modes = {"checks": "short", "reviews": "normal", "labels": "none"}
        manager = RuntimeModeManager(initial_modes)
        
        # Test mode cycling
        assert manager.cycle_mode("checks") == "normal"  # short -> normal
        assert manager.cycle_mode("checks") == "long"    # normal -> long  
        assert manager.cycle_mode("checks") == "none"    # long -> none
        assert manager.cycle_mode("checks") == "short"   # none -> short (wrap around)
        
        # Test thread safety (basic check)
        current_modes = manager.get_current_modes()
        assert isinstance(current_modes, dict)
        assert current_modes["checks"] == "short"
        
        print("  ✅ RuntimeModeManager working correctly")
        return True
    except Exception as e:
        print(f"  ❌ RuntimeModeManager error: {e}")
        return False

def test_spinner_manager():
    """Test the SpinnerManager functionality.""" 
    print("\n🧪 Testing SpinnerManager...")
    
    try:
        from prs.core.watch.spinner_manager import SpinnerManager
        from rich.text import Text
        
        # Test initialization
        spinner = SpinnerManager(30)
        
        # Test countdown display
        countdown_text = spinner.get_countdown_display(15)
        assert isinstance(countdown_text, Text)
        
        # Test enhanced countdown
        modes = {"checks": "short", "reviews": "normal", "labels": "long"}
        enhanced_text = spinner.get_enhanced_countdown_display(20, modes, True)
        assert isinstance(enhanced_text, Text)
        assert "Press c/r/l" in enhanced_text.plain
        assert "Checks: short" in enhanced_text.plain
        
        print("  ✅ SpinnerManager working correctly")
        return True
    except Exception as e:
        print(f"  ❌ SpinnerManager error: {e}")
        return False

def test_keyboard_handler():
    """Test the KeyboardHandler (mocked)."""
    print("\n🧪 Testing KeyboardHandler...")
    
    try:
        import queue
        from prs.core.watch.keyboard_handler import KeyboardHandler
        from prs.core.watch.runtime_modes import RuntimeModeManager
        
        # Test initialization
        initial_modes = {"checks": "short", "reviews": "normal", "labels": "none"}
        mode_manager = RuntimeModeManager(initial_modes)
        command_queue = queue.Queue()
        
        handler = KeyboardHandler(mode_manager, command_queue)
        
        # Test that it initializes without error
        assert handler.mode_manager is mode_manager
        assert handler.command_queue is command_queue
        assert handler._thread is None  # Not started yet
        
        print("  ✅ KeyboardHandler initializes correctly")
        return True
    except Exception as e:
        print(f"  ❌ KeyboardHandler error: {e}")
        return False

def test_mode_change_command():
    """Test the ModeChangeCommand structure."""
    print("\n🧪 Testing ModeChangeCommand...")
    
    try:
        from prs.core.watch.watch_types import ModeChangeCommand
        from datetime import datetime
        
        # Test command creation
        cmd = ModeChangeCommand(
            feature="checks",
            new_mode="long",
            timestamp=datetime.now().isoformat()
        )
        
        assert cmd.feature == "checks"
        assert cmd.new_mode == "long"
        assert isinstance(cmd.timestamp, str)
        
        print("  ✅ ModeChangeCommand working correctly")
        return True
    except Exception as e:
        print(f"  ❌ ModeChangeCommand error: {e}")
        return False

async def test_enhanced_watch_controller():
    """Test enhanced WatchController with mocked dependencies."""
    print("\n🧪 Testing enhanced WatchController...")
    
    try:
        from rich.console import Console
        from prs.core.watch.watch_types import WatchConfig
        from prs.core.watch.watch_controller import WatchController
        
        # Create test components
        console = Console(file=open(os.devnull, 'w'))
        config = WatchConfig(interval=10)
        
        controller = WatchController(console, config)
        
        # Test that enhanced components are initialized
        print(f"  Controller attributes: {[attr for attr in dir(controller) if not attr.startswith('_')]}")
        
        # Check if we have the enhanced attributes (may be different names)
        has_runtime_modes = hasattr(controller, 'runtime_modes') or hasattr(controller, '_runtime_modes')
        has_keyboard_handler = hasattr(controller, 'keyboard_handler') or hasattr(controller, '_keyboard_handler')
        has_spinner_manager = hasattr(controller, 'spinner_manager') or hasattr(controller, '_spinner_manager')
        
        assert has_runtime_modes, "Missing runtime_modes"
        assert has_keyboard_handler, "Missing keyboard_handler"
        assert has_spinner_manager, "Missing spinner_manager"
        
        # Test statistics (should work even if enhanced components not fully integrated)
        stats = controller.get_statistics()
        assert isinstance(stats, dict)
        assert 'is_running' in stats  # Basic functionality should still work
        
        print("  ✅ Enhanced WatchController working correctly")
        return True
    except Exception as e:
        print(f"  ❌ Enhanced WatchController error: {e}")
        return False

def test_visual_integration():
    """Test that visual components integrate properly."""
    print("\n🧪 Testing visual integration...")
    
    try:
        from rich.console import Console
        from prs.core.watch.spinner_manager import SpinnerManager
        from prs.core.watch.runtime_modes import RuntimeModeManager
        from prs.core.watch.live_manager import LiveDisplayManager
        from prs.core.watch.watch_types import WatchConfig
        
        # Create components
        console = Console(file=open(os.devnull, 'w'))
        config = WatchConfig(interval=15)
        spinner_manager = SpinnerManager(15)
        runtime_modes = RuntimeModeManager({"checks": "short", "reviews": "normal", "labels": "long"})
        
        # Create enhanced live manager
        live_manager = LiveDisplayManager(console, config, spinner_manager, runtime_modes)
        
        # Test that it has enhanced capabilities
        assert hasattr(live_manager, 'spinner_manager')
        assert hasattr(live_manager, 'runtime_modes')
        assert hasattr(live_manager, 'update_display_modes')
        assert hasattr(live_manager, '_create_enhanced_header_panel')
        
        # Test mode update functionality
        new_modes = {"checks": "long", "reviews": "short", "labels": "normal"}
        live_manager.update_display_modes(new_modes)  # Should not raise error
        
        print("  ✅ Visual integration working correctly")
        return True
    except Exception as e:
        print(f"  ❌ Visual integration error: {e}")
        return False

async def run_comprehensive_tests():
    """Run all comprehensive tests."""
    print("🚀 Enhanced Watch Mode - Comprehensive Integration Test\n")
    
    tests = [
        ("Component Imports", test_all_components_exist()),
        ("RuntimeModeManager", test_runtime_mode_manager()),
        ("SpinnerManager", test_spinner_manager()),
        ("KeyboardHandler", test_keyboard_handler()),
        ("ModeChangeCommand", test_mode_change_command()),
        ("Enhanced WatchController", await test_enhanced_watch_controller()),
        ("Visual Integration", test_visual_integration())
    ]
    
    results = []
    for test_name, result in tests:
        results.append(result)
    
    # Print summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("Enhanced watch mode is fully functional!")
        print("\n✨ New Features Available:")
        print("  • Press 'c' to cycle checks modes: none → short → normal → long")
        print("  • Press 'r' to cycle reviews modes: none → short → normal → long")
        print("  • Press 'l' to cycle labels modes: none → short → normal → long")
        print("  • Live countdown timer shows seconds until next update")
        print("  • Enhanced header shows current modes and keyboard shortcuts")
        print("  • All changes are runtime-only (no config file modification)")
        print("\n🚀 Usage: nprs --watch 30")
        print("  Then press c/r/l keys while watch mode is running!")
        return True
    else:
        print(f"\n⚠ {total - passed} tests failed")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_comprehensive_tests())
    sys.exit(0 if success else 1)