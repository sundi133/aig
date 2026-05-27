"""Tests covering the PRD §22 MVP acceptance criteria."""

import jwt


def _register_agent(client, admin_headers, **overrides):
    body = {
        "agent_id": "research-agent",
        "display_name": "Research Agent",
        "owner_team": "AI Platform",
        "environment": "test",
        "keycloak_client_id": "research-agent-client",
        "default_scopes": ["tools:read", "documents:read"],
        "allowed_tools": ["document_search", "summarizer"],
        "status": "active",
    }
    body.update(overrides)
    r = client.post("/v1/agents", json=body, headers=admin_headers)
    assert r.status_code == 201, r.text
    return r.json()


def _register_tool(client, admin_headers, **overrides):
    body = {
        "tool_id": "document_search",
        "display_name": "Document Search",
        "owner_team": "AI Platform",
        "risk_level": "low",
        "allowed_actions": ["read"],
        "approval_required_by_default": False,
        "status": "active",
    }
    body.update(overrides)
    r = client.post("/v1/tools", json=body, headers=admin_headers)
    assert r.status_code == 201, r.text
    return r.json()


def _create_run(client, admin_headers, **overrides):
    body = {
        "agent_id": "research-agent",
        "tenant_id": "tenant_123",
        "delegated_user_id": "user_456",
        "purpose": "summarize_contract",
        "requested_tools": ["document_search"],
        "ttl_seconds": 900,
    }
    body.update(overrides)
    r = client.post("/v1/agent-runs", json=body, headers=admin_headers)
    return r


def test_register_agent_and_tool(client, admin_headers):
    _register_agent(client, admin_headers)
    _register_tool(client, admin_headers)
    r = client.get("/v1/agents", headers=admin_headers)
    assert any(a["agent_id"] == "research-agent" for a in r.json())
    r = client.get("/v1/tools", headers=admin_headers)
    assert any(t["tool_id"] == "document_search" for t in r.json())


