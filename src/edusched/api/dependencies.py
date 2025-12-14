"""FastAPI dependencies for authentication and common functionality."""

from typing import TYPE_CHECKING, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

if TYPE_CHECKING:
    from edusched.api.models import User

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> "User":
    """
    Get the current authenticated user.

    For now, this is a placeholder implementation that accepts any token
    and returns a mock user. In a production environment, this would:
    1. Validate the JWT token
    2. Look up the user in the database
    3. Check if the user is active
    4. Return the user object

    Args:
        credentials: Optional HTTP Bearer credentials

    Returns:
        User object

    Raises:
        HTTPException: If authentication fails
    """
    # Placeholder user model
    from edusched.api.models import User

    # For development, accept any token and return a mock user
    if credentials is None:
        # No token provided - create anonymous user for testing
        return User(
            id="anonymous",
            username="anonymous",
            email="anonymous@example.com",
            is_active=True,
            is_superuser=False,
        )

    # For now, just validate that a token was provided
    # In production, you would decode and validate the JWT token
    try:
        # Placeholder token validation
        # TODO: Implement proper JWT validation
        token = credentials.credentials

        # For demo purposes, extract username from token if it looks like a simple token
        if token.startswith("user:"):
            username = token[5:]  # Remove "user:" prefix
        else:
            username = "demo_user"

        return User(
            id="demo",
            username=username,
            email=f"{username}@example.com",
            is_active=True,
            is_superuser=False,
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_active_user(current_user: "User" = Depends(get_current_user)) -> "User":
    """
    Get the current active user.

    Args:
        current_user: User from get_current_user

    Returns:
        Active user object

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


async def get_superuser(current_user: "User" = Depends(get_active_user)) -> "User":
    """
    Get the current superuser.

    Args:
        current_user: User from get_active_user

    Returns:
        Superuser object

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user


class RateLimiter:
    """Simple rate limiter for API endpoints.

    For development purposes, this is a placeholder implementation.
    In production, you would use Redis or another distributed cache
    to track request rates across multiple server instances.
    """

    def __init__(self, requests_per_minute: int = 60):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute per IP
        """
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # In production, use Redis

    async def check_rate_limit(self, client_ip: str) -> bool:
        """
        Check if client has exceeded rate limit.

        Args:
            client_ip: Client IP address

        Returns:
            True if request is allowed, False otherwise
        """
        import time
        from collections import deque

        now = time.time()
        minute_ago = now - 60

        # Get or create request queue for this IP
        if client_ip not in self.requests:
            self.requests[client_ip] = deque()

        # Remove old requests
        while self.requests[client_ip] and self.requests[client_ip][0] < minute_ago:
            self.requests[client_ip].popleft()

        # Check if under limit
        if len(self.requests[client_ip]) < self.requests_per_minute:
            self.requests[client_ip].append(now)
            return True

        return False


# Rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=100)


async def check_rate_limit(client_ip: str = None):
    """
    Dependency to check rate limit.

    Args:
        client_ip: Client IP address (injected by FastAPI)

    Raises:
        HTTPException: If rate limit exceeded
    """
    if client_ip and not await rate_limiter.check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
        )
