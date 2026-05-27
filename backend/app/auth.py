"""Auth helpers: admin token verification and run-token JWT issuance/verification."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, Header, HTTPException, status

from .config import Settings, get_settings
from .keys import get_signing_key


# ---------- Admin auth ----------

def require_admin(
    authorization: Optional[str] = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> str:
    """Validate ``Authorization: Bearer <token>`` against the admin token set.

    In production this would verify a Keycloak-issued JWT and check for an
    admin role. For MVP we accept any of the static tokens configured via
    ``AIG_ADMIN_TOKENS``.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(None, 1)[1].strip()
    if token not in settings.admin_token_set:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an admin")
    # The "actor" is just the token tail for now; good enough for audit attribution.
    return f"admin:{token[-6:]}" if len(token) >= 6 else "admin"


# ---------- Run-token issuance ----------

def issue_run_token(
    *,
    agent_id: str,
    agent_run_id: str,
    tenant_id: str,
    delegated_user_id: Optional[str],
    purpose: str,
    allowed_tools: list[str],
    scopes: list[str],
    ttl_seconds: int,
) -> tuple[str, int, int]:
    """Issue an RS256-signed task-scoped JWT for an agent run.

    Returns ``(jwt, iat, exp)``.
    """
    settings = get_settings()
    key = get_signing_key()

    now = int(time.time())
    exp = now + ttl_seconds

    claims: Dict[str, Any] = {
        "iss": settings.issuer,
        "sub": f"agent:{agent_id}",
        "aud": settings.token_audience,
        "agent_id": agent_id,
        "agent_run_id": agent_run_id,
        "tenant_id": tenant_id,
        "delegated_user_id": delegated_user_id,
        "purpose": purpose,
        "allowed_tools": allowed_tools,
        "scope": " ".join(scopes),
        "iat": now,
        "exp": exp,
    }
    token = jwt.encode(
        claims,
        key.private_pem,
        algorithm="RS256",
        headers={"kid": key.kid, "typ": "JWT"},
    )
    return token, now, exp


def verify_run_token(token: str, *, audience: Optional[str] = None) -> Dict[str, Any]:
    """Verify a run token's signature, audience, and expiration."""
    settings = get_settings()
    key = get_signing_key()
    try:
        claims = jwt.decode(
            token,
            key.public_pem,
            algorithms=["RS256"],
            audience=audience or settings.token_audience,
            issuer=settings.issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")
    return claims


def claims_age_seconds(claims: Dict[str, Any]) -> int:
    iat = claims.get("iat", 0)
    return int(time.time()) - int(iat)


def claims_expiry(claims: Dict[str, Any]) -> datetime:
    return datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc)
