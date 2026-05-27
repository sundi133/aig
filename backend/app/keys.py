"""RSA signing key management.

For MVP we generate (or load) an RSA-2048 key pair on first launch and persist
it under ``settings.key_dir``. Production deployments should mount keys from a
secret manager and disable on-disk generation.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

from .config import get_settings


@dataclass
class SigningKey:
    kid: str
    private_pem: bytes
    public_pem: bytes
    private_key: RSAPrivateKey
    public_key: RSAPublicKey


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big") or b"\x00"
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _load_or_create() -> SigningKey:
    settings = get_settings()

    if settings.private_key_pem and settings.public_key_pem:
        priv_pem = settings.private_key_pem.encode()
        pub_pem = settings.public_key_pem.encode()
    else:
        _ensure_dir(settings.key_dir)
        priv_path = os.path.join(settings.key_dir, "signing.private.pem")
        pub_path = os.path.join(settings.key_dir, "signing.public.pem")

        if not (os.path.exists(priv_path) and os.path.exists(pub_path)):
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            priv_pem = key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            pub_pem = key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            with open(priv_path, "wb") as f:
                f.write(priv_pem)
            os.chmod(priv_path, 0o600)
            with open(pub_path, "wb") as f:
                f.write(pub_pem)
        else:
            with open(priv_path, "rb") as f:
                priv_pem = f.read()
            with open(pub_path, "rb") as f:
                pub_pem = f.read()

    private_key = serialization.load_pem_private_key(priv_pem, password=None)
    if not isinstance(private_key, RSAPrivateKey):
        raise RuntimeError("Configured signing key is not an RSA key")
    public_key = private_key.public_key()

    return SigningKey(
        kid=settings.signing_key_id,
        private_pem=priv_pem,
        public_pem=pub_pem,
        private_key=private_key,
        public_key=public_key,
    )


@lru_cache
def get_signing_key() -> SigningKey:
    return _load_or_create()


def jwks() -> Dict[str, Any]:
    """Return the public JWKS document for JWT verification."""
    key = get_signing_key()
    numbers = key.public_key.public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": key.kid,
                "n": _b64url_uint(numbers.n),
                "e": _b64url_uint(numbers.e),
            }
        ]
    }
