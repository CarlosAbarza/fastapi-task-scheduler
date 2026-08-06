# app/main.py
import logging
from contextlib import asynccontextmanager
from uuid import UUID
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from prometheus_fastapi_instrumentator import Instrumentator

from app.database import engine, Base, SessionLocal
from app.models import Task
from app.schemas import TaskCreate, TaskResponse
from app.redis_client import redis_client

# Configuración básica de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("api")


# 1. Definir el ciclo de vida (lifespan) para inicializaciones al arrancar
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crear las tablas en la base de datos (PostgreSQL) si no existen
    Base.metadata.create_all(bind=engine)
    yield


# 2. Inicializar FastAPI vinculando el lifespan
app = FastAPI(
    title="FastAPI Task Scheduler",
    description="API para encolamiento asíncrono de tareas pesadas",
    version="1.0.0",
    lifespan=lifespan,
)

# Instrumentar con Prometheus exponiendo la ruta /metrics
Instrumentator().instrument(app).expose(app)


# 3. Dependencia para obtener la sesión de la Base de Datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 4. Endpoint para crear una tarea (POST)
@app.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Crear y encolar una nueva tarea",
)
def create_task(task_data: TaskCreate, db: Session = Depends(get_db)):
    # A. Crear el registro en la base de datos (estado inicial: pending)
    nueva_tarea = Task(name=task_data.name, payload=task_data.payload, status="pending")
    db.add(nueva_tarea)
    db.commit()
    db.refresh(nueva_tarea)  # Esto actualiza el objeto con el ID generado por la BD

    logger.info(f"Tarea registrada en DB con ID: {nueva_tarea.id}")

    # B. Encolar el ID de la tarea en Redis
    # Convertimos el ID a string para guardarlo en la cola de Redis
    redis_client.rpush("task_queue", str(nueva_tarea.id))
    logger.info(f"Tarea encolada en Redis con ID: {nueva_tarea.id}")

    # C. Retornar la información de la tarea (Pydantic la validará automáticamente)
    return nueva_tarea


# 5. Endpoint para consultar el estado de una tarea (GET)
@app.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Consultar el estado de una tarea",
)
def get_task(task_id: UUID, db: Session = Depends(get_db)):
    logger.info(f"Consultando estado de tarea con ID: {task_id}")
    # Buscar la tarea en la base de datos
    tarea = db.query(Task).filter(Task.id == task_id).first()

    # Si no existe, lanzar error 404
    if not tarea:
        logger.warning(
            f"Intento de consulta fallido: Tarea con ID {task_id} no encontrada"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada"
        )

    return tarea
