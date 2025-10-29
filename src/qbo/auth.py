# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""OAuth2 authentication for QuickBooks Online.

Handles the OAuth2 flow for QBO API access including:
- Initial authorization
- Token exchange
- Token refresh
- Secure token storage
"""

import logging
import json
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
from urllib.parse import urlencode
import webbrowser

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
import requests

from ..config import get_config
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


def _mask_token(token: str) -> str:
    """Mask a token for safe logging.

    Args:
        token: Token string to mask

    Returns:
        Masked token showing only first/last 4 chars
    """
    if not token or len(token) < 12:
        return "***MASKED***"
    return f"{token[:4]}...{token[-4:]}"


class QBOAuthManager:
    """Manages OAuth2 authentication for QuickBooks Online."""

    # QBO OAuth2 endpoints
    AUTH_URL = 'https://appcenter.intuit.com/connect/oauth2'
    TOKEN_URL = 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer'
    REVOKE_URL = 'https://developer.api.intuit.com/v2/oauth2/tokens/revoke'

    # Scopes needed for our operations
    SCOPES = [
        'com.intuit.quickbooks.accounting'
    ]

    def __init__(self):
        """Initialize auth manager with configuration."""
        config = get_config()

        self.client_id = config.get('qbo.client_id')
        self.client_secret = config.get('qbo.client_secret')
        self.redirect_uri = config.get('qbo.redirect_uri')
        self.company_id = config.get('qbo.company_id')
        self.sandbox = config.get('qbo.sandbox', True)

        # Token storage
        self.token_file = config.data_dir / 'qbo_tokens.enc'
        self.encryption_key_file = config.data_dir / '.qbo_key'

        # Get or create encryption key
        self._encryption_key = self._get_or_create_encryption_key()

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for token storage.

        Returns:
            Encryption key bytes
        """
        if self.encryption_key_file.exists():
            with open(self.encryption_key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.encryption_key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            self.encryption_key_file.chmod(0o600)
            logger.info("Created new encryption key for token storage")
            return key

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Get the authorization URL for user to visit.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL
        """
        if not self.client_id:
            raise ValueError("QBO client_id not configured")

        params = {
            'client_id': self.client_id,
            'scope': ' '.join(self.SCOPES),
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'state': state or 'security_token'
        }

        auth_url = f"{self.AUTH_URL}?{urlencode(params)}"
        logger.info("Generated authorization URL")
        return auth_url

    def authorize_interactive(self) -> Dict:
        """Interactive authorization flow.

        Opens browser for user to authorize, then prompts for callback URL.

        Returns:
            Token dictionary
        """
        print("\n" + "="*60)
        print("QuickBooks Online Authorization")
        print("="*60)

        # Generate and open authorization URL
        auth_url = self.get_authorization_url()
        print(f"\nOpening browser to authorize application...")
        print(f"If browser doesn't open, visit this URL:\n{auth_url}\n")

        webbrowser.open(auth_url)

        # Wait for user to complete authorization
        print("After authorizing, you'll be redirected to a URL.")
        print("Copy the ENTIRE URL from your browser's address bar and paste it here.\n")

        callback_url = input("Paste the callback URL: ").strip()

        # Extract authorization code
        if 'code=' not in callback_url:
            raise ValueError("Invalid callback URL - missing authorization code")

        # Parse code and realm ID
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(callback_url)
        params = parse_qs(parsed.query)

        if 'code' not in params:
            raise ValueError("Authorization code not found in callback URL")

        auth_code = params['code'][0]
        realm_id = params.get('realmId', [None])[0]

        if realm_id:
            logger.info(f"Received authorization for realm ID: {realm_id}")
            # Update company ID if provided
            config = get_config()
            config.set('qbo.company_id', realm_id)
            config.save()
            self.company_id = realm_id
        else:
            logger.warning("No realm ID in callback - using configured company ID")

        # Exchange code for tokens
        return self.exchange_code_for_tokens(auth_code)

    def exchange_code_for_tokens(self, auth_code: str) -> Dict:
        """Exchange authorization code for access and refresh tokens.

        Args:
            auth_code: Authorization code from callback

        Returns:
            Token dictionary
        """
        if not self.client_id or not self.client_secret:
            raise ValueError("QBO credentials not configured")

        logger.info("Exchanging authorization code for tokens")

        # Prepare auth header
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': self.redirect_uri
        }

        response = requests.post(self.TOKEN_URL, headers=headers, data=data)

        if response.status_code != 200:
            # Don't log response.text as it might contain sensitive data
            logger.error(f"Token exchange failed with status {response.status_code}")
            raise RuntimeError(f"Failed to exchange authorization code (status {response.status_code})")

        tokens = response.json()

        # Add metadata
        tokens['created_at'] = datetime.utcnow().isoformat()
        tokens['expires_at'] = (
            datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600))
        ).isoformat()

        # Save tokens
        self.save_tokens(tokens)

        logger.info("Successfully obtained and saved tokens")
        return tokens

    def refresh_access_token(self, refresh_token: Optional[str] = None) -> Dict:
        """Refresh the access token using refresh token.

        Args:
            refresh_token: Optional refresh token (uses stored if None)

        Returns:
            New token dictionary
        """
        if refresh_token is None:
            tokens = self.load_tokens()
            if not tokens or 'refresh_token' not in tokens:
                raise ValueError("No refresh token available")
            refresh_token = tokens['refresh_token']

        logger.info("Refreshing access token")

        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }

        response = requests.post(self.TOKEN_URL, headers=headers, data=data)

        if response.status_code != 200:
            # Don't log response.text as it might contain sensitive data
            logger.error(f"Token refresh failed with status {response.status_code}")
            raise RuntimeError(f"Failed to refresh token (status {response.status_code})")

        new_tokens = response.json()

        # Add metadata
        new_tokens['created_at'] = datetime.utcnow().isoformat()
        new_tokens['expires_at'] = (
            datetime.utcnow() + timedelta(seconds=new_tokens.get('expires_in', 3600))
        ).isoformat()

        # Save new tokens (which includes the new refresh token from Intuit)
        self.save_tokens(new_tokens)

        # Log success with masked token for security
        if 'refresh_token' in new_tokens:
            logger.info(f"Successfully refreshed and saved tokens (refresh token: {_mask_token(new_tokens['refresh_token'])})")
        else:
            logger.info("Successfully refreshed and saved tokens")
        return new_tokens

    def save_tokens(self, tokens: Dict) -> None:
        """Save tokens to encrypted file.

        Args:
            tokens: Token dictionary
        """
        cipher = Fernet(self._encryption_key)

        # Convert to JSON and encrypt
        token_json = json.dumps(tokens)
        encrypted = cipher.encrypt(token_json.encode())

        # Save to file
        with open(self.token_file, 'wb') as f:
            f.write(encrypted)

        # Set restrictive permissions
        self.token_file.chmod(0o600)

        logger.debug("Tokens saved to encrypted file")

    def load_tokens(self) -> Optional[Dict]:
        """Load tokens from encrypted file.

        Returns:
            Token dictionary or None if file doesn't exist
        """
        if not self.token_file.exists():
            logger.debug("No token file found")
            return None

        try:
            cipher = Fernet(self._encryption_key)

            # Read and decrypt
            with open(self.token_file, 'rb') as f:
                encrypted = f.read()

            decrypted = cipher.decrypt(encrypted)
            tokens = json.loads(decrypted.decode())

            logger.debug("Tokens loaded from encrypted file")
            return tokens

        except Exception as e:
            logger.error(f"Error loading tokens: {e}")
            return None

    def get_valid_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        Returns:
            Valid access token

        Raises:
            RuntimeError: If no tokens available or refresh fails
        """
        tokens = self.load_tokens()

        if not tokens:
            raise RuntimeError(
                "No tokens available. Please run authorization flow first."
            )

        # Check if token is expired
        expires_at = datetime.fromisoformat(tokens['expires_at'])
        now = datetime.utcnow()

        # Refresh if expired or expiring soon (within 5 minutes)
        if now >= expires_at - timedelta(minutes=5):
            logger.info("Access token expired or expiring soon, refreshing...")
            tokens = self.refresh_access_token(tokens.get('refresh_token'))

        return tokens['access_token']

    def revoke_tokens(self) -> None:
        """Revoke the current tokens."""
        tokens = self.load_tokens()

        if not tokens:
            logger.warning("No tokens to revoke")
            return

        logger.info("Revoking tokens")

        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        data = {
            'token': tokens.get('refresh_token') or tokens.get('access_token')
        }

        response = requests.post(self.REVOKE_URL, headers=headers, data=data)

        if response.status_code == 200:
            logger.info("Tokens revoked successfully")
            # Delete token file
            if self.token_file.exists():
                self.token_file.unlink()
        else:
            logger.error(f"Token revocation failed with status {response.status_code}")

    def is_authorized(self) -> bool:
        """Check if we have valid authorization.

        Returns:
            True if authorized, False otherwise
        """
        try:
            self.get_valid_access_token()
            return True
        except:
            return False
