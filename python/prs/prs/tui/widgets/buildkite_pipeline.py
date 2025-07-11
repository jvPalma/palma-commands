"""
Buildkite pipeline visualization widget for TUI.

Provides interactive visualization of Buildkite pipelines, builds,
jobs, and dependencies within the terminal interface.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid, ScrollableContainer
from textual.widgets import Static, Label, ProgressBar, Button, Select, Tree, DataTable
from textual.reactive import reactive
from textual.binding import Binding
from textual.message import Message
from textual.timer import Timer

from prs.ci_tools.buildkite.client import (
    BuildkiteClient, BuildkitePipeline, BuildkiteBuild, 
    BuildkiteJob, BuildkiteArtifact
)


@dataclass
class PipelineNode:
    """Represents a node in the pipeline visualization."""
    id: str
    name: str
    type: str  # pipeline, build, job, step
    state: str
    children: List['PipelineNode']
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if self.children is None:
            self.children = []


class PipelineTreeWidget(Tree):
    """Tree widget for displaying pipeline structure."""
    
    def __init__(self, pipeline: BuildkitePipeline, **kwargs):
        super().__init__(pipeline.name, **kwargs)
        self.pipeline = pipeline
        self.build_nodes: Dict[str, Any] = {}
        
    def update_with_builds(self, builds: List[BuildkiteBuild]):
        """Update tree with build information."""
        self.clear()
        self.build_nodes.clear()
        
        # Group builds by branch
        builds_by_branch = {}
        for build in builds:
            branch = build.branch
            if branch not in builds_by_branch:
                builds_by_branch[branch] = []
            builds_by_branch[branch].append(build)
            
        # Create tree structure
        for branch, branch_builds in builds_by_branch.items():
            # Sort builds by number (newest first)
            branch_builds.sort(key=lambda b: b.number, reverse=True)
            
            # Add branch node
            branch_node = self.root.add(f"📋 {branch}")
            
            # Add builds for this branch (limit to latest 10)
            for build in branch_builds[:10]:
                status_icon = self._get_status_icon(build.state)
                build_label = f"{status_icon} #{build.number} - {build.message[:50]}"
                if len(build.message) > 50:
                    build_label += "..."
                    
                build_node = branch_node.add(build_label)
                self.build_nodes[str(build_node.id)] = build
                
    def _get_status_icon(self, state: str) -> str:
        """Get icon for build state."""
        status_icons = {
            "passed": "✅",
            "failed": "❌", 
            "running": "🔄",
            "scheduled": "⏰",
            "canceled": "⚪",
            "skipped": "⏭️",
            "blocked": "🚫",
            "canceling": "⏹️"
        }
        return status_icons.get(state, "❓")
        
    def get_selected_build(self) -> Optional[BuildkiteBuild]:
        """Get the currently selected build."""
        if self.cursor_node and str(self.cursor_node.id) in self.build_nodes:
            return self.build_nodes[str(self.cursor_node.id)]
        return None


class BuildDetailsWidget(Container):
    """Widget displaying detailed build information."""
    
    build = reactive(None, recompose=True)
    jobs = reactive([], recompose=True)
    artifacts = reactive([], recompose=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client: Optional[BuildkiteClient] = None
        
    def compose(self) -> ComposeResult:
        """Compose build details widget."""
        if not self.build:
            yield Label("Select a build to view details", classes="no-selection")
            return
            
        with Container(classes="build-details"):
            # Build header
            with Horizontal(classes="build-header"):
                status_icon = self._get_status_icon(self.build.state)
                yield Label(f"{status_icon} Build #{self.build.number}", classes="build-title")
                yield Label(f"State: {self.build.state}", classes="build-state")
                if self.build.duration:
                    duration_str = self._format_duration(self.build.duration)
                    yield Label(f"Duration: {duration_str}", classes="build-duration")
                    
            # Build info
            with Grid(classes="build-info-grid"):
                yield Label("Message:", classes="info-label")
                yield Label(self.build.message, classes="info-value")
                
                yield Label("Branch:", classes="info-label")
                yield Label(self.build.branch, classes="info-value")
                
                yield Label("Commit:", classes="info-label")
                yield Label(self.build.commit[:8], classes="info-value")
                
                yield Label("Creator:", classes="info-label")
                creator_name = self.build.creator.get('name', 'Unknown')
                yield Label(creator_name, classes="info-value")
                
                if self.build.is_pull_request_build:
                    yield Label("PR:", classes="info-label")
                    yield Label(f"#{self.build.pr_number}", classes="info-value")
                    
            # Actions
            with Horizontal(classes="build-actions"):
                yield Button("🔄 Rebuild", id="rebuild-btn", variant="primary")
                yield Button("❌ Cancel", id="cancel-btn", variant="warning")
                yield Button("🌐 Open in Browser", id="open-btn", variant="default")
                yield Button("📊 View Logs", id="logs-btn", variant="default")
                
            # Jobs section
            if self.jobs:
                yield Label("Jobs:", classes="section-title")
                yield self._create_jobs_table()
                
            # Artifacts section
            if self.artifacts:
                yield Label("Artifacts:", classes="section-title")
                yield self._create_artifacts_table()
                
    def _create_jobs_table(self) -> DataTable:
        """Create jobs data table."""
        table = DataTable(id="jobs-table")
        table.add_columns("Name", "State", "Duration", "Exit Code")
        
        for job in self.jobs:
            status_icon = self._get_status_icon(job.state)
            name = f"{status_icon} {job.name or 'Unnamed'}"
            
            duration = ""
            if job.duration:
                duration = self._format_duration(job.duration)
                
            exit_code = str(job.exit_status) if job.exit_status is not None else ""
            
            table.add_row(name, job.state, duration, exit_code)
            
        return table
        
    def _create_artifacts_table(self) -> DataTable:
        """Create artifacts data table."""
        table = DataTable(id="artifacts-table")
        table.add_columns("Filename", "Size", "Type", "Actions")
        
        for artifact in self.artifacts:
            size_str = self._format_file_size(artifact.file_size)
            actions = "📥 Download"  # Simplified - would be a button in real implementation
            
            table.add_row(
                artifact.filename,
                size_str,
                artifact.mime_type,
                actions
            )
            
        return table
        
    def _get_status_icon(self, state: str) -> str:
        """Get icon for job/build state."""
        status_icons = {
            "passed": "✅",
            "failed": "❌",
            "running": "🔄", 
            "scheduled": "⏰",
            "assigned": "👤",
            "accepted": "✋",
            "canceled": "⚪",
            "skipped": "⏭️",
            "broken": "💥",
            "expired": "⏰",
            "finished": "🏁"
        }
        return status_icons.get(state, "❓")
        
    def _format_duration(self, duration: timedelta) -> str:
        """Format duration for display."""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
            
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size for display."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
        
    async def update_build(self, build: BuildkiteBuild, client: BuildkiteClient):
        """Update with new build information."""
        self.build = build
        self.client = client
        
        if client and build:
            # Load jobs and artifacts asynchronously
            pipeline_slug = build.pipeline.get('slug', '')
            
            # Get jobs
            jobs = client.get_build_jobs(pipeline_slug, build.number)
            self.jobs = jobs
            
            # Get artifacts
            artifacts = client.get_build_artifacts(pipeline_slug, build.number)
            self.artifacts = artifacts
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if not self.build or not self.client:
            return
            
        pipeline_slug = self.build.pipeline.get('slug', '')
        
        if event.button.id == "rebuild-btn":
            success = self.client.rebuild(pipeline_slug, self.build.number)
            if success:
                self.post_message(self.BuildRebuilt(self.build.number))
            else:
                self.post_message(self.ActionFailed("Failed to rebuild"))
                
        elif event.button.id == "cancel-btn":
            if self.build.state in ["running", "scheduled"]:
                success = self.client.cancel_build(pipeline_slug, self.build.number)
                if success:
                    self.post_message(self.BuildCanceled(self.build.number))
                else:
                    self.post_message(self.ActionFailed("Failed to cancel"))
                    
        elif event.button.id == "open-btn":
            import webbrowser
            webbrowser.open(self.build.web_url)
            
        elif event.button.id == "logs-btn":
            self.post_message(self.LogsRequested(self.build))
            
    class BuildRebuilt(Message):
        def __init__(self, build_number: int):
            super().__init__()
            self.build_number = build_number
            
    class BuildCanceled(Message):
        def __init__(self, build_number: int):
            super().__init__()
            self.build_number = build_number
            
    class ActionFailed(Message):
        def __init__(self, error_message: str):
            super().__init__()
            self.error_message = error_message
            
    class LogsRequested(Message):
        def __init__(self, build: BuildkiteBuild):
            super().__init__()
            self.build = build


class PipelineMetricsWidget(Container):
    """Widget displaying pipeline performance metrics."""
    
    metrics = reactive({}, recompose=True)
    timeframe = reactive(30)  # days
    
    def compose(self) -> ComposeResult:
        """Compose metrics widget."""
        if not self.metrics:
            yield Label("Loading metrics...", classes="loading")
            return
            
        with Container(classes="pipeline-metrics"):
            yield Label("📊 Pipeline Metrics", classes="section-title")
            
            # Key metrics
            with Grid(classes="metrics-grid"):
                yield Label("Total Builds:", classes="metric-label")
                yield Label(str(self.metrics.get("total_builds", 0)), classes="metric-value")
                
                yield Label("Success Rate:", classes="metric-label")
                success_rate = self.metrics.get("success_rate", 0)
                yield Label(f"{success_rate:.1f}%", classes="metric-value")
                
                yield Label("Avg Duration:", classes="metric-label")
                avg_duration = self.metrics.get("average_duration")
                if avg_duration:
                    duration_str = self._format_duration(timedelta(seconds=avg_duration))
                    yield Label(duration_str, classes="metric-value")
                else:
                    yield Label("N/A", classes="metric-value")
                    
                yield Label("Builds/Day:", classes="metric-label")
                builds_per_day = self.metrics.get("builds_per_day", 0)
                yield Label(f"{builds_per_day:.1f}", classes="metric-value")
                
            # Progress bars for success rate
            if self.metrics.get("total_builds", 0) > 0:
                success_pct = success_rate / 100.0
                yield Label(f"Success Rate: {success_rate:.1f}%")
                yield ProgressBar(progress=success_pct, id="success-rate-bar")
                
    def _format_duration(self, duration: timedelta) -> str:
        """Format duration for display."""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m"
        else:
            return f"{seconds}s"
            
    def update_metrics(self, metrics: Dict[str, Any]):
        """Update with new metrics."""
        self.metrics = metrics


class BuildkitePipelineWidget(Container):
    """
    Main Buildkite pipeline visualization widget.
    
    Provides comprehensive pipeline monitoring with build history,
    job details, metrics, and interactive controls.
    """
    
    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("f", "filter_builds", "Filter"),
        Binding("m", "toggle_metrics", "Metrics"),
        Binding("s", "pipeline_settings", "Settings"),
        Binding("h", "help", "Help"),
    ]
    
    pipeline = reactive(None, recompose=True)
    builds = reactive([], recompose=True)
    selected_build = reactive(None)
    show_metrics = reactive(True)
    filter_state = reactive("all")  # all, passed, failed, running
    
    def __init__(self, pipeline_slug: str, **kwargs):
        super().__init__(**kwargs)
        self.pipeline_slug = pipeline_slug
        self.client: Optional[BuildkiteClient] = None
        self._refresh_timer: Optional[Timer] = None
        self._auto_refresh = True
        
    def compose(self) -> ComposeResult:
        """Compose the pipeline widget."""
        with Container(id="buildkite-pipeline-container"):
            # Header
            with Horizontal(classes="pipeline-header"):
                if self.pipeline:
                    yield Label(f"🔧 {self.pipeline.name}", classes="pipeline-title")
                    yield Label(f"({self.pipeline.slug})", classes="pipeline-slug")
                else:
                    yield Label("Loading pipeline...", classes="loading-title")
                    
                # Filter controls
                yield Select([
                    ("All Builds", "all"),
                    ("Passed", "passed"),
                    ("Failed", "failed"),
                    ("Running", "running"),
                    ("Scheduled", "scheduled")
                ], value=self.filter_state, id="filter-select")
                
                yield Button("🔄 Refresh", id="refresh-btn", variant="primary")
                
            # Main content
            with Horizontal(classes="pipeline-content"):
                # Left panel - Pipeline tree
                with Container(classes="pipeline-tree-panel", id="tree-panel"):
                    if self.pipeline:
                        yield PipelineTreeWidget(self.pipeline, id="pipeline-tree")
                    else:
                        yield Label("Loading...", classes="loading")
                        
                # Right panel - Build details
                with Container(classes="build-details-panel", id="details-panel"):
                    yield BuildDetailsWidget(id="build-details")
                    
            # Bottom panel - Metrics (optional)
            if self.show_metrics:
                with Container(classes="metrics-panel", id="metrics-panel"):
                    yield PipelineMetricsWidget(id="pipeline-metrics")
                    
    async def initialize(self, client: BuildkiteClient):
        """Initialize the widget with Buildkite client."""
        self.client = client
        
        # Load pipeline information
        pipeline = client.get_pipeline(self.pipeline_slug)
        if pipeline:
            self.pipeline = pipeline
            
        # Load initial builds
        await self._refresh_builds()
        
        # Start auto-refresh
        if self._auto_refresh:
            self._start_auto_refresh()
            
    async def _refresh_builds(self):
        """Refresh builds from Buildkite."""
        if not self.client:
            return
            
        # Determine state filter
        state_filter = None if self.filter_state == "all" else self.filter_state
        
        # Get recent builds
        builds = self.client.get_builds(
            pipeline_slug=self.pipeline_slug,
            state=state_filter,
            created_from=datetime.now() - timedelta(days=30),
            per_page=50
        )
        
        self.builds = builds
        
        # Update tree widget
        try:
            tree_widget = self.query_one("#pipeline-tree", PipelineTreeWidget)
            tree_widget.update_with_builds(builds)
        except:
            pass
            
        # Update metrics
        if self.show_metrics:
            metrics = self.client.get_pipeline_metrics(self.pipeline_slug, days=30)
            try:
                metrics_widget = self.query_one("#pipeline-metrics", PipelineMetricsWidget)
                metrics_widget.update_metrics(metrics)
            except:
                pass
                
    def _start_auto_refresh(self):
        """Start automatic refresh timer."""
        if self._refresh_timer:
            self._refresh_timer.stop()
            
        # Refresh every 30 seconds
        self._refresh_timer = self.set_interval(30.0, self._auto_refresh_callback)
        
    def _stop_auto_refresh(self):
        """Stop automatic refresh timer."""
        if self._refresh_timer:
            self._refresh_timer.stop()
            self._refresh_timer = None
            
    async def _auto_refresh_callback(self):
        """Auto-refresh callback."""
        if self._auto_refresh:
            await self._refresh_builds()
            
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        tree_widget = self.query_one("#pipeline-tree", PipelineTreeWidget)
        selected_build = tree_widget.get_selected_build()
        
        if selected_build:
            self.selected_build = selected_build
            
            # Update build details
            details_widget = self.query_one("#build-details", BuildDetailsWidget)
            asyncio.create_task(details_widget.update_build(selected_build, self.client))
            
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle filter selection changes."""
        if event.select.id == "filter-select":
            self.filter_state = event.value
            asyncio.create_task(self._refresh_builds())
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh-btn":
            asyncio.create_task(self._refresh_builds())
            
    # Action handlers
    def action_refresh(self) -> None:
        """Refresh builds."""
        asyncio.create_task(self._refresh_builds())
        
    def action_filter_builds(self) -> None:
        """Cycle through filter options."""
        filters = ["all", "passed", "failed", "running", "scheduled"]
        current_index = filters.index(self.filter_state)
        next_index = (current_index + 1) % len(filters)
        self.filter_state = filters[next_index]
        
        # Update select widget
        filter_select = self.query_one("#filter-select", Select)
        filter_select.value = self.filter_state
        
    def action_toggle_metrics(self) -> None:
        """Toggle metrics panel."""
        self.show_metrics = not self.show_metrics
        self.refresh(recompose=True)
        
    def action_pipeline_settings(self) -> None:
        """Show pipeline settings."""
        # TODO: Implement settings modal
        pass
        
    def action_help(self) -> None:
        """Show help information."""
        # TODO: Implement help modal
        pass
        
    def on_mount(self) -> None:
        """Handle widget mounting."""
        pass
        
    def on_unmount(self) -> None:
        """Handle widget unmounting."""
        self._stop_auto_refresh()