import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, get_db
from app.database import Base
from app.redis_client import redis_client

from sqlalchemy.pool import StaticPool

# 1. Configuración de Base de Datos temporal en memoria (SQLite) para aislamiento
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 2. Fixture para preparar la Base de Datos antes de cada prueba
@pytest.fixture(name="db_session")
def fixture_db_session():
    # Crear la estructura de tablas de SQLAlchemy en la base temporal
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Eliminar las tablas al terminar cada test para asegurar limpieza
        Base.metadata.drop_all(bind=engine)


# 3. Fixture para simular el cliente de peticiones de FastAPI (TestClient)
@pytest.fixture(name="client")
def fixture_client(db_session):
    # Sobreescribimos la dependencia 'get_db' para que apunte a la base de pruebas (SQLite)
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    # Limpiar las inyecciones de dependencias al terminar la prueba
    app.dependency_overrides.clear()


# 4. Fixture para simular (mockear) Redis
@pytest.fixture(name="mock_redis", autouse=True)
def fixture_mock_redis():
    # Guardamos la referencia al método rpush original
    original_rpush = redis_client.rpush
    # Reemplazamos rpush con un simulador (MagicMock) que no hace conexión real
    redis_client.rpush = MagicMock(return_value=1)
    yield redis_client
    # Restauramos el método original al terminar
    redis_client.rpush = original_rpush


# === PRUEBAS UNITARIAS E INTEGRACIÓN ===


def test_create_task(client, mock_redis):
    """Prueba que el endpoint POST /tasks crea la tarea y la encola en Redis"""
    payload = {"name": "Prueba de Integracion", "payload": {"datos": 123}}

    # Simular la llamada HTTP POST
    response = client.post("/tasks", json=payload)

    # Validaciones HTTP
    assert response.status_code == 202
    data = response.json()
    assert data["name"] == "Prueba de Integracion"
    assert data["payload"] == {"datos": 123}
    assert "id" in data
    assert data["status"] == "pending"

    # Validar que llamamos a Redis para encolar el ID correcto
    mock_redis.rpush.assert_called_once()
    # call_args es una tupla: (args, kwargs)
    args, _ = mock_redis.rpush.call_args
    assert args[0] == "task_queue"
    assert args[1] == data["id"]


def test_get_task_success(client):
    """Prueba que el endpoint GET /tasks/{id} retorna la tarea existente"""
    # 1. Crear una tarea de prueba
    post_response = client.post(
        "/tasks", json={"name": "Tarea para consultar", "payload": None}
    )
    task_id = post_response.json()["id"]

    # 2. Consultar la tarea recién creada
    get_response = client.get(f"/tasks/{task_id}")

    assert get_response.status_code == 200
    data = get_response.json()
    assert data["id"] == task_id
    assert data["name"] == "Tarea para consultar"
    assert data["status"] == "pending"


def test_get_task_not_found(client):
    """Prueba que el endpoint GET /tasks/{id} lanza 404 si la tarea no existe"""
    non_existent_uuid = "00000000-0000-0000-0000-000000000000"

    # Consultar ID inexistente
    response = client.get(f"/tasks/{non_existent_uuid}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Tarea no encontrada"
