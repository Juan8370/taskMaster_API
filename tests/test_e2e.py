import uuid
import pytest
from datetime import datetime, timedelta, UTC
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.task import Task
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES


def _cleanup_user(email: str):
    """Utility function to clean up test users and their tasks"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            # cascade delete tasks if any
            db.query(Task).filter(Task.user_email == email).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()

# Recreate all tables for each test
@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client():
    return TestClient(app)

class TestE2E:
    def test_complete_user_journey(self, client: TestClient, db: Session):
        # 1. Registro de usuario
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "SecurePass123!"
        
        # Validar que el email es requerido
        r = client.post("/auth/register", json={"password": password})
        assert r.status_code == 422
        
        # Registrar usuario correctamente
        r = client.post("/auth/register", json={
            "email": email,
            "password": password
        })
        assert r.status_code == 200
        user_data = r.json()
        assert user_data["email"] == email
        assert "id" in user_data
        
        # Verificar que no se puede registrar el mismo email
        r = client.post("/auth/register", json={
            "email": email,
            "password": "OtherPass123!"
        })
        assert r.status_code == 400
        assert "exists" in r.json()["detail"].lower()

        # 2. Login y manejo de tokens
        # Intento con contraseña incorrecta
        r = client.post("/auth/login", json={
            "email": email,
            "password": "WrongPass123!"
        })
        assert r.status_code == 401
        
        # Login exitoso
        r = client.post("/auth/login", json={
            "email": email,
            "password": password
        })
        assert r.status_code == 200
        token = r.json()["token"]
        
        # 3. Operaciones con tareas
        # Crear tarea sin token
        r = client.post("/tasks/", json={"title": "Test Task"})
        assert r.status_code == 422  # o 401 dependiendo de tu implementación
        
        # Crear tarea con token inválido
        r = client.post("/tasks/?token=invalid", json={"title": "Test Task"})
        assert r.status_code == 401
        
        # Crear tarea exitosamente
        task_title = "Mi primera tarea"
        r = client.post(f"/tasks/?token={token}", json={"title": task_title})
        assert r.status_code == 200
        task_data = r.json()
        assert task_data["title"] == task_title
        task_id = task_data["id"]
        
        # Verificar que la tarea aparece en el listado
        r = client.get(f"/tasks/?token={token}")
        assert r.status_code == 200
        tasks = r.json()
        assert len(tasks) == 1
        assert tasks[0]["id"] == task_id
        assert tasks[0]["title"] == task_title

        # 4. Prueba de permisos y aislamiento
        # Crear otro usuario
        other_email = f"other_{uuid.uuid4().hex[:8]}@example.com"
        r = client.post("/auth/register", json={
            "email": other_email,
            "password": "OtherPass123!"
        })
        assert r.status_code == 200
        
        # Login con el otro usuario
        r = client.post("/auth/login", json={
            "email": other_email,
            "password": "OtherPass123!"
        })
        other_token = r.json()["token"]
        
        # Verificar que el otro usuario no ve las tareas del primero
        r = client.get(f"/tasks/?token={other_token}")
        assert r.status_code == 200
        assert len(r.json()) == 0
        
        # Verificar que no puede borrar la tarea del primer usuario
        r = client.delete(f"/tasks/{task_id}?token={other_token}")
        assert r.status_code == 403
        
        # 5. Limpieza y verificación final
        # El primer usuario borra su tarea
        r = client.delete(f"/tasks/{task_id}?token={token}")
        assert r.status_code == 200
        
        # Verificar que la tarea fue eliminada
        r = client.get(f"/tasks/?token={token}")
        assert r.status_code == 200
        assert len(r.json()) == 0

    def test_input_validation_and_limits(self, client: TestClient):
        """Prueba límites y validaciones de entrada"""
        # Registro con contraseña demasiado larga (>72 bytes)
        r = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "a" * 100
        })
        assert r.status_code in (400, 422)
        assert "too long" in r.text.lower() or "72" in r.text

        # Email inválido
        r = client.post("/auth/register", json={
            "email": "not_an_email",
            "password": "Pass123!"
        })
        assert r.status_code == 422

        # Tarea sin título
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        r = client.post("/auth/register", json={
            "email": email,
            "password": "Pass123!"
        })
        assert r.status_code == 200
        
        r = client.post("/auth/login", json={
            "email": email,
            "password": "Pass123!"
        })
        token = r.json()["token"]
        
        r = client.post(f"/tasks/?token={token}", json={})
        assert r.status_code == 422

        # Título vacío
        r = client.post(f"/tasks/?token={token}", json={"title": ""})
        assert r.status_code == 422

        # Cleanup
        _cleanup_user(email)

    def test_token_expiration(self, client: TestClient, monkeypatch):
        """Prueba expiración de tokens"""
        # Guardar valor original
        original_expire = ACCESS_TOKEN_EXPIRE_MINUTES
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        try:
            # Configurar token para que expire en 1 segundo
            import app.config
            app.config.ACCESS_TOKEN_EXPIRE_MINUTES = 1/60  # 1 segundo
            
            # Registrar y hacer login
            r = client.post("/auth/register", json={
                "email": email,
                "password": "Pass123!"
            })
            assert r.status_code == 200

            r = client.post("/auth/login", json={
                "email": email,
                "password": "Pass123!"
            })
            token = r.json()["token"]

            # Crear tarea con token válido
            r = client.post(f"/tasks/?token={token}", json={"title": "Test Task"})
            assert r.status_code == 200

            # Esperar a que el token expire
            import time
            time.sleep(2)  # 2 segundos > 1 segundo de expiración
            
            # Intentar usar el token expirado
            r = client.post(f"/tasks/?token={token}", json={"title": "Another Task"})
            assert r.status_code == 401
            assert "expired" in r.json()["detail"].lower()
        finally:
            # Restaurar valor original y limpiar
            app.config.ACCESS_TOKEN_EXPIRE_MINUTES = original_expire
            _cleanup_user(email)

    def test_concurrent_operations(self, client: TestClient):
        """Prueba operaciones concurrentes básicas"""
        import concurrent.futures
        
        # Crear usuario para las pruebas
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        r = client.post("/auth/register", json={
            "email": email,
            "password": "Pass123!"
        })
        assert r.status_code == 200
        
        r = client.post("/auth/login", json={
            "email": email,
            "password": "Pass123!"
        })
        token = r.json()["token"]
        
        try:
            # Crear múltiples tareas concurrentemente
            def create_task(i):
                return client.post(
                    f"/tasks/?token={token}",
                    json={"title": f"Concurrent Task {i}"}
                )
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(create_task, i) for i in range(5)]
                responses = [f.result() for f in futures]
            
            # Verificar que todas las tareas se crearon
            assert all(r.status_code == 200 for r in responses)
            
            # Verificar el número total de tareas
            r = client.get(f"/tasks/?token={token}")
            assert r.status_code == 200
            tasks = r.json()
            assert len(tasks) == 5

            # Verificar que todas tienen títulos únicos
            titles = {task["title"] for task in tasks}
            assert len(titles) == 5  # No duplicados

            # Verificar que todos pertenecen al usuario correcto
            for task in tasks:
                assert task["user_email"] == email
        finally:
            # Cleanup
            _cleanup_user(email)