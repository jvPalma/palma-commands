"""
GitHub Actions data adapter for transforming API responses into unified CI models.

This adapter converts GitHub Actions API responses (both REST API and GraphQL) into
the standardized CI models defined in the base module.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import logging
from dateutil.parser import parse as parse_datetime

from prs.ci_tools.base.models import (
    CICheck, CIJob, CIPipeline, CIBuild, CIAggregatedMetrics, 
    TestResult, BuildStep
)
from prs.ci_tools.base.enums import CIProvider, BuildStatus, JobStatus, TestStatus

logger = logging.getLogger(__name__)


class GitHubActionsAdapter:
    """
    Adapter for transforming GitHub Actions API responses into unified CI models.
    
    Supports both REST API and GraphQL responses from GitHub Actions.
    """
    
    def __init__(self):
        self.provider = CIProvider.GITHUB_ACTIONS
    
    def workflow_run_to_ci_build(self, workflow_run_data: Dict[str, Any]) -> CIBuild:
        """
        Transform GitHub Actions workflow run data to CIBuild model.
        
        Args:
            workflow_run_data: GitHub Actions workflow run data from API
            
        Returns:
            CIBuild: Unified CI build model
        """
        try:
            # Extract basic information
            build_id = str(workflow_run_data.get("id", ""))
            run_number = workflow_run_data.get("run_number")
            status = self._map_workflow_status(workflow_run_data.get("status"))
            url = workflow_run_data.get("html_url")
            commit_sha = workflow_run_data.get("head_sha")
            branch = workflow_run_data.get("head_branch")
            message = workflow_run_data.get("display_title", "")
            
            # Author information
            author = None
            if "head_commit" in workflow_run_data:
                author = workflow_run_data["head_commit"].get("author", {}).get("name")
            elif "actor" in workflow_run_data:
                author = workflow_run_data["actor"].get("login")
            
            # Timing information
            created_at = self._parse_datetime(workflow_run_data.get("created_at"))
            updated_at = self._parse_datetime(workflow_run_data.get("updated_at"))
            run_started_at = self._parse_datetime(workflow_run_data.get("run_started_at"))
            
            # Calculate duration
            duration = None
            if created_at and updated_at:
                duration = (updated_at - created_at).total_seconds()
            
            # Convert to pipeline if jobs data is available
            pipelines = []
            if "jobs" in workflow_run_data:
                pipeline = self.workflow_run_to_ci_pipeline(workflow_run_data)
                pipelines.append(pipeline)
            
            # Extract checks if available
            checks = []
            if "check_runs" in workflow_run_data:
                checks = [
                    self.check_run_to_ci_check(check_run)
                    for check_run in workflow_run_data["check_runs"]
                ]
            
            # Metadata
            metadata = {
                "workflow_name": workflow_run_data.get("name", ""),
                "event": workflow_run_data.get("event", ""),
                "workflow_id": workflow_run_data.get("workflow_id"),
                "repository": workflow_run_data.get("repository", {}).get("full_name", ""),
                "run_attempt": workflow_run_data.get("run_attempt", 1),
                "cancel_url": workflow_run_data.get("cancel_url"),
                "rerun_url": workflow_run_data.get("rerun_url"),
                "previous_attempt_url": workflow_run_data.get("previous_attempt_url"),
            }
            
            return CIBuild(
                id=build_id,
                number=run_number,
                provider=self.provider,
                status=status,
                url=url,
                commit_sha=commit_sha,
                branch=branch,
                message=message,
                author=author,
                started_at=run_started_at or created_at,
                completed_at=updated_at,
                duration=duration,
                checks=checks,
                pipelines=pipelines,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error transforming workflow run to CI build: {e}")
            return self._create_error_build(workflow_run_data, str(e))
    
    def workflow_run_to_ci_pipeline(self, workflow_run_data: Dict[str, Any]) -> CIPipeline:
        """
        Transform GitHub Actions workflow run data to CIPipeline model.
        
        Args:
            workflow_run_data: GitHub Actions workflow run data from API
            
        Returns:
            CIPipeline: Unified CI pipeline model
        """
        try:
            pipeline_id = str(workflow_run_data.get("id", ""))
            name = workflow_run_data.get("name", "")
            status = self._map_workflow_status(workflow_run_data.get("status"))
            trigger = workflow_run_data.get("event", "")
            branch = workflow_run_data.get("head_branch")
            commit_sha = workflow_run_data.get("head_sha")
            
            # Timing
            started_at = self._parse_datetime(workflow_run_data.get("run_started_at"))
            completed_at = self._parse_datetime(workflow_run_data.get("updated_at"))
            
            # Calculate duration
            duration = None
            if started_at and completed_at:
                duration = (completed_at - started_at).total_seconds()
            
            # Transform jobs
            jobs = []
            if "jobs" in workflow_run_data:
                jobs = [
                    self.job_to_ci_job(job_data)
                    for job_data in workflow_run_data["jobs"]
                ]
            
            # Metadata
            metadata = {
                "workflow_id": workflow_run_data.get("workflow_id"),
                "run_number": workflow_run_data.get("run_number"),
                "run_attempt": workflow_run_data.get("run_attempt", 1),
                "repository": workflow_run_data.get("repository", {}).get("full_name", ""),
                "actor": workflow_run_data.get("actor", {}).get("login", ""),
                "conclusion": workflow_run_data.get("conclusion"),
            }
            
            return CIPipeline(
                id=pipeline_id,
                name=name,
                status=status,
                trigger=trigger,
                branch=branch,
                commit_sha=commit_sha,
                started_at=started_at,
                completed_at=completed_at,
                duration=duration,
                jobs=jobs,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error transforming workflow run to CI pipeline: {e}")
            return self._create_error_pipeline(workflow_run_data, str(e))
    
    def job_to_ci_job(self, job_data: Dict[str, Any]) -> CIJob:
        """
        Transform GitHub Actions job data to CIJob model.
        
        Args:
            job_data: GitHub Actions job data from API
            
        Returns:
            CIJob: Unified CI job model
        """
        try:
            job_id = str(job_data.get("id", ""))
            name = job_data.get("name", "")
            status = self._map_job_status(job_data.get("status"), job_data.get("conclusion"))
            
            # Timing
            started_at = self._parse_datetime(job_data.get("started_at"))
            completed_at = self._parse_datetime(job_data.get("completed_at"))
            
            # Calculate duration
            duration = None
            if started_at and completed_at:
                duration = (completed_at - started_at).total_seconds()
            
            # Runner information
            runner = None
            if "runner_name" in job_data:
                runner = job_data["runner_name"]
            elif "labels" in job_data:
                runner = ", ".join(job_data["labels"])
            
            # Environment
            environment = job_data.get("environment", {}).get("name") if job_data.get("environment") else None
            
            # Logs URL
            logs_url = job_data.get("logs_url")
            
            # Transform steps
            steps = []
            if "steps" in job_data:
                steps = [
                    self.step_to_build_step(step_data)
                    for step_data in job_data["steps"]
                ]
            
            # Extract test results from steps or logs
            test_results = self._extract_test_results_from_job(job_data)
            
            # Artifacts
            artifacts = []
            if "artifacts" in job_data:
                artifacts = [
                    artifact.get("name", "")
                    for artifact in job_data["artifacts"]
                ]
            
            # Metadata
            metadata = {
                "runner_group_name": job_data.get("runner_group_name"),
                "runner_group_id": job_data.get("runner_group_id"),
                "runner_id": job_data.get("runner_id"),
                "workflow_name": job_data.get("workflow_name"),
                "head_branch": job_data.get("head_branch"),
                "run_id": job_data.get("run_id"),
                "run_url": job_data.get("run_url"),
                "run_attempt": job_data.get("run_attempt"),
                "node_id": job_data.get("node_id"),
                "check_run_url": job_data.get("check_run_url"),
                "labels": job_data.get("labels", []),
                "conclusion": job_data.get("conclusion"),
            }
            
            return CIJob(
                id=job_id,
                name=name,
                status=status,
                started_at=started_at,
                completed_at=completed_at,
                duration=duration,
                runner=runner,
                environment=environment,
                logs_url=logs_url,
                steps=steps,
                test_results=test_results,
                artifacts=artifacts,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error transforming job to CI job: {e}")
            return self._create_error_job(job_data, str(e))
    
    def check_run_to_ci_check(self, check_run_data: Dict[str, Any]) -> CICheck:
        """
        Transform GitHub Actions check run data to CICheck model.
        
        Args:
            check_run_data: GitHub Actions check run data from API
            
        Returns:
            CICheck: Unified CI check model
        """
        try:
            name = check_run_data.get("name", "")
            status = self._map_check_status(check_run_data.get("status"), check_run_data.get("conclusion"))
            conclusion = check_run_data.get("conclusion")
            
            # Timing
            started_at = self._parse_datetime(check_run_data.get("started_at"))
            completed_at = self._parse_datetime(check_run_data.get("completed_at"))
            
            # URLs and metadata
            details_url = check_run_data.get("details_url")
            external_id = check_run_data.get("external_id")
            context = check_run_data.get("context", name)
            description = check_run_data.get("output", {}).get("summary", "")
            target_url = check_run_data.get("html_url")
            
            return CICheck(
                name=name,
                status=status,
                conclusion=conclusion,
                started_at=started_at,
                completed_at=completed_at,
                details_url=details_url,
                external_id=external_id,
                context=context,
                description=description,
                target_url=target_url
            )
            
        except Exception as e:
            logger.error(f"Error transforming check run to CI check: {e}")
            return CICheck(
                name=check_run_data.get("name", "Unknown"),
                status=BuildStatus.ERROR,
                description=f"Error processing check: {e}"
            )
    
    def step_to_build_step(self, step_data: Dict[str, Any]) -> BuildStep:
        """
        Transform GitHub Actions step data to BuildStep model.
        
        Args:
            step_data: GitHub Actions step data from API
            
        Returns:
            BuildStep: Unified build step model
        """
        try:
            name = step_data.get("name", "")
            status = self._map_step_status(step_data.get("status"), step_data.get("conclusion"))
            
            # Timing
            started_at = self._parse_datetime(step_data.get("started_at"))
            completed_at = self._parse_datetime(step_data.get("completed_at"))
            
            # Calculate duration
            duration = None
            if started_at and completed_at:
                duration = (completed_at - started_at).total_seconds()
            
            # Command and execution details
            command = step_data.get("run", {}).get("command") if step_data.get("run") else None
            exit_code = step_data.get("exit_code")
            
            # Logs (if available)
            logs = step_data.get("logs")
            
            return BuildStep(
                name=name,
                status=status,
                started_at=started_at,
                completed_at=completed_at,
                duration=duration,
                command=command,
                exit_code=exit_code,
                logs=logs
            )
            
        except Exception as e:
            logger.error(f"Error transforming step to build step: {e}")
            return BuildStep(
                name=step_data.get("name", "Unknown"),
                status=JobStatus.ERROR
            )
    
    def test_results_to_test_result(self, test_data: Dict[str, Any]) -> TestResult:
        """
        Transform test results data to TestResult model.
        
        Args:
            test_data: Test result data from various sources
            
        Returns:
            TestResult: Unified test result model
        """
        try:
            name = test_data.get("name", "")
            status = self._map_test_status(test_data.get("status", test_data.get("outcome")))
            duration = test_data.get("duration")
            message = test_data.get("message", test_data.get("failure_message"))
            file_path = test_data.get("file_path", test_data.get("file"))
            line_number = test_data.get("line_number", test_data.get("line"))
            suite_name = test_data.get("suite_name", test_data.get("classname"))
            
            return TestResult(
                name=name,
                status=status,
                duration=duration,
                message=message,
                file_path=file_path,
                line_number=line_number,
                suite_name=suite_name
            )
            
        except Exception as e:
            logger.error(f"Error transforming test result: {e}")
            return TestResult(
                name=test_data.get("name", "Unknown"),
                status=TestStatus.ERROR,
                message=f"Error processing test: {e}"
            )
    
    def _map_workflow_status(self, status: Optional[str]) -> BuildStatus:
        """Map GitHub Actions workflow status to unified BuildStatus."""
        if not status:
            return BuildStatus.UNKNOWN
        
        status_map = {
            "queued": BuildStatus.QUEUED,
            "in_progress": BuildStatus.IN_PROGRESS,
            "completed": BuildStatus.SUCCESS,  # Default for completed, refined by conclusion
            "waiting": BuildStatus.PENDING,
            "requested": BuildStatus.PENDING,
        }
        
        return status_map.get(status.lower(), BuildStatus.UNKNOWN)
    
    def _map_job_status(self, status: Optional[str], conclusion: Optional[str]) -> JobStatus:
        """Map GitHub Actions job status and conclusion to unified JobStatus."""
        if conclusion:
            conclusion_map = {
                "success": JobStatus.SUCCESS,
                "failure": JobStatus.FAILURE,
                "cancelled": JobStatus.CANCELLED,
                "skipped": JobStatus.SKIPPED,
                "timed_out": JobStatus.TIMEOUT,
                "action_required": JobStatus.PENDING,
                "neutral": JobStatus.SUCCESS,
            }
            mapped_conclusion = conclusion_map.get(conclusion.lower(), JobStatus.UNKNOWN)
            if mapped_conclusion != JobStatus.UNKNOWN:
                return mapped_conclusion
        
        if status:
            status_map = {
                "queued": JobStatus.QUEUED,
                "in_progress": JobStatus.IN_PROGRESS,
                "completed": JobStatus.SUCCESS,  # Fallback if conclusion not available
                "waiting": JobStatus.PENDING,
            }
            return status_map.get(status.lower(), JobStatus.UNKNOWN)
        
        return JobStatus.UNKNOWN
    
    def _map_check_status(self, status: Optional[str], conclusion: Optional[str]) -> BuildStatus:
        """Map GitHub Actions check status and conclusion to unified BuildStatus."""
        if conclusion:
            conclusion_map = {
                "success": BuildStatus.SUCCESS,
                "failure": BuildStatus.FAILURE,
                "cancelled": BuildStatus.CANCELLED,
                "skipped": BuildStatus.SKIPPED,
                "timed_out": BuildStatus.TIMEOUT,
                "action_required": BuildStatus.PENDING,
                "neutral": BuildStatus.SUCCESS,
            }
            mapped_conclusion = conclusion_map.get(conclusion.lower(), BuildStatus.UNKNOWN)
            if mapped_conclusion != BuildStatus.UNKNOWN:
                return mapped_conclusion
        
        if status:
            status_map = {
                "queued": BuildStatus.QUEUED,
                "in_progress": BuildStatus.IN_PROGRESS,
                "completed": BuildStatus.SUCCESS,  # Fallback if conclusion not available
                "waiting": BuildStatus.PENDING,
            }
            return status_map.get(status.lower(), BuildStatus.UNKNOWN)
        
        return BuildStatus.UNKNOWN
    
    def _map_step_status(self, status: Optional[str], conclusion: Optional[str]) -> JobStatus:
        """Map GitHub Actions step status and conclusion to unified JobStatus."""
        if conclusion:
            conclusion_map = {
                "success": JobStatus.SUCCESS,
                "failure": JobStatus.FAILURE,
                "cancelled": JobStatus.CANCELLED,
                "skipped": JobStatus.SKIPPED,
                "timed_out": JobStatus.TIMEOUT,
            }
            mapped_conclusion = conclusion_map.get(conclusion.lower(), JobStatus.UNKNOWN)
            if mapped_conclusion != JobStatus.UNKNOWN:
                return mapped_conclusion
        
        if status:
            status_map = {
                "queued": JobStatus.QUEUED,
                "in_progress": JobStatus.IN_PROGRESS,
                "completed": JobStatus.SUCCESS,  # Fallback if conclusion not available
                "waiting": JobStatus.PENDING,
            }
            return status_map.get(status.lower(), JobStatus.UNKNOWN)
        
        return JobStatus.UNKNOWN
    
    def _map_test_status(self, status: Optional[str]) -> TestStatus:
        """Map test status to unified TestStatus."""
        if not status:
            return TestStatus.UNKNOWN
        
        status_map = {
            "passed": TestStatus.PASSED,
            "failed": TestStatus.FAILED,
            "skipped": TestStatus.SKIPPED,
            "error": TestStatus.ERROR,
            "timeout": TestStatus.TIMEOUT,
            "success": TestStatus.PASSED,
            "failure": TestStatus.FAILED,
        }
        
        return status_map.get(status.lower(), TestStatus.UNKNOWN)
    
    def _parse_datetime(self, datetime_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string to datetime object."""
        if not datetime_str:
            return None
        
        try:
            # Handle different datetime formats from GitHub API
            if datetime_str.endswith('Z'):
                datetime_str = datetime_str[:-1] + '+00:00'
            
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse datetime '{datetime_str}': {e}")
            return None
    
    def _extract_test_results_from_job(self, job_data: Dict[str, Any]) -> List[TestResult]:
        """Extract test results from job data or logs."""
        test_results = []
        
        # Check if test results are directly provided
        if "test_results" in job_data:
            for test_data in job_data["test_results"]:
                test_results.append(self.test_results_to_test_result(test_data))
        
        # Check annotations for test failures
        if "annotations" in job_data:
            for annotation in job_data["annotations"]:
                if annotation.get("annotation_level") == "failure":
                    test_result = TestResult(
                        name=annotation.get("title", "Test Failure"),
                        status=TestStatus.FAILED,
                        message=annotation.get("message", ""),
                        file_path=annotation.get("path"),
                        line_number=annotation.get("start_line"),
                    )
                    test_results.append(test_result)
        
        return test_results
    
    def _create_error_build(self, original_data: Dict[str, Any], error_msg: str) -> CIBuild:
        """Create an error CIBuild when transformation fails."""
        return CIBuild(
            id=str(original_data.get("id", "unknown")),
            provider=self.provider,
            status=BuildStatus.ERROR,
            message=f"Error processing build: {error_msg}",
            metadata={"original_data": original_data, "error": error_msg}
        )
    
    def _create_error_pipeline(self, original_data: Dict[str, Any], error_msg: str) -> CIPipeline:
        """Create an error CIPipeline when transformation fails."""
        return CIPipeline(
            id=str(original_data.get("id", "unknown")),
            name=original_data.get("name", "Unknown Pipeline"),
            status=BuildStatus.ERROR,
            metadata={"original_data": original_data, "error": error_msg}
        )
    
    def _create_error_job(self, original_data: Dict[str, Any], error_msg: str) -> CIJob:
        """Create an error CIJob when transformation fails."""
        return CIJob(
            id=str(original_data.get("id", "unknown")),
            name=original_data.get("name", "Unknown Job"),
            status=JobStatus.ERROR,
            metadata={"original_data": original_data, "error": error_msg}
        )