"""Request/response middleware and utilities."""
import time
import logging
from fastapi import Request
from typing import Callable

logger = logging.getLogger(__name__)


class RequestTimingMiddleware:
    """Middleware to log request timing."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )
        
        return response
