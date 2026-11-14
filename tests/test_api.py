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


async def test_demo_user_signs_in(client):
    r = await client.post(
        "/auth/signin", json={"email": "demo@expo-summit.dev", "password": "demo12345"}
    )
    assert r.status_code == 200


async def test_ideas_and_voting(client):
    a = await _signup_signin(client, "a@b.com")
    b = await _signup_signin(client, "b@b.com")
    ha = {"Authorization": f"Bearer {a['access_token']}"}
    hb = {"Authorization": f"Bearer {b['access_token']}"}

    # must be signed in to create; validation applies
    body = {"title": "Smart queues", "description": "Predict wait times and route visitors."}
    assert (await client.post("/ideas", json=body)).status_code == 401
    assert (
        await client.post("/ideas", json={"title": "x", "description": "y"}, headers=ha)
    ).status_code == 422
    r = await client.post("/ideas", json=body, headers=ha)
    assert r.status_code == 201
    iid = r.json()["id"]
    assert r.json()["votes"] == 0

    # one vote per user per idea
    r = await client.put(f"/ideas/{iid}/vote", headers=ha)
    assert r.json()["votes"] == 1 and r.json()["voted"]
    r = await client.put(f"/ideas/{iid}/vote", headers=ha)
    assert r.json()["votes"] == 1
    r = await client.put(f"/ideas/{iid}/vote", headers=hb)
    assert r.json()["votes"] == 2

    # ranking: most voted first, voted flag is per user
    ideas = (await client.get("/ideas", headers=hb)).json()
    assert ideas[0]["id"] == iid and ideas[0]["voted"]
    assert (await client.get("/ideas")).json()[0]["voted"] is False

    r = await client.delete(f"/ideas/{iid}/vote", headers=hb)
    assert r.json()["votes"] == 1 and not r.json()["voted"]

    # only the author (or admin) can delete
    assert (await client.delete(f"/ideas/{iid}", headers=hb)).status_code == 403
    assert (await client.delete(f"/ideas/{iid}", headers=ha)).status_code == 204
    assert (await client.get(f"/ideas/{iid}")).status_code == 404


async def test_roles(client):
    tok = await _signup_signin(client)
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    assert (await client.get("/admin/users", headers=h)).status_code == 403
