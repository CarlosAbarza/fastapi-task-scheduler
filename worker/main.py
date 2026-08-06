# worker/main.py
import time
import logging
import uuid

from app.database import SessionLocal
from app.models import Task
from app.redis_client import redis_client

# Configuración básica de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("worker")


def process_task(task_id: uuid.UUID):
    # Crear una nueva sesión de Base de Datos para el Worker
    db = SessionLocal()
    try:
        # 1. Buscar la tarea
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"Tarea {task_id} no encontrada en la Base de Datos.")
            return

        # 2. Cambiar estado a "processing"
        logger.info(f"Iniciando procesamiento de tarea {task_id}: {task.name}")
        task.status = "processing"
        db.commit()

        # 3. Simular el trabajo pesado (cálculo o retraso)
        # Aquí puedes poner la lógica real en el futuro. Por ahora simularemos 5 segundos.
        time.sleep(5)

        # 4. Cambiar estado a "completed"
        task.status = "completed"
        db.commit()
        logger.info(f"Tarea {task_id} completada exitosamente.")

    except Exception:
        logger.exception(f"Error procesando tarea {task_id}")
        # Si algo falla, marcamos la tarea como "failed" en la BD
        db.rollback()  # Deshace cualquier cambio a medio camino en la transacción

        # Intentamos actualizar el estado a fallido
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = "failed"
                db.commit()
        except Exception as db_err:
            logger.critical(f"Error crítico al guardar estado fallido: {str(db_err)}")

    finally:
        # Cerramos siempre la sesión del worker al terminar
        db.close()


def main():
    logger.info("Iniciando Worker. Escuchando cola 'task_queue'...")

    while True:
        try:
            # BRPOP bloqueará el hilo de ejecución hasta que llegue un elemento a Redis.
            # El timeout de 5 indica que si no hay nada en 5 segundos, retorna None y vuelve a intentar.
            # Esto mantiene la conexión viva y nos permite pausar el loop de manera controlada.
            result = redis_client.brpop("task_queue", timeout=5)

            if result:
                # brpop retorna una tupla: (nombre_de_la_cola, valor)
                # ej: ("task_queue", "d3b07384-d113-4956-a5db-2554dec4d3b1")
                cola_nombre, task_id_str = result
                task_id = uuid.UUID(task_id_str)

                # Procesar la tarea
                process_task(task_id)

        except Exception as e:
            logger.error(f"Error en el bucle principal: {str(e)}")
            time.sleep(
                2
            )  # Pausa de seguridad antes de reintentar si se cae la conexión de Redis


if __name__ == "__main__":
    main()
