
from pathlib import Path
from datetime import datetime

import pandas as pd

from database.db import SessionLocal
from database.models import OperationSchedule, ScheduleRun


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "processed" / "pilot_schedule.csv"


def import_schedule(
    run_id,
    solver_status,
    makespan_minutes,
    solver_time_seconds,
):
    print("\nFORGEIQ SCHEDULE IMPORT")
    print("=" * 40)

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Schedule CSV not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)

    required_columns = [
        "operation_id",
        "order_id",
        "machine_id",
        "calendar_id",
        "start_time",
        "end_time",
        "status",
    ]

    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(f"Missing CSV columns: {missing}")

    if df.empty:
        raise ValueError("Schedule CSV is empty.")

    if df["operation_id"].duplicated().any():
        raise ValueError("Duplicate operation IDs found in schedule CSV.")

    if df[required_columns].isnull().any().any():
        raise ValueError("Required schedule fields contain empty values.")

    df["start_time"] = pd.to_datetime(df["start_time"], errors="raise")
    df["end_time"] = pd.to_datetime(df["end_time"], errors="raise")

    if (df["end_time"] <= df["start_time"]).any():
        raise ValueError("Some operations have invalid start/end times.")

    session = SessionLocal()

    try:
        if session.get(ScheduleRun, run_id) is not None:
            raise ValueError(f"Schedule run already exists: {run_id}")

        run = ScheduleRun(
            run_id=run_id,
            created_at=datetime.now(),
            solver_status=solver_status,
            makespan_minutes=makespan_minutes,
            solver_time_seconds=solver_time_seconds,
            scheduled_operations=len(df),
            imported_operations=0,
            import_status="PENDING",
        )

        session.add(run)
        session.flush()

        records = []

        for row in df.to_dict(orient="records"):
            records.append(
                OperationSchedule(
                    schedule_id=f"SCHED-{run_id}-{row['operation_id']}",
                    run_id=run_id,
                    order_id=row["order_id"],
                    operation_id=row["operation_id"],
                    machine_id=row["machine_id"],
                    calendar_id=row["calendar_id"],
                    start_time=row["start_time"].to_pydatetime(),
                    end_time=row["end_time"].to_pydatetime(),
                    status=row["status"],
                )
            )

        # Insert all schedule records together.
        session.add_all(records)
        # Update import tracking before committing the transaction.
        run.imported_operations = len(records)
        run.import_status = (
            "COMPLETE"
            if len(records) == run.scheduled_operations
            else "PARTIAL"
        )
        session.commit()

        print("Run ID:", run_id)
        print("Schedule records imported:", len(records))
        print("Previous schedule runs preserved.")

        return len(records)

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(
        "Call import_schedule() through the optimization API."
    )
