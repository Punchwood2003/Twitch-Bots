"""
Database Configuration Management

This module provides configuration management for database connections,
integrating with environment variables and providing validation.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    """
    Database configuration with validation and environment variable support.
    
    Supports both direct PostgreSQL connections and Supabase configurations.
    All settings can be overridden via environment variables with DB_ prefix.
    """
    
    # Core Database Connection
    db_user: str = Field(..., env="DB_USER", description="Database username")
    db_password: str = Field(..., env="DB_PASSWORD", description="Database password")
    db_host: str = Field(..., env="DB_HOST", description="Database host")
    db_port: int = Field(5432, env="DB_PORT", description="Database port")
    db_name: str = Field(..., env="DB_NAME", description="Database name")
    
    # Supabase API Configuration
    supabase_url: Optional[str] = Field(None, env="SUPABASE_URL", description="Supabase project URL")
    supabase_anon_key: Optional[str] = Field(None, env="SUPABASE_ANON_KEY", description="Supabase anonymous key")
    supabase_service_role_key: Optional[str] = Field(None, env="SUPABASE_SERVICE_ROLE_KEY", description="Supabase service role key")
    
    # Connection Pool Settings
    db_pool_size: int = Field(10, env="DB_POOL_SIZE", description="Database connection pool size")
    db_max_overflow: int = Field(20, env="DB_MAX_OVERFLOW", description="Maximum connection overflow")
    db_echo: bool = Field(False, env="DB_ECHO", description="Enable SQL query logging")
    
    # Timeout Settings
    db_connect_timeout: int = Field(30, env="DB_CONNECT_TIMEOUT", description="Connection timeout in seconds")
    db_query_timeout: int = Field(60, env="DB_QUERY_TIMEOUT", description="Query timeout in seconds")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator('db_port')
    def validate_port(cls, v):
        """Validate database port is in valid range."""
        if not (1 <= v <= 65535):
            raise ValueError('Database port must be between 1 and 65535')
        return v
    
    @validator('db_pool_size')
    def validate_pool_size(cls, v):
        """Validate pool size is reasonable."""
        if v < 1:
            raise ValueError('Pool size must be at least 1')
        if v > 100:
            raise ValueError('Pool size should not exceed 100 for most applications')
        return v
    
    @property
    def database_url(self) -> str:
        """
        Generate the complete database URL for SQLAlchemy.
        
        Returns:
            str: PostgreSQL connection URL
        """
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def sync_database_url(self) -> str:
        """
        Generate synchronous database URL for migrations.
        
        Returns:
            str: Synchronous PostgreSQL connection URL
        """
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    def get_connection_params(self) -> Dict[str, Any]:
        """
        Get connection parameters for direct asyncpg usage.
        
        Returns:
            Dict[str, Any]: Connection parameters
        """
        return {
            "host": self.db_host,
            "port": self.db_port,
            "user": self.db_user,
            "password": self.db_password,
            "database": self.db_name,
            "command_timeout": self.db_query_timeout,
        }
    
    @classmethod
    def from_env_file(cls, env_file_path: Optional[Path] = None) -> "DatabaseConfig":
        """
        Create configuration from environment file.
        
        Args:
            env_file_path: Optional path to .env file. Defaults to db/.env
            
        Returns:
            DatabaseConfig: Configured instance
        """
        if env_file_path is None:
            env_file_path = Path(__file__).parent / ".env"
        
        if env_file_path.exists():
            return cls(_env_file=str(env_file_path))
        else:
            # Fall back to environment variables only
            return cls()


# Global configuration instance
_config: Optional[DatabaseConfig] = None


def get_database_config(env_file_path: Optional[Path] = None) -> DatabaseConfig:
    """
    Get or create the global database configuration instance.
    
    Args:
        env_file_path: Optional path to environment file
        
    Returns:
        DatabaseConfig: Global configuration instance
    """
    global _config
    if _config is None:
        _config = DatabaseConfig.from_env_file(env_file_path)
    return _config


def reset_database_config() -> None:
    """Reset the global configuration (useful for testing)."""
    global _config
    _config = None
