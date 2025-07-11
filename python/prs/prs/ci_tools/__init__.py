"""
CI Tools module for enhanced CI/CD integration.

This module provides abstractions for different CI/CD providers and their data models,
as well as authentication management for CI platforms.
"""

from .base.models import (
    CICheck,
    CIJob,
    CIPipeline,
    CIBuild,
    CIAggregatedMetrics,
    TestResult,
    BuildStep,
)
from .base.enums import (
    CIProvider,
    BuildStatus,
    JobStatus,
    TestStatus,
)
from .auth import CIAuthManager, SSOPortalAuth, TokenStorage
from .base.provider import provider_registry

# Register providers
def _register_providers():
    """Register all available CI providers."""
    # Register GitHub Actions provider
    try:
        from .github_actions.provider import GitHubActionsProvider
        provider_registry.register(
            GitHubActionsProvider,
            metadata={
                'name': 'GitHub Actions',
                'description': 'GitHub Actions CI/CD integration',
                'supports_pr_checks': True,
                'supports_builds': True,
                'supports_metrics': True,
                'requires_gh_cli': True
            }
        )
    except ImportError as e:
        import logging
        logging.getLogger("prs.ci_tools").warning(f"Failed to register GitHub Actions provider: {e}")

# Register providers on import
_register_providers()

__all__ = [
    "CICheck",
    "CIJob",
    "CIPipeline",
    "CIBuild",
    "CIAggregatedMetrics",
    "TestResult",
    "BuildStep",
    "CIProvider",
    "BuildStatus",
    "JobStatus",
    "TestStatus",
    "CIAuthManager",
    "SSOPortalAuth",
    "TokenStorage",
    "provider_registry",
]