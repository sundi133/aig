"""Authorization decision API.

The Tool Gateway calls this endpoint before invoking any tool. Per §17.3 the
request body identifies the agent, run, tenant, tool, action, and optional
risk. If an ``access_token`` is supplied we trust its signed claims as the
ground truth for agent/run/tenant identity -- this is the preferred path.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import audit
from ..auth import require_admin, verify_run_token
from ..db import get_db
from ..models import Agent, AgentRun, Approval, Tool
from ..policy import PolicyInput, evaluate
from ..schemas import AuthorizeRequest, AuthorizeResponse

router = APIRouter(prefix="/v1", tags=["authorize"])


def _merge_claims(body: AuthorizeRequest, claims: Dict[str, Any]) -> AuthorizeRequest:
    """Token claims always win over request body fields for identity inputs."""
    return AuthorizeRequest(
        agent_id=claims.get("agent_id") or body.agent_id,
        agent_run_id=claims.get("agent_run_id") or body.agent_run_id,
        tenant_id=claims.get("tenant_id") or body.tenant_id,
        delegated_user_id=claims.get("delegated_user_id") or body.delegated_user_id,
        tool_id=body.tool_id,
        action=body.action,
        resource=body.resource,
        risk_level=body.risk_level,
        correlation_id=body.correlation_id,
        access_token=body.access_token,
    )


@router.post("/authorize", response_model=AuthorizeResponse)
def authorize(
    body: AuthorizeRequest,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
) -> AuthorizeResponse:
    claims: Dict[str, Any] = {}
    if body.access_token:
        claims = verify_run_token(body.access_token)
        body = _merge_claims(body, claims)

    if not body.agent_id or not body.agent_run_id or not body.tenant_id:
        raise HTTPException(
            status_code=400,
            detail="agent_id, agent_run_id, and tenant_id are required (provide an access_token to derive them automatically)",
        )

    correlation_id = body.correlation_id or f"cor_{uuid.uuid4().hex[:16]}"
    decision_id = f"dec_{uuid.uuid4().hex[:16]}"

    agent = db.get(Agent, body.agent_id)
    tool = db.get(Tool, body.tool_id)
    run = db.get(AgentRun, body.agent_run_id)

    # If we have a verified token, the allowed_tools claim is authoritative;
    # the DB-stored allowed_tools is a fallback for callers without tokens.
    run_allowed_tools = claims.get("allowed_tools") if claims else None

    # Even with valid signature, a run can be revoked or expired in the DB.
    if run is not None and run.expires_at:
        # SQLite returns naive datetimes; normalize before comparing.
        exp = run.expires_at if run.expires_at.tzinfo else run.expires_at.replace(tzinfo=timezone.utc)
        if exp <= datetime.now(timezone.utc):
            run.status = "expired"

    decision = evaluate(
        inp=PolicyInput(
            agent_id=body.agent_id,
            agent_run_id=body.agent_run_id,
            tenant_id=body.tenant_id,
            delegated_user_id=body.delegated_user_id,
            tool_id=body.tool_id,
            action=body.action,
            resource=body.resource,
            risk_level=body.risk_level,
        ),
        agent=agent,
        tool=tool,
        run=run,
        run_allowed_tools=run_allowed_tools,
    )

    approval_id = None
    if decision.decision == "require_approval":
        approval = Approval(
            approval_id=f"app_{uuid.uuid4().hex[:24]}",
            agent_id=body.agent_id,
            agent_run_id=body.agent_run_id,
            tenant_id=body.tenant_id,
            delegated_user_id=body.delegated_user_id,
            tool_id=body.tool_id,
            action=body.action,
            resource=body.resource,
            reason=decision.reason,
            status="pending",
        )
        db.add(approval)
        approval_id = approval.approval_id

    audit.write_event(
        db,
        event_type="authorization.decision",
        tenant_id=body.tenant_id,
        agent_id=body.agent_id,
        agent_run_id=body.agent_run_id,
        delegated_user_id=body.delegated_user_id,
        actor_id=actor,
        tool_id=body.tool_id,
        action=body.action,
        resource=body.resource,
        decision=decision.decision,
        reason_code=decision.reason_code,
        correlation_id=correlation_id,
        metadata={
            "decision_id": decision_id,
            "risk_level": body.risk_level,
            "approval_id": approval_id,
            "had_token": bool(body.access_token),
        },
    )
    db.commit()

    return AuthorizeResponse(
        decision=decision.decision,  # type: ignore[arg-type]
        reason=decision.reason,
        reason_code=decision.reason_code,
        decision_id=decision_id,
        approval_id=approval_id,
        correlation_id=correlation_id,
    )
