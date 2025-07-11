"""
Token Storage Module

Provides secure storage for CI authentication tokens using keyring
or encrypted file storage as fallback.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

try:
    from cryptography.fernet import Fernet
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False


class TokenStorage:
    """
    Secure token storage manager for CI authentication.
    
    Uses keyring for secure storage when available, falls back to
    encrypted file storage, and finally to plain file storage.
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize token storage.
        
        Args:
            storage_dir: Directory for file-based storage (defaults to ~/.prs/tokens)
        """
        self.storage_dir = storage_dir or Path.home() / ".prs" / "tokens"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.keyring_service = "prs-ci-auth"
        self.encryption_key_path = self.storage_dir / ".key"
        self.tokens_file = self.storage_dir / "tokens.json"
        
        # Initialize encryption key if using file storage
        if not KEYRING_AVAILABLE:
            self._ensure_encryption_key()
    
    def _ensure_encryption_key(self) -> None:
        """Ensure encryption key exists for file storage."""
        if not self.encryption_key_path.exists() and ENCRYPTION_AVAILABLE:
            key = Fernet.generate_key()
            self.encryption_key_path.write_bytes(key)
            # Set restrictive permissions
            os.chmod(self.encryption_key_path, 0o600)
    
    def _get_encryption_key(self) -> Optional[bytes]:
        """Get encryption key for file storage."""
        if not ENCRYPTION_AVAILABLE:
            return None
        
        try:
            return self.encryption_key_path.read_bytes()
        except FileNotFoundError:
            return None
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt data if encryption is available."""
        if not ENCRYPTION_AVAILABLE:
            return data
        
        key = self._get_encryption_key()
        if not key:
            return data
        
        fernet = Fernet(key)
        return fernet.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data if encryption is available."""
        if not ENCRYPTION_AVAILABLE:
            return encrypted_data
        
        key = self._get_encryption_key()
        if not key:
            return encrypted_data
        
        try:
            fernet = Fernet(key)
            return fernet.decrypt(encrypted_data.encode()).decode()
        except Exception:
            # If decryption fails, assume it's plain text
            return encrypted_data
    
    def _keyring_key(self, provider: str, token_type: str = "access") -> str:
        """Generate keyring key for provider and token type."""
        return f"{provider}_{token_type}_token"
    
    def store_token(self, provider: str, token: str, token_type: str = "access",
                   expires_at: Optional[datetime] = None, 
                   refresh_token: Optional[str] = None) -> None:
        """
        Store authentication token securely.
        
        Args:
            provider: CI provider name (e.g., 'buildkite')
            token: The authentication token
            token_type: Type of token ('access', 'refresh', 'api_key')
            expires_at: Token expiration time
            refresh_token: Optional refresh token
        """
        token_data = {
            "token": token,
            "token_type": token_type,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "refresh_token": refresh_token,
            "stored_at": datetime.now().isoformat()
        }
        
        if KEYRING_AVAILABLE:
            self._store_in_keyring(provider, token_data)
        else:
            self._store_in_file(provider, token_data)
    
    def _store_in_keyring(self, provider: str, token_data: Dict[str, Any]) -> None:
        """Store token data in system keyring."""
        key = self._keyring_key(provider, token_data["token_type"])
        keyring.set_password(self.keyring_service, key, json.dumps(token_data))
    
    def _store_in_file(self, provider: str, token_data: Dict[str, Any]) -> None:
        """Store token data in encrypted file."""
        # Load existing tokens
        tokens = self._load_tokens_from_file()
        
        # Update with new token
        if provider not in tokens:
            tokens[provider] = {}
        tokens[provider][token_data["token_type"]] = token_data
        
        # Save back to file
        self._save_tokens_to_file(tokens)
    
    def _load_tokens_from_file(self) -> Dict[str, Dict[str, Any]]:
        """Load tokens from encrypted file."""
        if not self.tokens_file.exists():
            return {}
        
        try:
            encrypted_content = self.tokens_file.read_text()
            decrypted_content = self._decrypt_data(encrypted_content)
            return json.loads(decrypted_content)
        except (json.JSONDecodeError, Exception):
            return {}
    
    def _save_tokens_to_file(self, tokens: Dict[str, Dict[str, Any]]) -> None:
        """Save tokens to encrypted file."""
        content = json.dumps(tokens, indent=2)
        encrypted_content = self._encrypt_data(content)
        
        self.tokens_file.write_text(encrypted_content)
        # Set restrictive permissions
        os.chmod(self.tokens_file, 0o600)
    
    def get_token(self, provider: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """
        Retrieve authentication token.
        
        Args:
            provider: CI provider name
            token_type: Type of token to retrieve
            
        Returns:
            Token data dictionary or None if not found
        """
        if KEYRING_AVAILABLE:
            return self._get_from_keyring(provider, token_type)
        else:
            return self._get_from_file(provider, token_type)
    
    def _get_from_keyring(self, provider: str, token_type: str) -> Optional[Dict[str, Any]]:
        """Get token from system keyring."""
        try:
            key = self._keyring_key(provider, token_type)
            token_json = keyring.get_password(self.keyring_service, key)
            if token_json:
                return json.loads(token_json)
        except Exception:
            pass
        return None
    
    def _get_from_file(self, provider: str, token_type: str) -> Optional[Dict[str, Any]]:
        """Get token from encrypted file."""
        tokens = self._load_tokens_from_file()
        return tokens.get(provider, {}).get(token_type)
    
    def is_token_expired(self, token_data: Dict[str, Any]) -> bool:
        """Check if token is expired."""
        if not token_data or not token_data.get("expires_at"):
            return False
        
        try:
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            return datetime.now() >= expires_at
        except (ValueError, TypeError):
            return False
    
    def is_token_expiring_soon(self, token_data: Dict[str, Any], 
                              minutes_threshold: int = 10) -> bool:
        """Check if token is expiring soon."""
        if not token_data or not token_data.get("expires_at"):
            return False
        
        try:
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            threshold = datetime.now() + timedelta(minutes=minutes_threshold)
            return expires_at <= threshold
        except (ValueError, TypeError):
            return False
    
    def delete_token(self, provider: str, token_type: str = "access") -> None:
        """Delete stored token."""
        if KEYRING_AVAILABLE:
            self._delete_from_keyring(provider, token_type)
        else:
            self._delete_from_file(provider, token_type)
    
    def _delete_from_keyring(self, provider: str, token_type: str) -> None:
        """Delete token from system keyring."""
        try:
            key = self._keyring_key(provider, token_type)
            keyring.delete_password(self.keyring_service, key)
        except keyring.errors.PasswordDeleteError:
            pass
    
    def _delete_from_file(self, provider: str, token_type: str) -> None:
        """Delete token from encrypted file."""
        tokens = self._load_tokens_from_file()
        if provider in tokens and token_type in tokens[provider]:
            del tokens[provider][token_type]
            if not tokens[provider]:
                del tokens[provider]
            self._save_tokens_to_file(tokens)
    
    def clear_provider_tokens(self, provider: str) -> None:
        """Clear all tokens for a provider."""
        if KEYRING_AVAILABLE:
            # Clear common token types from keyring
            for token_type in ["access", "refresh", "api_key"]:
                self._delete_from_keyring(provider, token_type)
        else:
            tokens = self._load_tokens_from_file()
            if provider in tokens:
                del tokens[provider]
                self._save_tokens_to_file(tokens)
    
    def list_providers(self) -> list[str]:
        """List all providers with stored tokens."""
        if KEYRING_AVAILABLE:
            # For keyring, we'd need to enumerate, which is complex
            # Fall back to file-based listing
            pass
        
        tokens = self._load_tokens_from_file()
        return list(tokens.keys())
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about storage backend."""
        return {
            "keyring_available": KEYRING_AVAILABLE,
            "encryption_available": ENCRYPTION_AVAILABLE,
            "using_keyring": KEYRING_AVAILABLE,
            "storage_dir": str(self.storage_dir),
            "tokens_file": str(self.tokens_file) if self.tokens_file.exists() else None
        }