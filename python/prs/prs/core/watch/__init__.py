"""
Watch module for PRS CLI - Real-time PR monitoring

This module provides watch functionality for continuous monitoring of PR status
with smooth, flicker-free updates using Rich.Live display.
"""

from .watch_controller import WatchController
from .pr_cache import PRStateCache
from .diff_engine import DiffEngine, ChangeSet
from .live_manager import LiveDisplayManager
from .watch_types import WatchConfig, PRSnapshot

__all__ = [
    'WatchController',
    'PRStateCache', 
    'DiffEngine',
    'ChangeSet',
    'LiveDisplayManager',
    'WatchConfig',
    'PRSnapshot'
]