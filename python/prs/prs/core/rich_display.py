"""
Rich-enhanced display module for PRS.
"""
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.box import ROUNDED, SIMPLE, MINIMAL_HEAVY_HEAD
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import print as rprint

from prs.core.models import PullRequest
from prs.core.author.helpers import get_author_color
from prs.core.title.helpers import compute_open_status
from prs.core.status.border_logic import get_pr_border_color_and_style
from prs.core.layout import (
    build_pr_display,
    build_multiple_prs_display,
    build_compact_display,
    build_detailed_display,
    format_pr_line1,
    format_pr_line2_short,
    format_normal_mode_data,
    format_long_mode_data
)
from prs.config import get


def get_rich_color(color_name: str) -> str:
    """Convert our color names to Rich color names."""
    color_mappings = {
        "green": "green",
        "green-bright": "bright_green",
        "yellow": "yellow",
        "yellow-bright": "bright_yellow",
        "red": "red",
        "red-bright": "bright_red",
        "blue": "blue",
        "blue-bright": "bright_blue",
        "cyan": "cyan",
        "cyan-bright": "bright_cyan",
        "magenta": "magenta",
        "magenta-bright": "bright_magenta",
        "gray-0": "bright_black",
        "gray-1": "bright_black",
        "gray-2": "bright_black",
        "gray-3": "bright_black",
        "gray-4": "bright_black",
        "white": "white",
    }
    return color_mappings.get(color_name, "white")


