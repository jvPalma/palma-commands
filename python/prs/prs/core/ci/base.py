"""
Base CI Provider interface for PRS.

This module defines the base interface that all CI providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class CIJob:
    """Represents a CI job/step within a workflow."""
    name: str
    status: str  # queued, in_progress, completed
    conclusion: str  # success, failure, cancelled, skipped, neutral
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration: Optional[int] = None  # in seconds
    logs_url: Optional[str] = None
    runner: Optional[str] = None  # e.g., ubuntu-latest, windows-latest


@dataclass
class CIWorkflow:
    """Represents a CI workflow run."""
    id: str
    name: str
    status: str  # queued, in_progress, completed
    conclusion: str  # success, failure, cancelled, skipped, neutral
    event: str  # push, pull_request, workflow_dispatch, etc.
    branch: str
    commit_sha: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration: Optional[int] = None  # in seconds
    html_url: Optional[str] = None
    run_number: Optional[int] = None
    attempt: Optional[int] = None
    jobs: List[CIJob] = None
    workflow_file: Optional[str] = None  # .github/workflows/ci.yml
    runner_group: Optional[str] = None
    artifacts_count: Optional[int] = None
    
    def __post_init__(self):
        if self.jobs is None:
            self.jobs = []


@dataclass
class CIData:
    """Aggregated CI data for a pull request."""
    workflows: List[CIWorkflow]
    total_workflows: int
    successful_workflows: int
    failed_workflows: int
    pending_workflows: int
    last_updated: Optional[str] = None
    
    def __post_init__(self):
        if not self.workflows:
            self.workflows = []


class BaseCIProvider(ABC):
    """Base class for CI providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the CI provider with configuration."""
        self.config = config
        self.name = self.__class__.__name__
        
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the CI provider is available and properly configured."""
        pass
    
    @abstractmethod
    def get_ci_data(self, repository: str, pr_number: int) -> Optional[CIData]:
        """
        Get CI data for a specific pull request.
        
        Args:
            repository: Repository name in format "owner/repo"
            pr_number: Pull request number
            
        Returns:
            CIData object or None if no data available
        """
        pass
    
    @abstractmethod
    def get_workflow_logs(self, repository: str, workflow_id: str) -> Optional[str]:
        """
        Get logs for a specific workflow.
        
        Args:
            repository: Repository name in format "owner/repo"
            workflow_id: Workflow run ID
            
        Returns:
            Log content or None if not available
        """
        pass
    
    def get_display_name(self) -> str:
        """Get the display name for this CI provider."""
        return self.name.replace('Provider', '').replace('CI', '').strip()
    
    def get_status_emoji(self, status: str, conclusion: str) -> str:
        """Get emoji representation for workflow/job status."""
        if status == "completed":
            if conclusion == "success":
                return "✅"
            elif conclusion == "failure":
                return "❌"
            elif conclusion == "cancelled":
                return "🚫"
            elif conclusion == "skipped":
                return "⏩"
            else:
                return "⚪"
        elif status == "in_progress":
            return "🟡"
        elif status == "queued":
            return "⏳"
        else:
            return "❓"
    
    def get_status_color(self, status: str, conclusion: str) -> str:
        """Get color representation for workflow/job status."""
        if status == "completed":
            if conclusion == "success":
                return "green"
            elif conclusion == "failure":
                return "red"
            elif conclusion == "cancelled":
                return "gray-2"
            elif conclusion == "skipped":
                return "gray-3"
            else:
                return "gray-1"
        elif status == "in_progress":
            return "yellow"
        elif status == "queued":
            return "cyan"
        else:
            return "gray-0"
    
    def format_duration(self, duration: Optional[int]) -> str:
        """Format duration in seconds to human-readable format."""
        if not duration:
            return "N/A"
        
        if duration < 60:
            return f"{duration}s"
        elif duration < 3600:
            minutes = duration // 60
            seconds = duration % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            return f"{hours}h {minutes}m"