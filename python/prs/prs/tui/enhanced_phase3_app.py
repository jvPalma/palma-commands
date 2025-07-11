"""
Enhanced Phase 3 PRS TUI Application.

Integrates all Phase 3 enhancements including real-time streaming,
smart polling, analytics dashboard, build progress monitoring,
notifications, Buildkite integration, and team performance tracking.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, TabbedContent, TabPane
from textual.reactive import reactive
from textual.worker import Worker
from textual.message import Message

from prs.config import get, all_config
from prs.core.models import PullRequest
from prs.core.usecases import list_pull_requests
from prs.tui.data.data_manager import TUIDataManager
from prs.tui.services.update_service import UpdateService
from prs.tui.services.realtime_service import RealTimeStreamService
from prs.tui.services.smart_polling import SmartPollingManager
from prs.tui.services.notification_service import NotificationService
from prs.ci_tools.buildkite.client import BuildkiteClient

# Enhanced widgets
from prs.tui.widgets.header import HeaderWidget
from prs.tui.widgets.footer import FooterWidget
from prs.tui.widgets.status_bar import StatusBarWidget
from prs.tui.widgets.pr_list import PRListWidget
from prs.tui.widgets.analytics_dashboard import AnalyticsDashboard
from prs.tui.widgets.build_progress import BuildProgressManager
from prs.tui.widgets.buildkite_pipeline import BuildkitePipelineWidget
from prs.tui.widgets.logs_viewer import LogsViewerWidget
from prs.tui.widgets.team_dashboard import TeamDashboard


class EnhancedPRSApp(App):
    """
    Enhanced PRS TUI Application with Phase 3 features.
    
    Provides comprehensive PR management with real-time updates,
    advanced analytics, build monitoring, and team collaboration insights.
    """
    
    CSS_PATH = "styles/enhanced_app.tcss"
    TITLE = "PRS - Enhanced Pull Request Management"
    SUB_TITLE = "Real-time CI/CD Monitoring & Team Analytics"
    
    # Reactive attributes
    loading = reactive(False)
    error_message = reactive("")
    current_tab = reactive("prs")
    
    # Data
    pull_requests: List[PullRequest] = reactive([], recompose=True)
    selected_pr: Optional[PullRequest] = reactive(None)
    
    # Configuration
    config: Dict[str, Any] = reactive({})
    
    BINDINGS = [
        Binding("ctrl+c,q", "quit", "Quit", show=True),
        Binding("ctrl+r", "force_refresh", "Force Refresh", show=True),
        Binding("ctrl+n", "notifications", "Notifications", show=True),
        Binding("ctrl+b", "buildkite", "Buildkite", show=True),
        Binding("ctrl+a", "analytics", "Analytics", show=True),
        Binding("ctrl+t", "team", "Team", show=True),
        Binding("ctrl+l", "logs", "Logs", show=True),
        Binding("f1", "help", "Help", show=True),
        Binding("f2", "settings", "Settings", show=True),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Core services
        self.data_manager: Optional[TUIDataManager] = None
        self.update_service: Optional[UpdateService] = None
        self.stream_service: Optional[RealTimeStreamService] = None
        self.polling_manager: Optional[SmartPollingManager] = None
        self.notification_service: Optional[NotificationService] = None
        
        # External integrations
        self.buildkite_client: Optional[BuildkiteClient] = None
        
        # State
        self.last_refresh = datetime.now()
        self.services_initialized = False
        
    def compose(self) -> ComposeResult:
        """Compose the enhanced application layout."""
        with Container(id="enhanced-app-container"):
            yield HeaderWidget(id="header")
            
            with TabbedContent(id="main-tabs"):
                # Main PR list tab
                with TabPane("Pull Requests", id="prs-tab"):
                    with Vertical():
                        yield StatusBarWidget(id="status-bar")
                        yield PRListWidget(id="pr-list")
                        
                # Analytics dashboard tab
                with TabPane("Analytics", id="analytics-tab"):
                    yield AnalyticsDashboard(id="analytics-dashboard")
                    
                # Build monitoring tab
                with TabPane("Builds", id="builds-tab"):
                    yield BuildProgressManager(id="build-progress")
                    
                # Buildkite integration tab
                with TabPane("Pipelines", id="pipelines-tab"):
                    if self._is_buildkite_configured():
                        pipeline_slug = get("buildkite", "default_pipeline", fallback="")
                        if pipeline_slug:
                            yield BuildkitePipelineWidget(pipeline_slug, id="buildkite-pipeline")
                        else:
                            yield Container(Static("No default pipeline configured"))
                    else:
                        yield Container(Static("Buildkite not configured"))
                        
                # Logs viewer tab
                with TabPane("Logs", id="logs-tab"):
                    yield LogsViewerWidget(id="logs-viewer")
                    
                # Team dashboard tab
                with TabPane("Team", id="team-tab"):
                    yield TeamDashboard(id="team-dashboard")
                    
            yield FooterWidget(id="footer")
            
    def on_mount(self) -> None:
        """Initialize the enhanced application."""
        self.load_configuration()
        self.call_after_refresh(self.initialize_services)
        
    async def initialize_services(self):
        """Initialize all enhanced services."""
        if self.services_initialized:
            return
            
        try:
            # Initialize core data manager
            self.data_manager = TUIDataManager()
            
            # Initialize streaming service
            self.stream_service = RealTimeStreamService(self.data_manager)
            self.stream_service.add_event_callback(self._on_stream_event)
            self.stream_service.start_streaming()
            
            # Initialize update service
            self.update_service = UpdateService(self.data_manager)
            self.update_service.add_update_callback(self._on_data_update)
            self.update_service.start()
            
            # Initialize smart polling
            self.polling_manager = SmartPollingManager(self.data_manager, self.stream_service)
            self.polling_manager.start_polling()
            
            # Initialize notification service
            self.notification_service = NotificationService()
            self.notification_service.start()
            self.stream_service.add_event_callback(self.notification_service.handle_stream_event)
            
            # Initialize Buildkite client if configured
            if self._is_buildkite_configured():
                self.buildkite_client = BuildkiteClient()
                if self.buildkite_client.test_connection():
                    self.update_status("Buildkite integration active")
                    
            # Load initial data
            await self._load_initial_data()
            
            # Start monitoring active PRs
            self._start_pr_monitoring()
            
            self.services_initialized = True
            self.update_status("Enhanced services initialized")
            
        except Exception as e:
            self.error_message = f"Failed to initialize services: {str(e)}"
            
    async def _load_initial_data(self):
        """Load initial PR data."""
        self.loading = True
        try:
            # Load PRs through data manager
            include_drafts = self.config.get("pr-info", {}).get("include_drafts", "false").lower() == "true"
            prs = await self.data_manager.load_initial_data(include_drafts)
            
            self.pull_requests = prs
            self.last_refresh = datetime.now()
            
            # Update all dashboard widgets
            self._update_dashboards()
            
            self.update_status(f"Loaded {len(prs)} PRs")
            
        except Exception as e:
            self.error_message = f"Failed to load PR data: {str(e)}"
        finally:
            self.loading = False
            
    def _start_pr_monitoring(self):
        """Start monitoring active PRs for real-time updates."""
        if not self.polling_manager:
            return
            
        # Register pollers for active PRs
        for pr in self.pull_requests:
            self.polling_manager.register_pr_poller(pr.id)
            
            # Boost monitoring for PRs with active builds
            if hasattr(pr, 'ci_data') and pr.ci_data and pr.ci_data.pending_workflows > 0:
                self.polling_manager.boost_pr_polling(pr.id, duration_seconds=300)
                
    def _update_dashboards(self):
        """Update all dashboard widgets with current data."""
        try:
            # Update analytics dashboard
            analytics = self.query_one("#analytics-dashboard", AnalyticsDashboard)
            analytics.update_data(self.pull_requests)
        except:
            pass
            
        try:
            # Update team dashboard
            team_dashboard = self.query_one("#team-dashboard", TeamDashboard)
            team_dashboard.update_data(self.pull_requests)
        except:
            pass
            
    def _on_stream_event(self, event):
        """Handle real-time stream events."""
        # Update build progress manager
        try:
            build_manager = self.query_one("#build-progress", BuildProgressManager)
            build_manager.handle_stream_event(event)
        except:
            pass
            
        # Show notification in status bar for critical events
        if event.event_type.name in ["BUILD_FAILURE", "BUILD_COMPLETE"]:
            message = f"PR #{event.pr_id}: {event.event_type.name.replace('_', ' ').title()}"
            self.update_status(message)
            
    def _on_data_update(self, update):
        """Handle data updates."""
        if update.update_type in ['initial', 'refresh']:
            self.pull_requests = update.data
            self.last_refresh = update.timestamp
            self._update_dashboards()
        elif update.update_type == 'pr_update':
            # Update specific PR in list
            self._update_pr_in_list(update.data)
            
    def _update_pr_in_list(self, updated_pr: PullRequest):
        """Update a specific PR in the list."""
        for i, pr in enumerate(self.pull_requests):
            if pr.id == updated_pr.id:
                self.pull_requests[i] = updated_pr
                break
                
    def load_configuration(self) -> None:
        """Load PRS configuration."""
        try:
            self.config = all_config()
            
            # Set window title with repo info
            repo_name = get("git", "repo_name", fallback="Unknown Repo")
            username = get("git", "username", fallback="Unknown User")
            self.title = f"PRS Enhanced - {repo_name} ({username})"
            
        except Exception as e:
            self.error_message = f"Failed to load configuration: {str(e)}"
            
    def _is_buildkite_configured(self) -> bool:
        """Check if Buildkite is properly configured."""
        return bool(
            get("buildkite", "api_token", fallback="") and
            get("buildkite", "organization", fallback="")
        )
        
    def update_status(self, message: str):
        """Update status bar message."""
        try:
            status_bar = self.query_one("#status-bar", StatusBarWidget)
            status_bar.set_status(message)
        except:
            pass
            
    def update_header_refresh_time(self):
        """Update header with last refresh time."""
        try:
            header = self.query_one("#header", HeaderWidget)
            header.update_refresh_time(self.last_refresh)
        except:
            pass
            
    # Tab change handling
    def on_tabbed_content_tab_activated(self, event) -> None:
        """Handle tab activation."""
        self.current_tab = event.tab.id
        
        # Initialize tab-specific data if needed
        if event.tab.id == "pipelines-tab" and self.buildkite_client:
            self._initialize_buildkite_tab()
        elif event.tab.id == "logs-tab":
            self._initialize_logs_tab()
            
    def _initialize_buildkite_tab(self):
        """Initialize Buildkite pipeline tab."""
        try:
            pipeline_widget = self.query_one("#buildkite-pipeline", BuildkitePipelineWidget)
            if self.buildkite_client:
                asyncio.create_task(pipeline_widget.initialize(self.buildkite_client))
        except:
            pass
            
    def _initialize_logs_tab(self):
        """Initialize logs viewer tab."""
        # If a PR is selected, load its logs
        if self.selected_pr and self.buildkite_client:
            try:
                logs_viewer = self.query_one("#logs-viewer", LogsViewerWidget)
                # This would need integration with the selected PR's build data
            except:
                pass
                
    # Message handlers for dashboard interactions
    def on_analytics_dashboard_refresh_requested(self, message) -> None:
        """Handle analytics dashboard refresh request."""
        asyncio.create_task(self._refresh_data())
        
    def on_team_dashboard_refresh_requested(self, message) -> None:
        """Handle team dashboard refresh request."""
        asyncio.create_task(self._refresh_data())
        
    def on_build_progress_manager_refresh_all_requested(self, message) -> None:
        """Handle build progress refresh request."""
        # Trigger refresh of build data
        if self.polling_manager:
            for pr in self.pull_requests:
                self.polling_manager.boost_pr_polling(pr.id, duration_seconds=60)
                
    def on_logs_viewer_widget_logs_saved(self, message) -> None:
        """Handle logs saved notification."""
        self.update_status(f"Logs saved to {message.filename}")
        
    def on_logs_viewer_widget_save_failed(self, message) -> None:
        """Handle logs save failure."""
        self.update_status(f"Failed to save logs: {message.error}")
        
    async def _refresh_data(self):
        """Refresh all data."""
        if not self.data_manager:
            return
            
        self.loading = True
        try:
            # Refresh through data manager
            prs = await self.data_manager.refresh_pr_data()
            self.pull_requests = prs
            self.last_refresh = datetime.now()
            
            # Update dashboards
            self._update_dashboards()
            self.update_header_refresh_time()
            
            self.update_status(f"Refreshed {len(prs)} PRs")
            
        except Exception as e:
            self.error_message = f"Failed to refresh data: {str(e)}"
        finally:
            self.loading = False
            
    # Action handlers
    def action_quit(self) -> None:
        """Quit the application."""
        self._cleanup_services()
        self.exit()
        
    def action_force_refresh(self) -> None:
        """Force refresh all data."""
        asyncio.create_task(self._refresh_data())
        
    def action_notifications(self) -> None:
        """Show notifications panel."""
        if self.notification_service:
            stats = self.notification_service.get_notification_stats()
            message = f"Notifications: {stats['total_notifications']} sent, {stats['active_rules']} rules active"
            self.update_status(message)
            
    def action_buildkite(self) -> None:
        """Switch to Buildkite tab."""
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)
            tabs.active = "pipelines-tab"
        except:
            pass
            
    def action_analytics(self) -> None:
        """Switch to analytics tab."""
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)
            tabs.active = "analytics-tab"
        except:
            pass
            
    def action_team(self) -> None:
        """Switch to team dashboard tab."""
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)
            tabs.active = "team-tab"
        except:
            pass
            
    def action_logs(self) -> None:
        """Switch to logs viewer tab."""
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)
            tabs.active = "logs-tab"
        except:
            pass
            
    def action_help(self) -> None:
        """Show help information."""
        help_text = """
