# app/redis_client.py
import os
import redis

# 1. URL de conexión a Redis (por defecto apunta a localhost)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 2. Cliente de Redis
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
