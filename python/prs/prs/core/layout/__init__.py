"""
PRS Columnar Layout System

This module provides a sophisticated columnar layout system for displaying
GitHub pull request information in a structured, readable format.

Layout Structure:
- Line 1: Always visible with PR number and title
- Line 2: Short mode data in fixed-size columns with emojis/colors  
- Lines 3-9: Columnar layout with normal mode (first column) and long mode data

Key Features:
- Responsive layout that adapts to terminal width
- Rich text formatting and color support
- Graceful overflow handling with truncation indicators
- Configurable column spacing and sizing
- Support for variable numbers of columns based on available data

Main Components:
- column_formatter: Functions to format content into columns
- layout_calculator: Functions to calculate column widths and positions  
- display_builder: Main functions to build the complete display

Usage:
    from prs.core.layout import build_pr_display, print_pr_display
    
    # Build display string
    display_text = build_pr_display(pr)
    
    # Print directly to console
    print_pr_display(pr)
    
    # Multiple PRs
    display_text = build_multiple_prs_display(prs)
"""

from .display_builder import (
    build_pr_display,
    build_multiple_prs_display,
    build_compact_display,
    build_detailed_display,
    print_pr_display,
    print_multiple_prs_display,
    get_display_preview
)

from .column_formatter import (
    format_pr_line1,
    format_pr_line2_short,
    format_normal_mode_data,
    format_long_mode_data,
    truncate_text,
    pad_text,
    get_display_width
)

from .layout_calculator import (
    get_terminal_width,
    calculate_optimal_column_widths,
    get_layout_config
)

__all__ = [
    # Main display functions
    "build_pr_display",
    "build_multiple_prs_display", 
    "build_compact_display",
    "build_detailed_display",
    "print_pr_display",
    "print_multiple_prs_display",
    "get_display_preview",
    
    # Formatting functions
    "format_pr_line1",
    "format_pr_line2_short", 
    "format_normal_mode_data",
    "format_long_mode_data",
    "truncate_text",
    "pad_text",
    "get_display_width",
    
    # Layout calculation functions
    "get_terminal_width",
    "calculate_optimal_column_widths",
    "get_layout_config"
]

# Version info
__version__ = "1.0.0"
__author__ = "PRS Layout System"
__description__ = "Columnar layout system for GitHub pull request displays"