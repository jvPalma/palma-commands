"""
Unit tests for RuntimeModeManager.
"""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from ..runtime_modes import RuntimeModeManager


class TestRuntimeModeManager:
    """Test cases for RuntimeModeManager class."""
    
    def test_init_with_valid_modes(self):
        """Test initialization with valid modes."""
        initial_modes = {"checks": "normal", "reviews": "short", "labels": "none"}
        manager = RuntimeModeManager(initial_modes)
        
        assert manager.get_current_modes() == initial_modes
    
    def test_init_with_invalid_feature(self):
        """Test initialization with invalid feature name."""
        with pytest.raises(ValueError, match="Invalid feature 'invalid'"):
            RuntimeModeManager({"invalid": "normal"})
    
    def test_init_with_invalid_mode(self):
        """Test initialization with invalid mode."""
        with pytest.raises(ValueError, match="Invalid mode 'invalid'"):
            RuntimeModeManager({"checks": "invalid"})
    
    def test_init_fills_missing_features(self):
        """Test that missing features are filled with default mode."""
        manager = RuntimeModeManager({"checks": "short"})
        modes = manager.get_current_modes()
        
        assert modes["checks"] == "short"
        assert modes["reviews"] == "normal"  # Default
        assert modes["labels"] == "normal"   # Default
    
    def test_cycle_mode_progression(self):
        """Test that cycle_mode progresses through modes correctly."""
        manager = RuntimeModeManager({"checks": "none"})
        
        # Test full cycle: none → short → normal → long → none
        assert manager.cycle_mode("checks") == "short"
        assert manager.cycle_mode("checks") == "normal"
        assert manager.cycle_mode("checks") == "long"
        assert manager.cycle_mode("checks") == "none"
    
    def test_cycle_mode_invalid_feature(self):
        """Test cycling with invalid feature."""
        manager = RuntimeModeManager({})
        
        with pytest.raises(ValueError, match="Invalid feature 'invalid'"):
            manager.cycle_mode("invalid")
    
    def test_get_mode(self):
        """Test getting mode for specific feature."""
        manager = RuntimeModeManager({"checks": "long"})
        
        assert manager.get_mode("checks") == "long"
        assert manager.get_mode("reviews") == "normal"  # Default
    
    def test_get_mode_invalid_feature(self):
        """Test getting mode for invalid feature."""
        manager = RuntimeModeManager({})
        
        with pytest.raises(ValueError, match="Invalid feature 'invalid'"):
            manager.get_mode("invalid")
    
    def test_set_mode(self):
        """Test setting mode for feature."""
        manager = RuntimeModeManager({})
        
        manager.set_mode("checks", "long")
        assert manager.get_mode("checks") == "long"
    
    def test_set_mode_invalid_feature(self):
        """Test setting mode for invalid feature."""
        manager = RuntimeModeManager({})
        
        with pytest.raises(ValueError, match="Invalid feature 'invalid'"):
            manager.set_mode("invalid", "normal")
    
    def test_set_mode_invalid_mode(self):
        """Test setting invalid mode."""
        manager = RuntimeModeManager({})
        
        with pytest.raises(ValueError, match="Invalid mode 'invalid'"):
            manager.set_mode("checks", "invalid")
    
    def test_get_next_mode(self):
        """Test getting next mode without changing current mode."""
        manager = RuntimeModeManager({"checks": "short"})
        
        next_mode = manager.get_next_mode("checks")
        assert next_mode == "normal"
        assert manager.get_mode("checks") == "short"  # Unchanged
    
    def test_get_next_mode_wraps_around(self):
        """Test that get_next_mode wraps around from last to first."""
        manager = RuntimeModeManager({"checks": "long"})
        
        next_mode = manager.get_next_mode("checks")
        assert next_mode == "none"
    
    def test_get_next_mode_invalid_feature(self):
        """Test getting next mode for invalid feature."""
        manager = RuntimeModeManager({})
        
        with pytest.raises(ValueError, match="Invalid feature 'invalid'"):
            manager.get_next_mode("invalid")
    
    def test_reset_to_defaults(self):
        """Test resetting all modes to defaults."""
        manager = RuntimeModeManager({"checks": "none", "reviews": "long", "labels": "short"})
        
        manager.reset_to_defaults()
        modes = manager.get_current_modes()
        
        assert all(mode == "normal" for mode in modes.values())
    
    def test_get_current_modes_returns_copy(self):
        """Test that get_current_modes returns a copy, not reference."""
        manager = RuntimeModeManager({"checks": "short"})
        
        modes1 = manager.get_current_modes()
        modes2 = manager.get_current_modes()
        
        # Modify one copy
        modes1["checks"] = "long"
        
        # Other copy should be unchanged
        assert modes2["checks"] == "short"
        # Manager should be unchanged
        assert manager.get_mode("checks") == "short"
    
    def test_thread_safety_concurrent_cycles(self):
        """Test thread safety with concurrent cycle operations."""
        manager = RuntimeModeManager({})
        results = []
        
        def cycle_feature(feature, iterations):
            for _ in range(iterations):
                result = manager.cycle_mode(feature)
                results.append((feature, result))
                time.sleep(0.001)  # Small delay to increase chance of race conditions
        
        # Run concurrent cycles on different features
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(cycle_feature, "checks", 10),
                executor.submit(cycle_feature, "reviews", 10),
                executor.submit(cycle_feature, "labels", 10)
            ]
            
            for future in futures:
                future.result()
        
        # Check that we got expected number of results
        assert len(results) == 30
        
        # Check that each feature cycled independently
        checks_results = [r[1] for r in results if r[0] == "checks"]
        reviews_results = [r[1] for r in results if r[0] == "reviews"]
        labels_results = [r[1] for r in results if r[0] == "labels"]
        
        assert len(checks_results) == 10
        assert len(reviews_results) == 10
        assert len(labels_results) == 10
    
    def test_thread_safety_concurrent_reads_writes(self):
        """Test thread safety with concurrent reads and writes."""
        manager = RuntimeModeManager({"checks": "normal"})
        read_results = []
        write_results = []
        
        def reader():
            for _ in range(50):
                modes = manager.get_current_modes()
                read_results.append(modes)
                time.sleep(0.001)
        
        def writer():
            for i in range(25):
                new_mode = manager.cycle_mode("checks")
                write_results.append(new_mode)
                time.sleep(0.002)
        
        # Run concurrent readers and writers
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(reader),
                executor.submit(reader),
                executor.submit(writer),
                executor.submit(writer)
            ]
            
            for future in futures:
                future.result()
        
        # Verify we got expected number of operations
        assert len(read_results) == 100
        assert len(write_results) == 50
        
        # Verify all read results are valid
        for modes in read_results:
            assert "checks" in modes
            assert "reviews" in modes
            assert "labels" in modes
            assert modes["checks"] in RuntimeModeManager.MODE_CYCLE
    
    def test_string_representation(self):
        """Test string representation of manager."""
        manager = RuntimeModeManager({"checks": "long", "reviews": "none", "labels": "short"})
        
        str_repr = str(manager)
        assert "RuntimeModeManager" in str_repr
        assert "checks=long" in str_repr
        assert "reviews=none" in str_repr
        assert "labels=short" in str_repr
    
    def test_mode_cycle_constants(self):
        """Test that mode cycle constants are correct."""
        expected_modes = ["none", "short", "normal", "long"]
        assert RuntimeModeManager.MODE_CYCLE == expected_modes
    
    def test_valid_features_constants(self):
        """Test that valid features constants are correct."""
        expected_features = {"checks", "reviews", "labels"}
        assert RuntimeModeManager.VALID_FEATURES == expected_features
    
    def test_reentrant_lock_behavior(self):
        """Test that reentrant lock allows nested calls from same thread."""
        manager = RuntimeModeManager({})
        
        def nested_operations():
            # This should work without deadlock due to reentrant lock
            manager.set_mode("checks", "long")
            current_modes = manager.get_current_modes()
            manager.cycle_mode("reviews")
            return current_modes
        
        # Should complete without hanging
        result = nested_operations()
        assert result["checks"] == "long"
        assert manager.get_mode("reviews") == "long"  # Cycled from default "normal" to "long"