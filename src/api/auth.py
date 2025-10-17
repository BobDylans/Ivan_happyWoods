"""
API Key Authentication Middleware

Provides API key-based authentication for FastAPI endpoints.
Keys are configured via environment variables.
"""
import os
import logging
from typing import Optional, List
from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate API keys for protected endpoints.
    
    Configuration:
        API_KEYS: Comma-separated list of valid API keys (env var)
        API_KEY_ENABLED: Set to "false" to disable auth (default: true)
    
    Exempt paths:
        - /health
        - /docs
        - /openapi.json
        - /redoc
    """
    
    def __init__(self, app, exempt_paths: Optional[List[str]] = None):
        super().__init__(app)
        
        # Load configuration
        self.enabled = os.getenv("API_KEY_ENABLED", "true").lower() != "false"
        
        # Load valid API keys from environment
        keys_str = os.getenv("API_KEYS", "")
        self.valid_keys = set(k.strip() for k in keys_str.split(",") if k.strip())
        
        # Default exempt paths
        self.exempt_paths = exempt_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/favicon.ico",
            "/api/v1/health"  # Health check 不需要认证
        ]
        
        if self.enabled:
            if not self.valid_keys:
                logger.warning(
                    "API key authentication enabled but no keys configured. "
                    "Set API_KEYS environment variable."
                )
            else:
                logger.info(f"API key authentication enabled with {len(self.valid_keys)} key(s)")
        else:
            logger.info("API key authentication disabled")
    
    async def dispatch(self, request: Request, call_next):
        """Process request and validate API key if required."""
        
        # Skip if auth disabled
        if not self.enabled:
            return await call_next(request)
        
        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Check if path is exempt
        path = request.url.path
        if any(path.startswith(exempt) for exempt in self.exempt_paths):
            return await call_next(request)
        
        # Extract API key from header
        api_key = request.headers.get("X-API-Key")
        
        # Validate
        if not api_key:
            logger.warning(f"Missing API key for {request.method} {path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing API key. Include X-API-Key header."},
                headers={"WWW-Authenticate": "APIKey"},
            )
        
        if self.valid_keys and api_key not in self.valid_keys:
            logger.warning(f"Invalid API key attempt for {request.method} {path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Invalid API key"},
            )
        
        # Key valid, proceed
        logger.debug(f"API key validated for {request.method} {path}")
        return await call_next(request)


def get_api_key(api_key: str = api_key_header) -> str:
    """
    Dependency for extracting and validating API key.
    Use this as FastAPI dependency in routes that need auth.
    
    Example:
        @app.get("/protected")
        async def protected_route(api_key: str = Depends(get_api_key)):
            ...
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "APIKey"},
        )
    
    # Validate against configured keys
    keys_str = os.getenv("API_KEYS", "")
    valid_keys = set(k.strip() for k in keys_str.split(",") if k.strip())
    
    if valid_keys and api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return api_key
