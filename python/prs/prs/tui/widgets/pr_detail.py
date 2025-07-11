"""
PR Detail widget for displaying comprehensive pull request information.

Provides inline detail panel and full-screen detail views with
rich formatting and interactive elements.
"""

from typing import Optional, List
from textual.widgets import Static, DataTable, Label, Button
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.message import Message

from ...core.models import PullRequest


class PRDetailWidget(Static):
    """
    Detailed PR information widget.
    
    Shows comprehensive PR information including:
    - Basic metadata (title, author, dates)
    - Status indicators (checks, reviews, labels)
    - Statistics (additions, deletions, files)
    - Action buttons
    """
    
    # Reactive attributes
    pr: Optional[PullRequest] = reactive(None)
    compact_mode = reactive(False)
    show_actions = reactive(True)
    
    class ActionRequested(Message):
        """Message sent when an action is requested."""
        def __init__(self, action: str, pr: PullRequest) -> None:
            self.action = action
            self.pr = pr
            super().__init__()
    
    def __init__(self, pr: Optional[PullRequest] = None, **kwargs):
        super().__init__(**kwargs)
        if pr:
            self.pr = pr
    
    def compose(self):
        """Compose the PR detail widget."""
        if not self.pr:
            yield Static("[dim]No PR selected[/dim]", classes="no-selection")
            return
        
        with ScrollableContainer(classes="pr-detail-scroll"):
            # Header section
            yield self.create_header_section()
            
            # Status section
            yield self.create_status_section()
            
            # Metadata section
            yield self.create_metadata_section()
            
            # Checks section
            if self.pr.checks:
                yield self.create_checks_section()
            
            # Reviews section
            if self.pr.reviews:
                yield self.create_reviews_section()
            
            # Labels section
            if self.pr.labels:
                yield self.create_labels_section()
            
            # Actions section
            if self.show_actions:
                yield self.create_actions_section()
    
    def create_header_section(self) -> Container:
        """Create PR header with title and basic info."""
        container = Container(classes="detail-section header-section")
        
        with container:
            # PR title
            title_text = self.pr.title
            if getattr(self.pr, 'is_draft', False):
                title_text = f"[yellow]DRAFT[/yellow] {title_text}"
            
            yield Label(f"[bold]{title_text}[/bold]", classes="pr-title")
            
            # PR number and state
            state_color = {
                "open": "green",
                "closed": "red", 
                "merged": "purple"
            }.get(getattr(self.pr, 'state', 'open'), "gray")
            
            yield Label(
                f"[cyan]#{self.pr.id}[/cyan] • [{state_color}]{getattr(self.pr, 'state', 'open').upper()}[/{state_color}]",
                classes="pr-meta"
            )
            
            # Author and branch
            branch_text = getattr(self.pr, 'branch', 'unknown')
            yield Label(
                f"[green]@{self.pr.author}[/green] wants to merge [yellow]{branch_text}[/yellow]",
                classes="pr-author"
            )
        
        return container
    
    def create_status_section(self) -> Container:
        """Create status indicators section."""
        container = Container(classes="detail-section")
        
        with container:
            yield Label("[bold]Status[/bold]", classes="section-title")
            
            # Calculate status indicators
            checks_passing = sum(1 for check in self.pr.checks 
                               if check.get('conclusion') == 'success' or check.get('status') == 'completed')
            checks_failing = sum(1 for check in self.pr.checks 
                               if check.get('conclusion') in ['failure', 'error'])
            checks_pending = len(self.pr.checks) - checks_passing - checks_failing
            
            reviews_approved = sum(1 for review in self.pr.reviews 
                                 if review.get('state') == 'approved')
            reviews_requested = sum(1 for review in self.pr.reviews 
                                  if review.get('state') == 'review_requested')
            reviews_changes = sum(1 for review in self.pr.reviews 
                                if review.get('state') == 'changes_requested')
            
            # Status indicators
            status_items = []
            
            if checks_passing > 0:
                status_items.append(f"[green]✓ {checks_passing} checks passing[/green]")
            if checks_failing > 0:
                status_items.append(f"[red]✗ {checks_failing} checks failing[/red]")
            if checks_pending > 0:
                status_items.append(f"[yellow]⏳ {checks_pending} checks pending[/yellow]")
            
            if reviews_approved > 0:
                status_items.append(f"[green]✓ {reviews_approved} approved[/green]")
            if reviews_changes > 0:
                status_items.append(f"[red]⚠ {reviews_changes} changes requested[/red]")
            if reviews_requested > 0:
                status_items.append(f"[yellow]? {reviews_requested} reviews requested[/yellow]")
            
            if not status_items:
                status_items.append("[dim]No status information[/dim]")
            
            for item in status_items:
                yield Label(item, classes="status-item")
        
        return container
    
    def create_metadata_section(self) -> Container:
        """Create metadata section with dates and statistics."""
        container = Container(classes="detail-section")
        
        with container:
            yield Label("[bold]Details[/bold]", classes="section-title")
            
            # Dates
            created_at = getattr(self.pr, 'created_at', None)
            updated_at = getattr(self.pr, 'updated_at', None)
            
            if created_at:
                yield Label(f"Created: [dim]{created_at}[/dim]", classes="meta-item")
            if updated_at:
                yield Label(f"Updated: [dim]{updated_at}[/dim]", classes="meta-item")
            
            # Statistics
            additions = getattr(self.pr, 'additions', 0)
            deletions = getattr(self.pr, 'deletions', 0)
            changed_files = getattr(self.pr, 'changed_files', 0)
            
            yield Label(
                f"[green]+{additions}[/green] [red]-{deletions}[/red] "
                f"in [cyan]{changed_files}[/cyan] files",
                classes="meta-item"
            )
            
            # Commits
            commits = getattr(self.pr, 'commits', [])
            commit_count = len(commits) if commits else 0
            yield Label(f"[yellow]{commit_count}[/yellow] commits", classes="meta-item")
            
            # URL
            if not self.compact_mode:
                yield Label(
                    f"[link={self.pr.url}]View on GitHub[/link]",
                    classes="meta-item"
                )
        
        return container
    
    def create_checks_section(self) -> Container:
        """Create checks status section."""
        container = Container(classes="detail-section")
        
        with container:
            yield Label("[bold]Checks[/bold]", classes="section-title")
            
            # Group checks by status
            passing_checks = []
            failing_checks = []
            pending_checks = []
            
            for check in self.pr.checks:
                status = check.get('conclusion', check.get('status', 'unknown'))
                name = check.get('name', 'Unknown Check')
                
                if status in ['success', 'completed']:
                    passing_checks.append(name)
                elif status in ['failure', 'error', 'failed']:
                    failing_checks.append(name)
                else:
                    pending_checks.append(name)
            
            # Display grouped checks
            if passing_checks:
                yield Label(f"[green]✓[/green] Passing ({len(passing_checks)}):", classes="check-group")
                for check in passing_checks[:3]:  # Show first 3
                    yield Label(f"  • {check}", classes="check-item")
                if len(passing_checks) > 3:
                    yield Label(f"  • ... and {len(passing_checks) - 3} more", classes="check-item text-muted")
            
            if failing_checks:
                yield Label(f"[red]✗[/red] Failing ({len(failing_checks)}):", classes="check-group")
                for check in failing_checks[:3]:  # Show first 3
                    yield Label(f"  • {check}", classes="check-item")
                if len(failing_checks) > 3:
                    yield Label(f"  • ... and {len(failing_checks) - 3} more", classes="check-item text-muted")
            
            if pending_checks:
                yield Label(f"[yellow]⏳[/yellow] Pending ({len(pending_checks)}):", classes="check-group")
                for check in pending_checks[:3]:  # Show first 3
                    yield Label(f"  • {check}", classes="check-item")
                if len(pending_checks) > 3:
                    yield Label(f"  • ... and {len(pending_checks) - 3} more", classes="check-item text-muted")
        
        return container
    
    def create_reviews_section(self) -> Container:
        """Create reviews section."""
        container = Container(classes="detail-section")
        
        with container:
            yield Label("[bold]Reviews[/bold]", classes="section-title")
            
            # Group reviews by state
            approved_reviews = []
            changes_requested = []
            commented_reviews = []
            
            for review in self.pr.reviews:
                state = review.get('state', 'unknown')
                reviewer = review.get('user', {}).get('login', 'Unknown')
                
                if state == 'approved':
                    approved_reviews.append(reviewer)
                elif state == 'changes_requested':
                    changes_requested.append(reviewer)
                elif state == 'commented':
                    commented_reviews.append(reviewer)
            
            # Display reviews
            if approved_reviews:
                yield Label(f"[green]✓[/green] Approved by:", classes="review-group")
                for reviewer in approved_reviews:
                    yield Label(f"  • @{reviewer}", classes="review-item")
            
            if changes_requested:
                yield Label(f"[red]⚠[/red] Changes requested by:", classes="review-group")
                for reviewer in changes_requested:
                    yield Label(f"  • @{reviewer}", classes="review-item")
            
            if commented_reviews:
                yield Label(f"[blue]💬[/blue] Commented by:", classes="review-group")
                for reviewer in commented_reviews:
                    yield Label(f"  • @{reviewer}", classes="review-item")
            
            if not (approved_reviews or changes_requested or commented_reviews):
                yield Label("[dim]No reviews yet[/dim]", classes="review-item")
        
        return container
    
    def create_labels_section(self) -> Container:
        """Create labels section."""
        container = Container(classes="detail-section")
        
        with container:
            yield Label("[bold]Labels[/bold]", classes="section-title")
            
            # Display labels
            labels_text = []
            for label in self.pr.labels:
                labels_text.append(f"[blue]{label}[/blue]")
            
            if labels_text:
                yield Label(" • ".join(labels_text), classes="labels-list")
            else:
                yield Label("[dim]No labels[/dim]", classes="labels-list")
        
        return container
    
    def create_actions_section(self) -> Container:
        """Create action buttons section."""
        container = Container(classes="detail-section")
        
        with container:
            yield Label("[bold]Actions[/bold]", classes="section-title")
            
            with Horizontal(classes="actions-row"):
                yield Button("Open in Browser", id="open-browser", variant="primary")
                yield Button("Copy URL", id="copy-url", variant="default")
                yield Button("Refresh", id="refresh", variant="default")
        
        return container
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle action button presses."""
        if not self.pr:
            return
        
        action_map = {
            "open-browser": "open_browser",
            "copy-url": "copy_url", 
            "refresh": "refresh"
        }
        
        action = action_map.get(event.button.id)
        if action:
            self.post_message(self.ActionRequested(action, self.pr))
    
    def watch_pr(self, new_pr: Optional[PullRequest]) -> None:
        """React to PR changes by refreshing content."""
        if new_pr:
            self.refresh(recompose=True)
    
    def watch_compact_mode(self, compact: bool) -> None:
        """React to compact mode changes."""
        self.refresh(recompose=True)


class CompactPRDetailWidget(PRDetailWidget):
    """
    Compact version of the PR detail widget for smaller spaces.
    """
    
    def __init__(self, pr: Optional[PullRequest] = None, **kwargs):
        super().__init__(pr=pr, **kwargs)
        self.compact_mode = True
        self.show_actions = False
    
    def compose(self):
        """Compose compact PR detail widget."""
        if not self.pr:
            yield Static("No PR selected", classes="text-muted text-center")
            return
        
        # Compact header
        title = self.pr.title[:40] + "..." if len(self.pr.title) > 40 else self.pr.title
        if self.pr.is_draft:
            title = f"[DRAFT] {title}"
        
        yield Label(f"[bold]{title}[/bold]", classes="compact-title")
        yield Label(f"[cyan]#{self.pr.id}[/cyan] by [green]@{self.pr.author}[/green]", classes="compact-meta")
        
        # Quick status
        status_parts = []
        
        # Checks
        checks_total = len(self.pr.checks)
        if checks_total > 0:
            checks_passing = sum(1 for check in self.pr.checks 
                               if check.get('conclusion') == 'success')
            if checks_passing == checks_total:
                status_parts.append("[green]✓ All checks[/green]")
            else:
                status_parts.append(f"[yellow]⏳ {checks_passing}/{checks_total} checks[/yellow]")
        
        # Reviews
        reviews_approved = sum(1 for review in self.pr.reviews 
                             if review.get('state') == 'approved')
        if reviews_approved > 0:
            status_parts.append(f"[green]✓ {reviews_approved} approved[/green]")
        
        if status_parts:
            yield Label(" • ".join(status_parts), classes="compact-status")
        
        # Stats
        yield Label(
            f"[green]+{self.pr.additions}[/green] [red]-{self.pr.deletions}[/red] "
            f"in {self.pr.changed_files} files",
            classes="compact-stats"
        )