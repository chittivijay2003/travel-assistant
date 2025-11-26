"""Application configuration settings.

This module manages all configuration settings for the Travel Assistant API,
including API keys, model configurations, and server settings.
All settings are loaded from environment variables using pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be configured via environment variables or .env file.
    Required settings will raise an error if not provided.
    """

    # Google Gemini API Configuration
    google_api_key: str  # Required - will fail if not set

    # Gemini Model Configuration
    gemini_flash_model: str = "gemini-2.5-flash"  # Latest stable Flash model

    # Model Parameters
    model_temperature: float = 0.7  # Controls randomness (0.0-1.0)
    max_output_tokens: int = 2048  # Max output tokens

    # API Server Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False

    # Application Metadata
    app_name: str = "Travel Assistant API"
    app_version: str = "0.1.0"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    def get_model_name(self) -> str:
        """Get the Gemini model name."""
        return self.gemini_flash_model


# Global settings instance - import this in other modules
settings = Settings()
