"""
CI Manager for PRS.

This module manages multiple CI providers and provides a unified interface
for retrieving CI data.
"""

from typing import Dict, List, Optional, Any
from .base import BaseCIProvider, CIData
from .github_actions import GitHubActionsProvider
from prs.config import get_ci_platform_config


class CIManager:
    """Manages multiple CI providers and provides unified CI data access."""
    
    def __init__(self):
        self.providers: Dict[str, BaseCIProvider] = {}
        self.default_provider: Optional[str] = None
        
    def register_provider(self, name: str, provider: BaseCIProvider):
        """Register a CI provider."""
        self.providers[name] = provider
        
        # Set as default if it's the first available provider
        if not self.default_provider and provider.is_available():
            self.default_provider = name
    
    def get_provider(self, name: str) -> Optional[BaseCIProvider]:
        """Get a specific CI provider by name."""
        return self.providers.get(name)
    
    def get_available_providers(self) -> List[str]:
        """Get list of available CI provider names."""
        return [name for name, provider in self.providers.items() 
                if provider.is_available()]
    
    def get_ci_data(self, repository: str, pr_number: int, 
                   provider_name: Optional[str] = None) -> Optional[CIData]:
        """
        Get CI data for a PR from a specific provider or the default provider.
        
        Args:
            repository: Repository name in format "owner/repo"
            pr_number: Pull request number
            provider_name: Specific provider name, uses default if None
            
        Returns:
            CIData object or None if no data available
        """
        # Use specified provider or default
        target_provider = provider_name or self.default_provider
        
        if not target_provider or target_provider not in self.providers:
            return None
            
        provider = self.providers[target_provider]
        if not provider.is_available():
            return None
            
        return provider.get_ci_data(repository, pr_number)
    
    def get_aggregated_ci_data(self, repository: str, pr_number: int) -> Dict[str, CIData]:
        """
        Get CI data from all available providers.
        
        Args:
            repository: Repository name in format "owner/repo"
            pr_number: Pull request number
            
        Returns:
            Dictionary mapping provider names to CIData objects
        """
        results = {}
        
        for name, provider in self.providers.items():
            if provider.is_available():
                data = provider.get_ci_data(repository, pr_number)
                if data:
                    results[name] = data
                    
        return results
    
    def get_workflow_logs(self, repository: str, workflow_id: str, 
                         provider_name: Optional[str] = None) -> Optional[str]:
        """Get workflow logs from a specific provider."""
        target_provider = provider_name or self.default_provider
        
        if not target_provider or target_provider not in self.providers:
            return None
            
        provider = self.providers[target_provider]
        if not provider.is_available():
            return None
            
        return provider.get_workflow_logs(repository, workflow_id)
    
    def initialize_default_providers(self):
        """Initialize and register default CI providers."""
        # GitHub Actions
        github_config = get_ci_platform_config('github_actions')
        if github_config.get('has_env_token'):
            github_provider = GitHubActionsProvider(github_config)
            self.register_provider('github_actions', github_provider)
    
    def get_status_summary(self, repository: str, pr_number: int) -> Dict[str, Any]:
        """
        Get a summary of CI status from all providers.
        
        Args:
            repository: Repository name in format "owner/repo"
            pr_number: Pull request number
            
        Returns:
            Dictionary with summary information
        """
        all_data = self.get_aggregated_ci_data(repository, pr_number)
        
        if not all_data:
            return {
                'status': 'unknown',
                'providers': [],
                'total_workflows': 0,
                'successful_workflows': 0,
                'failed_workflows': 0,
                'pending_workflows': 0
            }
        
        # Aggregate statistics
        total_workflows = sum(data.total_workflows for data in all_data.values())
        successful_workflows = sum(data.successful_workflows for data in all_data.values())
        failed_workflows = sum(data.failed_workflows for data in all_data.values())
        pending_workflows = sum(data.pending_workflows for data in all_data.values())
        
        # Determine overall status
        if failed_workflows > 0:
            status = 'failure'
        elif pending_workflows > 0:
            status = 'pending'
        elif successful_workflows > 0:
            status = 'success'
        else:
            status = 'unknown'
        
        return {
            'status': status,
            'providers': list(all_data.keys()),
            'total_workflows': total_workflows,
            'successful_workflows': successful_workflows,
            'failed_workflows': failed_workflows,
            'pending_workflows': pending_workflows,
            'provider_data': all_data
        }
    
    def format_ci_display(self, repository: str, pr_number: int, 
                         verbosity: str = "normal") -> str:
        """
        Format CI information for display.
        
        Args:
            repository: Repository name in format "owner/repo"
            pr_number: Pull request number
            verbosity: Display verbosity level (short, normal, long)
            
        Returns:
            Formatted string for display
        """
        all_data = self.get_aggregated_ci_data(repository, pr_number)
        
        if not all_data:
            if verbosity == "short":
                return "○ No CI"
            else:
                return "No CI/CD data available"
        
        display_lines = []
        
        for provider_name, data in all_data.items():
            provider = self.providers[provider_name]
            
            if verbosity == "short":
                # Short format - just show summary
                if hasattr(provider, 'get_workflow_summary'):
                    summary = provider.get_workflow_summary(data.workflows)
                    display_lines.append(f"{summary['emoji']} {summary['text']}")
                else:
                    # Fallback summary
                    if data.failed_workflows > 0:
                        display_lines.append(f"❌ {data.failed_workflows} failed")
                    elif data.pending_workflows > 0:
                        display_lines.append(f"🟡 {data.pending_workflows} pending")
                    elif data.successful_workflows > 0:
                        display_lines.append(f"✅ {data.successful_workflows} passed")
                    else:
                        display_lines.append("○ No workflows")
            
            elif verbosity == "normal":
                # Normal format - show provider name and summary
                provider_display = provider.get_display_name()
                if hasattr(provider, 'get_workflow_details'):
                    details = provider.get_workflow_details(data.workflows, "normal")
                    display_lines.append(f"{provider_display}:")
                    display_lines.append(f"  {details}")
                else:
                    # Fallback details
                    display_lines.append(f"{provider_display}: {data.total_workflows} workflows")
            
            elif verbosity == "long":
                # Long format - show detailed information
                provider_display = provider.get_display_name()
                display_lines.append(f"{provider_display}:")
                
                if hasattr(provider, 'get_workflow_details'):
                    details = provider.get_workflow_details(data.workflows, "long")
                    # Indent the details
                    indented_details = "\n".join(f"  {line}" for line in details.split("\n"))
                    display_lines.append(indented_details)
                else:
                    # Fallback detailed view
                    display_lines.append(f"  Total workflows: {data.total_workflows}")
                    display_lines.append(f"  Successful: {data.successful_workflows}")
                    display_lines.append(f"  Failed: {data.failed_workflows}")
                    display_lines.append(f"  Pending: {data.pending_workflows}")
        
        return "\n".join(display_lines)


# Global CI manager instance
_ci_manager = None


def get_ci_manager() -> CIManager:
    """Get the global CI manager instance."""
    global _ci_manager
    if _ci_manager is None:
        _ci_manager = CIManager()
        _ci_manager.initialize_default_providers()
    return _ci_manager