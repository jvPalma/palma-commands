"""
Core enums for CI/CD integration.

This module defines the status states and provider types used throughout the CI tools.
"""

from enum import Enum


class CIProvider(Enum):
    """Supported CI/CD providers."""
    GITHUB_ACTIONS = "github_actions"
    JENKINS = "jenkins"
    GITLAB_CI = "gitlab_ci"
    TRAVIS_CI = "travis_ci"
    CIRCLE_CI = "circle_ci"
    AZURE_PIPELINES = "azure_pipelines"
    BUILDKITE = "buildkite"
    TEAMCITY = "teamcity"
    BAMBOO = "bamboo"
    DRONE = "drone"
    UNKNOWN = "unknown"


class BuildStatus(Enum):
    """Build status states."""
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    ERROR = "error"
    UNKNOWN = "unknown"


class JobStatus(Enum):
    """Job status states."""
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    ERROR = "error"
    UNKNOWN = "unknown"


class TestStatus(Enum):
    """Test result states."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"