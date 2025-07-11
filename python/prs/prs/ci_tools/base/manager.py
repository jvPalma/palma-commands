"""
CI Manager System

This module provides the CIManager class that orchestrates multiple CI providers,
handles authentication, health monitoring, and provides a unified interface for
accessing CI/CD information across different platforms.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import RLock

from .provider import CIProviderInterface, CIProviderError, CIProviderAuthError, provider_factory
from .models import CIBuild, CIPipeline, CICheck, CIAggregatedMetrics
from .enums import CIProvider, BuildStatus
from ..auth.auth_manager import CIAuthManager


class CIManagerError(Exception):
    """Base exception for CI manager errors."""
    pass


class CIManager:
    """
    CI Manager for orchestrating multiple CI providers.
    
    This class provides a unified interface for accessing CI/CD information
    across multiple providers, handles authentication, health monitoring,
    and provides fallback mechanisms for failed providers.
    """
    
    def __init__(self, auth_manager: Optional[CIAuthManager] = None,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize CI manager.
        
        Args:
            auth_manager: Authentication manager instance
            config: Optional configuration dictionary
        """
        self.auth_manager = auth_manager or CIAuthManager()
        self.config = config or {}
        self.logger = logging.getLogger("prs.ci_tools.manager")
        
        # Provider management
        self._providers: Dict[str, CIProviderInterface] = {}
        self._provider_health: Dict[str, Dict[str, Any]] = {}
        self._provider_lock = RLock()
        
        # Configuration
        self._health_check_interval = self.config.get('health_check_interval', 300)  # 5 minutes
        self._max_concurrent_requests = self.config.get('max_concurrent_requests', 5)
        self._request_timeout = self.config.get('request_timeout', 30)
        self._fallback_enabled = self.config.get('fallback_enabled', True)
        self._cache_enabled = self.config.get('cache_enabled', True)
        
        # Runtime state
        self._last_health_check = {}
        self._initialized = False
        self._executor = ThreadPoolExecutor(max_workers=self._max_concurrent_requests)
        
        # Performance metrics
        self._metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'fallback_requests': 0,
            'avg_response_time': 0.0,
            'provider_usage': {}
        }
    
    def initialize(self, provider_names: Optional[List[str]] = None,
                  provider_configs: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        """
        Initialize the CI manager with providers.
        
        Args:
            provider_names: List of provider names to initialize (default: all available)
            provider_configs: Optional provider-specific configurations
        """
        if self._initialized:
            self.logger.warning("CI manager already initialized")
            return
        
        provider_configs = provider_configs or {}
        
        # Use all available providers if none specified
        if provider_names is None:
            provider_names = provider_factory.get_available_providers()
        
        # Initialize providers
        for provider_name in provider_names:
            try:
                provider_config = provider_configs.get(provider_name, {})
                provider = provider_factory.create_provider(
                    provider_name, self.auth_manager, provider_config
                )
                
                with self._provider_lock:
                    self._providers[provider_name] = provider
                    self._provider_health[provider_name] = {
                        'status': 'unknown',
                        'last_check': None,
                        'consecutive_failures': 0,
                        'total_requests': 0,
                        'successful_requests': 0,
                        'failed_requests': 0,
                        'avg_response_time': 0.0
                    }
                
                self.logger.info(f"Initialized provider: {provider_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize provider {provider_name}: {e}")
        
        self._initialized = True
        self.logger.info(f"CI manager initialized with {len(self._providers)} providers")
        
        # Perform initial health check
        self.health_check_all()
    
    def add_provider(self, provider_name: str, 
                    provider_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a new provider to the manager.
        
        Args:
            provider_name: Name of provider to add
            provider_config: Optional provider configuration
            
        Returns:
            True if provider was added successfully
        """
        if not self._initialized:
            raise CIManagerError("CI manager not initialized")
        
        if provider_name in self._providers:
            self.logger.warning(f"Provider {provider_name} already exists")
            return False
        
        try:
            provider = provider_factory.create_provider(
                provider_name, self.auth_manager, provider_config
            )
            
            with self._provider_lock:
                self._providers[provider_name] = provider
                self._provider_health[provider_name] = {
                    'status': 'unknown',
                    'last_check': None,
                    'consecutive_failures': 0,
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': 0,
                    'avg_response_time': 0.0
                }
            
            self.logger.info(f"Added provider: {provider_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add provider {provider_name}: {e}")
            return False
    
    def remove_provider(self, provider_name: str) -> bool:
        """
        Remove a provider from the manager.
        
        Args:
            provider_name: Name of provider to remove
            
        Returns:
            True if provider was removed successfully
        """
        with self._provider_lock:
            if provider_name in self._providers:
                del self._providers[provider_name]
                del self._provider_health[provider_name]
                self.logger.info(f"Removed provider: {provider_name}")
                return True
        
        return False
    
    def get_provider(self, provider_name: str) -> Optional[CIProviderInterface]:
        """
        Get a provider instance by name.
        
        Args:
            provider_name: Name of provider
            
        Returns:
            Provider instance or None if not found
        """
        return self._providers.get(provider_name)
    
    def list_providers(self) -> List[str]:
        """
        Get list of active provider names.
        
        Returns:
            List of provider names
        """
        return list(self._providers.keys())
    
    def get_healthy_providers(self) -> List[str]:
        """
        Get list of healthy provider names.
        
        Returns:
            List of healthy provider names
        """
        healthy_providers = []
        
        with self._provider_lock:
            for provider_name, health in self._provider_health.items():
                if health['status'] == 'healthy':
                    healthy_providers.append(provider_name)
        
        return healthy_providers
    
    def _execute_with_fallback(self, method_name: str, *args, **kwargs) -> Tuple[Any, str]:
        """
        Execute a method with fallback to healthy providers.
        
        Args:
            method_name: Name of method to execute
            *args: Method arguments
            **kwargs: Method keyword arguments
            
        Returns:
            Tuple of (result, provider_name)
            
        Raises:
            CIManagerError: If all providers fail
        """
        start_time = datetime.now()
        healthy_providers = self.get_healthy_providers()
        
        if not healthy_providers:
            # Try all providers if none are marked as healthy
            healthy_providers = self.list_providers()
        
        if not healthy_providers:
            raise CIManagerError("No providers available")
        
        last_error = None
        
        # Try each provider in order
        for provider_name in healthy_providers:
            try:
                provider = self._providers[provider_name]
                
                # Check if provider supports the method
                if not hasattr(provider, method_name):
                    continue
                
                # Execute method
                method = getattr(provider, method_name)
                result = method(*args, **kwargs)
                
                # Update metrics
                self._update_provider_metrics(provider_name, success=True, 
                                            response_time=(datetime.now() - start_time).total_seconds())
                
                return result, provider_name
                
            except CIProviderAuthError as e:
                self.logger.warning(f"Authentication error for {provider_name}: {e}")
                self._update_provider_health(provider_name, 'unhealthy', str(e))
                last_error = e
                
            except Exception as e:
                self.logger.error(f"Error executing {method_name} on {provider_name}: {e}")
                self._update_provider_metrics(provider_name, success=False)
                last_error = e
        
        # All providers failed
        self._metrics['failed_requests'] += 1
        if last_error:
            raise CIManagerError(f"All providers failed. Last error: {last_error}")
        else:
            raise CIManagerError("All providers failed")
    
    def _update_provider_metrics(self, provider_name: str, success: bool, 
                               response_time: float = 0.0) -> None:
        """
        Update provider metrics.
        
        Args:
            provider_name: Name of provider
            success: Whether the request was successful
            response_time: Response time in seconds
        """
        with self._provider_lock:
            if provider_name not in self._provider_health:
                return
            
            health = self._provider_health[provider_name]
            health['total_requests'] += 1
            
            if success:
                health['successful_requests'] += 1
                health['consecutive_failures'] = 0
                
                # Update average response time
                if health['total_requests'] > 1:
                    health['avg_response_time'] = (
                        (health['avg_response_time'] * (health['total_requests'] - 1) + response_time) /
                        health['total_requests']
                    )
                else:
                    health['avg_response_time'] = response_time
                    
            else:
                health['failed_requests'] += 1
                health['consecutive_failures'] += 1
                
                # Mark as unhealthy if too many consecutive failures
                if health['consecutive_failures'] >= 3:
                    health['status'] = 'unhealthy'
        
        # Update global metrics
        self._metrics['total_requests'] += 1
        if success:
            self._metrics['successful_requests'] += 1
        else:
            self._metrics['failed_requests'] += 1
        
        # Update provider usage
        if provider_name not in self._metrics['provider_usage']:
            self._metrics['provider_usage'][provider_name] = 0
        self._metrics['provider_usage'][provider_name] += 1
    
    def _update_provider_health(self, provider_name: str, status: str, message: str = None) -> None:
        """
        Update provider health status.
        
        Args:
            provider_name: Name of provider
            status: Health status ('healthy', 'unhealthy', 'unknown')
            message: Optional status message
        """
        with self._provider_lock:
            if provider_name in self._provider_health:
                self._provider_health[provider_name]['status'] = status
                self._provider_health[provider_name]['last_check'] = datetime.now()
                if message:
                    self._provider_health[provider_name]['message'] = message
    
    def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform health check on all providers.
        
        Returns:
            Dictionary of provider health statuses
        """
        health_results = {}
        
        if not self._providers:
            return health_results
        
        with ThreadPoolExecutor(max_workers=len(self._providers)) as executor:
            # Submit health checks for all providers
            future_to_provider = {
                executor.submit(self._health_check_provider, provider_name): provider_name
                for provider_name in self._providers.keys()
            }
            
            # Collect results
            for future in as_completed(future_to_provider):
                provider_name = future_to_provider[future]
                try:
                    health_result = future.result(timeout=self._request_timeout)
                    health_results[provider_name] = health_result
                except Exception as e:
                    self.logger.error(f"Health check failed for {provider_name}: {e}")
                    health_results[provider_name] = {
                        'status': 'unhealthy',
                        'message': str(e),
                        'last_check': datetime.now()
                    }
        
        return health_results
    
    def _health_check_provider(self, provider_name: str) -> Dict[str, Any]:
        """
        Perform health check on a specific provider.
        
        Args:
            provider_name: Name of provider
            
        Returns:
            Health check result
        """
        try:
            provider = self._providers[provider_name]
            health_result = provider.health_check()
            
            # Update internal health tracking
            status = 'healthy' if health_result['status'] == 'healthy' else 'unhealthy'
            self._update_provider_health(provider_name, status, 
                                       health_result.get('message'))
            
            return health_result
            
        except Exception as e:
            self.logger.error(f"Health check failed for {provider_name}: {e}")
            self._update_provider_health(provider_name, 'unhealthy', str(e))
            return {
                'status': 'unhealthy',
                'message': str(e),
                'last_check': datetime.now()
            }
    
    def get_pr_checks(self, repo_owner: str, repo_name: str, pr_number: int) -> List[CICheck]:
        """
        Get status checks for a pull request from all providers.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            pr_number: Pull request number
            
        Returns:
            List of CI checks from all providers
        """
        all_checks = []
        
        # Get checks from all healthy providers
        healthy_providers = self.get_healthy_providers()
        
        if not healthy_providers:
            return all_checks
        
        with ThreadPoolExecutor(max_workers=len(healthy_providers)) as executor:
            future_to_provider = {
                executor.submit(self._get_provider_checks, provider_name, 
                              repo_owner, repo_name, pr_number): provider_name
                for provider_name in healthy_providers
            }
            
            for future in as_completed(future_to_provider):
                provider_name = future_to_provider[future]
                try:
                    checks = future.result(timeout=self._request_timeout)
                    all_checks.extend(checks)
                except Exception as e:
                    self.logger.error(f"Failed to get checks from {provider_name}: {e}")
                    self._update_provider_metrics(provider_name, success=False)
        
        return all_checks
    
    def _get_provider_checks(self, provider_name: str, repo_owner: str, 
                           repo_name: str, pr_number: int) -> List[CICheck]:
        """Get checks from a specific provider."""
        provider = self._providers[provider_name]
        return provider.get_pr_checks(repo_owner, repo_name, pr_number)
    
    def get_pr_builds(self, repo_owner: str, repo_name: str, pr_number: int) -> List[CIBuild]:
        """
        Get builds for a pull request from all providers.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            pr_number: Pull request number
            
        Returns:
            List of CI builds from all providers
        """
        all_builds = []
        
        # Get builds from all healthy providers
        healthy_providers = self.get_healthy_providers()
        
        if not healthy_providers:
            return all_builds
        
        with ThreadPoolExecutor(max_workers=len(healthy_providers)) as executor:
            future_to_provider = {
                executor.submit(self._get_provider_builds, provider_name,
                              repo_owner, repo_name, pr_number): provider_name
                for provider_name in healthy_providers
            }
            
            for future in as_completed(future_to_provider):
                provider_name = future_to_provider[future]
                try:
                    builds = future.result(timeout=self._request_timeout)
                    all_builds.extend(builds)
                except Exception as e:
                    self.logger.error(f"Failed to get builds from {provider_name}: {e}")
                    self._update_provider_metrics(provider_name, success=False)
        
        return all_builds
    
    def _get_provider_builds(self, provider_name: str, repo_owner: str,
                           repo_name: str, pr_number: int) -> List[CIBuild]:
        """Get builds from a specific provider."""
        provider = self._providers[provider_name]
        return provider.get_pr_builds(repo_owner, repo_name, pr_number)
    
    def get_build_details(self, build_id: str, provider_name: Optional[str] = None) -> Optional[CIBuild]:
        """
        Get detailed information for a specific build.
        
        Args:
            build_id: Build identifier
            provider_name: Optional specific provider name
            
        Returns:
            Build details or None if not found
        """
        if provider_name:
            # Get from specific provider
            provider = self._providers.get(provider_name)
            if provider:
                try:
                    return provider.get_build_details(build_id)
                except Exception as e:
                    self.logger.error(f"Failed to get build details from {provider_name}: {e}")
            return None
        
        # Try with fallback
        try:
            result, _ = self._execute_with_fallback('get_build_details', build_id)
            return result
        except CIManagerError:
            return None
    
    def get_aggregated_metrics(self, repo_owner: str, repo_name: str, 
                             days: int = 30) -> Optional[CIAggregatedMetrics]:
        """
        Get aggregated metrics for a repository.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            days: Number of days to analyze
            
        Returns:
            Aggregated metrics or None if not available
        """
        try:
            result, _ = self._execute_with_fallback('get_aggregated_metrics', 
                                                  repo_owner, repo_name, days)
            return result
        except CIManagerError:
            return None
    
    def get_manager_status(self) -> Dict[str, Any]:
        """
        Get overall manager status.
        
        Returns:
            Manager status information
        """
        with self._provider_lock:
            return {
                'initialized': self._initialized,
                'total_providers': len(self._providers),
                'healthy_providers': len(self.get_healthy_providers()),
                'provider_health': self._provider_health.copy(),
                'metrics': self._metrics.copy(),
                'config': {
                    'health_check_interval': self._health_check_interval,
                    'max_concurrent_requests': self._max_concurrent_requests,
                    'request_timeout': self._request_timeout,
                    'fallback_enabled': self._fallback_enabled
                }
            }
    
    def get_provider_info(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific provider.
        
        Args:
            provider_name: Name of provider
            
        Returns:
            Provider information or None if not found
        """
        provider = self._providers.get(provider_name)
        if provider:
            info = provider.get_provider_info()
            
            # Add manager-specific metrics
            with self._provider_lock:
                if provider_name in self._provider_health:
                    info['manager_metrics'] = self._provider_health[provider_name].copy()
            
            return info
        
        return None
    
    def shutdown(self) -> None:
        """Shutdown the CI manager and clean up resources."""
        self.logger.info("Shutting down CI manager")
        
        # Shutdown executor
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)
        
        # Clear providers
        with self._provider_lock:
            self._providers.clear()
            self._provider_health.clear()
        
        self._initialized = False
        self.logger.info("CI manager shutdown complete")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()