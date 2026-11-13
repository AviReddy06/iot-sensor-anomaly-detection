"""
backend/routes/auth_routes.py
Authentication route for admin login.
Validates credentials from the environment, rate-limits attempts, and returns signed tokens.
"""

from __future__ import annotations
import hmac
from fastapi import APIRouter, HTTPException, Request, status
from backend import config
from backend.auth import (
    TOKEN_EXPIRY_SECONDS,
    check_rate_limit,
    generate_signed_token,
)
from backend.database import log_audit
from backend.schemas.admin_schemas import AdminLoginRequest, AdminLoginResponse

router = APIRouter(tags=["auth"])


@router.post("/api/auth/login", response_model=AdminLoginResponse)
def login_admin(req: AdminLoginRequest, request: Request):
    # Step 1: If ADMIN_PASSWORD is unset in environment, return 503
    if not config.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin access is unavailable: ADMIN_PASSWORD environment variable is not set.",
        )

    # Step 2: Rate limit checks per client IP address (max 5 per minute)
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_rate_limit(client_ip)

    # Step 3: Validate password using constant-time comparison (password is never logged)
    is_valid = hmac.compare_digest(req.password.strip(), config.ADMIN_PASSWORD.strip())
    if not is_valid:
        log_audit("LOGIN_FAILED", client_ip, "Invalid admin password attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
        )

    # Step 4: Issue signed expiring token
    token = generate_signed_token()
    log_audit("LOGIN_SUCCESS", client_ip, "Admin successfully authenticated")

    return AdminLoginResponse(
        token=token,
        token_type="bearer",
        expires_in_seconds=TOKEN_EXPIRY_SECONDS,
    )
