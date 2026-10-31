
from pathlib import Path

import pandas as pd


DATA_DIR = Path("data/raw")


def load_csv(filename):
    path = DATA_DIR / filename

    assert path.exists(), f"Missing dataset: {filename}"

    return pd.read_csv(path)


def test_expected_dataset_sizes():
    expected_sizes = {
        "products.csv": 100,
        "machines.csv": 40,
        "materials.csv": 200,
        "production_orders.csv": 500,
        "order_operations.csv": 2000,
    }

    for filename, expected_count in expected_sizes.items():
        df = load_csv(filename)

        assert len(df) == expected_count, (
            f"{filename}: expected {expected_count} rows, "
            f"found {len(df)}"
        )


def test_unique_product_ids():
    products = load_csv("products.csv")

    assert products["product_id"].is_unique


def test_unique_machine_ids():
    machines = load_csv("machines.csv")

    assert machines["machine_id"].is_unique


def test_unique_order_ids():
    orders = load_csv("production_orders.csv")

    assert orders["order_id"].is_unique


def test_operation_ids_are_unique():
    operations = load_csv("order_operations.csv")

    assert operations["operation_id"].is_unique
