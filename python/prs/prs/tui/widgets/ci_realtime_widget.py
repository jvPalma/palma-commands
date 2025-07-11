"""
Real-time CI status widget for PRS TUI.
Displays live CI status updates with progress bars and notifications.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, ProgressBar, Label, Button
from textual.reactive import reactive, var
from textual.message import Message
from textual.timer import Timer

from ...ci_tools.base.models import CICheck, BuildStatus
from ..events.events import CIStatusUpdateEvent, PRUpdateEvent
from ..services.realtime_ci_service import RealtimeCIService, CIStatusSnapshot


@dataclass
class CIStatusDisplay:
    """Display information for CI status."""
    pr_id: int
    overall_status: BuildStatus
    checks: List[CICheck]
    last_updated: datetime
    is_active: bool = False
    progress_value: float = 0.0
    status_text: str = ""
    status_color: str = "default"


class CIRealtimeWidget(Container):
    """
    Real-time CI status widget.
    
    Displays live CI status updates with:
    - Progress bars for running builds
    - Status indicators with colors
    - Last updated timestamps
    - Active/stable PR indicators
    """
    
    DEFAULT_CSS = """
    CIRealtimeWidget {
        border: solid $primary;
        height: auto;
        margin: 1;
    }
    
    .ci-header {
        background: $primary 20%;
        color: $text;
        padding: 1;
        text-align: center;
        font-weight: bold;
    }
    
    .ci-status-item {
        padding: 1;
        margin: 1;
        border: solid $accent;
        height: auto;
    }
    
    .ci-status-item.active {
        border: solid $success;
        background: $success 10%;
    }
    
    .ci-status-item.failed {
        border: solid $error;
        background: $error 10%;
    }
    
    .ci-status-item.passed {
        border: solid $success;
        background: $success 10%;
    }
    
    .ci-status-item.pending {
        border: solid $warning;
        background: $warning 10%;
    }
    
    .ci-progress {
        width: 100%;
        margin: 1 0;
    }
    
    .ci-checks-list {
        margin: 1 0;
    }
    
    .ci-check-item {
        margin: 0 2;
        padding: 0 1;
    }
    
    .ci-timestamp {
        color: $text-muted;
        text-align: right;
        font-size: 0.9em;
    }
    
    .ci-controls {
        padding: 1;
        text-align: center;
    }
    """
    
    # Reactive properties
    pr_statuses: reactive[Dict[int, CIStatusDisplay]] = reactive({})
    show_all_checks: reactive[bool] = reactive(False)
    auto_refresh: reactive[bool] = reactive(True)
    
    def __init__(self, realtime_service: RealtimeCIService, **kwargs):
        super().__init__(**kwargs)
        self.realtime_service = realtime_service
        self.update_timer: Optional[Timer] = None
        
        # Subscribe to real-time events
        self.realtime_service.add_status_update_callback(self._on_ci_status_update)
        self.realtime_service.add_pr_update_callback(self._on_pr_update)
    
    def compose(self) -> ComposeResult:
        """Compose the CI real-time widget."""
        with Vertical():
            yield Static("🔄 Real-time CI Status", classes="ci-header")
            
            with Container(id="ci-status-container"):
                yield self._create_status_display()
            
            with Horizontal(classes="ci-controls"):
                yield Button("Refresh", id="refresh-btn", variant="primary")
                yield Button("Toggle Details", id="details-btn", variant="secondary")
                yield Button("Settings", id="settings-btn", variant="secondary")
    
    def _create_status_display(self) -> Container:
        """Create the status display container."""
        container = Container(id="ci-status-list")
        
        if not self.pr_statuses:
            container.compose_add_child(Static("No CI data available", classes="empty-state"))
            return container
        
        # Sort PRs by priority (active first, then by last updated)
        sorted_prs = sorted(
            self.pr_statuses.items(),
            key=lambda x: (not x[1].is_active, x[1].last_updated),
            reverse=True
        )
        
        for pr_id, status_display in sorted_prs:
            container.compose_add_child(self._create_pr_status_item(pr_id, status_display))
        
        return container
    
    def _create_pr_status_item(self, pr_id: int, status_display: CIStatusDisplay) -> Container:
        """Create a status item for a single PR."""
        # Determine CSS classes based on status
        classes = ["ci-status-item"]
        if status_display.is_active:
            classes.append("active")
        classes.append(status_display.overall_status.value.lower())
        
        with Container(classes=" ".join(classes)):
            # PR header with status
            with Horizontal():
                yield Static(f"PR #{pr_id}", classes="pr-title")
                yield Static(self._get_status_icon(status_display.overall_status), classes="status-icon")
                yield Static(status_display.status_text, classes="status-text")
                yield Static(
                    self._format_timestamp(status_display.last_updated),
                    classes="ci-timestamp"
                )
            
            # Progress bar for active builds
            if status_display.is_active and status_display.progress_value > 0:
                yield ProgressBar(
                    total=100,
                    progress=status_display.progress_value,
                    classes="ci-progress"
                )
            
            # Checks list
            if self.show_all_checks and status_display.checks:
                with Vertical(classes="ci-checks-list"):
                    for check in status_display.checks:
                        yield self._create_check_item(check)
    
    def _create_check_item(self, check: CICheck) -> Horizontal:
        """Create a display item for a single check."""
        with Horizontal(classes="ci-check-item"):
            yield Static(self._get_status_icon(check.status), classes="check-icon")
            yield Static(check.name, classes="check-name")
            yield Static(check.status.value, classes="check-status")
            if check.details_url:
                yield Button("🔗", id=f"check-link-{check.id}", classes="check-link")
    
    def _get_status_icon(self, status: BuildStatus) -> str:
        """Get icon for build status."""
        icons = {
            BuildStatus.PASSED: "✅",
            BuildStatus.FAILED: "❌",
            BuildStatus.PENDING: "⏳",
            BuildStatus.UNKNOWN: "❓"
        }
        return icons.get(status, "❓")
    
    def _format_timestamp(self, timestamp: datetime) -> str:
        """Format timestamp for display."""
        now = datetime.now()
        delta = now - timestamp
        
        if delta.total_seconds() < 60:
            return "just now"
        elif delta.total_seconds() < 3600:
            minutes = int(delta.total_seconds() / 60)
            return f"{minutes}m ago"
        elif delta.total_seconds() < 86400:
            hours = int(delta.total_seconds() / 3600)
            return f"{hours}h ago"
        else:
            return timestamp.strftime("%m/%d %H:%M")
    
    def _on_ci_status_update(self, event: CIStatusUpdateEvent):
        """Handle CI status update event."""
        # Update status display
        self.pr_statuses[event.pr_id] = CIStatusDisplay(
            pr_id=event.pr_id,
            overall_status=event.status,
            checks=event.checks,
            last_updated=event.timestamp,
            is_active=event.status == BuildStatus.PENDING,
            progress_value=self._calculate_progress(event.checks),
            status_text=self._get_status_text(event.status),
            status_color=self._get_status_color(event.status)
        )
        
        # Trigger UI refresh
        self.refresh()
    
    def _on_pr_update(self, event: PRUpdateEvent):
        """Handle PR update event."""
        if event.update_type == "ci_status":
            # Update from PR update event
            if event.pr_id in self.pr_statuses:
                status_display = self.pr_statuses[event.pr_id]
                status_display.last_updated = event.timestamp
                self.refresh()
    
    def _calculate_progress(self, checks: List[CICheck]) -> float:
        """Calculate progress percentage for checks."""
        if not checks:
            return 0.0
        
        completed = sum(1 for check in checks if check.status != BuildStatus.PENDING)
        return (completed / len(checks)) * 100
    
    def _get_status_text(self, status: BuildStatus) -> str:
        """Get status text for display."""
        text_map = {
            BuildStatus.PASSED: "All checks passed",
            BuildStatus.FAILED: "Some checks failed",
            BuildStatus.PENDING: "Checks running...",
            BuildStatus.UNKNOWN: "Status unknown"
        }
        return text_map.get(status, "Unknown")
    
    def _get_status_color(self, status: BuildStatus) -> str:
        """Get color for status."""
        color_map = {
            BuildStatus.PASSED: "success",
            BuildStatus.FAILED: "error",
            BuildStatus.PENDING: "warning",
            BuildStatus.UNKNOWN: "default"
        }
        return color_map.get(status, "default")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "refresh-btn":
            self._refresh_data()
        elif event.button.id == "details-btn":
            self.show_all_checks = not self.show_all_checks
            self.refresh()
        elif event.button.id == "settings-btn":
            self._open_settings()
        elif event.button.id and event.button.id.startswith("check-link-"):
            check_id = event.button.id.replace("check-link-", "")
            self._open_check_details(check_id)
    
    def _refresh_data(self):
        """Manually refresh CI data."""
        self.realtime_service.force_refresh()
        
        # Show refresh feedback
        self.notify("Refreshing CI data...", severity="info")
    
    def _open_settings(self):
        """Open CI settings modal."""
        # This would open a settings modal
        self.notify("Settings not implemented yet", severity="warning")
    
    def _open_check_details(self, check_id: str):
        """Open check details in browser."""
        # This would open the check details URL
        self.notify(f"Opening check {check_id}...", severity="info")
    
    def watch_pr_statuses(self, pr_statuses: Dict[int, CIStatusDisplay]) -> None:
        """Watch for changes in PR statuses."""
        self.refresh()
    
    def update_pr_data(self, pr_ids: Set[int]):
        """Update the list of PRs to monitor."""
        # Remove statuses for PRs no longer in the list
        self.pr_statuses = {
            pr_id: status for pr_id, status in self.pr_statuses.items()
            if pr_id in pr_ids
        }
        
        # Update real-time service
        self.realtime_service.update_pr_list(pr_ids)
        
        self.refresh()
    
    def start_auto_refresh(self, interval: int = 30):
        """Start automatic refresh timer."""
        if self.update_timer:
            self.update_timer.stop()
        
        self.update_timer = self.set_interval(interval, self._auto_refresh)
        self.auto_refresh = True
    
    def stop_auto_refresh(self):
        """Stop automatic refresh timer."""
        if self.update_timer:
            self.update_timer.stop()
            self.update_timer = None
        
        self.auto_refresh = False
    
    def _auto_refresh(self):
        """Automatic refresh callback."""
        if self.auto_refresh:
            self._refresh_data()
    
    def get_service_stats(self) -> Dict[str, any]:
        """Get real-time service statistics."""
        return self.realtime_service.get_service_stats()
    
    def on_mount(self) -> None:
        """Handle widget mount."""
        # Start auto-refresh by default
        self.start_auto_refresh()
    
    def on_unmount(self) -> None:
        """Handle widget unmount."""
        # Stop auto-refresh
        self.stop_auto_refresh()


class CIProgressModal(Container):
    """Modal for showing detailed CI progress."""
    
    DEFAULT_CSS = """
    CIProgressModal {
        border: thick $primary;
        background: $surface;
        width: 80%;
        height: 80%;
        margin: 2;
        padding: 2;
    }
    
    .progress-header {
        background: $primary;
        color: $text;
        padding: 1;
        margin-bottom: 1;
        text-align: center;
    }
    
    .progress-content {
        height: 1fr;
        overflow: auto;
    }
    
    .progress-item {
        margin: 1;
        padding: 1;
        border: solid $accent;
    }
    
    .progress-footer {
        text-align: center;
        padding: 1;
    }
    """
    
    def __init__(self, pr_id: int, checks: List[CICheck], **kwargs):
        super().__init__(**kwargs)
        self.pr_id = pr_id
        self.checks = checks
    
    def compose(self) -> ComposeResult:
        """Compose the progress modal."""
        with Vertical():
            yield Static(f"CI Progress for PR #{self.pr_id}", classes="progress-header")
            
            with Container(classes="progress-content"):
                for check in self.checks:
                    with Container(classes="progress-item"):
                        yield Static(f"🔧 {check.name}", classes="check-name")
                        yield Static(f"Status: {check.status.value}", classes="check-status")
                        if check.details_url:
                            yield Button("View Details", id=f"view-{check.id}")
                        
                        # Progress bar if pending
                        if check.status == BuildStatus.PENDING:
                            yield ProgressBar(total=100, progress=50, classes="check-progress")
            
            with Container(classes="progress-footer"):
                yield Button("Close", id="close-modal", variant="primary")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "close-modal":
            self.remove()
        elif event.button.id and event.button.id.startswith("view-"):
            check_id = event.button.id.replace("view-", "")
            # Open check details
            self.notify(f"Opening check {check_id}...", severity="info")