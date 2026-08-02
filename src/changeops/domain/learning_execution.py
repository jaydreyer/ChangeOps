from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator


class AssignTrainingParameters(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    worker_identifier: str
    course_identifier: str
    description: str
    due_date: date | None

    @field_validator("worker_identifier", "course_identifier", "description")
    @classmethod
    def require_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must be nonempty")
        return value
