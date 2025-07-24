"""
Display module for PR rendering functionality.

This module provides organized rendering capabilities for PR display:
- Panel rendering and orchestration
- Feature-specific rendering functions  
- Display configuration and mode resolution
"""

from .panel_renderer import render_pr_panel, render_ignored_count
from .feature_renderers import (
    render_summary_status,
    render_url_info,
    render_branch_info,
    render_checks_detail,
    render_reviews_detail,
    render_labels_detail
)
from .display_config import resolve_display_modes, get_panel_color

__all__ = [
    "render_pr_panel",
    "render_ignored_count", 
    "render_summary_status",
    "render_url_info",
    "render_branch_info",
    "render_checks_detail",
    "render_reviews_detail",
    "render_labels_detail",
    "resolve_display_modes",
    "get_panel_color"
]