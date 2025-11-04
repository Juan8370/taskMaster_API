import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User

client = TestClient(app)


def _cleanup_user(email: str):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        if u:
            db.delete(u)
            db.commit()
    finally:
        db.close()


def test_register_and_login_success():
    email = f"test_{uuid.uuid4().hex}@example.com"
    password = "correct_horse_battery_staple"

    # register
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == email
    assert "id" in data

    # login
    r2 = client.post("/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200
    data2 = r2.json()
    assert "token" in data2

    # cleanup
    _cleanup_user(email)


def test_register_password_too_long():
    email = f"test_{uuid.uuid4().hex}@example.com"
    password = "a" * 100  # 100 bytes > bcrypt 72

    r = client.post("/auth/register", json={"email": email, "password": password})
    # could be 422 (pydantic validator) or 400 (router mapped), accept either
    assert r.status_code in (422, 400)
    text = r.text.lower()
    assert "password" in text and ("too long" in text or "72" in text)


def test_login_with_too_long_password_fails():
    # create a real user
    email = f"test_{uuid.uuid4().hex}@example.com"
    password = "safepassword"
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200

    # attempt login with overly long password
    bad = "a" * 100
    r2 = client.post("/auth/login", json={"email": email, "password": bad})
    # could be validation 422 or authentication 401; accept either
    assert r2.status_code in (422, 401)

    # cleanup
    _cleanup_user(email)