def test_admin_requires_bearer(client):
    r = client.get("/v1/agents")
    assert r.status_code == 401
    r = client.get("/v1/agents", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 403


def test_create_run_issues_signed_token_with_required_claims(client, admin_headers):
    _register_agent(client, admin_headers)
    _register_tool(client, admin_headers)
    r = _create_run(client, admin_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["agent_run_id"].startswith("run_")
    assert body["expires_in"] == 900

    # Verify token via JWKS.
    jwks = client.get("/.well-known/jwks.json").json()
    assert jwks["keys"], "JWKS must publish at least one key"
    # Token signature checked via the same key fetched directly by the test --
    # we use the public PEM from the key cache for simplicity.
    from app.keys import get_signing_key

    pub = get_signing_key().public_pem
    claims = jwt.decode(
        body["access_token"],
        pub,
        algorithms=["RS256"],
        audience="tool-gateway",
        issuer="https://identity.test",
    )
    for required in (
        "iss", "sub", "aud", "agent_id", "agent_run_id", "tenant_id",
        "delegated_user_id", "purpose", "allowed_tools", "scope", "iat", "exp",
    ):
        assert required in claims, f"missing claim {required!r}"
    assert claims["agent_id"] == "research-agent"
    assert claims["agent_run_id"] == body["agent_run_id"]
    assert claims["tenant_id"] == "tenant_123"
    assert "document_search" in claims["allowed_tools"]


def test_run_rejects_tools_not_in_agent_scope(client, admin_headers):
    _register_agent(client, admin_headers)
    _register_tool(client, admin_headers)
    r = _create_run(client, admin_headers, requested_tools=["forbidden_tool"])
    assert r.status_code == 403


def test_disabled_agent_cannot_get_token(client, admin_headers):
    _register_agent(client, admin_headers)
    _register_tool(client, admin_headers)
    r = client.post("/v1/agents/research-agent/disable", headers=admin_headers)
    assert r.status_code == 200
    r = _create_run(client, admin_headers)
    assert r.status_code == 403


def test_authorization_allow_deny_and_require_approval(client, admin_headers):
    _register_agent(
        client,
        admin_headers,
        allowed_tools=["document_search", "summarizer", "email"],
    )
    _register_tool(client, admin_headers)
    _register_tool(
        client,
        admin_headers,
        tool_id="email",
        display_name="Email",
        risk_level="high",
        allowed_actions=["send_external"],
        approval_required_by_default=False,
    )
    _register_tool(
        client,
        admin_headers,
        tool_id="summarizer",
        display_name="Summarizer",
        risk_level="low",
        allowed_actions=["run"],
    )

    run = _create_run(
        client,
        admin_headers,
        requested_tools=["document_search", "email"],
    ).json()
    token = run["access_token"]

    # allow path -- token-driven
    r = client.post(
        "/v1/authorize",
        json={
            "access_token": token,
            "tool_id": "document_search",
            "action": "read",
            "resource": "doc_789",
            "risk_level": "low",
        },
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["decision"] == "allow"
    assert j["decision_id"].startswith("dec_")
    assert j["correlation_id"]

    # require_approval path -- email:send_external is in HIGH_RISK_ACTIONS
    r = client.post(
        "/v1/authorize",
        json={
            "access_token": token,
            "tool_id": "email",
            "action": "send_external",
            "resource": "ceo@example.com",
            "risk_level": "high",
        },
        headers=admin_headers,
    )
    assert r.status_code == 200
    j = r.json()
    assert j["decision"] == "require_approval"
    assert j["approval_id"] and j["approval_id"].startswith("app_")

    # deny path -- summarizer is in agent scope but NOT in this run's allowed_tools
    r = client.post(
        "/v1/authorize",
        json={
            "access_token": token,
            "tool_id": "summarizer",
            "action": "run",
        },
        headers=admin_headers,
    )
    assert r.status_code == 200
    j = r.json()
    assert j["decision"] == "deny"
    assert j["reason_code"] == "tool_not_in_run_scope"


def test_disabled_tool_cannot_be_authorized(client, admin_headers):
    _register_agent(client, admin_headers)
    _register_tool(client, admin_headers)
    run = _create_run(client, admin_headers).json()

    client.post("/v1/tools/document_search/disable", headers=admin_headers)
    r = client.post(
        "/v1/authorize",
        json={"access_token": run["access_token"], "tool_id": "document_search", "action": "read"},
        headers=admin_headers,
    )
    assert r.json()["decision"] == "deny"
    assert r.json()["reason_code"] == "tool_disabled"


def test_tenant_mismatch_is_denied(client, admin_headers):
    _register_agent(client, admin_headers)
    _register_tool(client, admin_headers)
    run = _create_run(client, admin_headers).json()
    r = client.post(
        "/v1/authorize",
        json={
            # Override claims-derived tenant by NOT passing access_token.
            "agent_id": "research-agent",
            "agent_run_id": run["agent_run_id"],
            "tenant_id": "tenant_OTHER",
            "tool_id": "document_search",
            "action": "read",
        },
        headers=admin_headers,
    )
    assert r.json()["decision"] == "deny"
    assert r.json()["reason_code"] == "tenant_mismatch"


def test_approval_resolution_flow(client, admin_headers):
    _register_agent(client, admin_headers, allowed_tools=["email"])
    _register_tool(
        client,
        admin_headers,
        tool_id="email",
        display_name="Email",
        risk_level="high",
        allowed_actions=["send_external"],
    )
    run = _create_run(
        client,
        admin_headers,
        requested_tools=["email"],
    ).json()
    auth = client.post(
        "/v1/authorize",
        json={"access_token": run["access_token"], "tool_id": "email", "action": "send_external"},
        headers=admin_headers,
    ).json()
    approval_id = auth["approval_id"]

    r = client.post(
        f"/v1/approvals/{approval_id}/resolve",
        json={"decision": "approved", "resolver_id": "user:security-lead", "note": "ok"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    # Idempotency: cannot resolve twice.
    r = client.post(
        f"/v1/approvals/{approval_id}/resolve",
        json={"decision": "rejected", "resolver_id": "user:security-lead"},
        headers=admin_headers,
    )
    assert r.status_code == 409


def test_audit_log_captures_full_run(client, admin_headers):
    _register_agent(client, admin_headers)
    _register_tool(client, admin_headers)
    run = _create_run(client, admin_headers).json()
    client.post(
        "/v1/authorize",
        json={"access_token": run["access_token"], "tool_id": "document_search", "action": "read"},
        headers=admin_headers,
    )

    r = client.get(
        "/v1/audit-events",
        params={"agent_run_id": run["agent_run_id"]},
        headers=admin_headers,
    )
    assert r.status_code == 200
    events = r.json()
    types = {e["event_type"] for e in events}
    assert {"agent_run.created", "token.issued", "authorization.decision"}.issubset(types)


def test_jwks_publishes_signing_key(client):
    r = client.get("/.well-known/jwks.json")
    assert r.status_code == 200
    j = r.json()
    assert j["keys"][0]["kty"] == "RSA"
    assert j["keys"][0]["alg"] == "RS256"
    assert j["keys"][0]["kid"]
