"""Activity 2 - 팀 활동기록 · 내 활동기록 (specs/activity). 최근순 50건."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, iso, membership_of, require_member
from ..models import Activity, User

router = APIRouter(tags=["Activity"])

LIMIT = 50


def activity_rows(db: Session, *conds) -> list[dict]:
    rows = db.execute(
        select(Activity, User.name).join(User, User.id == Activity.actor_id)
        .where(*conds).order_by(Activity.created_at.desc(), Activity.id.desc()).limit(LIMIT)
    ).all()
    return [{"id": a.id, "kind": a.kind, "actor_name": name, "text": f"{name} {a.target}",
             "created_at": iso(a.created_at)} for a, name in rows]


@router.get("/teams/{team_id}/activities", summary="팀 활동기록 - 최근 50건")
def team_activities(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    return activity_rows(db, Activity.team_id == team_id)


@router.get("/me/activities", summary="내 활동기록 - 최근 50건")
def my_activities(user: User = Depends(current_user), db: Session = Depends(get_db)):
    mem = membership_of(db, user.id)
    if mem is None:
        return []
    return activity_rows(db, Activity.actor_id == user.id, Activity.team_id == mem.team_id)
