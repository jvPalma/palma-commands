"""
Main TUI application for PRS.

This module contains the main PRSApp class that coordinates the entire
terminal user interface experience.
"""

from typing import Any, Dict, List, Optional
import asyncio
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.worker import Worker, get_current_worker

from prs.config import get, all_config
from prs.core.models import PullRequest
from prs.core.usecases import list_pull_requests
from prs.tui.widgets.header import HeaderWidget
from prs.tui.widgets.footer import FooterWidget
from prs.tui.widgets.filter_bar import FilterBarWidget
from prs.tui.widgets.status_bar import StatusBarWidget
from prs.tui.widgets.pr_list import PRListWidget
from prs.tui.widgets.navigation_sidebar import NavigationSidebar
from prs.tui.widgets.pr_details import PRDetailsWidget


class PRSApp(App):
    """
    Main PRS TUI Application.
    
    Provides an interactive terminal interface for browsing pull requests
    with real-time updates, filtering, and advanced navigation features.
    """
    
    CSS_PATH = "styles/app.tcss"
    TITLE = "PRS - Pull Request Status"
    SUB_TITLE = "Interactive Terminal Interface"
    
    # Reactive attributes for state management
    loading = reactive(False)
    error_message = reactive("")
    filter_text = reactive("")
    show_drafts = reactive(False)
    auto_refresh = reactive(True)
    refresh_interval = reactive(30)  # seconds
    
    # Data state
    pull_requests: List[PullRequest] = reactive([])
    filtered_prs: List[PullRequest] = reactive([])
    selected_pr: Optional[PullRequest] = reactive(None)
    
    # UI state
    details_panel_expanded = reactive(False)
    active_panel = reactive("pr_list")  # "sidebar", "pr_list", "details"
    
    # Configuration
    config: Dict[str, Any] = reactive({})
    
    BINDINGS = [
        Binding("ctrl+c,q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("f", "toggle_filter", "Filter", show=True),
        Binding("d", "toggle_drafts", "Toggle Drafts", show=True),
        Binding("a", "toggle_auto_refresh", "Auto Refresh", show=True),
        Binding("h,?", "help", "Help", show=True),
        Binding("c", "config", "Config", show=True),
        Binding("s", "settings", "Settings", show=True),
        Binding("escape", "clear_selection", "Clear", show=False),
        Binding("ctrl+r", "force_refresh", "Force Refresh", show=False),
        Binding("space", "toggle_details", "Toggle Details", show=False),
        Binding("enter", "open_pr", "Open PR", show=False),
        Binding("tab", "switch_panel", "Switch Panel", show=False),
        Binding("shift+tab", "switch_panel_reverse", "Switch Panel (Reverse)", show=False),
        Binding("up,k", "cursor_up", "Up", show=False),
        Binding("down,j", "cursor_down", "Down", show=False),
        Binding("home", "first_item", "First", show=False),
        Binding("end", "last_item", "Last", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        # Number keys for quick filters
        Binding("1", "filter_all", "All PRs", show=False),
        Binding("2", "filter_open", "Open PRs", show=False),
        Binding("3", "filter_drafts", "Drafts", show=False),
        Binding("4", "filter_my_prs", "My PRs", show=False),
        Binding("5", "filter_approved", "Approved", show=False),
        Binding("6", "filter_failed", "Failed Checks", show=False),
        # Navigation shortcuts
        Binding("g,g", "goto_first", "Go to First", show=False),
        Binding("shift+g", "goto_last", "Go to Last", show=False),
        Binding("o", "open_pr", "Open PR", show=False),
        Binding("ctrl+u", "half_page_up", "Half Page Up", show=False),
        Binding("ctrl+d", "half_page_down", "Half Page Down", show=False),
        # Focus management
        Binding("ctrl+1", "focus_sidebar", "Focus Sidebar", show=False),
        Binding("ctrl+2", "focus_pr_list", "Focus PR List", show=False),
        Binding("ctrl+3", "focus_details", "Focus Details", show=False),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.refresh_worker: Optional[Worker] = None
        self.last_refresh = datetime.now()
        
        # State guards to prevent infinite refresh loops
        self._updating_filters = False
        self._refreshing_prs = False
        
    def compose(self) -> ComposeResult:
        """Compose the main application layout with 3-panel design."""
        with Container(id="app-container"):
            yield HeaderWidget(id="header")
            yield FilterBarWidget(id="filter-bar")
            
            with Horizontal(id="main-content"):
                # Left panel - Navigation sidebar
                yield NavigationSidebar(id="sidebar")
                
                # Center panel - PR list and details
                with Vertical(id="center-panel"):
                    yield StatusBarWidget(id="status-bar")
                    yield PRListWidget(id="pr-list")
                    
                    # Bottom panel - PR details (initially hidden)
                    with Container(id="details-panel"):
                        yield PRDetailsWidget(id="pr-details")
                
            yield FooterWidget(id="footer")
    
    def on_mount(self) -> None:
        """Initialize the application when mounted."""
        self.load_configuration()
        self.setup_widgets()
        self.start_auto_refresh()
        self.call_after_refresh(self.initial_load)
    
    def load_configuration(self) -> None:
        """Load PRS configuration into reactive state."""
        try:
            # Use safe dict for config instead of all_config() which might have issues
            self.config = {}
            
            # Extract common settings with safe fallbacks
            try:
                self.show_drafts = get("pr-info", "include_drafts", fallback="false").lower() == "true"
            except:
                self.show_drafts = False
            
            # Set window title with repo info
            try:
                repo_name = get("git", "repo_name", fallback="Unknown Repo")
                username = get("git", "username", fallback="Unknown User")
                self.title = f"PRS - {repo_name} ({username})"
            except:
                self.title = "PRS - Pull Request Status"
            
        except Exception as e:
            self.error_message = f"Configuration error: {type(e).__name__}: {str(e)[:50]}"
    
    def setup_widgets(self) -> None:
        """Setup widget connections and callbacks."""
        try:
            # Setup navigation sidebar
            try:
                sidebar = self.query_one("#sidebar", NavigationSidebar)
                sidebar.update_repository_info(
                    get("git", "repo_name", fallback="Unknown Repo"),
                    get("git", "username", fallback="Unknown User")
                )
                sidebar.set_auto_refresh(self.auto_refresh)
            except Exception:
                pass
            
            # Setup details panel (initially hidden)
            try:
                details_panel = self.query_one("#details-panel")
                details_panel.display = False
            except Exception:
                pass
            
        except Exception as e:
            self.error_message = f"Failed to setup widgets: {str(e)}"
    
    def initial_load(self) -> None:
        """Perform initial data load."""
        # Debug log
        with open('/tmp/pr_debug.log', 'a') as f:
            f.write("initial_load called\n")
        
        # Add immediate test data to see if widget works
        self.update_status_bar("Loading test data...")
        
        # Test with direct PR data
        from prs.core.models import PullRequest
        test_pr = PullRequest(
            id=999,
            title="Test PR for TUI",
            author="test-user",
            labels=["test"],
            checks=[],
            reviews=[],
            comments=[],
            url="https://github.com/test/test/pull/999",
            branch="test-branch",
            is_draft=False,
            created_at="2025-01-16T10:00:00Z"
        )
        
        with open('/tmp/pr_debug.log', 'a') as f:
            f.write(f"Created test PR: {test_pr.title} (ID: {test_pr.id})\n")
        
        self.pull_requests = [test_pr]
        with open('/tmp/pr_debug.log', 'a') as f:
            f.write(f"Set pull_requests to {len(self.pull_requests)} items\n")
        
        self.update_status_bar("Test PR loaded!")
        self.apply_filters()
        
        # Set initial focus to PR list
        self.active_panel = "pr_list"
        self.call_after_refresh(self.focus_active_panel)
        
        # Also do normal refresh
        self.action_refresh()
    
    def start_auto_refresh(self) -> None:
        """Start the auto-refresh worker if enabled."""
        if self.auto_refresh and not self.refresh_worker:
            self.refresh_worker = self.run_worker(
                self.auto_refresh_worker, 
                name="auto_refresh",
                group="background"
            )
    
    def stop_auto_refresh(self) -> None:
        """Stop the auto-refresh worker."""
        if self.refresh_worker:
            self.refresh_worker.cancel()
            self.refresh_worker = None
    
    async def auto_refresh_worker(self) -> None:
        """Background worker for auto-refreshing data."""
        while True:
            await asyncio.sleep(self.refresh_interval)
            if self.auto_refresh:
                self.refresh_pull_requests()
    
    def refresh_pull_requests(self) -> None:
        """Refresh pull request data from the API."""
        if self.loading or self._refreshing_prs:
            return
            
        self._refreshing_prs = True
        try:
            # Simplified synchronous approach for now
            self.loading = True
            self.update_status_bar("Loading PRs...")
            
            try:
                options = {
                    "include_draft": self.show_drafts,
                    "enable_cache": True,
                    "format": "data"
                }
                
                result = self._fetch_pr_data(options)
                
                if "error" in result:
                    self.error_message = result["error"]
                    self.update_status_bar(f"Error: {result['error']}")
                else:
                    prs = result.get("prs", [])
                    self.pull_requests = prs
                    self.last_refresh = datetime.now()
                    self.error_message = ""
                    self.update_status_bar(f"Loaded {len(prs)} PRs - Total: {len(self.pull_requests)}")
                    self.update_header_refresh_time()
                
            except Exception as e:
                self.error_message = str(e)
                self.update_status_bar(f"Exception: {str(e)[:50]}")
                
            self.loading = False
            self.apply_filters()
        finally:
            self._refreshing_prs = False
    
    def _fetch_pr_data(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch PR data using existing PRS logic.
        """
        try:
            # Import the core data fetching functions directly
            from prs.vc_tools.github.client import get_pull_request_details, list_pull_request_ids
            from prs.core.helpers import resolve_owner
            from prs.config import get
            
            # Set up filters like the main function does
            filters = {
                "state": "open",
                "include_draft": options.get("include_draft", False),
            }
            
            # Fetch PR refs
            pr_refs = list_pull_request_ids(filters)
            all_prs = []
            
            for pr_id, source_tag, is_draft in pr_refs:
                pr_model = get_pull_request_details(pr_id)
                pr_model.source = source_tag
                pr_model.isDraft = is_draft
                all_prs.append(pr_model)
            
            return {
                "prs": all_prs,
                "total": len(all_prs),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def apply_filters(self) -> None:
        """Apply current filters to the PR list."""
        if self._updating_filters:
            return
            
        self._updating_filters = True
        try:
            filtered = self.pull_requests
            
            # Apply text filter
            if self.filter_text.strip():
                text_lower = self.filter_text.lower()
                filtered = [
                    pr for pr in filtered
                    if (text_lower in pr.title.lower() or 
                        text_lower in pr.author.lower() or
                        text_lower in str(pr.id) or
                        any(text_lower in label.lower() for label in pr.labels))
                ]
            
            self.filtered_prs = filtered
            self.update_pr_list()
            self.update_footer_counts()
        finally:
            self._updating_filters = False
    
    def update_pr_list(self) -> None:
        """Update the PR list widget with filtered data."""
        try:
            # Debug log
            with open('/tmp/pr_debug.log', 'a') as f:
                f.write(f"update_pr_list called - filtered_prs: {len(self.filtered_prs)}\n")
                for i, pr in enumerate(self.filtered_prs):
                    f.write(f"  Filtered PR {i}: {pr.title} (ID: {pr.id})\n")
            
            pr_list = self.query_one("#pr-list", PRListWidget)
            pr_list.update_pull_requests(self.filtered_prs)
            
            # Update sidebar statistics
            try:
                sidebar = self.query_one("#sidebar", NavigationSidebar)
                sidebar.update_stats(self.pull_requests)
            except Exception:
                pass
                
        except Exception as e:
            with open('/tmp/pr_debug.log', 'a') as f:
                f.write(f"update_pr_list failed: {str(e)}\n")
            self.error_message = f"Failed to update PR list: {str(e)}"
    
    def update_status_bar(self, message: str) -> None:
        """Update the status bar with a message."""
        try:
            status_bar = self.query_one("#status-bar", StatusBarWidget)
            status_bar.set_status(message)
        except Exception:
            pass
    
    def update_header_refresh_time(self) -> None:
        """Update the header with last refresh time."""
        try:
            header = self.query_one("#header", HeaderWidget)
            header.update_refresh_time(self.last_refresh)
            
            # Also update sidebar refresh time
            sidebar = self.query_one("#sidebar", NavigationSidebar)
            sidebar.update_refresh_time(self.last_refresh)
        except Exception:
            pass
    
    def update_footer_counts(self) -> None:
        """Update footer with PR counts."""
        try:
            footer = self.query_one("#footer", FooterWidget)
            footer.update_pr_counts(len(self.pull_requests), len(self.filtered_prs))
        except Exception:
            pass
    
    # Event handlers
    def on_filter_changed(self, filters: Dict[str, Any]) -> None:
        """Handle filter changes from the filter bar."""
        self.filter_text = filters.get("search_text", "")
        
        # Handle other filter types here (authors, labels, etc.)
        if filters.get("include_drafts") != self.show_drafts:
            self.show_drafts = filters.get("include_drafts", False)
        else:
            # Just apply text filters without refreshing data
            self.apply_filters()
    
    def on_pr_selected(self, pr: PullRequest, index: int) -> None:
        """Handle PR selection."""
        self.selected_pr = pr
        self.update_status_bar(f"Selected: #{pr.id} - {pr.title}")
    
    def on_pr_activated(self, pr: PullRequest, index: int) -> None:
        """Handle PR activation (enter/double-click)."""
        self.selected_pr = pr
        # Open PR in browser by default
        import webbrowser
        try:
            webbrowser.open(pr.url)
            self.update_status_bar(f"Opened #{pr.id} in browser")
        except Exception as e:
            self.update_status_bar(f"Failed to open PR: {str(e)}")
    
    def on_filter_bar_widget_filter_changed(self, message) -> None:
        """Handle filter text changes."""
        self.filter_text = message.filter_text
        self.apply_filters()
    
    def on_filter_bar_widget_quick_filter_selected(self, message) -> None:
        """Handle quick filter selection."""
        # Convert quick filter to text filter
        filter_text = f"{message.filter_type}:{message.value}"
        self.filter_text = filter_text
        self.apply_filters()
    
    def on_pr_list_widget_pr_selected(self, message) -> None:
        """Handle PR selection from PR list."""
        self.selected_pr = message.pr
        self.update_status_bar(f"Selected: #{message.pr.id} - {message.pr.title}")
        
        # Update PR details widget
        try:
            details = self.query_one("#pr-details", PRDetailsWidget)
            details.set_pr(message.pr)
        except Exception:
            pass
    
    def on_pr_list_widget_pr_activated(self, message) -> None:
        """Handle PR activation from PR list."""
        self.selected_pr = message.pr
        # Open PR in browser by default
        import webbrowser
        try:
            webbrowser.open(message.pr.url)
            self.update_status_bar(f"Opened #{message.pr.id} in browser")
        except Exception as e:
            self.update_status_bar(f"Failed to open PR: {str(e)}")
    
    def on_navigation_sidebar_filter_changed(self, message) -> None:
        """Handle filter changes from navigation sidebar."""
        filter_type = message.filter_type
        
        # Apply filter based on type
        if filter_type == "all":
            self.filter_text = ""
        elif filter_type == "open":
            self.filter_text = "state:open"
        elif filter_type == "drafts":
            self.filter_text = "is:draft"
        elif filter_type == "my_prs":
            self.filter_text = f"author:{get('git', 'username', fallback='')}"
        elif filter_type == "approved":
            self.filter_text = "review:approved"
        elif filter_type == "failed":
            self.filter_text = "status:failure"
        
        # Apply the filter
        self.apply_filters()
        
    def on_navigation_sidebar_action_requested(self, message) -> None:
        """Handle action requests from navigation sidebar."""
        action = message.action
        
        if action == "refresh":
            self.action_refresh()
        elif action == "settings":
            self.action_settings()
        elif action == "help":
            self.action_help()
        elif action == "quit":
            self.action_quit()
    
    def on_pr_detail_widget_action_requested(self, message) -> None:
        """Handle action requests from PR detail widget."""
        action = message.action
        pr = message.pr
        
        if action == "open_browser":
            import webbrowser
            try:
                webbrowser.open(pr.url)
                self.update_status_bar(f"Opened #{pr.id} in browser")
            except Exception as e:
                self.update_status_bar(f"Failed to open PR: {str(e)}")
        elif action == "copy_url":
            # Copy URL to clipboard (if available)
            try:
                import pyperclip
                pyperclip.copy(pr.url)
                self.update_status_bar(f"Copied URL for #{pr.id}")
            except ImportError:
                self.update_status_bar("pyperclip not available for URL copying")
            except Exception as e:
                self.update_status_bar(f"Failed to copy URL: {str(e)}")
        elif action == "refresh":
            self.action_refresh()
    
    # Watchers for reactive attributes
    def watch_filter_text(self, new_value: str) -> None:
        """React to filter text changes."""
        if not self._updating_filters:
            self.apply_filters()
    
    def watch_show_drafts(self, new_value: bool) -> None:
        """React to draft toggle changes."""
        if not self._refreshing_prs:
            self.refresh_pull_requests()
    
    def watch_auto_refresh(self, new_value: bool) -> None:
        """React to auto-refresh toggle changes."""
        if new_value:
            self.start_auto_refresh()
        else:
            self.stop_auto_refresh()
        
        # Update footer to show auto-refresh status
        try:
            footer = self.query_one("#footer", FooterWidget)
            footer.set_auto_refresh(new_value)
        except Exception:
            pass
        
        # Update sidebar auto-refresh status
        try:
            sidebar = self.query_one("#sidebar", NavigationSidebar)
            sidebar.set_auto_refresh(new_value)
        except Exception:
            pass
    
    def watch_selected_pr(self, new_pr: Optional[PullRequest]) -> None:
        """React to selected PR changes."""
        try:
            # Update PR detail widget
            detail_widget = self.query_one("#pr-detail", PRDetailWidget)
            detail_widget.pr = new_pr
            
            # If a PR is selected and details panel is not expanded, expand it
            if new_pr and not self.details_panel_expanded:
                self.details_panel_expanded = True
                
        except Exception:
            pass
    
    def watch_details_panel_expanded(self, expanded: bool) -> None:
        """React to details panel expansion changes."""
        try:
            details_panel = self.query_one("#details-panel")
            details_panel.display = expanded
        except Exception:
            pass
    
    def watch_loading(self, new_value: bool) -> None:
        """React to loading state changes."""
        try:
            pr_list = self.query_one("#pr-list", PRListWidget)
            pr_list.set_loading(new_value)
            
            footer = self.query_one("#footer", FooterWidget)
            footer.set_loading(new_value)
        except Exception:
            pass
    
    def watch_error_message(self, new_value: str) -> None:
        """React to error message changes."""
        try:
            footer = self.query_one("#footer", FooterWidget)
            if new_value:
                footer.set_error(new_value)
            else:
                footer.clear_error()
        except Exception:
            pass
    
    # Action handlers
    def action_quit(self) -> None:
        """Quit the application."""
        self.stop_auto_refresh()
        self.exit()
    
    def action_refresh(self) -> None:
        """Manually refresh PR data."""
        self.refresh_pull_requests()
    
    def action_force_refresh(self) -> None:
        """Force refresh with cache invalidation."""
        # TODO: Implement cache invalidation
        self.refresh_pull_requests()
    
    def action_toggle_filter(self) -> None:
        """Toggle the filter bar focus."""
        try:
            filter_bar = self.query_one("#filter-bar", FilterBarWidget)
            filter_bar.focus_search()
        except Exception:
            pass
    
    def action_toggle_drafts(self) -> None:
        """Toggle inclusion of draft PRs."""
        self.show_drafts = not self.show_drafts
    
    def action_toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh mode."""
        self.auto_refresh = not self.auto_refresh
    
    def action_help(self) -> None:
        """Show help dialog."""
        # TODO: Implement help dialog
        self.update_status_bar("Help dialog not implemented yet")
    
    def action_config(self) -> None:
        """Show configuration dialog."""
        # TODO: Implement config dialog
        self.update_status_bar("Configuration dialog not implemented yet")
    
    def action_settings(self) -> None:
        """Show settings dialog."""
        # TODO: Implement settings dialog
        self.update_status_bar("Settings dialog not implemented yet")
    
    def action_clear_selection(self) -> None:
        """Clear current selection."""
        self.selected_pr = None
        self.update_status_bar("Selection cleared")
    
    def action_select_item(self) -> None:
        """Select the current item."""
        try:
            pr_list = self.query_one("#pr-list", PRListWidget)
            selected = pr_list.get_selected_pr()
            if selected:
                self.on_pr_activated(selected, pr_list.selected_index)
        except Exception:
            pass
    
    def action_toggle_details(self) -> None:
        """Toggle the details panel."""
        self.details_panel_expanded = not self.details_panel_expanded
        
        # Update status bar
        status = "expanded" if self.details_panel_expanded else "collapsed"
        self.update_status_bar(f"Details panel {status}")
    
    def action_switch_panel(self) -> None:
        """Switch to next panel."""
        panels = ["sidebar", "pr_list", "details"]
        current_index = panels.index(self.active_panel)
        next_index = (current_index + 1) % len(panels)
        
        # Skip details panel if not expanded
        if panels[next_index] == "details" and not self.details_panel_expanded:
            next_index = (next_index + 1) % len(panels)
        
        self.active_panel = panels[next_index]
        self.focus_active_panel()
    
    def action_switch_panel_reverse(self) -> None:
        """Switch to previous panel."""
        panels = ["sidebar", "pr_list", "details"]
        current_index = panels.index(self.active_panel)
        prev_index = (current_index - 1) % len(panels)
        
        # Skip details panel if not expanded
        if panels[prev_index] == "details" and not self.details_panel_expanded:
            prev_index = (prev_index - 1) % len(panels)
        
        self.active_panel = panels[prev_index]
        self.focus_active_panel()
    
    def focus_active_panel(self) -> None:
        """Focus the active panel."""
        try:
            if self.active_panel == "sidebar":
                sidebar = self.query_one("#sidebar", NavigationSidebar)
                sidebar.focus()
                self.update_status_bar("Focused: Navigation Sidebar")
            elif self.active_panel == "pr_list":
                pr_list = self.query_one("#pr-list", PRListWidget)
                pr_list.focus()
                self.update_status_bar("Focused: PR List")
            elif self.active_panel == "details" and self.details_panel_expanded:
                detail_widget = self.query_one("#pr-detail", PRDetailWidget)
                detail_widget.focus()
                self.update_status_bar("Focused: PR Details")
        except Exception:
            pass
    
    def action_open_pr(self) -> None:
        """Open the selected PR in browser."""
        if self.selected_pr:
            import webbrowser
            try:
                webbrowser.open(self.selected_pr.url)
                self.update_status_bar(f"Opened #{self.selected_pr.id} in browser")
            except Exception as e:
                self.update_status_bar(f"Failed to open PR: {str(e)}")
    
    # Navigation actions that can be delegated to PR list
    def action_cursor_up(self) -> None:
        """Move cursor up in PR list."""
        if self.active_panel == "pr_list":
            try:
                pr_list = self.query_one("#pr-list", PRListWidget)
                pr_list.action_cursor_up()
            except Exception:
                pass
    
    def action_cursor_down(self) -> None:
        """Move cursor down in PR list."""
        if self.active_panel == "pr_list":
            try:
                pr_list = self.query_one("#pr-list", PRListWidget)
                pr_list.action_cursor_down()
            except Exception:
                pass
    
    def action_first_item(self) -> None:
        """Go to first item in PR list."""
        if self.active_panel == "pr_list":
            try:
                pr_list = self.query_one("#pr-list", PRListWidget)
                pr_list.action_first_item()
            except Exception:
                pass
    
    def action_last_item(self) -> None:
        """Go to last item in PR list."""
        if self.active_panel == "pr_list":
            try:
                pr_list = self.query_one("#pr-list", PRListWidget)
                pr_list.action_last_item()
            except Exception:
                pass
    
    def action_page_up(self) -> None:
        """Page up in PR list."""
        if self.active_panel == "pr_list":
            try:
                pr_list = self.query_one("#pr-list", PRListWidget)
                pr_list.action_page_up()
            except Exception:
                pass
    
    def action_page_down(self) -> None:
        """Page down in PR list."""
        if self.active_panel == "pr_list":
            try:
                pr_list = self.query_one("#pr-list", PRListWidget)
                pr_list.action_page_down()
            except Exception:
                pass
    
    # Filter actions
    def action_filter_all(self) -> None:
        """Filter to show all PRs."""
        try:
            sidebar = self.query_one("#sidebar", NavigationSidebar)
            sidebar.action_filter_all()
        except Exception:
            pass
    
    def action_filter_open(self) -> None:
        """Filter to show open PRs."""
        try:
            sidebar = self.query_one("#sidebar", NavigationSidebar)
            sidebar.action_filter_open()
        except Exception:
            pass
    
    def action_filter_drafts(self) -> None:
        """Filter to show draft PRs."""
        try:
            sidebar = self.query_one("#sidebar", NavigationSidebar)
            sidebar.action_filter_drafts()
        except Exception:
            pass
    
    def action_filter_my_prs(self) -> None:
        """Filter to show my PRs."""
        try:
            sidebar = self.query_one("#sidebar", NavigationSidebar)
            sidebar.action_filter_my_prs()
        except Exception:
            pass
    
    def action_filter_approved(self) -> None:
        """Filter to show approved PRs."""
        try:
            sidebar = self.query_one("#sidebar", NavigationSidebar)
            sidebar.action_filter_approved()
        except Exception:
            pass
    
    def action_filter_failed(self) -> None:
        """Filter to show PRs with failed checks."""
        try:
            sidebar = self.query_one("#sidebar", NavigationSidebar)
            sidebar.action_filter_failed()
        except Exception:
            pass
    
    # Navigation shortcuts
    def action_goto_first(self) -> None:
        """Go to first PR."""
        self.action_first_item()
    
    def action_goto_last(self) -> None:
        """Go to last PR."""
        self.action_last_item()
    
    def action_half_page_up(self) -> None:
        """Half page up."""
        if self.active_panel == "pr_list":
            try:
                pr_list = self.query_one("#pr-list", PRListWidget)
                # Half page is roughly 5 items
                current_index = pr_list.selected_index
                new_index = max(0, current_index - 5)
                pr_list.select_pr(new_index)
            except Exception:
                pass
    
    def action_half_page_down(self) -> None:
        """Half page down."""
        if self.active_panel == "pr_list":
            try:
                pr_list = self.query_one("#pr-list", PRListWidget)
                # Half page is roughly 5 items
                current_index = pr_list.selected_index
                new_index = min(len(self.pull_requests) - 1, current_index + 5)
                pr_list.select_pr(new_index)
            except Exception:
                pass
    
    # Focus management
    def action_focus_sidebar(self) -> None:
        """Focus the sidebar."""
        self.active_panel = "sidebar"
        self.focus_active_panel()
    
    def action_focus_pr_list(self) -> None:
        """Focus the PR list."""
        self.active_panel = "pr_list"
        self.focus_active_panel()
    
    def action_focus_details(self) -> None:
        """Focus the details panel."""
        if self.details_panel_expanded:
            self.active_panel = "details"
            self.focus_active_panel()
        else:
            # If details panel is not expanded, expand it and focus
            self.details_panel_expanded = True
            self.active_panel = "details"
            self.call_after_refresh(self.focus_active_panel)


def run_tui_app() -> None:
    """Run the PRS TUI application."""
    app = PRSApp()
    app.run()


if __name__ == "__main__":
    run_tui_app()