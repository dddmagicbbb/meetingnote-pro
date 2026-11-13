"""Auth 5 - 회원가입 · 로그인 · 내 정보 조회와 수정 · 로그아웃 (specs/auth)."""
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import security
from ..db import get_db
from ..deps import current_user, user_dict
from ..errors import ApiError
from ..models import User

router = APIRouter(prefix="/auth", tags=["Auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8


class SignupIn(BaseModel):
    email: str
    password: str
    name: str


class LoginIn(BaseModel):
    email: str
    password: str


class MeIn(BaseModel):
    name: str | None = None
    password: str | None = None


def check_email(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise ApiError(400, "EMAIL_INVALID")
    return email


def check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise ApiError(400, "PASSWORD_TOO_WEAK")


def check_name(name: str) -> str:
    name = name.strip()
    if not name or len(name) > 50:
        raise ApiError(400, "VALIDATION_ERROR", "이름은 1~50자")
    return name


@router.post("/signup", status_code=201, summary="회원가입 - 201 {token, user}")
def signup(data: SignupIn, db: Session = Depends(get_db)):
    email = check_email(data.email)
    check_password(data.password)
    name = check_name(data.name)
    if db.scalar(select(User).where(User.email == email)):
        raise ApiError(409, "EMAIL_DUPLICATED")
    user = User(email=email, password_hash=security.hash_password(data.password), name=name)
    db.add(user)
    db.commit()
    return {"token": security.create_token(user.id), "user": user_dict(db, user)}


@router.post("/login", summary="로그인 - 200 {token, user}")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
    # 이메일이 없어도 비밀번호가 틀려도 같은 응답
    if user is None or not security.verify_password(data.password, user.password_hash):
        raise ApiError(401, "INVALID_CREDENTIALS")
    return {"token": security.create_token(user.id), "user": user_dict(db, user)}


@router.get("/me", summary="내 정보 - id · name · email · role")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_dict(db, user)


@router.put("/me", summary="이름 · 비밀번호 변경 (현재 비밀번호 없음)")
def update_me(data: MeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if data.name is None and data.password is None:
        raise ApiError(400, "VALIDATION_ERROR", "name 또는 password 가 필요")
    if data.password is not None:
        check_password(data.password)
    if data.name is not None:
        user.name = check_name(data.name)
    if data.password is not None:
        user.password_hash = security.hash_password(data.password)
    db.commit()  # 계정 변경은 활동기록에 남기지 않음
    return user_dict(db, user)


@router.post("/logout", summary="로그아웃 - 서버 블랙리스트 없이 200")
def logout(_: User = Depends(current_user)):
    return {"ok": True}
