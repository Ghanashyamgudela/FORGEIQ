import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "forgeiq.db"


def migrate():
    connection = sqlite3.connect(DB_PATH)

    try:
        cursor = connection.cursor()

        columns = {
            row[1]
            for row in cursor.execute(
                "PRAGMA table_info(schedule_runs)"
            ).fetchall()
        }

        if "imported_operations" not in columns:
            cursor.execute("""
            ALTER TABLE schedule_runs
            ADD COLUMN imported_operations INTEGER NOT NULL DEFAULT 0
            """)

            if "import_status" not in columns:
                cursor.execute("""
                ALTER TABLE schedule_runs
                ADD COLUMN import_status TEXT NOT NULL DEFAULT 'PENDING'
                """)

                # Reconcile run metadata with actual persisted schedule rows.
                cursor.execute("""
                UPDATE schedule_runs
                SET imported_operations = (
                    SELECT COUNT(*)
                    FROM operation_schedules
                    WHERE operation_schedules.run_id = schedule_runs.run_id
                )
                """)

                cursor.execute("""
                UPDATE schedule_runs
                SET import_status = CASE
                WHEN imported_operations = scheduled_operations
                THEN 'COMPLETE'
                WHEN imported_operations > 0
                THEN 'PARTIAL'
                ELSE 'FAILED'
                END
                """)

                connection.commit()

                print("Migration completed successfully.")
                print("\nSchedule import reconciliation:")

                rows = cursor.execute("""
                SELECT
                run_id,
                scheduled_operations,
                imported_operations,
                import_status
                FROM schedule_runs
                ORDER BY created_at DESC
                """).fetchall()

                for row in rows:
                    print(row)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    migrate()