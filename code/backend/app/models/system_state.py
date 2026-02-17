from pydantic import BaseModel
from datetime import datetime

class SystemStateSchema(BaseModel):
    id: str | None = None
    mode_type: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    requires_recovery: bool | None = None
    description: str | None = None

    model_config = {"alias_generator": lambda s: ''.join([s.split('_')[0]] + [w.capitalize() for w in s.split('_')[1:]]), "populate_by_name": True}
