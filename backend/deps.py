"""공통 의존성 - 현재 사용자, 소속 팀 확인, 시각 형식, 활동 기록."""
from datetime import datetime, timezone

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import security
from .db import get_db
from .errors import ApiError
from .models import Activity, Membership, Team, User

bearer = HTTPBearer(auto_error=False, description="로그인 · 가입 응답의 token 을 넣는다")

ACTIVITY_KINDS = ("meeting_add", "todo_assign", "todo_done", "comment_add", "member_join")


def iso(dt: datetime | None) -> str | None:
    """UTC ISO 8601 (끝에 Z)."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc, microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(value: str) -> datetime:
    """ISO 문자열 → UTC naive. 시간대가 없으면 UTC 로 본다."""
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise ApiError(400, "VALIDATION_ERROR", "시각은 ISO 8601 형식")
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if cred is None or not cred.credentials:
        raise ApiError(401, "TOKEN_EXPIRED")
    user_id = security.decode_token(cred.credentials)
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise ApiError(401, "TOKEN_EXPIRED")
    return user


def membership_of(db: Session, user_id: int) -> Membership | None:
    return db.scalar(select(Membership).where(Membership.user_id == user_id))


def role_of(db: Session, user_id: int) -> str | None:
    m = membership_of(db, user_id)
    return m.role if m else None


def require_member(db: Session, user: User, team_id: int) -> Membership:
    """그 팀 소속이 아니면 403 FORBIDDEN."""
    m = membership_of(db, user.id)
    if m is None or m.team_id != team_id:
        raise ApiError(403, "FORBIDDEN")
    return m


def require_owner(db: Session, user: User, team_id: int) -> Team:
    m = require_member(db, user, team_id)
    if m.role != "owner":
        raise ApiError(403, "OWNER_ONLY")
    return db.get(Team, team_id)


def user_dict(db: Session, user: User) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email, "role": role_of(db, user.id)}


def record(db: Session, team_id: int, actor_id: int, kind: str, target: str) -> None:
    """활동 기록. kind 는 5종 밖의 값을 만들지 않는다."""
    assert kind in ACTIVITY_KINDS, kind
    db.add(Activity(team_id=team_id, actor_id=actor_id, kind=kind, target=target))
