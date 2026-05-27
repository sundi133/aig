import os
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def _env() -> None:
    tmp = tempfile.mkdtemp(prefix="aig-test-")
    os.environ["AIG_DATABASE_URL"] = f"sqlite:///{tmp}/aig-test.db"
    os.environ["AIG_KEY_DIR"] = f"{tmp}/keys"
    os.environ["AIG_ADMIN_TOKENS"] = "admin-test"
    os.environ["AIG_ISSUER"] = "https://identity.test"

    # Reset cached settings/keys so the env overrides take effect.
    from app.config import get_settings
    from app.keys import get_signing_key

    get_settings.cache_clear()
    get_signing_key.cache_clear()


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    # Late import so env vars are honored.
    from app.db import Base, engine
    from app.main import create_app

    # Fresh DB per test for isolation.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_headers() -> dict:
    return {"Authorization": "Bearer admin-test"}
