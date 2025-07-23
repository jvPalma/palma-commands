"""
Main panel rendering orchestration.

This module handles:
- Panel title formatting
- Content assembly from feature renderers
- Panel creation and display
- Console output management
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
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


def assemble_panel_content(pr, modes: dict) -> Text:
    """
    Assemble all panel content from feature renderers.
    
    Args:
        pr: Pull request model object
        modes: Dictionary of display modes
        
    Returns:
        Rich Text object with complete panel content
    """
    content_parts = []

    # Summary line with status badges
    summary_text = render_summary_status(pr, modes)
    content_parts.append(summary_text)

    # Branch information
    branch_text = render_branch_info(pr, modes["branch"])
    if branch_text:
        content_parts.append(branch_text)

    # Detailed check information
    checks_detail = render_checks_detail(pr, modes["checks"])
    if checks_detail:
        content_parts.append(checks_detail)

    # Detailed review information
    reviews_detail = render_reviews_detail(pr, modes["reviews"])
    if reviews_detail:
        content_parts.append(reviews_detail)

    # Detailed label information
    labels_detail = render_labels_detail(pr, modes["labels"])
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
    panel_content = assemble_panel_content(pr, modes)
    panel_color = get_panel_color(pr)
    
    panel = Panel(
        panel_content,
        title=panel_title,
        subtitle=panel_subtitle,
        border_style=panel_color,
        title_align="left",
        subtitle_align="left",
        padding=(0, 1),
        expand=True
    )
    console.print(panel)


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