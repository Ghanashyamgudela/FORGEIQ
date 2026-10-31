
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

schedule = pd.read_csv(PROCESSED / "pilot_schedule.csv")
operations = pd.read_csv(RAW / "order_operations.csv")
eligibility = pd.read_csv(RAW / "routing_machine_eligibility.csv")
calendars = pd.read_csv(RAW / "machine_calendars.csv")

schedule["start_time"] = pd.to_datetime(schedule["start_time"])
schedule["end_time"] = pd.to_datetime(schedule["end_time"])
schedule["shift_start"] = pd.to_datetime(schedule["shift_start"])
schedule["shift_end"] = pd.to_datetime(schedule["shift_end"])

calendars["is_working"] = calendars["is_working"].astype(str).str.lower().isin(
    ["true", "1", "yes"]
)

print("\nFORGEIQ PILOT SCHEDULE VALIDATION")
print("=" * 45)

# 1. Duplicate operations
duplicates = schedule["operation_id"].duplicated().sum()

# 2. Machine eligibility
valid_pairs = eligibility[["operation_id", "machine_id"]].drop_duplicates()

eligibility_check = schedule.merge(
    valid_pairs,
    left_on=["routing_operation_id", "machine_id"],
    right_on=["operation_id", "machine_id"],
    how="left",
    indicator=True
)

ineligible = (eligibility_check["_merge"] != "both").sum()

# 3. Shift boundaries
outside_shift = (
    (schedule["start_time"] < schedule["shift_start"]) |
    (schedule["end_time"] > schedule["shift_end"])
).sum()

# 4. Working calendar
working_calendar = calendars[
    ["calendar_id", "is_working", "available_minutes"]
]

calendar_check = schedule.merge(
    working_calendar,
    on="calendar_id",
    how="left"
)

nonworking = (
    calendar_check["is_working"].isna() |
    (~calendar_check["is_working"])
).sum()

# 5. Machine overlaps
overlaps = 0

for machine_id, group in schedule.groupby("machine_id"):
    group = group.sort_values("start_time")
    previous_end = None

    for row in group.itertuples():
        if previous_end is not None and row.start_time < previous_end:
            overlaps += 1

        previous_end = (
            row.end_time
            if previous_end is None
            else max(previous_end, row.end_time)
        )

# 6. Shift capacity
shift_usage = schedule.groupby("calendar_id")[
    "duration_minutes"
].sum()

shift_capacity = working_calendar.set_index(
    "calendar_id"
)["available_minutes"]

capacity_violations = sum(
    minutes > shift_capacity.get(calendar_id, 0)
    for calendar_id, minutes in shift_usage.items()
)

# 7. Precedence
pilot_ids = set(schedule["operation_id"])

precedence = operations[
    operations["operation_id"].isin(pilot_ids)
][["operation_id", "predecessor_operation_id"]]

precedence = precedence.dropna(
    subset=["predecessor_operation_id"]
)

schedule_times = schedule.set_index("operation_id")
precedence_violations = 0

for row in precedence.itertuples(index=False):
    predecessor = row.predecessor_operation_id

    if predecessor in schedule_times.index:
        if (
            schedule_times.loc[predecessor, "end_time"]
            > schedule_times.loc[row.operation_id, "start_time"]
        ):
            precedence_violations += 1

checks = {
    "Duplicate operations": duplicates,
    "Ineligible machine assignments": ineligible,
    "Outside shift boundaries": outside_shift,
    "Non-working calendar assignments": nonworking,
    "Machine overlaps": overlaps,
    "Shift capacity violations": capacity_violations,
    "Precedence violations": precedence_violations,
}

for name, count in checks.items():
    result = "PASS" if count == 0 else "FAIL"
    print(f"{name:<35} {count:<5} {result}")

print("\nTotal scheduled operations:", len(schedule))
print("Unique orders:", schedule["order_id"].nunique())
print("Unique machines:", schedule["machine_id"].nunique())

print("\nVALIDATION COMPLETE")
