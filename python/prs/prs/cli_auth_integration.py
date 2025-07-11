"""
CLI Authentication Integration

This module provides CLI commands for managing CI authentication
within the PRS tool.
"""

import argparse
import sys
from typing import Optional

from .ci_tools.auth import CIAuthManager
from .config import get_storage_dir, should_use_keyring


def add_auth_commands(parser: argparse.ArgumentParser) -> None:
    """
    Add authentication-related commands to the CLI parser.
    
    Args:
        parser: The main argument parser
    """
    # Create auth subcommand group
    auth_group = parser.add_argument_group('authentication', 'CI authentication commands')
    
    # Auth status command
    auth_group.add_argument(
        '--auth-status',
        metavar='PLATFORM',
        nargs='?',
        const='all',
        help='Show authentication status for platform(s)'
    )
    
    # Auth setup command
    auth_group.add_argument(
        '--auth-setup',
        metavar='PLATFORM',
        help='Setup authentication for CI platform'
    )
    
    # Auth method selection
    auth_group.add_argument(
        '--auth-method',
        choices=['api_key', 'sso'],
        help='Authentication method to use (for --auth-setup)'
    )
    
    # Auth logout command
    auth_group.add_argument(
        '--auth-logout',
        metavar='PLATFORM',
        help='Logout from CI platform'
    )
    
    # Auth health check
    auth_group.add_argument(
        '--auth-health',
        action='store_true',
        help='Perform authentication system health check'
    )
    
    # Auth storage info
    auth_group.add_argument(
        '--auth-storage-info',
        action='store_true',
        help='Show token storage information'
    )


def handle_auth_commands(args: argparse.Namespace) -> bool:
    """
    Handle authentication-related CLI commands.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        True if an auth command was handled, False otherwise
    """
    # Check if any auth command was provided
    auth_commands = [
        'auth_status', 'auth_setup', 'auth_logout', 
        'auth_health', 'auth_storage_info'
    ]
    
    if not any(getattr(args, cmd, None) for cmd in auth_commands):
        return False
    
    # Initialize auth manager
    storage_dir = get_storage_dir() if should_use_keyring() else None
    auth_manager = CIAuthManager(storage_dir)
    
    # Handle specific commands
    if args.auth_status:
        handle_auth_status(auth_manager, args.auth_status)
    elif args.auth_setup:
        handle_auth_setup(auth_manager, args.auth_setup, args.auth_method)
    elif args.auth_logout:
        handle_auth_logout(auth_manager, args.auth_logout)
    elif args.auth_health:
        handle_auth_health(auth_manager)
    elif args.auth_storage_info:
        handle_auth_storage_info(auth_manager)
    
    return True


def handle_auth_status(auth_manager: CIAuthManager, platform: str) -> None:
    """Handle auth status command."""
    print("PRS CI Authentication Status")
    print("=" * 30)
    
    if platform == 'all':
        all_status = auth_manager.get_all_auth_status()
        for plat, status in all_status.items():
            print_platform_status(plat, status)
    else:
        if platform not in auth_manager.list_supported_platforms():
            print(f"Error: Platform '{platform}' is not supported")
            print(f"Supported platforms: {', '.join(auth_manager.list_supported_platforms())}")
            sys.exit(1)
        
        status = auth_manager.get_auth_status(platform)
        print_platform_status(platform, status)


def print_platform_status(platform: str, status: dict) -> None:
    """Print status for a single platform."""
    print(f"\n{platform.upper()}:")
    print(f"  Supported: {'Yes' if status['supported'] else 'No'}")
    
    if not status['supported']:
        if 'error' in status:
            print(f"  Error: {status['error']}")
        return
    
    print(f"  Authenticated: {'Yes' if status['authenticated'] else 'No'}")
    
    if status['authenticated']:
        print(f"  Method: {status['auth_method']}")
        print(f"  Token type: {status.get('token_type', 'unknown')}")
        
        if 'expires_at' in status and status['expires_at']:
            print(f"  Expires: {status['expires_at']}")
        if 'stored_at' in status and status['stored_at']:
            print(f"  Stored: {status['stored_at']}")
        if 'is_expired' in status:
            print(f"  Expired: {'Yes' if status['is_expired'] else 'No'}")
    else:
        print(f"  Environment variable: {status.get('env_var', 'N/A')}")
        print(f"  Supports SSO: {'Yes' if status.get('supports_sso') else 'No'}")
        print(f"  Supports API Key: {'Yes' if status.get('supports_api_key') else 'No'}")


