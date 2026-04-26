"""Application configuration management."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenRouter API
    openrouter_api_key: str
    openrouter_referer: str = "http://localhost:3000"
    
    # Application
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    
    # Cache
    cache_dir: str = "./cache"
    cache_max_age_hours: int = 24
    
    # PDF Processing
    pdf_max_size_mb: int = 50
    pdf_chunk_size: int = 4000
    pdf_chunk_overlap: int = 200
    
    # Model Configuration
    primary_model: str = "qwen/qwen2.5-72b-instruct:free"
    fallback_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    temperature: float = 0.2
    max_tokens: int = 4000
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"


settings = Settings()
