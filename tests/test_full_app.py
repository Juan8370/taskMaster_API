import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.task import Task

client = TestClient(app)


def _cleanup_user(email: str):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        if u:
            # cascade delete tasks if any
            db.query(Task).filter(Task.user_email == email).delete()
            db.delete(u)
            db.commit()
    finally:
        db.close()


def test_full_app_flow_create_list_delete_tasks():
    # ensure tables exist for this test run
    Base.metadata.create_all(bind=engine)
    # create primary user
    email = f"test_{uuid.uuid4().hex}@example.com"
    password = "strong_password"

    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200

    # login
    r2 = client.post("/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200
    token = r2.json()["token"]

    # create two tasks
    t1 = client.post(f"/tasks/?token={token}", json={"title": "task one"})
    assert t1.status_code == 200
    id1 = t1.json()["id"]

    t2 = client.post(f"/tasks/?token={token}", json={"title": "task two"})
    assert t2.status_code == 200
    id2 = t2.json()["id"]

    # list tasks
    l = client.get(f"/tasks/?token={token}")
    assert l.status_code == 200
    titles = {t["title"] for t in l.json()}
    assert titles >= {"task one", "task two"}

    # delete first task
    d = client.delete(f"/tasks/{id1}?token={token}")
    assert d.status_code == 200

    # list again
    l2 = client.get(f"/tasks/?token={token}")
    assert l2.status_code == 200
    titles2 = [t["title"] for t in l2.json()]
    assert "task one" not in titles2
    assert "task two" in titles2

    # create second user and ensure they cannot delete other's task
    other = f"other_{uuid.uuid4().hex}@example.com"
    r3 = client.post("/auth/register", json={"email": other, "password": "pw"})
    assert r3.status_code == 200
    r4 = client.post("/auth/login", json={"email": other, "password": "pw"})
    token_other = r4.json()["token"]

    # attempt to delete remaining task as other user
    d2 = client.delete(f"/tasks/{id2}?token={token_other}")
    assert d2.status_code == 403

    # cleanup
    _cleanup_user(email)
    _cleanup_user(other)
    # tear down tables to keep test isolation
    Base.metadata.drop_all(bind=engine)
