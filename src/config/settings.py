"""
Configuration management module.

Loads and validates configuration from .env file using pydantic-settings.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI API Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL"
    )
    openai_model: str = Field(
        default="gpt-4",
        description="Default OpenAI model to use"
    )

    # Optional: Agent-specific models
    planner_model: Optional[str] = Field(
        default=None,
        description="Model for planning agent (defaults to openai_model)"
    )
    coder_model: Optional[str] = Field(
        default=None,
        description="Model for coding agent (defaults to openai_model)"
    )
    evaluator_model: Optional[str] = Field(
        default=None,
        description="Model for evaluation agent (defaults to openai_model)"
    )

    # Workspace Configuration
    workspace_dir: str = Field(
        default="./workspace",
        description="Directory for agent workspace"
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_file: str = Field(
        default="./logs/code-agent.log",
        description="Log file path"
    )

    # Web Search Configuration (Optional)
    brave_api_key: Optional[str] = Field(
        default=None,
        description="Brave API key for web search"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed_levels:
            raise ValueError(
                f"log_level must be one of {allowed_levels}, got {v}"
            )
        return v_upper

    @field_validator("workspace_dir", "log_file")
    @classmethod
    def expand_path(cls, v: str) -> str:
        """Expand relative paths to absolute paths."""
        return str(Path(v).expanduser().resolve())

    def get_planner_model(self) -> str:
        """Get the model name for planning agent."""
        return self.planner_model or self.openai_model

    def get_coder_model(self) -> str:
        """Get the model name for coding agent."""
        return self.coder_model or self.openai_model

    def get_evaluator_model(self) -> str:
        """Get the model name for evaluation agent."""
        return self.evaluator_model or self.openai_model

    def ensure_directories(self) -> None:
        """Ensure workspace and log directories exist."""
        Path(self.workspace_dir).mkdir(parents=True, exist_ok=True)
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create the global settings instance.

    Returns:
        Settings: The application settings.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_directories()
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment.

    Returns:
        Settings: The reloaded settings.
    """
    global _settings
    _settings = Settings()
    _settings.ensure_directories()
    return _settings
