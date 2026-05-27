"""Agentic AI Identity Gateway -- Python SDK.

Two surfaces:

    AIGAdminClient   -- admin/control plane operations (register agents/tools,
                        create runs, search audit logs, resolve approvals).

    AIGAgentClient   -- runtime client for agents to request scoped tokens
                        and authorize tool calls. Uses an admin token to
                        create runs in MVP; in production the agent runtime
                        would present its own Keycloak-issued service-account
                        token to mint runs.
"""

from .client import AIGAdminClient, AIGAgentClient, AIGError, AuthorizeResult, RunToken

__all__ = ["AIGAdminClient", "AIGAgentClient", "AIGError", "AuthorizeResult", "RunToken"]
__version__ = "0.1.0"
