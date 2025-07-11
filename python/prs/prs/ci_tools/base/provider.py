"""
CI Provider Interface and Registry System

This module defines the abstract base class for CI providers and implements
the registry and factory systems for managing multiple CI providers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Union, Tuple
from datetime import datetime

from .models import CIBuild, CIPipeline, CICheck, CIAggregatedMetrics
from .enums import CIProvider, BuildStatus


class CIProviderError(Exception):
    """Base exception for CI provider errors."""
    pass


class CIProviderAuthError(CIProviderError):
    """Authentication error for CI provider."""
    pass


class CIProviderAPIError(CIProviderError):
    """API error for CI provider."""
    pass


class CIProviderConfigError(CIProviderError):
    """Configuration error for CI provider."""
    pass


class CIProviderInterface(ABC):
    """
    Abstract base class for CI providers.
    
    This interface defines the contract that all CI providers must implement
    to integrate with the PRS tool. It provides methods for authentication,
    data retrieval, and health monitoring.
    """
    
    def __init__(self, auth_manager, config: Optional[Dict[str, Any]] = None):
        """
        Initialize CI provider.
        
        Args:
            auth_manager: Authentication manager instance
            config: Optional provider-specific configuration
        """
        self.auth_manager = auth_manager
        self.config = config or {}
        self.logger = logging.getLogger(f"prs.ci_tools.{self.provider_name}")
        self._authenticated = False
        self._health_status = {
            'status': 'unknown',
            'last_check': None,
            'message': None
        }
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (must match CIProvider enum value)."""
        pass
    
    @property
    @abstractmethod
    def provider_type(self) -> CIProvider:
        """Return the provider type enum."""
        pass
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return the base URL for the provider API."""
        pass
    
    @property
    @abstractmethod
    def requires_auth(self) -> bool:
        """Return True if provider requires authentication."""
        pass
    
    @property
    @abstractmethod
    def supported_features(self) -> List[str]:
        """
        Return list of supported features.
        
        Possible features:
        - 'checks': Status checks
        - 'builds': Build information
        - 'pipelines': Pipeline/workflow information
        - 'metrics': Aggregated metrics
        - 'realtime': Real-time updates
        - 'history': Historical data
        """
        pass
    
    @abstractmethod
    def validate_auth(self) -> bool:
        """
        Validate authentication credentials.
        
        Returns:
            True if authentication is valid
            
        Raises:
            CIProviderAuthError: If authentication fails
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    def get_build_details(self, build_id: str) -> Optional[CIBuild]:
        """
        Get detailed information for a specific build.
        
        Args:
            build_id: Build identifier
            
        Returns:
            Build details or None if not found
            
        Raises:
            CIProviderError: If operation fails
        """
        # Default implementation - providers can override
        return None
    
    def get_pipeline_details(self, pipeline_id: str) -> Optional[CIPipeline]:
        """
        Get detailed information for a specific pipeline.
        
        Args:
            pipeline_id: Pipeline identifier
            
        Returns:
            Pipeline details or None if not found
            
        Raises:
            CIProviderError: If operation fails
        """
        # Default implementation - providers can override
        return None
    
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
        # Default implementation - providers can override
        return []
    
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
        # Default implementation - providers can override
        return None
    
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
        # Default implementation - providers can override
        return {}
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the provider.
        
        Returns:
            Health check results
        """
        try:
            # Basic connectivity test
            auth_valid = self.validate_auth() if self.requires_auth else True
            
            if auth_valid:
                self._health_status = {
                    'status': 'healthy',
                    'last_check': datetime.now(),
                    'message': 'All systems operational'
                }
            else:
                self._health_status = {
                    'status': 'unhealthy',
                    'last_check': datetime.now(),
                    'message': 'Authentication failed'
                }
                
        except Exception as e:
            self._health_status = {
                'status': 'unhealthy',
                'last_check': datetime.now(),
                'message': str(e)
            }
        
        return {
            'provider': self.provider_name,
            'type': self.provider_type.value,
            'base_url': self.base_url,
            'requires_auth': self.requires_auth,
            'authenticated': self._authenticated,
            'supported_features': self.supported_features,
            **self._health_status
        }
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get provider information.
        
        Returns:
            Provider information dictionary
        """
        return {
            'name': self.provider_name,
            'type': self.provider_type.value,
            'base_url': self.base_url,
            'requires_auth': self.requires_auth,
            'authenticated': self._authenticated,
            'supported_features': self.supported_features,
            'config': self.config
        }