def create_pr_panel(pr: PullRequest, options: Dict) -> Panel:
    """Create a Rich panel for a single PR with proper verbosity filtering."""
    # Get display options
    ci_mode = options.get("ci_mode", "short")
    review_mode = options.get("review_mode", "short")
    labels_mode = options.get("labels_mode", "short")
    comments_mode = options.get("comments_mode", "short")
    author_mode = options.get("author_mode", "short")
    pr_url_mode = options.get("pr_url_mode", "short")
    branch_mode = options.get("branch_mode", "short")
    
    content_lines = []
    
    # Line 1: Empty (title is in panel border)
    # Line 2: Short mode indicators (only if any field is set to short)
    short_fields = []
    if ci_mode == "short" and pr.checks:
        from prs.core.checks.helpers import get_checks
        short_fields.append(get_checks(pr, "short"))
    if review_mode == "short" and pr.reviews:
        from prs.core.reviews.helpers import get_reviews
        short_fields.append(get_reviews(pr, "short"))
    if labels_mode == "short" and pr.labels:
        from prs.core.labels.helpers import get_labels
        short_fields.append(get_labels(pr, "short"))
    if comments_mode == "short" and pr.comments:
        from prs.core.comments.helpers import get_comments
        short_fields.append(get_comments(pr, "short"))
    if author_mode == "short":
        from prs.core.author.helpers import get_author
        short_fields.append(get_author(pr, "short"))
    if branch_mode == "short" and pr.branch:
        short_fields.append(f"🌿 {pr.branch[:10]}...")
    if pr_url_mode == "short" and hasattr(pr, 'url'):
        short_fields.append(f"🔗 PR")
    
    if short_fields:
        line2 = Text()
        line2.append(" | ".join(short_fields))
        content_lines.append(line2)
    
    # Line 3+: Columnar layout for normal and long modes
    # Column 1: All normal mode fields
    normal_items = []
    
    if ci_mode == "normal" and pr.checks:
        from prs.core.checks.helpers import get_checks
        # Check if we have GitHub Actions data for enhanced display
        github_actions_summary = _get_github_actions_summary(pr)
        if github_actions_summary:
            normal_items.append(f"GitHub Actions: {github_actions_summary['text']}")
        else:
            normal_items.append(f"CI/CD: {get_checks(pr, 'normal')}")
    if review_mode == "normal" and pr.reviews:
        from prs.core.reviews.helpers import get_reviews
        normal_items.append(f"Reviews: {get_reviews(pr, 'normal')}")
    if labels_mode == "normal" and pr.labels:
        from prs.core.labels.helpers import get_labels
        normal_items.append(f"Labels: {get_labels(pr, 'normal')}")
    if comments_mode == "normal" and pr.comments:
        from prs.core.comments.helpers import get_comments
        normal_items.append(f"Comments: {get_comments(pr, 'normal')}")
    if author_mode == "normal":
        from prs.core.author.helpers import get_author
        normal_items.append(f"Author: {get_author(pr, 'normal')}")
    if branch_mode == "normal" and pr.branch:
        normal_items.append(f"Branch: {pr.branch}")
    if pr_url_mode == "normal" and hasattr(pr, 'url'):
        normal_items.append(f"URL: {getattr(pr, 'url', '')}")
    
    # Columns 2+: All long mode fields
    long_columns = []
    
    if ci_mode == "long" and pr.checks:
        from prs.core.checks.helpers import get_checks
        # Check if we have GitHub Actions data for enhanced display
        if hasattr(pr, 'ci_data') and pr.ci_data:
            workflows_details = []
            for workflow in pr.ci_data.workflows[:3]:  # Show top 3 workflows
                status_emoji = "✅" if workflow.conclusion == "success" else "❌" if workflow.conclusion == "failure" else "🟡"
                duration = _format_duration(workflow.duration)
                workflows_details.append(f"{status_emoji} {workflow.name} ({duration})")
                
                # Show job details for failed workflows
                if workflow.conclusion == "failure" and workflow.jobs:
                    for job in workflow.jobs[:2]:  # Show top 2 failed jobs
                        if job.conclusion == "failure":
                            job_duration = _format_duration(job.duration)
                            workflows_details.append(f"  ↳ {job.name} failed ({job_duration})")
            
            if len(pr.ci_data.workflows) > 3:
                workflows_details.append(f"... and {len(pr.ci_data.workflows) - 3} more workflows")
            
            long_columns.append(("GitHub Actions", "\n".join(workflows_details)))
        else:
            checks_content = get_checks(pr, 'long')
            long_columns.append(("CI/CD Detail", checks_content))
    if review_mode == "long" and pr.reviews:
        from prs.core.reviews.helpers import get_reviews
        reviews_content = get_reviews(pr, 'long')
        long_columns.append(("Reviews Detail", reviews_content))
    if labels_mode == "long" and pr.labels:
        from prs.core.labels.helpers import get_labels
        labels_content = get_labels(pr, 'long')
        long_columns.append(("Labels Detail", labels_content))
    if comments_mode == "long" and pr.comments:
        from prs.core.comments.helpers import get_comments
        comments_content = get_comments(pr, 'long')
        long_columns.append(("Comments Detail", comments_content))
    if author_mode == "long":
        from prs.core.author.helpers import get_author
        author_content = get_author(pr, 'long')
        long_columns.append(("Author Detail", author_content))
    if branch_mode == "long" and pr.branch:
        branch_content = f"{pr.branch}\n→ {pr.branch.split('/')[-1]}"
        long_columns.append(("Branch Detail", branch_content))
    if pr_url_mode == "long" and hasattr(pr, 'url'):
        url_content = getattr(pr, 'url', '')
        long_columns.append(("URL", url_content))
    
    # Add normal mode items (line by line)
    for item in normal_items:
        content_lines.append(Text.from_ansi(item))
    
    # Add separator if we have both normal and long mode content
    if normal_items and long_columns:
        content_lines.append(Text("-" * 40, style="bright_black"))
    
    # Add long mode items (column titles with content)
    for title, content in long_columns:
        # Split content into lines and limit to 7 lines
        lines = content.split('\n')[:7]
        if len(content.split('\n')) > 7:
            lines.append("...")
        
        # Create title and content
        section = Text()
        section.append(f"{title}:\n", style="bold yellow")
        section.append("\n".join(lines))
        content_lines.append(section)
    
    # Combine all content
    if len(content_lines) == 0:
        # If no content, add an empty line to prevent empty panel
        content = Text("")
    elif len(content_lines) == 1:
        content = content_lines[0]
    else:
        # Join multiple lines/elements
        combined = Text()
        for i, line in enumerate(content_lines):
            if i > 0:
                combined.append("\n")
            if isinstance(line, Text):
                combined.append(line)
            else:
                # For non-Text objects (like Columns), convert to string
                combined.append(str(line))
        content = combined
    
    # Panel title (left side): PR number and title
    title_left = f"#{pr.id:06d} {pr.title[:50]}{'...' if len(pr.title) > 50 else ''}"
    
    # Panel subtitle (right side): File changes
    subtitle_right = ""
    if hasattr(pr, 'additions') and hasattr(pr, 'deletions'):
        if pr.additions or pr.deletions:
            subtitle_right = f"📊 +{pr.additions or 0}/-{pr.deletions or 0}"
            if hasattr(pr, 'changed_files') and pr.changed_files:
                subtitle_right += f" ({pr.changed_files} files)"
    
    # Get dynamic border color and style based on PR status
    border_color, style_info = get_pr_border_color_and_style(pr)
    
    # Override with draft styling if needed (drafts get dimmed border)
    if pr.is_draft:
        border_style = "bright_black"
    else:
        border_style = border_color
    
    return Panel(
        content,
        title=title_left,
        subtitle=subtitle_right,
        title_align="left",
        subtitle_align="right",
        border_style=border_style,
        box=ROUNDED,
        padding=(0, 1),
    )


