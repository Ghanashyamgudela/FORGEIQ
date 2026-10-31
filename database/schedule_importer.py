
from pathlib import Path

import pandas as pd

from database.db import SessionLocal
from database.models import OperationSchedule


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "processed" / "pilot_schedule.csv"


def import_schedule(replace_existing=False):
    print("\nFORGEIQ SCHEDULE IMPORT")
    print("=" * 40)

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Schedule CSV not found: {CSV_PATH}"
        )

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
        raise ValueError(
            f"Missing CSV columns: {missing}"
        )

    if df.empty:
        raise ValueError("Schedule CSV is empty.")

    if df["operation_id"].duplicated().any():
        raise ValueError(
            "Duplicate operation IDs found in schedule CSV."
        )

    if df[required_columns].isnull().any().any():
        raise ValueError(
            "Required schedule fields contain empty values."
        )

    df["start_time"] = pd.to_datetime(
        df["start_time"], errors="raise"
    )

    df["end_time"] = pd.to_datetime(
        df["end_time"], errors="raise"
    )

    if (df["end_time"] <= df["start_time"]).any():
        raise ValueError(
            "Some operations have invalid start/end times."
        )

    session = SessionLocal()

    try:
        existing_count = (
            session.query(OperationSchedule).count()
        )

        if existing_count > 0 and not replace_existing:
            raise RuntimeError(
                f"Database already contains {existing_count} "
                "schedule records. Import cancelled. "
                "Use replace_existing=True to replace them."
            )
        if replace_existing and existing_count > 0:
            session.query(OperationSchedule).delete(
                synchronize_session=False
            )

        records = []

        for row in df.to_dict(orient="records"):
            record = OperationSchedule(
                schedule_id=f"SCHED-{row['operation_id']}",
                order_id=row["order_id"],
                operation_id=row["operation_id"],
                machine_id=row["machine_id"],
                calendar_id=row["calendar_id"],
                start_time=row["start_time"].to_pydatetime(),
                end_time=row["end_time"].to_pydatetime(),
                status=row["status"],
            )

            records.append(record)

        session.add_all(records)
        session.commit()

        print(f"CSV records: {len(df)}")
        print(f"Database records imported: {len(records)}")
        print("Schedule import completed successfully!")
        return len(records)

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    import_schedule()
