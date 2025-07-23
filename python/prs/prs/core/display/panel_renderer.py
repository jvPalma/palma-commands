"""
Main panel rendering orchestration.

This module handles:
- Panel title formatting
- Content assembly from feature renderers
- Panel creation and display
- Console output management
- Dynamic column width calculations for table layouts

DYNAMIC WIDTH CALCULATION ENGINE:
The calculate_dynamic_widths() function implements intelligent column width
distribution based on content scenarios:

1. NORMAL-only scenario: NORMAL gets 100% width
2. 1 NORMAL + 1 LONG scenario: NORMAL max 60%, LONG gets rest
3. Multiple columns scenario: NORMAL 40-50% range, distribute rest among LONG columns
4. Always respect NORMAL column min 40%, max 50% constraints for multi-column scenarios
5. Handle edge cases: narrow terminals (< 80 chars), very wide displays (> 200 chars)
6. All width calculations sum to console_width

The algorithm adapts to different terminal sizes:
- Very wide displays (≥200 chars): Allow more space for NORMAL column
- Wide displays (≥160 chars): Balanced distribution
- Standard displays (≥120 chars): Conservative approach
- Narrow displays (<120 chars): Minimum NORMAL width, maximize LONG columns
"""

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box
from typing import List, Tuple, Dict
from prs.core.title.helpers import format_title
from prs.utils.formatting import color_text, color_text_bg
from prs.core.title.helpers import compute_open_status
from prs.core.display.display_config import get_panel_color, MAX_TITLE_LENGTH
from prs.core.display.feature_renderers import (
    render_summary_status,
    render_url_info,
    render_branch_info,
    render_checks_detail,
    render_reviews_detail,
    render_labels_detail
)

# Character limits for LONG mode columns
FEATURE_CHARACTER_LIMITS = {
    "Checks": 60,
    "Reviews": 35,
    "Labels": 30
}


def create_panel_title(pr) -> Text:
    """
    Create formatted panel title with PR number and title.
    
    Args:
        pr: Pull request model object
        
    Returns:
        Rich Text object with formatted panel title
    """
    # OPEN STATUS
    open_text, open_color = compute_open_status(pr)

    pr_number = f"#{pr.id:06d}"
    title_formatted = format_title(pr.title)
    
    # Create Rich Text object instead of ANSI string
    title_text = Text()
    title_text.append(f"{open_text}", style=open_color)
    title_text.append(" ")
    title_text.append(f"{pr_number}", style=open_color)
    title_text.append(" ")
    title_text.append(f"{title_formatted}", style="white")
    
    # Check if title is too long and truncate if needed
    if len(title_text.plain) >= MAX_TITLE_LENGTH:
        # Truncate the plain text and rebuild
        truncated_plain = title_text.plain[:MAX_TITLE_LENGTH-3] + "..."
        truncated_text = Text()
        truncated_text.append(f"{open_text}", style=open_color)
        truncated_text.append(" ")
        truncated_text.append(f"{pr_number}", style=open_color)
        truncated_text.append(" ")
        # Calculate remaining space for title
        remaining_space = MAX_TITLE_LENGTH - len(f"{open_text} {pr_number} ") - 3
        if remaining_space > 0:
            truncated_text.append(title_formatted[:remaining_space] + "...", style="white")
        return truncated_text
    else:
        return title_text


def create_panel_subtitle(pr, modes: dict) -> Text or None:
    """
    Create panel subtitle with URL if URL display is enabled.
    
    Args:
        pr: Pull request model object
        modes: Dictionary of display modes
        
    Returns:
        Rich Text object with URL or None if URL mode is 'none'
    """
    if modes["pr_url"] == "none":
        return None
    
    subtitle_text = Text()
    subtitle_text.append(pr.url, style="cyan")
    return subtitle_text


