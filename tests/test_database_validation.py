import pytest

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from database import validate_db


@pytest.fixture
def validation_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    with engine.begin() as connection:
        connection.execute(text("""
        CREATE TABLE parent (
            id INTEGER PRIMARY KEY
        )
        """))

        connection.execute(text("""
        CREATE TABLE child (
            id INTEGER PRIMARY KEY,
            parent_id INTEGER,
            FOREIGN KEY(parent_id) REFERENCES parent(id)
        )
        """))

        connection.execute(
            text("INSERT INTO parent (id) VALUES (1)")
        )

        connection.execute(
            text("INSERT INTO child (id, parent_id) VALUES (1, 1)")
        )

    try:
        yield engine
    finally:
        engine.dispose()


def test_database_validation_passes(validation_engine, monkeypatch, capsys):
    monkeypatch.setattr(
        validate_db,
        "engine",
        validation_engine,
    )

    validate_db.validate_database()

    output = capsys.readouterr().out

    assert "Primary-key checks: PASSED" in output
    assert "Duplicate checks: PASSED" in output
    assert "Foreign-key checks: PASSED" in output
    assert "Database integrity: PASSED" in output


def test_database_validation_detects_missing_primary_key(
    validation_engine,
    monkeypatch,
    capsys,
):
    with validation_engine.begin() as connection:
        connection.execute(text("""
        CREATE TABLE invalid_table (
            name TEXT
        )
        """))

    monkeypatch.setattr(
        validate_db,
        "engine",
        validation_engine,
    )

    validate_db.validate_database()

    output = capsys.readouterr().out

    assert "invalid_table: Missing primary key" in output
    assert "Database integrity: FAILED" in output