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
from prs.utils.formatting import color_map


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
    """Create a Rich panel for a single PR."""
    # Get display options
    checks_mode = options.get("checks_mode", "short")
    review_mode = options.get("review_mode", "short")
    labels_mode = options.get("labels_mode", "short")
    comments_mode = options.get("comments_mode", "short")
    
    # Create title with PR number and title
    pr_number = f"#{pr.id:06d}"
    title_text = pr.title[:70] + "..." if len(pr.title) > 70 else pr.title
    
    # Determine title color based on draft status
    title_color = "bright_black" if pr.is_draft else "blue"
    
    # Create panel title
    panel_title = Text()
    panel_title.append(pr_number, style="bright_black")
    panel_title.append(" ", style="")
    panel_title.append(title_text, style=title_color)
    
    # Create content sections
    content_lines = []
    
    # Status line
    open_text, open_color = compute_open_status(pr)
    status_line = Text()
    status_line.append(f"[{open_text}]", style=get_rich_color(open_color))
    
    # Add checks status
    if pr.checks and checks_mode != "none":
        checks_summary = _get_checks_summary(pr.checks)
        status_line.append(" ")
        status_line.append(checks_summary["text"], style=checks_summary["style"])
    
    # Add review status
    if pr.reviews and review_mode != "none":
        review_summary = _get_review_summary(pr.reviews)
        status_line.append(" ")
        status_line.append(review_summary["text"], style=review_summary["style"])
    
    content_lines.append(status_line)
    
    # Author line
    author_color = get_author_color(pr.author)
    author_line = Text()
    author_line.append("Author: ", style="bright_black")
    author_line.append(pr.author, style=get_rich_color(author_color))
    content_lines.append(author_line)
    
    # Metrics line
    if pr.additions or pr.deletions or pr.changed_files:
        metrics_line = Text()
        metrics_line.append("Changes: ", style="bright_black")
        metrics_line.append(f"+{pr.additions}", style="green")
        metrics_line.append(" ", style="")
        metrics_line.append(f"-{pr.deletions}", style="red")
        metrics_line.append(" ", style="")
        metrics_line.append(f"({pr.changed_files} files)", style="blue")
        content_lines.append(metrics_line)
    
    # Labels
    if pr.labels and labels_mode != "none":
        labels_line = Text()
        labels_line.append("Labels: ", style="bright_black")
        for i, label in enumerate(pr.labels):
            if i > 0:
                labels_line.append(", ", style="")
            labels_line.append(label, style="cyan")
        content_lines.append(labels_line)
    
    # Branch
    if pr.branch:
        branch_line = Text()
        branch_line.append("Branch: ", style="bright_black")
        branch_line.append(pr.branch, style="yellow")
        content_lines.append(branch_line)
    
    # Combine content
    content = Text("\n").join(content_lines)
    
    # Create panel with appropriate border style
    border_style = "green" if open_text == "READY" else "yellow" if pr.is_draft else "white"
    
    return Panel(
        content,
        title=panel_title,
        title_align="left",
        border_style=border_style,
        box=ROUNDED,
        padding=(0, 1),
    )


def _get_checks_summary(checks: List[Dict]) -> Dict[str, str]:
    """Get a summary of check statuses."""
    if not checks:
        return {"text": "○ No checks", "style": "bright_black"}
    
    # Count check statuses
    success = 0
    failure = 0
    pending = 0
    
    for check in checks:
        if isinstance(check, dict):
            status = check.get("status", "").upper()
            conclusion = check.get("conclusion", "").upper()
            
            if status == "COMPLETED":
                if conclusion in ["SUCCESS", "NEUTRAL", "SKIPPED"]:
                    success += 1
                else:
                    failure += 1
            else:
                pending += 1
    
    total = len(checks)
    
    if failure > 0:
        return {"text": f"✗ Checks {success}/{total}", "style": "red"}
    elif pending > 0:
        return {"text": f"◐ Checks {success}/{total}", "style": "yellow"}
    else:
        return {"text": f"✓ Checks {success}/{total}", "style": "green"}


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
    """Display PRs using Rich formatting."""
    console = Console()
    
    # Create header
    header = Text()
    header.append("🔍 ", style="blue")
    header.append("Pull Requests", style="bold blue")
    header.append(f" ({len(prs)} open)", style="bright_black")
    console.print(Panel(header, box=MINIMAL_HEAVY_HEAD, border_style="blue"))
    console.print()
    
    # Display each PR as a panel
    for pr in prs:
        panel = create_pr_panel(pr, options)
        console.print(panel)
        console.print()  # Space between panels


def create_pr_table(prs: List[PullRequest], options: Dict) -> Table:
    """Create a Rich table view of PRs."""
    table = Table(
        title="Pull Requests",
        title_style="bold blue",
        show_header=True,
        header_style="bold cyan",
        box=SIMPLE,
        expand=False,
    )
    
    # Add columns
    table.add_column("PR", style="bright_black", no_wrap=True)
    table.add_column("Title", style="blue", overflow="ellipsis", max_width=50)
    table.add_column("Status", justify="center")
    table.add_column("Checks", justify="center")
    table.add_column("Reviews", justify="center")
    table.add_column("Author", style="cyan")
    table.add_column("Changes", justify="right")
    
    # Add rows
    for pr in prs:
        # PR number
        pr_num = f"#{pr.id:06d}"
        
        # Title
        title = pr.title[:50] + "..." if len(pr.title) > 50 else pr.title
        if pr.is_draft:
            title = Text(title, style="bright_black")
        
        # Status
        open_text, open_color = compute_open_status(pr)
        status = Text(f"[{open_text}]", style=get_rich_color(open_color))
        
        # Checks
        checks_summary = _get_checks_summary(pr.checks)
        checks = Text(checks_summary["text"], style=checks_summary["style"])
        
        # Reviews
        review_summary = _get_review_summary(pr.reviews)
        reviews = Text(review_summary["text"], style=review_summary["style"])
        
        # Author
        author_color = get_author_color(pr.author)
        author = Text(pr.author, style=get_rich_color(author_color))
        
        # Changes
        changes = Text()
        changes.append(f"+{pr.additions}", style="green")
        changes.append("/", style="bright_black")
        changes.append(f"-{pr.deletions}", style="red")
        
        table.add_row(pr_num, title, status, checks, reviews, author, changes)
    
    return table


def display_prs_table(prs: List[PullRequest], options: Dict):
    """Display PRs in a table format."""
    console = Console()
    table = create_pr_table(prs, options)
    console.print(table)


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