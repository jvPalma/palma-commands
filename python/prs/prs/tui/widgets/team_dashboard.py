"""
Team performance dashboard widgets for PRS TUI.

Provides comprehensive team analytics, individual performance metrics,
collaboration insights, and productivity tracking.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import statistics

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid, ScrollableContainer
from textual.widgets import Static, Label, ProgressBar, Button, Select, DataTable
from textual.reactive import reactive
from textual.binding import Binding
from textual.message import Message

from prs.core.models import PullRequest
from prs.tui.widgets.charts import SparklineChart, BarChart, PieChart


@dataclass
class ContributorStats:
    """Individual contributor statistics."""
    username: str
    name: str = ""
    avatar_url: str = ""
    
    # PR metrics
    total_prs: int = 0
    open_prs: int = 0
    merged_prs: int = 0
    draft_prs: int = 0
    
    # Review metrics
    reviews_given: int = 0
    reviews_received: int = 0
    approval_rate: float = 0.0  # percentage of PRs that get approved
    
    # Time metrics
    avg_pr_size: float = 0.0  # lines changed
    avg_cycle_time: float = 0.0  # hours from PR to merge
    avg_review_time: float = 0.0  # hours to review
    
    # Quality metrics
    ci_success_rate: float = 0.0
    revert_rate: float = 0.0
    
    # Activity
    commits_count: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    files_changed: int = 0
    
    # Collaboration
    unique_reviewers: int = 0
    cross_team_prs: int = 0
    
    @property
    def productivity_score(self) -> float:
        """Calculate overall productivity score (0-100)."""
        # Weighted scoring based on various metrics
        scores = []
        
        # PR activity (30%)
        if self.total_prs > 0:
            pr_score = min(self.total_prs * 10, 100)  # 10 points per PR, max 100
            scores.append((pr_score, 0.3))
        
        # Review participation (20%)
        review_score = min(self.reviews_given * 5, 100)  # 5 points per review
        scores.append((review_score, 0.2))
        
        # Quality (25%)
        quality_score = (self.ci_success_rate + (100 - self.revert_rate * 10)) / 2
        scores.append((quality_score, 0.25))
        
        # Timeliness (15%)
        if self.avg_cycle_time > 0:
            # Lower cycle time = higher score
            time_score = max(0, 100 - (self.avg_cycle_time / 24) * 10)  # Penalty for long cycles
            scores.append((time_score, 0.15))
        
        # Collaboration (10%)
        collab_score = min(self.unique_reviewers * 20, 100)  # 20 points per unique reviewer
        scores.append((collab_score, 0.1))
        
        if not scores:
            return 0.0
            
        weighted_sum = sum(score * weight for score, weight in scores)
        total_weight = sum(weight for _, weight in scores)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0


@dataclass
class TeamStats:
    """Team-wide statistics."""
    total_contributors: int = 0
    active_contributors: int = 0  # contributors with activity in timeframe
    
    # PR metrics
    total_prs: int = 0
    avg_prs_per_contributor: float = 0.0
    pr_velocity: float = 0.0  # PRs per day
    
    # Review metrics
    review_coverage: float = 0.0  # percentage of PRs that get reviewed
    avg_reviews_per_pr: float = 0.0
    review_response_time: float = 0.0  # average time to first review
    
    # Collaboration
    cross_review_rate: float = 0.0  # percentage of reviews from different authors
    knowledge_sharing_score: float = 0.0  # how well knowledge is distributed
    
    # Quality
    overall_ci_success_rate: float = 0.0
    overall_revert_rate: float = 0.0
    
    # Time metrics
    avg_cycle_time: float = 0.0
    cycle_time_trend: List[float] = None
    
    def __post_init__(self):
        if self.cycle_time_trend is None:
            self.cycle_time_trend = []


class TeamMetricsCalculator:
    """Calculates team performance metrics from PR data."""
    
    @staticmethod
    def calculate_contributor_stats(prs: List[PullRequest], 
                                  username: str,
                                  timeframe_days: int = 30) -> ContributorStats:
        """Calculate statistics for a specific contributor."""
        stats = ContributorStats(username=username)
        
        # Filter PRs for this contributor
        user_prs = [pr for pr in prs if pr.author == username]
        
        if not user_prs:
            return stats
            
        # Basic PR metrics
        stats.total_prs = len(user_prs)
        stats.open_prs = sum(1 for pr in user_prs if not pr.merged and not pr.closed_at)
        stats.merged_prs = sum(1 for pr in user_prs if pr.merged)
        stats.draft_prs = sum(1 for pr in user_prs if pr.is_draft)
        
        # Review metrics - reviews given
        stats.reviews_given = 0
        for pr in prs:  # All PRs, not just user's
            if pr.reviews:
                for review in pr.reviews:
                    if review.get('user') == username and pr.author != username:
                        stats.reviews_given += 1
                        
        # Reviews received
        stats.reviews_received = sum(len(pr.reviews) for pr in user_prs if pr.reviews)
        
        # Approval rate
        approved_prs = 0
        for pr in user_prs:
            if pr.reviews:
                for review in pr.reviews:
                    if review.get('state') == 'APPROVED':
                        approved_prs += 1
                        break
        stats.approval_rate = (approved_prs / stats.total_prs * 100) if stats.total_prs > 0 else 0
        
        # Size metrics
        total_additions = sum(pr.additions for pr in user_prs if pr.additions)
        total_deletions = sum(pr.deletions for pr in user_prs if pr.deletions)
        total_files = sum(pr.changed_files for pr in user_prs if pr.changed_files)
        
        stats.lines_added = total_additions
        stats.lines_deleted = total_deletions
        stats.files_changed = total_files
        stats.avg_pr_size = (total_additions + total_deletions) / stats.total_prs if stats.total_prs > 0 else 0
        
        # CI success rate
        ci_successes = 0
        ci_total = 0
        for pr in user_prs:
            if hasattr(pr, 'ci_data') and pr.ci_data:
                ci_total += 1
                if pr.ci_data.failed_workflows == 0 and pr.ci_data.successful_workflows > 0:
                    ci_successes += 1
        stats.ci_success_rate = (ci_successes / ci_total * 100) if ci_total > 0 else 0
        
        # Collaboration metrics
        reviewers = set()
        for pr in user_prs:
            if pr.reviews:
                for review in pr.reviews:
                    reviewer = review.get('user')
                    if reviewer and reviewer != username:
                        reviewers.add(reviewer)
        stats.unique_reviewers = len(reviewers)
        
        # Time metrics (simplified - would need actual timestamps)
        stats.avg_cycle_time = 48.0  # Simplified - 48 hours average
        stats.avg_review_time = 6.0   # Simplified - 6 hours average
        
        return stats
    
    @staticmethod
    def calculate_team_stats(prs: List[PullRequest], 
                           timeframe_days: int = 30) -> TeamStats:
        """Calculate team-wide statistics."""
        stats = TeamStats()
        
        if not prs:
            return stats
            
        # Get all contributors
        contributors = set(pr.author for pr in prs)
        stats.total_contributors = len(contributors)
        stats.active_contributors = len(contributors)  # All are active in this timeframe
        
        # PR metrics
        stats.total_prs = len(prs)
        stats.avg_prs_per_contributor = stats.total_prs / stats.active_contributors if stats.active_contributors > 0 else 0
        stats.pr_velocity = stats.total_prs / timeframe_days
        
        # Review metrics
        reviewed_prs = sum(1 for pr in prs if pr.reviews)
        stats.review_coverage = (reviewed_prs / stats.total_prs * 100) if stats.total_prs > 0 else 0
        
        total_reviews = sum(len(pr.reviews) for pr in prs if pr.reviews)
        stats.avg_reviews_per_pr = total_reviews / stats.total_prs if stats.total_prs > 0 else 0
        
        # Cross-review rate
        cross_reviews = 0
        total_reviews_counted = 0
        for pr in prs:
            if pr.reviews:
                for review in pr.reviews:
                    total_reviews_counted += 1
                    if review.get('user') != pr.author:
                        cross_reviews += 1
        stats.cross_review_rate = (cross_reviews / total_reviews_counted * 100) if total_reviews_counted > 0 else 0
        
        # Quality metrics
        ci_successes = 0
        ci_total = 0
        for pr in prs:
            if hasattr(pr, 'ci_data') and pr.ci_data:
                ci_total += 1
                if pr.ci_data.failed_workflows == 0 and pr.ci_data.successful_workflows > 0:
                    ci_successes += 1
        stats.overall_ci_success_rate = (ci_successes / ci_total * 100) if ci_total > 0 else 0
        
        # Time metrics (simplified)
        stats.avg_cycle_time = 48.0  # hours
        stats.review_response_time = 8.0  # hours
        stats.cycle_time_trend = [45, 50, 48, 42, 46, 44, 48]  # Last 7 days
        
        # Knowledge sharing (simplified calculation)
        # Based on how evenly reviews are distributed
        review_distribution = defaultdict(int)
        for pr in prs:
            if pr.reviews:
                for review in pr.reviews:
                    reviewer = review.get('user')
                    if reviewer:
                        review_distribution[reviewer] += 1
                        
        if review_distribution:
            review_counts = list(review_distribution.values())
            std_dev = statistics.stdev(review_counts) if len(review_counts) > 1 else 0
            mean_reviews = statistics.mean(review_counts)
            # Lower std dev relative to mean = better knowledge sharing
            stats.knowledge_sharing_score = max(0, 100 - (std_dev / mean_reviews * 100)) if mean_reviews > 0 else 0
        
        return stats


class ContributorCard(Container):
    """Widget displaying individual contributor metrics."""
    
    def __init__(self, contributor_stats: ContributorStats, **kwargs):
        super().__init__(**kwargs)
        self.stats = contributor_stats
        
    def compose(self) -> ComposeResult:
        """Compose contributor card."""
        with Container(classes="contributor-card"):
            # Header
            with Horizontal(classes="contributor-header"):
                yield Label(f"👤 {self.stats.username}", classes="contributor-name")
                productivity = self.stats.productivity_score
                yield Label(f"Score: {productivity:.0f}", classes="productivity-score")
                
            # Key metrics
            with Grid(classes="contributor-metrics"):
                yield Label("PRs:", classes="metric-label")
                yield Label(str(self.stats.total_prs), classes="metric-value")
                
                yield Label("Reviews:", classes="metric-label")
                yield Label(str(self.stats.reviews_given), classes="metric-value")
                
                yield Label("CI Success:", classes="metric-label")
                yield Label(f"{self.stats.ci_success_rate:.0f}%", classes="metric-value")
                
                yield Label("Cycle Time:", classes="metric-label")
                yield Label(f"{self.stats.avg_cycle_time:.0f}h", classes="metric-value")
                
            # Progress bars
            yield Label("Approval Rate")
            yield ProgressBar(progress=self.stats.approval_rate / 100, classes="approval-bar")
            
            yield Label("Productivity Score")
            yield ProgressBar(progress=productivity / 100, classes="productivity-bar")


class TeamOverviewWidget(Container):
    """Widget displaying team-wide overview metrics."""
    
    team_stats = reactive(None, recompose=True)
    
    def compose(self) -> ComposeResult:
        """Compose team overview."""
        if not self.team_stats:
            yield Label("Loading team data...", classes="loading")
            return
            
        with Container(classes="team-overview"):
            yield Label("👥 Team Overview", classes="section-title")
            
            # Key metrics grid
            with Grid(classes="team-metrics-grid"):
                yield Label("Active Contributors:", classes="team-metric-label")
                yield Label(str(self.team_stats.active_contributors), classes="team-metric-value")
                
                yield Label("Total PRs:", classes="team-metric-label")
                yield Label(str(self.team_stats.total_prs), classes="team-metric-value")
                
                yield Label("PR Velocity:", classes="team-metric-label")
                yield Label(f"{self.team_stats.pr_velocity:.1f}/day", classes="team-metric-value")
                
                yield Label("Review Coverage:", classes="team-metric-label")
                yield Label(f"{self.team_stats.review_coverage:.0f}%", classes="team-metric-value")
                
                yield Label("CI Success Rate:", classes="team-metric-label")
                yield Label(f"{self.team_stats.overall_ci_success_rate:.0f}%", classes="team-metric-value")
                
                yield Label("Avg Cycle Time:", classes="team-metric-label")
                yield Label(f"{self.team_stats.avg_cycle_time:.0f}h", classes="team-metric-value")
                
            # Progress indicators
            with Container(classes="team-progress"):
                yield Label("Review Coverage")
                yield ProgressBar(progress=self.team_stats.review_coverage / 100)
                
                yield Label("CI Success Rate")
                yield ProgressBar(progress=self.team_stats.overall_ci_success_rate / 100)
                
                yield Label("Knowledge Sharing")
                yield ProgressBar(progress=self.team_stats.knowledge_sharing_score / 100)
                
            # Trend chart
            if self.team_stats.cycle_time_trend:
                yield Label("📈 Cycle Time Trend (7 days)")
                yield SparklineChart(data=self.team_stats.cycle_time_trend, height=4)


class CollaborationMatrixWidget(Container):
    """Widget showing collaboration patterns between team members."""
    
    def __init__(self, prs: List[PullRequest], **kwargs):
        super().__init__(**kwargs)
        self.prs = prs
        
    def compose(self) -> ComposeResult:
        """Compose collaboration matrix."""
        with Container(classes="collaboration-matrix"):
            yield Label("🤝 Collaboration Matrix", classes="section-title")
            
            # Build collaboration data
            collaboration_data = self._build_collaboration_data()
            
            if not collaboration_data:
                yield Label("No collaboration data available")
                return
                
            # Create table
            table = DataTable(id="collaboration-table")
            
            # Get all contributors
            contributors = sorted(set(collaboration_data.keys()))
            
            # Add columns
            table.add_column("Reviewer")
            for contributor in contributors:
                table.add_column(contributor[:8])  # Truncate names
                
            # Add rows
            for reviewer in contributors:
                row_data = [reviewer[:8]]
                for author in contributors:
                    if author in collaboration_data.get(reviewer, {}):
                        count = collaboration_data[reviewer][author]
                        row_data.append(str(count))
                    else:
                        row_data.append("0")
                table.add_row(*row_data)
                
            yield table
            
    def _build_collaboration_data(self) -> Dict[str, Dict[str, int]]:
        """Build collaboration matrix data."""
        # reviewer -> author -> count
        collaboration = defaultdict(lambda: defaultdict(int))
        
        for pr in self.prs:
            if pr.reviews:
                for review in pr.reviews:
                    reviewer = review.get('user')
                    if reviewer and reviewer != pr.author:
                        collaboration[reviewer][pr.author] += 1
                        
        return dict(collaboration)


class TopContributorsWidget(Container):
    """Widget showing top contributors by various metrics."""
    
    contributors = reactive([], recompose=True)
    sort_by = reactive("productivity")  # productivity, prs, reviews, quality
    
    def compose(self) -> ComposeResult:
        """Compose top contributors widget."""
        with Container(classes="top-contributors"):
            with Horizontal(classes="top-contributors-header"):
                yield Label("🏆 Top Contributors", classes="section-title")
                yield Select([
                    ("Productivity", "productivity"),
                    ("PRs Created", "prs"),
                    ("Reviews Given", "reviews"),
                    ("CI Success", "quality")
                ], value=self.sort_by, id="sort-select")
                
            # Sort contributors
            sorted_contributors = self._sort_contributors()
            
            # Display top 10
            for i, contributor in enumerate(sorted_contributors[:10]):
                with Horizontal(classes="contributor-row"):
                    yield Label(f"{i+1}.", classes="rank")
                    yield Label(contributor.username, classes="contributor-name")
                    
                    if self.sort_by == "productivity":
                        yield Label(f"{contributor.productivity_score:.0f}", classes="metric")
                    elif self.sort_by == "prs":
                        yield Label(str(contributor.total_prs), classes="metric")
                    elif self.sort_by == "reviews":
                        yield Label(str(contributor.reviews_given), classes="metric")
                    elif self.sort_by == "quality":
                        yield Label(f"{contributor.ci_success_rate:.0f}%", classes="metric")
                        
    def _sort_contributors(self) -> List[ContributorStats]:
        """Sort contributors by selected metric."""
        if self.sort_by == "productivity":
            return sorted(self.contributors, key=lambda c: c.productivity_score, reverse=True)
        elif self.sort_by == "prs":
            return sorted(self.contributors, key=lambda c: c.total_prs, reverse=True)
        elif self.sort_by == "reviews":
            return sorted(self.contributors, key=lambda c: c.reviews_given, reverse=True)
        elif self.sort_by == "quality":
            return sorted(self.contributors, key=lambda c: c.ci_success_rate, reverse=True)
        return self.contributors
        
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle sort selection changes."""
        if event.select.id == "sort-select":
            self.sort_by = event.value
            self.refresh(recompose=True)