def _determine_display_mode(options: Dict) -> str:
    """Determine the display mode based on verbosity options."""
    # Check verbosity settings to determine appropriate display mode
    ci_mode = options.get("ci_mode", "short")
    review_mode = options.get("review_mode", "short")
    labels_mode = options.get("labels_mode", "short")
    comments_mode = options.get("comments_mode", "short")
    author_mode = options.get("author_mode", "short")
    pr_url_mode = options.get("pr_url_mode", "short")
    branch_mode = options.get("branch_mode", "short")
    
    # Count how many are set to "none" (compact mode)
    none_count = sum(1 for mode in [ci_mode, review_mode, labels_mode, 
                                   comments_mode, author_mode, pr_url_mode, branch_mode] 
                    if mode == "none")
    
    # Count how many are set to "long" (detailed mode)
    long_count = sum(1 for mode in [ci_mode, review_mode, labels_mode, 
                                   comments_mode, author_mode, pr_url_mode, branch_mode] 
                    if mode == "long")
    
    # Determine mode based on verbosity
    if none_count >= 5:  # Most are "none"
        return "compact"
    elif long_count >= 3:  # Many are "long"
        return "detailed"
    else:
        return "normal"


def _get_checks_summary(checks: List[Dict]) -> Dict[str, str]:
    """Get a summary of CI/CD check statuses including GitHub Actions."""
    if not checks:
        return {"text": "○ No CI/CD", "style": "bright_black"}
    
    # Count check statuses
    success = 0
    failure = 0
    pending = 0
    github_actions_count = 0
    
    for check in checks:
        if isinstance(check, dict):
            status = check.get("status", "").upper()
            conclusion = check.get("conclusion", "").upper()
            context = check.get("context", "")
            
            # Track GitHub Actions workflows
            if context.startswith("github-actions/"):
                github_actions_count += 1
            
            if status == "COMPLETED":
                if conclusion in ["SUCCESS", "NEUTRAL", "SKIPPED"]:
                    success += 1
                else:
                    failure += 1
            else:
                pending += 1
    
    total = len(checks)
    
    # Enhanced display for GitHub Actions
    if github_actions_count > 0:
        ga_text = f"GHA+{total-github_actions_count}" if total > github_actions_count else "GHA"
        
        if failure > 0:
            return {"text": f"✗ {ga_text} {success}/{total}", "style": "red"}
        elif pending > 0:
            return {"text": f"◐ {ga_text} {success}/{total}", "style": "yellow"}
        else:
            return {"text": f"✓ {ga_text} {success}/{total}", "style": "green"}
    else:
        # Fallback for non-GitHub Actions checks
        if failure > 0:
            return {"text": f"✗ CI/CD {success}/{total}", "style": "red"}
        elif pending > 0:
            return {"text": f"◐ CI/CD {success}/{total}", "style": "yellow"}
        else:
            return {"text": f"✓ CI/CD {success}/{total}", "style": "green"}


