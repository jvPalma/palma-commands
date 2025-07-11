"""
Pull Request list widget for the PRS TUI application.

Displays a list of pull requests with navigation and selection capabilities.
"""

from typing import List, Optional, Callable
from datetime import datetime

from textual.widgets import Static, ListView, ListItem, Label
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding

from prs.core.models import PullRequest


class PRListItem(Static):
    """
    Individual pull request item in the list.
    """
    
    def __init__(self, pr: PullRequest, **kwargs):
        super().__init__(**kwargs)
        self.pr = pr
        self.can_focus = True
        self.selected = False
        # Debug log
        with open('/tmp/pr_debug.log', 'a') as f:
            f.write(f"PRListItem created for PR: {pr.title} (ID: {pr.id})\n")
    
    def compose(self):
        """Compose the PR item layout."""
        # Create a horizontal layout with status indicators and content
        with Horizontal(classes="pr-item-container"):
            # Status indicators column
            with Vertical(classes="pr-status-column"):
                yield Static(self.render_status_indicators(), classes="pr-status")
            
            # Main content column
            with Vertical(classes="pr-content-column"):
                # PR header with number and title
                yield Static(self.render_pr_header_line(), classes="pr-header")
                # PR metadata
                yield Static(self.render_pr_meta(), classes="pr-meta")
    
    def render_status_indicators(self) -> str:
        """Render compact status indicators."""
        indicators = []
        
        # Draft indicator
        if getattr(self.pr, 'is_draft', False):
            indicators.append("[dim yellow]D[/dim yellow]")
        
        # CI status
        if self.pr.checks:
            check_statuses = [check.get('status', 'unknown') for check in self.pr.checks]
            if 'failure' in check_statuses or 'error' in check_statuses:
                indicators.append("[red]✗[/red]")
            elif 'pending' in check_statuses or 'in_progress' in check_statuses:
                indicators.append("[yellow]⟳[/yellow]")
            elif all(status == 'success' for status in check_statuses):
                indicators.append("[green]✓[/green]")
            else:
                indicators.append("[dim]?[/dim]")
        
        # Review status
        if self.pr.reviews:
            review_states = [review.get('state', '') for review in self.pr.reviews]
            if 'APPROVED' in review_states:
                indicators.append("[green]👍[/green]")
            elif 'CHANGES_REQUESTED' in review_states:
                indicators.append("[red]👎[/red]")
            elif 'COMMENTED' in review_states:
                indicators.append("[yellow]💬[/yellow]")
        
        # Return indicators stacked vertically
        return "\n".join(indicators) if indicators else "[dim]•[/dim]"
    
    def render_pr_header_line(self) -> str:
        """Render PR number and title on one line."""
        # PR number
        pr_num = f"[bold cyan]#{self.pr.id}[/bold cyan]"
        
        # PR title
        title = self.pr.title
        if len(title) > 70:
            title = title[:67] + "..."
        
        return f"{pr_num} {title}"
    
    def render_pr_header(self) -> str:
        """Render PR number and status indicators."""
        # PR number
        pr_num = f"[bold cyan]#{self.pr.id}[/bold cyan]"
        
        # Draft indicator
        if getattr(self.pr, 'is_draft', False):
            pr_num += " [dim yellow]DRAFT[/dim yellow]"
        
        # Status indicators
        status_parts = []
        
        # CI status
        if self.pr.checks:
            check_statuses = [check.get('status', 'unknown') for check in self.pr.checks]
            if 'failure' in check_statuses or 'error' in check_statuses:
                status_parts.append("[red]✗[/red]")
            elif 'pending' in check_statuses or 'in_progress' in check_statuses:
                status_parts.append("[yellow]⟳[/yellow]")
            elif all(status == 'success' for status in check_statuses):
                status_parts.append("[green]✓[/green]")
            else:
                status_parts.append("[dim]?[/dim]")
        
        # Review status
        if self.pr.reviews:
            review_states = [review.get('state', '') for review in self.pr.reviews]
            if 'APPROVED' in review_states:
                status_parts.append("[green]👍[/green]")
            elif 'CHANGES_REQUESTED' in review_states:
                status_parts.append("[red]👎[/red]")
            elif 'COMMENTED' in review_states:
                status_parts.append("[yellow]💬[/yellow]")
        
        status_str = "".join(status_parts) if status_parts else ""
        
        return f"{pr_num} {status_str}".strip()
    
    def render_pr_title(self) -> str:
        """Render PR title."""
        title = self.pr.title
        
        # Truncate if too long
        if len(title) > 60:
            title = title[:57] + "..."
        
        return f"[bold]{title}[/bold]"
    
    def render_pr_meta(self) -> str:
        """Render PR metadata (author, labels, etc.)."""
        parts = []
        
        # Author
        parts.append(f"[cyan]@{self.pr.author}[/cyan]")
        
        # Branch
        if hasattr(self.pr, 'branch') and self.pr.branch:
            branch = self.pr.branch
            if len(branch) > 20:
                branch = branch[:17] + "..."
            parts.append(f"[dim]{branch}[/dim]")
        
        # Labels (first few)
        if self.pr.labels:
            label_display = []
            for label in self.pr.labels[:3]:
                if len(label) > 15:
                    label = label[:12] + "..."
                label_display.append(f"[blue]{label}[/blue]")
            
            if len(self.pr.labels) > 3:
                label_display.append(f"[dim]+{len(self.pr.labels) - 3}[/dim]")
            
            parts.append(" ".join(label_display))
        
        # Created/updated time
        if hasattr(self.pr, 'created_at') and self.pr.created_at:
            try:
                created = datetime.fromisoformat(self.pr.created_at.replace('Z', '+00:00'))
                time_ago = self.format_time_ago(created)
                parts.append(f"[dim]{time_ago}[/dim]")
            except (ValueError, AttributeError):
                pass
        
        return " • ".join(parts)
    
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
    
    def on_click(self, event) -> None:
        """Handle click events on the PR item."""
        self.post_message(PRListWidget.PRSelected(self.pr, 0))
    
    def on_focus(self, event) -> None:
        """Handle focus events on the PR item."""
        self.selected = True
        self.add_class("selected")
        self.post_message(PRListWidget.PRSelected(self.pr, 0))
    
    def on_blur(self, event) -> None:
        """Handle blur events on the PR item."""
        self.selected = False
        self.remove_class("selected")
    
    def on_key(self, event) -> None:
        """Handle key events on the PR item."""
        if event.key == "enter":
            self.post_message(PRListWidget.PRActivated(self.pr, 0))
        elif event.key == "space":
            self.post_message(PRListWidget.PRSelected(self.pr, 0))


