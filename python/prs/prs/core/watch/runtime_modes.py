"""
Runtime mode management for enhanced watch mode.

Provides thread-safe management of verbosity modes for different PR features
with support for runtime cycling through modes.
"""

import threading
from typing import Dict, List
from datetime import datetime


class RuntimeModeManager:
    """
    Thread-safe manager for runtime verbosity mode changes.
    
    Manages the current verbosity modes for features (checks, reviews, labels)
    and provides methods to cycle through modes safely from multiple threads.
    """
    
    # Available verbosity modes in cycle order
    MODE_CYCLE = ["none", "short", "normal", "long"]
    
    # Valid features that can have mode changes
    VALID_FEATURES = {"checks", "reviews", "labels"}
    
    def __init__(self, initial_modes: Dict[str, str]):
        """
        Initialize the runtime mode manager.
        
        Args:
            initial_modes: Dictionary mapping feature names to initial verbosity modes
                         e.g., {"checks": "normal", "reviews": "short", "labels": "none"}
        """
        self._lock = threading.RLock()  # Re-entrant lock for nested calls
        self._modes = {}
        
        # Validate and set initial modes
        for feature, mode in initial_modes.items():
            if feature not in self.VALID_FEATURES:
                raise ValueError(f"Invalid feature '{feature}'. Valid features: {self.VALID_FEATURES}")
            if mode not in self.MODE_CYCLE:
                raise ValueError(f"Invalid mode '{mode}'. Valid modes: {self.MODE_CYCLE}")
            self._modes[feature] = mode
        
        # Ensure all valid features have a mode set
        for feature in self.VALID_FEATURES:
            if feature not in self._modes:
                self._modes[feature] = "normal"  # Default mode
    
    def cycle_mode(self, feature: str) -> str:
        """
        Cycle to the next verbosity mode for the specified feature.
        
        Cycles through modes in order: none → short → normal → long → none
        
        Args:
            feature: The feature to cycle ("checks", "reviews", or "labels")
            
        Returns:
            The new mode after cycling
            
        Raises:
            ValueError: If feature is not valid
        """
        if feature not in self.VALID_FEATURES:
            raise ValueError(f"Invalid feature '{feature}'. Valid features: {self.VALID_FEATURES}")
        
        with self._lock:
            current_mode = self._modes[feature]
            current_index = self.MODE_CYCLE.index(current_mode)
            next_index = (current_index + 1) % len(self.MODE_CYCLE)
            new_mode = self.MODE_CYCLE[next_index]
            self._modes[feature] = new_mode
            return new_mode
    
    def get_current_modes(self) -> Dict[str, str]:
        """
        Get a copy of the current modes for all features.
        
        Returns:
            Dictionary mapping feature names to their current verbosity modes
        """
        with self._lock:
            return self._modes.copy()
    
    def get_mode(self, feature: str) -> str:
        """
        Get the current mode for a specific feature.
        
        Args:
            feature: The feature to query
            
        Returns:
            The current verbosity mode for the feature
            
        Raises:
            ValueError: If feature is not valid
        """
        if feature not in self.VALID_FEATURES:
            raise ValueError(f"Invalid feature '{feature}'. Valid features: {self.VALID_FEATURES}")
        
        with self._lock:
            return self._modes[feature]
    
    def set_mode(self, feature: str, mode: str) -> None:
        """
        Set the mode for a specific feature.
        
        Args:
            feature: The feature to set mode for
            mode: The verbosity mode to set
            
        Raises:
            ValueError: If feature or mode is not valid
        """
        if feature not in self.VALID_FEATURES:
            raise ValueError(f"Invalid feature '{feature}'. Valid features: {self.VALID_FEATURES}")
        if mode not in self.MODE_CYCLE:
            raise ValueError(f"Invalid mode '{mode}'. Valid modes: {self.MODE_CYCLE}")
        
        with self._lock:
            self._modes[feature] = mode
    
    def get_next_mode(self, feature: str) -> str:
        """
        Get the next mode in the cycle for a feature without changing it.
        
        Args:
            feature: The feature to query
            
        Returns:
            The next mode that would be set if cycle_mode() was called
            
        Raises:
            ValueError: If feature is not valid
        """
        if feature not in self.VALID_FEATURES:
            raise ValueError(f"Invalid feature '{feature}'. Valid features: {self.VALID_FEATURES}")
        
        with self._lock:
            current_mode = self._modes[feature]
            current_index = self.MODE_CYCLE.index(current_mode)
            next_index = (current_index + 1) % len(self.MODE_CYCLE)
            return self.MODE_CYCLE[next_index]
    
    def reset_to_defaults(self) -> None:
        """Reset all modes to default values."""
        with self._lock:
            for feature in self.VALID_FEATURES:
                self._modes[feature] = "normal"
    
    def __str__(self) -> str:
        """String representation showing current modes."""
        with self._lock:
            modes_str = ", ".join(f"{feature}={mode}" for feature, mode in sorted(self._modes.items()))
            return f"RuntimeModeManager({modes_str})"