"""
GitHub Actions CI Provider for PRS.

This module implements the GitHub Actions CI provider integration.
"""

import json
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime
import re

from .base import BaseCIProvider, CIData, CIWorkflow, CIJob
from prs.config import (
    is_github_actions_enabled, get_workflow_display_limit, get_job_display_limit,
    should_show_runner_info, should_show_workflow_files, should_show_artifacts
)


class GitHubActionsProvider(BaseCIProvider):
    """GitHub Actions CI provider implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.token = config.get('env_token')
        self.base_url = config.get('base_url', 'https://api.github.com')
        
    def is_available(self) -> bool:
        """Check if GitHub Actions is available."""
        return is_github_actions_enabled() and bool(self.token) and self._check_gh_cli()
    
    def _check_gh_cli(self) -> bool:
        """Check if GitHub CLI is available and authenticated."""
        try:
            result = subprocess.run(
                ['gh', 'auth', 'status'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_ci_data(self, repository: str, pr_number: int) -> Optional[CIData]:
        """Get GitHub Actions workflow data for a PR."""
        try:
            workflows = self._get_workflow_runs(repository, pr_number)
            if not workflows:
                return None
                
            # Calculate statistics
            total_workflows = len(workflows)
            successful_workflows = sum(1 for w in workflows if w.conclusion == "success")
            failed_workflows = sum(1 for w in workflows if w.conclusion == "failure")
            pending_workflows = sum(1 for w in workflows if w.status in ["queued", "in_progress"])
            
            return CIData(
                workflows=workflows,
                total_workflows=total_workflows,
                successful_workflows=successful_workflows,
                failed_workflows=failed_workflows,
                pending_workflows=pending_workflows,
                last_updated=datetime.now().isoformat()
            )
        except Exception as e:
            # Graceful degradation - return None if we can't get data
            return None
    
    def _get_workflow_runs(self, repository: str, pr_number: int) -> List[CIWorkflow]:
        """Get workflow runs for a specific PR."""
        try:
            # Get workflow runs for the PR
            cmd = [
                'gh', 'api', 
                f'/repos/{repository}/actions/runs',
                '--jq', '.workflow_runs[]',
                '--method', 'GET',
                '-F', f'event=pull_request',
                '-F', f'per_page=20'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return []
                
            workflows = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        workflow_data = json.loads(line)
                        
                        # Check if this workflow run is for our PR
                        if self._is_workflow_for_pr(workflow_data, pr_number):
                            workflow = self._parse_workflow_data(workflow_data)
                            if workflow:
                                # Get jobs for this workflow
                                jobs = self._get_workflow_jobs(repository, workflow.id)
                                workflow.jobs = jobs
                                workflows.append(workflow)
                    except json.JSONDecodeError:
                        continue
            
            return workflows
            
        except Exception as e:
            return []
    
    def _is_workflow_for_pr(self, workflow_data: Dict, pr_number: int) -> bool:
        """Check if a workflow run is associated with the given PR."""
        # Check pull requests array
        pull_requests = workflow_data.get('pull_requests', [])
        for pr in pull_requests:
            if pr.get('number') == pr_number:
                return True
        
        # Check head branch and commit message for PR references
        head_branch = workflow_data.get('head_branch', '')
        head_commit = workflow_data.get('head_commit', {})
        commit_message = head_commit.get('message', '')
        
        # Look for PR references in commit message
        pr_pattern = rf'#\b{pr_number}\b'
        if re.search(pr_pattern, commit_message):
            return True
            
        return False
    
    def _parse_workflow_data(self, data: Dict) -> Optional[CIWorkflow]:
        """Parse GitHub Actions workflow data into CIWorkflow object."""
        try:
            # Calculate duration
            duration = None
            if data.get('created_at') and data.get('updated_at'):
                created = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
                updated = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
                duration = int((updated - created).total_seconds())
            
            # Extract workflow file path
            workflow_file = None
            workflow_url = data.get('workflow_url', '')
            if workflow_url:
                # Extract workflow file from URL
                match = re.search(r'/workflows/([^/]+)$', workflow_url)
                if match:
                    workflow_file = f'.github/workflows/{match.group(1)}'
            
            return CIWorkflow(
                id=str(data.get('id', '')),
                name=data.get('name', 'Unknown Workflow'),
                status=data.get('status', 'unknown'),
                conclusion=data.get('conclusion', 'unknown'),
                event=data.get('event', 'unknown'),
                branch=data.get('head_branch', ''),
                commit_sha=data.get('head_sha', ''),
                started_at=data.get('created_at'),
                completed_at=data.get('updated_at'),
                duration=duration,
                html_url=data.get('html_url'),
                run_number=data.get('run_number'),
                attempt=data.get('run_attempt', 1),
                workflow_file=workflow_file,
                runner_group=data.get('runner_group_name'),
                artifacts_count=data.get('artifacts_url', '').count('artifacts') if data.get('artifacts_url') else 0
            )
        except Exception as e:
            return None
    
    def _get_workflow_jobs(self, repository: str, workflow_id: str) -> List[CIJob]:
        """Get jobs for a specific workflow run."""
        try:
            cmd = [
                'gh', 'api', 
                f'/repos/{repository}/actions/runs/{workflow_id}/jobs',
                '--jq', '.jobs[]'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            
            if result.returncode != 0:
                return []
                
            jobs = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        job_data = json.loads(line)
                        job = self._parse_job_data(job_data)
                        if job:
                            jobs.append(job)
                    except json.JSONDecodeError:
                        continue
            
            return jobs
            
        except Exception as e:
            return []
    
    def _parse_job_data(self, data: Dict) -> Optional[CIJob]:
        """Parse GitHub Actions job data into CIJob object."""
        try:
            # Calculate duration
            duration = None
            if data.get('started_at') and data.get('completed_at'):
                started = datetime.fromisoformat(data['started_at'].replace('Z', '+00:00'))
                completed = datetime.fromisoformat(data['completed_at'].replace('Z', '+00:00'))
                duration = int((completed - started).total_seconds())
            
            # Extract runner information
            runner = None
            runner_name = data.get('runner_name', '')
            if runner_name:
                # Extract runner type (ubuntu-latest, windows-latest, etc.)
                runner_match = re.search(r'(ubuntu|windows|macos)-\w+', runner_name, re.IGNORECASE)
                if runner_match:
                    runner = runner_match.group(0).lower()
                else:
                    runner = runner_name[:20]  # Truncate long runner names
            
            return CIJob(
                name=data.get('name', 'Unknown Job'),
                status=data.get('status', 'unknown'),
                conclusion=data.get('conclusion', 'unknown'),
                started_at=data.get('started_at'),
                completed_at=data.get('completed_at'),
                duration=duration,
                logs_url=data.get('html_url'),
                runner=runner
            )
        except Exception as e:
            return None
    
    def get_workflow_logs(self, repository: str, workflow_id: str) -> Optional[str]:
        """Get logs for a specific workflow run."""
        try:
            cmd = [
                'gh', 'api', 
                f'/repos/{repository}/actions/runs/{workflow_id}/logs',
                '--method', 'GET'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return result.stdout
            else:
                return None
                
        except Exception as e:
            return None
    
    def get_display_name(self) -> str:
        """Get display name for GitHub Actions."""
        return "GitHub Actions"
    
    def get_workflow_summary(self, workflows: List[CIWorkflow]) -> Dict[str, Any]:
        """Get a summary of workflow statuses for display."""
        if not workflows:
            return {
                'text': 'No workflows',
                'color': 'gray-2',
                'emoji': '○'
            }
        
        # Count statuses
        success_count = sum(1 for w in workflows if w.conclusion == "success")
        failure_count = sum(1 for w in workflows if w.conclusion == "failure")
        pending_count = sum(1 for w in workflows if w.status in ["queued", "in_progress"])
        total_count = len(workflows)
        
        # Determine overall status
        if failure_count > 0:
            return {
                'text': f'{failure_count} failed',
                'color': 'red',
                'emoji': '❌'
            }
        elif pending_count > 0:
            return {
                'text': f'{pending_count} pending',
                'color': 'yellow',
                'emoji': '🟡'
            }
        elif success_count == total_count:
            return {
                'text': f'{success_count} passed',
                'color': 'green',
                'emoji': '✅'
            }
        else:
            return {
                'text': f'{success_count}/{total_count}',
                'color': 'cyan',
                'emoji': '◐'
            }
    
    def get_workflow_details(self, workflows: List[CIWorkflow], verbosity: str = "normal") -> str:
        """Get detailed workflow information for display."""
        if not workflows:
            return "No GitHub Actions workflows found"
        
        workflow_limit = get_workflow_display_limit()
        job_limit = get_job_display_limit()
        
        if verbosity == "short":
            summary = self.get_workflow_summary(workflows)
            return f"{summary['emoji']} {summary['text']}"
        
        elif verbosity == "normal":
            lines = []
            display_workflows = workflows[:workflow_limit]
            
            for workflow in display_workflows:
                emoji = self.get_status_emoji(workflow.status, workflow.conclusion)
                duration_str = self.format_duration(workflow.duration)
                lines.append(f"{emoji} {workflow.name} ({duration_str})")
            
            if len(workflows) > workflow_limit:
                lines.append(f"... and {len(workflows) - workflow_limit} more")
            
            return "\n".join(lines)
        
        elif verbosity == "long":
            lines = []
            display_workflows = workflows[:workflow_limit]
            
            for workflow in display_workflows:
                emoji = self.get_status_emoji(workflow.status, workflow.conclusion)
                duration_str = self.format_duration(workflow.duration)
                
                # Workflow header
                lines.append(f"{emoji} {workflow.name} (Run #{workflow.run_number})")
                lines.append(f"   Status: {workflow.status}/{workflow.conclusion}")
                lines.append(f"   Duration: {duration_str}")
                lines.append(f"   Event: {workflow.event}")
                
                if should_show_workflow_files() and workflow.workflow_file:
                    lines.append(f"   File: {workflow.workflow_file}")
                
                if should_show_artifacts() and workflow.artifacts_count:
                    lines.append(f"   Artifacts: {workflow.artifacts_count}")
                
                # Show jobs
                if workflow.jobs:
                    lines.append("   Jobs:")
                    display_jobs = workflow.jobs[:job_limit]
                    
                    for job in display_jobs:
                        job_emoji = self.get_status_emoji(job.status, job.conclusion)
                        job_duration = self.format_duration(job.duration)
                        
                        runner_info = ""
                        if should_show_runner_info() and job.runner:
                            runner_info = f" ({job.runner})"
                        
                        lines.append(f"     {job_emoji} {job.name}{runner_info} - {job_duration}")
                    
                    if len(workflow.jobs) > job_limit:
                        lines.append(f"     ... and {len(workflow.jobs) - job_limit} more jobs")
                
                lines.append("")  # Empty line between workflows
            
            if len(workflows) > workflow_limit:
                lines.append(f"... and {len(workflows) - workflow_limit} more workflows")
            
            return "\n".join(lines)
        
        else:
            return ""