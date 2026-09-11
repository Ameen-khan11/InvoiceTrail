from unittest.mock import patch, MagicMock
import json
import urllib.error
from app.models import User
from app.extensions import db


def test_google_auth_demo_signup(client):
    res = client.post("/api/auth/google", json={
        "demo_email": "googlenew@example.com",
        "demo_name": "Google User",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert "access_token" in data
    assert data["user"]["email"] == "googlenew@example.com"
    assert data["user"]["name"] == "Google User"
    assert data["user"]["google_connected"] is True
    assert data["user"]["has_password"] is False


def test_google_auth_demo_existing_login(client):
    client.post("/api/auth/google", json={
        "demo_email": "googleexisting@example.com",
        "demo_name": "Existing Google",
    })

    res = client.post("/api/auth/google", json={
        "demo_email": "googleexisting@example.com",
        "demo_name": "Existing Google",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "access_token" in data
    assert data["user"]["email"] == "googleexisting@example.com"


def test_google_auth_account_linking(client, create_user):
    create_user(email="preexisting@example.com", name="Original Name", password="Password123!")

    res = client.post("/api/auth/google", json={
        "demo_email": "preexisting@example.com",
        "demo_name": "Original Name",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["user"]["email"] == "preexisting@example.com"
    assert data["user"]["google_connected"] is True
    assert data["user"]["has_password"] is True


def test_google_auth_missing_credential(client):
    res = client.post("/api/auth/google", json={})
    assert res.status_code == 422
    assert res.get_json()["field"] == "credential"


def test_google_auth_invalid_token(client):
    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("url", 400, "Bad Request", {}, None)):
        res = client.post("/api/auth/google", json={"credential": "invalid-token-123"})
        assert res.status_code == 401
        assert "Invalid or expired Google credential" in res.get_json()["error"]


def test_google_auth_valid_verified_token(client):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "sub": "google-sub-123456",
        "email": "realtoken@example.com",
        "email_verified": "true",
        "name": "Verified User",
        "aud": "",
    }).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        res = client.post("/api/auth/google", json={"credential": "valid-token-xyz"})
        assert res.status_code == 201
        data = res.get_json()
        assert data["user"]["email"] == "realtoken@example.com"
        assert data["user"]["name"] == "Verified User"
        assert data["user"]["google_connected"] is True
