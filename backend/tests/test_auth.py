def test_signup_success(client):
    res = client.post("/api/auth/signup", json={
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "Password123!",
        "business_name": "Jane Studios",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert "access_token" in data
    assert data["user"]["email"] == "jane@example.com"
    assert data["user"]["name"] == "Jane Doe"
    assert data["user"]["business_name"] == "Jane Studios"
    assert "password_hash" not in data["user"]


def test_signup_validation(client):
    # Missing required field
    res = client.post("/api/auth/signup", json={"email": "incomplete@example.com"})
    assert res.status_code == 422

    # Invalid email format
    res = client.post("/api/auth/signup", json={
        "name": "Bob",
        "email": "not-an-email",
        "password": "Password123!",
    })
    assert res.status_code == 422
    assert res.get_json()["field"] == "email"

    # Password too short (<8 chars)
    res = client.post("/api/auth/signup", json={
        "name": "Bob",
        "email": "bob@example.com",
        "password": "short",
    })
    assert res.status_code == 422
    assert res.get_json()["field"] == "password"


def test_signup_duplicate_email(client):
    payload = {
        "name": "Alice",
        "email": "alice@example.com",
        "password": "Password123!",
    }
    res1 = client.post("/api/auth/signup", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/auth/signup", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.get_json()["error"]


def test_login_success(client, create_user):
    create_user(email="login@example.com", password="SecretPassword123!")

    res = client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "SecretPassword123!",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "access_token" in data
    assert data["user"]["email"] == "login@example.com"


def test_login_invalid_credentials(client, create_user):
    create_user(email="user@example.com", password="CorrectPassword123!")

    # Wrong password
    res1 = client.post("/api/auth/login", json={
        "email": "user@example.com",
        "password": "WrongPassword123!",
    })
    assert res1.status_code == 401
    assert res1.get_json()["error"] == "Invalid email or password"

    # Non-existent user (identical message)
    res2 = client.post("/api/auth/login", json={
        "email": "ghost@example.com",
        "password": "SomePassword123!",
    })
    assert res2.status_code == 401
    assert res2.get_json()["error"] == "Invalid email or password"


def test_me_endpoint(client, create_user):
    user, headers = create_user(email="me@example.com", name="Me User")

    # With auth headers
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.get_json()["email"] == "me@example.com"

    # Without auth headers
    res_no_auth = client.get("/api/auth/me")
    assert res_no_auth.status_code == 401
