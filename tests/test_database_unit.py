
from datetime import datetime

import pytest

from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import Base
from database.models import (
    ChangeoverMatrix,
    Machine,
    OperationSchedule,
    Product,
    Routing,
    ScheduleRun,
)


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database for each test."""

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
    session = TestSession()

    yield session

    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_database_tables_are_created(db_session):
    table_names = set(Base.metadata.tables.keys())

    assert "products" in table_names
    assert "machines" in table_names
    assert "production_orders" in table_names
    assert "schedule_runs" in table_names
    assert "operation_schedules" in table_names


def test_product_can_be_inserted_and_retrieved(db_session):
    product = Product(
        product_id="TEST-PROD-001",
        sku="TEST-SKU-001",
        product_name="Test Product",
        family="TEST",
        category="TEST",
        unit="PCS",
        lifecycle_state="ACTIVE",
    )

    db_session.add(product)
    db_session.commit()

    saved_product = db_session.get(Product, "TEST-PROD-001")

    assert saved_product is not None
    assert saved_product.sku == "TEST-SKU-001"


def test_duplicate_product_sku_is_rejected(db_session):
    first = Product(
        product_id="TEST-PROD-001",
        sku="DUPLICATE-SKU",
        product_name="Product One",
        family="TEST",
        category="TEST",
    )

    second = Product(
        product_id="TEST-PROD-002",
        sku="DUPLICATE-SKU",
        product_name="Product Two",
        family="TEST",
        category="TEST",
    )

    db_session.add(first)
    db_session.commit()

    db_session.add(second)

    with pytest.raises(IntegrityError):
        db_session.commit()

        db_session.rollback()


def test_routing_without_product_is_rejected(db_session):
    routing = Routing(
        routing_id="TEST-ROUTE-001",
        product_id="NONEXISTENT-PRODUCT",
        version=1,
        lifecycle_state="ACTIVE",
    )

    db_session.add(routing)

    with pytest.raises(IntegrityError):
        db_session.commit()

        db_session.rollback()


def test_duplicate_changeover_rule_is_rejected(db_session):
    machine = Machine(
        machine_id="TEST-MACH-001",
        machine_name="Test Machine",
        machine_type="CUTTING",
        capacity_per_shift=480,
        status="ACTIVE",
    )
    db_session.add(machine)
    db_session.commit()

    first = ChangeoverMatrix(
        changeover_id="TEST-CO-001",
        machine_id="TEST-MACH-001",
        from_family="FAMILY-A",
        to_family="FAMILY-B",
        setup_minutes=30,
    )
    second = ChangeoverMatrix(
        changeover_id="TEST-CO-002",
        machine_id="TEST-MACH-001",
        from_family="FAMILY-A",
        to_family="FAMILY-B",
        setup_minutes=45,
    )
    db_session.add(first)
    db_session.commit()
    db_session.add(second)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_multiple_schedule_runs_are_preserved(db_session):
    first_run = ScheduleRun(
        run_id="TEST-RUN-001",
        created_at=datetime(2026, 11, 1, 8, 0),
        solver_status="FEASIBLE",
        makespan_minutes=480,
        solver_time_seconds=12.5,
        scheduled_operations=10,
        imported_operations=10,
        import_status="COMPLETE",
    )
    second_run = ScheduleRun(
        run_id="TEST-RUN-002",
        created_at=datetime(2026, 11, 1, 9, 0),
        solver_status="OPTIMAL",
        makespan_minutes=420,
        solver_time_seconds=18.0,
        scheduled_operations=10,
        imported_operations=10,
        import_status="COMPLETE",
    )
    db_session.add_all([first_run, second_run])
    db_session.commit()

    saved_runs = db_session.query(ScheduleRun).all()
    assert len(saved_runs) == 2
    saved_ids = {run.run_id for run in saved_runs}
    assert saved_ids == {"TEST-RUN-001", "TEST-RUN-002"}


def test_partial_schedule_import_status_is_preserved(db_session):
    run = ScheduleRun(
        run_id="TEST-RUN-003",
        created_at=datetime(2026, 11, 1, 10, 0),
        solver_status="FEASIBLE",
        makespan_minutes=500,
        solver_time_seconds=20.0,
        scheduled_operations=80,
        imported_operations=25,
        import_status="PARTIAL",
    )
    db_session.add(run)
    db_session.commit()

    saved_run = db_session.get(ScheduleRun, "TEST-RUN-003")
    assert saved_run is not None
    assert saved_run.scheduled_operations == 80
    assert saved_run.imported_operations == 25
    assert saved_run.import_status == "PARTIAL"


def test_schedule_with_invalid_machine_is_rejected(db_session):
    schedule = OperationSchedule(
        schedule_id="TEST-SCH-001",
        run_id=None,
        order_id="NONEXISTENT-ORDER",
        operation_id="NONEXISTENT-OP",
        machine_id="NONEXISTENT-MACHINE",
        calendar_id=None,
        start_time=datetime(2026, 11, 1, 8, 0),
        end_time=datetime(2026, 11, 1, 9, 0),
        status="SCHEDULED",
    )
    db_session.add(schedule)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