def _format_duration(duration: Optional[int]) -> str:
    """Format duration in seconds to human-readable format."""
    if not duration:
        return "N/A"
    
    if duration < 60:
        return f"{duration}s"
    elif duration < 3600:
        minutes = duration // 60
        seconds = duration % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        return f"{hours}h {minutes}m"


def _get_github_actions_summary(pr) -> Optional[Dict[str, str]]:
    """Get GitHub Actions specific summary if CI data is available."""
    if not hasattr(pr, 'ci_data') or not pr.ci_data:
        return None
    
    ci_data = pr.ci_data
    
    # GitHub Actions emoji indicators
    if ci_data.failed_workflows > 0:
        return {
            "text": f"⚡ {ci_data.failed_workflows} failed",
            "style": "red",
            "emoji": "❌"
        }
    elif ci_data.pending_workflows > 0:
        return {
            "text": f"⚡ {ci_data.pending_workflows} running",
            "style": "yellow", 
            "emoji": "🟡"
        }
    elif ci_data.successful_workflows > 0:
        return {
            "text": f"⚡ {ci_data.successful_workflows} passed",
            "style": "green",
            "emoji": "✅"
        }
    else:
        return {
            "text": "⚡ no workflows",
            "style": "bright_black",
            "emoji": "○"
        }


def _get_review_summary(reviews: List[Dict]) -> Dict[str, str]:
    """Get a summary of review statuses."""
    if not reviews:
        return {"text": "○ No reviews", "style": "bright_black"}
    
    # Count review states
    approved = 0
    changes_requested = 0
    
    for review in reviews:
        if isinstance(review, dict):
            state = review.get("state", "").upper()
            if state == "APPROVED":
                approved += 1
            elif state == "CHANGES_REQUESTED":
                changes_requested += 1
    
    if changes_requested > 0:
        return {"text": f"✗ Reviews ({changes_requested} changes)", "style": "red"}
    elif approved > 0:
        return {"text": f"✓ Reviews ({approved} approved)", "style": "green"}
    else:
        return {"text": "◐ Reviews pending", "style": "yellow"}


def display_prs_rich(prs: List[PullRequest], options: Dict):
    """Display PRs using Rich formatting with the new layout system."""
    console = Console()
    
    # Handle empty PR list
    if not prs:
        console.print(Panel(
            Text("No pull requests found.", style="bright_black"),
            title="Pull Requests",
            title_style="bold blue",
            border_style="blue",
            box=MINIMAL_HEAVY_HEAD
        ))
        return
    
    # Create header with enhanced information
    header = Text()
    header.append("🔍 ", style="blue")
    header.append("Pull Requests", style="bold blue")
    header.append(f" ({len(prs)} found)", style="bright_black")
    
    # Add status summary
    draft_count = sum(1 for pr in prs if pr.is_draft)
    open_count = len(prs) - draft_count
    if draft_count > 0:
        header.append(f" • {open_count} open, {draft_count} draft", style="cyan")
    
    console.print(Panel(header, box=MINIMAL_HEAVY_HEAD, border_style="blue"))
    console.print()
    
    # Display each PR using the fixed panel creation
    for i, pr in enumerate(prs):
        panel = create_pr_panel(pr, options)
        console.print(panel)
        
        # Add spacing between PRs except for the last one
        if i < len(prs) - 1:
            console.print()


