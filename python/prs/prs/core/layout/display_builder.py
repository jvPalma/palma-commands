"""
Main display builder for the PRS columnar layout system.
"""
from typing import List, Dict, Optional
from rich.console import Console
from rich.text import Text

from prs.core.models import PullRequest
from .column_formatter import (
    format_pr_line1,
    format_pr_line2_short,
    format_normal_mode_data,
    format_long_mode_data,
    format_column_with_width,
    align_columns_by_rows,
    pad_text,
    truncate_text,
    get_display_width
)
from .layout_calculator import (
    get_terminal_width,
    calculate_line2_column_widths,
    calculate_normal_column_width,
    calculate_content_column_positions,
    fit_columns_to_terminal,
    get_layout_config
)


def build_pr_display(pr: PullRequest, options: Optional[Dict] = None) -> str:
    """
    Build the complete columnar display for a single PR.
    
    Layout:
    - Line 1: PR number and title (always visible)
    - Line 2: Short mode data in fixed columns with emojis
    - Lines 3-9: Columnar layout with normal mode (first column) and long mode data
    
    Args:
        pr: The PullRequest object to display
        options: Display options (for future extensibility)
        
    Returns:
        Formatted string ready for display
    """
    if options is None:
        options = {}
    
    # Get terminal configuration
    terminal_width = get_terminal_width()
    layout_config = get_layout_config(terminal_width)
    
    lines = []
    
    # Line 1: PR number and title (always visible)
    line1 = format_pr_line1(pr)
    lines.append(line1)
    
    # Line 2: Short mode data with emojis/colors
    line2 = build_line2_display(pr, terminal_width)
    if line2:
        lines.append(line2)
    
    # Lines 3-9: Columnar layout
    content_lines = build_content_columns_display(pr, terminal_width, layout_config)
    lines.extend(content_lines)
    
    return "\n".join(lines)


def build_line2_display(pr: PullRequest, terminal_width: int) -> str:
    """Build Line 2 with short mode data in fixed columns."""
    short_columns = format_pr_line2_short(pr)
    
    if not short_columns:
        return ""
    
    # Calculate column widths
    column_widths = calculate_line2_column_widths(short_columns, terminal_width)
    
    # Build the line
    line_parts = []
    for i, ((content, _), width) in enumerate(zip(short_columns, column_widths)):
        if i < len(column_widths):
            # Truncate and pad content to fit column width
            formatted_content = truncate_text(content, width)
            padded_content = pad_text(formatted_content, width)
            line_parts.append(padded_content)
    
    return " ".join(line_parts)


def build_content_columns_display(
    pr: PullRequest,
    terminal_width: int,
    layout_config: Dict[str, int]
) -> List[str]:
    """
    Build the columnar content display (lines 3-9).
    
    First column: normal mode data
    Additional columns: long mode data (max 7 lines with "..." if more)
    """
    # Get normal mode data (first column)
    normal_data = format_normal_mode_data(pr)
    
    # Get long mode data (additional columns)
    long_data = format_long_mode_data(pr)
    
    # Fit columns to terminal width
    max_long_columns = layout_config.get("max_long_columns", 4)
    fitted_long_data = fit_columns_to_terminal(long_data, terminal_width, max_long_columns)
    
    # Calculate column layout
    normal_width = calculate_normal_column_width(terminal_width, len(fitted_long_data))
    
    column_positions = calculate_content_column_positions(
        normal_width,
        fitted_long_data,
        terminal_width,
        layout_config.get("column_spacing", 2)
    )
    
    if not normal_data and not fitted_long_data:
        return []
    
    # Format columns with calculated widths
    formatted_columns = {}
    
    # Format normal column
    if normal_data:
        normal_position = column_positions.get("normal", (0, normal_width))
        formatted_normal = format_column_with_width(
            normal_data,
            normal_position[1],
            None  # No title for normal column
        )
        formatted_columns["normal"] = formatted_normal
    
    # Format long mode columns
    for col_name, col_data in fitted_long_data.items():
        if col_name in column_positions:
            _, width = column_positions[col_name]
            formatted_col = format_column_with_width(
                col_data,
                width,
                col_name  # Use column name as title
            )
            formatted_columns[col_name] = formatted_col
    
    # Align all columns by rows (max 7 lines for content)
    max_content_lines = 7
    aligned_rows = align_columns_by_rows(formatted_columns, max_content_lines)
    
    # Build output lines with proper positioning
    output_lines = []
    column_names = ["normal"] + [name for name in fitted_long_data.keys() if name in column_positions]
    
    for row in aligned_rows:
        line_parts = []
        current_pos = 0
        
        for i, col_name in enumerate(column_names):
            if col_name in column_positions and i < len(row):
                expected_pos, width = column_positions[col_name]
                
                # Add spacing if needed
                if current_pos < expected_pos:
                    line_parts.append(" " * (expected_pos - current_pos))
                
                # Add column content
                content = row[i] if i < len(row) else ""
                if content:
                    line_parts.append(content)
                    current_pos = expected_pos + get_display_width(content)
                else:
                    line_parts.append(" " * width)
                    current_pos = expected_pos + width
        
        output_lines.append("".join(line_parts))
    
    return output_lines


