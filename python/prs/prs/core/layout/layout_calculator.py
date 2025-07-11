"""
Layout calculation utilities for the PRS columnar layout system.
"""
import os
import shutil
from typing import List, Tuple, Dict, Optional
from rich.console import Console

from .column_formatter import get_display_width, strip_ansi_codes


def get_terminal_width() -> int:
    """Get the current terminal width, with fallback to 80 columns."""
    try:
        # Try to get terminal size
        terminal_size = shutil.get_terminal_size()
        return terminal_size.columns
    except (OSError, AttributeError):
        # Fallback for environments where terminal size can't be determined
        return int(os.environ.get('COLUMNS', 80))


def calculate_optimal_column_widths(
    terminal_width: int,
    num_columns: int,
    min_column_width: int = 20,
    max_column_width: int = 50,
    column_spacing: int = 2
) -> List[int]:
    """
    Calculate optimal column widths based on terminal width and number of columns.
    
    Args:
        terminal_width: Available terminal width
        num_columns: Number of columns to fit
        min_column_width: Minimum width for any column
        max_column_width: Maximum width for any column
        column_spacing: Space between columns
        
    Returns:
        List of column widths
    """
    if num_columns <= 0:
        return []
    
    if num_columns == 1:
        return [min(terminal_width, max_column_width)]
    
    # Calculate available width after accounting for spacing
    spacing_width = column_spacing * (num_columns - 1)
    available_width = terminal_width - spacing_width
    
    # Calculate base width per column
    base_width = available_width // num_columns
    
    # Ensure minimum width requirements
    if base_width < min_column_width:
        # Not enough space for all columns at minimum width
        # Reduce number of columns that can fit
        max_possible_columns = (terminal_width + column_spacing) // (min_column_width + column_spacing)
        actual_columns = min(num_columns, max_possible_columns)
        
        if actual_columns <= 0:
            return [min_column_width]  # Return at least one column
        
        # Recalculate for reduced columns
        spacing_width = column_spacing * (actual_columns - 1)
        available_width = terminal_width - spacing_width
        base_width = available_width // actual_columns
        
        return [max(base_width, min_column_width)] * actual_columns
    
    # Ensure maximum width constraints
    if base_width > max_column_width:
        base_width = max_column_width
    
    # Distribute remaining width
    widths = [base_width] * num_columns
    remaining_width = available_width - (base_width * num_columns)
    
    # Distribute extra width to columns, starting from the first
    for i in range(min(remaining_width, num_columns)):
        if widths[i] < max_column_width:
            widths[i] += 1
    
    return widths


def calculate_line2_column_widths(short_columns: List[Tuple[str, int]], terminal_width: int) -> List[int]:
    """
    Calculate column widths for Line 2 based on content and fixed sizes.
    
    Args:
        short_columns: List of (content, preferred_width) tuples
        terminal_width: Available terminal width
        
    Returns:
        List of actual column widths to use
    """
    if not short_columns:
        return []
    
    # Start with preferred widths
    preferred_widths = [width for _, width in short_columns]
    total_preferred = sum(preferred_widths)
    
    # Account for spacing (1 space between columns)
    spacing = len(short_columns) - 1
    total_with_spacing = total_preferred + spacing
    
    if total_with_spacing <= terminal_width:
        # Preferred widths fit, return them
        return preferred_widths
    
    # Need to compress columns
    available_width = terminal_width - spacing
    
    # Calculate minimum widths based on actual content
    min_widths = []
    for content, preferred in short_columns:
        actual_width = get_display_width(content)
        min_widths.append(min(actual_width + 2, preferred))  # Add small padding
    
    total_min = sum(min_widths)
    
    if total_min > available_width:
        # Even minimum widths don't fit, use proportional scaling
        scale_factor = available_width / total_min
        scaled_widths = [max(3, int(width * scale_factor)) for width in min_widths]
        
        # Ensure we don't exceed available width
        while sum(scaled_widths) > available_width and any(w > 3 for w in scaled_widths):
            for i in range(len(scaled_widths)):
                if scaled_widths[i] > 3:
                    scaled_widths[i] -= 1
                    if sum(scaled_widths) <= available_width:
                        break
        
        return scaled_widths
    
    # Distribute available width proportionally
    extra_width = available_width - total_min
    
    # Distribute extra width proportionally to preferred sizes
    final_widths = min_widths.copy()
    if extra_width > 0:
        total_preferred_above_min = sum(max(0, pref - min_w) for pref, min_w in zip(preferred_widths, min_widths))
        
        if total_preferred_above_min > 0:
            for i, (pref, min_w) in enumerate(zip(preferred_widths, min_widths)):
                if pref > min_w:
                    proportion = (pref - min_w) / total_preferred_above_min
                    additional = int(extra_width * proportion)
                    final_widths[i] = min_w + additional
    
    return final_widths


