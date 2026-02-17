from datetime import datetime

from app.models.task import TaskSchema


def test_task_schema_camelcase_and_population():
    # Default values and alias generation
    t = TaskSchema(name="Sample Task")
    dumped = t.model_dump(by_alias=True)
    assert "isCompleted" in dumped

    # Populate by alias (camelCase) should map to snake_case attribute
    t2 = TaskSchema(**{"isCompleted": True, "name": "Alias Task"})
    assert t2.is_completed is True
