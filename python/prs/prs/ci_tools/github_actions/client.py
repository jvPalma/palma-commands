"""
GitHub Actions API client for CI/CD integration.

This module provides low-level API access to GitHub Actions workflows, runs, and jobs.
"""

import json
import subprocess
import logging
from typing import Dict, List, Optional, Any

from prs.config import get, get_ci_platform_config
from prs.core.helpers import resolve_owner


class GitHubActionsClient:
    """
    Client for interacting with GitHub Actions API.
    
    Uses the existing GitHub CLI (gh) for authentication and API calls,
    leveraging the same authentication mechanism as the main PRS tool.
    """
    
    def __init__(self, auth_manager=None):
        """
        Initialize GitHub Actions client.
        
        Args:
            auth_manager: Authentication manager instance (optional)
        """
        self.auth_manager = auth_manager
        self.logger = logging.getLogger("prs.ci_tools.github_actions.client")
        
        # Get configuration
        self.config = get_ci_platform_config('github_actions')
        self.base_url = self.config.get('base_url', 'https://api.github.com')
        
        # Repository info - handle gracefully if not configured
        try:
            self.repo_owner = resolve_owner()
            self.repo_name = get("git", "repo_name")
        except Exception as e:
            self.logger.warning(f"Failed to resolve repository info: {e}")
            self.repo_owner = None
            self.repo_name = None
    
    def _run_gh_command(self, args: List[str]) -> Dict[str, Any]:
        """
        Execute a GitHub CLI command and return parsed JSON response.
        
        Args:
            args: Command arguments for gh CLI
            
        Returns:
            Parsed JSON response
            
        Raises:
            subprocess.CalledProcessError: If command fails
        """
        try:
            output = subprocess.check_output(args, text=True, stderr=subprocess.PIPE)
            if output.strip():
                return json.loads(output)
            return {}
        except subprocess.CalledProcessError as e:
            self.logger.error(f"GitHub CLI command failed: {' '.join(args)}")
            self.logger.error(f"Error: {e.stderr}")
            raise
    
    def get_pr_details(self, pr_number: int) -> Dict[str, Any]:
        """
        Get pull request details including commit SHA.
        
        Args:
            pr_number: Pull request number
            
        Returns:
            PR details with commit information
        """
        if not self.repo_owner or not self.repo_name:
            raise ValueError("Repository owner and name must be configured")
        
        args = [
            "gh", "pr", "view", str(pr_number),
            "--repo", f"{self.repo_owner}/{self.repo_name}",
            "--json", "number,title,headRefName,headRepository,commits"
        ]
        
        return self._run_gh_command(args)
    
    def get_workflow_runs_for_pr(self, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get workflow runs for a specific pull request.
        
        Args:
            pr_number: Pull request number
            
        Returns:
            List of workflow runs
        """
        if not self.repo_owner or not self.repo_name:
            raise ValueError("Repository owner and name must be configured")
        
        # First get PR details to get the head commit SHA
        pr_details = self.get_pr_details(pr_number)
        
        if not pr_details.get('commits'):
            return []
        
        # Get the latest commit SHA
        latest_commit = pr_details['commits'][-1]['oid']
        
        # Get workflow runs for the commit
        args = [
            "gh", "api", f"repos/{self.repo_owner}/{self.repo_name}/actions/runs",
            "--jq", ".workflow_runs[] | select(.head_sha == \"" + latest_commit + "\")"
        ]
        
        try:
            output = subprocess.check_output(args, text=True, stderr=subprocess.PIPE)
            if not output.strip():
                return []
            
            # Parse each line as separate JSON object
            runs = []
            for line in output.strip().split('\n'):
                if line.strip():
                    runs.append(json.loads(line))
            
            return runs
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get workflow runs for PR {pr_number}: {e}")
            return []
    
    def get_workflow_run_details(self, run_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a workflow run.
        
        Args:
            run_id: Workflow run ID
            
        Returns:
            Workflow run details
        """
        if not self.repo_owner or not self.repo_name:
            raise ValueError("Repository owner and name must be configured")
        
        args = [
            "gh", "api", f"repos/{self.repo_owner}/{self.repo_name}/actions/runs/{run_id}"
        ]
        
        return self._run_gh_command(args)
    
    def get_workflow_run_jobs(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Get jobs for a workflow run.
        
        Args:
            run_id: Workflow run ID
            
        Returns:
            List of jobs
        """
        if not self.repo_owner or not self.repo_name:
            raise ValueError("Repository owner and name must be configured")
        
        args = [
            "gh", "api", f"repos/{self.repo_owner}/{self.repo_name}/actions/runs/{run_id}/jobs"
        ]
        
        result = self._run_gh_command(args)
        return result.get('jobs', [])
    
    def get_job_logs(self, job_id: str) -> Optional[str]:
        """
        Get logs for a specific job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job logs or None if not available
        """
        if not self.repo_owner or not self.repo_name:
            raise ValueError("Repository owner and name must be configured")
        
        args = [
            "gh", "api", f"repos/{self.repo_owner}/{self.repo_name}/actions/jobs/{job_id}/logs"
        ]
        
        try:
            output = subprocess.check_output(args, text=True, stderr=subprocess.PIPE)
            return output
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to get logs for job {job_id}: {e}")
            return None
    
    def get_workflow_run_artifacts(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Get artifacts for a workflow run.
        
        Args:
            run_id: Workflow run ID
            
        Returns:
            List of artifacts
        """
        if not self.repo_owner or not self.repo_name:
            raise ValueError("Repository owner and name must be configured")
        
        args = [
            "gh", "api", f"repos/{self.repo_owner}/{self.repo_name}/actions/runs/{run_id}/artifacts"
        ]
        
        result = self._run_gh_command(args)
        return result.get('artifacts', [])
    
    def get_check_runs_for_pr(self, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get check runs for a pull request.
        
        Args:
            pr_number: Pull request number
            
        Returns:
            List of check runs
        """
        if not self.repo_owner or not self.repo_name:
            raise ValueError("Repository owner and name must be configured")
        
        # Get PR details first
        pr_details = self.get_pr_details(pr_number)
        
        if not pr_details.get('commits'):
            return []
        
        # Get the latest commit SHA
        latest_commit = pr_details['commits'][-1]['oid']
        
        # Get check runs for the commit
        args = [
            "gh", "api", f"repos/{self.repo_owner}/{self.repo_name}/commits/{latest_commit}/check-runs"
        ]
        
        result = self._run_gh_command(args)
        return result.get('check_runs', [])
    
    def get_repository_workflows(self) -> List[Dict[str, Any]]:
        """
        Get all workflows in the repository.
        
        Returns:
            List of workflows
        """
        if not self.repo_owner or not self.repo_name:
            raise ValueError("Repository owner and name must be configured")
        
        args = [
            "gh", "api", f"repos/{self.repo_owner}/{self.repo_name}/actions/workflows"
        ]
        
        result = self._run_gh_command(args)
        return result.get('workflows', [])
    
    def get_workflow_runs(self, workflow_id: Optional[str] = None, 
                         branch: Optional[str] = None, 
                         limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get workflow runs for repository.
        
        Args:
            workflow_id: Optional workflow ID filter
            branch: Optional branch filter
            limit: Maximum number of runs to return
            
        Returns:
            List of workflow runs
        """
        if not self.repo_owner or not self.repo_name:
            raise ValueError("Repository owner and name must be configured")
        
        endpoint = f"repos/{self.repo_owner}/{self.repo_name}/actions/runs"
        
        # Build query parameters
        params = [f"per_page={limit}"]
        
        if workflow_id:
            # Get runs for specific workflow
            endpoint = f"repos/{self.repo_owner}/{self.repo_name}/actions/workflows/{workflow_id}/runs"
        
        if branch:
            params.append(f"branch={branch}")
        
        # Construct API call
        args = ["gh", "api", endpoint]
        
        if params:
            args.extend(["-F", "&".join(params)])
        
        result = self._run_gh_command(args)
        return result.get('workflow_runs', [])
    
    def validate_authentication(self) -> bool:
        """
        Validate GitHub authentication.
        
        Returns:
            True if authentication is valid
        """
        try:
            args = ["gh", "auth", "status"]
            subprocess.check_output(args, text=True, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get API rate limit status.
        
        Returns:
            Rate limit information
        """
        args = ["gh", "api", "rate_limit"]
        return self._run_gh_command(args)