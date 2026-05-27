from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AIG_", env_file=".env", extra="ignore")

    # Service identity
    issuer: str = "https://identity.local.aig"
    token_audience: str = "tool-gateway"

    # Storage
    database_url: str = "sqlite:///./aig.db"

    # Signing keys (PEM). If unset, a key pair is generated on first launch and
    # cached under ./keys/.
    private_key_pem: Optional[str] = None
    public_key_pem: Optional[str] = None
    key_dir: str = "./keys"
    signing_key_id: str = "aig-key-1"

    # Admin authentication. Comma-separated list of static bearer tokens that
    # may call write/admin APIs. In production this would be replaced with
    # Keycloak-issued admin tokens.
    admin_tokens: str = "admin-dev-token"

    # Token issuance defaults
    default_token_ttl_seconds: int = 900
    max_token_ttl_seconds: int = 3600

    # Keycloak (optional). When set, JWTs presented to the gateway by humans/
    # clients may be verified against this issuer's JWKS. Not required for MVP.
    keycloak_issuer: Optional[str] = None
    keycloak_jwks_url: Optional[str] = None

    # Policy
    fail_closed: bool = True

    # CORS for the dashboard
    cors_origins: str = "http://localhost:3000"

    @property
    def admin_token_set(self) -> set[str]:
        return {t.strip() for t in self.admin_tokens.split(",") if t.strip()}

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
