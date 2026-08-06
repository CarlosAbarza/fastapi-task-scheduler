# deployments/Dockerfile
# 1. Usar una imagen base oficial de Python liviana (slim)
FROM python:3.11-slim

# 2. Configurar variables de entorno críticas de Python para contenedores
# Evita que Python escriba archivos .pyc (caché) en el contenedor
ENV PYTHONDONTWRITEBYTECODE=1
# Evita que Python guarde en buffer los logs; se imprimen directo en la consola en tiempo real
ENV PYTHONUNBUFFERED=1

# 3. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /code

# 4. Instalar las dependencias del sistema necesarias
# gcc y python3-dev a veces son requeridos para compilar ciertas librerías de Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 5. Copiar requirements.txt e instalar dependencias de Python
# Hacemos esto ANTES de copiar el resto del código para aprovechar la caché de Docker
COPY requirements.txt /code/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 6. Copiar el código del proyecto al directorio de trabajo del contenedor
COPY ./app /code/app
COPY ./worker /code/worker

# 7. Exponer el puerto por defecto de la API
EXPOSE 8000

# 8. Comando por defecto (en este caso levantará la API de FastAPI)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
