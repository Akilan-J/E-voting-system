from fastapi import Header, HTTPException, Request, Response
from typing import List, Optional
import time
from collections import defaultdict

# Simple in-memory rate limiter store
# { "ip_address": [timestamp1, timestamp2, ...] }
rate_limit_store = defaultdict(list)

class RateLimiter:
    """
    Dependency for Rate Limiting.
    Usage: Depends(RateLimiter(times=5, seconds=60))
    """
    def __init__(self, times: int = 10, seconds: int = 60):
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request):
        if not request.client or not request.client.host:
            # Fallback for tests or proxies
            client_ip = "127.0.0.1"
        else:
            client_ip = request.client.host
        current_time = time.time()
        
        # Get history for this IP
        history = rate_limit_store[client_ip]
        
        # Clean old requests
        valid_history = [t for t in history if current_time - t < self.seconds]
        rate_limit_store[client_ip] = valid_history
        
        if len(valid_history) >= self.times:
            raise HTTPException(
                status_code=429, 
                detail=f"Rate limit exceeded. Try again in {self.seconds} seconds."
            )
        
        # Add current request
        rate_limit_store[client_ip].append(current_time)
        return True

class RoleChecker:
    """
    Dependency for Role-Based Access Control (RBAC).
    Checks the 'X-User-Role' header.
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, x_user_role: str = Header(default="guest", alias="X-User-Role")):
        """
        Validates the role header.
        In a real app, this would decode a JWT.
        """
        if x_user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Operation not permitted. Required roles: {self.allowed_roles}"
            )
        return x_user_role
