from __future__ import annotations

from app.schemas.base import CamelModel


class FlowPointSchema(CamelModel):
    time: str
    activity_score: float


class FlowStateSchema(CamelModel):
    flow_percent: int
    change_percent: int
    window_label: str
    series: list[FlowPointSchema]