class PRListWidget(Static):
    """
    Widget for displaying and navigating pull requests.
    """
    
    # Reactive attributes
    pull_requests: List[PullRequest] = reactive([])
    selected_index = reactive(-1)
    loading = reactive(False)
    
    BINDINGS = [
        Binding("up,k", "cursor_up", "Up", show=False),
        Binding("down,j", "cursor_down", "Down", show=False),
        Binding("enter", "select_item", "Select", show=False),
        Binding("space", "toggle_selection", "Toggle", show=False),
        Binding("o", "open_in_browser", "Open", show=False),
        Binding("home", "first_item", "First", show=False),
        Binding("end", "last_item", "Last", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
    ]
    
    class PRSelected(Message):
        """Message sent when a PR is selected."""
        
        def __init__(self, pr: PullRequest, index: int):
            super().__init__()
            self.pr = pr
            self.index = index
    
    class PRActivated(Message):
        """Message sent when a PR is activated (double-click, enter)."""
        
        def __init__(self, pr: PullRequest, index: int):
            super().__init__()
            self.pr = pr
            self.index = index
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.on_select_callback: Optional[Callable] = None
        self.on_activate_callback: Optional[Callable] = None
        self._refreshing_list = False
        self._pending_update = False
    
    def compose(self):
        """Compose the PR list layout."""
        # Start with empty content - will be populated by refresh_list
        return []
    
    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        # If there was a pending update, apply it now
        if self._pending_update:
            self._pending_update = False
            self.refresh_list()
    
    def update_pull_requests(self, prs: List[PullRequest]) -> None:
        """Update the list of pull requests."""
        # Debug log
        with open('/tmp/pr_debug.log', 'a') as f:
            f.write(f"update_pull_requests called with {len(prs)} PRs\n")
            for i, pr in enumerate(prs):
                f.write(f"  PR {i}: {pr.title} (ID: {pr.id})\n")
        
        self.pull_requests = prs
        self.selected_index = 0 if prs else -1
        
        # If not mounted yet, defer the update
        if not self.is_mounted:
            self._pending_update = True
        else:
            self.refresh_list()
    
    def set_loading(self, loading: bool) -> None:
        """Set loading state."""
        self.loading = loading
        
        # If not mounted yet, defer the update
        if not self.is_mounted:
            self._pending_update = True
        else:
            self.refresh_list()
    
    def refresh_list(self) -> None:
        """Refresh the list display using ListView."""
        if self._refreshing_list:
            return
            
        self._refreshing_list = True
        try:
            # Debug log
            with open('/tmp/pr_debug.log', 'a') as f:
                f.write(f"refresh_list called - loading: {self.loading}, PRs: {len(self.pull_requests)}\n")
            
            # Clear all existing content to avoid ID conflicts
            for child in list(self.children):
                child.remove()
            
            # Show appropriate widget based on state
            if self.loading:
                loading_msg = Static("[cyan]Loading PRs...[/cyan]", classes="loading-message")
                self.mount(loading_msg)
            elif not self.pull_requests:
                empty_msg = Static("[dim]No pull requests found[/dim]", classes="empty-message")
                self.mount(empty_msg)
            else:
                # Use enhanced PRListItem widgets directly (skip ListView for now)
                try:
                    with open('/tmp/pr_debug.log', 'a') as f:
                        f.write(f"Using enhanced PRListItem widgets for {len(self.pull_requests)} PRs\n")
                    
                    # Create container for PR items
                    container = Vertical(classes="pr-container")
                    self.mount(container)
                    
                    # Add each PR as an enhanced PRListItem
                    for i, pr in enumerate(self.pull_requests):
                        pr_item = PRListItem(pr)
                        container.mount(pr_item)
                        
                        # Focus the first item by default
                        if i == 0:
                            pr_item.add_class("selected")
                            pr_item.selected = True
                        
                        with open('/tmp/pr_debug.log', 'a') as f:
                            f.write(f"Mounted enhanced PR {i}: {pr.title[:50]}...\n")
                    
                except Exception as e:
                    with open('/tmp/pr_debug.log', 'a') as f:
                        f.write(f"Enhanced PRListItem approach failed: {str(e)}\n")
                    
                    # Fallback to simple display
                    all_prs_text = "\n".join([f"#{pr.id}: {pr.title}" for pr in self.pull_requests])
                    final_msg = Static(f"PRs Found:\n{all_prs_text}")
                    self.mount(final_msg)
                    
        finally:
            self._refreshing_list = False
    
    def _populate_list_view(self, list_view: ListView) -> None:
        """Populate ListView after it's mounted."""
        try:
            with open('/tmp/pr_debug.log', 'a') as f:
                f.write(f"_populate_list_view called with {len(self.pull_requests)} PRs\n")
            
            # Clear existing items
            list_view.clear()
            
            # Add PR items to the ListView using proper PRListItem
            for i, pr in enumerate(self.pull_requests):
                with open('/tmp/pr_debug.log', 'a') as f:
                    f.write(f"Adding PR {i}: {pr.title}\n")
                
                # Create PRListItem with full PR data
                pr_item = PRListItem(pr)
                list_view.append(pr_item)
            
            # Set initial selection
            if self.selected_index >= 0 and self.selected_index < len(self.pull_requests):
                try:
                    list_view.index = self.selected_index
                except Exception as select_error:
                    with open('/tmp/pr_debug.log', 'a') as f:
                        f.write(f"Error setting ListView selection: {str(select_error)}\n")
            
            with open('/tmp/pr_debug.log', 'a') as f:
                f.write(f"ListView populated successfully with {len(self.pull_requests)} items\n")
                
        except Exception as e:
            with open('/tmp/pr_debug.log', 'a') as f:
                f.write(f"Error populating ListView: {str(e)}\n")
    
    def get_selected_pr(self) -> Optional[PullRequest]:
        """Get currently selected PR."""
        if 0 <= self.selected_index < len(self.pull_requests):
            return self.pull_requests[self.selected_index]
        return None
    
    def select_pr(self, index: int) -> None:
        """Select PR at given index."""
        if 0 <= index < len(self.pull_requests):
            self.selected_index = index
            pr = self.pull_requests[index]
            
            # Update list view selection
            try:
                list_view = self.query_one("#pr-list-view", ListView)
                list_view.index = index
            except Exception:
                pass
            
            # Emit selection message
            self.post_message(self.PRSelected(pr, index))
            
            # Call callback if set
            if self.on_select_callback:
                self.on_select_callback(pr, index)
    
    def activate_pr(self, index: int) -> None:
        """Activate PR at given index."""
        if 0 <= index < len(self.pull_requests):
            pr = self.pull_requests[index]
            
            # Emit activation message
            self.post_message(self.PRActivated(pr, index))
            
            # Call callback if set
            if self.on_activate_callback:
                self.on_activate_callback(pr, index)
    
    def set_callbacks(self, on_select: Optional[Callable] = None, on_activate: Optional[Callable] = None) -> None:
        """Set callback functions."""
        self.on_select_callback = on_select
        self.on_activate_callback = on_activate
    
    # Event handlers
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle list view selection."""
        if event.item and hasattr(event.item, 'pr'):
            try:
                index = self.pull_requests.index(event.item.pr)
                self.activate_pr(index)
            except ValueError:
                # PR not in current list, possibly due to filtering
                pass
    
    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle list view highlighting."""
        if event.item and hasattr(event.item, 'pr'):
            try:
                index = self.pull_requests.index(event.item.pr)
                self.selected_index = index
                self.post_message(self.PRSelected(event.item.pr, index))
            except ValueError:
                # PR not in current list, possibly due to filtering
                pass
    
    # Action handlers
    def action_cursor_up(self) -> None:
        """Move cursor up."""
        if self.pull_requests:
            try:
                list_view = self.query_one("#pr-list-view", ListView)
                if list_view.index > 0:
                    list_view.index -= 1
                    self.selected_index = list_view.index
                    pr = self.pull_requests[self.selected_index]
                    self.post_message(self.PRSelected(pr, self.selected_index))
            except Exception:
                # Fallback to direct index manipulation
                if self.selected_index > 0:
                    self.select_pr(self.selected_index - 1)
    
    def action_cursor_down(self) -> None:
        """Move cursor down."""
        if self.pull_requests:
            try:
                list_view = self.query_one("#pr-list-view", ListView)
                if list_view.index < len(self.pull_requests) - 1:
                    list_view.index += 1
                    self.selected_index = list_view.index
                    pr = self.pull_requests[self.selected_index]
                    self.post_message(self.PRSelected(pr, self.selected_index))
            except Exception:
                # Fallback to direct index manipulation
                if self.selected_index < len(self.pull_requests) - 1:
                    self.select_pr(self.selected_index + 1)
    
    def action_select_item(self) -> None:
        """Select current item."""
        if self.selected_index >= 0:
            self.activate_pr(self.selected_index)
    
    def action_toggle_selection(self) -> None:
        """Toggle selection of current item."""
        if self.selected_index >= 0:
            self.select_pr(self.selected_index)
    
    def action_open_in_browser(self) -> None:
        """Open current PR in browser."""
        pr = self.get_selected_pr()
        if pr:
            import webbrowser
            try:
                webbrowser.open(pr.url)
            except Exception as e:
                # Could emit error message here
                pass
    
    def action_first_item(self) -> None:
        """Go to first item."""
        if self.pull_requests:
            try:
                list_view = self.query_one("#pr-list-view", ListView)
                list_view.index = 0
                self.selected_index = 0
                pr = self.pull_requests[0]
                self.post_message(self.PRSelected(pr, 0))
            except Exception:
                self.select_pr(0)
    
    def action_last_item(self) -> None:
        """Go to last item."""
        if self.pull_requests:
            try:
                list_view = self.query_one("#pr-list-view", ListView)
                last_index = len(self.pull_requests) - 1
                list_view.index = last_index
                self.selected_index = last_index
                pr = self.pull_requests[last_index]
                self.post_message(self.PRSelected(pr, last_index))
            except Exception:
                self.select_pr(len(self.pull_requests) - 1)
    
    def action_page_up(self) -> None:
        """Page up."""
        if self.pull_requests:
            try:
                list_view = self.query_one("#pr-list-view", ListView)
                new_index = max(0, list_view.index - 10)
                list_view.index = new_index
                self.selected_index = new_index
                pr = self.pull_requests[new_index]
                self.post_message(self.PRSelected(pr, new_index))
            except Exception:
                new_index = max(0, self.selected_index - 10)
                self.select_pr(new_index)
    
    def action_page_down(self) -> None:
        """Page down."""
        if self.pull_requests:
            try:
                list_view = self.query_one("#pr-list-view", ListView)
                new_index = min(len(self.pull_requests) - 1, list_view.index + 10)
                list_view.index = new_index
                self.selected_index = new_index
                pr = self.pull_requests[new_index]
                self.post_message(self.PRSelected(pr, new_index))
            except Exception:
                new_index = min(len(self.pull_requests) - 1, self.selected_index + 10)
                self.select_pr(new_index)
    
    # Watchers
    def watch_pull_requests(self, new_value: List[PullRequest]) -> None:
        """React to PR list changes."""
        if not self._refreshing_list:
            self.refresh_list()
    
    def watch_loading(self, new_value: bool) -> None:
        """React to loading state changes."""
        if not self._refreshing_list:
            self.refresh_list()


class CompactPRListWidget(PRListWidget):
    """
    Compact version of the PR list for smaller terminals.
    """
    
    def compose(self):
        """Compose compact PR list layout."""
        # Always create a stable structure
        yield Static("[cyan]Loading...[/cyan]", classes="loading-message compact", id="loading-msg")
        yield Static("[dim]No PRs[/dim]", classes="empty-message compact", id="empty-msg")
        yield ListView(id="pr-list", classes="pr-list compact")
        yield Static("", classes="error-message compact", id="error-msg")
    
    def refresh_list(self) -> None:
        """Refresh the list display with compact items."""
        if self._refreshing_list:
            return
            
        self._refreshing_list = True
        try:
            # Debug: Write to a log file to see what's happening
            with open('/tmp/pr_debug.log', 'a') as f:
                f.write(f"CompactPRListWidget.refresh_list called - loading: {self.loading}, PRs: {len(self.pull_requests)}\n")
            
            # Get widgets
            try:
                loading_msg = self.query_one("#loading-msg", Static)
                empty_msg = self.query_one("#empty-msg", Static)
                list_view = self.query_one("#pr-list", ListView)
                error_msg = self.query_one("#error-msg", Static)
            except Exception as e:
                with open('/tmp/pr_debug.log', 'a') as f:
                    f.write(f"Error querying compact widgets: {str(e)}\n")
                return
            
            # Check if ListView is properly mounted and ready
            if not (list_view.is_mounted and self.is_mounted):
                with open('/tmp/pr_debug.log', 'a') as f:
                    f.write(f"Compact ListView or parent not mounted yet (list: {list_view.is_mounted}, parent: {self.is_mounted}), deferring update\n")
                # Defer the update until after mounting is complete
                self.call_after_refresh(self.refresh_list)
                return
            
            # Hide all widgets initially
            loading_msg.display = False
            empty_msg.display = False
            list_view.display = False
            error_msg.display = False
            
            # Show appropriate widget based on state
            if self.loading:
                loading_msg.display = True
            elif not self.pull_requests:
                empty_msg.display = True
            else:
                # Update ListView content with compact items and extra safety checks
                try:
                    # Clear existing items safely
                    if list_view.is_mounted:
                        list_view.clear()
                        
                        # Add new compact items only if ListView is still mounted after clear
                        if list_view.is_mounted:
                            for pr in self.pull_requests:
                                list_view.append(CompactPRListItem(pr))
                            
                            # Set initial selection after all items are added
                            if self.selected_index >= 0 and self.selected_index < len(self.pull_requests):
                                try:
                                    list_view.index = self.selected_index
                                except Exception as select_error:
                                    with open('/tmp/pr_debug.log', 'a') as f:
                                        f.write(f"Error setting compact ListView selection: {str(select_error)}\n")
                            
                            list_view.display = True
                        else:
                            with open('/tmp/pr_debug.log', 'a') as f:
                                f.write(f"Compact ListView became unmounted during update\n")
                    else:
                        with open('/tmp/pr_debug.log', 'a') as f:
                            f.write(f"Compact ListView not mounted when trying to update\n")
                    
                except Exception as e:
                    with open('/tmp/pr_debug.log', 'a') as f:
                        f.write(f"Error updating compact ListView: {str(e)}\n")
                    # Show error message
                    try:
                        error_msg.update(f"[red]Error loading PRs: {str(e)}[/red]")
                        error_msg.display = True
                    except Exception as err_error:
                        with open('/tmp/pr_debug.log', 'a') as f:
                            f.write(f"Error showing compact error message: {str(err_error)}\n")
                    
        finally:
            self._refreshing_list = False


class CompactPRListItem(PRListItem):
    """
    Compact version of PR list item.
    """
    
    def compose(self):
        """Compose compact PR item layout."""
        yield Static(f"{self.render_compact_pr()}", classes="pr-item compact")
    
    def render_compact_pr(self) -> str:
        """Render compact PR representation."""
        # PR number and title (truncated)
        title = self.pr.title
        if len(title) > 40:
            title = title[:37] + "..."
        
        # Basic status
        status = ""
        if getattr(self.pr, 'is_draft', False):
            status += "[dim]D[/dim]"
        
        if self.pr.checks:
            check_statuses = [check.get('status', 'unknown') for check in self.pr.checks]
            if 'failure' in check_statuses:
                status += "[red]✗[/red]"
            elif 'success' in check_statuses:
                status += "[green]✓[/green]"
            else:
                status += "[yellow]⟳[/yellow]"
        
        return f"[cyan]#{self.pr.id}[/cyan] {status} {title}"