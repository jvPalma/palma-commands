"""
Core data models for CI/CD integration.

This module defines the comprehensive data models used to represent CI/CD information
across different providers. All models support serialization/deserialization for
cache storage.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import json

from .enums import CIProvider, BuildStatus, JobStatus, TestStatus


@dataclass
class TestResult:
    """Represents a test result within a CI job."""
    name: str
    status: TestStatus
    duration: Optional[float] = None
    message: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suite_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['status'] = self.status.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestResult':
        """Create from dictionary for deserialization."""
        data['status'] = TestStatus(data['status'])
        return cls(**data)


@dataclass
class BuildStep:
    """Represents a build step within a CI job."""
    name: str
    status: JobStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    command: Optional[str] = None
    exit_code: Optional[int] = None
    logs: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['status'] = self.status.value
        result['started_at'] = self.started_at.isoformat() if self.started_at else None
        result['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BuildStep':
        """Create from dictionary for deserialization."""
        data['status'] = JobStatus(data['status'])
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)


@dataclass
class CICheck:
    """Represents an individual CI check (status check)."""
    name: str
    status: BuildStatus
    conclusion: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    details_url: Optional[str] = None
    external_id: Optional[str] = None
    context: Optional[str] = None
    description: Optional[str] = None
    target_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['status'] = self.status.value
        result['started_at'] = self.started_at.isoformat() if self.started_at else None
        result['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CICheck':
        """Create from dictionary for deserialization."""
        data['status'] = BuildStatus(data['status'])
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)


@dataclass
class CIJob:
    """Represents an individual CI job/step."""
    id: str
    name: str
    status: JobStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    runner: Optional[str] = None
    environment: Optional[str] = None
    logs_url: Optional[str] = None
    steps: List[BuildStep] = field(default_factory=list)
    test_results: List[TestResult] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['status'] = self.status.value
        result['started_at'] = self.started_at.isoformat() if self.started_at else None
        result['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        result['steps'] = [step.to_dict() for step in self.steps]
        result['test_results'] = [test.to_dict() for test in self.test_results]
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CIJob':
        """Create from dictionary for deserialization."""
        data['status'] = JobStatus(data['status'])
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        
        data['steps'] = [BuildStep.from_dict(step) for step in data.get('steps', [])]
        data['test_results'] = [TestResult.from_dict(test) for test in data.get('test_results', [])]
        
        return cls(**data)


@dataclass
class CIPipeline:
    """Represents a complete CI pipeline/workflow."""
    id: str
    name: str
    status: BuildStatus
    trigger: Optional[str] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    jobs: List[CIJob] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['status'] = self.status.value
        result['started_at'] = self.started_at.isoformat() if self.started_at else None
        result['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        result['jobs'] = [job.to_dict() for job in self.jobs]
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CIPipeline':
        """Create from dictionary for deserialization."""
        data['status'] = BuildStatus(data['status'])
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        
        data['jobs'] = [CIJob.from_dict(job) for job in data.get('jobs', [])]
        
        return cls(**data)


@dataclass
class CIBuild:
    """Represents a complete CI build run."""
    id: str
    number: Optional[int] = None
    provider: CIProvider = CIProvider.UNKNOWN
    status: BuildStatus = BuildStatus.UNKNOWN
    url: Optional[str] = None
    commit_sha: Optional[str] = None
    branch: Optional[str] = None
    message: Optional[str] = None
    author: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    checks: List[CICheck] = field(default_factory=list)
    pipelines: List[CIPipeline] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['provider'] = self.provider.value
        result['status'] = self.status.value
        result['started_at'] = self.started_at.isoformat() if self.started_at else None
        result['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        result['checks'] = [check.to_dict() for check in self.checks]
        result['pipelines'] = [pipeline.to_dict() for pipeline in self.pipelines]
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CIBuild':
        """Create from dictionary for deserialization."""
        data['provider'] = CIProvider(data['provider'])
        data['status'] = BuildStatus(data['status'])
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        
        data['checks'] = [CICheck.from_dict(check) for check in data.get('checks', [])]
        data['pipelines'] = [CIPipeline.from_dict(pipeline) for pipeline in data.get('pipelines', [])]
        
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert to JSON string for cache storage."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'CIBuild':
        """Create from JSON string for cache retrieval."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class CIAggregatedMetrics:
    """Represents aggregated CI metrics and analytics."""
    total_builds: int = 0
    successful_builds: int = 0
    failed_builds: int = 0
    cancelled_builds: int = 0
    average_duration: Optional[float] = None
    success_rate: Optional[float] = None
    failure_rate: Optional[float] = None
    most_common_failures: List[str] = field(default_factory=list)
    average_queue_time: Optional[float] = None
    total_test_runs: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    test_success_rate: Optional[float] = None
    flaky_tests: List[str] = field(default_factory=list)
    coverage_percentage: Optional[float] = None
    build_frequency: Optional[float] = None  # builds per day
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CIAggregatedMetrics':
        """Create from dictionary for deserialization."""
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert to JSON string for cache storage."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'CIAggregatedMetrics':
        """Create from JSON string for cache retrieval."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def calculate_rates(self) -> None:
        """Calculate success and failure rates based on build counts."""
        if self.total_builds > 0:
            self.success_rate = (self.successful_builds / self.total_builds) * 100
            self.failure_rate = (self.failed_builds / self.total_builds) * 100
        
        if self.total_test_runs > 0:
            self.test_success_rate = (self.passed_tests / self.total_test_runs) * 100