def truncate_rich_text(text: Text, max_chars: int) -> Text:
    """
    Truncate Rich Text while preserving styling, adding ellipsis if content is truncated.
    
    Args:
        text: Rich Text object to truncate
        max_chars: Maximum characters per line
        
    Returns:
        Rich Text object with character limits applied and ellipsis if truncated
    """
    if not text or max_chars <= 0:
        return text
    
    # Handle empty or very short content
    plain_text = text.plain
    if len(plain_text) <= max_chars:
        return text
    
    # Simple approach: truncate at character boundary and add ellipsis
    # For more complex styling preservation, we'd need to track Rich Text spans
    if max_chars <= 3:
        return Text("...", style="dim")
    
    # Truncate the text and preserve basic styling
    truncated_plain = plain_text[:max_chars - 3]
    
    # Create new Text with truncated content
    truncated = Text()
    
    # Try to preserve styling by copying character by character with their styles
    for i, char in enumerate(truncated_plain):
        if i < len(plain_text):
            # Get style at this position from original text
            try:
                style = text.get_style_at_offset(i)
                truncated.append(char, style=style)
            except:
                # Fallback to plain text if style extraction fails
                truncated.append(char)
    
    # Add ellipsis
    truncated.append("...", style="dim")
    
    return truncated


def apply_character_limits(long_items: List[Tuple[str, Text]], feature_limits: Dict[str, int]) -> List[Tuple[str, Text]]:
    """
    Apply character limits to LONG mode column content while preserving Rich Text styling.
    
    Args:
        long_items: List of (header, content) tuples from collect_long_items
        feature_limits: Dictionary mapping feature names to character limits
        
    Returns:
        List of (header, content) tuples with character limits applied
    """
    if not long_items or not feature_limits:
        return long_items
    
    limited_items = []
    
    for header, content in long_items:
        # Get the character limit for this feature
        max_chars = feature_limits.get(header, 60)  # Default to 60 if not found
        
        if not content:
            limited_items.append((header, content))
            continue
        
        # Process content line by line while attempting to preserve Rich Text styling
        content_lines = content.plain.split('\n')
        
        if len(content_lines) <= 1:
            # Single line content - apply Rich Text aware truncation
            limited_content = truncate_rich_text(content, max_chars)
            limited_items.append((header, limited_content))
        else:
            # Multi-line content - for now, just apply simple truncation without breaking Rich Text styling
            # This preserves the original styling but may allow some lines to exceed character limits
            if len(content.plain) <= max_chars:
                # Content fits within limits
                limited_items.append((header, content))
            else:
                # Apply simple truncation using the truncate_rich_text function
                limited_content = truncate_rich_text(content, max_chars)
                limited_items.append((header, limited_content))
    
    return limited_items


def assemble_panel_content(pr, modes: dict, console: Console) -> object:
    """
    Assemble all panel content from feature renderers.
    
    Args:
        pr: Pull request model object
        modes: Dictionary of display modes
        console: Rich console for width calculation
        
    Returns:
        Rich Text object or Table object with complete panel content
    """
    content_parts = []

    # Line 1: Summary line with SHORT status badges (always first)
    summary_text = render_summary_status(pr, modes)
    content_parts.append(summary_text)

    # Check if we should use table layout for NORMAL/LONG content
    if should_use_table_layout(modes):
        # Create header section (summary + branch)
        header_content = Text("").join(content_parts)
        
        # Collect table content
        normal_items = collect_normal_items(pr, modes)
        long_items = collect_long_items(pr, modes)
        
        # Character limits are now automatically applied in collect_long_items()
        
        # Only create table if we have content for it
        if normal_items or long_items:
            console_width = console.size.width if hasattr(console, 'size') else 50
            table = create_table_layout(normal_items, long_items, console_width)
            
            # Return combined content: header + table using Group
            # Compact layout achieved through table box=None and padding=(0, 0)
            if header_content.plain.strip():
                return Group(header_content, table)
            else:
                return table
    
    # Fall back to current vertical layout for non-table modes
    # Add detailed information for SHORT mode or when no table needed
    checks_detail = render_checks_detail(pr, modes["checks"], modes)
    if checks_detail:
        content_parts.append(checks_detail)

    # Detailed review information
    reviews_detail = render_reviews_detail(pr, modes["reviews"], modes)
    if reviews_detail:
        content_parts.append(reviews_detail)

    # Detailed label information
    labels_detail = render_labels_detail(pr, modes["labels"], modes)
    if labels_detail:
        content_parts.append(labels_detail)

    return Text("\n").join(content_parts)


