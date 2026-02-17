from pydantic import BaseModel
from datetime import datetime

class ManualReportSchema(BaseModel):
    id: str | None = None
    title: str
    body: str
    word_count: int | None = None
    associated_task_ids: list[str] | None = None
    created_at: datetime | None = None

    model_config = {"alias_generator": lambda s: ''.join([s.split('_')[0]] + [w.capitalize() for w in s.split('_')[1:]]), "populate_by_name": True}
