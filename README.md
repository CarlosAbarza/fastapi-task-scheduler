# 🚀 FastAPI Task Scheduler

API REST asíncrona de alto rendimiento desarrollada en **FastAPI** para el encolamiento de tareas pesadas, con procesamiento en background mediante un **Worker independiente**, persistencia en **PostgreSQL**, cola de mensajería en **Redis**, monitoreo con **Prometheus + Grafana**, y validaciones automatizadas mediante un pipeline de **CI (GitHub Actions)**.

---

## 🗺️ Diagrama de Arquitectura

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart TB

    %% ===================== ACTORES / CLIENTE =====================
    Cliente["<<actor>>\nCliente\n(Navegador / Postman)"]

    %% ===================== CAPA DE APLICACIÓN =====================
    subgraph APP["Capa de Aplicación"]
        FastAPI["<<component>>\nFastAPI Web API\nmain.py\n:8000"]
        Worker["<<component>>\nPython Worker\nmain.py\n(proceso independiente)"]
    end

    %% ===================== CAPA DE DATOS =====================
    subgraph DATA["Capa de Datos"]
        Postgres[("<<database>>\nPostgreSQL DB\nmodels.py\n:5432")]
        Redis[("<<cache>>\nRedis Cache\nredis_client.py\n:6379")]
    end

    %% ===================== CAPA DE MONITOREO =====================
    subgraph MON["Capa de Monitoreo"]
        Prometheus["<<component>>\nPrometheus Server\n:9090"]
        Grafana["<<component>>\nGrafana Server\n:3000"]
    end

    %% ===================== CONEXIONES =====================
    Cliente -- "1: HTTP POST /tasks" --> FastAPI
    FastAPI -. "1.1: HTTP 202 Accepted\n(Retorna UUID)" .-> Cliente
    Cliente -- "1.2: HTTP GET /tasks/{id}" --> FastAPI
    
    FastAPI -- "2: TCP/SQL\nINSERT (estado=pending)" --> Postgres
    FastAPI -- "3: TCP/Redis\nRPUSH task_queue (UUID)" --> Redis
    
    Worker -- "4: TCP/Redis (BRPOP)\nPop UUID de la cola" --> Redis
    Worker -- "5: TCP/SQL\nUPDATE (processing)" --> Postgres
    Worker -- "5.1: Simular ejecución\n(5s sleep)" --> Worker
    Worker -- "5.2: TCP/SQL\nUPDATE (completed/failed)" --> Postgres
    
    Prometheus -- "6: HTTP (Pull)\nGET /metrics" --> FastAPI
    Grafana -- "7: HTTP/PromQL\nConsulta histórico" --> Prometheus
    Cliente -- "8: HTTP\nDashboard :3000" --> Grafana
    Cliente -- "9: HTTP (opcional)\nUI nativa :9090" --> Prometheus

    %% ===================== ESTILOS =====================
    classDef actor fill:#fef3c7,stroke:#b45309,stroke-width:1px,color:#000
    classDef app fill:#dbeafe,stroke:#1d4ed8,stroke-width:1px,color:#000
    classDef data fill:#dcfce7,stroke:#15803d,stroke-width:1px,color:#000
    classDef mon fill:#fce7f3,stroke:#a21caf,stroke-width:1px,color:#000

    class Cliente actor
    class FastAPI,Worker app
    class Postgres,Redis data
    class Prometheus,Grafana mon
