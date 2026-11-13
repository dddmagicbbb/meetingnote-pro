"""Meeting 6 - 업로드 · 저장 · 목록 · 단건 · 수정 · 삭제 (specs/meeting)."""
from datetime import timedelta

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from .. import gemini
from ..duedate import kst_date, parse_due
from ..db import get_db
from ..deps import current_user, iso, membership_of, parse_iso, record, require_member
from ..errors import ApiError
from ..models import Comment, Meeting, Membership, Todo, User
from .todos import todo_dicts

router = APIRouter(tags=["Meeting"])


class MeetingIn(BaseModel):
    title: str
    met_at: str
    attendees: str = ""
    body: str


class MeetingUpdate(BaseModel):
    title: str | None = None
    met_at: str | None = None
    attendees: str | None = None
    body: str | None = None


# ── 업로드 형식 판정 - 확장자가 아니라 내용의 앞 바이트로 ──────────
def sniff_audio(head: bytes) -> str | None:
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio/wav"
    if head[:3] == b"ID3":
        return "audio/mp3"
    if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
        return "audio/mp3"
    return None


# ── 담당자 대조 - 공백과 존칭(님)을 무시 ──────────────────────
def norm_name(name: str) -> str:
    n = "".join(name.split())
    while n.endswith("님"):
        n = n[:-1]
    return n


def match_member(name: str, members: dict[str, int]) -> int | None:
    key = norm_name(name)
    return members.get(key) if key else None


def decision_lines(decisions: str) -> list[str]:
    return [d for d in (decisions or "").splitlines() if d.strip()]


def check_text(value: str, field: str, limit: int) -> str:
    value = value.strip()
    if not value:
        raise ApiError(400, "VALIDATION_ERROR", f"{field} 는 필수")
    if len(value) > limit:
        raise ApiError(400, "VALIDATION_ERROR", f"{field} 는 {limit}자 이내")
    return value


def meeting_summary(db: Session, m: Meeting) -> dict:
    total, done = db.execute(
        select(func.count(), func.count().filter(Todo.status == "DONE")).where(Todo.meeting_id == m.id)
    ).one()
    return {
        "id": m.id, "title": m.title, "met_at": iso(m.met_at), "attendees": m.attendees,
        "summary": m.summary, "created_at": iso(m.created_at),
        "todo_done_count": done, "todo_total_count": total,
        "decision_count": len(decision_lines(m.decisions)),
    }


def can_edit(db: Session, user: User, m: Meeting) -> bool:
    mem = membership_of(db, user.id)
    return m.author_id == user.id or (mem is not None and mem.team_id == m.team_id and mem.role == "owner")


def meeting_detail(db: Session, user: User, m: Meeting) -> dict:
    d = meeting_summary(db, m)
    d.update({
        "team_id": m.team_id, "author_id": m.author_id, "body": m.body,
        "decisions": decision_lines(m.decisions),
        "todos": todo_dicts(db, user, db.scalars(select(Todo).where(Todo.meeting_id == m.id).order_by(Todo.id)).all()),
        "can_edit": can_edit(db, user, m),
    })
    return d


def get_meeting(db: Session, user: User, meeting_id: int) -> Meeting:
    """없거나 다른 팀 회의록이면 404 MEETING_NOT_FOUND."""
    m = db.get(Meeting, meeting_id)
    mem = membership_of(db, user.id)
    if m is None or mem is None or mem.team_id != m.team_id:
        raise ApiError(404, "MEETING_NOT_FOUND")
    return m


@router.post("/upload", summary="녹취 업로드 → 받아쓰기 200 {body} (저장 안 함)")
async def upload(file: UploadFile = File(...), _: User = Depends(current_user)):
    data = await file.read()
    mime = sniff_audio(data[:16])
    if mime is None:
        raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE")
    return {"body": gemini.transcribe(data, mime)}


