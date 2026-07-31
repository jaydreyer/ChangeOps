from sqlalchemy import func, select
from sqlalchemy.orm import Session

from changeops.db.models import (
    Organization,
    PolicyChange,
    PolicyChangeQuestion,
    TrainingRecord,
    Trip,
    Worker,
)
from changeops.db.session import SessionLocal
from changeops.services.seed_service import seed_database


def source_counts(session: Session) -> dict[str, int]:
    return {
        model.__tablename__: session.scalar(select(func.count()).select_from(model))
        for model in (
            Organization,
            PolicyChange,
            PolicyChangeQuestion,
            Worker,
            Trip,
            TrainingRecord,
        )
    }


def test_seed_is_repeatable_without_duplicates() -> None:
    with SessionLocal.begin() as session:
        before = source_counts(session)
        seed_database(session)
        seed_database(session)

    with SessionLocal() as session:
        after = source_counts(session)

    assert (
        before
        == after
        == {
            "organizations": 1,
            "policy_changes": 1,
            "policy_change_questions": 8,
            "workers": 6,
            "trips": 6,
            "training_records": 6,
        }
    )
