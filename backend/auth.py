"""
backend/auth.py
Authentication, rate limiting, and signed token handling.
Enforces admin protection, 5 attempts per minute per IP, and no password logging.
"""

from __future__ import annotations
import base64
from datetime import datetime, timezone
import hashlib
import hmac
import time
from typing import Dict, List, Optional
from fastapi import HTTPException, Header, Request, status
from backend import config


def _get_token_secret() -> bytes:
    pwd = config.ADMIN_PASSWORD or "iot_default_token_key"
    return hashlib.sha256(pwd.encode("utf-8")).digest()


TOKEN_EXPIRY_SECONDS: int = 3600 * 8  # 8 hours

# Rate limiting storage: ip -> list of failed attempt timestamps
_LOGIN_ATTEMPTS: Dict[str, List[float]] = {}
MAX_ATTEMPTS_PER_MINUTE: int = 5


def check_rate_limit(client_ip: str) -> None:
    # Step 1: Get current epoch time and prune attempts older than 60s
    now = time.time()
    attempts = _LOGIN_ATTEMPTS.get(client_ip, [])
    valid_attempts = [t for t in attempts if now - t < 60.0]
    _LOGIN_ATTEMPTS[client_ip] = valid_attempts

    # Step 2: Reject if rate limit reached
    if len(valid_attempts) >= MAX_ATTEMPTS_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait 1 minute.",
        )


def record_failed_attempt(client_ip: str) -> None:
    # Step 1: Record timestamped failed login attempt
    now = time.time()
    attempts = _LOGIN_ATTEMPTS.get(client_ip, [])
    valid_attempts = [t for t in attempts if now - t < 60.0]
    valid_attempts.append(now)
    _LOGIN_ATTEMPTS[client_ip] = valid_attempts


def clear_rate_limit(client_ip: str) -> None:
    # Step 1: Clear failed attempts on successful authentication
    _LOGIN_ATTEMPTS.pop(client_ip, None)


def generate_signed_token() -> str:
    # Step 1: Calculate expiry timestamp
    expiry = int(time.time()) + TOKEN_EXPIRY_SECONDS
    payload = f"admin:{expiry}".encode("utf-8")
    # Step 2: Compute HMAC-SHA256 signature
    sig = hmac.new(_get_token_secret(), payload, hashlib.sha256).hexdigest()
    # Step 3: Base64-encode payload and signature
    token_str = f"{expiry}:{sig}"
    return base64.urlsafe_b64encode(token_str.encode("utf-8")).decode("utf-8")


def verify_signed_token(token: str) -> bool:
    try:
        # Step 1: Decode token string
        raw = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        parts = raw.split(":")
        if len(parts) != 2:
            return False
        expiry = int(parts[0])
        provided_sig = parts[1]
        # Step 2: Verify timestamp has not expired
        if time.time() > expiry:
            return False
        # Step 3: Verify HMAC signature matches
        payload = f"admin:{expiry}".encode("utf-8")
        expected_sig = hmac.new(_get_token_secret(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(provided_sig, expected_sig)
    except Exception:
        return False


def require_admin_token(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> str:
    # Step 1: If ADMIN_PASSWORD is unset, admin routes return 503
    if not config.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin access is unavailable: ADMIN_PASSWORD environment variable is not set.",
        )
    # Step 2: Extract token from header or query param
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    elif "token" in request.query_params:
        token = request.query_params["token"]

    if not token or not verify_signed_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token.",
        )
    return token