@router.post("/teams/{team_id}/meetings", status_code=201, summary="회의록 저장 + 요약 · 결정사항 · 할 일 구분")
def create_meeting(team_id: int, data: MeetingIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    title = check_text(data.title, "제목", 200)
    body = check_text(data.body, "본문", 200_000)
    met_at = parse_iso(data.met_at)

    members = dict(db.execute(
        select(User.name, User.id).join(Membership, Membership.user_id == User.id).where(Membership.team_id == team_id)
    ).all())
    result = gemini.classify(body, list(members))  # 실패면 502, 저장하지 않음
    lookup = {norm_name(n): i for n, i in members.items()}
    names = {i: n for n, i in members.items()}

    m = Meeting(team_id=team_id, title=title, met_at=met_at, attendees=data.attendees.strip()[:500],
                body=body, summary=result["summary"], decisions="\n".join(result["decisions"]), author_id=user.id)
    db.add(m)
    db.flush()
    record(db, team_id, user.id, "meeting_add", f"회의록 「{title}」 등록")
    base = kst_date(met_at)  # 기한은 회의 날짜 기준 (modify-todo-due-date)
    for t in result["todos"]:
        assignee = match_member(t["assignee"], lookup)
        due_text = t["due"][:100]
        db.add(Todo(team_id=team_id, meeting_id=m.id, what=t["what"][:500], due_text=due_text,
                    due_date=parse_due(due_text, base), status="OPEN", assignee_id=assignee, author_id=user.id))
        if assignee:
            record(db, team_id, user.id, "todo_assign", f"할 일 「{t['what'][:100]}」 를 {names[assignee]}에게 배정")
    db.commit()
    return meeting_detail(db, user, m)


@router.get("/teams/{team_id}/meetings", summary="회의록 목록 - ?q= 제목 · 참석자, ?from=&to= 기간")
def list_meetings(team_id: int, q: str | None = None,
                  from_: str | None = Query(None, alias="from", description="ISO 날짜 (예: 2026-09-01)"),
                  to: str | None = Query(None, description="ISO 날짜 (그날 포함)"),
                  user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    stmt = select(Meeting).where(Meeting.team_id == team_id)
    if q and q.strip():
        # % · _ 는 글자 그대로 찾는다
        word = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{word}%"
        stmt = stmt.where(or_(Meeting.title.like(like, escape="\\"), Meeting.attendees.like(like, escape="\\")))
    if from_:
        stmt = stmt.where(Meeting.met_at >= parse_iso(from_[:10]))
    if to:
        stmt = stmt.where(Meeting.met_at < parse_iso(to[:10]) + timedelta(days=1))
    rows = db.scalars(stmt.order_by(Meeting.met_at.desc(), Meeting.id.desc())).all()
    return [meeting_summary(db, m) for m in rows]


@router.get("/meetings/{meeting_id}", summary="회의록 단건 - body · todos · can_edit 포함")
def read_meeting(meeting_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return meeting_detail(db, user, get_meeting(db, user, meeting_id))


@router.put("/meetings/{meeting_id}", summary="회의록 수정 (작성자 · owner) - 다시 구분하지 않음")
def update_meeting(meeting_id: int, data: MeetingUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = get_meeting(db, user, meeting_id)
    if not can_edit(db, user, m):
        raise ApiError(403, "FORBIDDEN")
    if data.title is not None:
        m.title = check_text(data.title, "제목", 200)
    if data.met_at is not None:
        m.met_at = parse_iso(data.met_at)
    if data.attendees is not None:
        m.attendees = data.attendees.strip()[:500]
    if data.body is not None:
        m.body = check_text(data.body, "본문", 200_000)
    db.commit()
    return meeting_detail(db, user, m)


@router.delete("/meetings/{meeting_id}", status_code=204, summary="회의록 삭제 - 딸린 할 일 · 댓글 함께")
def delete_meeting(meeting_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = get_meeting(db, user, meeting_id)
    if not can_edit(db, user, m):
        raise ApiError(403, "FORBIDDEN")
    db.execute(delete(Todo).where(Todo.meeting_id == m.id))
    db.execute(delete(Comment).where(Comment.meeting_id == m.id))
    db.delete(m)
    db.commit()
    return Response(status_code=204)
