from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import audit
from ..auth import require_admin
from ..db import get_db
from ..models import Tool
from ..schemas import ToolCreate, ToolRead, ToolUpdate

router = APIRouter(prefix="/v1/tools", tags=["tools"])


@router.post("", response_model=ToolRead, status_code=status.HTTP_201_CREATED)
def register_tool(
    body: ToolCreate,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
) -> ToolRead:
    if db.get(Tool, body.tool_id):
        raise HTTPException(status_code=409, detail=f"Tool {body.tool_id!r} already exists")
    tool = Tool(
        tool_id=body.tool_id,
        display_name=body.display_name,
        owner_team=body.owner_team,
        risk_level=body.risk_level,
        allowed_actions=body.allowed_actions,
        approval_required_by_default=body.approval_required_by_default,
        status=body.status,
    )
    db.add(tool)
    audit.write_event(
        db,
        event_type="tool.registered",
        tool_id=tool.tool_id,
        actor_id=actor,
        metadata={"risk_level": tool.risk_level, "owner_team": tool.owner_team},
    )
    db.commit()
    db.refresh(tool)
    return ToolRead.model_validate(tool)


@router.get("", response_model=List[ToolRead])
def list_tools(
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
    status_filter: Optional[str] = Query(default=None, alias="status"),
) -> List[ToolRead]:
    q = db.query(Tool)
    if status_filter:
        q = q.filter(Tool.status == status_filter)
    return [ToolRead.model_validate(t) for t in q.order_by(Tool.created_at.desc()).all()]


@router.get("/{tool_id}", response_model=ToolRead)
def get_tool(tool_id: str, db: Session = Depends(get_db), actor: str = Depends(require_admin)) -> ToolRead:
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return ToolRead.model_validate(tool)


@router.patch("/{tool_id}", response_model=ToolRead)
def update_tool(
    tool_id: str,
    body: ToolUpdate,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
) -> ToolRead:
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(tool, k, v)
    tool.updated_at = datetime.now(timezone.utc)
    audit.write_event(
        db,
        event_type="tool.updated",
        tool_id=tool.tool_id,
        actor_id=actor,
        metadata={"changes": changes},
    )
    db.commit()
    db.refresh(tool)
    return ToolRead.model_validate(tool)


@router.post("/{tool_id}/disable", response_model=ToolRead)
def disable_tool(
    tool_id: str,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
) -> ToolRead:
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    tool.status = "disabled"
    tool.updated_at = datetime.now(timezone.utc)
    audit.write_event(db, event_type="tool.disabled", tool_id=tool.tool_id, actor_id=actor)
    db.commit()
    db.refresh(tool)
    return ToolRead.model_validate(tool)
