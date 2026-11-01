
from sqlalchemy import inspect, text

from database import models
from database.db import engine


def validate_database():
    inspector = inspect(engine)
    errors = []

    print("\nFORGEIQ DATABASE INTEGRITY CHECK")
    print("=" * 45)

    tables = inspector.get_table_names()
    print(f"Tables found: {len(tables)}")

    with engine.connect() as connection:
        for table in tables:
            pk_info = inspector.get_pk_constraint(table)
            primary_keys = pk_info.get("constrained_columns") or []

            if not primary_keys:
                errors.append(f"{table}: Missing primary key")
                continue

            columns = ", ".join(f'"{column}"' for column in primary_keys)
            query = text(
                f'SELECT {columns}, COUNT(*) AS total '
                f'FROM "{table}" '
                f'GROUP BY {columns} '
                f'HAVING COUNT(*) > 1'
            )
            duplicates = connection.execute(query).fetchall()

            if duplicates:
                errors.append(
                    f"{table}: Duplicate primary-key records found"
                )

        foreign_key_errors = connection.execute(
            text("PRAGMA foreign_key_check")
        ).fetchall()
        if foreign_key_errors:
            errors.append(
                f"Foreign-key violations: {len(foreign_key_errors)}"
            )

    print("\nVALIDATION RESULTS")
    print("-" * 45)
    if errors:
        for error in errors:
            print("FAIL:", error)
        print("\nTotal issues:", len(errors))
        print("Database integrity: FAILED")
    else:
        print("Primary-key checks: PASSED")
        print("Duplicate checks: PASSED")
        print("Foreign-key checks: PASSED")
        print("\nTotal issues: 0")
        print("Database integrity: PASSED")


if __name__ == "__main__":
    validate_database()
