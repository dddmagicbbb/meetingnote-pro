"""MeetingNote Pro - FastAPI 앱.

로컬 실행:  uvicorn backend.main:app --reload
  화면         http://127.0.0.1:8000/login.html
  Swagger UI   http://127.0.0.1:8000/docs
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import config, errors
from .db import create_all
from .routers import activities, auth, comments, meetings, teams, todos

logging.basicConfig(level=logging.INFO)

TAGS = [
    {"name": "Auth", "description": "회원가입 · 로그인 · 내 정보 · 로그아웃 (5)"},
    {"name": "Team", "description": "팀 생성 · 목록 · 합류 · 멤버 · 초대코드 · 이름 (6)"},
    {"name": "Meeting", "description": "녹취 업로드 · 회의록 저장 · 목록 · 단건 · 수정 · 삭제 (6)"},
    {"name": "Todo", "description": "할 일 칸반 (5)"},
    {"name": "Comment", "description": "회의록 댓글 (3)"},
    {"name": "Activity", "description": "활동기록 (2)"},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_all()
    yield


app = FastAPI(
    title="MeetingNote Pro API",
    version="1.0.0",
    description="회의록 · 할 일 · 댓글 · 활동기록. 보호된 API 는 오른쪽 위 **Authorize** 에 "
                "signup · login 응답의 `token` 을 넣고 호출한다. 오류 본문은 언제나 `{code, msg}`.",
    openapi_tags=TAGS,
    lifespan=lifespan,
)
errors.install(app)

for r in (auth, teams, meetings, todos, comments, activities):
    app.include_router(r.router, prefix="/api")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/login.html")


# 정적 화면은 마지막에 마운트 - /docs · /api 를 가리지 않게
app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=False), name="frontend")
