
import pandas as pd
from pathlib import Path

from database.db import SessionLocal
from database import models
from database.init_db import initialize_database


RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

IMPORT_PLAN = [
    ("products.csv", models.Product, "products"),
    ("machines.csv", models.Machine, "machines"),
    ("materials.csv", models.Material, "materials"),
    ("routings.csv", models.Routing, "routings"),
    ("routing_operations.csv", models.RoutingOperation, "routing_operations"),
    ("production_orders.csv", models.ProductionOrder, "production_orders"),
    ("order_operations.csv", models.OrderOperation, "operations"),
    ("machine_calendars.csv", models.MachineCalendar, "machine_calendars"),
    ("inventory_lots.csv", models.InventoryLot, "inventory_lots"),
    ("routing_machine_eligibility.csv", models.RoutingMachineEligibility, "routing_machine_eligibility"),
    ("order_material_demand.csv", models.OrderMaterialDemand, "order_material_demand"),
    ("labor_calendars.csv", models.LaborCalendar, "labor_calendars"),
    ("changeover_matrix.csv", models.ChangeoverMatrix, "changeover_matrix"),
    ("operation_material_requirements.csv", models.OperationMaterialRequirement, "operation_material_requirements"),
    ("shared_tooling_assignments.csv", models.SharedToolingAssignment, "shared_tooling_assignments"),
]

DATETIME_COLUMNS = {
    "routings": ["effective_from", "effective_to"],
    "production_orders": ["order_date", "due_date"],
    "machine_calendars": ["shift_start", "shift_end"],
    "inventory_lots": ["available_at"],
    "labor_calendars": ["work_date", "start_time", "end_time"],
}


def prepare_records(csv_path, model, table_name):
    df = pd.read_csv(csv_path)

    generated_columns = {
        column.name
        for column in model.__table__.columns
        if column.primary_key and column.autoincrement is True
    }
    expected_columns = {
        column.name for column in model.__table__.columns
    } - generated_columns
    csv_columns = set(df.columns)

    missing = expected_columns - csv_columns
    extra = csv_columns - expected_columns

    if missing:
        raise ValueError(
            f"{table_name}: Missing CSV columns: {sorted(missing)}"
        )

    if extra:
        raise ValueError(
            f"{table_name}: Unexpected CSV columns: {sorted(extra)}"
        )

    for column in DATETIME_COLUMNS.get(table_name, []):
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")

    records = []
    for row in df.to_dict(orient="records"):
        clean_row = {}
        for key, value in row.items():
            if pd.isna(value):
                value = None
            elif isinstance(value, pd.Timestamp):
                value = value.to_pydatetime()
            clean_row[key] = value
        records.append(clean_row)

    return records


def seed_database():
    print("\nFORGEIQ CSV DATABASE IMPORT")
    print("=" * 55)

    if not RAW_DIR.exists():
        raise FileNotFoundError(f"CSV directory not found: {RAW_DIR}")

    initialize_database()
    session = SessionLocal()

    try:
        existing_counts = {
            table_name: session.query(model).count()
            for _, model, table_name in IMPORT_PLAN
        }
        expected_counts = {
            table_name: len(pd.read_csv(RAW_DIR / filename))
            for filename, _, table_name in IMPORT_PLAN
        }

        if existing_counts == expected_counts:
            print("\nDatabase already contains this CSV dataset.")
            print("No rows were changed.")
            return

        with session.begin():
            # Prevent accidental duplicate imports.
            for _, model, table_name in IMPORT_PLAN:
                if session.query(model).first():
                    raise RuntimeError(
                        f"Table '{table_name}' already contains data. "
                        "Import cancelled."
                    )

            print("\nStarting database import...\n")
            total_records = 0

            for filename, model, table_name in IMPORT_PLAN:
                csv_path = RAW_DIR / filename

                if not csv_path.exists():
                    raise FileNotFoundError(
                        f"Missing CSV file: {csv_path}"
                    )

                records = prepare_records(
                    csv_path, model, table_name
                )

                if records:
                    session.bulk_insert_mappings(model, records)

                count = len(records)
                total_records += count
                print(f"[OK] {filename:<42} {count:>6} records")

        print("\n" + "=" * 55)
        print("DATABASE IMPORT COMPLETED")
        print("=" * 55)
        print("Imported CSV files:", len(IMPORT_PLAN))
        print("Total imported records:", total_records)

        print("\nDATABASE ROW COUNTS")
        print("-" * 55)

        for _, model, table_name in IMPORT_PLAN:
            count = session.query(model).count()
            print(f"{table_name:<38} {count:>8}")

        print("\nAll imports completed successfully!")

    except Exception:
        session.rollback()
        print("\nIMPORT FAILED. Transaction rolled back.")
        raise

    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
