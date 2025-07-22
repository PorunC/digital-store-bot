"""Webhook middleware for security and rate limiting."""

import time
import logging
from typing import Dict, Any
from collections import defaultdict, deque

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class WebhookMiddleware(BaseHTTPMiddleware):
    """Middleware for webhook security and rate limiting."""
    
    def __init__(self, app, max_requests: int = 100, time_window: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_history: Dict[str, deque] = defaultdict(deque)
        
    async def dispatch(self, request: Request, call_next):
        """Process webhook request with security checks."""
        try:
            # Only apply to webhook endpoints
            if not request.url.path.startswith("/webhooks"):
                return await call_next(request)
            
            # Get client IP
            client_ip = self._get_client_ip(request)
            
            # Rate limiting
            if not self._check_rate_limit(client_ip):
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": "Too many webhook requests from this IP"
                    }
                )
            
            # Content type validation
            if not self._validate_content_type(request):
                logger.warning(f"Invalid content type from IP: {client_ip}")
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Invalid content type",
                        "message": "Expected application/json"
                    }
                )
            
            # Size limit check
            if not await self._check_content_size(request):
                logger.warning(f"Content too large from IP: {client_ip}")
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": "Content too large",
                        "message": "Webhook payload exceeds size limit"
                    }
                )
            
            # Add security headers
            response = await call_next(request)
            self._add_security_headers(response)
            
            # Log successful webhook
            logger.info(f"Webhook processed successfully from IP: {client_ip}, Path: {request.url.path}")
            
            return response
            
        except Exception as e:
            logger.error(f"Webhook middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": "Failed to process webhook"
                }
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address with proxy support."""
        # Check for forwarded headers (for reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        forwarded = request.headers.get("X-Forwarded")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if client is within rate limits."""
        current_time = time.time()
        requests = self.request_history[client_ip]
        
        # Remove old requests outside time window
        while requests and requests[0] < current_time - self.time_window:
            requests.popleft()
        
        # Check if under limit
        if len(requests) >= self.max_requests:
            return False
        
        # Add current request
        requests.append(current_time)
        return True
    
    def _validate_content_type(self, request: Request) -> bool:
        """Validate request content type."""
        content_type = request.headers.get("content-type", "")
        return content_type.startswith("application/json")
    
    async def _check_content_size(self, request: Request, max_size: int = 1024 * 1024) -> bool:
        """Check if content size is within limits (1MB default)."""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                return size <= max_size
            except ValueError:
                return False
        return True
    
    def _add_security_headers(self, response) -> None:
        """Add security headers to response."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    
    def get_rate_limit_status(self, client_ip: str) -> Dict[str, Any]:
        """Get current rate limit status for an IP."""
        current_time = time.time()
        requests = self.request_history.get(client_ip, deque())
        
        # Clean old requests
        while requests and requests[0] < current_time - self.time_window:
            requests.popleft()
        
        return {
            "client_ip": client_ip,
            "requests_in_window": len(requests),
            "max_requests": self.max_requests,
            "time_window": self.time_window,
            "remaining_requests": max(0, self.max_requests - len(requests)),
            "reset_time": current_time + self.time_window if requests else None
        }