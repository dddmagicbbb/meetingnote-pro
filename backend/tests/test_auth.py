"""specs/auth 서버 시나리오."""
import time
from datetime import datetime, timedelta, timezone

from backend import security
from backend.db import SessionLocal
from backend.models import User
from backend.tests.conftest import err


def test_signup_returns_token_and_user_with_bcrypt_hash(client):
    r = client.post("/api/auth/signup", json={"email": "hong@example.com", "password": "password1", "name": "홍길동"})
    assert r.status_code == 201
    body = r.json()
    assert body["token"]
    assert body["user"] == {"id": body["user"]["id"], "name": "홍길동", "email": "hong@example.com", "role": None}
    with SessionLocal() as db:
        u = db.get(User, body["user"]["id"])
        assert u.password_hash != "password1"
        assert u.password_hash.startswith("$2")


def test_signup_is_fast_enough(client):
    t = time.perf_counter()
    client.post("/api/auth/signup", json={"email": "fast@example.com", "password": "password1", "name": "a"})
    assert time.perf_counter() - t < 0.25  # ACME Metrics 250ms


def test_signup_email_invalid(client):
    err(client.post("/api/auth/signup", json={"email": "hong@example", "password": "password1", "name": "a"}),
        400, "EMAIL_INVALID")


def test_signup_password_too_weak(client):
    err(client.post("/api/auth/signup", json={"email": "a@example.com", "password": "12345", "name": "a"}),
        400, "PASSWORD_TOO_WEAK")


def test_signup_missing_fields_is_validation_error(client):
    err(client.post("/api/auth/signup", json={}), 400, "VALIDATION_ERROR")


def test_signup_duplicate_email(api, client):
    api.signup(email="kim@example.com")
    err(client.post("/api/auth/signup", json={"email": "kim@example.com", "password": "password1", "name": "b"}),
        409, "EMAIL_DUPLICATED")


def test_login_success(api, client):
    api.signup(email="kim@example.com")
    r = client.post("/api/auth/login", json={"email": "kim@example.com", "password": "password1"})
    assert r.status_code == 200
    assert r.json()["token"] and r.json()["user"]["email"] == "kim@example.com"


def test_login_failure_is_same_for_wrong_password_and_unknown_email(api, client):
    api.signup(email="kim@example.com")
    a = client.post("/api/auth/login", json={"email": "kim@example.com", "password": "wrongpass"})
    b = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrongpass"})
    err(a, 401, "INVALID_CREDENTIALS")
    err(b, 401, "INVALID_CREDENTIALS")
    assert a.json() == b.json()


def test_no_token_is_token_expired(client):
    err(client.get("/api/auth/me"), 401, "TOKEN_EXPIRED")


def test_forged_token_is_token_expired(client):
    err(client.get("/api/auth/me", headers={"Authorization": "Bearer abc.def.ghi"}), 401, "TOKEN_EXPIRED")


def test_expired_token(api, client):
    u = api.signup()
    old = security.create_token(u.id, now=datetime.now(timezone.utc) - timedelta(hours=24, minutes=1))
    err(client.get("/api/auth/me", headers={"Authorization": f"Bearer {old}"}), 401, "TOKEN_EXPIRED")


def test_token_valid_just_under_24h(api, client):
    u = api.signup()
    tok = security.create_token(u.id, now=datetime.now(timezone.utc) - timedelta(hours=23, minutes=59))
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 200


def test_me_includes_owner_role(api, client):
    u = api.signup()
    api.team(u)
    assert client.get("/api/auth/me", headers=u.h).json()["role"] == "owner"


def test_update_name_only_keeps_password(api, client):
    u = api.signup(email="kim@example.com")
    r = client.put("/api/auth/me", json={"name": "김과장"}, headers=u.h)
    assert r.status_code == 200 and r.json()["name"] == "김과장"
    assert client.post("/api/auth/login", json={"email": "kim@example.com", "password": "password1"}).status_code == 200


def test_update_password(api, client):
    u = api.signup(email="kim@example.com")
    assert client.put("/api/auth/me", json={"password": "newpassword"}, headers=u.h).status_code == 200
    assert client.post("/api/auth/login", json={"email": "kim@example.com", "password": "newpassword"}).status_code == 200


def test_update_password_too_weak(api, client):
    u = api.signup()
    err(client.put("/api/auth/me", json={"password": "1234567"}, headers=u.h), 400, "PASSWORD_TOO_WEAK")


def test_account_change_is_not_an_activity(api, client):
    u = api.signup()
    api.team(u)
    client.put("/api/auth/me", json={"name": "김과장"}, headers=u.h)
    assert client.get("/api/me/activities", headers=u.h).json() == []


def test_logout_returns_200(api, client):
    u = api.signup()
    assert client.post("/api/auth/logout", headers=u.h).status_code == 200
