"""
Real-time build progress widgets for CI/CD monitoring.

Provides progress bars, status indicators, and live updates for
running builds within the TUI interface.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Static, Label, ProgressBar, Button
from textual.reactive import reactive
from textual.binding import Binding
from textual.message import Message
from textual.timer import Timer

from prs.tui.services.realtime_service import StreamEvent, StreamEventType


class BuildStatus(Enum):
    """Build status states."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class BuildProgress:
    """Build progress information."""
    workflow_id: str
    workflow_name: str
    pr_id: int
    status: BuildStatus
    progress: float = 0.0  # 0.0 to 1.0
    start_time: Optional[datetime] = None
    estimated_duration: Optional[int] = None  # seconds
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    error_message: str = ""
    logs_url: str = ""


class AnimatedProgressBar(ProgressBar):
    """Enhanced progress bar with animations and status indicators."""
    
    def __init__(self, build_progress: BuildProgress, **kwargs):
        super().__init__(**kwargs)
        self.build_progress = build_progress
        self.animation_frame = 0
        self.last_update = time.time()
        
    def render_bar(self, progress: float) -> str:
        """Render progress bar with animations."""
        if self.build_progress.status == BuildStatus.RUNNING:
            # Animated progress bar for running builds
            return self._render_animated_bar(progress)
        elif self.build_progress.status == BuildStatus.QUEUED:
            # Pulsing animation for queued builds
            return self._render_pulsing_bar()
        else:
            # Static bar for completed builds
            return super().render_bar(progress)
            
    def _render_animated_bar(self, progress: float) -> str:
        """Render animated progress bar for running builds."""
        bar_width = self.size.width - 2  # Account for borders
        filled_width = int(progress * bar_width)
        
        # Create base bar
        bar = "█" * filled_width + "░" * (bar_width - filled_width)
        
        # Add animation at the progress head
        if filled_width < bar_width and self.build_progress.status == BuildStatus.RUNNING:
            # Animate the next character
            self.animation_frame = (self.animation_frame + 1) % 4
            animation_chars = ["▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"]
            
            if filled_width < len(bar):
                frame_char = animation_chars[self.animation_frame * 2]
                bar = bar[:filled_width] + frame_char + bar[filled_width + 1:]
                
        return bar
        
    def _render_pulsing_bar(self) -> str:
        """Render pulsing animation for queued builds."""
        bar_width = self.size.width - 2
        
        # Create pulsing effect
        self.animation_frame = (self.animation_frame + 1) % 8
        intensity = abs(4 - self.animation_frame) / 4.0
        
        pulse_chars = ["░", "▒", "▓", "█"]
        char_index = int(intensity * (len(pulse_chars) - 1))
        pulse_char = pulse_chars[char_index]
        
        return pulse_char * bar_width


