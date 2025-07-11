"""
SSO Portal Authentication Module

Provides SSO portal integration for CI platforms like Buildkite that
support web-based OAuth-like authentication flows.
"""

import json
import secrets
import string
import subprocess
import time
import webbrowser
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse, parse_qs, urlencode

from .token_storage import TokenStorage


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""
    
    def do_GET(self):
        """Handle GET requests for OAuth callback."""
        self.server.callback_received = True
        
        # Parse callback parameters
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        self.server.callback_params = {
            key: value[0] if value else None 
            for key, value in query_params.items()
        }
        
        # Send response to browser
        if 'code' in query_params:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
            <html>
            <body>
                <h1>Authentication Successful!</h1>
                <p>You can now close this window and return to the terminal.</p>
                <script>setTimeout(function() { window.close(); }, 3000);</script>
            </body>
            </html>
            """)
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
            <html>
            <body>
                <h1>Authentication Failed</h1>
                <p>There was an error during authentication. Please try again.</p>
                <script>setTimeout(function() { window.close(); }, 3000);</script>
            </body>
            </html>
            """)
    
    def log_message(self, format, *args):
        """Suppress log messages."""
        pass


class SSOPortalAuth:
    """
    SSO Portal authentication manager for CI platforms.
    
    Provides web-based OAuth-like authentication flows for platforms
    like Buildkite that support SSO portal integration.
    """
    
    def __init__(self, provider: str, base_url: str, token_storage: TokenStorage):
        """
        Initialize SSO portal authentication.
        
        Args:
            provider: CI provider name (e.g., 'buildkite')
            base_url: Base URL for the CI platform
            token_storage: Token storage instance
        """
        self.provider = provider
        self.base_url = base_url.rstrip('/')
        self.token_storage = token_storage
        
        # OAuth-like configuration
        self.client_id = f"prs-cli-{provider}"
        self.redirect_uri = "http://localhost:8080/callback"
        self.scope = "read_builds,read_build_logs,read_pipelines"
        
        # Buildkite-specific endpoints
        self.auth_endpoints = {
            'buildkite': {
                'authorize': f"{self.base_url}/user/api_access_tokens/new",
                'token': f"{self.base_url}/v2/access_token",
                'validate': f"{self.base_url}/v2/user"
            }
        }
    
    def _generate_state(self) -> str:
        """Generate random state parameter for OAuth security."""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    def _get_authorization_url(self, state: str) -> str:
        """
        Generate authorization URL for SSO portal.
        
        Args:
            state: Random state parameter for security
            
        Returns:
            Authorization URL
        """
        if self.provider == 'buildkite':
            # Buildkite uses a manual token creation page
            return f"{self.base_url}/user/api_access_tokens/new"
        
        # Generic OAuth-like flow
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'state': state,
            'response_type': 'code'
        }
        
        endpoint = self.auth_endpoints.get(self.provider, {}).get('authorize')
        if not endpoint:
            raise ValueError(f"No authorization endpoint configured for {self.provider}")
        
        return f"{endpoint}?{urlencode(params)}"
    
    def _start_callback_server(self, timeout: int = 300) -> Tuple[bool, Dict[str, Any]]:
        """
        Start local HTTP server to handle OAuth callback.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (success, callback_params)
        """
        server = HTTPServer(('localhost', 8080), CallbackHandler)
        server.timeout = 1
        server.callback_received = False
        server.callback_params = {}
        
        start_time = time.time()
        
        while not server.callback_received and (time.time() - start_time) < timeout:
            server.handle_request()
        
        success = server.callback_received
        params = server.callback_params
        
        server.server_close()
        return success, params
    
    def _exchange_code_for_token(self, code: str, state: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from callback
            state: State parameter for validation
            
        Returns:
            Token data or None if failed
        """
        endpoint = self.auth_endpoints.get(self.provider, {}).get('token')
        if not endpoint:
            return None
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'state': state
        }
        
        try:
            # Use curl for HTTP request
            curl_cmd = [
                'curl', '-X', 'POST',
                '-H', 'Content-Type: application/x-www-form-urlencoded',
                '-d', urlencode(data),
                endpoint
            ]
            
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                response_data = json.loads(result.stdout)
                return response_data
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
            pass
        
        return None
    
    def _validate_token_with_api(self, token: str) -> bool:
        """
        Validate token by making API call.
        
        Args:
            token: Access token to validate
            
        Returns:
            True if token is valid
        """
        endpoint = self.auth_endpoints.get(self.provider, {}).get('validate')
        if not endpoint:
            return False
        
        try:
            curl_cmd = [
                'curl', '-H', f'Authorization: Bearer {token}',
                endpoint
            ]
            
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, Exception):
            return False
    
    def authenticate_interactive(self) -> Optional[Dict[str, Any]]:
        """
        Perform interactive SSO authentication.
        
        Returns:
            Token data or None if failed
        """
        state = self._generate_state()
        auth_url = self._get_authorization_url(state)
        
        if self.provider == 'buildkite':
            return self._buildkite_manual_auth(auth_url)
        else:
            return self._oauth_flow_auth(auth_url, state)
    
    def _buildkite_manual_auth(self, auth_url: str) -> Optional[Dict[str, Any]]:
        """
        Handle Buildkite manual token creation flow.
        
        Args:
            auth_url: URL to Buildkite token creation page
            
        Returns:
            Token data or None if failed
        """
        print(f"Opening Buildkite API access token page...")
        print(f"URL: {auth_url}")
        print()
        print("Please follow these steps:")
        print("1. Create a new API access token")
        print("2. Set the description to: 'PRS CLI Tool'")
        print("3. Select these scopes: read_builds, read_build_logs, read_pipelines")
        print("4. Click 'Create API Access Token'")
        print("5. Copy the generated token")
        print()
        
        # Open browser
        try:
            webbrowser.open(auth_url)
        except Exception:
            print("Unable to open browser automatically. Please visit the URL manually.")
        
        # Prompt for token
        while True:
            token = input("Enter your Buildkite API token: ").strip()
            if not token:
                continue
            
            print("Validating token...")
            if self._validate_token_with_api(token):
                print("Token validated successfully!")
                
                # Create token data
                token_data = {
                    'access_token': token,
                    'token_type': 'Bearer',
                    'expires_in': None,  # Buildkite tokens don't expire
                    'scope': self.scope
                }
                
                # Store token
                self.token_storage.store_token(
                    provider=self.provider,
                    token=token,
                    token_type='api_key'
                )
                
                return token_data
            else:
                print("Token validation failed. Please check the token and try again.")
                retry = input("Try again? (y/n): ").strip().lower()
                if retry not in ['y', 'yes']:
                    break
        
        return None
    
    def _oauth_flow_auth(self, auth_url: str, state: str) -> Optional[Dict[str, Any]]:
        """
        Handle OAuth-like authentication flow.
        
        Args:
            auth_url: Authorization URL
            state: State parameter
            
        Returns:
            Token data or None if failed
        """
        print(f"Opening browser for {self.provider} authentication...")
        print(f"URL: {auth_url}")
        print("Please complete the authentication in your browser.")
        print("This will automatically redirect back to the application.")
        print()
        
        # Open browser
        try:
            webbrowser.open(auth_url)
        except Exception:
            print("Unable to open browser automatically. Please visit the URL manually.")
        
        # Start callback server
        print("Waiting for authentication callback...")
        success, params = self._start_callback_server()
        
        if not success:
            print("Authentication timed out or failed.")
            return None
        
        # Check for error
        if 'error' in params:
            print(f"Authentication error: {params.get('error_description', params['error'])}")
            return None
        
        # Validate state
        if params.get('state') != state:
            print("Invalid state parameter. Authentication may have been tampered with.")
            return None
        
        # Exchange code for token
        code = params.get('code')
        if not code:
            print("No authorization code received.")
            return None
        
        print("Exchanging authorization code for access token...")
        token_data = self._exchange_code_for_token(code, state)
        
        if not token_data:
            print("Failed to exchange authorization code for token.")
            return None
        
        # Store token
        expires_at = None
        if 'expires_in' in token_data:
            expires_at = datetime.now() + timedelta(seconds=token_data['expires_in'])
        
        self.token_storage.store_token(
            provider=self.provider,
            token=token_data['access_token'],
            token_type='access',
            expires_at=expires_at,
            refresh_token=token_data.get('refresh_token')
        )
        
        print("Authentication successful!")
        return token_data
    
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New token data or None if failed
        """
        endpoint = self.auth_endpoints.get(self.provider, {}).get('token')
        if not endpoint:
            return None
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id
        }
        
        try:
            curl_cmd = [
                'curl', '-X', 'POST',
                '-H', 'Content-Type: application/x-www-form-urlencoded',
                '-d', urlencode(data),
                endpoint
            ]
            
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                response_data = json.loads(result.stdout)
                
                # Store new token
                expires_at = None
                if 'expires_in' in response_data:
                    expires_at = datetime.now() + timedelta(seconds=response_data['expires_in'])
                
                self.token_storage.store_token(
                    provider=self.provider,
                    token=response_data['access_token'],
                    token_type='access',
                    expires_at=expires_at,
                    refresh_token=response_data.get('refresh_token', refresh_token)
                )
                
                return response_data
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
            pass
        
        return None
    
    def validate_stored_token(self) -> bool:
        """
        Validate stored token.
        
        Returns:
            True if stored token is valid
        """
        # Try API key first (for Buildkite)
        token_data = self.token_storage.get_token(self.provider, 'api_key')
        if token_data:
            return self._validate_token_with_api(token_data['token'])
        
        # Try access token
        token_data = self.token_storage.get_token(self.provider, 'access')
        if token_data:
            if self.token_storage.is_token_expired(token_data):
                # Try to refresh
                if token_data.get('refresh_token'):
                    new_token_data = self.refresh_token(token_data['refresh_token'])
                    return new_token_data is not None
                return False
            
            return self._validate_token_with_api(token_data['token'])
        
        return False
    
    def get_valid_token(self) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.
        
        Returns:
            Valid access token or None
        """
        # Try API key first (for Buildkite)
        token_data = self.token_storage.get_token(self.provider, 'api_key')
        if token_data:
            if self._validate_token_with_api(token_data['token']):
                return token_data['token']
        
        # Try access token
        token_data = self.token_storage.get_token(self.provider, 'access')
        if token_data:
            if self.token_storage.is_token_expired(token_data):
                # Try to refresh
                if token_data.get('refresh_token'):
                    new_token_data = self.refresh_token(token_data['refresh_token'])
                    if new_token_data:
                        return new_token_data['access_token']
                return None
            
            if self._validate_token_with_api(token_data['token']):
                return token_data['token']
        
        return None
    
    def logout(self) -> None:
        """Clear stored authentication tokens."""
        self.token_storage.clear_provider_tokens(self.provider)
        print(f"Logged out from {self.provider}")
    
    def get_auth_status(self) -> Dict[str, Any]:
        """
        Get current authentication status.
        
        Returns:
            Authentication status information
        """
        token_data = self.token_storage.get_token(self.provider, 'api_key')
        if not token_data:
            token_data = self.token_storage.get_token(self.provider, 'access')
        
        if not token_data:
            return {
                'authenticated': False,
                'provider': self.provider,
                'token_type': None,
                'expires_at': None,
                'is_expired': False
            }
        
        is_expired = self.token_storage.is_token_expired(token_data)
        
        return {
            'authenticated': True,
            'provider': self.provider,
            'token_type': token_data.get('token_type', 'unknown'),
            'expires_at': token_data.get('expires_at'),
            'is_expired': is_expired,
            'stored_at': token_data.get('stored_at')
        }