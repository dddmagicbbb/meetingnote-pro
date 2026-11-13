"""specs/todo 서버 시나리오."""
from backend.tests.conftest import err


def add(client, user, tid, what="할 일", assignee_id=None, due_text=""):
    r = client.post(f"/api/teams/{tid}/todos", json={"what": what, "assignee_id": assignee_id, "due_text": due_text},
                    headers=user.h)
    assert r.status_code == 201, r.text
    return r.json()


def test_list_fields_with_meeting_title(squad, api, client, fake_gemini):
    api.meeting(squad["kim"], squad["tid"], title="2차 스프린트 계획 회의")
    add(client, squad["kim"], squad["tid"], "직접 등록 건")
    rows = client.get(f"/api/teams/{squad['tid']}/todos", headers=squad["kim"].h).json()
    assert set(rows[0]) >= {"id", "what", "assignee_id", "assignee_name", "due_text", "status",
                            "meeting_title", "can_delete"}
    by = {r["what"]: r for r in rows}
    assert by["목록 화면 및 검색 구현"]["meeting_title"] == "2차 스프린트 계획 회의"
    assert by["직접 등록 건"]["meeting_title"] is None


def test_sort_status_then_due(squad, client):
    k, tid = squad["kim"], squad["tid"]
    a = add(client, k, tid, "a", due_text="나")
    add(client, k, tid, "b", due_text="가")
    c = add(client, k, tid, "c", due_text="다")
    client.put(f"/api/todos/{a['id']}", json={"status": "DONE"}, headers=k.h)
    client.put(f"/api/todos/{c['id']}", json={"status": "DOING"}, headers=k.h)
    rows = client.get(f"/api/teams/{tid}/todos", headers=k.h).json()
    assert [r["what"] for r in rows] == ["b", "c", "a"]


def test_my_todos_only_mine(squad, client):
    k, p, tid = squad["kim"], squad["park"], squad["tid"]
    add(client, k, tid, "김 것", k.id)
    add(client, k, tid, "박 것", p.id)
    add(client, k, tid, "미정")
    mine = client.get("/api/me/todos", headers=k.h).json()
    assert [t["what"] for t in mine] == ["김 것"]


def test_my_todos_empty(squad, client):
    r = client.get("/api/me/todos", headers=squad["lee"].h)
    assert r.status_code == 200 and r.json() == []


def test_status_done_records_and_back(squad, client):
    k, p, tid = squad["kim"], squad["park"], squad["tid"]
    t = add(client, k, tid, "배포 키 환경변수 이전")
    r = client.put(f"/api/todos/{t['id']}", json={"status": "DONE"}, headers=p.h)  # 팀원 누구나
    assert r.status_code == 200 and r.json()["status"] == "DONE"
    acts = client.get(f"/api/teams/{tid}/activities", headers=k.h).json()
    assert acts[0]["kind"] == "todo_done" and acts[0]["text"] == "박과장 할 일 「배포 키 환경변수 이전」 완료"
    assert client.put(f"/api/todos/{t['id']}", json={"status": "OPEN"}, headers=p.h).json()["status"] == "OPEN"


def test_unknown_status(squad, client):
    t = add(client, squad["kim"], squad["tid"])
    err(client.put(f"/api/todos/{t['id']}", json={"status": "CLOSED"}, headers=squad["kim"].h), 400, "VALIDATION_ERROR")


def test_assign_records_and_unassign(squad, client):
    k, l, tid = squad["kim"], squad["lee"], squad["tid"]
    t = add(client, k, tid, "사용자 인터뷰")
    r = client.put(f"/api/todos/{t['id']}", json={"assignee_id": l.id, "due_text": "다음 달 10일"}, headers=k.h)
    assert r.json()["assignee_name"] == "이주임" and r.json()["due_text"] == "다음 달 10일"
    acts = client.get(f"/api/teams/{tid}/activities", headers=k.h).json()
    assert acts[0]["kind"] == "todo_assign"
    r = client.put(f"/api/todos/{t['id']}", json={"assignee_id": None}, headers=k.h)
    assert r.json()["assignee_id"] is None


def test_assignee_outside_team(squad, api, client):
    outsider = api.signup("외부")
    t = add(client, squad["kim"], squad["tid"])
    err(client.put(f"/api/todos/{t['id']}", json={"assignee_id": outsider.id}, headers=squad["kim"].h),
        400, "VALIDATION_ERROR")


def test_done_is_kept(squad, client):
    k, tid = squad["kim"], squad["tid"]
    t = add(client, k, tid)
    client.put(f"/api/todos/{t['id']}", json={"status": "DONE"}, headers=k.h)
    assert [r["status"] for r in client.get(f"/api/teams/{tid}/todos", headers=k.h).json()] == ["DONE"]


def test_delete_permissions(squad, client):
    k, p, l, tid = squad["kim"], squad["park"], squad["lee"], squad["tid"]
    t = add(client, p, tid, "박이 만든 것", assignee_id=l.id)
    rows = {r["id"]: r for r in client.get(f"/api/teams/{tid}/todos", headers=p.h).json()}
    assert rows[t["id"]]["can_delete"] is True
    # 만든 사람 · 담당자 · owner 가 아닌 사람 없음 → 새 멤버로 확인
    t2 = add(client, p, tid, "박 혼자")
    err(client.delete(f"/api/todos/{t2['id']}", headers=l.h), 403, "FORBIDDEN")
    assert {r["id"]: r for r in client.get(f"/api/teams/{tid}/todos", headers=l.h).json()}[t2["id"]]["can_delete"] is False
    assert client.delete(f"/api/todos/{t['id']}", headers=l.h).status_code == 204   # 담당자
    assert client.delete(f"/api/todos/{t2['id']}", headers=k.h).status_code == 204  # owner


