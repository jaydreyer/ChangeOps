import pytest

from changeops.services.demo_reset_service import (
    DEMO_RESET_CONFIRMATION,
    DemoResetSafetyError,
    validate_demo_reset_target,
)


def test_demo_reset_accepts_only_explicit_local_demo_database() -> None:
    validate_demo_reset_target(
        "postgresql+psycopg://changeops:changeops@db:5432/changeops",
        DEMO_RESET_CONFIRMATION,
    )


@pytest.mark.parametrize(
    ("database_url", "confirmation"),
    [
        (
            "postgresql+psycopg://changeops:changeops@db:5432/changeops",
            None,
        ),
        (
            "postgresql+psycopg://changeops:changeops@prod.example.com/changeops",
            DEMO_RESET_CONFIRMATION,
        ),
        (
            "postgresql+psycopg://changeops:changeops@db/changeops_production",
            DEMO_RESET_CONFIRMATION,
        ),
    ],
)
def test_demo_reset_rejects_unsafe_target(
    database_url: str,
    confirmation: str | None,
) -> None:
    with pytest.raises(DemoResetSafetyError):
        validate_demo_reset_target(database_url, confirmation)
