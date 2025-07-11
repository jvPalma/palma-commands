"""
Screen classes for the PRS TUI application.

This module provides different screen layouts and navigation patterns
for various application states and user workflows.
"""

from .main_screen import MainScreen, CompactMainScreen
from .detail_screen import DetailScreen
from .settings_screen import SettingsScreen  
from .help_screen import HelpScreen

__all__ = [
    "MainScreen",
    "CompactMainScreen", 
    "DetailScreen",
    "SettingsScreen",
    "HelpScreen"
]