def test_meeting_author_can_delete_extracted_todo(squad, api, client, fake_gemini):
    m = api.meeting(squad["park"], squad["tid"])
    tid_ = m["todos"][2]["id"]  # 미정 할 일
    assert client.delete(f"/api/todos/{tid_}", headers=squad["park"].h).status_code == 204


def test_create_direct(squad, client):
    k, l, tid = squad["kim"], squad["lee"], squad["tid"]
    t = add(client, k, tid, "회의실 예약 규칙 정리", l.id, "이번 주 안")
    assert t["status"] == "OPEN" and t["meeting_title"] is None and t["assignee_name"] == "이주임"
    acts = client.get(f"/api/teams/{tid}/activities", headers=k.h).json()
    assert acts[0]["kind"] == "todo_assign"
    assert acts[0]["text"] == "김대리 할 일 「회의실 예약 규칙 정리」 를 이주임에게 배정"


def test_create_direct_without_assignee_records_nothing(squad, client):
    k, tid = squad["kim"], squad["tid"]
    before = len(client.get(f"/api/teams/{tid}/activities", headers=k.h).json())
    add(client, k, tid, "담당자 없는 일")
    assert len(client.get(f"/api/teams/{tid}/activities", headers=k.h).json()) == before


def test_create_requires_what(squad, client):
    err(client.post(f"/api/teams/{squad['tid']}/todos", json={"what": " "}, headers=squad["kim"].h),
        400, "VALIDATION_ERROR")


def test_other_team_todos_forbidden(squad, api, client):
    outsider = api.signup("외부")
    err(client.get(f"/api/teams/{squad['tid']}/todos", headers=outsider.h), 403, "FORBIDDEN")


# ── 기한 날짜 (modify-todo-due-date) ─────────────────────
from datetime import timedelta  # noqa: E402

from backend.duedate import kst_date  # noqa: E402


def test_direct_due_uses_registration_day(squad, client):
    t = add(client, squad["kim"], squad["tid"], "x", due_text="다음 주까지")
    assert t["due_date"] == (kst_date(None) + timedelta(days=7)).isoformat()
    assert t["due_text"] == "다음 주까지"


def test_direct_undecidable_due(squad, client):
    t = add(client, squad["kim"], squad["tid"], "x", due_text="다음 분기")
    assert t["due_date"] is None and t["due_text"] == "다음 분기"


def test_edit_due_text_recomputes_from_meeting_date(squad, api, client, fake_gemini):
    m = api.meeting(squad["kim"], squad["tid"])  # 회의 9/24(목)
    todo_id = m["todos"][2]["id"]
    r = client.put(f"/api/todos/{todo_id}", json={"due_text": "다음 주까지"}, headers=squad["kim"].h)
    assert r.status_code == 200
    assert r.json()["due_date"] == "2026-10-01" and r.json()["due_text"] == "다음 주까지"
    r = client.put(f"/api/todos/{todo_id}", json={"due_text": "곧"}, headers=squad["kim"].h)
    assert r.json()["due_date"] is None


def test_sort_by_due_date_nulls_last(squad, api, client, fake_gemini):
    fake_gemini["classify_result"] = {"summary": "s", "decisions": [], "todos": [
        {"what": "a", "assignee": "", "due": "다음 주 금요일"},   # 10-02
        {"what": "b", "assignee": "", "due": "다음 분기"},        # null
        {"what": "c", "assignee": "", "due": "이번 주 안"},       # 09-25
    ]}
    api.meeting(squad["kim"], squad["tid"])
    rows = client.get(f"/api/teams/{squad['tid']}/todos", headers=squad["kim"].h).json()
    assert [r["what"] for r in rows] == ["c", "a", "b"]
    assert [r["due_date"] for r in rows] == ["2026-09-25", "2026-10-02", None]


def test_migrate_adds_column_and_fills(tmp_path):
    import sqlalchemy as sa

    from backend.db import Base, migrate
    eng = sa.create_engine(f"sqlite:///{(tmp_path / 'old.db').as_posix()}")
    Base.metadata.create_all(eng)
    with eng.begin() as c:
        c.execute(sa.text("ALTER TABLE todos DROP COLUMN due_date"))  # 옛 스키마 흉내
        c.execute(sa.text("INSERT INTO users (id,email,password_hash,name,created_at) VALUES (1,'a@a.com','x','a','2026-01-01')"))
        c.execute(sa.text("INSERT INTO teams (id,name,invite_code,owner_id,created_at) VALUES (1,'t','MN-AAAA',1,'2026-01-01')"))
        c.execute(sa.text("INSERT INTO meetings (id,team_id,title,met_at,attendees,body,summary,decisions,author_id,created_at) "
                          "VALUES (1,1,'m','2026-09-24 05:00:00','','b','','',1,'2026-09-24')"))
        c.execute(sa.text("INSERT INTO todos (team_id,meeting_id,what,due_text,status,author_id,created_at) VALUES "
                          "(1,1,'a','다음 주 금요일','OPEN',1,'2026-09-24'),(1,1,'b','다음 분기','OPEN',1,'2026-09-24'),"
                          "(1,NULL,'c','내일','OPEN',1,'2026-11-13 01:00:00')"))
    assert migrate(eng) == 2
    assert migrate(eng) == 0  # 두 번 돌려도 같음
    with eng.connect() as c:
        got = dict(c.execute(sa.text("SELECT what, due_date FROM todos")).all())
    assert got == {"a": "2026-10-02", "b": None, "c": "2026-11-14"}