class TeamDashboard(Container):
    """
    Main team performance dashboard.
    
    Provides comprehensive team analytics including individual performance,
    collaboration patterns, and team-wide metrics.
    """
    
    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("t", "toggle_timeframe", "Timeframe"),
        Binding("v", "toggle_view", "View"),
        Binding("e", "export_report", "Export"),
        Binding("f", "filter_contributors", "Filter"),
    ]
    
    prs = reactive([], recompose=True)
    timeframe_days = reactive(30)
    view_mode = reactive("overview")  # overview, contributors, collaboration
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.team_stats: Optional[TeamStats] = None
        self.contributor_stats: List[ContributorStats] = []
        
    def compose(self) -> ComposeResult:
        """Compose team dashboard."""
        with Container(id="team-dashboard-container"):
            # Header
            with Horizontal(classes="dashboard-header"):
                yield Label("👥 Team Performance Dashboard", classes="dashboard-title")
                yield Select([
                    ("Last 7 days", 7),
                    ("Last 30 days", 30),
                    ("Last 90 days", 90)
                ], value=self.timeframe_days, id="timeframe-select")
                yield Select([
                    ("Overview", "overview"),
                    ("Contributors", "contributors"),
                    ("Collaboration", "collaboration")
                ], value=self.view_mode, id="view-select")
                yield Button("🔄 Refresh", id="refresh-btn", variant="primary")
                
            # Main content
            with ScrollableContainer(id="dashboard-content"):
                if self.view_mode == "overview":
                    yield from self._compose_overview()
                elif self.view_mode == "contributors":
                    yield from self._compose_contributors_view()
                else:
                    yield from self._compose_collaboration_view()
                    
    def _compose_overview(self) -> ComposeResult:
        """Compose overview dashboard."""
        # Team overview
        team_overview = TeamOverviewWidget(id="team-overview")
        if self.team_stats:
            team_overview.team_stats = self.team_stats
        yield team_overview
        
        # Top contributors
        yield TopContributorsWidget(contributors=self.contributor_stats, id="top-contributors")
        
        # Quick stats
        if self.team_stats:
            with Horizontal(classes="quick-stats"):
                with Container(classes="stat-card"):
                    yield Label("Average PRs per Contributor", classes="stat-label")
                    yield Label(f"{self.team_stats.avg_prs_per_contributor:.1f}", classes="stat-value")
                    
                with Container(classes="stat-card"):
                    yield Label("Review Response Time", classes="stat-label")
                    yield Label(f"{self.team_stats.review_response_time:.0f}h", classes="stat-value")
                    
                with Container(classes="stat-card"):
                    yield Label("Cross-Review Rate", classes="stat-label")
                    yield Label(f"{self.team_stats.cross_review_rate:.0f}%", classes="stat-value")
                    
    def _compose_contributors_view(self) -> ComposeResult:
        """Compose contributors detail view."""
        yield Label("Individual Contributors", classes="view-title")
        
        with Grid(classes="contributors-grid"):
            for contributor in self.contributor_stats:
                yield ContributorCard(contributor)
                
    def _compose_collaboration_view(self) -> ComposeResult:
        """Compose collaboration analysis view."""
        yield Label("Team Collaboration Analysis", classes="view-title")
        
        # Collaboration matrix
        yield CollaborationMatrixWidget(self.prs)
        
        # Collaboration insights
        with Container(classes="collaboration-insights"):
            yield Label("🔍 Collaboration Insights", classes="section-title")
            
            if self.team_stats:
                yield Label(f"• {self.team_stats.cross_review_rate:.0f}% of reviews are cross-team")
                yield Label(f"• Knowledge sharing score: {self.team_stats.knowledge_sharing_score:.0f}/100")
                yield Label(f"• Average {self.team_stats.avg_reviews_per_pr:.1f} reviews per PR")
                
    def update_data(self, prs: List[PullRequest]):
        """Update dashboard with new PR data."""
        self.prs = prs
        
        # Calculate team statistics
        self.team_stats = TeamMetricsCalculator.calculate_team_stats(prs, self.timeframe_days)
        
        # Calculate individual contributor statistics
        contributors = set(pr.author for pr in prs)
        self.contributor_stats = [
            TeamMetricsCalculator.calculate_contributor_stats(prs, username, self.timeframe_days)
            for username in contributors
        ]
        
        # Trigger recompose
        self.refresh(recompose=True)
        
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle selection changes."""
        if event.select.id == "timeframe-select":
            self.timeframe_days = event.value
            self.update_data(self.prs)  # Recalculate with new timeframe
        elif event.select.id == "view-select":
            self.view_mode = event.value
            self.refresh(recompose=True)
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh-btn":
            self.post_message(self.RefreshRequested())
            
    # Action handlers
    def action_refresh(self) -> None:
        """Refresh dashboard data."""
        self.post_message(self.RefreshRequested())
        
    def action_toggle_timeframe(self) -> None:
        """Toggle timeframe."""
        timeframes = [7, 30, 90]
        current_index = timeframes.index(self.timeframe_days)
        next_index = (current_index + 1) % len(timeframes)
        self.timeframe_days = timeframes[next_index]
        
        # Update select widget
        timeframe_select = self.query_one("#timeframe-select", Select)
        timeframe_select.value = self.timeframe_days
        
    def action_toggle_view(self) -> None:
        """Toggle view mode."""
        views = ["overview", "contributors", "collaboration"]
        current_index = views.index(self.view_mode)
        next_index = (current_index + 1) % len(views)
        self.view_mode = views[next_index]
        
        # Update select widget
        view_select = self.query_one("#view-select", Select)
        view_select.value = self.view_mode
        
    def action_export_report(self) -> None:
        """Export team performance report."""
        self.post_message(self.ExportRequested())
        
    def action_filter_contributors(self) -> None:
        """Filter contributors by various criteria."""
        # TODO: Implement contributor filtering
        pass
        
    class RefreshRequested(Message):
        """Message sent when refresh is requested."""
        
    class ExportRequested(Message):
        """Message sent when export is requested."""