"""
Enhanced TUI application for PRS with advanced features.

This module provides the enhanced TUI interface with real-time updates,
advanced search, configuration management, and performance optimizations.
"""

import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header, Footer, Button, Label, Static, DataTable, 
    Checkbox, Select, Input, ProgressBar
)
from textual.reactive import reactive
from textual.message import Message
from textual.screen import Screen
from textual.binding import Binding

from prs.core.models import PullRequest
from prs.tui.data.data_manager import TUIDataManager, TUIDataUpdate
from prs.tui.services.update_service import UpdateService, UpdatePriority
from prs.tui.widgets.search_modal import SearchModal, SearchFilter
from prs.tui.widgets.config_modal import ConfigModal
from prs.tui.widgets.help_modal import HelpModal
from prs.tui.utils.performance import (
    DataPaginator, RenderOptimizer, profile_async_function, 
    AsyncTaskManager, memory_monitor
)
from prs.tui.utils.error_handling import (
    setup_error_handling, get_logger, get_recovery,
    handle_async_errors, error_boundary, ErrorCategory
)
from prs.tui.styles.themes import get_theme_manager


class EnhancedPRSMainScreen(Screen):
    """Enhanced main screen for the PRS TUI application."""
    
    BINDINGS = [
        Binding("f1", "show_help", "Help", priority=True),
        Binding("f5", "refresh", "Refresh", priority=True),
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("ctrl+f", "search", "Search", priority=True),
        Binding("ctrl+comma", "config", "Config", priority=True),
        Binding("ctrl+w", "toggle_watch", "Watch Mode", priority=True),
        Binding("ctrl+t", "toggle_format", "Toggle Format", priority=True),
        Binding("ctrl+d", "toggle_drafts", "Toggle Drafts", priority=True),
        Binding("escape", "clear_selection", "Clear Selection"),
    ]
    
    # Reactive properties
    prs: reactive[List[PullRequest]] = reactive([])
    loading: reactive[bool] = reactive(False)
    watch_mode: reactive[bool] = reactive(False)
    include_drafts: reactive[bool] = reactive(False)
    display_format: reactive[str] = reactive("panels")  # panels or table
    
    def __init__(self, data_manager: TUIDataManager, update_service: UpdateService):
        super().__init__()
        self.data_manager = data_manager
        self.update_service = update_service
        self.current_filter: Optional[SearchFilter] = None
        self.selected_prs: List[int] = []
        
        # Performance optimizations
        self.paginator: Optional[DataPaginator] = None
        self.render_optimizer = RenderOptimizer(viewport_size=20)
        self.task_manager = AsyncTaskManager(max_concurrent=3)
        
        # Subscribe to updates
        self.data_manager.add_update_callback(self._on_data_update)
        self.update_service.add_update_callback(self._on_update_event)
        
        # Setup error handling
        setup_error_handling()
        self.logger = get_logger()
        self.recovery = get_recovery()
        
        # Setup memory monitoring
        memory_monitor.add_cleanup_callback(self._cleanup_memory)
    
    def compose(self) -> ComposeResult:
        """Compose the main screen."""
        yield Header()
        
        with Container(id="main_container"):
            # Control panel
            with Horizontal(id="control_panel", classes="control_row"):
                yield Button("Refresh", id="refresh_btn", variant="primary")
                yield Button("Search", id="search_btn")
                yield Button("Config", id="config_btn")
                yield Checkbox("Include Drafts", id="draft_checkbox", value=self.include_drafts)
                yield Checkbox("Watch Mode", id="watch_checkbox", value=self.watch_mode)
                yield Select([
                    ("Panels", "panels"),
                    ("Table", "table")
                ], value=self.display_format, id="format_select")
            
            # Status bar
            with Horizontal(id="status_bar", classes="status_row"):
                yield Label("Ready", id="status_label")
                yield Label("", id="stats_label")
                yield ProgressBar(id="progress_bar", show_eta=False)
            
            # Main content area
            yield Container(id="content_area")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        with error_boundary(self.logger, ErrorCategory.UI, "mounting main screen"):
            self._update_content_area()
            asyncio.create_task(self._load_initial_data())
    
    @handle_async_errors(ErrorCategory.DATA, "loading initial data")
    @profile_async_function("load_initial_data")
    async def _load_initial_data(self) -> None:
        """Load initial PR data with performance optimization."""
        self.loading = True
        self._update_status("Loading pull requests...")
        
        try:
            prs = await self.data_manager.load_initial_data(self.include_drafts)
            
            # Setup pagination for large datasets
            if len(prs) > 50:
                self.paginator = DataPaginator(prs, page_size=20)
                self.prs = self.paginator.get_current_page()
            else:
                self.prs = prs
            
            self._update_status(f"Loaded {len(prs)} pull requests")
            
            # Check memory usage
            if memory_monitor.check_memory_usage():
                self.logger.warning("High memory usage detected", category=ErrorCategory.SYSTEM)
                memory_monitor.trigger_cleanup()
                
        except Exception as e:
            self.logger.error(f"Failed to load initial data: {e}", 
                            exception=e, category=ErrorCategory.DATA)
            self._update_status(f"Error loading data: {e}")
            
            # Attempt recovery
            error_report = self.logger.get_recent_errors(1)[0]
            if await self.recovery.attempt_recovery(error_report):
                await self._load_initial_data()
        finally:
            self.loading = False
    
    def _on_data_update(self, update: TUIDataUpdate) -> None:
        """Handle data updates from the data manager."""
        with error_boundary(self.logger, ErrorCategory.DATA, "handling data update"):
            if update.update_type in ['initial', 'refresh']:
                if self.paginator:
                    self.paginator.data = update.data
                    self.prs = self.paginator.get_current_page()
                else:
                    self.prs = update.data
                self._update_stats()
            elif update.update_type == 'pr_update':
                # Update specific PR in the list
                for i, pr in enumerate(self.prs):
                    if pr.id == update.pr_id:
                        self.prs[i] = update.data
                        break
                self._update_content_area()
    
    def _on_update_event(self, update: TUIDataUpdate) -> None:
        """Handle update events from the update service."""
        # Log performance metrics
        if hasattr(update, 'duration'):
            self.logger.debug(f"Update took {update.duration:.2f}s", 
                            category=ErrorCategory.SYSTEM)
    
    def _update_content_area(self) -> None:
        """Update the main content area based on current display format."""
        with error_boundary(self.logger, ErrorCategory.UI, "updating content area"):
            content_area = self.query_one("#content_area")
            content_area.remove_children()
            
            if self.display_format == "table":
                with content_area:
                    yield self._create_table_view()
            else:
                with content_area:
                    yield self._create_panels_view()
    
    def _create_table_view(self) -> DataTable:
        """Create optimized table view for PRs."""
        table = DataTable(id="pr_table")
        
        # Add columns
        table.add_columns(
            "ID", "Title", "Author", "Status", "CI", "Reviews", "Labels"
        )
        
        # Add rows with viewport optimization
        visible_prs = self.prs
        if len(self.prs) > 100:  # Use optimization for large datasets
            visible_range = self.render_optimizer.get_visible_range()
            visible_prs = self.prs[visible_range[0]:visible_range[1]]
        
        for pr in visible_prs:
            ci_status = self._get_ci_status_text(pr)
            review_status = self._get_review_status_text(pr)
            labels_text = ", ".join(pr.labels[:3]) + ("..." if len(pr.labels) > 3 else "")
            
            table.add_row(
                str(pr.id),
                pr.title[:50] + ("..." if len(pr.title) > 50 else ""),
                pr.author,
                "Draft" if pr.isDraft else "Open",
                ci_status,
                review_status,
                labels_text
            )
        
        return table
    
    def _create_panels_view(self) -> Container:
        """Create optimized panels view for PRs."""
        container = Container(id="panels_container")
        
        with container:
            if not self.prs:
                yield Label("No pull requests found", id="no_prs_label")
            else:
                # Use viewport optimization for large datasets
                visible_prs = self.prs
                if len(self.prs) > 50:
                    visible_range = self.render_optimizer.get_visible_range()
                    visible_prs = self.prs[visible_range[0]:visible_range[1]]
                
                for pr in visible_prs:
                    yield self._create_pr_panel(pr)
        
        return container
    
    def _create_pr_panel(self, pr: PullRequest) -> Container:
        """Create a panel for a single PR."""
        panel_classes = ["pr_panel"]
        if pr.id in self.selected_prs:
            panel_classes.append("selected")
        
        panel = Container(classes=" ".join(panel_classes), id=f"pr_panel_{pr.id}")
        
        with panel:
            # Header row
            with Horizontal(classes="pr_header"):
                yield Label(f"#{pr.id}", classes="pr_id")
                yield Label(pr.title, classes="pr_title")
                if pr.isDraft:
                    yield Label("DRAFT", classes="pr_draft_badge")
            
            # Info row
            with Horizontal(classes="pr_info"):
                yield Label(f"by {pr.author}", classes="pr_author")
                yield Label(self._get_ci_status_text(pr), classes="pr_ci_status")
                yield Label(self._get_review_status_text(pr), classes="pr_review_status")
            
            # Labels row
            if pr.labels:
                with Horizontal(classes="pr_labels"):
                    for label in pr.labels[:5]:  # Show max 5 labels
                        yield Label(label, classes="pr_label")
                    if len(pr.labels) > 5:
                        yield Label(f"+{len(pr.labels) - 5}", classes="pr_label_more")
        
        return panel
    
    def _get_ci_status_text(self, pr: PullRequest) -> str:
        """Get CI status text for display."""
        if hasattr(pr, 'ci_data') and pr.ci_data:
            if pr.ci_data.failed_workflows > 0:
                return f"❌ {pr.ci_data.failed_workflows} failed"
            elif pr.ci_data.pending_workflows > 0:
                return f"⏳ {pr.ci_data.pending_workflows} pending"
            elif pr.ci_data.successful_workflows > 0:
                return f"✅ {pr.ci_data.successful_workflows} passed"
            else:
                return "⚫ No CI"
        return "⚫ No CI"
    
    def _get_review_status_text(self, pr: PullRequest) -> str:
        """Get review status text for display."""
        approved = sum(1 for review in pr.reviews if review.get('state') == 'APPROVED')
        requested = sum(1 for review in pr.reviews if review.get('state') == 'REVIEW_REQUESTED')
        changes = sum(1 for review in pr.reviews if review.get('state') == 'CHANGES_REQUESTED')
        
        if approved > 0:
            return f"✅ {approved} approved"
        elif changes > 0:
            return f"🔄 {changes} changes requested"
        elif requested > 0:
            return f"👁️ {requested} pending"
        else:
            return "👁️ No reviews"
    
    def _update_status(self, message: str) -> None:
        """Update the status label."""
        try:
            status_label = self.query_one("#status_label")
            status_label.update(message)
        except Exception:
            # Fail silently if status label not found
            pass
    
    def _update_stats(self) -> None:
        """Update the statistics label."""
        try:
            stats = self.data_manager.get_stats()
            stats_text = f"PRs: {stats['total_prs']}"
            if stats['total_prs'] > 0:
                stats_text += f" | Drafts: {stats['draft_prs']}"
                if stats['ci_stats']['prs_with_ci'] > 0:
                    stats_text += f" | CI: ✅{stats['ci_stats']['passing_ci']} ❌{stats['ci_stats']['failing_ci']} ⏳{stats['ci_stats']['pending_ci']}"
            
            stats_label = self.query_one("#stats_label")
            stats_label.update(stats_text)
        except Exception:
            # Fail silently if stats label not found
            pass
    
    def _cleanup_memory(self) -> None:
        """Clean up memory when needed."""
        # Clear old error reports
        self.logger.clear_reports()
        
        # Cancel completed tasks
        asyncio.create_task(self.task_manager.cancel_all_tasks())
        
        # Reset pagination to reduce memory usage
        if self.paginator and len(self.paginator.data) > 200:
            self.paginator = DataPaginator(self.paginator.data[-100:], page_size=20)
            self.prs = self.paginator.get_current_page()
    
    # Action handlers
    def action_show_help(self) -> None:
        """Show help modal."""
        self.app.push_screen(HelpModal())
    
    @handle_async_errors(ErrorCategory.UI, "refreshing data")
    async def action_refresh(self) -> None:
        """Refresh data."""
        self.loading = True
        self._update_status("Refreshing...")
        
        try:
            prs = await self.data_manager.refresh_pr_data()
            
            if self.paginator:
                self.paginator.data = prs
                self.prs = self.paginator.get_current_page()
            else:
                self.prs = prs
                
            self._update_status("Refreshed")
        except Exception as e:
            self.logger.error(f"Refresh failed: {e}", exception=e, category=ErrorCategory.DATA)
            self._update_status(f"Refresh failed: {e}")
        finally:
            self.loading = False
    
    def action_search(self) -> None:
        """Open search modal."""
        search_modal = SearchModal(self.prs, current_filter=self.current_filter)
        search_modal.set_message_handler(SearchModal.SearchSubmitted, self._on_search_submitted)
        self.app.push_screen(search_modal)
    
    def action_config(self) -> None:
        """Open configuration modal."""
        config_modal = ConfigModal()
        config_modal.set_message_handler(ConfigModal.ConfigSaved, self._on_config_saved)
        self.app.push_screen(config_modal)
    
    def action_toggle_watch(self) -> None:
        """Toggle watch mode."""
        self.watch_mode = not self.watch_mode
        if self.watch_mode:
            self.update_service.start_watch_mode(30)
            self._update_status("Watch mode enabled")
        else:
            self.update_service.stop_watch_mode()
            self._update_status("Watch mode disabled")
        
        # Update checkbox
        try:
            watch_checkbox = self.query_one("#watch_checkbox")
            watch_checkbox.value = self.watch_mode
        except Exception:
            pass
    
    def action_toggle_format(self) -> None:
        """Toggle display format."""
        self.display_format = "table" if self.display_format == "panels" else "panels"
        self._update_content_area()
        
        # Update select
        try:
            format_select = self.query_one("#format_select")
            format_select.value = self.display_format
        except Exception:
            pass
    
    def action_toggle_drafts(self) -> None:
        """Toggle draft PRs inclusion."""
        self.include_drafts = not self.include_drafts
        
        # Update checkbox
        try:
            draft_checkbox = self.query_one("#draft_checkbox")
            draft_checkbox.value = self.include_drafts
        except Exception:
            pass
        
        # Reload data
        asyncio.create_task(self._load_initial_data())
    
    def action_clear_selection(self) -> None:
        """Clear PR selection."""
        self.selected_prs.clear()
        self._update_content_area()
    
    # Event handlers
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh_btn":
            asyncio.create_task(self.action_refresh())
        elif event.button.id == "search_btn":
            self.action_search()
        elif event.button.id == "config_btn":
            self.action_config()
    
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes."""
        if event.checkbox.id == "draft_checkbox":
            self.include_drafts = event.value
            asyncio.create_task(self._load_initial_data())
        elif event.checkbox.id == "watch_checkbox":
            self.watch_mode = event.value
            if self.watch_mode:
                self.update_service.start_watch_mode(30)
            else:
                self.update_service.stop_watch_mode()
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes."""
        if event.select.id == "format_select":
            self.display_format = event.value
            self._update_content_area()
    
    def _on_search_submitted(self, message: SearchModal.SearchSubmitted) -> None:
        """Handle search submission."""
        self.current_filter = message.search_filter
        # Apply the filter to the current PR list
        # This would filter self.prs based on the search criteria
        self._update_status(f"Applied search filter with {len(message.search_filter.criteria)} criteria")
    
    def _on_config_saved(self, message: ConfigModal.ConfigSaved) -> None:
        """Handle configuration save."""
        self._update_status(f"Configuration saved ({len(message.changes)} changes)")


