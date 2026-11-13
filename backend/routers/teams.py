"""Team 6 - 팀 생성 · 목록 · 합류 · 멤버 · 초대코드 재발급 · 이름 변경 (specs/team)."""
import secrets
import string

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, iso, membership_of, record, require_member, require_owner
from ..errors import ApiError
from ..models import Membership, Team, Todo, User

router = APIRouter(tags=["Team"])

TEAM_LIMIT = 6
CODE_CHARS = string.ascii_uppercase + string.digits


class TeamIn(BaseModel):
    name: str


class JoinIn(BaseModel):
    invite_code: str


def new_code(db: Session) -> str:
    while True:
        code = "MN-" + "".join(secrets.choice(CODE_CHARS) for _ in range(4))
        if not db.scalar(select(Team).where(Team.invite_code == code)):
            return code


def check_team_name(name: str) -> str:
    name = name.strip()
    if not name or len(name) > 50:
        raise ApiError(400, "VALIDATION_ERROR", "팀 이름은 1~50자")
    return name


def member_count(db: Session, team_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Membership).where(Membership.team_id == team_id))


def team_dict(db: Session, team: Team, role: str) -> dict:
    return {
        "id": team.id, "name": team.name, "invite_code": team.invite_code,
        "owner_id": team.owner_id, "role": role,
        "member_count": member_count(db, team.id), "created_at": iso(team.created_at),
    }


def ensure_no_team(db: Session, user: User) -> None:
    if membership_of(db, user.id):
        raise ApiError(400, "VALIDATION_ERROR", "이미 다른 팀 소속")


@router.post("/teams", status_code=201, summary="팀 생성 - 만든 사람이 owner")
def create_team(data: TeamIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_no_team(db, user)
    team = Team(name=check_team_name(data.name), invite_code=new_code(db), owner_id=user.id)
    db.add(team)
    db.flush()
    db.add(Membership(team_id=team.id, user_id=user.id, role="owner"))
    db.commit()  # 팀 생성은 활동 kind 5종에 없음
    return team_dict(db, team, "owner")


@router.get("/teams", summary="내 소속 팀 (없으면 빈 배열)")
def list_teams(user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = membership_of(db, user.id)
    if m is None:
        return []
    return [team_dict(db, db.get(Team, m.team_id), m.role)]


@router.post("/teams/join", summary="초대코드로 합류")
def join_team(data: JoinIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_no_team(db, user)
    team = db.scalar(select(Team).where(Team.invite_code == data.invite_code.strip().upper()))
    if team is None:
        raise ApiError(404, "INVITE_NOT_FOUND")
    if member_count(db, team.id) >= TEAM_LIMIT:
        raise ApiError(409, "TEAM_FULL", f"{team.name} 은 이미 {TEAM_LIMIT}명. owner 에게 문의")
    db.add(Membership(team_id=team.id, user_id=user.id, role="member"))
    record(db, team.id, user.id, "member_join", "초대코드로 합류")
    db.commit()
    return team_dict(db, team, "member")


@router.get("/teams/{team_id}/members", summary="멤버 목록 - todo_count 포함")
def list_members(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    todo_counts = dict(db.execute(
        select(Todo.assignee_id, func.count()).where(Todo.team_id == team_id, Todo.assignee_id.is_not(None))
        .group_by(Todo.assignee_id)
    ).all())
    rows = db.execute(
        select(User, Membership.role).join(Membership, Membership.user_id == User.id)
        .where(Membership.team_id == team_id).order_by(Membership.joined_at, Membership.id)
    ).all()
    return [
        {"id": u.id, "name": u.name, "email": u.email, "role": role, "todo_count": todo_counts.get(u.id, 0)}
        for u, role in rows
    ]


@router.put("/teams/{team_id}/code", summary="초대코드 재발급 (owner)")
def reissue_code(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    team = require_owner(db, user, team_id)
    team.invite_code = new_code(db)
    db.commit()
    return team_dict(db, team, "owner")


@router.put("/teams/{team_id}", summary="팀 이름 변경 (owner)")
def rename_team(team_id: int, data: TeamIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    team = require_owner(db, user, team_id)
    team.name = check_team_name(data.name)
    db.commit()
    return team_dict(db, team, "owner")
