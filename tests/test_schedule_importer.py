import pandas as pd
import pytest

from database import schedule_importer
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import Base
from database.models import (
    Product,
    Routing,
    RoutingOperation,
    ProductionOrder,
    OrderOperation,
    Machine,
    MachineCalendar,
    ScheduleRun,
    OperationSchedule,
)

import runpy

def test_importer_direct_execution_is_blocked():
    with pytest.raises(
        SystemExit,
        match="Call import_schedule\\(\\) through the optimization API",
    ):
        runpy.run_path(
            str(schedule_importer.__file__),
            run_name="__main__",
        )
@pytest.fixture
def test_database(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    TestSession = sessionmaker(bind=engine)

    monkeypatch.setattr(
        schedule_importer,
        "SessionLocal",
        TestSession,
    )

    session = TestSession()
    session.add(Product(
        product_id="PROD-001",
        sku="SKU-001",
        product_name="Test Product",
        family="FAMILY-A",
        category="TEST",
    ))
    session.add(Routing(
        routing_id="ROUTE-001",
        product_id="PROD-001",
    ))
    session.commit()

    session.add(RoutingOperation(
        operation_id="ROUTE-OP-001",
        routing_id="ROUTE-001",
        sequence_number=1,
        duration_minutes=60,
    ))
    session.commit()

    session.add(ProductionOrder(
        order_id="ORD-001",
        product_id="PROD-001",
        routing_id="ROUTE-001",
        quantity=10,
        priority="HIGH",
        due_date=pd.Timestamp("2026-11-02").to_pydatetime(),
        status="RELEASED",
    ))
    session.commit()

    session.add(OrderOperation(
        operation_id="OP-001",
        order_id="ORD-001",
        routing_operation_id="ROUTE-OP-001",
        sequence_number=1,
        duration_minutes=60,
        status="RELEASED",
    ))
    session.commit()

    session.add(Machine(
        machine_id="M-001",
        machine_name="Test Machine",
        machine_type="CUTTING",
        capacity_per_shift=480,
        status="ACTIVE",
    ))
    session.commit()

    session.add(MachineCalendar(
        calendar_id="CAL-001",
        machine_id="M-001",
        shift_start=pd.Timestamp("2026-11-01 06:00:00").to_pydatetime(),
        shift_end=pd.Timestamp("2026-11-01 14:00:00").to_pydatetime(),
        available_minutes=480,
        is_working=True,
    ))
    session.commit()
    session.close()

    yield TestSession

    engine.dispose()

@pytest.fixture
def valid_schedule_df():
    return pd.DataFrame([
        {
            "operation_id": "OP-001",
            "order_id": "ORD-001",
            "machine_id": "M-001",
            "calendar_id": "CAL-001",
            "start_time": "2026-11-01 08:00:00",
            "end_time": "2026-11-01 09:00:00",
            "status": "SCHEDULED",
        }
    ])


@pytest.fixture
def schedule_csv(tmp_path, monkeypatch, valid_schedule_df):
    csv_path = tmp_path / "pilot_schedule.csv"
    valid_schedule_df.to_csv(csv_path, index=False)

    monkeypatch.setattr(
        schedule_importer,
        "CSV_PATH",
        csv_path,
    )

    return csv_path
def test_import_rejects_missing_columns(schedule_csv):
    df = pd.read_csv(schedule_csv)
    df = df.drop(columns=["machine_id"])
    df.to_csv(schedule_csv, index=False)

    with pytest.raises(ValueError, match="Missing CSV columns"):
        schedule_importer.import_schedule(
            "TEST-RUN-001", "FEASIBLE", 60, 1.5
        )


def test_import_rejects_empty_csv(schedule_csv):
    pd.DataFrame(columns=[
        "operation_id",
        "order_id",
        "machine_id",
        "calendar_id",
        "start_time",
        "end_time",
        "status",
    ]).to_csv(schedule_csv, index=False)

    with pytest.raises(ValueError, match="empty"):
        schedule_importer.import_schedule(
            "TEST-RUN-002", "FEASIBLE", 60, 1.5
        )


def test_import_rejects_duplicate_operations(schedule_csv):
    df = pd.read_csv(schedule_csv)
    df = pd.concat([df, df], ignore_index=True)
    df.to_csv(schedule_csv, index=False)

    with pytest.raises(ValueError, match="Duplicate operation IDs"):
        schedule_importer.import_schedule(
            "TEST-RUN-003", "FEASIBLE", 60, 1.5
        )


def test_import_rejects_missing_values(schedule_csv):
    df = pd.read_csv(schedule_csv)
    df.loc[0, "machine_id"] = None
    df.to_csv(schedule_csv, index=False)

    with pytest.raises(ValueError, match="empty values"):
        schedule_importer.import_schedule(
            "TEST-RUN-004", "FEASIBLE", 60, 1.5
        )


def test_import_rejects_invalid_time_order(schedule_csv):
    df = pd.read_csv(schedule_csv)
    df.loc[0, "end_time"] = "2026-11-01 07:00:00"
    df.to_csv(schedule_csv, index=False)

    with pytest.raises(ValueError, match="invalid start/end times"):
        schedule_importer.import_schedule(
            "TEST-RUN-005", "FEASIBLE", 60, 1.5
        )


def test_successful_schedule_import(schedule_csv, test_database):
    imported_count = schedule_importer.import_schedule(
        run_id="TEST-RUN-SUCCESS",
        solver_status="FEASIBLE",
        makespan_minutes=60,
        solver_time_seconds=1.5,
    )
    assert imported_count == 1
    session = test_database()
    try:
        run = session.get(ScheduleRun, "TEST-RUN-SUCCESS")
        assert run is not None
        assert run.scheduled_operations == 1
        assert run.imported_operations == 1
        assert run.import_status == "COMPLETE"
        schedules = session.query(OperationSchedule).filter_by(
            run_id="TEST-RUN-SUCCESS"
        ).all()
        assert len(schedules) == 1
        assert schedules[0].operation_id == "OP-001"
        assert schedules[0].machine_id == "M-001"
        assert schedules[0].status == "SCHEDULED"
    finally:
        session.close()
def test_import_rejects_duplicate_run_id(schedule_csv, test_database):
    schedule_importer.import_schedule(
        run_id="TEST-RUN-DUPLICATE",
        solver_status="FEASIBLE",
        makespan_minutes=60,
        solver_time_seconds=1.5,
    )

    with pytest.raises(
        ValueError,
        match="Schedule run already exists",
    ):
        schedule_importer.import_schedule(
            run_id="TEST-RUN-DUPLICATE",
            solver_status="FEASIBLE",
            makespan_minutes=60,
            solver_time_seconds=1.5,
        )

        session = test_database()
        try:
            runs = session.query(ScheduleRun).filter_by(
                run_id="TEST-RUN-DUPLICATE"
            ).count()

            assert runs == 1
        finally:
            session.close()
def test_failed_import_rolls_back_schedule_run(
    schedule_csv,
    test_database,
):
    df = pd.read_csv(schedule_csv)

    # Use a nonexistent machine to trigger a foreign-key failure.
    df.loc[0, "machine_id"] = "NONEXISTENT-MACHINE"
    df.to_csv(schedule_csv, index=False)

    with pytest.raises(Exception):
        schedule_importer.import_schedule(
            run_id="TEST-RUN-ROLLBACK",
            solver_status="FEASIBLE",
            makespan_minutes=60,
            solver_time_seconds=1.5,
        )

        session = test_database()
        try:
            run = session.get(ScheduleRun, "TEST-RUN-ROLLBACK")
            assert run is None

            schedule_count = session.query(OperationSchedule).filter_by(
                run_id="TEST-RUN-ROLLBACK"
            ).count()

            assert schedule_count == 0
        finally:
            session.close()
def test_import_rejects_missing_csv(monkeypatch, tmp_path):
    missing_path = tmp_path / "missing_schedule.csv"

    monkeypatch.setattr(
        schedule_importer,
        "CSV_PATH",
        missing_path,
    )

    with pytest.raises(FileNotFoundError, match="Schedule CSV not found"):
        schedule_importer.import_schedule(
            "TEST-RUN-MISSING",
            "FEASIBLE",
            60,
            1.5,
        )