def calculate_content_column_positions(
    normal_column_width: int,
    long_columns_data: Dict[str, List[str]],
    terminal_width: int,
    column_spacing: int = 2
) -> Dict[str, Tuple[int, int]]:
    """
    Calculate positions and widths for content columns (normal + long mode columns).
    
    Args:
        normal_column_width: Width allocated to the normal mode column
        long_columns_data: Dict of long mode column data
        terminal_width: Available terminal width
        column_spacing: Space between columns
        
    Returns:
        Dict mapping column names to (start_position, width) tuples
    """
    positions = {}
    current_position = 0
    
    # First column (normal mode)
    positions["normal"] = (current_position, normal_column_width)
    current_position += normal_column_width + column_spacing
    
    if not long_columns_data:
        return positions
    
    # Calculate remaining width for long mode columns
    remaining_width = terminal_width - current_position
    
    if remaining_width <= 0:
        return positions
    
    long_column_names = list(long_columns_data.keys())
    num_long_columns = len(long_column_names)
    
    if num_long_columns == 0:
        return positions
    
    # Calculate widths for long columns
    long_column_widths = calculate_optimal_column_widths(
        remaining_width,
        num_long_columns,
        min_column_width=15,
        max_column_width=40,
        column_spacing=column_spacing
    )
    
    # Assign positions to long columns
    for i, column_name in enumerate(long_column_names):
        if i < len(long_column_widths):
            width = long_column_widths[i]
            positions[column_name] = (current_position, width)
            current_position += width + column_spacing
        else:
            # No more space for this column
            break
    
    return positions


def calculate_normal_column_width(terminal_width: int, num_long_columns: int) -> int:
    """
    Calculate the width for the normal mode column based on available space.
    
    Args:
        terminal_width: Available terminal width
        num_long_columns: Number of additional long mode columns
        
    Returns:
        Width for the normal mode column
    """
    if num_long_columns == 0:
        # Only normal column, use reasonable portion of terminal
        return min(terminal_width, 60)
    
    # Reserve space for long columns (estimate)
    min_long_column_width = 15
    spacing_per_column = 2
    reserved_for_long = num_long_columns * (min_long_column_width + spacing_per_column)
    
    # Available width for normal column
    available_for_normal = terminal_width - reserved_for_long
    
    # Ensure minimum and maximum bounds
    min_normal_width = 30
    max_normal_width = 50
    
    return max(min_normal_width, min(available_for_normal, max_normal_width))


def fit_columns_to_terminal(
    columns_data: Dict[str, List[str]],
    terminal_width: int,
    max_columns: Optional[int] = None
) -> Dict[str, List[str]]:
    """
    Determine which columns can fit in the terminal and return the filtered data.
    
    Args:
        columns_data: Dict of column data
        terminal_width: Available terminal width
        max_columns: Maximum number of columns to show (None for no limit)
        
    Returns:
        Filtered dict of columns that can fit
    """
    if not columns_data:
        return {}
    
    column_names = list(columns_data.keys())
    
    if max_columns is not None:
        column_names = column_names[:max_columns]
    
    # Estimate minimum space needed per column
    min_column_width = 15
    spacing_per_column = 2
    
    # Calculate how many columns can fit
    max_possible_columns = (terminal_width + spacing_per_column) // (min_column_width + spacing_per_column)
    
    if max_possible_columns < len(column_names):
        column_names = column_names[:max_possible_columns]
    
    # Return filtered data
    return {name: columns_data[name] for name in column_names if name in columns_data}


def get_layout_config(terminal_width: int) -> Dict[str, int]:
    """
    Get layout configuration based on terminal width.
    
    Args:
        terminal_width: Available terminal width
        
    Returns:
        Dict with layout configuration values
    """
    config = {
        "terminal_width": terminal_width,
        "column_spacing": 2,
        "max_long_columns": 4,
        "min_column_width": 15,
        "max_column_width": 50,
        "normal_column_min_width": 30,
        "normal_column_max_width": 50,
    }
    
    # Adjust configuration based on terminal width
    if terminal_width < 80:
        # Narrow terminal
        config.update({
            "column_spacing": 1,
            "max_long_columns": 2,
            "min_column_width": 12,
            "max_column_width": 30,
            "normal_column_min_width": 25,
            "normal_column_max_width": 35,
        })
    elif terminal_width < 120:
        # Medium terminal
        config.update({
            "max_long_columns": 3,
            "max_column_width": 40,
        })
    else:
        # Wide terminal
        config.update({
            "max_long_columns": 5,
            "max_column_width": 60,
        })
    
    return config