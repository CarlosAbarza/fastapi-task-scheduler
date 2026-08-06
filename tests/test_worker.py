import pytest
import uuid
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Task
from worker.main import process_task

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
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


# 3. Pruebas Unitarias para el Worker


@patch("worker.main.SessionLocal")
def test_process_task_success(mock_session_local, db_session):
    """Prueba que el worker procese la tarea correctamente pasando de pending a completed"""
    # Hacer que SessionLocal() retorne nuestra base SQLite en memoria
    mock_session_local.return_value = db_session

    # Crear una tarea pendiente en la BD de pruebas
    task_id = uuid.uuid4()
    task = Task(
        id=task_id,
        name="Prueba de Worker Exitosa",
        payload={"valor": 42},
        status="pending",
    )
    db_session.add(task)
    db_session.commit()

    # Mockear el delay para ejecución instantánea
    with patch("worker.main.time.sleep") as mock_sleep:
        process_task(task_id)
        mock_sleep.assert_called_once_with(5)

    # Refrescar y validar que el estado cambió a 'completed'
    db_session.expire_all()
    updated_task = db_session.query(Task).filter(Task.id == task_id).first()
    assert updated_task.status == "completed"


@patch("worker.main.SessionLocal")
def test_process_task_failed(mock_session_local, db_session):
    """Prueba que si ocurre una excepción, el worker haga rollback y marque la tarea como failed"""
    mock_session_local.return_value = db_session

    # Crear tarea pendiente
    task_id = uuid.uuid4()
    task = Task(
        id=task_id, name="Prueba de Worker Fallida", payload=None, status="pending"
    )
    db_session.add(task)
    db_session.commit()

    # Simular una excepción en time.sleep para gatillar el bloque except en process_task
    with patch(
        "worker.main.time.sleep", side_effect=Exception("Simulated processing crash")
    ):
        process_task(task_id)

    # Refrescar y validar que el estado cambió a 'failed'
    db_session.expire_all()
    updated_task = db_session.query(Task).filter(Task.id == task_id).first()
    assert updated_task.status == "failed"


@patch("worker.main.SessionLocal")
def test_process_task_not_found(mock_session_local, db_session):
    """Prueba que el worker maneje correctamente el caso cuando la tarea no existe en base de datos"""
    mock_session_local.return_value = db_session

    # UUID aleatorio que no está en la BD
    non_existent_id = uuid.uuid4()

    # Esto no debería lanzar errores, simplemente registrar un warning y retornar
    process_task(non_existent_id)
