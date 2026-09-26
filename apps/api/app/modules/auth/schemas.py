from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MeResponse(BaseModel):
    id: UUID
    email: str
    display_name: str | None = None
    created_at: datetime