class CIProviderRegistry:
    """
    Registry for managing CI provider classes.
    
    This class maintains a registry of available CI providers and provides
    methods for registration, lookup, and enumeration.
    """
    
    def __init__(self):
        """Initialize the provider registry."""
        self._providers: Dict[str, Type[CIProviderInterface]] = {}
        self._provider_metadata: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger("prs.ci_tools.registry")
    
    def register(self, provider_class: Type[CIProviderInterface], 
                metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Register a CI provider class.
        
        Args:
            provider_class: Provider class to register
            metadata: Optional metadata about the provider
            
        Raises:
            CIProviderConfigError: If provider is invalid
        """
        # Validate provider class
        if not issubclass(provider_class, CIProviderInterface):
            raise CIProviderConfigError(
                f"Provider class {provider_class.__name__} must inherit from CIProviderInterface"
            )
        
        # Get provider name from class
        try:
            # Create temporary instance to get provider name
            temp_instance = provider_class(auth_manager=None, config={})
            provider_name = temp_instance.provider_name
        except Exception as e:
            raise CIProviderConfigError(
                f"Failed to get provider name from {provider_class.__name__}: {e}"
            )
        
        # Check for duplicate registration
        if provider_name in self._providers:
            self.logger.warning(f"Overriding existing provider: {provider_name}")
        
        # Register provider
        self._providers[provider_name] = provider_class
        self._provider_metadata[provider_name] = metadata or {}
        
        self.logger.info(f"Registered CI provider: {provider_name}")
    
    def unregister(self, provider_name: str) -> None:
        """
        Unregister a CI provider.
        
        Args:
            provider_name: Name of provider to unregister
        """
        if provider_name in self._providers:
            del self._providers[provider_name]
            del self._provider_metadata[provider_name]
            self.logger.info(f"Unregistered CI provider: {provider_name}")
    
    def get_provider_class(self, provider_name: str) -> Optional[Type[CIProviderInterface]]:
        """
        Get provider class by name.
        
        Args:
            provider_name: Name of provider
            
        Returns:
            Provider class or None if not found
        """
        return self._providers.get(provider_name)
    
    def list_providers(self) -> List[str]:
        """
        Get list of registered provider names.
        
        Returns:
            List of provider names
        """
        return list(self._providers.keys())
    
    def get_provider_metadata(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a provider.
        
        Args:
            provider_name: Name of provider
            
        Returns:
            Provider metadata or None if not found
        """
        return self._provider_metadata.get(provider_name)
    
    def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for all registered providers.
        
        Returns:
            Dictionary mapping provider names to metadata
        """
        return self._provider_metadata.copy()
    
    def is_registered(self, provider_name: str) -> bool:
        """
        Check if a provider is registered.
        
        Args:
            provider_name: Name of provider
            
        Returns:
            True if provider is registered
        """
        return provider_name in self._providers
    
    def clear(self) -> None:
        """Clear all registered providers."""
        self._providers.clear()
        self._provider_metadata.clear()
        self.logger.info("Cleared all registered providers")


class CIProviderFactory:
    """
    Factory for creating CI provider instances.
    
    This class handles the creation and configuration of CI provider instances
    based on the registry and provided configuration.
    """
    
    def __init__(self, registry: CIProviderRegistry):
        """
        Initialize the provider factory.
        
        Args:
            registry: Provider registry instance
        """
        self.registry = registry
        self.logger = logging.getLogger("prs.ci_tools.factory")
    
    def create_provider(self, provider_name: str, auth_manager,
                       config: Optional[Dict[str, Any]] = None) -> CIProviderInterface:
        """
        Create a CI provider instance.
        
        Args:
            provider_name: Name of provider to create
            auth_manager: Authentication manager instance
            config: Optional provider configuration
            
        Returns:
            Provider instance
            
        Raises:
            CIProviderConfigError: If provider cannot be created
        """
        provider_class = self.registry.get_provider_class(provider_name)
        if not provider_class:
            raise CIProviderConfigError(f"Unknown provider: {provider_name}")
        
        try:
            provider = provider_class(auth_manager=auth_manager, config=config)
            self.logger.info(f"Created provider instance: {provider_name}")
            return provider
        except Exception as e:
            raise CIProviderConfigError(
                f"Failed to create provider {provider_name}: {e}"
            )
    
    def create_providers(self, provider_names: List[str], auth_manager,
                        configs: Optional[Dict[str, Dict[str, Any]]] = None) -> List[CIProviderInterface]:
        """
        Create multiple provider instances.
        
        Args:
            provider_names: List of provider names to create
            auth_manager: Authentication manager instance
            configs: Optional provider configurations
            
        Returns:
            List of provider instances
            
        Raises:
            CIProviderConfigError: If any provider cannot be created
        """
        providers = []
        configs = configs or {}
        
        for provider_name in provider_names:
            provider_config = configs.get(provider_name)
            provider = self.create_provider(provider_name, auth_manager, provider_config)
            providers.append(provider)
        
        return providers
    
    def create_all_providers(self, auth_manager,
                           configs: Optional[Dict[str, Dict[str, Any]]] = None) -> List[CIProviderInterface]:
        """
        Create instances of all registered providers.
        
        Args:
            auth_manager: Authentication manager instance
            configs: Optional provider configurations
            
        Returns:
            List of all provider instances
        """
        provider_names = self.registry.list_providers()
        return self.create_providers(provider_names, auth_manager, configs)
    
    def get_available_providers(self) -> List[str]:
        """
        Get list of available provider names.
        
        Returns:
            List of provider names
        """
        return self.registry.list_providers()
    
    def validate_provider_config(self, provider_name: str, 
                                config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate provider configuration.
        
        Args:
            provider_name: Name of provider
            config: Configuration to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        provider_class = self.registry.get_provider_class(provider_name)
        if not provider_class:
            return False, f"Unknown provider: {provider_name}"
        
        try:
            # Try to create instance with config
            provider = provider_class(auth_manager=None, config=config)
            return True, None
        except Exception as e:
            return False, str(e)


# Global registry instance
provider_registry = CIProviderRegistry()
provider_factory = CIProviderFactory(provider_registry)