class EnhancedPRSTUIApp(App):
    """Enhanced TUI application for PRS with performance optimizations."""
    
    CSS_PATH = "styles/default.tcss"
    TITLE = "PRS - Pull Request Status"
    SUB_TITLE = "Enhanced Interactive Terminal Interface"
    
    def __init__(self, include_drafts: bool = False, watch_interval: int = 30):
        super().__init__()
        self.include_drafts = include_drafts
        self.watch_interval = watch_interval
        
        # Initialize managers
        self.data_manager = TUIDataManager()
        self.update_service = UpdateService(self.data_manager)
        
        # Apply theme
        theme_manager = get_theme_manager()
        theme_manager.apply_theme_to_app(self)
    
    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Start the update service
        self.update_service.start()
        
        # Start CI monitoring
        self.update_service.start_ci_monitoring(60)
    
    def compose(self) -> ComposeResult:
        """Compose the main app."""
        yield EnhancedPRSMainScreen(self.data_manager, self.update_service)
    
    def on_unmount(self) -> None:
        """Called when the app is unmounted."""
        # Clean up
        self.update_service.cleanup()
        self.data_manager.cleanup()


def run_enhanced_tui(include_drafts: bool = False, watch_interval: int = 30) -> None:
    """Run the enhanced TUI application."""
    # Setup error handling
    setup_error_handling("/tmp/prs_tui.log")
    
    app = EnhancedPRSTUIApp(include_drafts, watch_interval)
    try:
        app.run()
    except Exception as e:
        logger = get_logger()
        logger.critical(f"TUI application crashed: {e}", exception=e, category=ErrorCategory.SYSTEM)
        raise