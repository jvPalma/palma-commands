#!/usr/bin/env python3
"""
Example usage of the CI authentication system.

This script demonstrates how to use the CI authentication system
for authenticating with various CI platforms.
"""

import sys
from pathlib import Path

# Add the prs module to the path
sys.path.insert(0, str(Path(__file__).parent))

from prs.ci_tools.auth import CIAuthManager
from prs.config import get_storage_dir, should_use_keyring


def main():
    """Main function to demonstrate authentication usage."""
    print("PRS CI Authentication System Demo")
    print("=" * 40)
    
    # Initialize authentication manager
    storage_dir = get_storage_dir() if should_use_keyring() else None
    auth_manager = CIAuthManager(storage_dir)
    
    print(f"Storage info: {auth_manager.get_storage_info()}")
    print()
    
    # List supported platforms
    print("Supported CI platforms:")
    platforms = auth_manager.list_supported_platforms()
    for platform in platforms:
        info = auth_manager.get_platform_info(platform)
        print(f"  - {info['name']} ({platform})")
    print()
    
    # Show current authentication status
    print("Current authentication status:")
    all_status = auth_manager.get_all_auth_status()
    for platform, status in all_status.items():
        auth_status = "✓ Authenticated" if status['authenticated'] else "✗ Not authenticated"
        print(f"  {platform}: {auth_status}")
        if status['authenticated']:
            print(f"    Method: {status['auth_method']}")
            if status.get('token_type'):
                print(f"    Token type: {status['token_type']}")
    print()
    
    # Example: Check Buildkite authentication
    print("Buildkite authentication example:")
    buildkite_status = auth_manager.get_auth_status('buildkite')
    print(f"Authenticated: {buildkite_status['authenticated']}")
    
    if buildkite_status['authenticated']:
        token = auth_manager.get_valid_token('buildkite')
        print(f"Valid token available: {bool(token)}")
        if token:
            print(f"Token (first 10 chars): {token[:10]}...")
    else:
        print("To authenticate with Buildkite, run:")
        print("  python example_auth_usage.py --setup-auth buildkite")
    print()
    
    # Health check
    print("Authentication system health check:")
    health = auth_manager.health_check()
    print(f"Overall status: {health['overall_status']}")
    if health['issues']:
        print("Issues found:")
        for issue in health['issues']:
            print(f"  - {issue}")
    print()


def setup_auth(platform: str):
    """Setup authentication for a platform."""
    print(f"Setting up authentication for {platform}...")
    
    auth_manager = CIAuthManager()
    success = auth_manager.setup_interactive_auth(platform)
    
    if success:
        print(f"Authentication setup successful for {platform}!")
        
        # Test the authentication
        token = auth_manager.get_valid_token(platform)
        if token:
            print(f"Token retrieved successfully: {token[:10]}...")
        else:
            print("Warning: Could not retrieve token after setup")
    else:
        print(f"Authentication setup failed for {platform}")


def show_auth_status(platform: str = None):
    """Show authentication status for platform(s)."""
    auth_manager = CIAuthManager()
    
    if platform:
        status = auth_manager.get_auth_status(platform)
        print(f"Authentication status for {platform}:")
        print(f"  Supported: {status['supported']}")
        print(f"  Authenticated: {status['authenticated']}")
        if status['authenticated']:
            print(f"  Method: {status['auth_method']}")
            print(f"  Token type: {status.get('token_type', 'unknown')}")
    else:
        all_status = auth_manager.get_all_auth_status()
        print("Authentication status for all platforms:")
        for plat, status in all_status.items():
            auth_status = "✓" if status['authenticated'] else "✗"
            print(f"  {plat}: {auth_status} {status['auth_method'] if status['authenticated'] else 'Not authenticated'}")


def logout_platform(platform: str):
    """Logout from a platform."""
    auth_manager = CIAuthManager()
    auth_manager.logout(platform)
    print(f"Logged out from {platform}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PRS CI Authentication Demo")
    parser.add_argument("--setup-auth", metavar="PLATFORM", help="Setup authentication for platform")
    parser.add_argument("--status", metavar="PLATFORM", nargs="?", const="all", help="Show authentication status")
    parser.add_argument("--logout", metavar="PLATFORM", help="Logout from platform")
    
    args = parser.parse_args()
    
    if args.setup_auth:
        setup_auth(args.setup_auth)
    elif args.status:
        if args.status == "all":
            show_auth_status()
        else:
            show_auth_status(args.status)
    elif args.logout:
        logout_platform(args.logout)
    else:
        main()