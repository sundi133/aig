"""Seed a few agents, tools, and a run -- and demonstrate the auth flow.

Run after `uvicorn app.main:app --reload`:

    AIG_TOKEN=admin-dev-token python examples/demo_seed.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sdk", "python"))

from aig_sdk import AIGAdminClient, AIGAgentClient

BASE = os.environ.get("AIG_BASE_URL", "http://localhost:8080")
TOKEN = os.environ.get("AIG_TOKEN", "admin-dev-token")


def _maybe(call):
    try:
        return call()
    except Exception as exc:
        if "already exists" in str(exc):
            return None
        raise


def main() -> None:
    admin = AIGAdminClient(BASE, admin_token=TOKEN)

    _maybe(lambda: admin.register_agent(
        agent_id="research-agent",
        display_name="Research Agent",
        owner_team="AI Platform",
        environment="dev",
        keycloak_client_id="research-agent-client",
        default_scopes=["tools:read", "documents:read"],
        allowed_tools=["document_search", "summarizer", "email"],
        status="active",
    ))
    _maybe(lambda: admin.register_tool(
        tool_id="document_search",
        display_name="Document Search",
        owner_team="AI Platform",
        risk_level="low",
        allowed_actions=["read"],
        approval_required_by_default=False,
    ))
    _maybe(lambda: admin.register_tool(
        tool_id="summarizer",
        display_name="Summarizer",
        owner_team="AI Platform",
        risk_level="low",
        allowed_actions=["run"],
    ))
    _maybe(lambda: admin.register_tool(
        tool_id="email",
        display_name="Email",
        owner_team="Workplace",
        risk_level="high",
        allowed_actions=["send_internal", "send_external"],
    ))

    print("Seeded agents and tools.")

    agent = AIGAgentClient(BASE, admin_token=TOKEN)
    run = agent.start_run(
        agent_id="research-agent",
        tenant_id="tenant_123",
        delegated_user_id="user_456",
        purpose="summarize_contract",
        requested_tools=["document_search", "email"],
    )
    print(f"Started run {run.agent_run_id} (expires in {run.expires_in}s)")

    for tool_id, action, expected in [
        ("document_search", "read", "allow"),
        ("email", "send_external", "require_approval"),
        ("summarizer", "run", "deny"),  # not in this run's requested_tools
    ]:
        r = agent.authorize(tool_id=tool_id, action=action, resource="example")
        marker = "OK" if r.decision == expected else "??"
        print(f"  [{marker}] {tool_id}:{action} -> {r.decision} ({r.reason_code})")

    print("\nLast 5 audit events:")
    for e in admin.search_audit_events(agent_run_id=run.agent_run_id, limit=5):
        print(f"  {e['timestamp']}  {e['event_type']:24s}  {e.get('decision') or ''}  {e.get('reason_code') or ''}")


if __name__ == "__main__":
    main()
