
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw"
PROCESSED = PROJECT_ROOT / "data" / "processed"
VIOLATION_COLUMNS = [
    "issue_type",
    "skill",
    "work_date",
    "shift",
    "timestamp",
    "required_workers",
    "available_workers",
    "affected_operations",
    "explanation",
]


def load_data():
    schedule = pd.read_csv(PROCESSED / "pilot_schedule.csv")
    operations = pd.read_csv(RAW / "order_operations.csv")
    labor = pd.read_csv(RAW / "labor_calendars.csv")

    schedule = schedule.merge(
        operations[
            ["operation_id", "required_skill", "labor_required"]
        ],
        on="operation_id",
        how="left",
        validate="one_to_one",
    )

    return schedule, labor


def validate_labor_capacity(schedule, labor):
    violations = []

    schedule = schedule.copy()
    labor = labor.copy()

    schedule["start_time"] = pd.to_datetime(schedule["start_time"])
    schedule["end_time"] = pd.to_datetime(schedule["end_time"])

    labor["work_date"] = pd.to_datetime(
        labor["work_date"]
    ).dt.date

    labor["is_working"] = (
        labor["is_working"]
        .astype(str)
        .str.lower()
        .eq("true")
    )

    for _, shift in labor.iterrows():

        if not shift["is_working"]:
            continue

        skill = shift["skill"]
        work_date = shift["work_date"]

        shift_start = pd.Timestamp(
            f"{work_date} {shift['start_time']}"
        )

        shift_end = pd.Timestamp(
            f"{work_date} {shift['end_time']}"
        )

        relevant = schedule[
            (schedule["required_skill"] == skill)
            & (schedule["start_time"] < shift_end)
            & (schedule["end_time"] > shift_start)
        ]

        events = []

        for _, operation in relevant.iterrows():

            start = max(operation["start_time"], shift_start)
            end = min(operation["end_time"], shift_end)

            workers = int(operation["labor_required"])

            operation_id = operation["operation_id"]

            events.append((start, 1, workers, operation_id))
            events.append((end, 0, -workers, operation_id))

            # End events are processed before start events
            # when two operations meet at the same timestamp.
            events.sort(key=lambda event: (event[0], event[1]))

            current_workers = 0
            active_operations = set()

            for timestamp, event_type, change, operation_id in events:

                current_workers += change

                if event_type == 0:
                    active_operations.discard(operation_id)
                    continue

                active_operations.add(operation_id)

                available_workers = int(shift["available_workers"])

                if current_workers > available_workers:

                    violations.append({
                        "issue_type": "LABOR_CAPACITY_EXCEEDED",
                        "skill": skill,
                        "work_date": str(work_date),
                        "shift": shift["shift"],
                        "timestamp": str(timestamp),
                        "required_workers": current_workers,
                        "available_workers": available_workers,
                        "affected_operations": "|".join(
                            sorted(active_operations)
                        ),
                        "explanation": (
                            f"Required workers: {current_workers}; "
                            f"available workers: {available_workers} "
                            f"for skill {skill} at {timestamp}."
                        ),
                    })

                    return violations


def main():

    PROCESSED.mkdir(parents=True, exist_ok=True)

    print("\nFORGEIQ LABOR CAPACITY VALIDATION")
    print("=" * 50)

    schedule, labor = load_data()

    print("Scheduled operations:", len(schedule))
    print("Labor calendar records:", len(labor))

    violations = validate_labor_capacity(schedule, labor)

    print("\nLABOR VALIDATION RESULTS")
    print("-" * 50)

    report = pd.DataFrame(violations, columns=VIOLATION_COLUMNS)
    report_path = PROCESSED / "pilot_labor_violations.csv"
    report.to_csv(report_path, index=False)

    if violations:

        print("Labor capacity violations:", len(report))

        print(
            report[
                [
                    "skill",
                    "work_date",
                    "shift",
                    "required_workers",
                    "available_workers",
                    "timestamp",
                ]
            ].to_string(index=False)
        )

        print("\nReport saved:", report_path)

    else:

        print("Labor capacity violations: 0")
        print("No labor capacity violations detected.")

    print("\nReport saved:", report_path)
    print("\nVALIDATION COMPLETE")


if __name__ == "__main__":
    main()
