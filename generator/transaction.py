
import csv
import random
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

from generator.config import (
    SEED,
    START_DATE,
    OUTPUT_DIR
)

rng = random.Random(SEED + 1)

OUTPUT = Path(OUTPUT_DIR)
OUTPUT.mkdir(parents=True, exist_ok=True)

GROUND_TRUTH = Path("data/ground_truth")
GROUND_TRUTH.mkdir(parents=True, exist_ok=True)

START = datetime.strptime(START_DATE, "%Y-%m-%d")


def read_csv(filename):
    with open(OUTPUT / filename, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def export_csv(filename, records):
    if not records:
        return

    with open(OUTPUT / filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)


        # --------------------------------------------------
        # 1. LOAD MASTER DATA
        # --------------------------------------------------

def load_master_data():
    products = read_csv("products.csv")
    routings = read_csv("routings.csv")
    operations = read_csv("routing_operations.csv")
    requirements = read_csv("operation_material_requirements.csv")
    materials = read_csv("materials.csv")
    machines = read_csv("machines.csv")

    return products, routings, operations, requirements, materials, machines


# --------------------------------------------------
# 2. PRODUCTION ORDERS
# --------------------------------------------------

def generate_orders(products, routings):
    orders = []
    product_routing = {
        routing["product_id"]: routing["routing_id"]
        for routing in routings
    }

    for i in range(1, 501):
        product = rng.choice(products)

        order_id = f"ORD-2026-{i:06d}"

        order_date = START + timedelta(
            days=rng.randint(0, 15),
            hours=rng.randint(0, 8)
        )

        quantity = rng.choice([50, 75, 100, 150, 200, 250])

        priority = rng.choices(
            ["LOW", "NORMAL", "HIGH", "URGENT"],
            weights=[15, 50, 25, 10]
        )[0]

        lead_days = {
            "LOW": 18,
            "NORMAL": 14,
            "HIGH": 10,
            "URGENT": 6
        }[priority]

        due_date = order_date + timedelta(
            days=lead_days + rng.randint(-2, 3)
        )

        orders.append({
            "order_id": order_id,
            "product_id": product["product_id"],
            "routing_id": product_routing[product["product_id"]],
            "quantity": quantity,
            "priority": priority,
            "order_date": order_date.isoformat(),
            "due_date": due_date.isoformat(),
            "status": "RELEASED"
        })

    export_csv("production_orders.csv", orders)
    return orders


    # --------------------------------------------------
    # 3. ORDER-SPECIFIC OPERATIONS
    # --------------------------------------------------

def generate_order_operations(orders, operations):
    order_operations = []

    routing_operations = defaultdict(list)
    for operation in operations:
        routing_operations[operation["routing_id"]].append(operation)

    for order in orders:
        route_ops = sorted(
            routing_operations[order["routing_id"]],
            key=lambda operation: int(operation["sequence_number"])
        )

        for index, operation in enumerate(route_ops, start=1):
            order_operation_id = f"OP-{order['order_id']}-{index:02d}"

            order_operations.append({
                "operation_id": order_operation_id,
                "order_id": order["order_id"],
                "routing_operation_id": operation["operation_id"],
                "sequence_number": operation["sequence_number"],
                "duration_minutes": operation["duration_minutes"],
                "required_machine_type": operation[
                    "required_machine_type"
                ],
                "required_skill": operation["required_skill"],
                "labor_required": operation["labor_required"],
                "predecessor_operation_id": (
                    f"OP-{order['order_id']}-{index - 1:02d}"
                    if index > 1 else ""
                ),
                "status": "PENDING"
            })

    export_csv("order_operations.csv", order_operations)
    return order_operations


            # --------------------------------------------------
            # 4. INVENTORY LOTS
            # --------------------------------------------------

def generate_inventory(materials, orders, requirements):
    demand = defaultdict(float)
    material_units = {
        material["material_id"]: material["unit"]
        for material in materials
    }

    requirement_by_operation = defaultdict(lambda: defaultdict(float))
    for requirement in requirements:
        requirement_by_operation[requirement["operation_id"]][
            requirement["material_id"]
        ] += float(requirement["quantity_per_unit"])

    operations = read_csv("routing_operations.csv")
    operations_by_routing = defaultdict(list)
    for operation in operations:
        operations_by_routing[operation["routing_id"]].append(operation)

    for order in orders:
        for operation in operations_by_routing[order["routing_id"]]:
            for material_id, quantity_per_unit in requirement_by_operation[
                operation["operation_id"]
            ].items():
                demand[material_id] += quantity_per_unit * int(order["quantity"])

    lots = []
    for index, material in enumerate(materials, start=1):
        material_id = material["material_id"]
        required_quantity = demand[material_id]

        available_quantity = round(
            max(required_quantity * 1.25, 1000), 2
        )
        delayed = rng.random() < 0.10
        availability_date = START + timedelta(
            days=rng.randint(0, 3) if not delayed else rng.randint(7, 15)
        )

        lots.append({
            "lot_id": f"LOT-2026-{index:06d}",
            "material_id": material_id,
            "quantity": available_quantity,
            "reserved_quantity": 0,
            "available_at": availability_date.isoformat(),
            "quality_status": "RELEASED",
            "is_delayed": delayed
        })

    export_csv("inventory_lots.csv", lots)
    return lots


                    # --------------------------------------------------
                    # 5. ORDER MATERIAL REQUIREMENTS
                    # --------------------------------------------------

def generate_order_material_demand(orders, operations, requirements):
    demand_records = []

    operation_requirements = defaultdict(lambda: defaultdict(float))
    requirement_units = {}
    for requirement in requirements:
        operation_requirements[requirement["operation_id"]][
            requirement["material_id"]
        ] += float(requirement["quantity_per_unit"])
        requirement_units[requirement["material_id"]] = requirement["unit"]

    for operation in operations:
        for material_id, quantity_per_unit in operation_requirements[
            operation["routing_operation_id"]
        ].items():
            demand_records.append({
                "demand_id": (
                    f"DEM-{operation['order_id']}-"
                    f"{int(operation['sequence_number']):02d}-{material_id}"
                ),
                "order_id": operation["order_id"],
                "operation_id": operation["operation_id"],
                "material_id": material_id,
                "required_quantity": round(
                    quantity_per_unit * int(
                        next(
                            order["quantity"]
                            for order in orders
                            if order["order_id"] == operation["order_id"]
                        )
                    ),
                    2
                ),
                "unit": requirement_units[material_id]
            })

    export_csv("order_material_demand.csv", demand_records)
    return demand_records


                    # --------------------------------------------------
                    # 6. SHARED TOOLING ASSIGNMENTS
                    # --------------------------------------------------

def generate_tool_assignments(operations):
    tools = [
        "TOOL-CUT-001",
        "TOOL-CUT-002",
        "TOOL-MACH-001",
        "TOOL-MACH-002",
        "TOOL-ASM-001",
        "TOOL-ASM-002",
        "TOOL-PACK-001",
        "TOOL-PACK-002"
    ]

    assignments = []

    for operation in operations:
        machine_type = operation["required_machine_type"]

        tool = {
            "CUTTING": tools[0:2],
            "MACHINING": tools[2:4],
            "ASSEMBLY": tools[4:6],
            "PACKAGING": tools[6:8]
        }[machine_type]

        assignments.append({
            "operation_id": operation["operation_id"],
            "tool_id": rng.choice(tool),
            "tool_sharing": True
        })

    export_csv("shared_tooling_assignments.csv", assignments)
    return assignments


    # --------------------------------------------------
    # 7. GENERATION PIPELINE
    # --------------------------------------------------

def main():
    print("FORGEIQ TRANSACTION GENERATOR")
    print("=" * 40)

    (
        products,
        routings,
        operations,
        requirements,
        materials,
        machines
    ) = load_master_data()

    orders = generate_orders(products, routings)

    order_operations = generate_order_operations(
        orders, operations
    )

    inventory = generate_inventory(
        materials, orders, requirements
    )

    material_demand = generate_order_material_demand(
        orders, order_operations, requirements
    )

    tooling = generate_tool_assignments(order_operations)

    print("Production orders:", len(orders))
    print("Order operations:", len(order_operations))
    print("Inventory lots:", len(inventory))
    print("Material demand records:", len(material_demand))
    print("Shared tooling assignments:", len(tooling))
    print("=" * 40)
    print("Transaction generation completed!")


if __name__ == "__main__":
    main()
