import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import Base, engine
from app.main import app
from app.seed import seed


@pytest.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t/api/v1") as c:
        yield c


async def _signup_signin(c, email="a@b.com", pw="password123"):
    r = await c.post("/auth/signup", json={"name": "A", "email": email, "password": pw})
    assert r.status_code == 201
    r = await c.post("/auth/signin", json={"email": email, "password": pw})
    assert r.status_code == 200
    return r.json()


async def test_auth_flow(client):
    tok = await _signup_signin(client)
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    assert (await client.get("/users/me", headers=h)).json()["email"] == "a@b.com"

    # duplicate + bad password
    r = await client.post(
        "/auth/signup", json={"name": "A", "email": "a@b.com", "password": "password123"}
    )
    assert r.status_code == 409
    r = await client.post("/auth/signin", json={"email": "a@b.com", "password": "wrong"})
    assert r.status_code == 401

    # refresh rotates
    r = await client.post("/auth/refresh", json={"refresh_token": tok["refresh_token"]})
    assert r.status_code == 200
    r2 = await client.post("/auth/refresh", json={"refresh_token": tok["refresh_token"]})
    assert r2.status_code == 401

    # signout revokes
    new = r.json()
    await client.post("/auth/signout", json={"refresh_token": new["refresh_token"]})
    r = await client.post("/auth/refresh", json={"refresh_token": new["refresh_token"]})
    assert r.status_code == 401


async def test_verify_and_reset(client):
    r = await client.post(
        "/auth/signup", json={"name": "A", "email": "x@y.com", "password": "password123"}
    )
    r = await client.post("/auth/verify-email", json={"token": r.json()["dev_verify_token"]})
    assert r.status_code == 200
    r = await client.post("/auth/forgot-password", json={"email": "x@y.com"})
    r = await client.post(
        "/auth/reset-password",
        json={"token": r.json()["dev_reset_token"], "password": "newpassword1"},
    )
    assert r.status_code == 200
    r = await client.post("/auth/signin", json={"email": "x@y.com", "password": "newpassword1"})
    assert r.status_code == 200


async def test_schedule_and_roles(client):
    tok = await _signup_signin(client)
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    sessions = (await client.get("/sessions", headers=h)).json()
    assert len(sessions) >= 5
    sid = sessions[0]["id"]
    assert (await client.put(f"/me/schedule/{sid}", headers=h)).status_code == 204
    mine = (await client.get("/me/schedule", headers=h)).json()
    assert [m["id"] for m in mine] == [sid] and mine[0]["saved"]
    await client.delete(f"/me/schedule/{sid}", headers=h)
    assert (await client.get("/me/schedule", headers=h)).json() == []
    # attendee cannot use admin endpoints
    assert (await client.get("/admin/users", headers=h)).status_code == 403
    assert (await client.get("/speakers")).status_code == 200
