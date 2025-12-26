"""FastAPI dependencies for authentication and common functionality."""

import base64
import hmac
import json
import os
import time
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Dict, Optional

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

    allow_anonymous = os.getenv("EDUSCHED_ALLOW_ANONYMOUS", "true").lower() == "true"

    # For development, optionally allow anonymous access
    if credentials is None:
        if not allow_anonymous:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return User(
            id="anonymous",
            username="anonymous",
            email="anonymous@example.com",
            is_active=True,
            is_superuser=False,
        )

    try:
        token = credentials.credentials

        jwt_secret = os.getenv("EDUSCHED_JWT_SECRET")
        if not jwt_secret:
            if allow_anonymous:
                return User(
                    id="demo",
                    username="demo_user",
                    email="demo_user@example.com",
                    is_active=True,
                    is_superuser=False,
                )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server auth not configured (missing EDUSCHED_JWT_SECRET)",
            )

        payload = _decode_and_verify_hs256_jwt(token, jwt_secret)
        _validate_claims(payload)

        user_id = str(payload.get("sub") or payload.get("user_id") or payload.get("uid") or "")
        username = str(payload.get("preferred_username") or payload.get("username") or "")
        email = str(payload.get("email") or "")

        if not user_id:
            user_id = username or "user"
        if not username:
            username = user_id
        if not email:
            email = f"{username}@example.com"

        is_active = bool(payload.get("is_active", True))
        is_superuser = bool(payload.get("is_superuser", False))

        return User(
            id=user_id,
            username=username,
            email=email,
            is_active=is_active,
            is_superuser=is_superuser,
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _b64url_decode(data: str) -> bytes:
    padding_needed = (-len(data)) % 4
    return base64.urlsafe_b64decode((data + ("=" * padding_needed)).encode("utf-8"))


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _decode_and_verify_hs256_jwt(token: str, secret: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")

    header_b64, payload_b64, signature_b64 = parts
    header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
    if header.get("alg") != "HS256":
        raise ValueError("Unsupported JWT alg")

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, sha256).digest()
    expected_sig_b64 = _b64url_encode(expected_sig)

    if not hmac.compare_digest(expected_sig_b64, signature_b64):
        raise ValueError("Invalid JWT signature")

    payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    return payload


def _validate_claims(payload: Dict[str, Any]) -> None:
    now = int(time.time())

    exp = payload.get("exp")
    if exp is not None:
        if not isinstance(exp, (int, float)):
            raise ValueError("Invalid exp claim")
        if int(exp) < now:
            raise ValueError("Token expired")

    issuer = os.getenv("EDUSCHED_JWT_ISSUER")
    if issuer:
        if payload.get("iss") != issuer:
            raise ValueError("Invalid issuer")

    audience = os.getenv("EDUSCHED_JWT_AUDIENCE")
    if audience:
        aud = payload.get("aud")
        if isinstance(aud, str):
            valid = aud == audience
        elif isinstance(aud, list):
            valid = audience in aud
        else:
            valid = False
        if not valid:
            raise ValueError("Invalid audience")


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