class BuildProgressWidget(Container):
    """Widget displaying progress for a single build."""
    
    build_progress = reactive(None, recompose=True)
    show_details = reactive(False)
    auto_update = reactive(True)
    
    def __init__(self, build_progress: BuildProgress, **kwargs):
        super().__init__(**kwargs)
        self.build_progress = build_progress
        self._update_timer: Optional[Timer] = None
        
    def compose(self) -> ComposeResult:
        """Compose the build progress widget."""
        if not self.build_progress:
            yield Label("No build data")
            return
            
        with Container(classes=f"build-progress build-status-{self.build_progress.status.value}"):
            # Header with build info
            with Horizontal(classes="build-header"):
                yield Label(f"🔧 {self.build_progress.workflow_name}", classes="build-name")
                yield Label(f"PR #{self.build_progress.pr_id}", classes="build-pr")
                yield Label(self._get_status_indicator(), classes="build-status")
                
            # Progress bar
            yield AnimatedProgressBar(
                self.build_progress,
                progress=self.build_progress.progress,
                id=f"progress-{self.build_progress.workflow_id}"
            )
            
            # Progress details
            with Horizontal(classes="build-details"):
                yield Label(self._get_progress_text(), classes="progress-text")
                yield Label(self._get_timing_info(), classes="timing-info")
                
            # Optional detailed view
            if self.show_details:
                yield from self._compose_details()
                
    def _compose_details(self) -> ComposeResult:
        """Compose detailed build information."""
        with Container(classes="build-details-expanded"):
            if self.build_progress.current_step:
                yield Label(f"Current: {self.build_progress.current_step}", classes="current-step")
                
            if self.build_progress.total_steps > 0:
                steps_progress = self.build_progress.completed_steps / self.build_progress.total_steps
                yield Label(f"Steps: {self.build_progress.completed_steps}/{self.build_progress.total_steps}")
                yield ProgressBar(progress=steps_progress, id="steps-progress")
                
            if self.build_progress.error_message:
                yield Label(f"❌ {self.build_progress.error_message}", classes="error-message")
                
            if self.build_progress.logs_url:
                yield Button("View Logs", id="view-logs-btn", variant="primary")
                
    def _get_status_indicator(self) -> str:
        """Get status indicator emoji/text."""
        status_indicators = {
            BuildStatus.QUEUED: "🟡 Queued",
            BuildStatus.RUNNING: "🔄 Running",
            BuildStatus.SUCCESS: "✅ Success",
            BuildStatus.FAILURE: "❌ Failed",
            BuildStatus.CANCELLED: "⚪ Cancelled",
            BuildStatus.TIMEOUT: "⏰ Timeout"
        }
        return status_indicators.get(self.build_progress.status, "❓ Unknown")
        
    def _get_progress_text(self) -> str:
        """Get progress percentage text."""
        percentage = self.build_progress.progress * 100
        return f"{percentage:.1f}%"
        
    def _get_timing_info(self) -> str:
        """Get timing information."""
        if not self.build_progress.start_time:
            return ""
            
        elapsed = datetime.now() - self.build_progress.start_time
        elapsed_str = self._format_duration(elapsed)
        
        if self.build_progress.estimated_duration and self.build_progress.status == BuildStatus.RUNNING:
            remaining = timedelta(seconds=self.build_progress.estimated_duration) - elapsed
            if remaining.total_seconds() > 0:
                remaining_str = self._format_duration(remaining)
                return f"{elapsed_str} / ~{remaining_str}"
                
        return elapsed_str
        
    def _format_duration(self, duration: timedelta) -> str:
        """Format duration for display."""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
            
    def start_auto_update(self):
        """Start automatic progress updates."""
        if self._update_timer:
            self._update_timer.stop()
            
        # Update every second for running builds, every 5 seconds for others
        interval = 1.0 if self.build_progress.status == BuildStatus.RUNNING else 5.0
        self._update_timer = self.set_interval(interval, self._update_progress)
        
    def stop_auto_update(self):
        """Stop automatic progress updates."""
        if self._update_timer:
            self._update_timer.stop()
            self._update_timer = None
            
    def _update_progress(self):
        """Update progress display."""
        if self.build_progress.status == BuildStatus.RUNNING:
            # Simulate progress for running builds (in real implementation,
            # this would fetch actual progress from CI provider)
            self._estimate_progress()
            
        # Update progress bar
        try:
            progress_bar = self.query_one(f"#progress-{self.build_progress.workflow_id}", AnimatedProgressBar)
            progress_bar.progress = self.build_progress.progress
            progress_bar.refresh()
        except:
            pass
            
        # Refresh timing info
        self.refresh()
        
    def _estimate_progress(self):
        """Estimate build progress based on elapsed time."""
        if not self.build_progress.start_time:
            return
            
        elapsed = (datetime.now() - self.build_progress.start_time).total_seconds()
        
        if self.build_progress.estimated_duration:
            # Progress based on estimated duration
            estimated_progress = min(elapsed / self.build_progress.estimated_duration, 0.95)
            self.build_progress.progress = max(self.build_progress.progress, estimated_progress)
        else:
            # Linear progress simulation (fallback)
            # Slow down as we approach completion
            if self.build_progress.progress < 0.8:
                increment = 0.01
            elif self.build_progress.progress < 0.9:
                increment = 0.005
            else:
                increment = 0.001
                
            self.build_progress.progress = min(self.build_progress.progress + increment, 0.95)
            
    def update_build_progress(self, new_progress: BuildProgress):
        """Update with new progress information."""
        self.build_progress = new_progress
        
        # Restart timer if status changed
        if new_progress.status == BuildStatus.RUNNING:
            self.start_auto_update()
        else:
            self.stop_auto_update()
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "view-logs-btn":
            self.post_message(self.LogsRequested(self.build_progress.workflow_id, self.build_progress.logs_url))
            
    def on_mount(self) -> None:
        """Start auto-update when mounted."""
        if self.auto_update and self.build_progress.status == BuildStatus.RUNNING:
            self.start_auto_update()
            
    def on_unmount(self) -> None:
        """Clean up when unmounted."""
        self.stop_auto_update()
        
    class LogsRequested(Message):
        """Message sent when logs viewing is requested."""
        def __init__(self, workflow_id: str, logs_url: str):
            super().__init__()
            self.workflow_id = workflow_id
            self.logs_url = logs_url


