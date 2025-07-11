"""
Buildkite API client for enhanced pipeline integration.

Provides comprehensive access to Buildkite APIs for pipeline monitoring,
build management, and artifact retrieval.
"""

import requests
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import time

from prs.config import get


@dataclass
class BuildkitePipeline:
    """Buildkite pipeline information."""
    id: str
    name: str
    slug: str
    url: str
    web_url: str
    repository: str
    default_branch: str
    description: str
    env: Dict[str, str]
    provider: Dict[str, Any]
    skip_queued_branch_builds: bool
    cancel_running_branch_builds: bool
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> 'BuildkitePipeline':
        """Create from Buildkite API response."""
        return cls(
            id=data['id'],
            name=data['name'],
            slug=data['slug'],
            url=data['url'],
            web_url=data['web_url'],
            repository=data['repository'],
            default_branch=data['default_branch'],
            description=data.get('description', ''),
            env=data.get('env', {}),
            provider=data.get('provider', {}),
            skip_queued_branch_builds=data.get('skip_queued_branch_builds', False),
            cancel_running_branch_builds=data.get('cancel_running_branch_builds', False),
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
        )


@dataclass
class BuildkiteBuild:
    """Buildkite build information."""
    id: str
    number: int
    state: str
    blocked: bool
    message: str
    commit: str
    branch: str
    source: str
    creator: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    meta_data: Dict[str, Any]
    pull_request: Optional[Dict[str, Any]]
    pipeline: Dict[str, Any]
    web_url: str
    url: str
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate build duration."""
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        return None
    
    @property
    def is_pull_request_build(self) -> bool:
        """Check if this is a pull request build."""
        return self.pull_request is not None
    
    @property
    def pr_number(self) -> Optional[int]:
        """Get PR number if this is a PR build."""
        if self.pull_request:
            return self.pull_request.get('number')
        return None
    
    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> 'BuildkiteBuild':
        """Create from Buildkite API response."""
        started_at = None
        if data.get('started_at'):
            started_at = datetime.fromisoformat(data['started_at'].replace('Z', '+00:00'))
            
        finished_at = None
        if data.get('finished_at'):
            finished_at = datetime.fromisoformat(data['finished_at'].replace('Z', '+00:00'))
        
        return cls(
            id=data['id'],
            number=data['number'],
            state=data['state'],
            blocked=data.get('blocked', False),
            message=data['message'],
            commit=data['commit'],
            branch=data['branch'],
            source=data['source'],
            creator=data.get('creator', {}),
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
            started_at=started_at,
            finished_at=finished_at,
            meta_data=data.get('meta_data', {}),
            pull_request=data.get('pull_request'),
            pipeline=data.get('pipeline', {}),
            web_url=data['web_url'],
            url=data['url']
        )


@dataclass
class BuildkiteJob:
    """Buildkite job information."""
    id: str
    name: str
    state: str
    type: str
    command: Optional[str]
    step_key: Optional[str]
    agent_query_rules: List[str]
    artifact_paths: Optional[str]
    env: Dict[str, str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    log_url: str
    raw_log_url: str
    web_url: str
    exit_status: Optional[int]
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate job duration."""
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        return None
    
    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> 'BuildkiteJob':
        """Create from Buildkite API response."""
        started_at = None
        if data.get('started_at'):
            started_at = datetime.fromisoformat(data['started_at'].replace('Z', '+00:00'))
            
        finished_at = None
        if data.get('finished_at'):
            finished_at = datetime.fromisoformat(data['finished_at'].replace('Z', '+00:00'))
        
        return cls(
            id=data['id'],
            name=data.get('name', ''),
            state=data['state'],
            type=data.get('type', 'script'),
            command=data.get('command'),
            step_key=data.get('step_key'),
            agent_query_rules=data.get('agent_query_rules', []),
            artifact_paths=data.get('artifact_paths'),
            env=data.get('env', {}),
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
            started_at=started_at,
            finished_at=finished_at,
            log_url=data.get('log_url', ''),
            raw_log_url=data.get('raw_log_url', ''),
            web_url=data.get('web_url', ''),
            exit_status=data.get('exit_status')
        )


@dataclass
class BuildkiteArtifact:
    """Buildkite artifact information."""
    id: str
    filename: str
    path: str
    file_size: int
    mime_type: str
    md5sum: str
    sha1sum: str
    url: str
    download_url: str
    created_at: datetime
    
    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> 'BuildkiteArtifact':
        """Create from Buildkite API response."""
        return cls(
            id=data['id'],
            filename=data['filename'],
            path=data['path'],
            file_size=data['file_size'],
            mime_type=data['mime_type'],
            md5sum=data['md5sum'],
            sha1sum=data['sha1sum'],
            url=data['url'],
            download_url=data['download_url'],
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        )


