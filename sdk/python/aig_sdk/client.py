from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import httpx


class AIGError(RuntimeError):
    def __init__(self, message: str, *, status_code: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


@dataclass
class RunToken:
    agent_run_id: str
    access_token: str
    expires_in: int
    issued_at: float

    @property
    def expires_at(self) -> float:
        return self.issued_at + self.expires_in

    def is_expired(self, *, leeway: int = 5) -> bool:
        return time.time() + leeway >= self.expires_at


@dataclass
class AuthorizeResult:
    decision: str  # "allow" | "deny" | "require_approval"
    reason: str
    reason_code: str
    decision_id: str
    approval_id: Optional[str]
    correlation_id: Optional[str]

    @property
    def allowed(self) -> bool:
        return self.decision == "allow"


class _BaseClient:
    def __init__(self, base_url: str, *, admin_token: Optional[str] = None, timeout: float = 10.0):
        self._base_url = base_url.rstrip("/")
        self._http = httpx.Client(base_url=self._base_url, timeout=timeout)
        self._admin_token = admin_token

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self._admin_token:
            h["Authorization"] = f"Bearer {self._admin_token}"
        return h

    def _request(self, method: str, path: str, *, json: Any = None, params: Any = None) -> Any:
        resp = self._http.request(method, path, headers=self._headers(), json=json, params=params)
        if resp.status_code >= 400:
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            raise AIGError(
                f"AIG {method} {path} failed: {resp.status_code}",
                status_code=resp.status_code,
                body=body,
            )
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "_BaseClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


class AIGAdminClient(_BaseClient):
    """Admin/control-plane client."""

    # ---- Agents ----
    def register_agent(self, **fields: Any) -> Dict[str, Any]:
        return self._request("POST", "/v1/agents", json=fields)

    def list_agents(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/v1/agents") or []

    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/v1/agents/{agent_id}")

    def disable_agent(self, agent_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/v1/agents/{agent_id}/disable")

    # ---- Tools ----
    def register_tool(self, **fields: Any) -> Dict[str, Any]:
        return self._request("POST", "/v1/tools", json=fields)

    def list_tools(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/v1/tools") or []

    def disable_tool(self, tool_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/v1/tools/{tool_id}/disable")

    # ---- Runs ----
    def create_agent_run(
        self,
        *,
        agent_id: str,
        tenant_id: str,
        purpose: str,
        delegated_user_id: Optional[str] = None,
        requested_tools: Optional[Iterable[str]] = None,
        ttl_seconds: int = 900,
        scopes: Optional[Iterable[str]] = None,
    ) -> RunToken:
        body = {
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "purpose": purpose,
            "delegated_user_id": delegated_user_id,
            "requested_tools": list(requested_tools or []),
            "ttl_seconds": ttl_seconds,
            "scopes": list(scopes or []),
        }
        issued_at = time.time()
        resp = self._request("POST", "/v1/agent-runs", json=body)
        return RunToken(
            agent_run_id=resp["agent_run_id"],
            access_token=resp["access_token"],
            expires_in=resp["expires_in"],
            issued_at=issued_at,
        )

    def list_agent_runs(self, **filters: Any) -> List[Dict[str, Any]]:
        return self._request("GET", "/v1/agent-runs", params=filters) or []

    # ---- Approvals ----
    def list_approvals(self, **filters: Any) -> List[Dict[str, Any]]:
        return self._request("GET", "/v1/approvals", params=filters) or []

    def resolve_approval(self, approval_id: str, *, decision: str, resolver_id: str, note: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/approvals/{approval_id}/resolve",
            json={"decision": decision, "resolver_id": resolver_id, "note": note},
        )

    # ---- Audit ----
    def search_audit_events(self, **filters: Any) -> List[Dict[str, Any]]:
        return self._request("GET", "/v1/audit-events", params=filters) or []


class AIGAgentClient(_BaseClient):
    """Runtime client used by an agent / tool gateway.

    Typical usage in an agent runtime:

        client = AIGAgentClient("https://aig.example", admin_token=os.environ["AIG_TOKEN"])
        run = client.start_run(agent_id="research-agent", tenant_id="t1",
                                delegated_user_id="u1", purpose="summarize",
                                requested_tools=["document_search"])

        result = client.authorize(tool_id="document_search", action="read",
                                   resource="doc_42")
        if result.allowed:
            ...  # safe to call the tool
    """

    def __init__(self, base_url: str, *, admin_token: Optional[str] = None, timeout: float = 10.0):
        super().__init__(base_url, admin_token=admin_token, timeout=timeout)
        self._run_token: Optional[RunToken] = None

    @property
    def run_token(self) -> Optional[RunToken]:
        return self._run_token

    def start_run(
        self,
        *,
        agent_id: str,
        tenant_id: str,
        purpose: str,
        delegated_user_id: Optional[str] = None,
        requested_tools: Optional[Iterable[str]] = None,
        ttl_seconds: int = 900,
        scopes: Optional[Iterable[str]] = None,
    ) -> RunToken:
        admin = AIGAdminClient(self._base_url, admin_token=self._admin_token)
        try:
            self._run_token = admin.create_agent_run(
                agent_id=agent_id,
                tenant_id=tenant_id,
                purpose=purpose,
                delegated_user_id=delegated_user_id,
                requested_tools=requested_tools,
                ttl_seconds=ttl_seconds,
                scopes=scopes,
            )
        finally:
            admin.close()
        return self._run_token

    def authorize(
        self,
        *,
        tool_id: str,
        action: str,
        resource: Optional[str] = None,
        risk_level: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> AuthorizeResult:
        if self._run_token is None:
            raise AIGError("No active run -- call start_run() first")
        if self._run_token.is_expired():
            raise AIGError("Run token expired -- start a new run")

        body = {
            "access_token": self._run_token.access_token,
            "tool_id": tool_id,
            "action": action,
            "resource": resource,
            "risk_level": risk_level,
            "correlation_id": correlation_id or f"cor_{uuid.uuid4().hex[:16]}",
        }
        resp = self._request("POST", "/v1/authorize", json=body)
        return AuthorizeResult(
            decision=resp["decision"],
            reason=resp["reason"],
            reason_code=resp["reason_code"],
            decision_id=resp["decision_id"],
            approval_id=resp.get("approval_id"),
            correlation_id=resp.get("correlation_id"),
        )
