
from pathlib import Path

import pandas as pd
import pytest


DATA_DIR = Path("data/raw")
SCHEDULE_PATH = Path("data/processed/pilot_schedule.csv")


@pytest.fixture
def schedule():
    assert SCHEDULE_PATH.exists(), "Run the optimizer first."
    return pd.read_csv(SCHEDULE_PATH)


@pytest.fixture
def eligibility():
    return pd.read_csv(
        DATA_DIR / "routing_machine_eligibility.csv"
    )


@pytest.fixture
def operations():
    return pd.read_csv(
        DATA_DIR / "order_operations.csv"
    )


def test_machine_assignments_are_eligible(schedule, eligibility):
    allowed = set(
        zip(
            eligibility["operation_id"],
            eligibility["machine_id"],
        )
    )

    assigned = set(zip(
        schedule["routing_operation_id"],
        schedule["machine_id"],
    ))

    invalid = assigned - allowed

    assert not invalid, (
        f"Ineligible machine assignments found: {list(invalid)[:5]}"
    )


def test_operation_precedence_is_respected(schedule, operations):
    merged = schedule.merge(
        operations[["operation_id", "predecessor_operation_id"]],
        on="operation_id",
        how="left",
        validate="one_to_one",
    )

    merged["start_time"] = pd.to_datetime(merged["start_time"])
    merged["end_time"] = pd.to_datetime(merged["end_time"])
    schedule_ends = merged.set_index("operation_id")["end_time"]

    for operation in merged.itertuples(index=False):
        predecessor_id = operation.predecessor_operation_id
        if pd.notna(predecessor_id) and predecessor_id in schedule_ends:
            assert operation.start_time >= schedule_ends[predecessor_id], (
                f"Precedence violation: {predecessor_id} must finish before "
                f"{operation.operation_id} starts"
            )
