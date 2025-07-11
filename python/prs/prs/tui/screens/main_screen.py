"""
Main screen for the PRS TUI application.

Provides the primary interface showing PR list with optional detail panel,
filtering, and navigation controls.
"""

from typing import Optional
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, DataTable
from textual.reactive import reactive
from textual.binding import Binding
from textual.message import Message

from ..widgets.header import HeaderWidget
from ..widgets.filter_bar import FilterBarWidget
from ..widgets.status_bar import StatusBarWidget  
from ..widgets.footer import FooterWidget
from ..widgets.pr_list import PRListWidget
from ..widgets.pr_detail import PRDetailWidget
from ..models.tui_models import TUIState, PRListItem
from ...core.models import PullRequest


class MainScreen(Screen):
    """
    Main application screen with PR list and optional detail panel.
    
    Layout:
    ┌─────────────────────────────────────────────────┐
    │ Header (repo info, shortcuts)                   │
    ├─────────────────────────────────────────────────┤
    │ Filter Bar (search, quick filters)             │
    ├─────────────────────────────────────────────────┤
    │ Status Bar (loading, counts, messages)         │
    ├─────────────────────────────────────────────────┤
    │ ┌─────────────────┬─────────────────────────────┐ │
    │ │ PR List         │ PR Detail Panel (optional) │ │
    │ │                 │                             │ │
    │ │                 │                             │ │
    │ │                 │                             │ │
    │ └─────────────────┴─────────────────────────────┘ │
    ├─────────────────────────────────────────────────┤
    │ Footer (help, actions)                          │
    └─────────────────────────────────────────────────┘
    """
    
    CSS = """
    MainScreen {
        layout: grid;
        grid-size: 1 6;
        grid-rows: auto auto auto 1fr auto;
    }
    
    #header {
        dock: top;
        height: 3;
    }
    
    #filter-bar {
        dock: top;  
        height: 3;
    }
    
    #status-bar {
        dock: top;
        height: 1;
    }
    
    #main-content {
        layout: horizontal;
    }
    
    #pr-list-container {
        width: 60%;
        border: solid $primary;
    }
    
    #detail-panel-container {
        width: 40%;
        border: solid $secondary;
        display: none;
    }
    
    #detail-panel-container.visible {
        display: block;
    }
    
    #footer {
        dock: bottom;
        height: 2;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+c,q", "quit", "Quit", show=False),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("f", "focus_filter", "Filter", show=True),
        Binding("d", "toggle_drafts", "Drafts", show=True),
        Binding("tab", "toggle_detail", "Detail", show=True),
        Binding("enter", "open_detail", "Open", show=True),
        Binding("o", "open_in_browser", "Browser", show=True),
        Binding("s", "sort_menu", "Sort", show=True),
        Binding("?", "help", "Help", show=True),
        Binding("escape", "clear_focus", "Clear", show=False),
    ]
    
    # Reactive attributes
    show_detail_panel = reactive(False)
    loading = reactive(False)
    selected_pr: Optional[PullRequest] = reactive(None)
    
    class PRSelected(Message):
        """Message sent when a PR is selected."""
        def __init__(self, pr: Optional[PullRequest], index: int = -1) -> None:
            self.pr = pr
            self.index = index
            super().__init__()
    
    class RefreshRequested(Message):
        """Message sent when refresh is requested."""
        pass
    
    def __init__(self, tui_state: TUIState, **kwargs):
        super().__init__(**kwargs)
        self.tui_state = tui_state
        self.pr_list_widget: Optional[PRListWidget] = None
        self.detail_widget: Optional[PRDetailWidget] = None
        
    def compose(self):
        """Compose the main screen layout."""
        yield HeaderWidget(id="header")
        yield FilterBarWidget(id="filter-bar")
        yield StatusBarWidget(id="status-bar")
        
        with Container(id="main-content"):
            with Container(id="pr-list-container"):
                # PR list will be added via DataTable
                yield DataTable(id="pr-table", cursor_type="row")
            
            with Container(id="detail-panel-container"):
                yield Static("Select a PR to view details", id="detail-placeholder")
        
        yield FooterWidget(id="footer")
    
    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        self.setup_pr_table()
        self.setup_event_handlers()
        self.refresh_pr_data()
    
    def setup_pr_table(self) -> None:
        """Setup the PR data table."""
        table = self.query_one("#pr-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        
        # Add columns
        table.add_columns(
            "Status",
            "ID", 
            "Title",
            "Author",
            "Checks",
            "Reviews",
            "Labels"
        )
    
    def setup_event_handlers(self) -> None:
        """Setup event handlers for child widgets."""
        # Filter bar events
        filter_bar = self.query_one("#filter-bar", FilterBarWidget)
        filter_bar.watch(filter_bar.FilterChanged, self.on_filter_changed)
        filter_bar.watch(filter_bar.QuickFilterSelected, self.on_quick_filter)
        
        # Table selection events
        table = self.query_one("#pr-table", DataTable)
        table.watch(table.CursorChanged, self.on_table_cursor_changed)
    
    def refresh_pr_data(self) -> None:
        """Refresh PR data in the table."""
        table = self.query_one("#pr-table", DataTable)
        table.clear()
        
        filtered_items = self.tui_state.get_filtered_sorted_items()
        
        for item in filtered_items:
            pr = item.pr
            health = item.health
            
            # Status indicator
            status_icon = health.health_dots
            
            # Format labels
            labels_str = ", ".join(pr.labels[:3])
            if len(pr.labels) > 3:
                labels_str += f" (+{len(pr.labels) - 3})"
            
            # Check status
            checks_str = ""
            if health.checks_failing > 0:
                checks_str = f"❌{health.checks_failing}"
            elif health.checks_pending > 0:
                checks_str = f"⏳{health.checks_pending}"
            elif health.checks_passing > 0:
                checks_str = f"✅{health.checks_passing}"
            
            # Review status
            reviews_str = ""
            if health.reviews_approved > 0:
                reviews_str = f"✅{health.reviews_approved}"
            if health.reviews_changes > 0:
                reviews_str += f" ❌{health.reviews_changes}"
            if health.reviews_requested > 0:
                reviews_str += f" ⏳{health.reviews_requested}"
            
            table.add_row(
                status_icon,
                f"#{pr.id}",
                pr.title[:50] + ("..." if len(pr.title) > 50 else ""),
                pr.author,
                checks_str,
                reviews_str,
                labels_str
            )
        
        # Update status bar
        status_bar = self.query_one("#status-bar", StatusBarWidget)
        status_bar.update_statistics(
            total=len(self.tui_state.pr_items),
            filtered=len(filtered_items)
        )
    
    def on_filter_changed(self, message: FilterBarWidget.FilterChanged) -> None:
        """Handle filter changes."""
        # Update filter state
        self.tui_state.filter_state.search_query = message.filter_text
        
        # Update status bar
        status_bar = self.query_one("#status-bar", StatusBarWidget)
        status_bar.update_filter_status(message.filter_text)
        
        # Refresh table
        self.refresh_pr_data()
    
    def on_quick_filter(self, message: FilterBarWidget.QuickFilterSelected) -> None:
        """Handle quick filter selection."""
        filter_state = self.tui_state.filter_state
        
        if message.filter_type == "author" and message.value == "me":
            # TODO: Get current user from config
            filter_state.author_filter = "current_user"
        elif message.filter_type == "status":
            from ..models.tui_models import PRStatus
            if message.value == "needs_review":
                filter_state.status_filters = [PRStatus.PENDING]
            elif message.value == "approved":
                filter_state.status_filters = [PRStatus.HEALTHY]
        elif message.filter_type == "ci" and message.value == "failed":
            filter_state.status_filters = [PRStatus.CRITICAL]
        
        self.refresh_pr_data()
    
    def on_table_cursor_changed(self, message: DataTable.CursorChanged) -> None:
        """Handle table cursor changes."""
        if message.cursor_row is not None:
            filtered_items = self.tui_state.get_filtered_sorted_items()
            if 0 <= message.cursor_row < len(filtered_items):
                selected_item = filtered_items[message.cursor_row]
                self.selected_pr = selected_item.pr
                self.post_message(self.PRSelected(selected_item.pr, message.cursor_row))
                
                if self.show_detail_panel:
                    self.update_detail_panel(selected_item.pr)
    
    def update_detail_panel(self, pr: PullRequest) -> None:
        """Update the detail panel with PR information."""
        if not self.show_detail_panel:
            return
            
        container = self.query_one("#detail-panel-container")
        
        # Remove existing detail widget
        try:
            container.query_one("#detail-placeholder").remove()
        except:
            pass
        
        # Create new detail widget
        detail_widget = PRDetailWidget(pr=pr, id="pr-detail")
        container.mount(detail_widget)
    
    def watch_show_detail_panel(self, show: bool) -> None:
        """React to detail panel visibility changes."""
        container = self.query_one("#detail-panel-container")
        if show:
            container.add_class("visible")
            # Update with current selection
            if self.selected_pr:
                self.update_detail_panel(self.selected_pr)
        else:
            container.remove_class("visible")
    
    def watch_loading(self, loading: bool) -> None:
        """React to loading state changes."""
        status_bar = self.query_one("#status-bar", StatusBarWidget)
        status_bar.update_loading(loading)
    
    # Action handlers
    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
    
    def action_refresh(self) -> None:
        """Request data refresh."""
        self.post_message(self.RefreshRequested())
    
    def action_focus_filter(self) -> None:
        """Focus the filter input."""
        filter_bar = self.query_one("#filter-bar", FilterBarWidget)
        filter_bar.focus_filter()
    
    def action_toggle_drafts(self) -> None:
        """Toggle draft PR visibility."""
        filter_state = self.tui_state.filter_state
        filter_state.show_drafts = not filter_state.show_drafts
        self.refresh_pr_data()
    
    def action_toggle_detail(self) -> None:
        """Toggle detail panel visibility."""
        self.show_detail_panel = not self.show_detail_panel
    
    def action_open_detail(self) -> None:
        """Open detailed view of selected PR."""
        if self.selected_pr:
            # TODO: Push detail screen
            pass
    
    def action_open_in_browser(self) -> None:
        """Open selected PR in browser."""
        if self.selected_pr:
            import webbrowser
            try:
                webbrowser.open(self.selected_pr.url)
            except Exception as e:
                status_bar = self.query_one("#status-bar", StatusBarWidget)
                status_bar.show_error(f"Failed to open browser: {str(e)}")
    
    def action_sort_menu(self) -> None:
        """Show sort options menu."""
        # TODO: Implement sort menu
        pass
    
    def action_help(self) -> None:
        """Show help screen."""
        # TODO: Push help screen
        pass
    
    def action_clear_focus(self) -> None:
        """Clear current focus/selection."""
        table = self.query_one("#pr-table", DataTable)
        table.cursor_row = None
        self.selected_pr = None


class CompactMainScreen(MainScreen):
    """
    Compact version of the main screen for smaller terminals.
    
    Simplified layout with:
    - Compact header
    - Combined filter/status bar
    - PR list only (no detail panel)
    - Minimal footer
    """
    
    CSS = """
    CompactMainScreen {
        layout: grid;
        grid-size: 1 4;
        grid-rows: auto auto 1fr auto;
    }
    
    #header {
        height: 2;
    }
    
    #filter-status-bar {
        height: 2;
    }
    
    #pr-list-container {
        width: 100%;
    }
    
    #detail-panel-container {
        display: none;
    }
    
    #footer {
        height: 1;
    }
    """
    
    def compose(self):
        """Compose compact screen layout."""
        from ..widgets.header import CompactHeaderWidget
        from ..widgets.status_bar import CompactStatusBarWidget
        
        yield CompactHeaderWidget(id="header")
        
        # Combined filter and status bar
        with Container(id="filter-status-bar"):
            yield FilterBarWidget(id="filter-bar")
            yield CompactStatusBarWidget(id="status-bar")
        
        with Container(id="main-content"):
            with Container(id="pr-list-container"):
                yield DataTable(id="pr-table", cursor_type="row")
        
        yield FooterWidget(id="footer")
    
    def on_mount(self) -> None:
        """Initialize compact screen."""
        super().on_mount()
        # Force detail panel off in compact mode
        self.show_detail_panel = False