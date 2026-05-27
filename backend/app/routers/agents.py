from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import audit
from ..auth import require_admin
from ..db import get_db
from ..models import Agent
from ..schemas import AgentCreate, AgentRead, AgentUpdate

router = APIRouter(prefix="/v1/agents", tags=["agents"])


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def register_agent(
    body: AgentCreate,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
) -> AgentRead:
    existing = db.get(Agent, body.agent_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Agent {body.agent_id!r} already exists")
    agent = Agent(
        agent_id=body.agent_id,
        display_name=body.display_name,
        owner_team=body.owner_team,
        environment=body.environment,
        keycloak_client_id=body.keycloak_client_id,
        status=body.status,
        default_scopes=body.default_scopes,
        allowed_tools=body.allowed_tools,
    )
    db.add(agent)
    audit.write_event(
        db,
        event_type="agent.registered",
        agent_id=agent.agent_id,
        actor_id=actor,
        metadata={"display_name": agent.display_name, "owner_team": agent.owner_team},
    )
    db.commit()
    db.refresh(agent)
    return AgentRead.model_validate(agent)


@router.get("", response_model=List[AgentRead])
def list_agents(
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
    status_filter: Optional[str] = Query(default=None, alias="status"),
) -> List[AgentRead]:
    q = db.query(Agent)
    if status_filter:
        q = q.filter(Agent.status == status_filter)
    return [AgentRead.model_validate(a) for a in q.order_by(Agent.created_at.desc()).all()]


@router.get("/{agent_id}", response_model=AgentRead)
def get_agent(agent_id: str, db: Session = Depends(get_db), actor: str = Depends(require_admin)) -> AgentRead:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentRead.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentRead)
def update_agent(
    agent_id: str,
    body: AgentUpdate,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
) -> AgentRead:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(agent, k, v)
    agent.updated_at = datetime.now(timezone.utc)
    audit.write_event(
        db,
        event_type="agent.updated",
        agent_id=agent.agent_id,
        actor_id=actor,
        metadata={"changes": changes},
    )
    db.commit()
    db.refresh(agent)
    return AgentRead.model_validate(agent)


@router.post("/{agent_id}/disable", response_model=AgentRead)
def disable_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
) -> AgentRead:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.status = "disabled"
    agent.updated_at = datetime.now(timezone.utc)
    audit.write_event(db, event_type="agent.disabled", agent_id=agent.agent_id, actor_id=actor)
    db.commit()
    db.refresh(agent)
    return AgentRead.model_validate(agent)
