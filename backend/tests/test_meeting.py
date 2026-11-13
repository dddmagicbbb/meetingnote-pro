"""specs/meeting 서버 시나리오."""
import pytest
from google.genai import errors as gerr

from backend import gemini
from backend.db import SessionLocal
from backend.errors import ApiError
from backend.models import Meeting
from backend.tests.conftest import MP3, MP4, WAV, err


def upload(client, user, data, name="회의_녹음.wav"):
    return client.post("/api/upload", files={"file": (name, data, "audio/wav")}, headers=user.h)


# ── 업로드 ──────────────────────────────────────────────
def test_upload_wav_returns_body_without_saving(squad, client, fake_gemini):
    r = upload(client, squad["kim"], WAV)
    assert r.status_code == 200 and r.json() == {"body": fake_gemini["body"]}
    with SessionLocal() as db:
        assert db.query(Meeting).count() == 0


def test_upload_mp3(squad, client, fake_gemini):
    assert upload(client, squad["kim"], MP3, "a.mp3").status_code == 200


def test_upload_mp4_rejected(squad, client, fake_gemini):
    err(upload(client, squad["kim"], MP4, "회의_녹화.mp4"), 415, "UNSUPPORTED_MEDIA_TYPE")


def test_upload_renamed_mp4_rejected_by_content(squad, client, fake_gemini):
    err(upload(client, squad["kim"], MP4, "가짜.wav"), 415, "UNSUPPORTED_MEDIA_TYPE")
    assert fake_gemini["transcribe"] == 0


def test_upload_without_key_is_502(squad, client):
    err(upload(client, squad["kim"], WAV), 502, "VALIDATION_ERROR")


def test_provider_5xx_retried_once_then_502():
    calls = {"n": 0}

    def boom():
        calls["n"] += 1
        raise gerr.ServerError(503, {"error": {"code": 503, "message": "unavailable", "status": "UNAVAILABLE"}})

    with pytest.raises(ApiError) as e:
        gemini._with_retry(boom, "받아쓰기")
    assert calls["n"] == 2 and e.value.status == 502 and e.value.code == "VALIDATION_ERROR"


def test_provider_5xx_then_success():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise gerr.ServerError(500, {"error": {"code": 500, "message": "x", "status": "INTERNAL"}})
        return "ok"

    assert gemini._with_retry(flaky, "x") == "ok" and calls["n"] == 2


class _FakeClient:
    """google-genai Client 흉내 - 어느 경로로 보냈는지 기록."""

    def __init__(self):
        self.uploaded = []
        self.contents = None
        outer = self

        class Files:
            def upload(self, file, config):
                outer.uploaded.append((len(file.read()), config["mime_type"]))
                return "FILE_REF"

        class Models:
            def generate_content(self, model, contents, config=None):
                outer.contents = contents

                class R:
                    text = "받아쓴 본문"
                return R()

        self.files = Files()
        self.models = Models()


