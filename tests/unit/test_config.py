from sqlalchemy import make_url

from changeops.config import Settings


def test_component_database_settings_build_tls_required_encoded_url() -> None:
    settings = Settings(
        database_url=None,
        db_host="private-db.example.internal",
        db_port=5432,
        db_name="changeops",
        db_username="runtime user",
        db_password="p@ss:/word",
        db_sslmode="require",
        _env_file=None,
    )

    url = make_url(settings.database_url)
    assert url.host == "private-db.example.internal"
    assert url.database == "changeops"
    assert url.username == "runtime user"
    assert url.password == "p@ss:/word"
    assert url.query == {"sslmode": "require"}


def test_component_database_settings_fail_closed_when_incomplete() -> None:
    try:
        Settings(
            database_url=None,
            db_host="private-db.example.internal",
            db_name="changeops",
            db_username="runtime",
            db_sslmode="require",
            _env_file=None,
        )
    except ValueError as error:
        assert "must be set together" in str(error)
    else:
        raise AssertionError("Incomplete component configuration was accepted.")


def test_component_database_settings_reject_non_tls_connection() -> None:
    try:
        Settings(
            database_url=None,
            db_host="private-db.example.internal",
            db_name="changeops",
            db_username="runtime",
            db_password="secret",
            db_sslmode="disable",
            _env_file=None,
        )
    except ValueError as error:
        assert "DB_SSLMODE=require" in str(error)
    else:
        raise AssertionError("A non-TLS deployed database URL was accepted.")