class BuildProgressManager(Container):
    """
    Manager widget for multiple build progress displays.
    
    Coordinates real-time updates across multiple builds and provides
    a consolidated view of all active builds.
    """
    
    BINDINGS = [
        Binding("r", "refresh_all", "Refresh All"),
        Binding("c", "clear_completed", "Clear Completed"),
        Binding("d", "toggle_details", "Details"),
        Binding("s", "sort_builds", "Sort"),
    ]
    
    builds = reactive({}, recompose=True)  # workflow_id -> BuildProgress
    show_completed = reactive(True)
    show_details = reactive(False)
    sort_mode = reactive("status")  # status, time, name
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._event_callbacks: List[Callable] = []
        
    def compose(self) -> ComposeResult:
        """Compose the build progress manager."""
        with Container(id="build-progress-manager"):
            # Header
            with Horizontal(classes="manager-header"):
                yield Label("🏗️ Active Builds", classes="manager-title")
                yield Label(f"{len(self.builds)} builds", classes="build-count")
                yield Button("Clear Completed", id="clear-btn", variant="warning")
                
            # Build list
            with Vertical(classes="build-list", id="build-list"):
                if not self.builds:
                    yield Label("No active builds", classes="no-builds")
                else:
                    # Sort builds
                    sorted_builds = self._sort_builds()
                    
                    for build_progress in sorted_builds:
                        # Filter completed builds if configured
                        if not self.show_completed and build_progress.status in [
                            BuildStatus.SUCCESS, BuildStatus.FAILURE, 
                            BuildStatus.CANCELLED, BuildStatus.TIMEOUT
                        ]:
                            continue
                            
                        yield BuildProgressWidget(
                            build_progress,
                            id=f"build-{build_progress.workflow_id}",
                            classes="build-widget"
                        )
                        
    def _sort_builds(self) -> List[BuildProgress]:
        """Sort builds according to current sort mode."""
        builds_list = list(self.builds.values())
        
        if self.sort_mode == "status":
            # Sort by status priority (running first, then queued, etc.)
            status_priority = {
                BuildStatus.RUNNING: 0,
                BuildStatus.QUEUED: 1,
                BuildStatus.FAILURE: 2,
                BuildStatus.SUCCESS: 3,
                BuildStatus.CANCELLED: 4,
                BuildStatus.TIMEOUT: 5
            }
            builds_list.sort(key=lambda b: status_priority.get(b.status, 99))
        elif self.sort_mode == "time":
            # Sort by start time (newest first)
            builds_list.sort(key=lambda b: b.start_time or datetime.min, reverse=True)
        elif self.sort_mode == "name":
            # Sort by workflow name
            builds_list.sort(key=lambda b: b.workflow_name)
            
        return builds_list
        
    def add_build(self, build_progress: BuildProgress):
        """Add a new build to track."""
        self.builds[build_progress.workflow_id] = build_progress
        self.refresh(recompose=True)
        
    def update_build(self, workflow_id: str, build_progress: BuildProgress):
        """Update an existing build's progress."""
        if workflow_id in self.builds:
            self.builds[workflow_id] = build_progress
            
            # Update the specific widget
            try:
                widget = self.query_one(f"#build-{workflow_id}", BuildProgressWidget)
                widget.update_build_progress(build_progress)
            except:
                # Widget might not exist yet, trigger recompose
                self.refresh(recompose=True)
                
    def remove_build(self, workflow_id: str):
        """Remove a build from tracking."""
        if workflow_id in self.builds:
            del self.builds[workflow_id]
            self.refresh(recompose=True)
            
    def clear_completed_builds(self):
        """Clear all completed builds."""
        completed_statuses = {
            BuildStatus.SUCCESS, BuildStatus.FAILURE, 
            BuildStatus.CANCELLED, BuildStatus.TIMEOUT
        }
        
        # Remove completed builds
        self.builds = {
            workflow_id: build for workflow_id, build in self.builds.items()
            if build.status not in completed_statuses
        }
        self.refresh(recompose=True)
        
    def handle_stream_event(self, event: StreamEvent):
        """Handle real-time stream events."""
        if event.event_type == StreamEventType.BUILD_START:
            self._handle_build_start(event)
        elif event.event_type == StreamEventType.BUILD_PROGRESS:
            self._handle_build_progress(event)
        elif event.event_type == StreamEventType.BUILD_COMPLETE:
            self._handle_build_complete(event)
        elif event.event_type == StreamEventType.BUILD_FAILURE:
            self._handle_build_failure(event)
            
    def _handle_build_start(self, event: StreamEvent):
        """Handle build start event."""
        workflow_id = event.data.get('workflow_id')
        workflow_name = event.data.get('workflow_name', 'Unknown Workflow')
        
        build_progress = BuildProgress(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            pr_id=event.pr_id,
            status=BuildStatus.RUNNING,
            progress=0.0,
            start_time=event.timestamp,
            estimated_duration=600  # 10 minutes default estimate
        )
        
        self.add_build(build_progress)
        
    def _handle_build_progress(self, event: StreamEvent):
        """Handle build progress update."""
        workflow_id = event.data.get('workflow_id')
        if workflow_id not in self.builds:
            return
            
        build = self.builds[workflow_id]
        build.progress = event.data.get('progress', build.progress)
        build.current_step = event.data.get('current_step', build.current_step)
        
        self.update_build(workflow_id, build)
        
    def _handle_build_complete(self, event: StreamEvent):
        """Handle build completion."""
        workflow_id = event.data.get('workflow_id')
        if workflow_id not in self.builds:
            return
            
        build = self.builds[workflow_id]
        build.status = BuildStatus.SUCCESS if event.data.get('success', True) else BuildStatus.FAILURE
        build.progress = 1.0
        
        self.update_build(workflow_id, build)
        
    def _handle_build_failure(self, event: StreamEvent):
        """Handle build failure."""
        workflow_id = event.data.get('workflow_id')
        if workflow_id not in self.builds:
            return
            
        build = self.builds[workflow_id]
        build.status = BuildStatus.FAILURE
        build.error_message = event.data.get('error_message', 'Build failed')
        
        self.update_build(workflow_id, build)
        
    def get_summary_stats(self) -> Dict[str, int]:
        """Get summary statistics for all builds."""
        stats = {
            'total': len(self.builds),
            'running': 0,
            'queued': 0,
            'success': 0,
            'failed': 0,
            'cancelled': 0
        }
        
        for build in self.builds.values():
            if build.status == BuildStatus.RUNNING:
                stats['running'] += 1
            elif build.status == BuildStatus.QUEUED:
                stats['queued'] += 1
            elif build.status == BuildStatus.SUCCESS:
                stats['success'] += 1
            elif build.status == BuildStatus.FAILURE:
                stats['failed'] += 1
            elif build.status in [BuildStatus.CANCELLED, BuildStatus.TIMEOUT]:
                stats['cancelled'] += 1
                
        return stats
        
    # Action handlers
    def action_refresh_all(self):
        """Refresh all build progress."""
        self.post_message(self.RefreshAllRequested())
        
    def action_clear_completed(self):
        """Clear completed builds."""
        self.clear_completed_builds()
        
    def action_toggle_details(self):
        """Toggle detailed view for all builds."""
        self.show_details = not self.show_details
        # Update all build widgets
        for widget in self.query(BuildProgressWidget):
            widget.show_details = self.show_details
            widget.refresh(recompose=True)
            
    def action_sort_builds(self):
        """Cycle through sort modes."""
        sort_modes = ["status", "time", "name"]
        current_index = sort_modes.index(self.sort_mode)
        next_index = (current_index + 1) % len(sort_modes)
        self.sort_mode = sort_modes[next_index]
        self.refresh(recompose=True)
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "clear-btn":
            self.action_clear_completed()
            
    class RefreshAllRequested(Message):
        """Message sent when refresh all is requested."""