def render_pr_panel(pr, modes: dict, console: Console) -> None:
    """
    Render a single PR as a Rich panel.
    
    Args:
        pr: Pull request model object
        modes: Dictionary of display modes
        console: Rich console for output
    """
    panel_title = create_panel_title(pr)
    panel_subtitle = create_panel_subtitle(pr, modes)
    panel_content = assemble_panel_content(pr, modes, console)
    panel_color = get_panel_color(pr)
    
    panel = Panel(
        panel_content,
        title=panel_title,
        subtitle=panel_subtitle,
        border_style=panel_color,
        title_align="left",
        subtitle_align="left",
        padding=(0, 1),  # Remove all padding for compact layout
        expand=True
    )
    console.print(panel)
    
    # Branch information (if not "none") - displayed after panel without extra empty lines
    branch_text = render_branch_info(pr, modes["branch"])
    if branch_text:
        console.print(branch_text)
    
    console.print("")  # Add a single newline after each panel for separation


def should_use_table_layout(modes: dict) -> bool:
    """
    Detect if any modes are "normal" or "long" requiring table layout.
    
    Args:
        modes: Dictionary of display modes
        
    Returns:
        True if table layout should be used, False otherwise
    """
    if not modes:
        return False
        
    # Check if any of the key modes are "normal" or "long"
    table_modes = ["normal", "long"]
    features_to_check = ["checks", "reviews", "labels"]
    
    for feature in features_to_check:
        if modes.get(feature) in table_modes:
            return True
    
    return False


def collect_normal_items(pr, modes: dict) -> List[Text]:
    """
    Collect all items where mode == "normal" for column 1 display.
    
    Args:
        pr: Pull request model object
        modes: Dictionary of display modes
        
    Returns:
        List of Rich Text objects formatted as "Feature: content"
    """
    if not pr or not modes:
        return []
        
    normal_items = []
    
    # Check each feature mode and collect normal items
    # Pass modes dictionary for context-aware formatting
    if modes.get("checks") == "normal":
        checks_detail = render_checks_detail(pr, "normal", modes)
        if checks_detail:
            normal_items.append(checks_detail)
    
    if modes.get("reviews") == "normal":
        reviews_detail = render_reviews_detail(pr, "normal", modes)
        if reviews_detail:
            normal_items.append(reviews_detail)
    
    if modes.get("labels") == "normal":
        labels_detail = render_labels_detail(pr, "normal", modes)
        if labels_detail:
            normal_items.append(labels_detail)
    
    return normal_items


def collect_long_items(pr, modes: dict) -> List[Tuple[str, Text]]:
    """
    Collect items where mode == "long" with priority ordering and automatic character limits.
    
    Args:
        pr: Pull request model object
        modes: Dictionary of display modes
        
    Returns:
        List of (header, content) tuples with content limited to 5 lines max and character limits applied
        Priority order: Checks > Reviews > Labels
    """
    if not pr or not modes:
        return []
        
    long_items = []
    
    # Priority order: Checks > Reviews > Labels
    priority_features = [
        ("checks", "Checks"),
        ("reviews", "Reviews"), 
        ("labels", "Labels")
    ]
    
    for feature_key, header in priority_features:
        if modes.get(feature_key) == "long":
            if feature_key == "checks":
                content = render_checks_detail(pr, "long", modes)
            elif feature_key == "reviews":
                content = render_reviews_detail(pr, "long", modes)
            elif feature_key == "labels":
                content = render_labels_detail(pr, "long", modes)
            else:
                content = None
            
            if content:
                # Don't truncate lines here as it breaks Rich Text formatting
                # Character limits are handled in the formatting functions
                long_items.append((header, content))
    
    # Character limits are now applied in the formatting functions themselves
    # so we don't need to apply them again here
    return long_items


