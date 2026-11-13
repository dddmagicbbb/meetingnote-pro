"""Comment 3 - 등록 · 목록 · 삭제 (specs/comment)."""
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, iso, membership_of, record
from ..errors import ApiError
from ..models import Comment, Meeting, User
from .meetings import get_meeting

router = APIRouter(tags=["Comment"])

MAX_COMMENT = 500


class CommentIn(BaseModel):
    content: str


def can_delete(db: Session, user: User, c: Comment, team_id: int) -> bool:
    if c.user_id == user.id:
        return True
    mem = membership_of(db, user.id)
    return mem is not None and mem.team_id == team_id and mem.role == "owner"


def comment_dict(db: Session, user: User, c: Comment, author: User, team_id: int) -> dict:
    return {"id": c.id, "user_id": c.user_id, "user_name": author.name, "content": c.content,
            "created_at": iso(c.created_at), "can_delete": can_delete(db, user, c, team_id)}


@router.post("/meetings/{meeting_id}/comments", status_code=201, summary="댓글 등록 (500자 이내)")
def create_comment(meeting_id: int, data: CommentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = get_meeting(db, user, meeting_id)
    content = data.content.strip()
    if not content or len(content) > MAX_COMMENT:
        raise ApiError(400, "VALIDATION_ERROR", f"댓글은 1~{MAX_COMMENT}자")
    c = Comment(meeting_id=m.id, user_id=user.id, content=content)
    db.add(c)
    record(db, m.team_id, user.id, "comment_add", f"회의록 「{m.title}」 에 댓글")
    db.commit()
    return comment_dict(db, user, c, user, m.team_id)


@router.get("/meetings/{meeting_id}/comments", summary="댓글 목록 - 오래된 순")
def list_comments(meeting_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = get_meeting(db, user, meeting_id)
    rows = db.execute(
        select(Comment, User).join(User, User.id == Comment.user_id)
        .where(Comment.meeting_id == m.id).order_by(Comment.created_at, Comment.id)
    ).all()
    return [comment_dict(db, user, c, u, m.team_id) for c, u in rows]


@router.delete("/comments/{comment_id}", status_code=204, summary="댓글 삭제 (쓴 사람 · owner)")
def delete_comment(comment_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = db.get(Comment, comment_id)
    m = db.get(Meeting, c.meeting_id) if c else None
    mem = membership_of(db, user.id)
    if c is None or m is None or mem is None or mem.team_id != m.team_id:
        raise ApiError(404, "NOT_FOUND", "댓글을 찾을 수 없음")
    if not can_delete(db, user, c, m.team_id):
        raise ApiError(403, "FORBIDDEN")
    db.delete(c)
    db.commit()
    return Response(status_code=204)
