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
