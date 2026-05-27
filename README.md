# Agentic AI Identity Gateway (AIG)

Identity, authorization, approval, and audit layer for **agentic AI workloads**,
built on top of an enterprise IdP like Keycloak. Implements the MVP scope
described in `Agentic_Ai_Identity_Prd.pdf` (§11 / §22).

## What's in this repo

```
aig/
├── backend/      FastAPI service: agents, tools, runs, JWT issuance, JWKS,
│                  authorize, approvals, audit. SQLite by default, Postgres-ready.
├── sdk/
│   ├── python/   `aig_sdk` -- AIGAdminClient + AIGAgentClient
│   └── typescript/ @aig/sdk -- AIGClient
├── dashboard/    Next.js 14 admin dashboard (agents / tools / runs / approvals / audit)
├── examples/     `demo_seed.py` -- end-to-end smoke test
└── docker-compose.yml
```

## Quick start (local, no Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'
uvicorn app.main:app --reload --port 8080

# In another shell -- run the demo
cd ..
python examples/demo_seed.py
```

You can also browse the auto-generated API docs at `http://localhost:8080/docs`,
and the JWKS at `http://localhost:8080/.well-known/jwks.json`.

### Dashboard

```bash
cd dashboard
npm install
AIG_BACKEND_URL=http://localhost:8080 AIG_ADMIN_TOKEN=admin-dev-token npm run dev
# open http://localhost:3000
```

### Docker

```bash
docker compose up --build
# backend  -> http://localhost:8080
# dashboard -> http://localhost:3000
```

## Mapping to the PRD

| PRD section                          | Implementation                                                                    |
| ------------------------------------ | --------------------------------------------------------------------------------- |
| §10 core concepts                    | `backend/app/models.py`                                                            |
| §12.1 Agent registry                 | `backend/app/routers/agents.py`                                                    |
| §12.2 Tool registry                  | `backend/app/routers/tools.py`                                                     |
| §12.3 Agent run API                  | `backend/app/routers/agent_runs.py`                                                |
| §12.4 Token claims                   | `backend/app/auth.py::issue_run_token` (RS256, kid, iss/sub/aud/agent/run/tenant/...) |
| §12.5 Authorization check API        | `backend/app/routers/authorize.py` + `backend/app/policy.py`                       |
| §12.6 Approval workflow              | `backend/app/routers/approvals.py`                                                 |
| §12.7 Audit logging                  | `backend/app/audit.py` + `backend/app/routers/audit.py`                            |
| §12.8 Admin dashboard                | `dashboard/`                                                                       |
| §12.9 Developer SDK                  | `sdk/python/`, `sdk/typescript/`                                                   |
| §13.1 Security (deny by default, TLS) | static admin token + RS256 + deny-by-default rules in `policy.py`                 |
| §14 Policy model                     | `backend/app/policy.py` (high-risk action allowlist, tenant boundary, scope checks) |
| §15 Keycloak integration             | OIDC discovery + JWKS endpoint; `keycloak_client_id` field on agents              |
| §16 Data model                       | `backend/app/models.py` (Agent / Tool / AgentRun / Approval / AuditEvent)         |
| §17 APIs                             | `backend/app/routers/*` (all six endpoints)                                       |
| §22 MVP acceptance criteria          | `backend/tests/test_mvp_acceptance.py` -- 11 passing tests                         |

## Token model

Tokens are signed **RS256** JWTs issued by the gateway and verifiable against
`/.well-known/jwks.json`. Per §12.4 they include `agent_id`, `agent_run_id`,
`tenant_id`, `delegated_user_id`, `purpose`, `allowed_tools`, and `scope`.

A run token is the source of truth for *who* the agent is and *what it may
call*. The `/v1/authorize` endpoint accepts the token directly so the tool
gateway never has to rebuild claims from query parameters:

```http
POST /v1/authorize
{ "access_token": "eyJ...", "tool_id": "document_search", "action": "read", "resource": "doc_789" }
```

## Policy engine (MVP)

`backend/app/policy.py` is intentionally small but covers the rules the PRD
calls out (§14):

1. Agent must exist and be `active`.
2. Tool must exist and be `active`.
3. Run must exist, be `active`, and not expired.
4. Run.tenant_id == request.tenant_id (multi-tenant boundary).
5. tool_id must be in `run.allowed_tools` and in `agent.allowed_tools`.
6. action must be in `tool.allowed_actions`.
7. High-risk actions (`email:send_external`, `records:delete`,
   `permissions:update`, `purchase:create`, `code:execute_prod`,
   `data:export_sensitive`) require approval.
8. `tool.approval_required_by_default` and `risk_level in {high, critical}`
   also trigger approval.

Anything else allows. Failure of any rule denies with a machine-readable
`reason_code`. The interface (`PolicyInput` -> `PolicyDecision`) is the
seam that lets you swap in OPA or Cedar without changing the gateway.

## Audit trail

Every meaningful action emits an `AuditEvent` row with `event_id`,
`timestamp`, `tenant_id`, `agent_id`, `agent_run_id`, `delegated_user_id`,
`actor_id`, `tool_id`, `action`, `resource`, `decision`, `reason_code`,
`correlation_id`, and free-form `metadata`. The search API supports filtering
on any of these (§17.5).

Event types:

- `agent.registered`, `agent.updated`, `agent.disabled`
- `tool.registered`, `tool.updated`, `tool.disabled`
- `agent_run.created`, `token.issued`
- `authorization.decision`
- `approval.requested`, `approval.resolved`

## Tests

```bash
cd backend
pytest -q
```

11 tests cover the MVP acceptance criteria (§22): registration, scoped token
issuance with all required claims, allow/deny/require_approval decisions,
tenant boundary enforcement, disabled-agent/disabled-tool gating, approval
resolution, and audit completeness.

## Production hardening (out of MVP scope)

The PRD non-goals (§5) and "production" phase (§19) deliberately defer:

- Replace the static admin token with Keycloak admin role verification.
- Swap `policy.py` for OPA / Cedar / Keycloak Authorization Services.
- Move audit emission onto Kafka or a SIEM stream (currently DB-only).
- Add policy versioning, dry-run, and simulation.
- Add SPIFFE/SPIRE workload attestation for run identity binding.
