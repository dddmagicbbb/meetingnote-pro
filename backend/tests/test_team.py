"""specs/team 서버 시나리오."""
import re

from backend.tests.conftest import err


def test_create_team_makes_owner_and_code(api, client):
    u = api.signup()
    t = api.team(u)
    assert t["role"] == "owner" and t["owner_id"] == u.id
    assert re.fullmatch(r"MN-[A-Z0-9]{4}", t["invite_code"])


def test_create_team_not_an_activity(api, client):
    u = api.signup()
    api.team(u)
    assert client.get("/api/me/activities", headers=u.h).json() == []


def test_one_person_one_team_create(api, client):
    u = api.signup()
    api.team(u)
    err(client.post("/api/teams", json={"name": "두번째"}, headers=u.h), 400, "VALIDATION_ERROR")


def test_one_person_one_team_join(api, client):
    a, b = api.signup("a"), api.signup("b")
    api.team(a, "A팀")
    tb = api.team(b, "B팀")
    err(client.post("/api/teams/join", json={"invite_code": tb["invite_code"]}, headers=a.h), 400, "VALIDATION_ERROR")


def test_list_teams_empty_when_no_team(api, client):
    u = api.signup()
    r = client.get("/api/teams", headers=u.h)
    assert r.status_code == 200 and r.json() == []


def test_join_records_member_join(squad, client):
    acts = client.get(f"/api/teams/{squad['tid']}/activities", headers=squad["kim"].h).json()
    joins = [a for a in acts if a["kind"] == "member_join"]
    assert len(joins) == 2
    assert any(a["text"] == "박과장 초대코드로 합류" for a in joins)


def test_join_role_is_member(squad, client):
    assert client.get("/api/auth/me", headers=squad["park"].h).json()["role"] == "member"


def test_join_unknown_code(api, client):
    u = api.signup()
    err(client.post("/api/teams/join", json={"invite_code": "MN-0000"}, headers=u.h), 404, "INVITE_NOT_FOUND")
    assert client.get("/api/auth/me", headers=u.h).status_code == 200  # 계정 유지


def test_team_full_at_six(api, client):
    owner = api.signup("owner")
    t = api.team(owner)
    for i in range(5):
        api.join(api.signup(f"m{i}"), t)
    seventh = api.signup("seventh")
    err(client.post("/api/teams/join", json={"invite_code": t["invite_code"]}, headers=seventh.h), 409, "TEAM_FULL")


def test_members_with_todo_count_including_done(squad, client):
    tid, kim = squad["tid"], squad["kim"]
    ids = []
    for what in ("a", "b", "c"):
        ids.append(client.post(f"/api/teams/{tid}/todos", json={"what": what, "assignee_id": kim.id}, headers=kim.h).json()["id"])
    client.put(f"/api/todos/{ids[0]}", json={"status": "DONE"}, headers=kim.h)
    members = client.get(f"/api/teams/{tid}/members", headers=kim.h).json()
    by = {m["name"]: m for m in members}
    assert by["김대리"]["todo_count"] == 3
    assert set(by["김대리"]) == {"id", "name", "email", "role", "todo_count"}
    assert by["김대리"]["role"] == "owner" and by["박과장"]["role"] == "member"


def test_members_other_team_forbidden(squad, api, client):
    outsider = api.signup("외부")
    err(client.get(f"/api/teams/{squad['tid']}/members", headers=outsider.h), 403, "FORBIDDEN")


def test_reissue_code_invalidates_old(squad, api, client):
    old = squad["team"]["invite_code"]
    r = client.put(f"/api/teams/{squad['tid']}/code", headers=squad["kim"].h)
    assert r.status_code == 200
    new = r.json()["invite_code"]
    assert new != old
    newbie = api.signup("신규")
    err(client.post("/api/teams/join", json={"invite_code": old}, headers=newbie.h), 404, "INVITE_NOT_FOUND")
    assert client.post("/api/teams/join", json={"invite_code": new}, headers=newbie.h).status_code == 200
    # 이미 합류한 멤버는 그대로
    assert len(client.get(f"/api/teams/{squad['tid']}/members", headers=squad["kim"].h).json()) == 4


def test_rename_by_owner(squad, client):
    r = client.put(f"/api/teams/{squad['tid']}", json={"name": "기획1팀"}, headers=squad["kim"].h)
    assert r.status_code == 200 and r.json()["name"] == "기획1팀"


def test_owner_only_for_member(squad, client):
    err(client.put(f"/api/teams/{squad['tid']}", json={"name": "x"}, headers=squad["park"].h), 403, "OWNER_ONLY")
    err(client.put(f"/api/teams/{squad['tid']}/code", headers=squad["park"].h), 403, "OWNER_ONLY")
