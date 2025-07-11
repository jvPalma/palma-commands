"""
Enhanced Buildkite provider with pipeline data and build logs integration.
Provides deep integration with Buildkite for comprehensive CI insights.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import requests
from urllib.parse import urljoin

from ..base.models import CIProvider, CIBuild, CICheck, CIJob, BuildStatus
from ...config import get


@dataclass
class BuildkitePipeline:
    """Buildkite pipeline information."""
    id: str
    name: str
    slug: str
    url: str
    repository: str
    branch_configuration: Dict[str, Any] = field(default_factory=dict)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    description: Optional[str] = None


@dataclass
class BuildkiteBuild:
    """Buildkite build information."""
    id: str
    number: int
    state: str
    blocked: bool
    branch: str
    commit: str
    message: str
    author: Dict[str, str]
    url: str
    web_url: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    pipeline: Optional[BuildkitePipeline] = None
    jobs: List[Dict[str, Any]] = field(default_factory=list)
    pull_request: Optional[Dict[str, Any]] = None
    meta_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BuildkiteJob:
    """Buildkite job information."""
    id: str
    name: str
    state: str
    command: Optional[str] = None
    exit_status: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    log_url: Optional[str] = None
    web_url: Optional[str] = None
    agent: Optional[Dict[str, Any]] = None
    artifact_paths: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    retry_count: int = 0


@dataclass
class BuildkiteArtifact:
    """Buildkite artifact information."""
    id: str
    path: str
    filename: str
    mime_type: str
    file_size: int
    sha1sum: str
    download_url: str
    state: str
    created_at: Optional[datetime] = None


class EnhancedBuildkiteProvider:
    """
    Enhanced Buildkite provider with deep integration capabilities.
    
    Features:
    - Pipeline data and configuration
    - Build logs and artifacts
    - Real-time build status
    - Job-level details and metrics
    - Dependency visualization
    - Performance analytics
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.buildkite.com/v2"):
        self.api_key = api_key or get("buildkite", "api_key")
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        
        self.logger = logging.getLogger(__name__)
        
        # Cache for pipeline data
        self.pipeline_cache: Dict[str, BuildkitePipeline] = {}
        self.build_cache: Dict[str, BuildkiteBuild] = {}
    
    def get_organizations(self) -> List[Dict[str, Any]]:
        """Get all organizations accessible to the user."""
        try:
            response = self.session.get(f"{self.base_url}/organizations")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error fetching organizations: {e}")
            return []
    
    def get_pipelines(self, org_slug: str) -> List[BuildkitePipeline]:
        """Get all pipelines for an organization."""
        try:
            response = self.session.get(f"{self.base_url}/organizations/{org_slug}/pipelines")
            response.raise_for_status()
            
            pipelines = []
            for pipeline_data in response.json():
                pipeline = BuildkitePipeline(
                    id=pipeline_data["id"],
                    name=pipeline_data["name"],
                    slug=pipeline_data["slug"],
                    url=pipeline_data["url"],
                    repository=pipeline_data["repository"],
                    branch_configuration=pipeline_data.get("branch_configuration", {}),
                    steps=pipeline_data.get("steps", []),
                    env=pipeline_data.get("env", {}),
                    created_at=self._parse_datetime(pipeline_data.get("created_at")),
                    description=pipeline_data.get("description")
                )
                pipelines.append(pipeline)
                
                # Cache pipeline
                self.pipeline_cache[pipeline.slug] = pipeline
            
            return pipelines
            
        except Exception as e:
            self.logger.error(f"Error fetching pipelines for {org_slug}: {e}")
            return []
    
    def get_pipeline(self, org_slug: str, pipeline_slug: str) -> Optional[BuildkitePipeline]:
        """Get a specific pipeline."""
        # Check cache first
        if pipeline_slug in self.pipeline_cache:
            return self.pipeline_cache[pipeline_slug]
        
        try:
            response = self.session.get(f"{self.base_url}/organizations/{org_slug}/pipelines/{pipeline_slug}")
            response.raise_for_status()
            
            pipeline_data = response.json()
            pipeline = BuildkitePipeline(
                id=pipeline_data["id"],
                name=pipeline_data["name"],
                slug=pipeline_data["slug"],
                url=pipeline_data["url"],
                repository=pipeline_data["repository"],
                branch_configuration=pipeline_data.get("branch_configuration", {}),
                steps=pipeline_data.get("steps", []),
                env=pipeline_data.get("env", {}),
                created_at=self._parse_datetime(pipeline_data.get("created_at")),
                description=pipeline_data.get("description")
            )
            
            # Cache pipeline
            self.pipeline_cache[pipeline_slug] = pipeline
            return pipeline
            
        except Exception as e:
            self.logger.error(f"Error fetching pipeline {pipeline_slug}: {e}")
            return None
    
    def get_builds(self, org_slug: str, pipeline_slug: str, 
                  branch: Optional[str] = None, 
                  state: Optional[str] = None,
                  per_page: int = 30) -> List[BuildkiteBuild]:
        """Get builds for a pipeline."""
        try:
            params = {"per_page": per_page}
            if branch:
                params["branch"] = branch
            if state:
                params["state"] = state
            
            response = self.session.get(
                f"{self.base_url}/organizations/{org_slug}/pipelines/{pipeline_slug}/builds",
                params=params
            )
            response.raise_for_status()
            
            builds = []
            for build_data in response.json():
                build = self._parse_build(build_data)
                builds.append(build)
                
                # Cache build
                self.build_cache[build.id] = build
            
            return builds
            
        except Exception as e:
            self.logger.error(f"Error fetching builds for {pipeline_slug}: {e}")
            return []
    
    def get_build(self, org_slug: str, pipeline_slug: str, build_number: int) -> Optional[BuildkiteBuild]:
        """Get a specific build."""
        try:
            response = self.session.get(
                f"{self.base_url}/organizations/{org_slug}/pipelines/{pipeline_slug}/builds/{build_number}"
            )
            response.raise_for_status()
            
            build_data = response.json()
            build = self._parse_build(build_data)
            
            # Cache build
            self.build_cache[build.id] = build
            return build
            
        except Exception as e:
            self.logger.error(f"Error fetching build {build_number}: {e}")
            return None
    
    def get_build_jobs(self, org_slug: str, pipeline_slug: str, build_number: int) -> List[BuildkiteJob]:
        """Get jobs for a specific build."""
        try:
            build = self.get_build(org_slug, pipeline_slug, build_number)
            if not build:
                return []
            
            jobs = []
            for job_data in build.jobs:
                if job_data.get("type") == "script":
                    job = BuildkiteJob(
                        id=job_data["id"],
                        name=job_data.get("name", "Unknown"),
                        state=job_data["state"],
                        command=job_data.get("command"),
                        exit_status=job_data.get("exit_status"),
                        started_at=self._parse_datetime(job_data.get("started_at")),
                        finished_at=self._parse_datetime(job_data.get("finished_at")),
                        log_url=job_data.get("log_url"),
                        web_url=job_data.get("web_url"),
                        agent=job_data.get("agent"),
                        artifact_paths=job_data.get("artifact_paths", []),
                        env=job_data.get("env", {}),
                        retry_count=job_data.get("retries_count", 0)
                    )
                    jobs.append(job)
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Error fetching jobs for build {build_number}: {e}")
            return []
    
    def get_job_log(self, org_slug: str, pipeline_slug: str, build_number: int, job_id: str) -> Optional[str]:
        """Get log for a specific job."""
        try:
            response = self.session.get(
                f"{self.base_url}/organizations/{org_slug}/pipelines/{pipeline_slug}/builds/{build_number}/jobs/{job_id}/log"
            )
            response.raise_for_status()
            
            # The response is plain text log content
            return response.text
            
        except Exception as e:
            self.logger.error(f"Error fetching log for job {job_id}: {e}")
            return None
    
    def get_build_artifacts(self, org_slug: str, pipeline_slug: str, build_number: int) -> List[BuildkiteArtifact]:
        """Get artifacts for a build."""
        try:
            response = self.session.get(
                f"{self.base_url}/organizations/{org_slug}/pipelines/{pipeline_slug}/builds/{build_number}/artifacts"
            )
            response.raise_for_status()
            
            artifacts = []
            for artifact_data in response.json():
                artifact = BuildkiteArtifact(
                    id=artifact_data["id"],
                    path=artifact_data["path"],
                    filename=artifact_data["filename"],
                    mime_type=artifact_data["mime_type"],
                    file_size=artifact_data["file_size"],
                    sha1sum=artifact_data["sha1sum"],
                    download_url=artifact_data["download_url"],
                    state=artifact_data["state"],
                    created_at=self._parse_datetime(artifact_data.get("created_at"))
                )
                artifacts.append(artifact)
            
            return artifacts
            
        except Exception as e:
            self.logger.error(f"Error fetching artifacts for build {build_number}: {e}")
            return []
    
    def get_pr_builds(self, org_slug: str, pipeline_slug: str, pr_number: int) -> List[BuildkiteBuild]:
        """Get builds for a specific PR."""
        try:
            # Get all builds and filter by PR
            builds = self.get_builds(org_slug, pipeline_slug, per_page=100)
            
            pr_builds = []
            for build in builds:
                if build.pull_request and build.pull_request.get("number") == pr_number:
                    pr_builds.append(build)
            
            return pr_builds
            
        except Exception as e:
            self.logger.error(f"Error fetching PR builds for #{pr_number}: {e}")
            return []
    
    def get_pr_checks(self, pr_id: int, repo_owner: str, repo_name: str) -> List[CICheck]:
        """Get CI checks for a PR (implements base interface)."""
        try:
            # This assumes we know the organization and pipeline
            # In practice, this would need configuration mapping
            org_slug = repo_owner  # or get from config
            pipeline_slug = f"{repo_name}-ci"  # or get from config
            
            builds = self.get_pr_builds(org_slug, pipeline_slug, pr_id)
            
            checks = []
            for build in builds:
                # Get jobs for this build
                jobs = self.get_build_jobs(org_slug, pipeline_slug, build.number)
                
                for job in jobs:
                    check = CICheck(
                        id=job.id,
                        name=job.name,
                        status=self._map_job_status(job.state),
                        conclusion=job.state,
                        started_at=job.started_at,
                        completed_at=job.finished_at,
                        details_url=job.web_url,
                        summary=f"Buildkite job: {job.name}",
                        output=None  # Would need to fetch log
                    )
                    checks.append(check)
            
            return checks
            
        except Exception as e:
            self.logger.error(f"Error fetching PR checks for #{pr_id}: {e}")
            return []
    
    def get_pipeline_metrics(self, org_slug: str, pipeline_slug: str, 
                           days: int = 30) -> Dict[str, Any]:
        """Get pipeline performance metrics."""
        try:
            # Get builds from the last N days
            builds = self.get_builds(org_slug, pipeline_slug, per_page=100)
            
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_builds = [
                build for build in builds 
                if build.started_at and build.started_at >= cutoff_date
            ]
            
            if not recent_builds:
                return {}
            
            # Calculate metrics
            total_builds = len(recent_builds)
            successful_builds = len([b for b in recent_builds if b.state == "passed"])
            failed_builds = len([b for b in recent_builds if b.state == "failed"])
            
            # Calculate average build time
            finished_builds = [b for b in recent_builds if b.finished_at and b.started_at]
            if finished_builds:
                build_times = [
                    (b.finished_at - b.started_at).total_seconds() / 60  # minutes
                    for b in finished_builds
                ]
                avg_build_time = sum(build_times) / len(build_times)
            else:
                avg_build_time = 0
            
            # Success rate
            success_rate = (successful_builds / total_builds * 100) if total_builds > 0 else 0
            
            # Builds per day
            builds_per_day = total_builds / days
            
            # Most common failure reasons (simplified)
            failure_reasons = {}
            for build in recent_builds:
                if build.state == "failed":
                    # This is simplified - in practice, you'd analyze job failure patterns
                    failure_reasons["build_failure"] = failure_reasons.get("build_failure", 0) + 1
            
            return {
                "total_builds": total_builds,
                "successful_builds": successful_builds,
                "failed_builds": failed_builds,
                "success_rate": success_rate,
                "avg_build_time_minutes": avg_build_time,
                "builds_per_day": builds_per_day,
                "failure_reasons": failure_reasons,
                "period_days": days
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating pipeline metrics: {e}")
            return {}
    
    def get_pipeline_dependency_graph(self, org_slug: str, pipeline_slug: str) -> Dict[str, Any]:
        """Get pipeline dependency visualization data."""
        try:
            pipeline = self.get_pipeline(org_slug, pipeline_slug)
            if not pipeline:
                return {}
            
            # Parse pipeline steps for dependencies
            steps = pipeline.steps
            dependency_graph = {
                "nodes": [],
                "edges": []
            }
            
            for i, step in enumerate(steps):
                step_type = step.get("type", "command")
                
                node = {
                    "id": f"step_{i}",
                    "label": step.get("label", f"Step {i+1}"),
                    "type": step_type,
                    "command": step.get("command"),
                    "depends_on": step.get("depends_on", [])
                }
                dependency_graph["nodes"].append(node)
                
                # Add edges for dependencies
                for dependency in step.get("depends_on", []):
                    edge = {
                        "from": dependency,
                        "to": f"step_{i}",
                        "type": "depends_on"
                    }
                    dependency_graph["edges"].append(edge)
            
            return dependency_graph
            
        except Exception as e:
            self.logger.error(f"Error creating dependency graph: {e}")
            return {}
    
    def trigger_build(self, org_slug: str, pipeline_slug: str, 
                     branch: str = "main", 
                     message: Optional[str] = None,
                     commit: Optional[str] = None,
                     env: Optional[Dict[str, str]] = None) -> Optional[BuildkiteBuild]:
        """Trigger a new build."""
        try:
            payload = {
                "branch": branch,
                "message": message or f"Triggered via PRS at {datetime.now().isoformat()}",
            }
            
            if commit:
                payload["commit"] = commit
            
            if env:
                payload["env"] = env
            
            response = self.session.post(
                f"{self.base_url}/organizations/{org_slug}/pipelines/{pipeline_slug}/builds",
                json=payload
            )
            response.raise_for_status()
            
            build_data = response.json()
            build = self._parse_build(build_data)
            
            # Cache build
            self.build_cache[build.id] = build
            return build
            
        except Exception as e:
            self.logger.error(f"Error triggering build: {e}")
            return None
    
    def cancel_build(self, org_slug: str, pipeline_slug: str, build_number: int) -> bool:
        """Cancel a running build."""
        try:
            response = self.session.put(
                f"{self.base_url}/organizations/{org_slug}/pipelines/{pipeline_slug}/builds/{build_number}/cancel"
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            self.logger.error(f"Error canceling build {build_number}: {e}")
            return False
    
    def retry_build(self, org_slug: str, pipeline_slug: str, build_number: int) -> Optional[BuildkiteBuild]:
        """Retry a failed build."""
        try:
            response = self.session.put(
                f"{self.base_url}/organizations/{org_slug}/pipelines/{pipeline_slug}/builds/{build_number}/retry"
            )
            response.raise_for_status()
            
            build_data = response.json()
            build = self._parse_build(build_data)
            
            # Cache build
            self.build_cache[build.id] = build
            return build
            
        except Exception as e:
            self.logger.error(f"Error retrying build {build_number}: {e}")
            return None
    
    def _parse_build(self, build_data: Dict[str, Any]) -> BuildkiteBuild:
        """Parse build data from API response."""
        return BuildkiteBuild(
            id=build_data["id"],
            number=build_data["number"],
            state=build_data["state"],
            blocked=build_data.get("blocked", False),
            branch=build_data["branch"],
            commit=build_data["commit"],
            message=build_data["message"],
            author=build_data.get("author", {}),
            url=build_data["url"],
            web_url=build_data["web_url"],
            started_at=self._parse_datetime(build_data.get("started_at")),
            finished_at=self._parse_datetime(build_data.get("finished_at")),
            jobs=build_data.get("jobs", []),
            pull_request=build_data.get("pull_request"),
            meta_data=build_data.get("meta_data", {})
        )
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string."""
        if not date_str:
            return None
        
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None
    
    def _map_job_status(self, buildkite_state: str) -> BuildStatus:
        """Map Buildkite job state to BuildStatus."""
        status_map = {
            "passed": BuildStatus.PASSED,
            "failed": BuildStatus.FAILED,
            "canceled": BuildStatus.FAILED,
            "running": BuildStatus.PENDING,
            "scheduled": BuildStatus.PENDING,
            "assigned": BuildStatus.PENDING,
            "waiting": BuildStatus.PENDING,
            "blocked": BuildStatus.PENDING,
            "unblocked": BuildStatus.PENDING,
            "limiting": BuildStatus.PENDING,
            "limited": BuildStatus.PENDING,
            "skipped": BuildStatus.PASSED,
            "broken": BuildStatus.FAILED,
            "timed_out": BuildStatus.FAILED,
            "not_run": BuildStatus.UNKNOWN
        }
        return status_map.get(buildkite_state.lower(), BuildStatus.UNKNOWN)
    
    def get_build_analytics(self, org_slug: str, pipeline_slug: str, 
                          build_number: int) -> Dict[str, Any]:
        """Get detailed analytics for a specific build."""
        try:
            build = self.get_build(org_slug, pipeline_slug, build_number)
            if not build:
                return {}
            
            jobs = self.get_build_jobs(org_slug, pipeline_slug, build_number)
            
            # Calculate job timings
            job_timings = []
            for job in jobs:
                if job.started_at and job.finished_at:
                    duration = (job.finished_at - job.started_at).total_seconds()
                    job_timings.append({
                        "name": job.name,
                        "duration_seconds": duration,
                        "status": job.state,
                        "exit_status": job.exit_status,
                        "retry_count": job.retry_count
                    })
            
            # Calculate total build time
            total_time = 0
            if build.started_at and build.finished_at:
                total_time = (build.finished_at - build.started_at).total_seconds()
            
            # Identify bottlenecks
            bottlenecks = []
            if job_timings:
                avg_duration = sum(j["duration_seconds"] for j in job_timings) / len(job_timings)
                bottlenecks = [
                    job for job in job_timings 
                    if job["duration_seconds"] > avg_duration * 2
                ]
            
            return {
                "build_number": build.number,
                "state": build.state,
                "total_duration_seconds": total_time,
                "job_count": len(jobs),
                "job_timings": job_timings,
                "bottlenecks": bottlenecks,
                "commit": build.commit,
                "branch": build.branch,
                "author": build.author,
                "pull_request": build.pull_request
            }
            
        except Exception as e:
            self.logger.error(f"Error getting build analytics: {e}")
            return {}
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of the Buildkite API connection."""
        try:
            response = self.session.get(f"{self.base_url}/user")
            response.raise_for_status()
            
            user_data = response.json()
            return {
                "status": "healthy",
                "user": user_data.get("name", "Unknown"),
                "api_url": self.base_url,
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "api_url": self.base_url
            }