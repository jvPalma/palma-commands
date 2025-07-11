"""
CI Status Widget for the TUI application.

Provides detailed CI/CD status information with workflow runs, jobs,
and status indicators. Supports viewing logs and artifacts via links.
"""

from typing import List, Dict, Any, Optional, Callable
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich.align import Align
from datetime import datetime, timedelta
import re

from ..models.tui_models import TUIState, PRListItem
from ...core.models import PullRequest


class CIStatusWidget:
    """CI/CD status widget with detailed workflow information."""
    
    def __init__(self, tui_state: TUIState, console: Console):
        self.tui_state = tui_state
        self.console = console
        self.expanded_workflows: set = set()
        self.selected_workflow_index = 0
        
        # Callbacks
        self.on_log_request: Optional[Callable[[str], None]] = None
        self.on_artifact_request: Optional[Callable[[str], None]] = None
        
    def handle_key(self, key: str) -> bool:
        """
        Handle keyboard input for workflow navigation.
        Returns True if key was handled.
        """
        pr = self.tui_state.get_selected_pr()
        if not pr or not pr.checks:
            return False
        
        workflows = self._group_checks_by_workflow(pr.checks)
        workflow_names = list(workflows.keys())
        
        if key == "up" or key == "k":
            self.selected_workflow_index = max(0, self.selected_workflow_index - 1)
        elif key == "down" or key == "j":
            self.selected_workflow_index = min(len(workflow_names) - 1, 
                                             self.selected_workflow_index + 1)
        elif key == "enter" or key == "space":
            if 0 <= self.selected_workflow_index < len(workflow_names):
                workflow_name = workflow_names[self.selected_workflow_index]
                self.toggle_workflow_expansion(workflow_name)
        elif key == "l":
            # Request logs for selected workflow
            if (0 <= self.selected_workflow_index < len(workflow_names) and 
                self.on_log_request):
                workflow_name = workflow_names[self.selected_workflow_index]
                workflows = self._group_checks_by_workflow(pr.checks)
                first_check = workflows[workflow_name][0]
                if first_check.get('details_url'):
                    self.on_log_request(first_check['details_url'])
        elif key == "a":
            # Request artifacts for selected workflow
            if (0 <= self.selected_workflow_index < len(workflow_names) and 
                self.on_artifact_request):
                workflow_name = workflow_names[self.selected_workflow_index]
                workflows = self._group_checks_by_workflow(pr.checks)
                first_check = workflows[workflow_name][0]
                if first_check.get('details_url'):
                    self.on_artifact_request(first_check['details_url'])
        else:
            return False
        
        return True
    
    def toggle_workflow_expansion(self, workflow_name: str):
        """Toggle expansion of a workflow."""
        if workflow_name in self.expanded_workflows:
            self.expanded_workflows.remove(workflow_name)
        else:
            self.expanded_workflows.add(workflow_name)
    
    def render(self) -> Panel:
        """Render the CI status widget."""
        pr = self.tui_state.get_selected_pr()
        if not pr:
            return self._render_empty_state()
        
        if not pr.checks:
            return self._render_no_checks_state()
        
        # Get PR item for health info
        pr_item = None
        for item in self.tui_state.pr_items:
            if item.pr.id == pr.id:
                pr_item = item
                break
        
        content_parts = []
        
        # Overall status summary
        summary = self._create_status_summary(pr, pr_item)
        content_parts.append(summary)
        
        # Workflow details
        workflows_content = self._create_workflows_content(pr)
        content_parts.append(workflows_content)
        
        # Controls hint
        controls = Text("↑↓:nav enter:expand l:logs a:artifacts", style="dim")
        content_parts.append(controls)
        
        content = Group(*content_parts)
        
        return Panel(
            content,
            title="CI/CD Status",
            title_align="left",
            border_style="blue"
        )
    
    def _render_empty_state(self) -> Panel:
        """Render empty state when no PR is selected."""
        content = Align.center(
            Text("No pull request selected\nSelect a PR to view CI/CD status", 
                 style="dim italic")
        )
        return Panel(content, title="CI/CD Status", border_style="dim")
    
    def _render_no_checks_state(self) -> Panel:
        """Render state when PR has no checks."""
        content = Align.center(
            Text("No CI/CD checks found for this pull request", 
                 style="dim italic")
        )
        return Panel(content, title="CI/CD Status", border_style="yellow")
    
    def _create_status_summary(self, pr: PullRequest, pr_item: Optional[PRListItem]) -> Panel:
        """Create overall status summary."""
        summary_parts = []
        
        if pr_item:
            health = pr_item.health
            
            # Status overview
            status_text = Text()
            status_text.append("Overall Status: ")
            status_text.append(health.health_dots, 
                             style=self._get_health_style(health.status))
            status_text.append(f" {health.status.value.title()}")
            summary_parts.append(status_text)
            
            # Detailed counts
            if health.checks_passing or health.checks_failing or health.checks_pending:
                counts_text = Text()
                if health.checks_passing:
                    counts_text.append(f"✓ {health.checks_passing} passing ", style="green")
                if health.checks_failing:
                    counts_text.append(f"✗ {health.checks_failing} failing ", style="red")
                if health.checks_pending:
                    counts_text.append(f"⧗ {health.checks_pending} pending", style="yellow")
                summary_parts.append(counts_text)
        
        # Total checks
        total_checks = len(pr.checks)
        summary_parts.append(Text(f"Total checks: {total_checks}"))
        
        content = Group(*summary_parts)
        return Panel(content, title="Summary", border_style="blue")
    
    def _create_workflows_content(self, pr: PullRequest) -> Group:
        """Create detailed workflows content."""
        workflows = self._group_checks_by_workflow(pr.checks)
        workflow_parts = []
        
        for i, (workflow_name, checks) in enumerate(workflows.items()):
            is_selected = i == self.selected_workflow_index
            is_expanded = workflow_name in self.expanded_workflows
            
            workflow_panel = self._create_workflow_panel(
                workflow_name, checks, is_selected, is_expanded
            )
            workflow_parts.append(workflow_panel)
        
        return Group(*workflow_parts)
    
    def _group_checks_by_workflow(self, checks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group checks by workflow name."""
        workflows = {}
        
        for check in checks:
            # Extract workflow name from check name or use check name
            workflow_name = self._extract_workflow_name(check)
            
            if workflow_name not in workflows:
                workflows[workflow_name] = []
            workflows[workflow_name].append(check)
        
        return workflows
    
    def _extract_workflow_name(self, check: Dict[str, Any]) -> str:
        """Extract workflow name from check data."""
        name = check.get('name', check.get('check_name', 'Unknown'))
        
        # Common patterns for extracting workflow names
        # GitHub Actions: "workflow_name / job_name"
        if ' / ' in name:
            return name.split(' / ')[0]
        
        # Buildkite: "pipeline_name: step_name"
        if ': ' in name:
            return name.split(': ')[0]
        
        # CircleCI: "ci/circleci: job_name"
        if name.startswith('ci/'):
            parts = name.split(': ')
            if len(parts) > 1:
                return parts[0]
        
        # Default: use full name
        return name
    
    def _create_workflow_panel(self, workflow_name: str, checks: List[Dict[str, Any]], 
                              is_selected: bool, is_expanded: bool) -> Panel:
        """Create a panel for a single workflow."""
        # Calculate workflow status
        workflow_status = self._calculate_workflow_status(checks)
        
        # Header
        header = Text()
        if is_selected:
            header.append("► ", style="bold cyan")
        else:
            header.append("  ")
        
        # Expansion indicator
        if is_expanded:
            header.append("▼ ", style="dim")
        else:
            header.append("▶ ", style="dim")
        
        # Workflow name
        header.append(workflow_name, style="bold")
        
        # Status indicator
        status_style = self._get_status_style(workflow_status)
        header.append(f" ({workflow_status})", style=status_style)
        
        # Job count
        header.append(f" [{len(checks)} jobs]", style="dim")
        
        content_parts = [header]
        
        # Expanded content
        if is_expanded:
            content_parts.append(Text(""))
            for check in checks:
                job_line = self._format_job_line(check)
                content_parts.append(job_line)
        
        content = Group(*content_parts)
        
        border_style = "bright_blue" if is_selected else "blue"
        return Panel(content, border_style=border_style)
    
    def _calculate_workflow_status(self, checks: List[Dict[str, Any]]) -> str:
        """Calculate overall status for a workflow."""
        statuses = []
        for check in checks:
            status = check.get('conclusion') or check.get('status', 'unknown')
            statuses.append(status.lower())
        
        # Priority: failure > pending > success
        if any(s in ['failure', 'failed', 'error'] for s in statuses):
            return "failed"
        elif any(s in ['pending', 'in_progress', 'queued'] for s in statuses):
            return "pending"
        elif all(s in ['success', 'passed'] for s in statuses):
            return "passed"
        else:
            return "unknown"
    
    def _format_job_line(self, check: Dict[str, Any]) -> Text:
        """Format a single job/check line."""
        text = Text("    ")  # Indentation
        
        # Status indicator
        status = check.get('conclusion') or check.get('status', 'unknown')
        status = status.lower()
        
        if status in ['success', 'passed']:
            text.append("✓ ", style="green")
        elif status in ['failure', 'failed', 'error']:
            text.append("✗ ", style="red")
        elif status in ['pending', 'in_progress', 'queued']:
            text.append("⧗ ", style="yellow")
        elif status == 'cancelled':
            text.append("⊘ ", style="dim")
        elif status == 'skipped':
            text.append("⊝ ", style="dim")
        else:
            text.append("? ", style="blue")
        
        # Job name
        job_name = self._extract_job_name(check)
        text.append(job_name)
        
        # Duration
        duration = self._calculate_duration(check)
        if duration:
            text.append(f" ({duration})", style="dim")
        
        # Links indicators
        if check.get('details_url'):
            text.append(" 🔗", style="blue")
        
        return text
    
    def _extract_job_name(self, check: Dict[str, Any]) -> str:
        """Extract job name from check data."""
        name = check.get('name', check.get('check_name', 'Unknown'))
        
        # Remove workflow prefix if present
        if ' / ' in name:
            return name.split(' / ', 1)[1]
        elif ': ' in name:
            return name.split(': ', 1)[1]
        
        return name
    
    def _calculate_duration(self, check: Dict[str, Any]) -> Optional[str]:
        """Calculate duration of a check."""
        started_at = check.get('started_at')
        completed_at = check.get('completed_at')
        
        if not started_at or not completed_at:
            return None
        
        try:
            start = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            end = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
            duration = end - start
            
            if duration.total_seconds() < 60:
                return f"{int(duration.total_seconds())}s"
            elif duration.total_seconds() < 3600:
                return f"{int(duration.total_seconds() // 60)}m"
            else:
                hours = int(duration.total_seconds() // 3600)
                minutes = int((duration.total_seconds() % 3600) // 60)
                return f"{hours}h {minutes}m"
        except Exception:
            return None
    
    def _get_status_style(self, status: str) -> str:
        """Get style for status."""
        styles = {
            "passed": "green",
            "failed": "red",
            "pending": "yellow",
            "cancelled": "dim",
            "skipped": "dim",
            "unknown": "blue"
        }
        return styles.get(status, "blue")
    
    def _get_health_style(self, health_status) -> str:
        """Get style for health status."""
        from ..models.tui_models import PRStatus
        styles = {
            PRStatus.HEALTHY: "bold green",
            PRStatus.WARNING: "bold yellow", 
            PRStatus.PENDING: "bold blue",
            PRStatus.CRITICAL: "bold red",
            PRStatus.DRAFT: "dim white"
        }
        return styles.get(health_status, "dim white")
    
    def get_workflow_stats(self, pr: PullRequest) -> Dict[str, Any]:
        """Get statistics about workflows."""
        if not pr.checks:
            return {}
        
        workflows = self._group_checks_by_workflow(pr.checks)
        stats = {
            "total_workflows": len(workflows),
            "total_jobs": len(pr.checks),
            "workflows_passed": 0,
            "workflows_failed": 0,
            "workflows_pending": 0
        }
        
        for workflow_name, checks in workflows.items():
            status = self._calculate_workflow_status(checks)
            if status == "passed":
                stats["workflows_passed"] += 1
            elif status == "failed":
                stats["workflows_failed"] += 1
            elif status == "pending":
                stats["workflows_pending"] += 1
        
        return stats
    
    def reset_selection(self):
        """Reset selection to first workflow."""
        self.selected_workflow_index = 0
    
    def expand_all_workflows(self):
        """Expand all workflows."""
        pr = self.tui_state.get_selected_pr()
        if pr and pr.checks:
            workflows = self._group_checks_by_workflow(pr.checks)
            self.expanded_workflows = set(workflows.keys())
    
    def collapse_all_workflows(self):
        """Collapse all workflows."""
        self.expanded_workflows.clear()