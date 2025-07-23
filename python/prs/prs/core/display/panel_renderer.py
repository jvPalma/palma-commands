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
from prs.core.display.display_config import get_panel_color, MAX_TITLE_LENGTH
from prs.core.display.feature_renderers import (
    render_summary_status,
    render_url_info,
    render_branch_info,
    render_checks_detail,
    render_reviews_detail,
    render_labels_detail
)


def create_panel_title(pr) -> str:
    """
    Create formatted panel title with PR number and title.
    
    Args:
        pr: Pull request model object
        
    Returns:
        Formatted panel title string
    """
    pr_number = f"#{pr.id:06d}"
    title_formatted = format_title(pr.title)
    full_title = f"{pr_number} {title_formatted}"
    
    if len(full_title) >= MAX_TITLE_LENGTH:
        return full_title[:MAX_TITLE_LENGTH-3] + "..."
    else:
        return full_title


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

    # URL information
    url_text = render_url_info(pr, modes["pr_url"])
    if url_text:
        content_parts.append(url_text)

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
    panel_content = assemble_panel_content(pr, modes)
    panel_color = get_panel_color(pr)
    
    panel = Panel(
        panel_content,
        title=panel_title,
        border_style=panel_color,
        title_align="left",
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