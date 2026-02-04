"""
Configuration loader for the ingestion framework.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None


logger = logging.getLogger(__name__)


class IngestConfig:
    """
    Configuration for the ingestion framework.
    
    Loads and validates YAML configuration files.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to YAML config file (optional)
        """
        self.config_path = config_path
        self.config = self._load_config() if config_path else self._default_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if yaml is None:
            raise ImportError(
                "pyyaml is required for config loading. "
                "Install with: pip install pyyaml"
            )
        
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        logger.info(f"Loading config from: {self.config_path}")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        return config or {}

    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "storage": {
                "data_lake": {
                    "enabled": True,
                    "base_dir": "local/data_lake",
                },
                "sql_server": {
                    "enabled": False,
                },
            },
            "state": {
                "type": "sqlserver",
                "sqlserver": {
                    "host": "localhost",
                    "port": 1433,
                    "database": "Holocron",
                    "user": "sa",
                    "schema": "ingest",
                },
            },
            "runner": {
                "batch_size": 10,
                "max_retries": 3,
                "enable_discovery": True,
            },
            "sources": [],
        }

    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration."""
        return self.config.get("storage", {})

    def get_state_config(self) -> Dict[str, Any]:
        """Get state store configuration."""
        return self.config.get("state", {})

    def get_runner_config(self) -> Dict[str, Any]:
        """Get runner configuration."""
        return self.config.get("runner", {})

    def get_sources(self) -> List[Dict[str, Any]]:
        """Get list of source configurations."""
        return self.config.get("sources", [])

    def get_seeds(self) -> List[Dict[str, Any]]:
        """Get list of seed configurations."""
        return self.config.get("seeds", [])

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        keys = key.split(".")
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        
        return value if value is not None else default
