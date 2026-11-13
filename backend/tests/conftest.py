"""테스트 공통 - 임시 SQLite, TestClient, 가입 · 팀 도우미, Gemini 가짜 응답.

실제 Gemini 는 부르지 않는다. gemini.transcribe · gemini.classify 를 바꿔 끼운다.
"""
import os
import tempfile
from pathlib import Path

import pytest

_tmp = Path(tempfile.mkdtemp(prefix="mnp-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["GEMINI_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from backend import gemini  # noqa: E402
from backend.db import Base, engine  # noqa: E402
from backend.main import app  # noqa: E402

WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 32
MP3 = b"ID3\x03\x00\x00\x00" + b"\x00" * 32
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 32

DEFAULT_CLASSIFY = {
    "summary": "2차 스프린트 계획 회의\n검색 범위를 제목과 참석자로 확정\n받아쓰기 유료 전환은 다음 회의로",
    "decisions": ["목록 검색은 제목과 참석자 범위로 한정", "회의록 공유는 팀원 전체(외부 제외)"],
    "todos": [
        {"what": "목록 화면 및 검색 구현", "assignee": "김대리님", "due": "다음 주 금요일"},
        {"what": "받아쓰기 오류 처리", "assignee": "이 주임", "due": "이번 주 안"},
        {"what": "사용자 다섯 분 인터뷰", "assignee": "", "due": ""},
    ],
}


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def fake_gemini(monkeypatch):
    """받아쓰기 · 구분 가짜 응답. calls 로 호출 횟수를 본다."""
    state = {"transcribe": 0, "classify": 0, "classify_result": DEFAULT_CLASSIFY,
             "body": "김대리: 목록은 제가 다음 주 금요일까지 하겠습니다."}

    def transcribe(data, mime):
        state["transcribe"] += 1
        return state["body"]

    def classify(body, names):
        state["classify"] += 1
        res = state["classify_result"]
        if isinstance(res, Exception):
            raise res
        return res

    monkeypatch.setattr(gemini, "transcribe", transcribe)
    monkeypatch.setattr(gemini, "classify", classify)
    return state


class Api:
    """가입 · 로그인 · 팀 만들기 도우미."""

    def __init__(self, client):
        self.c = client
        self.n = 0

    def signup(self, name="김대리", email=None, password="password1"):
        self.n += 1
        email = email or f"user{self.n}@example.com"
        r = self.c.post("/api/auth/signup", json={"email": email, "password": password, "name": name})
        assert r.status_code == 201, r.text
        return User(self.c, r.json())

    def team(self, owner, name="기획팀"):
        r = self.c.post("/api/teams", json={"name": name}, headers=owner.h)
        assert r.status_code == 201, r.text
        return r.json()

    def join(self, user, team):
        r = self.c.post("/api/teams/join", json={"invite_code": team["invite_code"]}, headers=user.h)
        assert r.status_code == 200, r.text
        return r.json()

    def meeting(self, user, team_id, title="2차 스프린트 계획 회의", met_at="2026-09-24T05:00:00Z",
                attendees="김대리, 박과장, 이주임", body="받아쓴 본문"):
        r = self.c.post(f"/api/teams/{team_id}/meetings",
                        json={"title": title, "met_at": met_at, "attendees": attendees, "body": body}, headers=user.h)
        assert r.status_code == 201, r.text
        return r.json()


class User:
    def __init__(self, client, data):
        self.token = data["token"]
        self.user = data["user"]
        self.id = data["user"]["id"]
        self.h = {"Authorization": f"Bearer {self.token}"}


@pytest.fixture
def api(client):
    return Api(client)


@pytest.fixture
def squad(api):
    """기획팀 - owner 김대리, member 박과장 · 이주임."""
    kim = api.signup("김대리")
    team = api.team(kim)
    park = api.signup("박과장")
    lee = api.signup("이주임")
    api.join(park, team)
    api.join(lee, team)
    return {"team": team, "tid": team["id"], "kim": kim, "park": park, "lee": lee}


def err(r, status, code):
    assert r.status_code == status, f"{r.status_code} {r.text}"
    body = r.json()
    assert body["code"] == code, body
    assert "msg" in body
