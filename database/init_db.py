
from sqlalchemy import MetaData, Table, func, inspect, select

from database.db import engine, Base
from database import models


def initialize_database():
    print("\nFORGEIQ DATABASE INITIALIZATION")
    print("=" * 45)

    print("Creating database tables...")

    inspector = inspect(engine)
    schema_mismatch = False
    for table in Base.metadata.sorted_tables:
        if inspector.has_table(table.name):
            actual_columns = {
                column["name"]
                for column in inspector.get_columns(table.name)
            }
            expected_columns = {column.name for column in table.columns}
            actual_foreign_keys = {
                (
                    column_name,
                    foreign_key["referred_table"],
                    referred_column,
                )
                for foreign_key in inspector.get_foreign_keys(table.name)
                for column_name, referred_column in zip(
                    foreign_key["constrained_columns"],
                    foreign_key["referred_columns"],
                )
            }
            expected_foreign_keys = {
                (
                    foreign_key.parent.name,
                    foreign_key.column.table.name,
                    foreign_key.column.name,
                )
                for foreign_key in table.foreign_keys
            }
            if (
                actual_columns != expected_columns
                or actual_foreign_keys != expected_foreign_keys
            ):
                schema_mismatch = True
                break

    if schema_mismatch:
        with engine.connect() as connection:
            existing_tables = inspect(connection).get_table_names()
            metadata = MetaData()
            populated_tables = []
            for table_name in existing_tables:
                table = Table(
                    table_name,
                    metadata,
                    autoload_with=connection
                )
                if connection.scalar(
                    select(func.count()).select_from(table)
                ):
                    populated_tables.append(table_name)

        if populated_tables:
            raise RuntimeError(
                "Database schema is outdated and contains data; "
                "refusing to rebuild tables. Back up the database and "
                "migrate it before initializing. Populated tables: "
                + ", ".join(populated_tables)
            )

        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)

    print("\nDATABASE TABLES CREATED")
    print("-" * 45)

    for table_name in Base.metadata.tables:
        print(f"[OK] {table_name}")

    print("\nTotal tables:", len(Base.metadata.tables))
    print("Database initialization completed successfully!")


if __name__ == "__main__":
    initialize_database()
