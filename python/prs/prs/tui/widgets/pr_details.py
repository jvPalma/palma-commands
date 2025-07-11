"""
PR details widget for the PRS TUI application.

Displays comprehensive information about a selected pull request.
"""

from typing import Optional, List
from datetime import datetime

from textual.widgets import Static, Button, Label, TabbedContent, TabPane
from textual.containers import Vertical, Horizontal, Grid
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding

from prs.core.models import PullRequest


class PRDetailsWidget(Static):
    """
    Expandable details widget for showing comprehensive PR information.
    """
    
    # Reactive state
    selected_pr: Optional[PullRequest] = reactive(None)
    expanded = reactive(False)
    
    BINDINGS = [
        Binding("space", "toggle_expanded", "Toggle Details", show=False),
        Binding("escape", "collapse", "Collapse", show=False),
        Binding("o", "open_in_browser", "Open in Browser", show=False),
        Binding("c", "copy_url", "Copy URL", show=False),
    ]
    
    class ActionRequested(Message):
        """Message sent when an action is requested."""
        
        def __init__(self, action: str, pr: Optional[PullRequest] = None):
            super().__init__()
            self.action = action
            self.pr = pr
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.min_height = 3
        self.max_height = 20
    
    def compose(self):
        """Compose the PR details layout."""
        with Vertical(classes="pr-details"):
            # Header with toggle button
            with Horizontal(classes="details-header"):
                yield Button("📋 PR Details", id="toggle-details", classes="details-toggle")
                yield Static("", id="details-title", classes="details-title")
                yield Button("⬆", id="collapse-button", classes="collapse-button")
            
            # Collapsible content
            with TabbedContent(id="details-content", classes="details-content"):
                # Overview tab
                with TabPane("Overview", id="overview-tab"):
                    with Vertical(classes="overview-content"):
                        yield Static("", id="pr-overview", classes="pr-overview")
                        yield Static("", id="pr-metadata", classes="pr-metadata")
                
                # Checks tab
                with TabPane("Checks", id="checks-tab"):
                    with Vertical(classes="checks-content"):
                        yield Static("", id="checks-summary", classes="checks-summary")
                        yield Static("", id="checks-list", classes="checks-list")
                
                # Reviews tab
                with TabPane("Reviews", id="reviews-tab"):
                    with Vertical(classes="reviews-content"):
                        yield Static("", id="reviews-summary", classes="reviews-summary")
                        yield Static("", id="reviews-list", classes="reviews-list")
                
                # Files tab
                with TabPane("Files", id="files-tab"):
                    with Vertical(classes="files-content"):
                        yield Static("", id="files-summary", classes="files-summary")
                        yield Static("", id="files-list", classes="files-list")
    
    def on_mount(self):
        """Called when the widget is mounted."""
        self.set_expanded(False)
    
    def set_pr(self, pr: Optional[PullRequest]):
        """Set the PR to display details for."""
        self.selected_pr = pr
        if pr:
            self.update_details()
        else:
            self.clear_details()
    
    def set_expanded(self, expanded: bool):
        """Set the expanded state."""
        self.expanded = expanded
        
        try:
            content = self.query_one("#details-content", TabbedContent)
            collapse_button = self.query_one("#collapse-button", Button)
            
            if expanded:
                content.display = True
                collapse_button.label = "⬆"
                self.add_class("expanded")
            else:
                content.display = False
                collapse_button.label = "⬇"
                self.remove_class("expanded")
        except Exception:
            pass
    
    def update_details(self):
        """Update all detail displays with current PR data."""
        if not self.selected_pr:
            return
        
        self.update_title()
        self.update_overview()
        self.update_checks()
        self.update_reviews()
        self.update_files()
    
    def update_title(self):
        """Update the details title."""
        if not self.selected_pr:
            return
        
        try:
            title_widget = self.query_one("#details-title", Static)
            title_text = f"#{self.selected_pr.id}: {self.selected_pr.title[:50]}..."
            title_widget.update(f"[bold]{title_text}[/bold]")
        except Exception:
            pass
    
    def update_overview(self):
        """Update the overview tab content."""
        if not self.selected_pr:
            return
        
        try:
            overview = self.query_one("#pr-overview", Static)
            metadata = self.query_one("#pr-metadata", Static)
            
            pr = self.selected_pr
            
            # Overview content
            overview_text = f"""[bold cyan]#{pr.id}[/bold cyan] [bold]{pr.title}[/bold]
[dim]Author:[/dim] [cyan]@{pr.author}[/cyan]
[dim]Branch:[/dim] {getattr(pr, 'branch', 'unknown')}
[dim]URL:[/dim] {pr.url}"""
            
            if getattr(pr, 'is_draft', False):
                overview_text += "\n[yellow]⚠ Draft PR[/yellow]"
            
            overview.update(overview_text)
            
            # Metadata
            metadata_parts = []
            
            # Labels
            if pr.labels:
                label_text = " ".join([f"[blue]{label}[/blue]" for label in pr.labels[:5]])
                if len(pr.labels) > 5:
                    label_text += f" [dim]+{len(pr.labels) - 5} more[/dim]"
                metadata_parts.append(f"[dim]Labels:[/dim] {label_text}")
            
            # Created time
            if hasattr(pr, 'created_at') and pr.created_at:
                try:
                    created = datetime.fromisoformat(pr.created_at.replace('Z', '+00:00'))
                    time_ago = self.format_time_ago(created)
                    metadata_parts.append(f"[dim]Created:[/dim] {time_ago}")
                except (ValueError, AttributeError):
                    pass
            
            metadata.update("\n".join(metadata_parts))
            
        except Exception:
            pass
    
    def update_checks(self):
        """Update the checks tab content."""
        if not self.selected_pr:
            return
        
        try:
            summary = self.query_one("#checks-summary", Static)
            checks_list = self.query_one("#checks-list", Static)
            
            checks = self.selected_pr.checks or []
            
            if not checks:
                summary.update("[dim]No checks configured[/dim]")
                checks_list.update("")
                return
            
            # Summary
            passed = sum(1 for check in checks if check.get('status') == 'success')
            failed = sum(1 for check in checks if check.get('status') in ['failure', 'error'])
            pending = sum(1 for check in checks if check.get('status') in ['pending', 'in_progress'])
            
            summary_text = f"[green]✓ {passed}[/green] [red]✗ {failed}[/red] [yellow]⟳ {pending}[/yellow]"
            summary.update(summary_text)
            
            # Individual checks
            check_lines = []
            for check in checks:
                status = check.get('status', 'unknown')
                name = check.get('name', 'Unknown Check')
                
                if status == 'success':
                    icon = "[green]✓[/green]"
                elif status in ['failure', 'error']:
                    icon = "[red]✗[/red]"
                elif status in ['pending', 'in_progress']:
                    icon = "[yellow]⟳[/yellow]"
                else:
                    icon = "[dim]?[/dim]"
                
                check_lines.append(f"{icon} {name}")
            
            checks_list.update("\n".join(check_lines))
            
        except Exception:
            pass
    
    def update_reviews(self):
        """Update the reviews tab content."""
        if not self.selected_pr:
            return
        
        try:
            summary = self.query_one("#reviews-summary", Static)
            reviews_list = self.query_one("#reviews-list", Static)
            
            reviews = self.selected_pr.reviews or []
            
            if not reviews:
                summary.update("[dim]No reviews yet[/dim]")
                reviews_list.update("")
                return
            
            # Summary
            approved = sum(1 for review in reviews if review.get('state') == 'APPROVED')
            changes = sum(1 for review in reviews if review.get('state') == 'CHANGES_REQUESTED')
            commented = sum(1 for review in reviews if review.get('state') == 'COMMENTED')
            
            summary_text = f"[green]👍 {approved}[/green] [red]👎 {changes}[/red] [yellow]💬 {commented}[/yellow]"
            summary.update(summary_text)
            
            # Individual reviews
            review_lines = []
            for review in reviews:
                state = review.get('state', 'UNKNOWN')
                author = review.get('author', 'Unknown')
                
                if state == 'APPROVED':
                    icon = "[green]👍[/green]"
                elif state == 'CHANGES_REQUESTED':
                    icon = "[red]👎[/red]"
                elif state == 'COMMENTED':
                    icon = "[yellow]💬[/yellow]"
                else:
                    icon = "[dim]?[/dim]"
                
                review_lines.append(f"{icon} [cyan]@{author}[/cyan]")
            
            reviews_list.update("\n".join(review_lines))
            
        except Exception:
            pass
    
    def update_files(self):
        """Update the files tab content."""
        if not self.selected_pr:
            return
        
        try:
            summary = self.query_one("#files-summary", Static)
            files_list = self.query_one("#files-list", Static)
            
            # For now, show placeholder since file info isn't in the model
            summary.update("[dim]File information not available[/dim]")
            files_list.update("[dim]File diff view would be implemented here[/dim]")
            
        except Exception:
            pass
    
    def clear_details(self):
        """Clear all detail displays."""
        try:
            self.query_one("#details-title", Static).update("")
            self.query_one("#pr-overview", Static).update("[dim]No PR selected[/dim]")
            self.query_one("#pr-metadata", Static).update("")
            self.query_one("#checks-summary", Static).update("")
            self.query_one("#checks-list", Static).update("")
            self.query_one("#reviews-summary", Static).update("")
            self.query_one("#reviews-list", Static).update("")
            self.query_one("#files-summary", Static).update("")
            self.query_one("#files-list", Static).update("")
        except Exception:
            pass
    
    def format_time_ago(self, dt: datetime) -> str:
        """Format datetime as 'time ago' string."""
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        diff = now - dt
        
        if diff.days > 7:
            return f"{diff.days // 7}w ago"
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "now"
    
    # Event handlers
    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events."""
        if event.button.id == "toggle-details":
            self.action_toggle_expanded()
        elif event.button.id == "collapse-button":
            self.action_collapse()
    
    # Action handlers
    def action_toggle_expanded(self):
        """Toggle the expanded state."""
        self.set_expanded(not self.expanded)
    
    def action_collapse(self):
        """Collapse the details panel."""
        self.set_expanded(False)
    
    def action_open_in_browser(self):
        """Open the selected PR in browser."""
        if self.selected_pr:
            self.post_message(self.ActionRequested("open_in_browser", self.selected_pr))
    
    def action_copy_url(self):
        """Copy the PR URL to clipboard."""
        if self.selected_pr:
            self.post_message(self.ActionRequested("copy_url", self.selected_pr))
    
    # Watchers
    def watch_selected_pr(self, new_value: Optional[PullRequest]):
        """React to PR selection changes."""
        if new_value:
            self.update_details()
        else:
            self.clear_details()
    
    def watch_expanded(self, new_value: bool):
        """React to expanded state changes."""
        # Already handled in set_expanded
        pass