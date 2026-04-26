"""FastAPI application factory."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api import router

# Setup logging
setup_logging()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="GPT Study Wrapper API",
        description="AI-powered exam preparation assistant",
        version="1.0.0",
        debug=settings.debug
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routes
    app.include_router(router)
    
    # Startup/shutdown events
    @app.on_event("startup")
    async def startup():
        """Initialize on startup."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Starting {app.title} in {settings.environment} mode")
        logger.info(f"Primary model: {settings.primary_model}")
        logger.info(f"Cache directory: {settings.cache_dir}")
    
    @app.on_event("shutdown")
    async def shutdown():
        """Cleanup on shutdown."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Shutting down {app.title}")
    
    return app


app = create_app()
