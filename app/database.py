import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# URL de la BD con validación
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Permitir fallback a SQLite en memoria únicamente si se ejecutan pruebas automatizadas (pytest)
    if "pytest" in sys.modules or os.getenv("TESTING") == "1":
        DATABASE_URL = "sqlite:///:memory:"
    else:
        raise ValueError(
            "La variable de entorno DATABASE_URL no está configurada. "
            "Por favor, defínela para conectar a la base de datos."
        )

# Creación del engine
engine = create_engine(DATABASE_URL)

# Creación de la sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarativa
Base = declarative_base()