def handle_auth_setup(auth_manager: CIAuthManager, platform: str, method: Optional[str]) -> None:
    """Handle auth setup command."""
    print(f"Setting up authentication for {platform}...")
    
    if platform not in auth_manager.list_supported_platforms():
        print(f"Error: Platform '{platform}' is not supported")
        print(f"Supported platforms: {', '.join(auth_manager.list_supported_platforms())}")
        sys.exit(1)
    
    success = auth_manager.setup_interactive_auth(platform, method)
    
    if success:
        print(f"\nAuthentication setup successful for {platform}!")
        
        # Show final status
        status = auth_manager.get_auth_status(platform)
        print(f"Method: {status['auth_method']}")
        print(f"Token type: {status.get('token_type', 'unknown')}")
        
        # Test token
        token = auth_manager.get_valid_token(platform)
        if token:
            print("Token validation: SUCCESS")
        else:
            print("Token validation: FAILED")
    else:
        print(f"\nAuthentication setup failed for {platform}")
        sys.exit(1)


def handle_auth_logout(auth_manager: CIAuthManager, platform: str) -> None:
    """Handle auth logout command."""
    if platform == 'all':
        print("Logging out from all platforms...")
        auth_manager.logout_all()
        print("Logged out from all platforms")
    else:
        if platform not in auth_manager.list_supported_platforms():
            print(f"Error: Platform '{platform}' is not supported")
            print(f"Supported platforms: {', '.join(auth_manager.list_supported_platforms())}")
            sys.exit(1)
        
        print(f"Logging out from {platform}...")
        auth_manager.logout(platform)
        print(f"Logged out from {platform}")


def handle_auth_health(auth_manager: CIAuthManager) -> None:
    """Handle auth health check command."""
    print("PRS CI Authentication Health Check")
    print("=" * 35)
    
    health = auth_manager.health_check()
    
    print(f"Overall Status: {health['overall_status'].upper()}")
    
    # Storage info
    storage = health['storage_info']
    print(f"\nStorage:")
    print(f"  Keyring available: {'Yes' if storage['keyring_available'] else 'No'}")
    print(f"  Encryption available: {'Yes' if storage['encryption_available'] else 'No'}")
    print(f"  Using keyring: {'Yes' if storage['using_keyring'] else 'No'}")
    print(f"  Storage directory: {storage['storage_dir']}")
    
    # Platform status
    print(f"\nPlatform Status:")
    for platform, status in health['platforms'].items():
        auth_status = "✓" if status['authenticated'] else "✗"
        print(f"  {platform}: {auth_status}")
    
    # Issues
    if health['issues']:
        print(f"\nIssues:")
        for issue in health['issues']:
            print(f"  - {issue}")
    else:
        print(f"\nNo issues found.")


def handle_auth_storage_info(auth_manager: CIAuthManager) -> None:
    """Handle auth storage info command."""
    print("PRS CI Authentication Storage Information")
    print("=" * 42)
    
    storage_info = auth_manager.get_storage_info()
    
    print(f"Keyring available: {'Yes' if storage_info['keyring_available'] else 'No'}")
    print(f"Encryption available: {'Yes' if storage_info['encryption_available'] else 'No'}")
    print(f"Using keyring: {'Yes' if storage_info['using_keyring'] else 'No'}")
    print(f"Storage directory: {storage_info['storage_dir']}")
    
    if storage_info['tokens_file']:
        print(f"Tokens file: {storage_info['tokens_file']}")
    else:
        print("Tokens file: Not created")
    
    # List stored providers
    providers = auth_manager.token_storage.list_providers()
    if providers:
        print(f"\nStored tokens for providers:")
        for provider in providers:
            print(f"  - {provider}")
    else:
        print(f"\nNo stored tokens found")


def get_ci_auth_manager() -> CIAuthManager:
    """
    Get initialized CI authentication manager.
    
    Returns:
        CIAuthManager instance
    """
    storage_dir = get_storage_dir() if should_use_keyring() else None
    return CIAuthManager(storage_dir)


def ensure_ci_authentication(platform: str) -> Optional[str]:
    """
    Ensure CI authentication for platform, prompting if necessary.
    
    Args:
        platform: Platform name
        
    Returns:
        Valid token or None if authentication failed
    """
    auth_manager = get_ci_auth_manager()
    
    # Check if already authenticated
    token = auth_manager.get_valid_token(platform)
    if token:
        return token
    
    # Check if platform is supported
    if platform not in auth_manager.list_supported_platforms():
        print(f"Error: Platform '{platform}' is not supported")
        return None
    
    # Prompt for authentication
    print(f"Authentication required for {platform}")
    setup_auth = input("Setup authentication now? (y/n): ").strip().lower()
    
    if setup_auth in ['y', 'yes']:
        success = auth_manager.setup_interactive_auth(platform)
        if success:
            return auth_manager.get_valid_token(platform)
    
    return None