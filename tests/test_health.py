"""Smoke tests - verify the app starts and basic endpoints respond."""

import httpx


async def test_root_returns_200(client: httpx.AsyncClient):
    """GET / should return 200 with HTML content."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_root_contains_scholaverse(client: httpx.AsyncClient):
    """GET / should mention Scholaverse somewhere in the body."""
    response = await client.get("/")
    assert "Scholaverse" in response.text


async def test_unregistered_user_redirects_to_register(
    client: httpx.AsyncClient, auth_headers: dict
):
    """GET / with auth header but no registered user should redirect to /register."""
    response = await client.get("/", headers=auth_headers, follow_redirects=False)
    assert response.status_code == 302
    assert "/register" in response.headers["location"]


async def test_register_page_shows_email(
    client: httpx.AsyncClient, auth_headers: dict
):
    """GET /register should show the authenticated email."""
    response = await client.get("/register", headers=auth_headers)
    assert response.status_code == 200
    assert "test@example.com" in response.text
