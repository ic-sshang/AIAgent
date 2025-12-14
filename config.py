import json
import os
from pathlib import Path
from typing import Any, Dict


class Config:
    """Configuration loader for reading settings from config.json"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        Initialize the Config object.
        
        Args:
            config_file: Path to the JSON configuration file
        """
        self.config_file = config_file
        self._config_data: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> None:
        """Load configuration from JSON file."""
        config_path = Path(self.config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.
        Supports nested keys using dot notation (e.g., 'database.host')
        
        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section.
        
        Args:
            section: Name of the configuration section
            
        Returns:
            Dictionary containing the section data
        """
        return self._config_data.get(section, {})
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self.load()
    
    @property
    def all(self) -> Dict[str, Any]:
        """Get all configuration data."""
        return self._config_data.copy()


# Global config instance
_config_instance = None


def get_config(config_file: str = "config.json") -> Config:
    """
    Get or create the global configuration instance.
    
    Args:
        config_file: Path to the JSON configuration file
        
    Returns:
        Config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_file)
    return _config_instance


# Example usage
if __name__ == "__main__":
    # Load config
     config = Config()
    
    # # Access config values
    # print(f"App Name: {config.get('app.name')}")
    # print(f"Database Host: {config.get('database.host')}")
    # print(f"API Timeout: {config.get('api.timeout')}")
    
    # # Get entire section
    # db_config = config.get_section('database')
    # print(f"Database Config: {db_config}")
    
    # # Get with default value
    # unknown = config.get('unknown.key', 'default_value')
    # print(f"Unknown Key: {unknown}")
    
    # # Get all config
    # print(f"All Config: {config.all}")
