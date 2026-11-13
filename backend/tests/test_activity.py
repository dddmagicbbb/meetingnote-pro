"""specs/activity 서버 시나리오."""
from backend.db import SessionLocal
from backend.deps import ACTIVITY_KINDS
from backend.models import Activity
from backend.tests.conftest import err


def test_only_five_kinds(squad, api, client, fake_gemini):
    k, tid = squad["kim"], squad["tid"]
    m = api.meeting(k, tid)
    client.post(f"/api/meetings/{m['id']}/comments", json={"content": "c"}, headers=k.h)
    client.put(f"/api/todos/{m['todos'][0]['id']}", json={"status": "DONE"}, headers=k.h)
    client.put(f"/api/teams/{tid}", json={"name": "새이름"}, headers=k.h)
    client.put(f"/api/teams/{tid}/code", headers=k.h)
    client.put("/api/auth/me", json={"name": "김과장"}, headers=k.h)
    client.delete(f"/api/meetings/{m['id']}", headers=k.h)
    with SessionLocal() as db:
        kinds = {a.kind for a in db.query(Activity).all()}
    assert kinds == set(ACTIVITY_KINDS)


def test_team_creation_not_recorded(api, client):
    u = api.signup()
    api.team(u)
    r = client.get("/api/me/activities", headers=u.h)
    assert r.status_code == 200 and r.json() == []


def test_team_activities_fields_and_text(squad, api, client, fake_gemini):
    api.meeting(squad["kim"], squad["tid"], title="2차 스프린트 계획 회의")
    rows = client.get(f"/api/teams/{squad['tid']}/activities", headers=squad["park"].h).json()
    assert set(rows[0]) == {"id", "kind", "actor_name", "text", "created_at"}
    adds = [r for r in rows if r["kind"] == "meeting_add"]
    assert adds[0]["text"] == "김대리 회의록 「2차 스프린트 계획 회의」 등록"
    # 최근순
    assert [r["id"] for r in rows] == sorted((r["id"] for r in rows), reverse=True)


def test_limit_50(squad, client):
    k, tid = squad["kim"], squad["tid"]
    t = client.post(f"/api/teams/{tid}/todos", json={"what": "x"}, headers=k.h).json()
    for i in range(30):
        client.put(f"/api/todos/{t['id']}", json={"status": "DONE"}, headers=k.h)
        client.put(f"/api/todos/{t['id']}", json={"status": "OPEN"}, headers=k.h)
        client.put(f"/api/todos/{t['id']}", json={"assignee_id": squad["park"].id if i % 2 else k.id}, headers=k.h)
    assert len(client.get(f"/api/teams/{tid}/activities", headers=k.h).json()) == 50


def test_my_activities_only_mine(squad, client):
    k, p, tid = squad["kim"], squad["park"], squad["tid"]
    t = client.post(f"/api/teams/{tid}/todos", json={"what": "x"}, headers=k.h).json()
    client.put(f"/api/todos/{t['id']}", json={"status": "DONE"}, headers=p.h)
    mine = client.get("/api/me/activities", headers=p.h).json()
    assert {a["kind"] for a in mine} == {"member_join", "todo_done"}
    assert all(a["actor_name"] == "박과장" for a in mine)


def test_other_team_forbidden(squad, api, client):
    outsider = api.signup("외부")
    err(client.get(f"/api/teams/{squad['tid']}/activities", headers=outsider.h), 403, "FORBIDDEN")
