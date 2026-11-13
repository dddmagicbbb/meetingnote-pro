"""specs/comment 서버 시나리오."""
from backend.tests.conftest import err


def meeting(api, squad):
    return api.meeting(squad["kim"], squad["tid"])


def post(client, user, mid, content):
    return client.post(f"/api/meetings/{mid}/comments", json={"content": content}, headers=user.h)


def test_list_oldest_first(squad, api, client, fake_gemini):
    m = meeting(api, squad)
    post(client, squad["park"], m["id"], "첫째")
    post(client, squad["lee"], m["id"], "둘째")
    rows = client.get(f"/api/meetings/{m['id']}/comments", headers=squad["kim"].h).json()
    assert [r["content"] for r in rows] == ["첫째", "둘째"]
    assert set(rows[0]) == {"id", "user_id", "user_name", "content", "created_at", "can_delete"}
    assert rows[0]["user_name"] == "박과장"


def test_empty(squad, api, client, fake_gemini):
    m = meeting(api, squad)
    r = client.get(f"/api/meetings/{m['id']}/comments", headers=squad["kim"].h)
    assert r.status_code == 200 and r.json() == []


def test_create_records_activity(squad, api, client, fake_gemini):
    m = meeting(api, squad)
    r = post(client, squad["park"], m["id"], "기한은 금요일로 확정했으면 함")
    assert r.status_code == 201
    acts = client.get(f"/api/teams/{squad['tid']}/activities", headers=squad["kim"].h).json()
    assert acts[0]["kind"] == "comment_add"


def test_500_limit(squad, api, client, fake_gemini):
    m = meeting(api, squad)
    assert post(client, squad["kim"], m["id"], "가" * 500).status_code == 201
    err(post(client, squad["kim"], m["id"], "가" * 501), 400, "VALIDATION_ERROR")
    err(post(client, squad["kim"], m["id"], "   "), 400, "VALIDATION_ERROR")


def test_delete_by_author_and_owner_only(squad, api, client, fake_gemini):
    m = meeting(api, squad)
    c1 = post(client, squad["park"], m["id"], "박").json()
    c2 = post(client, squad["park"], m["id"], "박2").json()
    rows = {r["id"]: r for r in client.get(f"/api/meetings/{m['id']}/comments", headers=squad["lee"].h).json()}
    assert rows[c1["id"]]["can_delete"] is False
    err(client.delete(f"/api/comments/{c1['id']}", headers=squad["lee"].h), 403, "FORBIDDEN")
    assert client.delete(f"/api/comments/{c1['id']}", headers=squad["kim"].h).status_code == 204  # owner
    assert client.delete(f"/api/comments/{c2['id']}", headers=squad["park"].h).status_code == 204  # 쓴 사람
