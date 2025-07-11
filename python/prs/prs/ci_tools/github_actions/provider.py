"""
GitHub Actions CI provider implementation.

This module implements the CIProviderInterface for GitHub Actions integration.
"""

import logging
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from prs.ci_tools.base.provider import CIProviderInterface, CIProviderError, CIProviderAuthError
from prs.ci_tools.base.models import CICheck, CIBuild, CIAggregatedMetrics
from prs.ci_tools.base.enums import CIProvider, BuildStatus
from prs.config import get_ci_platform_config

from .client import GitHubActionsClient
from .adapter import GitHubActionsAdapter


class GitHubActionsProvider(CIProviderInterface):
    """
    GitHub Actions CI provider.
    
    Provides integration with GitHub Actions workflows, runs, and jobs
    using the existing GitHub CLI authentication from PRS.
    """
    
    def __init__(self, auth_manager=None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize GitHub Actions provider.
        
        Args:
            auth_manager: Authentication manager instance
            config: Optional provider-specific configuration
        """
        # Set provider metadata before calling parent constructor
        self._provider_name = "github_actions"
        self._provider_type = CIProvider.GITHUB_ACTIONS
        self._requires_auth = True
        self._supported_features = [
            'checks', 'builds', 'pipelines', 'metrics', 'history'
        ]
        
        # Get platform configuration
        self.platform_config = get_ci_platform_config('github_actions')
        self._base_url = self.platform_config.get('base_url', 'https://api.github.com')
        
        # Call parent constructor
        super().__init__(auth_manager, config)
        
        # Initialize client and adapter
        self.client = GitHubActionsClient(auth_manager)
        self.adapter = GitHubActionsAdapter()
    
    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return self._provider_name
    
    @property
    def provider_type(self) -> CIProvider:
        """Return the provider type enum."""
        return self._provider_type
    
    @property
    def base_url(self) -> str:
        """Return the base URL for the provider API."""
        return self._base_url
    
    @property
    def requires_auth(self) -> bool:
        """Return True if provider requires authentication."""
        return self._requires_auth
    
    @property
    def supported_features(self) -> List[str]:
        """Return list of supported features."""
        return self._supported_features
    
    def validate_auth(self) -> bool:
        """
        Validate authentication credentials.
        
        Returns:
            True if authentication is valid
            
        Raises:
            CIProviderAuthError: If authentication fails
        """
        try:
            # Use GitHub CLI auth status to check authentication
            is_valid = self.client.validate_authentication()
            
            if not is_valid:
                raise CIProviderAuthError("GitHub authentication failed. Please run 'gh auth login'")
            
            self._authenticated = True
            return True
            
        except subprocess.CalledProcessError as e:
            raise CIProviderAuthError(f"GitHub authentication validation failed: {e}")
        except Exception as e:
            raise CIProviderAuthError(f"Unexpected error during authentication: {e}")
    
    def get_pr_checks(self, repo_owner: str, repo_name: str, pr_number: int) -> List[CICheck]:
        """
        Get status checks for a pull request.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            pr_number: Pull request number
            
        Returns:
            List of CI checks
            
        Raises:
            CIProviderError: If operation fails
        """
        try:
            # Get check runs for the PR
            check_runs = self.client.get_check_runs_for_pr(pr_number)
            
            # Transform to CI checks
            ci_checks = []
            for check_run in check_runs:
                ci_check = self.adapter.transform_check_run_to_ci_check(check_run)
                ci_checks.append(ci_check)
            
            return ci_checks
            
        except subprocess.CalledProcessError as e:
            raise CIProviderError(f"Failed to get PR checks: {e}")
        except Exception as e:
            raise CIProviderError(f"Unexpected error getting PR checks: {e}")
    
    def get_pr_builds(self, repo_owner: str, repo_name: str, pr_number: int) -> List[CIBuild]:
        """
        Get builds for a pull request.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            pr_number: Pull request number
            
        Returns:
            List of CI builds
            
        Raises:
            CIProviderError: If operation fails
        """
        try:
            # Get workflow runs for the PR
            workflow_runs = self.client.get_workflow_runs_for_pr(pr_number)
            
            # Get check runs for additional context
            check_runs = self.client.get_check_runs_for_pr(pr_number)
            
            # Get jobs for each workflow run
            jobs_data = {}
            for workflow_run in workflow_runs:
                run_id = str(workflow_run.get('id', ''))
                try:
                    jobs = self.client.get_workflow_run_jobs(run_id)
                    jobs_data[run_id] = jobs
                except Exception as e:
                    self.logger.warning(f"Failed to get jobs for workflow run {run_id}: {e}")
                    jobs_data[run_id] = []
            
            # Transform to CI build
            if workflow_runs or check_runs:
                ci_build = self.adapter.transform_pr_data_to_ci_build(
                    pr_number, workflow_runs, check_runs, jobs_data
                )
                return [ci_build]
            
            return []
            
        except subprocess.CalledProcessError as e:
            raise CIProviderError(f"Failed to get PR builds: {e}")
        except Exception as e:
            raise CIProviderError(f"Unexpected error getting PR builds: {e}")
    
    def get_build_details(self, build_id: str) -> Optional[CIBuild]:
        """
        Get detailed information for a specific build.
        
        Args:
            build_id: Build identifier (workflow run ID)
            
        Returns:
            Build details or None if not found
            
        Raises:
            CIProviderError: If operation fails
        """
        try:
            # Get workflow run details
            workflow_run = self.client.get_workflow_run_details(build_id)
            
            if not workflow_run:
                return None
            
            # Get jobs for the workflow run
            jobs = self.client.get_workflow_run_jobs(build_id)
            
            # Transform to CI pipeline
            pipeline = self.adapter.transform_workflow_run_to_ci_pipeline(workflow_run, jobs)
            
            # Create CI build with the pipeline
            ci_build = CIBuild(
                id=build_id,
                provider=CIProvider.GITHUB_ACTIONS,
                status=pipeline.status,
                url=workflow_run.get('html_url'),
                commit_sha=workflow_run.get('head_sha'),
                branch=workflow_run.get('head_branch'),
                message=workflow_run.get('display_title'),
                author=workflow_run.get('actor', {}).get('login'),
                started_at=pipeline.started_at,
                completed_at=pipeline.completed_at,
                duration=pipeline.duration,
                pipelines=[pipeline]
            )
            
            return ci_build
            
        except subprocess.CalledProcessError as e:
            raise CIProviderError(f"Failed to get build details: {e}")
        except Exception as e:
            raise CIProviderError(f"Unexpected error getting build details: {e}")
    
    def get_build_history(self, repo_owner: str, repo_name: str, 
                         limit: int = 50, branch: Optional[str] = None) -> List[CIBuild]:
        """
        Get build history for a repository.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            limit: Maximum number of builds to return
            branch: Optional branch filter
            
        Returns:
            List of builds
            
        Raises:
            CIProviderError: If operation fails
        """
        try:
            # Get workflow runs
            workflow_runs = self.client.get_workflow_runs(
                workflow_id=None,
                branch=branch,
                limit=limit
            )
            
            ci_builds = []
            for workflow_run in workflow_runs:
                run_id = str(workflow_run.get('id', ''))
                
                # Get jobs for the workflow run
                try:
                    jobs = self.client.get_workflow_run_jobs(run_id)
                except Exception as e:
                    self.logger.warning(f"Failed to get jobs for workflow run {run_id}: {e}")
                    jobs = []
                
                # Transform to CI pipeline
                pipeline = self.adapter.transform_workflow_run_to_ci_pipeline(workflow_run, jobs)
                
                # Create CI build
                ci_build = CIBuild(
                    id=run_id,
                    number=workflow_run.get('run_number'),
                    provider=CIProvider.GITHUB_ACTIONS,
                    status=pipeline.status,
                    url=workflow_run.get('html_url'),
                    commit_sha=workflow_run.get('head_sha'),
                    branch=workflow_run.get('head_branch'),
                    message=workflow_run.get('display_title'),
                    author=workflow_run.get('actor', {}).get('login'),
                    started_at=pipeline.started_at,
                    completed_at=pipeline.completed_at,
                    duration=pipeline.duration,
                    pipelines=[pipeline]
                )
                
                ci_builds.append(ci_build)
            
            return ci_builds
            
        except subprocess.CalledProcessError as e:
            raise CIProviderError(f"Failed to get build history: {e}")
        except Exception as e:
            raise CIProviderError(f"Unexpected error getting build history: {e}")
    
    def get_aggregated_metrics(self, repo_owner: str, repo_name: str,
                              days: int = 30) -> Optional[CIAggregatedMetrics]:
        """
        Get aggregated metrics for a repository.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            days: Number of days to analyze
            
        Returns:
            Aggregated metrics or None if not supported
            
        Raises:
            CIProviderError: If operation fails
        """
        try:
            # Get recent builds for metrics calculation
            # We need more data for proper metrics, so increase limit
            builds = self.get_build_history(repo_owner, repo_name, limit=200)
            
            # Calculate metrics using the adapter
            metrics = self.adapter.calculate_aggregated_metrics(builds, days)
            
            return metrics
            
        except Exception as e:
            raise CIProviderError(f"Failed to get aggregated metrics: {e}")
    
    def get_job_logs(self, job_id: str) -> Optional[str]:
        """
        Get logs for a specific job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job logs or None if not available
            
        Raises:
            CIProviderError: If operation fails
        """
        try:
            return self.client.get_job_logs(job_id)
            
        except subprocess.CalledProcessError as e:
            raise CIProviderError(f"Failed to get job logs: {e}")
        except Exception as e:
            raise CIProviderError(f"Unexpected error getting job logs: {e}")
    
    def get_artifacts(self, build_id: str) -> List[str]:
        """
        Get artifacts for a build.
        
        Args:
            build_id: Build identifier (workflow run ID)
            
        Returns:
            List of artifact names
            
        Raises:
            CIProviderError: If operation fails
        """
        try:
            artifacts = self.client.get_workflow_run_artifacts(build_id)
            return [artifact.get('name', '') for artifact in artifacts]
            
        except subprocess.CalledProcessError as e:
            raise CIProviderError(f"Failed to get artifacts: {e}")
        except Exception as e:
            raise CIProviderError(f"Unexpected error getting artifacts: {e}")
    
    def get_real_time_status(self, repo_owner: str, repo_name: str, 
                           pr_number: int) -> Dict[str, Any]:
        """
        Get real-time status updates for a pull request.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            pr_number: Pull request number
            
        Returns:
            Real-time status information
            
        Raises:
            CIProviderError: If operation fails
        """
        try:
            # Get current workflow runs
            workflow_runs = self.client.get_workflow_runs_for_pr(pr_number)
            
            # Get check runs
            check_runs = self.client.get_check_runs_for_pr(pr_number)
            
            # Calculate status summary
            running_workflows = [run for run in workflow_runs if run.get('status') == 'in_progress']
            queued_workflows = [run for run in workflow_runs if run.get('status') == 'queued']
            completed_workflows = [run for run in workflow_runs if run.get('status') == 'completed']
            
            failed_workflows = [
                run for run in completed_workflows 
                if run.get('conclusion') == 'failure'
            ]
            
            return {
                'last_updated': datetime.now().isoformat(),
                'total_workflows': len(workflow_runs),
                'running_workflows': len(running_workflows),
                'queued_workflows': len(queued_workflows),
                'completed_workflows': len(completed_workflows),
                'failed_workflows': len(failed_workflows),
                'total_checks': len(check_runs),
                'workflow_runs': workflow_runs,
                'check_runs': check_runs
            }
            
        except subprocess.CalledProcessError as e:
            raise CIProviderError(f"Failed to get real-time status: {e}")
        except Exception as e:
            raise CIProviderError(f"Unexpected error getting real-time status: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the provider.
        
        Returns:
            Health check results
        """
        try:
            # Check GitHub CLI authentication
            auth_valid = self.client.validate_authentication()
            
            if not auth_valid:
                return {
                    'provider': self.provider_name,
                    'status': 'unhealthy',
                    'last_check': datetime.now().isoformat(),
                    'message': 'GitHub authentication failed',
                    'details': {
                        'auth_status': 'invalid',
                        'cli_available': True
                    }
                }
            
            # Check rate limit status
            try:
                rate_limit = self.client.get_rate_limit_status()
                rate_limit_info = {
                    'remaining': rate_limit.get('rate', {}).get('remaining'),
                    'limit': rate_limit.get('rate', {}).get('limit'),
                    'reset': rate_limit.get('rate', {}).get('reset')
                }
            except Exception:
                rate_limit_info = {'error': 'Failed to get rate limit info'}
            
            return {
                'provider': self.provider_name,
                'status': 'healthy',
                'last_check': datetime.now().isoformat(),
                'message': 'All systems operational',
                'details': {
                    'auth_status': 'valid',
                    'cli_available': True,
                    'rate_limit': rate_limit_info,
                    'base_url': self.base_url,
                    'supported_features': self.supported_features
                }
            }
            
        except Exception as e:
            return {
                'provider': self.provider_name,
                'status': 'unhealthy',
                'last_check': datetime.now().isoformat(),
                'message': f'Health check failed: {str(e)}',
                'details': {
                    'error': str(e),
                    'auth_status': 'unknown'
                }
            }