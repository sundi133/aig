"""Simple policy engine.

The MVP supports allow / deny / require_approval decisions driven by:

  * Agent registration (allowed_tools, status)
  * Tool registration (status, risk_level, allowed_actions, approval_required_by_default)
  * Run-scoped allowed_tools (token claim)
  * Tenant boundary (run tenant_id must match request tenant_id)
  * A small set of built-in high-risk action patterns (§7.4 / §12.6)

Production deployments would swap this for OPA, Cedar, or Keycloak Authorization
Services -- the engine returns a structured ``PolicyDecision`` so callers do
not need to change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from .models import Agent, AgentRun, Tool


# High-risk action patterns that always require approval unless explicitly
# overridden by tool config. Matches the examples in §12.6.
HIGH_RISK_ACTIONS = {
    "email:send_external",
    "records:delete",
    "permissions:update",
    "purchase:create",
    "code:execute_prod",
    "data:export_sensitive",
}


@dataclass
class PolicyInput:
    agent_id: str
    agent_run_id: str
    tenant_id: str
    delegated_user_id: Optional[str]
    tool_id: str
    action: str
    resource: Optional[str] = None
    risk_level: Optional[str] = None
    user_roles: List[str] = field(default_factory=list)
    agent_scopes: List[str] = field(default_factory=list)
    environment: Optional[str] = None


@dataclass
class PolicyDecision:
    decision: str  # "allow" | "deny" | "require_approval"
    reason_code: str
    reason: str


def _action_key(tool_id: str, action: str) -> str:
    return f"{tool_id}:{action}"


def _allowed(actions: Optional[Iterable[str]], action: str) -> bool:
    if not actions:
        return True  # Tool didn't constrain actions -> defer to agent/run scope.
    return action in set(actions) or "*" in set(actions)


def evaluate(
    *,
    inp: PolicyInput,
    agent: Optional[Agent],
    tool: Optional[Tool],
    run: Optional[AgentRun],
    run_allowed_tools: Optional[Iterable[str]] = None,
) -> PolicyDecision:
    """Apply MVP policy rules in order. First matching rule wins."""

    if agent is None:
        return PolicyDecision("deny", "agent_unknown", f"Agent {inp.agent_id!r} is not registered")
    if agent.status != "active":
        return PolicyDecision("deny", "agent_disabled", f"Agent {inp.agent_id!r} is not active")

    if tool is None:
        return PolicyDecision("deny", "tool_unknown", f"Tool {inp.tool_id!r} is not registered")
    if tool.status != "active":
        return PolicyDecision("deny", "tool_disabled", f"Tool {inp.tool_id!r} is not active")

    if run is None:
        return PolicyDecision("deny", "run_unknown", f"Agent run {inp.agent_run_id!r} not found")
    if run.status != "active":
        return PolicyDecision("deny", "run_inactive", f"Agent run {inp.agent_run_id!r} is not active")
    if run.tenant_id != inp.tenant_id:
        return PolicyDecision(
            "deny",
            "tenant_mismatch",
            f"Run tenant {run.tenant_id!r} does not match requested tenant {inp.tenant_id!r}",
        )

    # Run must have been scoped to this tool.
    allowed_for_run = list(run_allowed_tools or run.allowed_tools or [])
    if allowed_for_run and inp.tool_id not in allowed_for_run:
        return PolicyDecision(
            "deny",
            "tool_not_in_run_scope",
            f"Tool {inp.tool_id!r} not in run-scoped allowed_tools",
        )

    # Agent class must permit this tool too.
    agent_tools = list(agent.allowed_tools or [])
    if agent_tools and inp.tool_id not in agent_tools:
        return PolicyDecision(
            "deny",
            "tool_not_in_agent_scope",
            f"Tool {inp.tool_id!r} not in agent {agent.agent_id!r}'s allowed_tools",
        )

    # Action constraint from tool registry.
    if not _allowed(tool.allowed_actions, inp.action):
        return PolicyDecision(
            "deny",
            "action_not_allowed",
            f"Action {inp.action!r} not in tool {tool.tool_id!r}'s allowed_actions",
        )

    # Approval handling.
    if _action_key(tool.tool_id, inp.action) in HIGH_RISK_ACTIONS:
        return PolicyDecision(
            "require_approval",
            "high_risk_action",
            f"{tool.tool_id}:{inp.action} requires human approval",
        )
    if tool.approval_required_by_default:
        return PolicyDecision(
            "require_approval",
            "tool_default_approval",
            f"Tool {tool.tool_id!r} requires approval by default",
        )
    if (inp.risk_level or "").lower() in {"high", "critical"}:
        return PolicyDecision(
            "require_approval",
            "high_risk_level",
            f"Risk level {inp.risk_level!r} requires approval",
        )

    return PolicyDecision(
        "allow",
        "ok",
        f"Agent run is authorized for {tool.tool_id}:{inp.action} within {inp.tenant_id}",
    )
