
from pathlib import Path

import pandas as pd
import pytest


SCHEDULE_PATH = Path("data/processed/pilot_schedule.csv")


@pytest.fixture
def schedule():
    assert SCHEDULE_PATH.exists(), (
        "Pilot schedule not found. Run the optimizer first."
    )

    return pd.read_csv(SCHEDULE_PATH)


def test_schedule_has_80_operations(schedule):
    assert len(schedule) == 80


def test_each_operation_is_scheduled_once(schedule):
    assert schedule["operation_id"].is_unique


def test_schedule_has_no_missing_required_values(schedule):
    required_columns = [
        "operation_id",
        "order_id",
        "machine_id",
        "calendar_id",
        "start_time",
        "end_time",
        "status",
    ]

    assert schedule[required_columns].notna().all().all()


def test_schedule_times_are_valid(schedule):
    starts = pd.to_datetime(schedule["start_time"])
    ends = pd.to_datetime(schedule["end_time"])

    assert (ends > starts).all()


def test_all_operations_are_scheduled(schedule):
    assert (schedule["status"] == "SCHEDULED").all()