def calculate_dynamic_widths(console_width: int, has_normal: bool, num_long: int) -> Tuple[int, int, int, int]:
    """
    Calculate optimal column widths based on content scenarios and console width.
    
    This function implements the dynamic width calculation engine with the following rules:
    - NORMAL-only scenario: NORMAL gets 100% width
    - 1 NORMAL + 1 LONG scenario: NORMAL max 60%, LONG gets rest
    - Multiple columns scenario: NORMAL 40-50% range, distribute rest among LONG columns
    - Always respect NORMAL column min 40%, max 50% constraints for multi-column scenarios
    - Handle edge cases: narrow terminals, very wide displays
    
    Args:
        console_width: Available console width in characters
        has_normal: Whether NORMAL column content exists
        num_long: Number of LONG columns needed (0-3)
        
    Returns:
        Tuple of (normal_width, long1_width, long2_width, long3_width)
        All widths are integers and sum to console_width
        
    Mathematical Logic:
    1. Validate console_width and apply minimum constraints
    2. Handle NORMAL-only scenario (100% width)
    3. Handle 1 NORMAL + 1 LONG scenario (60%/40% split with constraints)
    4. Handle multiple columns with NORMAL 40-50% range
    5. Distribute remaining width evenly among LONG columns
    6. Apply edge case handling for very narrow/wide terminals
    """
    # Input validation and edge case handling
    if console_width <= 0:
        console_width = 120  # Default fallback width
    
    # Minimum width constraints to ensure readability
    MIN_CONSOLE_WIDTH = 80
    MIN_COLUMN_WIDTH = 20
    
    # Apply minimum console width for very narrow terminals
    if console_width < MIN_CONSOLE_WIDTH:
        console_width = MIN_CONSOLE_WIDTH
    
    # SCENARIO 1: NORMAL-only (no LONG columns)
    if has_normal and num_long == 0:
        return (console_width, 0, 0, 0)
    
    # SCENARIO 2: No NORMAL column (LONG columns only)
    if not has_normal and num_long > 0:
        # Distribute width evenly among LONG columns
        long_width = console_width // num_long
        remainder = console_width % num_long
        
        # Distribute remainder to first columns
        widths = [0, 0, 0, 0]  # normal, long1, long2, long3
        for i in range(min(num_long, 3)):
            widths[i + 1] = long_width + (1 if i < remainder else 0)
        
        return tuple(widths)
    
    # SCENARIO 3: 1 NORMAL + 1 LONG
    if has_normal and num_long == 1:
        # NORMAL gets max 60% but needs to leave minimum space for LONG
        max_normal_width = int(console_width * 0.6)
        min_long_width = MIN_COLUMN_WIDTH
        
        # Ensure LONG column gets at least minimum width
        if console_width - max_normal_width < min_long_width:
            normal_width = console_width - min_long_width
        else:
            normal_width = max_normal_width
        
        long_width = console_width - normal_width
        return (normal_width, long_width, 0, 0)
    
    # SCENARIO 4: Multiple columns (NORMAL + 2 or 3 LONG)
    if has_normal and num_long >= 2:
        # NORMAL column: 40-50% range based on console width and number of columns
        # For wider terminals and fewer columns, favor higher percentage
        # For narrower terminals and more columns, use lower percentage
        
        if console_width >= 200:
            # Very wide displays: can afford more space for NORMAL
            normal_percentage = 0.35
        elif console_width >= 160:
            # Wide displays: balanced approach
            normal_percentage = 0.40
        elif console_width >= 120:
            # Standard displays: conservative approach
            normal_percentage = 0.42
        else:
            # Narrow displays: minimum NORMAL width
            normal_percentage = 0.45
        
        normal_width = int(console_width * normal_percentage)
        
        # Ensure NORMAL column respects absolute constraints
        min_normal_width = int(console_width * 0.25)
        max_normal_width = int(console_width * 0.30)
        normal_width = max(min_normal_width, min(normal_width, max_normal_width))
        
        # Distribute remaining width among LONG columns
        remaining_width = console_width - normal_width
        long_width = remaining_width // num_long
        remainder = remaining_width % num_long
        
        # Build return tuple with remainder distributed to first columns
        widths = [normal_width, 0, 0, 0]
        for i in range(min(num_long, 3)):
            widths[i + 1] = long_width + (1 if i < remainder else 0)
        
        return tuple(widths)
    
    # Fallback: should not reach here with valid inputs
    # Return equal distribution as safety measure
    if has_normal:
        equal_width = console_width // (num_long + 1)
        remainder = console_width % (num_long + 1)
        
        widths = [equal_width + (1 if 0 < remainder else 0), 0, 0, 0]
        for i in range(min(num_long, 3)):
            widths[i + 1] = equal_width + (1 if i + 1 < remainder else 0)
        
        return tuple(widths)
    else:
        # No normal column
        return (0, console_width, 0, 0)