Enhanced PRS - Phase 3 Features:

Real-time Features:
- Live CI status updates
- Build progress monitoring
- Smart notifications

Analytics:
- PR velocity metrics
- Team performance insights
- Build success rates

Integrations:
- Buildkite pipeline visualization
- Build logs viewer
- Multi-channel notifications

Navigation:
- Ctrl+A: Analytics Dashboard
- Ctrl+T: Team Performance
- Ctrl+B: Buildkite Pipelines
- Ctrl+L: Logs Viewer
- Ctrl+N: Notification Status
"""
        self.update_status("Help: See key bindings and features above")
        
    def action_settings(self) -> None:
        """Show settings dialog."""
        # TODO: Implement settings modal
        self.update_status("Settings dialog not implemented yet")
        
    def _cleanup_services(self):
        """Clean up all services before exit."""
        if self.stream_service:
            self.stream_service.stop_streaming()
            self.stream_service.cleanup()
            
        if self.update_service:
            self.update_service.stop()
            self.update_service.cleanup()
            
        if self.polling_manager:
            self.polling_manager.stop_polling()
            self.polling_manager.cleanup()
            
        if self.notification_service:
            self.notification_service.stop()
            self.notification_service.cleanup()
            
        if self.data_manager:
            self.data_manager.cleanup()


def run_enhanced_prs_app() -> None:
    """Run the enhanced PRS TUI application."""
    app = EnhancedPRSApp()
    app.run()


if __name__ == "__main__":
    run_enhanced_prs_app()