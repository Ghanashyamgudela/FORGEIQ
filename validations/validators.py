import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw"
FIXTURES = PROJECT_ROOT / "data" / "test_fixtures"
REPORTS = PROJECT_ROOT / "data" / "processed"


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def export_csv(path, records):
    if not records:
        print(f"No records to export: {path}")
        return

    fieldnames = list(dict.fromkeys(key for record in records for key in record))
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

def get_severity(issue_type):
    severity_map = {
        "MATERIAL_UNAVAILABLE": "CRITICAL",
        "MACHINE_OVERLAP": "HIGH",
        "PRECEDENCE_VIOLATION": "HIGH",
        "CHANGEOVER_OMITTED": "HIGH",
        "OUTSIDE_SHIFT": "MEDIUM",
        "LABOR_CAPACITY_EXCEEDED": "MEDIUM",
    }

    return severity_map.get(issue_type, "LOW")
def parse_date(value):
    return datetime.fromisoformat(value)


def load_data():
    return {
        "products": read_csv(RAW / "products.csv"),
        "machines": read_csv(RAW / "machines.csv"),
        "operations": read_csv(RAW / "order_operations.csv"),
        "eligibility": read_csv(RAW / "routing_machine_eligibility.csv"),
        "calendars": read_csv(RAW / "machine_calendars.csv"),
        "inventory": read_csv(RAW / "inventory_lots.csv"),
        "labor_calendars": pd.read_csv(RAW / "labor_calendars.csv"),
        "material_demand": pd.read_csv(RAW / "order_material_demand.csv"),
        "changeovers": read_csv(RAW / "changeover_matrix.csv"),
        "schedules": read_csv(FIXTURES / "anomaly_scenarios.csv"),
    }


def check_labor_capacity(schedules, labor_calendars):
    violations = []
    schedules = schedules.copy()
    labor_calendars = labor_calendars.copy()
    schedules["start_time"] = pd.to_datetime(schedules["start_time"])
    schedules["end_time"] = pd.to_datetime(schedules["end_time"])
    labor_calendars["work_date"] = pd.to_datetime(
        labor_calendars["work_date"]
    ).dt.date
    labor_calendars["is_working"] = (
        labor_calendars["is_working"].astype(str).str.lower() == "true"
    )

    for _, shift in labor_calendars.iterrows():
        if not shift["is_working"]:
            continue

        skill = shift["skill"]
        work_date = shift["work_date"]
        shift_start = pd.Timestamp(f"{work_date} {shift['start_time']}")
        shift_end = pd.Timestamp(f"{work_date} {shift['end_time']}")
        relevant = schedules[
            (schedules["required_skill"] == skill)
            & (schedules["start_time"] < shift_end)
            & (schedules["end_time"] > shift_start)
        ]
        events = []
        for _, operation in relevant.iterrows():
            start = max(operation["start_time"], shift_start)
            end = min(operation["end_time"], shift_end)
            workers = int(operation["labor_required"])
            schedule_id = operation["schedule_id"]
            events.append((start, workers, schedule_id))
            events.append((end, -workers, schedule_id))

        events.sort(key=lambda event: (event[0], event[1]))
        current_workers = 0
        active_operations = set()
        for timestamp, change, schedule_id in events:
            current_workers += change
            if change < 0:
                active_operations.discard(schedule_id)
                continue

            active_operations.add(schedule_id)
            if current_workers > int(shift["available_workers"]):
                violations.append({
                    "issue_type": "LABOR_CAPACITY_EXCEEDED",
                    "affected_schedule_ids": "|".join(sorted(active_operations)),
                    "severity": "HIGH",
                    "explanation": (
                        f"Required workers: {current_workers}; available workers: "
                        f"{shift['available_workers']} for skill {skill} at {timestamp}"
                    ),
                    "recommended_action": (
                        "Move an operation to another shift or allocate additional "
                        "qualified workers."
                    ),
                    "status": "VIOLATION",
                })
                return violations

    return violations


