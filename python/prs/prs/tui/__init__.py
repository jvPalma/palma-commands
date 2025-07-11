"""
TUI (Terminal User Interface) module for PRS.

This module provides an interactive terminal interface for browsing
pull requests with real-time updates and advanced features.
"""

from .app import PRSApp, run_tui_app

__all__ = [
    "PRSApp",
    "run_tui_app",
]