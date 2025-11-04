import sys
from pathlib import Path

# ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
email = "quick_test_user@example.com"
password = "correct_horse_battery_staple"
r = client.post("/auth/register", json={"email": email, "password": password})
print('status', r.status_code)
try:
    print('json:', r.json())
except Exception:
    print('text:', r.text)
