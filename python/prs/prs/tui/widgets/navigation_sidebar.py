"""
Navigation sidebar widget for the PRS TUI application.

Provides quick filters, repository information, and action shortcuts.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from textual.widgets import Static, Button, Label
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding

from prs.config import get


class NavigationSidebar(Static):
    """
    Navigation sidebar with repository info, filters, and shortcuts.
    """
    
    # Reactive state
    total_prs = reactive(0)
    filtered_prs = reactive(0)
    show_drafts = reactive(False)
    auto_refresh = reactive(True)
    last_refresh: Optional[datetime] = reactive(None)
    
    BINDINGS = [
        Binding("1", "filter_open", "Open PRs", show=False),
        Binding("2", "filter_drafts", "Drafts", show=False),
        Binding("3", "filter_my_prs", "My PRs", show=False),
        Binding("4", "filter_reviewed", "Reviewed", show=False),
        Binding("5", "filter_approved", "Approved", show=False),
        Binding("ctrl+r", "toggle_auto_refresh", "Auto Refresh", show=False),
    ]
    
    class FilterChanged(Message):
        """Message sent when filter selection changes."""
        
        def __init__(self, filter_type: str, value: Any):
            super().__init__()
            self.filter_type = filter_type
            self.value = value
    
    class ActionRequested(Message):
        """Message sent when an action is requested."""
        
        def __init__(self, action: str):
            super().__init__()
            self.action = action
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_filter = "all"
        self.repository_name = ""
        self.username = ""
        self._load_config()
    
    def _load_config(self):
        """Load configuration for repository info."""
        try:
            self.repository_name = get("git", "repo_name", fallback="Unknown Repo")
            self.username = get("git", "username", fallback="Unknown User")
        except Exception:
            self.repository_name = "Unknown Repo"
            self.username = "Unknown User"
    
    def compose(self):
        """Compose the navigation sidebar layout."""
        with Vertical(classes="navigation-sidebar"):
            # Repository header
            with Vertical(classes="repo-header"):
                yield Label(f"[bold cyan]{self.repository_name}[/bold cyan]", classes="repo-name")
                yield Label(f"[dim]@{self.username}[/dim]", classes="username")
                yield Static("─" * 20, classes="separator")
            
            # Quick filters
            with Vertical(classes="quick-filters"):
                yield Label("[bold]Quick Filters[/bold]", classes="section-title")
                
                yield Button("📋 All PRs", id="filter-all", classes="filter-button active")
                yield Button("🟢 Open PRs", id="filter-open", classes="filter-button")
                yield Button("📝 Drafts", id="filter-drafts", classes="filter-button")
                yield Button("👤 My PRs", id="filter-my-prs", classes="filter-button")
                yield Button("👀 Reviewed", id="filter-reviewed", classes="filter-button")
                yield Button("✅ Approved", id="filter-approved", classes="filter-button")
                yield Button("🔴 Failed CI", id="filter-failed-ci", classes="filter-button")
                
                yield Static("─" * 20, classes="separator")
            
            # Status summary
            with Vertical(classes="status-summary"):
                yield Label("[bold]Status Summary[/bold]", classes="section-title")
                yield Static("", id="total-count", classes="count-display")
                yield Static("", id="filtered-count", classes="count-display")
                yield Static("", id="refresh-status", classes="refresh-status")
                
                yield Static("─" * 20, classes="separator")
            
            # Keyboard shortcuts
            with Vertical(classes="keyboard-shortcuts"):
                yield Label("[bold]Shortcuts[/bold]", classes="section-title")
                yield Static("[dim]↑/↓[/dim] Navigate", classes="shortcut-item")
                yield Static("[dim]Enter[/dim] Open PR", classes="shortcut-item")
                yield Static("[dim]Space[/dim] Toggle Details", classes="shortcut-item")
                yield Static("[dim]R[/dim] Refresh", classes="shortcut-item")
                yield Static("[dim]F[/dim] Filter", classes="shortcut-item")
                yield Static("[dim]D[/dim] Toggle Drafts", classes="shortcut-item")
                yield Static("[dim]Q[/dim] Quit", classes="shortcut-item")
                
                yield Static("─" * 20, classes="separator")
            
            # Actions
            with Vertical(classes="actions"):
                yield Label("[bold]Actions[/bold]", classes="section-title")
                yield Button("🔄 Refresh", id="action-refresh", classes="action-button")
                yield Button("🔧 Settings", id="action-settings", classes="action-button")
                yield Button("❓ Help", id="action-help", classes="action-button")
    
    def on_mount(self):
        """Called when the widget is mounted."""
        self.update_displays()
    
    def update_displays(self):
        """Update all dynamic displays."""
        self.update_count_displays()
        self.update_refresh_status()
    
    def update_count_displays(self):
        """Update PR count displays."""
        try:
            total_display = self.query_one("#total-count", Static)
            filtered_display = self.query_one("#filtered-count", Static)
            
            total_display.update(f"[cyan]Total:[/cyan] {self.total_prs}")
            if self.filtered_prs != self.total_prs:
                filtered_display.update(f"[yellow]Filtered:[/yellow] {self.filtered_prs}")
            else:
                filtered_display.update("")
        except Exception:
            pass
    
    def update_refresh_status(self):
        """Update refresh status display."""
        try:
            refresh_status = self.query_one("#refresh-status", Static)
            
            if self.auto_refresh:
                status_text = "[green]Auto:[/green] ON"
            else:
                status_text = "[dim]Auto:[/dim] OFF"
            
            if self.last_refresh:
                time_str = self.last_refresh.strftime("%H:%M:%S")
                status_text += f"\n[dim]Last: {time_str}[/dim]"
            
            refresh_status.update(status_text)
        except Exception:
            pass
    
    def set_active_filter(self, filter_type: str):
        """Set the active filter and update button states."""
        self.selected_filter = filter_type
        
        # Update button states
        for button in self.query(Button):
            if button.id and button.id.startswith("filter-"):
                if button.id == f"filter-{filter_type}":
                    button.add_class("active")
                else:
                    button.remove_class("active")
    
    def set_pr_counts(self, total: int, filtered: int):
        """Set PR counts and update displays."""
        self.total_prs = total
        self.filtered_prs = filtered
        self.update_count_displays()
    
    def set_auto_refresh(self, enabled: bool):
        """Set auto-refresh state."""
        self.auto_refresh = enabled
        self.update_refresh_status()
    
    def set_last_refresh(self, timestamp: datetime):
        """Set last refresh timestamp."""
        self.last_refresh = timestamp
        self.update_refresh_status()
    
    # Button event handlers
    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id and button_id.startswith("filter-"):
            filter_type = button_id.replace("filter-", "")
            self.set_active_filter(filter_type)
            self.post_message(self.FilterChanged(filter_type, True))
        
        elif button_id and button_id.startswith("action-"):
            action = button_id.replace("action-", "")
            self.post_message(self.ActionRequested(action))
    
    # Action handlers
    def action_filter_open(self):
        """Filter to open PRs."""
        self.set_active_filter("open")
        self.post_message(self.FilterChanged("open", True))
    
    def action_filter_drafts(self):
        """Filter to drafts."""
        self.set_active_filter("drafts")
        self.post_message(self.FilterChanged("drafts", True))
    
    def action_filter_my_prs(self):
        """Filter to my PRs."""
        self.set_active_filter("my-prs")
        self.post_message(self.FilterChanged("my-prs", True))
    
    def action_filter_reviewed(self):
        """Filter to reviewed PRs."""
        self.set_active_filter("reviewed")
        self.post_message(self.FilterChanged("reviewed", True))
    
    def action_filter_approved(self):
        """Filter to approved PRs."""
        self.set_active_filter("approved")
        self.post_message(self.FilterChanged("approved", True))
    
    def action_toggle_auto_refresh(self):
        """Toggle auto-refresh mode."""
        self.post_message(self.ActionRequested("toggle_auto_refresh"))
    
    # Watchers
    def watch_total_prs(self, new_value: int):
        """React to total PR count changes."""
        self.update_count_displays()
    
    def watch_filtered_prs(self, new_value: int):
        """React to filtered PR count changes."""
        self.update_count_displays()
    
    def watch_auto_refresh(self, new_value: bool):
        """React to auto-refresh state changes."""
        self.update_refresh_status()
    
    def watch_last_refresh(self, new_value: Optional[datetime]):
        """React to last refresh time changes."""
        self.update_refresh_status()