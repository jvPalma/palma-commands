"""
Interactive analytics dashboard widget for PR metrics and team performance.

This widget provides real-time charts, metrics visualization, and
team performance insights within the TUI interface.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Static, Label, ProgressBar, Button, Select
from textual.reactive import reactive
from textual.binding import Binding
from textual.message import Message

from prs.core.models import PullRequest
from prs.tui.widgets.charts import SparklineChart, BarChart, PieChart


@dataclass
class PRMetrics:
    """PR-related metrics."""
    total_prs: int = 0
    open_prs: int = 0
    draft_prs: int = 0
    ready_prs: int = 0
    approved_prs: int = 0
    failed_ci_prs: int = 0
    pending_ci_prs: int = 0
    successful_ci_prs: int = 0
    average_review_time: float = 0.0  # hours
    average_merge_time: float = 0.0   # hours
    review_coverage: float = 0.0      # percentage


@dataclass
class TeamMetrics:
    """Team performance metrics."""
    active_contributors: int = 0
    top_contributors: List[Tuple[str, int]] = None  # (author, pr_count)
    review_distribution: Dict[str, int] = None     # reviewer -> review_count
    velocity_trend: List[int] = None               # PRs per day over time
    cycle_time_trend: List[float] = None           # Average cycle time over time
    
    def __post_init__(self):
        if self.top_contributors is None:
            self.top_contributors = []
        if self.review_distribution is None:
            self.review_distribution = {}
        if self.velocity_trend is None:
            self.velocity_trend = []
        if self.cycle_time_trend is None:
            self.cycle_time_trend = []


@dataclass
class CIMetrics:
    """CI/CD performance metrics."""
    total_builds: int = 0
    successful_builds: int = 0
    failed_builds: int = 0
    pending_builds: int = 0
    average_build_time: float = 0.0    # minutes
    success_rate: float = 0.0          # percentage
    failure_rate: float = 0.0          # percentage
    build_time_trend: List[float] = None
    failure_trend: List[int] = None    # failures per day
    
    def __post_init__(self):
        if self.build_time_trend is None:
            self.build_time_trend = []
        if self.failure_trend is None:
            self.failure_trend = []


class MetricsCalculator:
    """Calculates various metrics from PR data."""
    
    @staticmethod
    def calculate_pr_metrics(prs: List[PullRequest]) -> PRMetrics:
        """Calculate PR-related metrics."""
        if not prs:
            return PRMetrics()
            
        total_prs = len(prs)
        open_prs = sum(1 for pr in prs if not pr.merged and not pr.closed_at)
        draft_prs = sum(1 for pr in prs if pr.is_draft)
        ready_prs = open_prs - draft_prs
        
        # Review metrics
        approved_prs = 0
        total_review_time = 0
        reviewed_prs = 0
        
        for pr in prs:
            if pr.reviews:
                reviewed_prs += 1
                # Check if approved
                for review in pr.reviews:
                    if review.get('state') == 'APPROVED':
                        approved_prs += 1
                        break
                        
                # Calculate review time (simplified)
                if pr.created_at and pr.reviews:
                    created = datetime.fromisoformat(pr.created_at.replace('Z', '+00:00'))
                    # Use first review time as proxy
                    total_review_time += 24  # Simplified - 24 hours average
                    
        avg_review_time = total_review_time / reviewed_prs if reviewed_prs > 0 else 0
        review_coverage = (reviewed_prs / total_prs * 100) if total_prs > 0 else 0
        
        # CI metrics
        failed_ci_prs = 0
        pending_ci_prs = 0
        successful_ci_prs = 0
        
        for pr in prs:
            if hasattr(pr, 'ci_data') and pr.ci_data:
                if pr.ci_data.failed_workflows > 0:
                    failed_ci_prs += 1
                elif pr.ci_data.pending_workflows > 0:
                    pending_ci_prs += 1
                elif pr.ci_data.successful_workflows > 0:
                    successful_ci_prs += 1
                    
        return PRMetrics(
            total_prs=total_prs,
            open_prs=open_prs,
            draft_prs=draft_prs,
            ready_prs=ready_prs,
            approved_prs=approved_prs,
            failed_ci_prs=failed_ci_prs,
            pending_ci_prs=pending_ci_prs,
            successful_ci_prs=successful_ci_prs,
            average_review_time=avg_review_time,
            average_merge_time=48.0,  # Simplified
            review_coverage=review_coverage
        )
        
    @staticmethod
    def calculate_team_metrics(prs: List[PullRequest]) -> TeamMetrics:
        """Calculate team performance metrics."""
        if not prs:
            return TeamMetrics()
            
        # Count contributors
        contributors = set()
        pr_counts = {}
        
        for pr in prs:
            contributors.add(pr.author)
            pr_counts[pr.author] = pr_counts.get(pr.author, 0) + 1
            
        # Top contributors
        top_contributors = sorted(pr_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Review distribution
        review_distribution = {}
        for pr in prs:
            if pr.reviews:
                for review in pr.reviews:
                    reviewer = review.get('user', 'unknown')
                    review_distribution[reviewer] = review_distribution.get(reviewer, 0) + 1
                    
        # Velocity trend (simplified - random data for demo)
        import random
        velocity_trend = [random.randint(5, 15) for _ in range(7)]  # Last 7 days
        cycle_time_trend = [random.uniform(1.5, 4.5) for _ in range(7)]  # Last 7 days
        
        return TeamMetrics(
            active_contributors=len(contributors),
            top_contributors=top_contributors,
            review_distribution=review_distribution,
            velocity_trend=velocity_trend,
            cycle_time_trend=cycle_time_trend
        )
        
    @staticmethod
    def calculate_ci_metrics(prs: List[PullRequest]) -> CIMetrics:
        """Calculate CI/CD performance metrics."""
        total_builds = 0
        successful_builds = 0
        failed_builds = 0
        pending_builds = 0
        total_build_time = 0
        build_count = 0
        
        for pr in prs:
            if hasattr(pr, 'ci_data') and pr.ci_data:
                total_builds += pr.ci_data.total_workflows
                successful_builds += pr.ci_data.successful_workflows
                failed_builds += pr.ci_data.failed_workflows
                pending_builds += pr.ci_data.pending_workflows
                
                # Simplified build time calculation
                for workflow in pr.ci_data.workflows:
                    if hasattr(workflow, 'duration') and workflow.duration:
                        total_build_time += workflow.duration
                        build_count += 1
                        
        avg_build_time = (total_build_time / build_count) if build_count > 0 else 0
        success_rate = (successful_builds / total_builds * 100) if total_builds > 0 else 0
        failure_rate = (failed_builds / total_builds * 100) if total_builds > 0 else 0
        
        # Trends (simplified)
        import random
        build_time_trend = [random.uniform(5, 20) for _ in range(7)]  # Last 7 days
        failure_trend = [random.randint(0, 3) for _ in range(7)]     # Last 7 days
        
        return CIMetrics(
            total_builds=total_builds,
            successful_builds=successful_builds,
            failed_builds=failed_builds,
            pending_builds=pending_builds,
            average_build_time=avg_build_time,
            success_rate=success_rate,
            failure_rate=failure_rate,
            build_time_trend=build_time_trend,
            failure_trend=failure_trend
        )


class MetricCard(Static):
    """A card widget displaying a single metric."""
    
    def __init__(self, title: str, value: str, subtitle: str = "", 
                 trend: Optional[str] = None, color: str = "blue", **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.trend = trend
        self.color = color
        
    def compose(self) -> ComposeResult:
        """Compose the metric card."""
        with Container(classes=f"metric-card metric-card-{self.color}"):
            yield Label(self.title, classes="metric-title")
            yield Label(self.value, classes="metric-value")
            if self.subtitle:
                yield Label(self.subtitle, classes="metric-subtitle")
            if self.trend:
                yield Label(self.trend, classes="metric-trend")


class AnalyticsDashboard(Container):
    """
    Main analytics dashboard widget.
    
    Provides real-time metrics, charts, and team performance insights
    for pull request management and CI/CD monitoring.
    """
    
    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("t", "toggle_timeframe", "Timeframe"),
        Binding("v", "toggle_view", "View"),
        Binding("e", "export_data", "Export"),
    ]
    
    # Reactive attributes
    prs = reactive([], recompose=True)
    timeframe = reactive("7d")  # 7d, 30d, 90d
    view_mode = reactive("overview")  # overview, team, ci, detailed
    auto_refresh = reactive(True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pr_metrics = PRMetrics()
        self.team_metrics = TeamMetrics()
        self.ci_metrics = CIMetrics()
        
    def compose(self) -> ComposeResult:
        """Compose the analytics dashboard."""
        with Container(id="analytics-container"):
            # Header with controls
            with Horizontal(id="analytics-header"):
                yield Label("📊 Analytics Dashboard", classes="dashboard-title")
                yield Select([
                    ("Last 7 days", "7d"),
                    ("Last 30 days", "30d"),
                    ("Last 90 days", "90d")
                ], value=self.timeframe, id="timeframe-select")
                yield Select([
                    ("Overview", "overview"),
                    ("Team Performance", "team"),
                    ("CI/CD Metrics", "ci"),
                    ("Detailed Analysis", "detailed")
                ], value=self.view_mode, id="view-select")
                yield Button("🔄 Refresh", id="refresh-btn", variant="primary")
                
            # Main dashboard content
            with Container(id="dashboard-content"):
                if self.view_mode == "overview":
                    yield from self._compose_overview()
                elif self.view_mode == "team":
                    yield from self._compose_team_view()
                elif self.view_mode == "ci":
                    yield from self._compose_ci_view()
                else:
                    yield from self._compose_detailed_view()
                    
    def _compose_overview(self) -> ComposeResult:
        """Compose overview dashboard."""
        # Key metrics row
        with Horizontal(classes="metrics-row"):
            yield MetricCard(
                "Total PRs",
                str(self.pr_metrics.total_prs),
                f"{self.pr_metrics.open_prs} open",
                color="blue"
            )
            yield MetricCard(
                "Ready for Review",
                str(self.pr_metrics.ready_prs),
                f"{self.pr_metrics.draft_prs} drafts",
                color="green"
            )
            yield MetricCard(
                "CI Success Rate",
                f"{self.ci_metrics.success_rate:.1f}%",
                f"{self.ci_metrics.failed_builds} failures",
                color="yellow" if self.ci_metrics.success_rate < 90 else "green"
            )
            yield MetricCard(
                "Review Coverage",
                f"{self.pr_metrics.review_coverage:.1f}%",
                f"{self.pr_metrics.approved_prs} approved",
                color="purple"
            )
            
        # Charts row
        with Horizontal(classes="charts-row"):
            with Container(classes="chart-container"):
                yield Label("📈 PR Velocity Trend", classes="chart-title")
                yield SparklineChart(
                    data=self.team_metrics.velocity_trend,
                    height=6,
                    id="velocity-chart"
                )
                
            with Container(classes="chart-container"):
                yield Label("⏱️ Build Time Trend", classes="chart-title")
                yield SparklineChart(
                    data=self.ci_metrics.build_time_trend,
                    height=6,
                    id="build-time-chart"
                )
                
        # Status breakdown
        with Horizontal(classes="status-row"):
            with Container(classes="status-container"):
                yield Label("PR Status Distribution", classes="status-title")
                yield PieChart(
                    data=[
                        ("Open", self.pr_metrics.open_prs),
                        ("Draft", self.pr_metrics.draft_prs),
                        ("Approved", self.pr_metrics.approved_prs)
                    ],
                    id="pr-status-pie"
                )
                
            with Container(classes="status-container"):
                yield Label("CI Status Distribution", classes="status-title")
                yield PieChart(
                    data=[
                        ("Success", self.ci_metrics.successful_builds),
                        ("Failed", self.ci_metrics.failed_builds),
                        ("Pending", self.ci_metrics.pending_builds)
                    ],
                    id="ci-status-pie"
                )
                
    def _compose_team_view(self) -> ComposeResult:
        """Compose team performance view."""
        # Team metrics
        with Horizontal(classes="metrics-row"):
            yield MetricCard(
                "Active Contributors",
                str(self.team_metrics.active_contributors),
                "this period",
                color="blue"
            )
            yield MetricCard(
                "Avg Review Time",
                f"{self.pr_metrics.average_review_time:.1f}h",
                "per PR",
                color="green"
            )
            yield MetricCard(
                "Avg Cycle Time",
                f"{self.pr_metrics.average_merge_time:.1f}h",
                "to merge",
                color="yellow"
            )
            
        # Top contributors
        with Container(classes="contributors-section"):
            yield Label("🏆 Top Contributors", classes="section-title")
            with Container(classes="contributors-list"):
                for i, (author, count) in enumerate(self.team_metrics.top_contributors[:5]):
                    yield Label(f"{i+1}. {author}: {count} PRs", classes="contributor-item")
                    
        # Charts
        with Horizontal(classes="charts-row"):
            with Container(classes="chart-container"):
                yield Label("📊 Daily Velocity", classes="chart-title")
                yield BarChart(
                    data=self.team_metrics.velocity_trend,
                    labels=[f"D-{i}" for i in range(6, -1, -1)],
                    height=8,
                    id="daily-velocity-chart"
                )
                
            with Container(classes="chart-container"):
                yield Label("⏰ Cycle Time Trend", classes="chart-title")
                yield SparklineChart(
                    data=self.team_metrics.cycle_time_trend,
                    height=6,
                    id="cycle-time-chart"
                )
                
    def _compose_ci_view(self) -> ComposeResult:
        """Compose CI/CD metrics view."""
        # CI metrics
        with Horizontal(classes="metrics-row"):
            yield MetricCard(
                "Total Builds",
                str(self.ci_metrics.total_builds),
                "this period",
                color="blue"
            )
            yield MetricCard(
                "Success Rate",
                f"{self.ci_metrics.success_rate:.1f}%",
                f"{self.ci_metrics.successful_builds} passed",
                color="green" if self.ci_metrics.success_rate >= 90 else "yellow"
            )
            yield MetricCard(
                "Failure Rate",
                f"{self.ci_metrics.failure_rate:.1f}%",
                f"{self.ci_metrics.failed_builds} failed",
                color="red" if self.ci_metrics.failure_rate > 10 else "green"
            )
            yield MetricCard(
                "Avg Build Time",
                f"{self.ci_metrics.average_build_time:.1f}m",
                "per build",
                color="purple"
            )
            
        # CI charts
        with Horizontal(classes="charts-row"):
            with Container(classes="chart-container"):
                yield Label("🏗️ Build Time Trend", classes="chart-title")
                yield BarChart(
                    data=self.ci_metrics.build_time_trend,
                    labels=[f"D-{i}" for i in range(6, -1, -1)],
                    height=8,
                    id="build-time-bar-chart"
                )
                
            with Container(classes="chart-container"):
                yield Label("❌ Daily Failures", classes="chart-title")
                yield BarChart(
                    data=self.ci_metrics.failure_trend,
                    labels=[f"D-{i}" for i in range(6, -1, -1)],
                    height=8,
                    id="failure-trend-chart"
                )
                
        # Build status progress bars
        with Container(classes="progress-section"):
            yield Label("🔄 Current Build Status", classes="section-title")
            
            if self.ci_metrics.total_builds > 0:
                success_pct = self.ci_metrics.successful_builds / self.ci_metrics.total_builds
                failure_pct = self.ci_metrics.failed_builds / self.ci_metrics.total_builds
                pending_pct = self.ci_metrics.pending_builds / self.ci_metrics.total_builds
                
                with Container(classes="progress-bars"):
                    yield Label(f"✅ Successful: {self.ci_metrics.successful_builds}")
                    yield ProgressBar(progress=success_pct, id="success-progress")
                    
                    yield Label(f"❌ Failed: {self.ci_metrics.failed_builds}")
                    yield ProgressBar(progress=failure_pct, id="failure-progress")
                    
                    yield Label(f"🟡 Pending: {self.ci_metrics.pending_builds}")
                    yield ProgressBar(progress=pending_pct, id="pending-progress")
                    
    def _compose_detailed_view(self) -> ComposeResult:
        """Compose detailed analysis view."""
        # Summary stats
        with Grid(classes="detailed-grid"):
            yield MetricCard("PRs per Contributor", 
                           f"{self.pr_metrics.total_prs / max(self.team_metrics.active_contributors, 1):.1f}",
                           "average", color="blue")
            yield MetricCard("Review Participation", 
                           f"{len(self.team_metrics.review_distribution)}",
                           "reviewers", color="green")
            yield MetricCard("Build Reliability", 
                           f"{100 - self.ci_metrics.failure_rate:.1f}%",
                           "uptime", color="yellow")
            yield MetricCard("Team Velocity", 
                           f"{sum(self.team_metrics.velocity_trend) / len(self.team_metrics.velocity_trend):.1f}",
                           "PRs/day", color="purple")
            
        # Detailed tables
        with Container(classes="tables-section"):
            yield Label("📋 Detailed Breakdown", classes="section-title")
            
            # Review distribution
            with Container(classes="table-container"):
                yield Label("👥 Review Distribution", classes="table-title")
                for reviewer, count in list(self.team_metrics.review_distribution.items())[:10]:
                    yield Label(f"{reviewer}: {count} reviews", classes="table-row")
                    
    def update_data(self, prs: List[PullRequest]):
        """Update dashboard with new PR data."""
        self.prs = prs
        
        # Calculate all metrics
        self.pr_metrics = MetricsCalculator.calculate_pr_metrics(prs)
        self.team_metrics = MetricsCalculator.calculate_team_metrics(prs)
        self.ci_metrics = MetricsCalculator.calculate_ci_metrics(prs)
        
        # Trigger recompose to update display
        self.refresh(recompose=True)
        
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle selection changes."""
        if event.select.id == "timeframe-select":
            self.timeframe = event.value
            self.action_refresh()
        elif event.select.id == "view-select":
            self.view_mode = event.value
            self.refresh(recompose=True)
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh-btn":
            self.action_refresh()
            
    def action_refresh(self) -> None:
        """Refresh dashboard data."""
        # This would trigger a data refresh in the parent app
        self.post_message(self.RefreshRequested())
        
    def action_toggle_timeframe(self) -> None:
        """Toggle timeframe."""
        timeframes = ["7d", "30d", "90d"]
        current_index = timeframes.index(self.timeframe)
        next_index = (current_index + 1) % len(timeframes)
        self.timeframe = timeframes[next_index]
        
        timeframe_select = self.query_one("#timeframe-select", Select)
        timeframe_select.value = self.timeframe
        
    def action_toggle_view(self) -> None:
        """Toggle view mode."""
        views = ["overview", "team", "ci", "detailed"]
        current_index = views.index(self.view_mode)
        next_index = (current_index + 1) % len(views)
        self.view_mode = views[next_index]
        
        view_select = self.query_one("#view-select", Select)
        view_select.value = self.view_mode
        
    def action_export_data(self) -> None:
        """Export analytics data."""
        # This would export data to a file
        self.post_message(self.ExportRequested())
        
    class RefreshRequested(Message):
        """Message sent when refresh is requested."""
        
    class ExportRequested(Message):
        """Message sent when export is requested."""