def build_multiple_prs_display(prs: List[PullRequest], options: Optional[Dict] = None) -> str:
    """
    Build display for multiple PRs.
    
    Args:
        prs: List of PullRequest objects
        options: Display options
        
    Returns:
        Formatted string ready for display
    """
    if not prs:
        return "No pull requests found."
    
    sections = []
    
    for i, pr in enumerate(prs):
        pr_display = build_pr_display(pr, options)
        sections.append(pr_display)
        
        # Add separator between PRs (except for the last one)
        if i < len(prs) - 1:
            sections.append("")  # Empty line separator
    
    return "\n".join(sections)


def build_compact_display(pr: PullRequest, terminal_width: Optional[int] = None) -> str:
    """
    Build a compact display for a PR (Lines 1-2 only).
    
    Args:
        pr: The PullRequest object
        terminal_width: Terminal width (auto-detected if None)
        
    Returns:
        Compact formatted string
    """
    if terminal_width is None:
        terminal_width = get_terminal_width()
    
    lines = []
    
    # Line 1: PR number and title
    line1 = format_pr_line1(pr)
    lines.append(line1)
    
    # Line 2: Short mode data
    line2 = build_line2_display(pr, terminal_width)
    if line2:
        lines.append(line2)
    
    return "\n".join(lines)


def build_detailed_display(pr: PullRequest, terminal_width: Optional[int] = None) -> str:
    """
    Build a detailed display for a PR (all lines with maximum columns).
    
    Args:
        pr: The PullRequest object
        terminal_width: Terminal width (auto-detected if None)
        
    Returns:
        Detailed formatted string
    """
    if terminal_width is None:
        terminal_width = get_terminal_width()
    
    # Use maximum columns configuration
    options = {"force_detailed": True}
    return build_pr_display(pr, options)


def print_pr_display(pr: PullRequest, options: Optional[Dict] = None, console: Optional[Console] = None):
    """
    Print the PR display directly to console.
    
    Args:
        pr: The PullRequest object
        options: Display options
        console: Rich Console instance (creates new one if None)
    """
    if console is None:
        console = Console()
    
    display_text = build_pr_display(pr, options)
    console.print(display_text)


def print_multiple_prs_display(
    prs: List[PullRequest],
    options: Optional[Dict] = None,
    console: Optional[Console] = None
):
    """
    Print multiple PRs display directly to console.
    
    Args:
        prs: List of PullRequest objects
        options: Display options
        console: Rich Console instance (creates new one if None)
    """
    if console is None:
        console = Console()
    
    display_text = build_multiple_prs_display(prs, options)
    console.print(display_text)


def get_display_preview(pr: PullRequest, max_width: int = 80) -> str:
    """
    Get a preview of how the PR display would look with a specific width.
    Useful for testing and debugging layout calculations.
    
    Args:
        pr: The PullRequest object
        max_width: Maximum width to use for preview
        
    Returns:
        Preview string with width indicators
    """
    lines = []
    
    # Add width ruler
    ruler = "".join([str(i % 10) for i in range(max_width)])
    lines.append(f"Width ruler: {ruler}")
    lines.append("-" * max_width)
    
    # Add PR display
    pr_display = build_pr_display(pr, {"preview_mode": True})
    lines.append(pr_display)
    
    lines.append("-" * max_width)
    
    return "\n".join(lines)