def _display_prs_compact_panels(prs: List[PullRequest], options: Dict, console: Console):
    """Display PRs using compact panels for better space efficiency."""
    for i, pr in enumerate(prs):
        # Use compact display from layout system
        content_text = build_compact_display(pr)
        content = Text.from_ansi(content_text)
        
        # Get border color based on PR status
        border_color, style_info = get_pr_border_color_and_style(pr)
        border_style = "bright_black" if pr.is_draft else border_color
        
        # Create simple panel with minimal padding
        panel = Panel(
            content,
            border_style=border_style,
            box=SIMPLE,
            padding=(0, 1),
            expand=False
        )
        
        console.print(panel)
        
        # Add minimal spacing between PRs
        if i < len(prs) - 1:
            console.print()


def _display_prs_full_panels(prs: List[PullRequest], options: Dict, console: Console):
    """Display PRs using full panels with complete layout system."""
    for i, pr in enumerate(prs):
        panel = create_pr_panel(pr, options)
        console.print(panel)
        
        # Add space between panels
        if i < len(prs) - 1:
            console.print()


def create_pr_table(prs: List[PullRequest], options: Dict) -> Table:
    """Create a Rich table view of PRs with enhanced layout integration."""
    # Determine table layout based on options and number of PRs
    is_compact = _determine_display_mode(options) == "compact" or len(prs) > 20
    
    if is_compact:
        return _create_compact_table(prs, options)
    else:
        return _create_detailed_table(prs, options)


def _create_compact_table(prs: List[PullRequest], options: Dict) -> Table:
    """Create a compact table for many PRs or when verbosity is low."""
    table = Table(
        title=f"Pull Requests ({len(prs)} found)",
        title_style="bold blue",
        show_header=True,
        header_style="bold cyan",
        box=SIMPLE,
        expand=False,
    )
    
    # Compact columns
    table.add_column("PR", style="bright_black", no_wrap=True, width=8)
    table.add_column("Title", style="blue", overflow="ellipsis", max_width=60)
    table.add_column("Health", justify="center", width=6)
    table.add_column("Status", justify="center", width=8)
    table.add_column("Author", style="cyan", width=12)
    
    for pr in prs:
        # PR number
        pr_num = f"#{pr.id:06d}"
        
        # Title with draft styling
        title = pr.title[:60] + "..." if len(pr.title) > 60 else pr.title
        if pr.is_draft:
            title = Text(title, style="bright_black")
        
        # Health indicator using border color logic
        border_color, style_info = get_pr_border_color_and_style(pr)
        health_indicators = {
            "green": "●●●",
            "cyan": "●●○", 
            "yellow": "●○○",
            "red": "●××"
        }
        health_text = health_indicators.get(border_color, "○○○")
        health = Text(health_text, style=border_color)
        
        # Status with emoji
        open_text, open_color = compute_open_status(pr)
        status_icon = "🟢" if open_text == "OPEN" else "🟡" if open_text == "DRFT" else "⚫"
        status = Text(f"{status_icon} {open_text[:4]}", style=get_rich_color(open_color))
        
        # Author with color coding
        config_username = get("git", "username")
        author_color, _ = get_author_color(pr.author, config_username)
        author = Text(pr.author[:12], style=get_rich_color(author_color))
        
        table.add_row(pr_num, title, health, status, author)
    
    return table