def check_material_quantity(schedules, material_demand, inventory_lots):
    violations = []
    assigned = schedules[
        schedules["inventory_lot_id"].notna()
        & schedules["inventory_lot_id"].astype(str).ne("")
    ]
    if assigned.empty:
        return violations

    lot_quantities = pd.to_numeric(
        inventory_lots.set_index("lot_id")["quantity"], errors="coerce"
    ).to_dict()
    lot_usage = defaultdict(lambda: {"quantity": 0, "schedule_ids": []})

    for _, schedule in assigned.iterrows():
        lot_id = schedule["inventory_lot_id"]
        operation_id = schedule["operation_id"]
        material_id = schedule["material_id"]
        matching_demand = material_demand[
            (material_demand["operation_id"] == operation_id)
            & (material_demand["material_id"] == material_id)
        ]
        if matching_demand.empty:
            continue

        required_quantity = pd.to_numeric(
            matching_demand["required_quantity"], errors="coerce"
        ).sum()
        usage = lot_usage[(lot_id, material_id)]
        usage["quantity"] += required_quantity
        usage["schedule_ids"].append(schedule["schedule_id"])

    for (lot_id, material_id), usage in lot_usage.items():
        available_quantity = lot_quantities.get(lot_id)
        if available_quantity is None or pd.isna(available_quantity):
            violations.append({
                "issue_type": "UNKNOWN_INVENTORY_LOT",
                "affected_schedule_ids": "|".join(usage["schedule_ids"]),
                "severity": "HIGH",
                "explanation": f"Inventory lot {lot_id} does not exist.",
                "recommended_action": "Assign a valid inventory lot.",
                "status": "VIOLATION",
            })
        elif usage["quantity"] > available_quantity:
            violations.append({
                "issue_type": "MATERIAL_QUANTITY_EXCEEDED",
                "affected_schedule_ids": "|".join(usage["schedule_ids"]),
                "severity": "HIGH",
                "explanation": (
                    f"Material {material_id}: scheduled demand {usage['quantity']} "
                    f"exceeds lot quantity {available_quantity}."
                ),
                "recommended_action": (
                    "Use another lot or reschedule operations after replenishment."
                ),
                "status": "VIOLATION",
            })

    return violations


