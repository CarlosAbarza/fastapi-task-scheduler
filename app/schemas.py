from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID


# Esquema base
class TaskBase(BaseModel):
    name: str = Field(
        ..., min_length=3, max_length=100, description="Nombre descriptivo de la tarea"
    )
    payload: Optional[Dict[str, Any]] = Field(
        default=None, description="Parámetros JSON para la tarea"
    )


# Esquema para crear una tarea
class TaskCreate(TaskBase):
    pass


# Esquema para devolver datos al usuario
class TaskResponse(TaskBase):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
