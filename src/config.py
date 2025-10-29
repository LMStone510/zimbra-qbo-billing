# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""Configuration management for Zimbra-QBO billing system.

Handles loading configuration from:
1. Environment variables (highest priority)
2. config.json file
3. Default values (lowest priority)
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


class Config:
    """Configuration manager for the application."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.

        Args:
            config_path: Path to config.json file. If None, uses default location.
        """
        self.base_dir = Path(__file__).parent.parent
        self.config_path = Path(config_path) if config_path else self.base_dir / "data" / "config.json"
        self.data_dir = self.base_dir / "data"
        self.log_dir = self.data_dir / "logs"

        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)

        # Load configuration
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file and environment variables."""
        # Start with defaults
        config = self._get_defaults()

        # Load from config file if it exists
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                file_config = json.load(f)
                self._deep_update(config, file_config)

        # Override with environment variables
        self._load_env_overrides(config)

        return config

    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            "zimbra": {
                "host": "",
                "port": 22,
                "username": "zimbra",
                "key_file": str(Path.home() / ".ssh" / "id_rsa"),
                "report_path": "/opt/MonthlyUsageReports"
            },
            "qbo": {
                "sandbox": True,
                "client_id": "",
                "client_secret": "",
                "redirect_uri": "http://localhost:8080/callback",
                "company_id": ""
            },
            "database": {
                "path": str(self.data_dir / "billing.db")
            },
            "exclusions": {
                "domains": [
                    "missioncriticalemail.com",
                    "*.archive",
                    "*test*"
                ],
                "cos_patterns": [
                    "mce-internal",
                    "*test*"
                ]
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }

    def _deep_update(self, base: Dict, update: Dict) -> None:
        """Recursively update base dictionary with values from update dictionary."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def _load_env_overrides(self, config: Dict[str, Any]) -> None:
        """Load configuration overrides from environment variables."""
        # Zimbra settings
        if os.getenv("ZIMBRA_HOST"):
            config["zimbra"]["host"] = os.getenv("ZIMBRA_HOST")
        if os.getenv("ZIMBRA_USERNAME"):
            config["zimbra"]["username"] = os.getenv("ZIMBRA_USERNAME")
        if os.getenv("ZIMBRA_KEY_FILE"):
            config["zimbra"]["key_file"] = os.getenv("ZIMBRA_KEY_FILE")
        if os.getenv("ZIMBRA_REPORT_PATH"):
            config["zimbra"]["report_path"] = os.getenv("ZIMBRA_REPORT_PATH")

        # QBO settings
        if os.getenv("QBO_CLIENT_ID"):
            config["qbo"]["client_id"] = os.getenv("QBO_CLIENT_ID")
        if os.getenv("QBO_CLIENT_SECRET"):
            config["qbo"]["client_secret"] = os.getenv("QBO_CLIENT_SECRET")
        if os.getenv("QBO_REDIRECT_URI"):
            config["qbo"]["redirect_uri"] = os.getenv("QBO_REDIRECT_URI")
        if os.getenv("QBO_COMPANY_ID"):
            config["qbo"]["company_id"] = os.getenv("QBO_COMPANY_ID")
        if os.getenv("QBO_SANDBOX"):
            config["qbo"]["sandbox"] = os.getenv("QBO_SANDBOX").lower() == "true"

        # Database settings
        if os.getenv("DATABASE_PATH"):
            config["database"]["path"] = os.getenv("DATABASE_PATH")

    def save(self) -> None:
        """Save current configuration to config file."""
        with open(self.config_path, 'w') as f:
            json.dump(self._config, f, indent=2)

    # Convenience properties for accessing config sections
    @property
    def zimbra(self) -> Dict[str, Any]:
        """Get Zimbra configuration."""
        return self._config["zimbra"]

    @property
    def qbo(self) -> Dict[str, Any]:
        """Get QuickBooks Online configuration."""
        return self._config["qbo"]

    @property
    def database(self) -> Dict[str, Any]:
        """Get database configuration."""
        return self._config["database"]

    @property
    def exclusions(self) -> Dict[str, Any]:
        """Get exclusion patterns."""
        return self._config["exclusions"]

    @property
    def logging(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self._config["logging"]

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key.

        Args:
            key: Configuration key (supports dot notation, e.g., 'zimbra.host')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value by key.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value


# Global configuration instance
_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """Get the global configuration instance.

    Args:
        config_path: Optional path to config file. Only used on first call.

    Returns:
        Configuration instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def reload_config(config_path: Optional[str] = None) -> Config:
    """Reload configuration from file.

    Args:
        config_path: Optional path to config file

    Returns:
        Reloaded configuration instance
    """
    global _config
    _config = Config(config_path)
    return _config
