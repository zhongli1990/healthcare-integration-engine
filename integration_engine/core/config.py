"""
Configuration management for the Integration Engine.

This module provides utilities for loading, validating, and accessing
configuration settings from YAML files with environment-specific overrides.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union, TypeVar, Type

import yaml
from pydantic import BaseModel, ValidationError, validator, root_validator, BaseSettings
from pydantic.env_settings import SettingsSourceCallable

logger = logging.getLogger(__name__)

# Type variable for generic model validation
T = TypeVar('T', bound='BaseModel')


def load_yaml_config(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    
    Args:
        file_path: Path to the YAML configuration file
        
    Returns:
        Dictionary containing the parsed configuration
        
    Raises:
        FileNotFoundError: If the configuration file does not exist
        yaml.YAMLError: If there is an error parsing the YAML
    """
    file_path = Path(file_path).resolve()
    
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            return config
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration file {file_path}: {e}")
        raise


def update_config(config: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively update a configuration dictionary with updates.
    
    Args:
        config: The base configuration dictionary
        updates: Dictionary containing updates to apply
        
    Returns:
        Updated configuration dictionary
    """
    if not updates:
        return config
    
    result = config.copy()
    
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = update_config(result[key], value)
        else:
            result[key] = value
    
    return result


def load_environment_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load environment-specific overrides from the configuration.
    
    Args:
        config: The base configuration dictionary
        
    Returns:
        Updated configuration with environment overrides applied
    """
    environment = config.get('global', {}).get('environment', 'development')
    
    # Get overrides for the current environment
    environment_overrides = config.get('environments', {}).get(environment, {})
    
    if environment_overrides:
        logger.info(f"Applying environment-specific overrides for '{environment}'")
        
        # Apply overrides
        updated_config = update_config(config, environment_overrides)
        
        # Ensure the environment is set correctly
        updated_config['global']['environment'] = environment
        
        return updated_config
    
    return config


def validate_config(config: Dict[str, Any], model: Type[T]) -> T:
    """
    Validate configuration against a Pydantic model.
    
    Args:
        config: Configuration dictionary to validate
        model: Pydantic model class to validate against
        
    Returns:
        Validated configuration as an instance of the model
        
    Raises:
        ValidationError: If the configuration is invalid
    """
    try:
        return model.parse_obj(config)
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise


class GlobalConfig(BaseModel):
    """Global configuration settings."""
    log_level: str = "INFO"
    environment: str = "development"
    instance_id: str = "integration-engine-01"
    timezone: str = "UTC"
    
    class Config:
        extra = "ignore"


class QueueConfig(BaseModel):
    """Queue configuration."""
    type: str = "redis"  # redis or memory
    redis: Dict[str, Any] = {
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "password": "",
        "ssl": False,
        "max_connections": 100
    }
    memory: Dict[str, Any] = {
        "max_size": 10000
    }
    
    class Config:
        extra = "ignore"


class DatabaseConfig(BaseModel):
    """Database configuration."""
    enabled: bool = True
    type: str = "sqlite"  # sqlite, postgresql, mysql
    sqlite: Dict[str, Any] = {
        "database": "data/integration_engine.db",
        "journal_mode": "WAL",
        "synchronous": "NORMAL",
        "busy_timeout": 5000
    }
    postgresql: Dict[str, Any] = {
        "host": "localhost",
        "port": 5432,
        "database": "integration_engine",
        "username": "postgres",
        "password": "postgres",
        "sslmode": "prefer",
        "pool_min": 1,
        "pool_max": 10
    }
    mysql: Dict[str, Any] = {
        "host": "localhost",
        "port": 3306,
        "database": "integration_engine",
        "username": "root",
        "password": "password",
        "charset": "utf8mb4",
        "pool_min": 1,
        "pool_max": 10
    }
    models: list = [
        "core.models.message",
        "core.models.audit",
        "core.models.routing"
    ]
    migrations_dir: str = "migrations"
    auto_migrate: bool = True
    
    class Config:
        extra = "ignore"


class APIConfig(BaseModel):
    """API server configuration."""
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    secret_key: str = "change-this-in-production"
    cors_enabled: bool = True
    cors_origins: list = ["*"]
    auth_enabled: bool = True
    auth_users: Dict[str, Dict[str, Any]] = {
        "admin": {
            "password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
            "scopes": ["admin"]
        },
        "user": {
            "password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
            "scopes": ["read", "write"]
        }
    }
    rate_limit: str = "1000/hour"
    enable_swagger: bool = True
    enable_redoc: bool = True
    enable_metrics: bool = True
    metrics_path: str = "/metrics"
    health_check_path: str = "/health"
    log_level: str = "info"
    
    class Config:
        extra = "ignore"


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""
    enabled: bool = True
    metrics: Dict[str, Any] = {
        "enable_prometheus": True,
        "prometheus_port": 9090,
        "enable_statsd": False,
        "statsd_host": "localhost",
        "statsd_port": 8125,
        "statsd_prefix": "integration_engine.",
        "enable_health_checks": True,
        "health_check_port": 8081
    }
    logging: Dict[str, Any] = {
        "enable_access_log": True,
        "access_log_format": "%(asctime)s - %(client_addr)s - %(request_line)s %(status_code)d",
        "enable_error_log": True,
        "error_log_level": "ERROR",
        "log_file": "logs/engine.log",
        "max_file_size": 10485760,  # 10MB
        "backup_count": 5
    }
    
    class Config:
        extra = "ignore"


class IntegrationEngineConfig(BaseSettings):
    """Main configuration model for the Integration Engine."""
    global_config: GlobalConfig = GlobalConfig()
    queues: QueueConfig = QueueConfig()
    database: DatabaseConfig = DatabaseConfig()
    api: APIConfig = APIConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    
    # Allow arbitrary types for the rest of the config
    class Config:
        extra = "allow"
    
    @classmethod
    def from_yaml(
        cls,
        file_path: Union[str, Path],
        env_override: bool = True
    ) -> 'IntegrationEngineConfig':
        """
        Load configuration from a YAML file.
        
        Args:
            file_path: Path to the YAML configuration file
            env_override: Whether to apply environment-specific overrides
            
        Returns:
            An instance of IntegrationEngineConfig
        """
        # Load base config
        config = load_yaml_config(file_path)
        
        # Apply environment overrides if enabled
        if env_override:
            config = load_environment_overrides(config)
        
        # Extract global config
        global_config = GlobalConfig.parse_obj(config.get("global", {}))
        
        # Update config with global settings
        config["global_config"] = global_config.dict()
        
        # Validate and parse the full config
        return cls.parse_obj(config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by dot notation key.
        
        Args:
            key: Dot notation key (e.g., "database.host")
            default: Default value if key is not found
            
        Returns:
            The configuration value or default if not found
        """
        keys = key.split('.')
        value = self.dict()
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default


# Global configuration instance
_config: Optional[IntegrationEngineConfig] = None


def get_config() -> IntegrationEngineConfig:
    """
    Get the global configuration instance.
    
    Returns:
        The global IntegrationEngineConfig instance
        
    Raises:
        RuntimeError: If the configuration has not been initialized
    """
    if _config is None:
        raise RuntimeError("Configuration has not been initialized. Call load_config() first.")
    return _config


def load_config(
    config_file: Optional[Union[str, Path]] = None,
    env_override: bool = True,
    **kwargs
) -> IntegrationEngineConfig:
    """
    Load and initialize the global configuration.
    
    Args:
        config_file: Path to the YAML configuration file. If not provided, looks for
                    'config.yaml' in the current directory and 'config' subdirectory.
        env_override: Whether to apply environment-specific overrides
        **kwargs: Additional keyword arguments to pass to the config
        
    Returns:
        The loaded IntegrationEngineConfig instance
    """
    global _config
    
    if config_file is None:
        # Try to find config file in common locations
        possible_paths = [
            Path("config.yaml"),
            Path("config/config.yaml"),
            Path("integration_engine/config/config.yaml"),
            Path("../config/config.yaml"),
            Path("/etc/integration-engine/config.yaml")
        ]
        
        for path in possible_paths:
            if path.exists():
                config_file = path
                break
        else:
            # No config file found, use defaults
            _config = IntegrationEngineConfig(**kwargs)
            return _config
    
    # Load config from file
    _config = IntegrationEngineConfig.from_yaml(config_file, env_override=env_override)
    
    # Apply any additional kwargs
    if kwargs:
        _config = _config.copy(update=kwargs)
    
    # Set log level
    log_level = _config.global_config.log_level.upper()
    logging.basicConfig(level=log_level)
    
    logger.info(f"Configuration loaded from {config_file}")
    logger.info(f"Environment: {_config.global_config.environment}")
    
    return _config


def reload_config() -> IntegrationEngineConfig:
    """
    Reload the configuration from the same file.
    
    Returns:
        The reloaded IntegrationEngineConfig instance
        
    Raises:
        RuntimeError: If the configuration has not been initialized
    """
    global _config
    
    if _config is None:
        raise RuntimeError("Configuration has not been initialized. Call load_config() first.")
    
    # Get the original config file path if available
    config_file = getattr(_config, "_config_file", None)
    
    # Reload the config
    return load_config(config_file=config_file)
