from fastapi import APIRouter

from ..config import get_settings
from ..keys import jwks as _jwks

router = APIRouter(tags=["wellknown"])


@router.get("/.well-known/openid-configuration")
def openid_configuration() -> dict:
    settings = get_settings()
    base = settings.issuer.rstrip("/")
    return {
        "issuer": settings.issuer,
        "jwks_uri": f"{base}/.well-known/jwks.json",
        "id_token_signing_alg_values_supported": ["RS256"],
        "response_types_supported": ["token"],
        "subject_types_supported": ["public"],
        "scopes_supported": ["tools:read", "tools:write", "documents:read"],
    }


@router.get("/.well-known/jwks.json")
def jwks_endpoint() -> dict:
    return _jwks()
