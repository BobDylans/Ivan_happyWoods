"""
Security Middleware

Authentication, rate limiting, and security middleware for the Voice Agent API.
"""

import time
import logging
from typing import Dict, Set, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .models import ErrorResponse

logger = logging.getLogger(__name__)


class APIKeyAuth(HTTPBearer):
    """API Key authentication handler."""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        # In production, these would come from configuration/database
        self.valid_api_keys = {
            "dev-test-key-123",  # Development key
            "demo-key-456",      # Demo key
            # Add production keys from configuration
        }
    
    async def __call__(self, request: Request) -> Optional[str]:
        """Validate API key from header."""
        # ⚠️ DEVELOPMENT MODE: API Key validation DISABLED
        # Skip authentication for all endpoints (for testing)
        logger.warning("🚨 API Key validation is DISABLED - For development only!")
        return "dev-bypass"
        
        # Skip authentication for health endpoints
        if request.url.path.startswith("/api/v1/health") or request.url.path in ["/", "/docs", "/redoc", "/openapi.json"]:
            return None
        
        # Check X-API-Key header first
        api_key = request.headers.get("X-API-Key")
        if api_key and api_key in self.valid_api_keys:
            return api_key
        
        # Fallback to Authorization header
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if credentials and credentials.credentials in self.valid_api_keys:
            return credentials.credentials
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with sliding window algorithm."""
    
    def __init__(self, app, requests_per_minute: int = 100, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        
        # Store request timestamps per API key
        self.request_history: Dict[str, deque] = defaultdict(deque)
        
        # Store blocked IPs (simple in-memory implementation)
        self.blocked_ips: Set[str] = set()
        self.ip_violations: Dict[str, int] = defaultdict(int)
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        client_ip = self._get_client_ip(request)
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            return JSONResponse(
                status_code=429,
                content=ErrorResponse(
                    error="IP address temporarily blocked due to rate limit violations",
                    error_code="IP_BLOCKED",
                    timestamp=datetime.now()
                ).dict()
            )
        
        # Skip rate limiting for health endpoints
        if request.url.path.startswith("/api/v1/health") or request.url.path in ["/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get API key for rate limiting
        api_key = request.headers.get("X-API-Key") or "anonymous"
        
        # Check rate limits
        current_time = datetime.now()
        if not self._check_rate_limit(api_key, current_time):
            # Increment IP violation count
            self.ip_violations[client_ip] += 1
            if self.ip_violations[client_ip] >= 5:  # Block after 5 violations
                self.blocked_ips.add(client_ip)
                logger.warning(f"Blocked IP {client_ip} due to repeated rate limit violations")
            
            return JSONResponse(
                status_code=429,
                content=ErrorResponse(
                    error="Rate limit exceeded",
                    error_code="RATE_LIMIT_EXCEEDED",
                    details={
                        "limit_per_minute": self.requests_per_minute,
                        "limit_per_hour": self.requests_per_hour,
                        "retry_after_seconds": 60
                    },
                    timestamp=current_time
                ).dict(),
                headers={"Retry-After": "60"}
            )
        
        # Record successful request
        self.request_history[api_key].append(current_time)
        
        # Add rate limit headers to response
        response = await call_next(request)
        self._add_rate_limit_headers(response, api_key, current_time)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check X-Forwarded-For header first (for proxy setups)
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        x_real_ip = request.headers.get("X-Real-IP")
        if x_real_ip:
            return x_real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _check_rate_limit(self, api_key: str, current_time: datetime) -> bool:
        """Check if request is within rate limits."""
        request_times = self.request_history[api_key]
        
        # Clean old requests (older than 1 hour)
        cutoff_time = current_time - timedelta(hours=1)
        while request_times and request_times[0] < cutoff_time:
            request_times.popleft()
        
        # Check hourly limit
        if len(request_times) >= self.requests_per_hour:
            return False
        
        # Check minute limit
        minute_cutoff = current_time - timedelta(minutes=1)
        recent_requests = sum(1 for req_time in request_times if req_time > minute_cutoff)
        
        return recent_requests < self.requests_per_minute
    
    def _add_rate_limit_headers(self, response, api_key: str, current_time: datetime):
        """Add rate limit information to response headers."""
        request_times = self.request_history[api_key]
        
        # Calculate remaining requests
        minute_cutoff = current_time - timedelta(minutes=1)
        requests_in_minute = sum(1 for req_time in request_times if req_time > minute_cutoff)
        requests_in_hour = len(request_times)
        
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(max(0, self.requests_per_minute - requests_in_minute))
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(max(0, self.requests_per_hour - requests_in_hour))
        response.headers["X-RateLimit-Reset"] = str(int((current_time + timedelta(minutes=1)).timestamp()))


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        )
        
        # API-specific headers
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate and sanitize incoming requests."""
    
    async def dispatch(self, request: Request, call_next):
        """Validate request before processing."""
        
        # Check request size (prevent large payloads)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
            return JSONResponse(
                status_code=413,
                content=ErrorResponse(
                    error="Request payload too large",
                    error_code="PAYLOAD_TOO_LARGE",
                    details={"max_size_mb": 10},
                    timestamp=datetime.now()
                ).dict()
            )
        
        # Validate User-Agent (block suspicious agents)
        user_agent = request.headers.get("user-agent", "").lower()
        suspicious_agents = ["bot", "crawler", "spider", "scraper"]
        if any(agent in user_agent for agent in suspicious_agents) and not any(
            allowed in user_agent for allowed in ["googlebot", "bingbot"]
        ):
            logger.warning(f"Blocked suspicious user agent: {user_agent}")
            return JSONResponse(
                status_code=403,
                content=ErrorResponse(
                    error="Access denied",
                    error_code="FORBIDDEN",
                    timestamp=datetime.now()
                ).dict()
            )
        
        return await call_next(request)


# Dependency for API key authentication
api_key_auth = APIKeyAuth()


async def get_current_api_key(api_key: str = api_key_auth) -> str:
    """Dependency to get current API key."""
    return api_key


# Rate limiting configuration
def create_rate_limit_middleware(requests_per_minute: int = 100, requests_per_hour: int = 1000):
    """Factory function to create rate limit middleware with custom limits."""
    return lambda app: RateLimitMiddleware(app, requests_per_minute, requests_per_hour)


# Cleanup utility for blocked IPs (would run periodically in production)
def cleanup_blocked_ips(middleware: RateLimitMiddleware, max_age_hours: int = 24):
    """Clean up old blocked IPs."""
    # In production, this would be implemented with a proper scheduler
    current_time = datetime.now()
    # Reset IP violations older than max_age_hours
    # This is a simplified implementation
    pass