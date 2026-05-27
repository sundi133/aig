import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import audit
from ..auth import issue_run_token, require_admin
from ..config import get_settings
from ..db import get_db
from ..models import Agent, AgentRun
from ..schemas import AgentRunCreate, AgentRunCreateResponse, AgentRunRead

router = APIRouter(prefix="/v1/agent-runs", tags=["agent_runs"])


@router.post("", response_model=AgentRunCreateResponse, status_code=status.HTTP_201_CREATED)
def create_agent_run(
    body: AgentRunCreate,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
) -> AgentRunCreateResponse:
    settings = get_settings()

    agent = db.get(Agent, body.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {body.agent_id!r} not registered")
    if agent.status != "active":
        raise HTTPException(status_code=403, detail=f"Agent {body.agent_id!r} is not active")

    agent_allowed = set(agent.allowed_tools or [])
    requested = list(dict.fromkeys(body.requested_tools))  # dedupe, preserve order

    if agent_allowed:
        disallowed = [t for t in requested if t not in agent_allowed]
        if disallowed:
            raise HTTPException(
                status_code=403,
                detail=f"Requested tools not permitted for this agent: {disallowed}",
            )
        allowed_for_run = requested or sorted(agent_allowed)
    else:
        allowed_for_run = requested

    ttl = min(body.ttl_seconds, settings.max_token_ttl_seconds)

    scopes = body.scopes or list(agent.default_scopes or [])

    run_id = f"run_{uuid.uuid4().hex[:24]}"
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl)

    run = AgentRun(
        agent_run_id=run_id,
        agent_id=body.agent_id,
        tenant_id=body.tenant_id,
        delegated_user_id=body.delegated_user_id,
        purpose=body.purpose,
        requested_tools=requested,
        allowed_tools=allowed_for_run,
        scopes=scopes,
        status="active",
        created_at=now,
        expires_at=expires_at,
    )
    db.add(run)

    token, iat, exp = issue_run_token(
        agent_id=body.agent_id,
        agent_run_id=run_id,
        tenant_id=body.tenant_id,
        delegated_user_id=body.delegated_user_id,
        purpose=body.purpose,
        allowed_tools=allowed_for_run,
        scopes=scopes,
        ttl_seconds=ttl,
    )

    audit.write_event(
        db,
        event_type="agent_run.created",
        tenant_id=body.tenant_id,
        agent_id=body.agent_id,
        agent_run_id=run_id,
        delegated_user_id=body.delegated_user_id,
        actor_id=actor,
        metadata={
            "purpose": body.purpose,
            "requested_tools": requested,
            "allowed_tools": allowed_for_run,
            "ttl_seconds": ttl,
        },
    )
    audit.write_event(
        db,
        event_type="token.issued",
        tenant_id=body.tenant_id,
        agent_id=body.agent_id,
        agent_run_id=run_id,
        delegated_user_id=body.delegated_user_id,
        actor_id=actor,
        metadata={"expires_at": expires_at.isoformat(), "scope": " ".join(scopes)},
    )
    db.commit()

    return AgentRunCreateResponse(agent_run_id=run_id, access_token=token, expires_in=ttl)


@router.get("", response_model=List[AgentRunRead])
def list_agent_runs(
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
    agent_id: Optional[str] = Query(default=None),
    tenant_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=500),
) -> List[AgentRunRead]:
    q = db.query(AgentRun)
    if agent_id:
        q = q.filter(AgentRun.agent_id == agent_id)
    if tenant_id:
        q = q.filter(AgentRun.tenant_id == tenant_id)
    rows = q.order_by(AgentRun.created_at.desc()).limit(limit).all()
    return [AgentRunRead.model_validate(r) for r in rows]


@router.get("/{agent_run_id}", response_model=AgentRunRead)
def get_agent_run(
    agent_run_id: str,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
) -> AgentRunRead:
    run = db.get(AgentRun, agent_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return AgentRunRead.model_validate(run)