def _create_detailed_table(prs: List[PullRequest], options: Dict) -> Table:
    """Create a detailed table with full information."""
    table = Table(
        title=f"Pull Requests - Detailed View ({len(prs)} found)",
        title_style="bold blue",
        show_header=True,
        header_style="bold cyan",
        box=SIMPLE,
        expand=False,
    )
    
    # Full columns with enhanced information
    table.add_column("PR", style="bright_black", no_wrap=True, width=8)
    table.add_column("Title", style="blue", overflow="ellipsis", max_width=50)
    table.add_column("Health", justify="center", width=6)
    table.add_column("Status", justify="center", width=8)
    table.add_column("CI/CD", justify="center", width=10)
    table.add_column("Reviews", justify="center", width=10)
    table.add_column("Author", style="cyan", width=12)
    table.add_column("Changes", justify="right", width=12)
    table.add_column("Labels", justify="center", width=8)
    
    for pr in prs:
        # PR number
        pr_num = f"#{pr.id:06d}"
        
        # Title with draft styling
        title = pr.title[:50] + "..." if len(pr.title) > 50 else pr.title
        if pr.is_draft:
            title = Text(title, style="bright_black")
        
        # Health indicator using border color logic
        border_color, style_info = get_pr_border_color_and_style(pr)
        health_indicators = {
            "green": "●●●",
            "cyan": "●●○", 
            "yellow": "●○○",
            "red": "●××"
        }
        health_text = health_indicators.get(border_color, "○○○")
        health = Text(health_text, style=border_color)
        
        # Status with emoji
        open_text, open_color = compute_open_status(pr)
        status_icon = "🟢" if open_text == "OPEN" else "🟡" if open_text == "DRFT" else "⚫"
        status = Text(f"{status_icon} {open_text[:4]}", style=get_rich_color(open_color))
        
        # CI/CD with enhanced summary (prioritize GitHub Actions if available)
        github_actions_summary = _get_github_actions_summary(pr)
        if github_actions_summary:
            checks = Text(f"{github_actions_summary['emoji']} {github_actions_summary['text'][:8]}", 
                         style=github_actions_summary["style"])
        else:
            checks_summary = _get_checks_summary(pr.checks)
            check_icon = "✅" if "green" in checks_summary["style"] else "❌" if "red" in checks_summary["style"] else "⏳"
            checks = Text(f"{check_icon} {checks_summary['text'][:8]}", style=checks_summary["style"])
        
        # Reviews with enhanced summary
        review_summary = _get_review_summary(pr.reviews)
        review_icon = "✅" if "green" in review_summary["style"] else "❌" if "red" in review_summary["style"] else "⏳"
        reviews = Text(f"{review_icon} {review_summary['text'][:8]}", style=review_summary["style"])
        
        # Author with color coding
        config_username = get("git", "username")
        author_color, _ = get_author_color(pr.author, config_username)
        author = Text(pr.author[:12], style=get_rich_color(author_color))
        
        # Changes with better formatting
        changes = Text()
        changes.append(f"+{pr.additions}", style="green")
        changes.append("/", style="bright_black")
        changes.append(f"-{pr.deletions}", style="red")
        
        # Labels count with indicator
        if pr.labels:
            label_count = len(pr.labels)
            label_icon = "🏷️" if label_count > 0 else "⚫"
            labels = Text(f"{label_icon} {label_count}", style="cyan" if label_count > 0 else "bright_black")
        else:
            labels = Text("⚫ 0", style="bright_black")
        
        table.add_row(pr_num, title, health, status, checks, reviews, author, changes, labels)
    
    return table


def display_prs_table(prs: List[PullRequest], options: Dict):
    """Display PRs in a table format with enhanced layout support."""
    console = Console()
    
    # Handle empty PR list
    if not prs:
        empty_table = Table(
            title="Pull Requests",
            title_style="bold blue",
            show_header=False,
            box=SIMPLE
        )
        empty_table.add_column("Message", justify="center")
        empty_table.add_row(Text("No pull requests found.", style="bright_black"))
        console.print(empty_table)
        return
    
    # Create and display the table
    table = create_pr_table(prs, options)
    console.print(table)
    
    # Add summary information
    draft_count = sum(1 for pr in prs if pr.is_draft)
    open_count = len(prs) - draft_count
    
    # Add health summary using border logic
    health_summary = _get_health_summary(prs)
    
    summary_text = Text()
    summary_text.append(f"\nSummary: ", style="bright_black")
    summary_text.append(f"{open_count} open", style="green" if open_count > 0 else "bright_black")
    
    if draft_count > 0:
        summary_text.append(", ", style="bright_black")
        summary_text.append(f"{draft_count} draft", style="yellow")
    
    summary_text.append(f" • Health: ", style="bright_black")
    summary_text.append(f"{health_summary['healthy']} healthy", style="green")
    summary_text.append(", ", style="bright_black")
    summary_text.append(f"{health_summary['attention']} need attention", style="red" if health_summary['attention'] > 0 else "bright_black")
    
    console.print(summary_text)


