"""
CI Authentication Manager

Main authentication manager that coordinates different authentication methods
for CI platforms including API keys, SSO portal, and token management.
"""

import os
from typing import Optional, Dict, Any, List
from pathlib import Path

from .token_storage import TokenStorage
from .sso_portal import SSOPortalAuth


class CIAuthManager:
    """
    Main authentication manager for CI platforms.
    
    Coordinates different authentication methods and provides a unified
    interface for authenticating with various CI platforms.
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize CI authentication manager.
        
        Args:
            storage_dir: Directory for token storage (defaults to ~/.prs/tokens)
        """
        self.token_storage = TokenStorage(storage_dir)
        self.sso_auths: Dict[str, SSOPortalAuth] = {}
        
        # Supported CI platforms
        self.supported_platforms = {
            'buildkite': {
                'name': 'Buildkite',
                'base_url': 'https://buildkite.com',
                'env_var': 'BUILDKITE_API_KEY',
                'supports_sso': True,
                'supports_api_key': True
            },
            'github_actions': {
                'name': 'GitHub Actions',
                'base_url': 'https://api.github.com',
                'env_var': 'GITHUB_TOKEN',
                'supports_sso': False,
                'supports_api_key': True
            },
            'gitlab_ci': {
                'name': 'GitLab CI',
                'base_url': 'https://gitlab.com',
                'env_var': 'GITLAB_TOKEN',
                'supports_sso': False,
                'supports_api_key': True
            },
            'jenkins': {
                'name': 'Jenkins',
                'base_url': '',  # Will be configured per instance
                'env_var': 'JENKINS_API_KEY',
                'supports_sso': False,
                'supports_api_key': True
            }
        }
    
    def get_platform_info(self, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get platform information.
        
        Args:
            platform: Platform name
            
        Returns:
            Platform information or None if not supported
        """
        return self.supported_platforms.get(platform)
    
    def list_supported_platforms(self) -> List[str]:
        """Get list of supported platforms."""
        return list(self.supported_platforms.keys())
    
    def _get_sso_auth(self, platform: str, base_url: Optional[str] = None) -> Optional[SSOPortalAuth]:
        """
        Get SSO authentication instance for platform.
        
        Args:
            platform: Platform name
            base_url: Optional custom base URL
            
        Returns:
            SSOPortalAuth instance or None if not supported
        """
        platform_info = self.get_platform_info(platform)
        if not platform_info or not platform_info['supports_sso']:
            return None
        
        if platform not in self.sso_auths:
            url = base_url or platform_info['base_url']
            self.sso_auths[platform] = SSOPortalAuth(
                provider=platform,
                base_url=url,
                token_storage=self.token_storage
            )
        
        return self.sso_auths[platform]
    
    def authenticate_with_env_var(self, platform: str) -> Optional[str]:
        """
        Authenticate using environment variable.
        
        Args:
            platform: Platform name
            
        Returns:
            Token from environment variable or None
        """
        platform_info = self.get_platform_info(platform)
        if not platform_info:
            return None
        
        env_var = platform_info['env_var']
        token = os.getenv(env_var)
        
        if token:
            # Store token for future use
            self.token_storage.store_token(
                provider=platform,
                token=token,
                token_type='api_key'
            )
        
        return token
    
    def authenticate_with_api_key(self, platform: str, api_key: str) -> bool:
        """
        Authenticate using API key.
        
        Args:
            platform: Platform name
            api_key: API key
            
        Returns:
            True if authentication successful
        """
        platform_info = self.get_platform_info(platform)
        if not platform_info or not platform_info['supports_api_key']:
            return False
        
        # Store API key
        self.token_storage.store_token(
            provider=platform,
            token=api_key,
            token_type='api_key'
        )
        
        return True
    
    def authenticate_with_sso(self, platform: str, base_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Authenticate using SSO portal.
        
        Args:
            platform: Platform name
            base_url: Optional custom base URL
            
        Returns:
            Token data or None if failed
        """
        sso_auth = self._get_sso_auth(platform, base_url)
        if not sso_auth:
            return None
        
        return sso_auth.authenticate_interactive()
    
    def get_valid_token(self, platform: str) -> Optional[str]:
        """
        Get a valid authentication token for platform.
        
        Tries multiple authentication methods in order:
        1. Environment variable
        2. Stored API key
        3. Stored SSO token (with refresh if needed)
        
        Args:
            platform: Platform name
            
        Returns:
            Valid token or None
        """
        # Try environment variable first
        env_token = self.authenticate_with_env_var(platform)
        if env_token:
            return env_token
        
        # Try stored API key
        token_data = self.token_storage.get_token(platform, 'api_key')
        if token_data:
            return token_data['token']
        
        # Try SSO token
        sso_auth = self._get_sso_auth(platform)
        if sso_auth:
            return sso_auth.get_valid_token()
        
        return None
    
    def is_authenticated(self, platform: str) -> bool:
        """
        Check if authenticated for platform.
        
        Args:
            platform: Platform name
            
        Returns:
            True if authenticated
        """
        return self.get_valid_token(platform) is not None
    
    def validate_token(self, platform: str) -> bool:
        """
        Validate stored token for platform.
        
        Args:
            platform: Platform name
            
        Returns:
            True if token is valid
        """
        # Check environment variable
        platform_info = self.get_platform_info(platform)
        if platform_info:
            env_token = os.getenv(platform_info['env_var'])
            if env_token:
                return True  # Assume env tokens are valid
        
        # Check stored API key
        token_data = self.token_storage.get_token(platform, 'api_key')
        if token_data:
            return True  # API keys don't typically expire
        
        # Check SSO token
        sso_auth = self._get_sso_auth(platform)
        if sso_auth:
            return sso_auth.validate_stored_token()
        
        return False
    
    def refresh_token(self, platform: str) -> bool:
        """
        Refresh token for platform if possible.
        
        Args:
            platform: Platform name
            
        Returns:
            True if token was refreshed
        """
        sso_auth = self._get_sso_auth(platform)
        if not sso_auth:
            return False
        
        token_data = self.token_storage.get_token(platform, 'access')
        if not token_data or not token_data.get('refresh_token'):
            return False
        
        new_token_data = sso_auth.refresh_token(token_data['refresh_token'])
        return new_token_data is not None
    
    def logout(self, platform: str) -> None:
        """
        Logout from platform (clear stored tokens).
        
        Args:
            platform: Platform name
        """
        self.token_storage.clear_provider_tokens(platform)
        
        # Clear SSO auth instance
        if platform in self.sso_auths:
            del self.sso_auths[platform]
    
    def logout_all(self) -> None:
        """Logout from all platforms."""
        for platform in self.list_supported_platforms():
            self.logout(platform)
    
    def get_auth_status(self, platform: str) -> Dict[str, Any]:
        """
        Get authentication status for platform.
        
        Args:
            platform: Platform name
            
        Returns:
            Authentication status information
        """
        platform_info = self.get_platform_info(platform)
        if not platform_info:
            return {
                'platform': platform,
                'supported': False,
                'authenticated': False,
                'error': 'Platform not supported'
            }
        
        # Check environment variable
        env_token = os.getenv(platform_info['env_var'])
        if env_token:
            return {
                'platform': platform,
                'supported': True,
                'authenticated': True,
                'auth_method': 'environment_variable',
                'env_var': platform_info['env_var'],
                'token_type': 'api_key'
            }
        
        # Check stored API key
        api_key_data = self.token_storage.get_token(platform, 'api_key')
        if api_key_data:
            return {
                'platform': platform,
                'supported': True,
                'authenticated': True,
                'auth_method': 'stored_api_key',
                'token_type': 'api_key',
                'stored_at': api_key_data.get('stored_at')
            }
        
        # Check SSO token
        sso_auth = self._get_sso_auth(platform)
        if sso_auth:
            sso_status = sso_auth.get_auth_status()
            if sso_status['authenticated']:
                return {
                    'platform': platform,
                    'supported': True,
                    'authenticated': True,
                    'auth_method': 'sso_portal',
                    **sso_status
                }
        
        return {
            'platform': platform,
            'supported': True,
            'authenticated': False,
            'auth_method': None,
            'supports_sso': platform_info['supports_sso'],
            'supports_api_key': platform_info['supports_api_key'],
            'env_var': platform_info['env_var']
        }
    
    def get_all_auth_status(self) -> Dict[str, Dict[str, Any]]:
        """Get authentication status for all platforms."""
        return {
            platform: self.get_auth_status(platform)
            for platform in self.list_supported_platforms()
        }
    
    def setup_interactive_auth(self, platform: str, method: Optional[str] = None) -> bool:
        """
        Setup authentication interactively.
        
        Args:
            platform: Platform name
            method: Authentication method ('api_key', 'sso', or None for auto)
            
        Returns:
            True if authentication setup successful
        """
        platform_info = self.get_platform_info(platform)
        if not platform_info:
            print(f"Platform '{platform}' is not supported.")
            return False
        
        print(f"Setting up authentication for {platform_info['name']}...")
        print()
        
        # Check current status
        current_status = self.get_auth_status(platform)
        if current_status['authenticated']:
            print(f"Already authenticated via {current_status['auth_method']}")
            overwrite = input("Overwrite existing authentication? (y/n): ").strip().lower()
            if overwrite not in ['y', 'yes']:
                return True
        
        # Determine authentication method
        if method is None:
            print("Available authentication methods:")
            methods = []
            
            if platform_info['supports_api_key']:
                methods.append("1. API Key")
            if platform_info['supports_sso']:
                methods.append("2. SSO Portal")
            
            for method_option in methods:
                print(f"  {method_option}")
            
            print()
            choice = input("Choose authentication method (1 or 2): ").strip()
            
            if choice == "1" and platform_info['supports_api_key']:
                method = "api_key"
            elif choice == "2" and platform_info['supports_sso']:
                method = "sso"
            else:
                print("Invalid choice.")
                return False
        
        # Perform authentication
        if method == "api_key":
            return self._setup_api_key_auth(platform, platform_info)
        elif method == "sso":
            return self._setup_sso_auth(platform, platform_info)
        else:
            print(f"Authentication method '{method}' not supported for {platform}")
            return False
    
    def _setup_api_key_auth(self, platform: str, platform_info: Dict[str, Any]) -> bool:
        """Setup API key authentication."""
        print(f"Setting up API key authentication for {platform_info['name']}...")
        print()
        
        # Check environment variable
        env_var = platform_info['env_var']
        env_token = os.getenv(env_var)
        
        if env_token:
            print(f"Found {env_var} environment variable.")
            use_env = input("Use environment variable? (y/n): ").strip().lower()
            if use_env in ['y', 'yes']:
                return self.authenticate_with_env_var(platform) is not None
        
        # Manual API key entry
        print(f"Please enter your {platform_info['name']} API key:")
        api_key = input("API Key: ").strip()
        
        if not api_key:
            print("No API key provided.")
            return False
        
        success = self.authenticate_with_api_key(platform, api_key)
        if success:
            print("API key authentication setup successful!")
        else:
            print("Failed to setup API key authentication.")
        
        return success
    
    def _setup_sso_auth(self, platform: str, platform_info: Dict[str, Any]) -> bool:
        """Setup SSO authentication."""
        print(f"Setting up SSO authentication for {platform_info['name']}...")
        print()
        
        # Custom base URL for platforms that need it
        base_url = None
        if platform == 'jenkins':
            base_url = input("Enter Jenkins base URL: ").strip()
            if not base_url:
                print("Jenkins base URL is required.")
                return False
        
        token_data = self.authenticate_with_sso(platform, base_url)
        return token_data is not None
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get token storage information."""
        return self.token_storage.get_storage_info()
    
    def cleanup_expired_tokens(self) -> None:
        """Clean up expired tokens from storage."""
        providers = self.token_storage.list_providers()
        
        for provider in providers:
            # Check access tokens
            token_data = self.token_storage.get_token(provider, 'access')
            if token_data and self.token_storage.is_token_expired(token_data):
                # Try to refresh first
                if not self.refresh_token(provider):
                    # Delete if refresh failed
                    self.token_storage.delete_token(provider, 'access')
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on authentication system.
        
        Returns:
            Health check results
        """
        health = {
            'overall_status': 'healthy',
            'storage_info': self.get_storage_info(),
            'platforms': {},
            'issues': []
        }
        
        # Check each platform
        for platform in self.list_supported_platforms():
            platform_status = self.get_auth_status(platform)
            health['platforms'][platform] = platform_status
            
            if platform_status['authenticated']:
                # Validate token
                if not self.validate_token(platform):
                    health['issues'].append(f"{platform}: Token validation failed")
                    health['overall_status'] = 'warning'
        
        # Check for expired tokens
        self.cleanup_expired_tokens()
        
        return health