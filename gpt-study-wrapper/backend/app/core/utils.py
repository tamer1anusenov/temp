"""Development utilities and helpers."""
import asyncio
import time
from functools import wraps
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)


def async_timer(func: Callable) -> Callable:
    """Decorator to time async functions."""
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{func.__name__} took {duration:.2f}s")
        return result
    return wrapper


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for retry logic with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
        
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed. Retrying in {delay}s...")
                    time.sleep(delay)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def validate_pdf_size(max_mb: int = 50) -> Callable:
    """Decorator to validate PDF file size."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(file_path: str, *args: Any, **kwargs: Any) -> Any:
            from pathlib import Path
            size_mb = Path(file_path).stat().st_size / (1024 * 1024)
            if size_mb > max_mb:
                raise ValueError(f"File too large: {size_mb:.1f}MB (max {max_mb}MB)")
            return func(file_path, *args, **kwargs)
        return wrapper
    return decorator
