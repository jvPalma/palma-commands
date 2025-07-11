"""
Base CI tools module containing core data models, enums, provider interface, and manager.
"""

from .models import (
    CICheck,
    CIJob,
    CIPipeline,
    CIBuild,
    CIAggregatedMetrics,
    TestResult,
    BuildStep,
)
from .enums import (
    CIProvider,
    BuildStatus,
    JobStatus,
    TestStatus,
)
from .provider import (
    CIProviderInterface,
    CIProviderError,
    CIProviderAuthError,
    CIProviderAPIError,
    CIProviderConfigError,
    CIProviderRegistry,
    CIProviderFactory,
    provider_registry,
    provider_factory,
)
from .manager import (
    CIManager,
    CIManagerError,
)

__all__ = [
    # Data models
    "CICheck",
    "CIJob",
    "CIPipeline",
    "CIBuild",
    "CIAggregatedMetrics",
    "TestResult",
    "BuildStep",
    # Enums
    "CIProvider",
    "BuildStatus",
    "JobStatus",
    "TestStatus",
    # Provider interface and exceptions
    "CIProviderInterface",
    "CIProviderError",
    "CIProviderAuthError",
    "CIProviderAPIError",
    "CIProviderConfigError",
    # Registry and factory
    "CIProviderRegistry",
    "CIProviderFactory",
    "provider_registry",
    "provider_factory",
    # Manager
    "CIManager",
    "CIManagerError",
]