def _get_health_summary(prs: List[PullRequest]) -> Dict[str, int]:
    """Get health summary statistics for a list of PRs."""
    healthy_count = 0
    attention_count = 0
    
    for pr in prs:
        border_color, style_info = get_pr_border_color_and_style(pr)
        if border_color == "green":
            healthy_count += 1
        elif border_color == "red":
            attention_count += 1
    
    return {
        "healthy": healthy_count,
        "attention": attention_count,
        "total": len(prs)
    }


def create_progress_bar(description: str = "Processing...") -> Progress:
    """Create a Rich progress bar for long operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=Console(),
        transient=True,
    )


# Rich-based formatting utilities for consistent messaging
def print_success(message: str, console: Optional[Console] = None):
    """Print a success message with consistent formatting."""
    if console is None:
        console = Console()
    console.print(f"[bold green]✅ {message}[/bold green]")


def print_error(message: str, console: Optional[Console] = None):
    """Print an error message with consistent formatting."""
    if console is None:
        console = Console()
    console.print(f"[bold red]❌ {message}[/bold red]")


def print_warning(message: str, console: Optional[Console] = None):
    """Print a warning message with consistent formatting."""
    if console is None:
        console = Console()
    console.print(f"[bold yellow]⚠️  {message}[/bold yellow]")


def print_info(message: str, console: Optional[Console] = None):
    """Print an info message with consistent formatting."""
    if console is None:
        console = Console()
    console.print(f"[bold blue]ℹ️  {message}[/bold blue]")


def print_processing(message: str, console: Optional[Console] = None):
    """Print a processing message with consistent formatting."""
    if console is None:
        console = Console()
    console.print(f"[bold cyan]⚙️  {message}[/bold cyan]")


def create_status_panel(title: str, content: str, status: str = "info") -> Panel:
    """Create a status panel with consistent styling."""
    status_styles = {
        "success": ("green", "✅"),
        "error": ("red", "❌"),
        "warning": ("yellow", "⚠️"),
        "info": ("blue", "ℹ️"),
        "processing": ("cyan", "⚙️")
    }
    
    style, emoji = status_styles.get(status, status_styles["info"])
    
    return Panel(
        content,
        title=f"{emoji} {title}",
        title_align="left",
        border_style=style,
        padding=(1, 2)
    )


def create_command_panel(title: str, commands: str, style: str = "cyan") -> Panel:
    """Create a panel for displaying commands with syntax highlighting."""
    return Panel(
        commands,
        title=f"🔧 {title}",
        title_align="left",
        border_style=style,
        padding=(0, 1)
    )


def print_section_header(text: str, console: Optional[Console] = None):
    """Print a section header with consistent formatting."""
    if console is None:
        console = Console()
    console.print(f"\n[bold cyan]📋 {text}[/bold cyan]")


def print_completion_message(task: str, details: Dict[str, int] = None, console: Optional[Console] = None):
    """Print a task completion message with optional details."""
    if console is None:
        console = Console()
    
    console.print(f"\n[bold green]🎉 {task} complete![/bold green]")
    
    if details:
        for key, value in details.items():
            console.print(f"   • {key}: [cyan]{value}[/cyan]")
    
    console.print()