```

---

## 💡 Justificación de Decisiones de Arquitectura

### 1. Desacoplamiento de la API y el Worker
Separar el servidor web de la API del proceso ejecutor de tareas (**Worker**) evita que las tareas pesadas (como cálculos matemáticos complejos, procesamiento de datos o peticiones externas de larga duración) bloqueen el ciclo de eventos (event loop) de FastAPI. Esto permite que la API siga recibiendo y respondiendo miles de peticiones por segundo con latencias mínimas.

### 2. Uso de `BRPOP` en Redis en lugar de Polling Activo
En [`worker/main.py`](worker/main.py), el Worker utiliza la operación bloqueante `brpop` de Redis con un tiempo de espera (`timeout=5`).
* **¿Por qué?** El *polling* activo (preguntar a Redis cada segundo mediante un loop continuo) consume recursos de CPU y genera tráfico de red innecesario.
* **Beneficio:** `BRPOP` suspende el hilo de ejecución de Python hasta que entra un elemento en la cola. Si la cola está vacía, el consumo de CPU del Worker es del 0%.

### 3. UUID como Clave Primaria en las Tareas
Las tareas se identifican mediante un identificador universal único (UUIDv4) en lugar de un entero secuencial (`1, 2, 3...`).
* **Seguridad (IDOR):** Evita que usuarios maliciosos puedan adivinar IDs de tareas ajenas incrementando secuencialmente el parámetro en el endpoint `GET /tasks/{id}`.
* **Escalabilidad:** Los UUID se pueden generar del lado del cliente o de la aplicación de forma distribuida sin riesgo de colisión y sin necesidad de sincronización centralizada en la base de datos.

### 4. Monitoreo mediante Modelo Pull (Prometheus)
FastAPI está instrumentado para exponer sus métricas operativas (latencia por percentiles, throughput de llamadas, códigos de estado) en `/metrics`. Prometheus consulta activamente este endpoint. Esto aísla a la API: si el servidor de monitoreo se cae, la API sigue funcionando al 100% de su capacidad sin bloquearse por intentar enviar logs o métricas.

---

## 🛠️ Comandos Rápidos (`Makefile`)

El proyecto cuenta con un [`Makefile`](Makefile) para simplificar la administración del entorno.

| Comando | Acción |
| :--- | :--- |
| `make run` | Construye las imágenes y levanta todo el entorno Docker (API, Worker, DB, Redis, Prometheus, Grafana) en segundo plano. |
| `make stop` | Apaga y detiene todos los contenedores de Docker sin perder los datos persistidos. |
| `make restart` | Realiza un reinicio rápido del entorno Docker. |
| `make logs` | Muestra la salida de logs en tiempo real de todos los contenedores. |
| `make test` | Ejecuta de forma aislada las pruebas unitarias e integración de la API usando `pytest`. |
| `make lint` | Ejecuta las validaciones de estilo de código (`black` y `flake8`). |
| `make format` | Formatea automáticamente el código del proyecto siguiendo el estándar PEP 8. |
| `make clean` | Apaga todos los contenedores y **elimina permanentemente** los volúmenes de datos de PostgreSQL y Grafana. |

---

## 🚀 Guía de Inicio Rápido

### Requisitos Previos
* **Docker** y **Docker Compose** instalados en el sistema.
* **Python 3.10+** (para desarrollo y pruebas locales).

### Paso 1: Configurar el Entorno Virtual (Local)
Para desarrollo, autocompletado y ejecución de pruebas locales:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Paso 2: Levantar el Entorno de Producción
Para iniciar todos los servicios del ecosistema:
```bash
make run
```

### Paso 3: Probar Endpoints
Puedes interactuar con la API a través de la documentación interactiva autogenerada por FastAPI (Swagger UI):
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

* **Crear una tarea:** `POST /tasks` con JSON:
  ```json
  {
    "name": "Procesamiento de Tesis",
    "payload": {"simulacion": "iteracion_100"}
  }
  ```
  *Retorna `202 Accepted` y el `id` (UUID) de la tarea.*
* **Consultar el estado:** `GET /tasks/{id}` para verificar si pasó de `pending` -> `processing` -> `completed` o `failed`.

### Paso 4: Monitoreo y Puertos Locales
* **API FastAPI:** [http://localhost:8000](http://localhost:8000) (métricas crudas en `/metrics`).
* **Prometheus:** [http://localhost:9090](http://localhost:9090) (explorador de métricas).
* **Grafana:** [http://localhost:3000](http://localhost:3000) (visualizador gráfico).
  * *Credenciales por defecto:* Usuario: `admin` \| Contraseña: `admin`
