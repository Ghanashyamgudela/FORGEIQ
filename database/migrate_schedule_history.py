
from sqlalchemy import inspect, text

from database.db import engine, SessionLocal
from database.models import ScheduleRun
from datetime import datetime

def migrate_schedule_history():
    print("\nFORGEIQ SCHEDULE HISTORY MIGRATION")
    print("=" * 45)

    inspector = inspect(engine)

    # Create the new schedule_runs table.
    ScheduleRun.__table__.create(engine, checkfirst=True)

    columns = {
        column["name"]
        for column in inspector.get_columns("operation_schedules")
    }

    # Add run_id to existing schedules if it does not exist.
    if "run_id" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE operation_schedules "
                    "ADD COLUMN run_id VARCHAR"
                    "REFERENCES schedule_runs(run_id)"
                )
            )
            print("[OK] Added run_id column.")
    else:
        print("[OK] run_id column already exists.")

        session = SessionLocal()

        try:
            existing_schedules = session.execute(
                text(
                    "SELECT COUNT(*) FROM operation_schedules "
                    "WHERE run_id IS NULL"
                )
            ).scalar_one()

            if existing_schedules:
                legacy_run = ScheduleRun(
                    run_id="RUN-LEGACY-000001",
                    created_at=datetime.now(),
                    solver_status="LEGACY",
                    makespan_minutes=None,
                    solver_time_seconds=None,
                    scheduled_operations=existing_schedules,
                )

                session.add(legacy_run)
                session.flush()

                session.execute(
                    text(
                        "UPDATE operation_schedules "
                        "SET run_id = :run_id WHERE run_id IS NULL"
                    ),
                    {"run_id": legacy_run.run_id},
                )

                session.commit()

                print("Legacy schedules assigned:", existing_schedules)
                print("Migration completed successfully.")

        except Exception:
            session.rollback()
            raise

        finally:
            session.close()


if __name__ == "__main__":
    migrate_schedule_history()