def create_table_layout(normal_items: List[Text], long_items: List[Tuple[str, Text]], console_width: int) -> Table:
    """
    Create Rich Table with appropriate columns and dynamic width calculation.
    
    Uses the calculate_dynamic_widths function to determine optimal column widths
    based on content scenarios and console width constraints.
    
    Args:
        normal_items: List of Text objects for column 1
        long_items: List of (header, content) tuples for columns 2-4
        console_width: Console width for dynamic sizing
        
    Returns:
        Rich Table object with proper styling and alignment
    """
    # Handle edge cases
    if console_width <= 0:
        console_width = 120  # Default width
    
    # Determine content configuration
    has_normal = len(normal_items) > 0
    num_long = min(len(long_items), 3)  # Maximum 3 LONG columns
    
    # Calculate dynamic widths using the width calculation engine
    normal_width, long1_width, long2_width, long3_width = calculate_dynamic_widths(
        console_width, has_normal, num_long
    )
    
    # Validation: ensure widths sum to console_width
    total_width = normal_width + long1_width + long2_width + long3_width
    if total_width != console_width:
        # Adjust the largest column to compensate for rounding errors
        diff = console_width - total_width
        if has_normal and normal_width > 0:
            normal_width += diff
        elif long1_width > 0:
            long1_width += diff
        elif long2_width > 0:
            long2_width += diff
        elif long3_width > 0:
            long3_width += diff
    
    # Create table based on calculated widths and available content
    # Use no box style for cleanest compact layout without borders or empty lines
    table = Table(box=None, show_header=False, padding=(0, 0))
    
    # Add NORMAL column if it has content and width
    if has_normal and normal_width > 0:
        table.add_column("Normal", width=normal_width, style="white", vertical="top")
    
    # Add LONG columns based on calculated widths
    if num_long >= 1 and long1_width > 0:
        table.add_column(long_items[0][0], width=long1_width, style="white", vertical="top")
    
    if num_long >= 2 and long2_width > 0:
        table.add_column(long_items[1][0], width=long2_width, style="white", vertical="top")
    
    if num_long >= 3 and long3_width > 0:
        table.add_column(long_items[2][0], width=long3_width, style="white", vertical="top")
    
    # Prepare row data based on what columns were actually added
    row_data = []
    
    # Add NORMAL column data if column exists
    if has_normal and normal_width > 0:
        normal_col = Text("\n").join(normal_items) if normal_items else Text("")
        row_data.append(normal_col)
    
    # Add LONG column data for each column that was created
    if num_long >= 1 and long1_width > 0:
        row_data.append(long_items[0][1])
    
    if num_long >= 2 and long2_width > 0:
        row_data.append(long_items[1][1])
    
    if num_long >= 3 and long3_width > 0:
        row_data.append(long_items[2][1])
    
    # Add single row with all data if we have any content
    if row_data and any(item.plain.strip() for item in row_data if isinstance(item, Text)):
        table.add_row(*row_data)
    elif row_data:
        # Add empty row if we have columns but no content
        table.add_row(*row_data)
    
    return table


def render_ignored_count(ignored_count: int, console: Console) -> None:
    """
    Render ignored PRs count message.
    
    Args:
        ignored_count: Number of ignored PRs
        console: Rich console for output
    """
    if ignored_count > 0:
        ignored_msg = Text(f"# ignored: {ignored_count}", style="dim")
        console.print(ignored_msg)