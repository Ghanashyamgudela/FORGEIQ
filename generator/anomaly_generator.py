import csv
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path.cwd()
if not (PROJECT_ROOT / "data" / "raw").is_dir():
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw"
GROUND = PROJECT_ROOT / "data" / "ground_truth"
FIXTURES = PROJECT_ROOT / "data" / "test_fixtures"


def read_csv(filename):
    with open(RAW / filename, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"No records to write: {path}")

    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    GROUND.mkdir(parents=True, exist_ok=True)
    FIXTURES.mkdir(parents=True, exist_ok=True)

    orders = read_csv("production_orders.csv")
    order_ops = read_csv("order_operations.csv")
    products = read_csv("products.csv")
    eligibility = read_csv("routing_machine_eligibility.csv")
    demand = read_csv("order_material_demand.csv")
    inventory = read_csv("inventory_lots.csv")
    changeovers = read_csv("changeover_matrix.csv")

    product_map = {product["product_id"]: product for product in products}
    operation_map = {operation["operation_id"]: operation for operation in order_ops}

    eligible_map = defaultdict(set)
    for row in eligibility:
        eligible_map[row["operation_id"]].add(row["machine_id"])

    changeover_map = {
        (row["machine_id"], row["from_family"], row["to_family"]): int(row["setup_minutes"])
        for row in changeovers
    }

    schedules = []
    ground_truth = []
    schedule_counter = 1

    def add_schedule(operation, machine_id, start, end):
        nonlocal schedule_counter

        order = next(order for order in orders if order["order_id"] == operation["order_id"])
        product = product_map[order["product_id"]]
        schedule_id = f"SCH-2026-{900000 + schedule_counter:06d}"
        schedule_counter += 1

        schedules.append({
            "schedule_id": schedule_id,
            "scenario_id": "",
            "order_id": operation["order_id"],
            "operation_id": operation["operation_id"],
            "routing_operation_id": operation["routing_operation_id"],
            "product_id": order["product_id"],
            "product_family": product["family"],
            "machine_id": machine_id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "status": "CANDIDATE",
        })
        return schedule_id

    def add_ground_truth(issue_type, ids, explanation, severity="HIGH"):
        scenario_id = f"ANOM-{len(ground_truth) + 1:03d}"
        ground_truth.append({
            "scenario_id": scenario_id,
            "issue_type": issue_type,
            "affected_schedule_ids": "|".join(ids),
            "expected_label": "VIOLATION",
            "severity": severity,
            "explanation": explanation,
        })
        affected_schedule_ids = set(ids)
        for schedule in schedules:
            if schedule["schedule_id"] in affected_schedule_ids:
                schedule["scenario_id"] = scenario_id

    def find_operation(sequence, excluded_orders=None):
        excluded_orders = excluded_orders or set()
        candidates = [
            operation for operation in order_ops
            if int(operation["sequence_number"]) == sequence
            and operation["order_id"] not in excluded_orders
        ]
        if not candidates:
            raise ValueError(f"No operation found for sequence {sequence}")
        return candidates

    base = datetime(2026, 11, 2, 6, 0)

    # Scenario 1: two eligible operations overlap on one machine.
    sequence_one = find_operation(1)
    overlap_pair = None
    for index, operation_one in enumerate(sequence_one):
        for operation_two in sequence_one[index + 1:]:
            if operation_one["order_id"] == operation_two["order_id"]:
                continue

            common_machines = (
                eligible_map[operation_one["routing_operation_id"]]
                & eligible_map[operation_two["routing_operation_id"]]
            )
            if common_machines:
                overlap_pair = (operation_one, operation_two, sorted(common_machines)[0])
                break
        if overlap_pair:
            break

    if not overlap_pair:
        raise ValueError("Could not find two sequence-one operations with a common eligible machine")

    first, second, shared_machine = overlap_pair
    first_id = add_schedule(first, shared_machine, base, base + timedelta(hours=2))
    second_id = add_schedule(
        second, shared_machine,
        base + timedelta(hours=1), base + timedelta(hours=3),
    )
    add_ground_truth(
        "MACHINE_OVERLAP", [first_id, second_id],
        "Two operations overlap on the same machine.",
    )

    # Scenario 2: operation two starts before operation one finishes.
    order_with_multiple_operations = next(
        order for order in orders
        if sum(operation["order_id"] == order["order_id"] for operation in order_ops) >= 2
    )
    sequence_ops = sorted(
        [operation for operation in order_ops if operation["order_id"] == order_with_multiple_operations["order_id"]],
        key=lambda operation: int(operation["sequence_number"]),
    )
    operation_one, operation_two = sequence_ops[:2]
    machine_one = sorted(eligible_map[operation_one["routing_operation_id"]])[0]
    machine_two = sorted(eligible_map[operation_two["routing_operation_id"]])[0]
    first_id = add_schedule(
        operation_one, machine_one,
        base + timedelta(hours=4), base + timedelta(hours=6),
    )
    second_id = add_schedule(
        operation_two, machine_two,
        base + timedelta(hours=3), base + timedelta(hours=5),
    )
    add_ground_truth(
        "PRECEDENCE_VIOLATION", [first_id, second_id],
        "Operation 2 starts before its predecessor finishes.",
    )

    # Scenario 3: schedule an operation before its required lot is available.
    delayed_match = next(
        (
            (lot, material_demand)
            for lot in inventory
            if lot["is_delayed"].lower() == "true"
            for material_demand in demand
            if material_demand["material_id"] == lot["material_id"]
        ),
        None,
    )
    if delayed_match is None:
        raise ValueError("No delayed material lot with production demand found")

    lot, material_demand = delayed_match
    material_operation = operation_map[material_demand["operation_id"]]
    material_machine = sorted(eligible_map[material_operation["routing_operation_id"]])[0]
    material_start = datetime.fromisoformat(lot["available_at"]) - timedelta(days=1)
    material_id = add_schedule(
        material_operation, material_machine,
        material_start, material_start + timedelta(hours=1),
    )
    schedules[-1]["material_id"] = lot["material_id"]
    schedules[-1]["inventory_lot_id"] = lot["lot_id"]
    add_ground_truth(
        "MATERIAL_UNAVAILABLE", [material_id],
        "Operation is scheduled before its required material lot becomes available.",
    )

    # Scenario 4: schedule work on a Sunday.
    outside_operation = find_operation(1)[-1]
    outside_machine = sorted(eligible_map[outside_operation["routing_operation_id"]])[0]
    outside_start = datetime(2026, 11, 1, 10, 0)
    outside_id = add_schedule(
        outside_operation, outside_machine,
        outside_start, outside_start + timedelta(hours=1),
    )
    add_ground_truth(
        "OUTSIDE_SHIFT", [outside_id],
        "Operation is scheduled on a non-working Sunday.",
    )

    # Scenario 5: omit the required setup between product families.
    changeover_pair = None
    for index, order_one in enumerate(orders):
        for order_two in orders[index + 1:]:
            family_one = product_map[order_one["product_id"]]["family"]
            family_two = product_map[order_two["product_id"]]["family"]
            if family_one == family_two:
                continue

            operations_one = [
                operation for operation in order_ops
                if operation["order_id"] == order_one["order_id"]
                and int(operation["sequence_number"]) == 1
            ]
            operations_two = [
                operation for operation in order_ops
                if operation["order_id"] == order_two["order_id"]
                and int(operation["sequence_number"]) == 1
            ]
            if not operations_one or not operations_two:
                continue

            eligible_one = eligible_map[operations_one[0]["routing_operation_id"]]
            eligible_two = eligible_map[operations_two[0]["routing_operation_id"]]
            common_machines = eligible_one & eligible_two
            setup_minutes = max(
                (changeover_map.get((machine, family_one, family_two), 0)
                 for machine in common_machines),
                default=0,
            )
            if common_machines and setup_minutes > 0:
                changeover_pair = (
                    operations_one[0], operations_two[0],
                    sorted(common_machines)[0], setup_minutes,
                )
                break
        if changeover_pair:
            break

    if not changeover_pair:
        raise ValueError("Could not find a changeover scenario")

    change_operation_one, change_operation_two, change_machine, setup_minutes = changeover_pair
    change_start = base + timedelta(hours=10)
    first_id = add_schedule(
        change_operation_one, change_machine,
        change_start, change_start + timedelta(hours=1),
    )
    second_id = add_schedule(
        change_operation_two, change_machine,
        change_start + timedelta(hours=1), change_start + timedelta(hours=2),
    )
    add_ground_truth(
        "CHANGEOVER_OMITTED", [first_id, second_id],
        f"Required {setup_minutes}-minute changeover was omitted.",
    )

    # Add deterministic secondary findings.
    # These are documented alongside the five primary findings.
    ground_truth.extend([
        {
            "scenario_id": "SEC-001",
            "issue_type": "OUTSIDE_SHIFT",
            "affected_schedule_ids": "SCH-2026-900005",
            "expected_label": "VIOLATION",
            "severity": "MEDIUM",
            "explanation": (
                "Secondary finding: operation also falls outside "
                "a valid working machine shift."
            ),
        },
        {
            "scenario_id": "SEC-002",
            "issue_type": "LABOR_CAPACITY_EXCEEDED",
            "affected_schedule_ids": (
                "SCH-2026-900001|SCH-2026-900002"
            ),
            "expected_label": "VIOLATION",
            "severity": "MEDIUM",
            "explanation": (
                "Secondary finding: overlapping operations require "
                "6 workers while only 4 are available."
            ),
        },
    ])

    write_csv(FIXTURES / "anomaly_scenarios.csv", schedules)
    write_csv(GROUND / "ground_truth.csv", ground_truth)

    print("\nFORGEIQ ANOMALY GENERATION COMPLETE")
    print("-----------------------------------")
    print("Injected scenarios:", len(ground_truth))
    print("Affected schedule records:", len(schedules))
    print("Machine overlap: YES")
    print("Precedence violation: YES")
    print("Material unavailable: YES")
    print("Outside shift: YES")
    print("Changeover omitted: YES")
    print("-----------------------------------")
    print("Ground truth saved separately.")


if __name__ == "__main__":
    main()