def test_transcribe_over_20mb_uses_files_api(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(gemini, "_client", lambda: fake)
    big = WAV + b"\x00" * (gemini.INLINE_LIMIT + 1)
    assert gemini.transcribe(big, "audio/wav") == "받아쓴 본문"
    assert fake.uploaded == [(len(big), "audio/wav")]
    assert fake.contents[1] == "FILE_REF"


def test_transcribe_small_file_is_inline(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(gemini, "_client", lambda: fake)
    assert gemini.transcribe(WAV, "audio/wav") == "받아쓴 본문"
    assert fake.uploaded == []
    assert fake.contents[1] != "FILE_REF"


def test_parse_classification_rejects_garbage():
    with pytest.raises(ApiError) as e:
        gemini.parse_classification("이건 JSON 이 아님")
    assert e.value.status == 502


def test_parse_classification_summary_lines():
    res = gemini.parse_classification('{"summary":["첫 줄"," 둘째 줄 ",""],"decisions":["a",""],"todos":[]}')
    assert res["summary"] == "첫 줄\n둘째 줄" and res["decisions"] == ["a"]


# ── 저장과 세 갈래 ──────────────────────────────────────
def test_save_splits_three_ways_and_records(squad, api, client, fake_gemini):
    m = api.meeting(squad["kim"], squad["tid"])
    assert m["summary"].startswith("2차 스프린트")
    assert m["decisions"] == ["목록 검색은 제목과 참석자 범위로 한정", "회의록 공유는 팀원 전체(외부 제외)"]
    assert m["decision_count"] == 2 and m["todo_total_count"] == 3 and m["todo_done_count"] == 0
    assert m["body"] == "받아쓴 본문"
    todos = {t["what"]: t for t in m["todos"]}
    # 존칭 · 공백 무시 대조
    assert todos["목록 화면 및 검색 구현"]["assignee_name"] == "김대리"
    assert todos["목록 화면 및 검색 구현"]["due_text"] == "다음 주 금요일"
    assert todos["받아쓰기 오류 처리"]["assignee_name"] == "이주임"
    assert todos["사용자 다섯 분 인터뷰"]["assignee_id"] is None
    assert all(t["status"] == "OPEN" for t in m["todos"])
    kinds = [a["kind"] for a in client.get(f"/api/teams/{squad['tid']}/activities", headers=squad["kim"].h).json()]
    assert kinds.count("meeting_add") == 1 and kinds.count("todo_assign") == 2


def test_unknown_assignee_is_unassigned(squad, api, fake_gemini):
    fake_gemini["classify_result"] = {"summary": "s", "decisions": [],
                                      "todos": [{"what": "x", "assignee": "최선임", "due": "내일"}]}
    m = api.meeting(squad["kim"], squad["tid"])
    assert m["todos"][0]["assignee_id"] is None


def test_save_requires_body(squad, client, fake_gemini):
    r = client.post(f"/api/teams/{squad['tid']}/meetings",
                    json={"title": "t", "met_at": "2026-09-24T05:00:00Z", "body": "  "}, headers=squad["kim"].h)
    err(r, 400, "VALIDATION_ERROR")


def test_classify_failure_does_not_save(squad, client, fake_gemini):
    fake_gemini["classify_result"] = ApiError(502, "VALIDATION_ERROR", "구분 실패")
    r = client.post(f"/api/teams/{squad['tid']}/meetings",
                    json={"title": "t", "met_at": "2026-09-24T05:00:00Z", "body": "본문"}, headers=squad["kim"].h)
    err(r, 502, "VALIDATION_ERROR")
    with SessionLocal() as db:
        assert db.query(Meeting).count() == 0


# ── 목록 · 검색 · 기간 ──────────────────────────────────
@pytest.fixture
def three(squad, api, fake_gemini):
    kim, tid = squad["kim"], squad["tid"]
    fake_gemini["classify_result"] = {"summary": "s", "decisions": ["d"], "todos": []}
    api.meeting(kim, tid, "기획 킥오프", "2026-09-10T00:00:00Z", "김대리, 박과장, 이주임, 최선임", body="예산 이야기")
    api.meeting(kim, tid, "배포 환경 점검", "2026-09-18T01:30:00Z", "박과장, 최선임")
    api.meeting(kim, tid, "2차 스프린트 계획 회의", "2026-09-24T05:00:00Z", "김대리, 박과장, 이주임")
    return squad


def test_list_fields_order_and_no_body(three, client):
    rows = client.get(f"/api/teams/{three['tid']}/meetings", headers=three["kim"].h).json()
    assert [r["title"] for r in rows] == ["2차 스프린트 계획 회의", "배포 환경 점검", "기획 킥오프"]
    assert set(rows[0]) == {"id", "title", "met_at", "attendees", "summary", "created_at",
                            "todo_done_count", "todo_total_count", "decision_count"}
    assert rows[0]["met_at"] == "2026-09-24T05:00:00Z"


def test_empty_list(squad, client):
    r = client.get(f"/api/teams/{squad['tid']}/meetings", headers=squad["kim"].h)
    assert r.status_code == 200 and r.json() == []


def test_search_title(three, client):
    rows = client.get(f"/api/teams/{three['tid']}/meetings", params={"q": "배포"}, headers=three["kim"].h).json()
    assert [r["title"] for r in rows] == ["배포 환경 점검"]


def test_search_attendee(three, client):
    rows = client.get(f"/api/teams/{three['tid']}/meetings", params={"q": "최선임"}, headers=three["kim"].h).json()
    assert len(rows) == 2


def test_search_body_not_matched(three, client):
    r = client.get(f"/api/teams/{three['tid']}/meetings", params={"q": "예산"}, headers=three["kim"].h)
    assert r.status_code == 200 and r.json() == []


def test_search_wildcards_are_literal(three, api, client, fake_gemini):
    api.meeting(three["kim"], three["tid"], "전환율 100% 달성 회의", "2026-09-25T00:00:00Z", "박과장")
    h, tid = three["kim"].h, three["tid"]
    assert [r["title"] for r in client.get(f"/api/teams/{tid}/meetings", params={"q": "%"}, headers=h).json()] \
        == ["전환율 100% 달성 회의"]
    assert client.get(f"/api/teams/{tid}/meetings", params={"q": "_"}, headers=h).json() == []


def test_period_filter(three, client):
    rows = client.get(f"/api/teams/{three['tid']}/meetings", params={"from": "2026-09-01", "to": "2026-09-18"},
                      headers=three["kim"].h).json()
    assert [r["title"] for r in rows] == ["배포 환경 점검", "기획 킥오프"]


# ── 단건 · 수정 · 삭제 · 권한 ───────────────────────────
def test_detail_has_body_todos_can_edit(squad, api, client, fake_gemini):
    m = api.meeting(squad["kim"], squad["tid"])
    d = client.get(f"/api/meetings/{m['id']}", headers=squad["park"].h).json()
    assert d["body"] == "받아쓴 본문" and len(d["todos"]) == 3
    assert d["can_edit"] is False
    assert client.get(f"/api/meetings/{m['id']}", headers=squad["kim"].h).json()["can_edit"] is True


def test_owner_can_edit_others_meeting(squad, api, client, fake_gemini):
    m = api.meeting(squad["park"], squad["tid"])
    assert client.get(f"/api/meetings/{m['id']}", headers=squad["kim"].h).json()["can_edit"] is True


def test_update_body_does_not_reclassify(squad, api, client, fake_gemini):
    m = api.meeting(squad["kim"], squad["tid"])
    before = fake_gemini["classify"]
    r = client.put(f"/api/meetings/{m['id']}", json={"body": "고친 본문", "title": "2차 (확정)"}, headers=squad["kim"].h)
    assert r.status_code == 200
    d = r.json()
    assert d["body"] == "고친 본문" and d["title"] == "2차 (확정)"
    assert d["summary"] == m["summary"] and d["decisions"] == m["decisions"] and len(d["todos"]) == 3
    assert fake_gemini["classify"] == before


def test_update_by_other_member_forbidden(squad, api, client, fake_gemini):
    m = api.meeting(squad["kim"], squad["tid"])
    err(client.put(f"/api/meetings/{m['id']}", json={"title": "x"}, headers=squad["park"].h), 403, "FORBIDDEN")
    err(client.delete(f"/api/meetings/{m['id']}", headers=squad["park"].h), 403, "FORBIDDEN")


def test_delete_cascades_todos_and_comments(squad, api, client, fake_gemini):
    kim, tid = squad["kim"], squad["tid"]
    m = api.meeting(kim, tid)
    client.post(f"/api/meetings/{m['id']}/comments", json={"content": "의견"}, headers=kim.h)
    assert client.delete(f"/api/meetings/{m['id']}", headers=kim.h).status_code == 204
    assert client.get(f"/api/teams/{tid}/todos", headers=kim.h).json() == []
    err(client.get(f"/api/meetings/{m['id']}/comments", headers=kim.h), 404, "MEETING_NOT_FOUND")


def test_missing_meeting(squad, client):
    err(client.get("/api/meetings/99", headers=squad["kim"].h), 404, "MEETING_NOT_FOUND")


def test_other_team_meeting_is_not_found(squad, api, client, fake_gemini):
    m = api.meeting(squad["kim"], squad["tid"])
    outsider = api.signup("외부")
    api.team(outsider, "다른팀")
    err(client.get(f"/api/meetings/{m['id']}", headers=outsider.h), 404, "MEETING_NOT_FOUND")


# ── 기한 날짜 (modify-todo-due-date) ─────────────────────
def test_save_converts_due_by_meeting_date(squad, api, fake_gemini):
    # met_at 2026-09-24T05:00Z = 한국 9/24(목) 14:00
    m = api.meeting(squad["kim"], squad["tid"])
    by = {t["what"]: t for t in m["todos"]}
    assert by["목록 화면 및 검색 구현"]["due_text"] == "다음 주 금요일"
    assert by["목록 화면 및 검색 구현"]["due_date"] == "2026-10-02"
    assert by["받아쓰기 오류 처리"]["due_date"] == "2026-09-25"   # 이번 주 안 → 그 주 금요일
    assert by["사용자 다섯 분 인터뷰"]["due_date"] is None and by["사용자 다섯 분 인터뷰"]["due_text"] == ""


def test_due_base_is_korean_date_of_meeting(squad, api, fake_gemini):
    # UTC 9/23 15:30 = 한국 9/24 00:30 → 기준일 9/24
    fake_gemini["classify_result"] = {"summary": "s", "decisions": [],
                                      "todos": [{"what": "x", "assignee": "", "due": "내일"}]}
    m = api.meeting(squad["kim"], squad["tid"], met_at="2026-09-23T15:30:00Z")
    assert m["todos"][0]["due_date"] == "2026-09-25"
