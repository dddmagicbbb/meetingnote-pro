"""Todo 5 - 팀 목록 · 직접 등록 · 변경 · 내 할 일 · 삭제 (specs/todo)."""
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..duedate import kst_date, parse_due
from ..deps import current_user, iso, membership_of, record, require_member
from ..errors import ApiError
from ..models import Meeting, Membership, Todo, User

router = APIRouter(tags=["Todo"])

STATUSES = ("OPEN", "DOING", "DONE")


class TodoIn(BaseModel):
    what: str
    assignee_id: int | None = None
    due_text: str = ""


class TodoUpdate(BaseModel):
    status: str | None = None
    assignee_id: int | None = None  # null 을 보내면 미정
    due_text: str | None = None
    what: str | None = None


def can_delete(db: Session, user: User, t: Todo) -> bool:
    if user.id in (t.author_id, t.assignee_id):
        return True
    mem = membership_of(db, user.id)
    return mem is not None and mem.team_id == t.team_id and mem.role == "owner"


def todo_dicts(db: Session, user: User, todos) -> list[dict]:
    todos = list(todos)
    user_ids = {t.assignee_id for t in todos if t.assignee_id}
    names = dict(db.execute(select(User.id, User.name).where(User.id.in_(user_ids))).all()) if user_ids else {}
    meeting_ids = {t.meeting_id for t in todos if t.meeting_id}
    titles = dict(db.execute(select(Meeting.id, Meeting.title).where(Meeting.id.in_(meeting_ids))).all()) if meeting_ids else {}
    return [{
        "id": t.id, "what": t.what, "assignee_id": t.assignee_id, "assignee_name": names.get(t.assignee_id),
        "due_text": t.due_text, "due_date": t.due_date.isoformat() if t.due_date else None, "status": t.status, "meeting_id": t.meeting_id,
        "meeting_title": titles.get(t.meeting_id), "author_id": t.author_id,
        "can_delete": can_delete(db, user, t), "created_at": iso(t.created_at),
    } for t in todos]


def sort_todos(todos) -> list[Todo]:
    """status(OPEN · DOING · DONE) 다음 due_date(빈 값은 뒤) 다음 due_text."""
    return sorted(todos, key=lambda t: (STATUSES.index(t.status) if t.status in STATUSES else 9,
                                        t.due_date is None, t.due_date or "", t.due_text or "", t.id))


def base_date(db: Session, t: Todo):
    """기한 기준일 - 회의록 할 일은 회의 날짜, 직접 등록은 등록한 날 (한국 날짜)."""
    if t.meeting_id:
        m = db.get(Meeting, t.meeting_id)
        if m is not None:
            return kst_date(m.met_at)
    return kst_date(t.created_at)


def check_assignee(db: Session, team_id: int, assignee_id: int | None) -> User | None:
    if assignee_id is None:
        return None
    ok = db.scalar(select(Membership).where(Membership.user_id == assignee_id, Membership.team_id == team_id))
    if ok is None:
        raise ApiError(400, "VALIDATION_ERROR", "담당자는 팀 멤버여야 함")
    return db.get(User, assignee_id)


def check_what(what: str) -> str:
    what = what.strip()
    if not what or len(what) > 500:
        raise ApiError(400, "VALIDATION_ERROR", "할 일 내용은 1~500자")
    return what


@router.get("/teams/{team_id}/todos", summary="팀 할 일 - meeting_title · can_delete 포함")
def list_todos(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    return todo_dicts(db, user, sort_todos(db.scalars(select(Todo).where(Todo.team_id == team_id)).all()))


@router.post("/teams/{team_id}/todos", status_code=201, summary="할 일 직접 등록 (출처: 직접 등록)")
def create_todo(team_id: int, data: TodoIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    what = check_what(data.what)
    assignee = check_assignee(db, team_id, data.assignee_id)
    due_text = data.due_text.strip()[:100]
    t = Todo(team_id=team_id, meeting_id=None, what=what, due_text=due_text,
             due_date=parse_due(due_text, kst_date(None)),  # 직접 등록은 등록한 날 기준
             status="OPEN", assignee_id=assignee.id if assignee else None, author_id=user.id)
    db.add(t)
    if assignee:
        record(db, team_id, user.id, "todo_assign", f"할 일 「{what[:100]}」 를 {assignee.name}에게 배정")
    db.commit()
    return todo_dicts(db, user, [t])[0]


@router.get("/me/todos", summary="내게 배정된 할 일")
def my_todos(user: User = Depends(current_user), db: Session = Depends(get_db)):
    mem = membership_of(db, user.id)
    if mem is None:
        return []
    rows = db.scalars(select(Todo).where(Todo.team_id == mem.team_id, Todo.assignee_id == user.id)).all()
    return todo_dicts(db, user, sort_todos(rows))


def get_todo(db: Session, user: User, todo_id: int) -> Todo:
    t = db.get(Todo, todo_id)
    if t is None:
        raise ApiError(404, "NOT_FOUND", "할 일을 찾을 수 없음")
    require_member(db, user, t.team_id)
    return t


@router.put("/todos/{todo_id}", summary="상태 · 담당자 · 기한 변경 (팀원 누구나)")
def update_todo(todo_id: int, data: TodoUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = get_todo(db, user, todo_id)
    sent = data.model_fields_set
    if data.status is not None and data.status not in STATUSES:
        raise ApiError(400, "VALIDATION_ERROR", "status 는 OPEN · DOING · DONE")
    if "what" in sent and data.what is not None:
        t.what = check_what(data.what)
    if "due_text" in sent and data.due_text is not None:
        t.due_text = data.due_text.strip()[:100]
        t.due_date = parse_due(t.due_text, base_date(db, t))
    if "assignee_id" in sent:
        assignee = check_assignee(db, t.team_id, data.assignee_id)
        new_id = assignee.id if assignee else None
        if new_id != t.assignee_id:
            t.assignee_id = new_id
            if assignee:
                record(db, t.team_id, user.id, "todo_assign", f"할 일 「{t.what[:100]}」 를 {assignee.name}에게 배정")
    if data.status is not None and data.status != t.status:
        if data.status == "DONE":
            record(db, t.team_id, user.id, "todo_done", f"할 일 「{t.what[:100]}」 완료")
        t.status = data.status
    db.commit()
    return todo_dicts(db, user, [t])[0]


@router.delete("/todos/{todo_id}", status_code=204, summary="할 일 삭제 (만든 사람 · 담당자 · owner)")
def delete_todo(todo_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = get_todo(db, user, todo_id)
    if not can_delete(db, user, t):
        raise ApiError(403, "FORBIDDEN")
    db.delete(t)
    db.commit()
    return Response(status_code=204)
