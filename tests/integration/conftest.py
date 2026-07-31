import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://changeops:changeops@localhost:5432/changeops_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from changeops.config import get_settings  # noqa: E402

get_settings.cache_clear()

from changeops.db.session import SessionLocal, engine  # noqa: E402
from changeops.main import create_app  # noqa: E402
from changeops.services.seed_service import seed_database  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_test_database() -> Iterator[None]:
    test_url = make_url(TEST_DATABASE_URL)
    database_name = test_url.database
    if not database_name or database_name != "changeops_test":
        raise RuntimeError("Integration tests require the dedicated changeops_test database")

    admin_engine = create_engine(
        test_url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )
    with admin_engine.connect() as connection:
        connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)')
        connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')

    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "head")
    yield

    engine.dispose()
    with admin_engine.connect() as connection:
        connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)')
    admin_engine.dispose()


@pytest.fixture(autouse=True)
def reset_scenario_data(migrated_test_database: None) -> Iterator[None]:
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE impact_assessments CASCADE"))
    with SessionLocal.begin() as session:
        seed_database(session)

    yield

    with SessionLocal.begin() as session:
        seed_database(session)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client
