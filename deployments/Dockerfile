# deployments/Dockerfile

# ================= Stage 1: Build stage =================
FROM python:3.11-slim AS builder

WORKDIR /build

# Instalar dependencias del sistema requeridas para compilar librerías de Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Crear y activar un entorno virtual
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

# Instalar dependencias en el virtualenv
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ================= Stage 2: Runner stage =================
FROM python:3.11-slim AS runner

# Configurar variables de entorno críticas
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/code
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /code

# Copiar el entorno virtual con todas las dependencias instaladas
COPY --from=builder /opt/venv /opt/venv

# Crear un usuario de sistema sin privilegios y su grupo de seguridad
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

# Copiar el código del proyecto y asignar la propiedad al usuario no privilegiado
COPY --chown=appuser:appgroup ./app /code/app
COPY --chown=appuser:appgroup ./worker /code/worker

# Cambiar el usuario de ejecución al no privilegiado
USER appuser

EXPOSE 8000

# Comando por defecto para iniciar la API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