class ConstraintValidator:
    def __init__(self, data):
        self.data = data
        self.violations = []
        self.machines = {row["machine_id"]: row for row in data["machines"]}
        self.operations = {row["operation_id"]: row for row in data["operations"]}
        self.eligible = defaultdict(set)
        for row in data["eligibility"]:
            self.eligible[row["operation_id"]].add(row["machine_id"])
        self.inventory = {row["lot_id"]: row for row in data["inventory"]}
        self.changeovers = {
            (row["machine_id"], row["from_family"], row["to_family"]): int(
                row["setup_minutes"]
            )
            for row in data["changeovers"]
        }

    def report(self, issue_type, schedule_ids, explanation, recommendation, severity="HIGH"):
        self.violations.append({
            "violation_id": f"VIO-{len(self.violations) + 1:05d}",
            "issue_type": issue_type,
            "affected_schedule_ids": "|".join(schedule_ids),
            "severity": severity,
            "explanation": explanation,
            "recommended_action": recommendation,
            "status": "OPEN",
        })

    def check_schedule_integrity(self):
        seen = set()
        for schedule in self.data["schedules"]:
            schedule_id = schedule["schedule_id"]
            if schedule_id in seen:
                self.report(
                    "DUPLICATE_SCHEDULE_ID", [schedule_id],
                    "Duplicate schedule identifier found.",
                    "Generate a unique immutable schedule ID.",
                )
            seen.add(schedule_id)

            start = parse_date(schedule["start_time"])
            end = parse_date(schedule["end_time"])
            if end <= start:
                self.report(
                    "INVALID_TIME_RANGE", [schedule_id],
                    "Schedule end must be later than start.",
                    "Correct the operation duration.",
                )
            if schedule["machine_id"] not in self.machines:
                self.report(
                    "UNKNOWN_MACHINE", [schedule_id],
                    "Machine ID does not exist.",
                    "Reference a valid machine master record.",
                )

    def check_machine_eligibility(self):
        for schedule in self.data["schedules"]:
            operation = self.operations.get(schedule["operation_id"])
            schedule_id = schedule["schedule_id"]
            if operation is None:
                self.report(
                    "UNKNOWN_OPERATION", [schedule_id],
                    "Scheduled operation does not exist.",
                    "Verify operation ID and its routing.",
                )
                continue
            machine_id = schedule["machine_id"]
            if machine_id not in self.eligible[operation["routing_operation_id"]]:
                self.report(
                    "MACHINE_INELIGIBLE", [schedule_id],
                    f"{machine_id} is not eligible for this operation.",
                    "Assign the operation to an eligible machine.",
                )

    def check_machine_overlap(self):
        by_machine = defaultdict(list)
        for schedule in self.data["schedules"]:
            by_machine[schedule["machine_id"]].append(schedule)
        for machine_id, rows in by_machine.items():
            rows.sort(key=lambda row: parse_date(row["start_time"]))
            for index, first in enumerate(rows):
                first_end = parse_date(first["end_time"])
                for second in rows[index + 1:]:
                    if parse_date(second["start_time"]) >= first_end:
                        break
                    if parse_date(second["end_time"]) > parse_date(first["start_time"]):
                        self.report(
                            "MACHINE_OVERLAP",
                            [first["schedule_id"], second["schedule_id"]],
                            f"Two operations overlap on {machine_id}.",
                            "Move one operation to another eligible machine or available time slot.",
                        )

    def check_precedence(self):
        by_scenario = defaultdict(lambda: defaultdict(list))

        # Group schedules by scenario and production order.
        for schedule in self.data["schedules"]:
            scenario_id = schedule.get("scenario_id")
            if not scenario_id:
                continue
            by_scenario[scenario_id][schedule["order_id"]].append(schedule)

        # Check precedence separately within each scenario.
        for orders in by_scenario.values():
            for rows in orders.values():
                rows.sort(
                    key=lambda row: int(
                        self.operations[row["operation_id"]]["sequence_number"]
                    )
                )
                for previous, current in zip(rows, rows[1:]):
                    previous_sequence = int(
                        self.operations[previous["operation_id"]]["sequence_number"]
                    )
                    current_sequence = int(
                        self.operations[current["operation_id"]]["sequence_number"]
                    )
                    if (
                        current_sequence > previous_sequence
                        and parse_date(current["start_time"])
                        < parse_date(previous["end_time"])
                    ):
                        self.report(
                            "PRECEDENCE_VIOLATION",
                            [
                                previous["schedule_id"],
                                current["schedule_id"],
                            ],
                            "A downstream operation starts before its predecessor finishes.",
                            "Reschedule the downstream operation after predecessor completion.",
                        )

    def check_material_availability(self):
        for schedule in self.data["schedules"]:
            lot_id = schedule.get("inventory_lot_id", "")
            material_id = schedule.get("material_id", "")
            if not lot_id:
                continue
            schedule_id = schedule["schedule_id"]
            lot = self.inventory.get(lot_id)
            if lot is None:
                self.report(
                    "UNKNOWN_INVENTORY_LOT", [schedule_id],
                    "Referenced inventory lot does not exist.",
                    "Assign a valid inventory lot.",
                )
                continue
            if lot["material_id"] != material_id:
                self.report(
                    "MATERIAL_LOT_MISMATCH", [schedule_id],
                    "The selected lot belongs to another material.",
                    "Select a lot for the required material.",
                )
                continue
            if parse_date(schedule["start_time"]) < parse_date(lot["available_at"]):
                self.report(
                    "MATERIAL_UNAVAILABLE", [schedule_id],
                    "Production starts before material availability.",
                    "Wait for material arrival or use another released lot.",
                )

    def check_machine_calendar(self):
        calendars_by_machine = defaultdict(list)
        for row in self.data["calendars"]:
            calendars_by_machine[row["machine_id"]].append(row)
        for schedule in self.data["schedules"]:
            start = parse_date(schedule["start_time"])
            end = parse_date(schedule["end_time"])
            duration = (end - start).total_seconds() / 60
            valid = any(
                calendar["is_working"].lower() == "true"
                and start >= parse_date(calendar["shift_start"])
                and end <= parse_date(calendar["shift_end"])
                and end > start
                and int(calendar["available_minutes"]) >= duration
                for calendar in calendars_by_machine[schedule["machine_id"]]
            )
            if not valid:
                self.report(
                    "OUTSIDE_SHIFT", [schedule["schedule_id"]],
                    "Operation is not fully covered by a working machine shift with sufficient available minutes.",
                    "Move operation into a valid machine calendar window.",
                )

    def check_changeovers(self):
        by_machine = defaultdict(list)
        for schedule in self.data["schedules"]:
            by_machine[schedule["machine_id"]].append(schedule)
        for machine_id, rows in by_machine.items():
            rows.sort(key=lambda row: parse_date(row["start_time"]))
            for previous, current in zip(rows, rows[1:]):
                previous_end = parse_date(previous["end_time"])
                current_start = parse_date(current["start_time"])
                if current_start < previous_end:
                    continue
                setup = self.changeovers.get(
                    (machine_id, previous["product_family"], current["product_family"]),
                    0,
                )
                gap = (current_start - previous_end).total_seconds() / 60
                if gap < setup:
                    self.report(
                        "CHANGEOVER_OMITTED",
                        [previous["schedule_id"], current["schedule_id"]],
                        f"Machine {machine_id} requires {setup} minutes of setup but only {gap:.0f} minutes are available.",
                        "Insert the required sequence-dependent changeover time.",
                    )

    def run_all(self):
        for check in (
            self.check_schedule_integrity,
            self.check_machine_eligibility,
            self.check_machine_overlap,
            self.check_precedence,
            self.check_material_availability,
            self.check_machine_calendar,
            self.check_changeovers,
        ):
            check()
        return self.violations


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    print("FORGEIQ CONSTRAINT VALIDATION")
    print("=" * 45)

    data = load_data()
    validator = ConstraintValidator(data)
    violations = validator.run_all()

    schedules = pd.DataFrame(data["schedules"]).merge(
        pd.DataFrame(data["operations"])[
            ["operation_id", "required_skill", "labor_required"]
        ],
        on="operation_id",
        how="left",
    )
    violations.extend(check_labor_capacity(schedules, data["labor_calendars"]))
    violations.extend(
        check_material_quantity(
            schedules,
            data["material_demand"],
            pd.DataFrame(data["inventory"]),
        )
    )

    # --------------------------------
    # SEVERITY CLASSIFICATION
    # --------------------------------
    severity_map = {
        "MATERIAL_UNAVAILABLE": "CRITICAL",
        "MACHINE_OVERLAP": "HIGH",
        "PRECEDENCE_VIOLATION": "HIGH",
        "CHANGEOVER_OMITTED": "HIGH",
        "OUTSIDE_SHIFT": "MEDIUM",
        "LABOR_CAPACITY_EXCEEDED": "MEDIUM",
    }
    for violation in violations:
        violation["severity"] = severity_map.get(
            violation["issue_type"],
            "LOW"
        )

    # --------------------------------
    # EXPORT VALIDATION REPORT
    # --------------------------------
    export_csv(REPORTS / "validation_report.csv", violations)
    counts = defaultdict(int)
    for violation in violations:
        counts[violation["issue_type"]] += 1

    print("Schedules examined:", len(data["schedules"]))
    print("Total violations:", len(violations))
    print("\nVIOLATION SUMMARY")
    for issue, count in sorted(counts.items()):
        print(f"{issue}: {count}")
    print(f"\nReport saved to {REPORTS / 'validation_report.csv'}")


if __name__ == "__main__":
    main()