class BuildkiteClient:
    """
    Enhanced Buildkite API client.
    
    Provides comprehensive access to Buildkite APIs with authentication,
    rate limiting, caching, and error handling.
    """
    
    def __init__(self, token: str = None, organization: str = None):
        self.token = token or get("buildkite", "api_token", fallback="")
        self.organization = organization or get("buildkite", "organization", fallback="")
        self.base_url = "https://api.buildkite.com/v2"
        
        # HTTP session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "PRS-TUI/1.0"
        })
        
        # Rate limiting
        self.rate_limit_remaining = 1000
        self.rate_limit_reset = time.time() + 3600
        
        # Simple cache
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)
        
    def _make_request(self, method: str, endpoint: str, 
                     params: Dict[str, Any] = None,
                     data: Dict[str, Any] = None,
                     use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Make authenticated request to Buildkite API."""
        if not self.token:
            raise ValueError("Buildkite API token not configured")
            
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        cache_key = f"{method}:{url}:{json.dumps(params, sort_keys=True) if params else ''}"
        
        # Check cache first
        if use_cache and method == "GET":
            cached_result = self._get_cached_result(cache_key)
            if cached_result is not None:
                return cached_result
        
        # Check rate limiting
        if self.rate_limit_remaining <= 1:
            wait_time = max(0, self.rate_limit_reset - time.time())
            if wait_time > 0:
                time.sleep(min(wait_time, 60))  # Max 1 minute wait
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=30
            )
            
            # Update rate limiting info
            self.rate_limit_remaining = int(response.headers.get('RateLimit-Remaining', 1000))
            self.rate_limit_reset = time.time() + int(response.headers.get('RateLimit-Reset', 3600))
            
            response.raise_for_status()
            result = response.json() if response.content else {}
            
            # Cache GET requests
            if use_cache and method == "GET":
                self._cache_result(cache_key, result)
                
            return result
            
        except requests.RequestException as e:
            print(f"Buildkite API error: {e}")
            return None
            
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if available and fresh."""
        if cache_key not in self._cache:
            return None
            
        cache_time = self._cache_timestamps.get(cache_key)
        if not cache_time or datetime.now() - cache_time > self._cache_ttl:
            # Cache expired
            self._cache.pop(cache_key, None)
            self._cache_timestamps.pop(cache_key, None)
            return None
            
        return self._cache[cache_key]
        
    def _cache_result(self, cache_key: str, result: Any):
        """Cache API result."""
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = datetime.now()
        
        # Limit cache size
        if len(self._cache) > 1000:
            # Remove oldest entries
            oldest_keys = sorted(
                self._cache_timestamps.keys(),
                key=lambda k: self._cache_timestamps[k]
            )[:100]
            
            for key in oldest_keys:
                self._cache.pop(key, None)
                self._cache_timestamps.pop(key, None)
    
    def get_pipelines(self) -> List[BuildkitePipeline]:
        """Get all pipelines for the organization."""
        if not self.organization:
            return []
            
        response = self._make_request("GET", f"/organizations/{self.organization}/pipelines")
        if not response:
            return []
            
        return [BuildkitePipeline.from_api(pipeline) for pipeline in response]
    
    def get_pipeline(self, pipeline_slug: str) -> Optional[BuildkitePipeline]:
        """Get specific pipeline information."""
        if not self.organization:
            return None
            
        response = self._make_request("GET", f"/organizations/{self.organization}/pipelines/{pipeline_slug}")
        if not response:
            return None
            
        return BuildkitePipeline.from_api(response)
    
    def get_builds(self, pipeline_slug: str = None, 
                   state: str = None, 
                   branch: str = None,
                   commit: str = None,
                   created_from: datetime = None,
                   created_to: datetime = None,
                   page: int = 1,
                   per_page: int = 30) -> List[BuildkiteBuild]:
        """Get builds with optional filtering."""
        if not self.organization:
            return []
            
        # Build endpoint
        if pipeline_slug:
            endpoint = f"/organizations/{self.organization}/pipelines/{pipeline_slug}/builds"
        else:
            endpoint = f"/organizations/{self.organization}/builds"
            
        # Build parameters
        params = {
            "page": page,
            "per_page": per_page
        }
        
        if state:
            params["state"] = state
        if branch:
            params["branch"] = branch
        if commit:
            params["commit"] = commit
        if created_from:
            params["created_from"] = created_from.isoformat()
        if created_to:
            params["created_to"] = created_to.isoformat()
            
        response = self._make_request("GET", endpoint, params=params)
        if not response:
            return []
            
        return [BuildkiteBuild.from_api(build) for build in response]
    
    def get_build(self, pipeline_slug: str, build_number: Union[int, str]) -> Optional[BuildkiteBuild]:
        """Get specific build information."""
        if not self.organization:
            return None
            
        response = self._make_request(
            "GET", 
            f"/organizations/{self.organization}/pipelines/{pipeline_slug}/builds/{build_number}"
        )
        if not response:
            return None
            
        return BuildkiteBuild.from_api(response)
    
    def get_build_jobs(self, pipeline_slug: str, build_number: Union[int, str]) -> List[BuildkiteJob]:
        """Get jobs for a specific build."""
        build = self.get_build(pipeline_slug, build_number)
        if not build:
            return []
            
        response = self._make_request(
            "GET",
            f"/organizations/{self.organization}/pipelines/{pipeline_slug}/builds/{build_number}/jobs"
        )
        if not response:
            return []
            
        return [BuildkiteJob.from_api(job) for job in response]
    
    def get_job_log(self, pipeline_slug: str, build_number: Union[int, str], 
                   job_id: str) -> Optional[str]:
        """Get raw log content for a job."""
        response = self._make_request(
            "GET",
            f"/organizations/{self.organization}/pipelines/{pipeline_slug}/builds/{build_number}/jobs/{job_id}/log",
            use_cache=False  # Don't cache logs
        )
        
        if response:
            return response.get('content', '')
        return None
    
    def get_build_artifacts(self, pipeline_slug: str, 
                           build_number: Union[int, str]) -> List[BuildkiteArtifact]:
        """Get artifacts for a specific build."""
        response = self._make_request(
            "GET",
            f"/organizations/{self.organization}/pipelines/{pipeline_slug}/builds/{build_number}/artifacts"
        )
        if not response:
            return []
            
        return [BuildkiteArtifact.from_api(artifact) for artifact in response]
    
    def download_artifact(self, artifact: BuildkiteArtifact, local_path: str) -> bool:
        """Download an artifact to local file."""
        try:
            response = self.session.get(artifact.download_url, stream=True)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            return True
        except Exception:
            return False
    
    def get_builds_for_pr(self, pr_number: int, 
                         pipeline_slug: str = None) -> List[BuildkiteBuild]:
        """Get builds associated with a specific pull request."""
        # Get recent builds and filter by PR
        builds = self.get_builds(
            pipeline_slug=pipeline_slug,
            created_from=datetime.now() - timedelta(days=30),  # Last 30 days
            per_page=100
        )
        
        # Filter for the specific PR
        pr_builds = []
        for build in builds:
            if build.is_pull_request_build and build.pr_number == pr_number:
                pr_builds.append(build)
                
        return pr_builds
    
    def get_pipeline_metrics(self, pipeline_slug: str, 
                           days: int = 30) -> Dict[str, Any]:
        """Get pipeline performance metrics."""
        since = datetime.now() - timedelta(days=days)
        builds = self.get_builds(
            pipeline_slug=pipeline_slug,
            created_from=since,
            per_page=100
        )
        
        if not builds:
            return {
                "total_builds": 0,
                "success_rate": 0.0,
                "average_duration": None,
                "builds_per_day": 0.0
            }
        
        # Calculate metrics
        total_builds = len(builds)
        successful_builds = sum(1 for build in builds if build.state == "passed")
        success_rate = (successful_builds / total_builds) * 100
        
        # Calculate average duration for completed builds
        completed_builds = [build for build in builds if build.duration]
        if completed_builds:
            total_duration = sum(build.duration.total_seconds() for build in completed_builds)
            average_duration = total_duration / len(completed_builds)
        else:
            average_duration = None
            
        builds_per_day = total_builds / days
        
        return {
            "total_builds": total_builds,
            "successful_builds": successful_builds,
            "failed_builds": total_builds - successful_builds,
            "success_rate": success_rate,
            "average_duration": average_duration,
            "builds_per_day": builds_per_day,
            "period_days": days
        }
    
    def rebuild(self, pipeline_slug: str, build_number: Union[int, str]) -> bool:
        """Rebuild a specific build."""
        response = self._make_request(
            "PUT",
            f"/organizations/{self.organization}/pipelines/{pipeline_slug}/builds/{build_number}/rebuild",
            use_cache=False
        )
        return response is not None
    
    def cancel_build(self, pipeline_slug: str, build_number: Union[int, str]) -> bool:
        """Cancel a running build."""
        response = self._make_request(
            "PUT",
            f"/organizations/{self.organization}/pipelines/{pipeline_slug}/builds/{build_number}/cancel",
            use_cache=False
        )
        return response is not None
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get organization agent status."""
        response = self._make_request("GET", f"/organizations/{self.organization}/agents")
        if not response:
            return {}
            
        agents = response
        total_agents = len(agents)
        connected_agents = sum(1 for agent in agents if agent.get('connection_state') == 'connected')
        
        return {
            "total_agents": total_agents,
            "connected_agents": connected_agents,
            "idle_agents": sum(1 for agent in agents 
                             if agent.get('connection_state') == 'connected' and not agent.get('job')),
            "busy_agents": sum(1 for agent in agents 
                             if agent.get('connection_state') == 'connected' and agent.get('job')),
            "agents": agents
        }
    
    def is_configured(self) -> bool:
        """Check if Buildkite is properly configured."""
        return bool(self.token and self.organization)
    
    def test_connection(self) -> bool:
        """Test connection to Buildkite API."""
        if not self.is_configured():
            return False
            
        try:
            response = self._make_request("GET", f"/organizations/{self.organization}")
            return response is not None
        except Exception:
            return False