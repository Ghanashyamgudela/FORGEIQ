
import csv
import random
from pathlib import Path
from datetime import datetime, timedelta

from generator.config import (
    SEED,
    PRODUCT_COUNT,
    MACHINE_COUNT,
    MATERIAL_COUNT,
    OPERATIONS_PER_ROUTING,
    START_DATE,
    DAYS_TO_GENERATE,
    OUTPUT_DIR
)

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

random.seed(SEED)

OUTPUT = Path(OUTPUT_DIR)
OUTPUT.mkdir(parents=True, exist_ok=True)

MACHINE_TYPES = [
    "CUTTING",
    "MACHINING",
    "ASSEMBLY",
    "PACKAGING"
]

PRODUCT_FAMILIES = [
    "AUTOMOTIVE",
    "ELECTRONICS",
    "INDUSTRIAL",
    "CONSUMER",
    "MEDICAL",
    "AEROSPACE",
    "ELECTRICAL",
    "MECHANICAL"
]

SHIFTS = [
    ("06:00", "14:00"),
    ("14:00", "22:00")
]

def export_csv(filename, records):
    if not records:
        return

    with open(OUTPUT / filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)


        # --------------------------------------------------
        # 1. PRODUCTS
        # --------------------------------------------------

def generate_products():
    products = []

    for i in range(1, PRODUCT_COUNT + 1):
        sku = f"SKU-{i:04d}"

        products.append({
            "product_id": f"PROD-2026-{i:06d}",
            "sku": sku,
            "product_name": f"FORGEIQ Product {i:03d}",
            "family": random.choice(PRODUCT_FAMILIES),
            "category": random.choice(["STANDARD", "PREMIUM", "CUSTOM"]),
            "unit": "PCS",
            "lifecycle_state": "ACTIVE"
        })

    export_csv("products.csv", products)
    return products


    # --------------------------------------------------
    # 2. MACHINES
    # --------------------------------------------------

def generate_machines():
    machines = []

    for i in range(1, MACHINE_COUNT + 1):
        machine_type = MACHINE_TYPES[(i - 1) // 10]

        machines.append({
            "machine_id": f"MACH-{i:03d}",
            "machine_name": f"{machine_type} Machine {i:03d}",
            "machine_type": machine_type,
            "capacity_per_shift": random.choice([420, 430, 440, 450]),
            "status": "ACTIVE",
            "location": f"ZONE-{((i - 1) // 10) + 1}"
        })

    export_csv("machines.csv", machines)
    return machines


    # --------------------------------------------------
    # 3. MATERIALS
    # --------------------------------------------------

def generate_materials():
    materials = []

    for i in range(1, MATERIAL_COUNT + 1):
        materials.append({
            "material_id": f"MAT-{i:04d}",
            "material_name": f"Industrial Material {i:03d}",
            "material_type": random.choice([
                "RAW",
                "COMPONENT",
                "PACKAGING",
                "ELECTRONIC"
            ]),
            "unit": random.choice(["PCS", "KG", "M"]),
            "lifecycle_state": "ACTIVE"
        })

    export_csv("materials.csv", materials)
    return materials


    # --------------------------------------------------
    # 4. ROUTINGS AND OPERATIONS
    # --------------------------------------------------

def generate_routings(products, machines, materials):
    routings = []
    operations = []
    eligibility = []
    requirements = []

    machines_by_type = {}
    for machine_type in MACHINE_TYPES:
        machines_by_type[machine_type] = [
            m["machine_id"]
            for m in machines
            if m["machine_type"] == machine_type
        ]

    material_units = {
        material["material_id"]: material["unit"]
        for material in materials
    }

    all_material_ids = list(material_units.keys())

    for product in products:
        sku = product["sku"]
        routing_id = f"ROUTE-{sku}-01"

        routings.append({
            "routing_id": routing_id,
            "product_id": product["product_id"],
            "version": 1,
            "effective_from": "2026-01-01",
            "effective_to": "",
            "lifecycle_state": "ACTIVE"
        })

        for step in range(1, OPERATIONS_PER_ROUTING + 1):
            operation_id = f"{routing_id}-OP-{step:02d}"
            machine_type = MACHINE_TYPES[step - 1]

            operations.append({
                "operation_id": operation_id,
                "routing_id": routing_id,
                "sequence_number": step,
                "operation_name": machine_type,
                "required_machine_type": machine_type,
                "duration_minutes": random.randint(20, 120),
                "required_skill": machine_type,
                "labor_required": random.randint(1, 3)
            })

            eligible_machines = random.sample(
                machines_by_type[machine_type],
                k=random.randint(3, 6)
            )

            for machine_id in eligible_machines:
                eligibility.append({
                    "routing_id": routing_id,
                    "operation_id": operation_id,
                    "machine_id": machine_id
                })

                selected_materials = random.sample(
                    all_material_ids,
                    k=random.randint(1, 2)
                )

                for material_id in selected_materials:
                    requirements.append({
                        "operation_id": operation_id,
                        "material_id": material_id,
                        "quantity_per_unit": round(
                            random.uniform(0.5, 3.0), 2
                        ),
                        "unit": material_units[material_id]
                    })

    export_csv("routings.csv", routings)
    export_csv("routing_operations.csv", operations)
    export_csv("routing_machine_eligibility.csv", eligibility)
    export_csv("operation_material_requirements.csv", requirements)

    return routings, operations, eligibility, requirements


                    # --------------------------------------------------
                    # 5. MACHINE CALENDARS
                    # --------------------------------------------------

def generate_calendars(machines):
    calendars = []

    start = datetime.strptime(START_DATE, "%Y-%m-%d")

    for machine in machines:
        for day in range(DAYS_TO_GENERATE):
            current_date = start + timedelta(days=day)

            for shift_number, (shift_start, shift_end) in enumerate(
                SHIFTS, start=1
            ):
                start_time = datetime.strptime(
                    f"{current_date.date()} {shift_start}",
                    "%Y-%m-%d %H:%M"
                )

                end_time = datetime.strptime(
                    f"{current_date.date()} {shift_end}",
                    "%Y-%m-%d %H:%M"
                )

                # Sundays are non-working days.
                working = current_date.weekday() != 6

                # Labelled maintenance downtime.
                maintenance = (
                    working and random.random() < 0.025
                )

                if maintenance:
                    working = False

                calendars.append({
                    "calendar_id": (
                        f"CAL-{machine['machine_id']}-"
                        f"{current_date.strftime('%Y%m%d')}-S{shift_number}"
                    ),
                    "machine_id": machine["machine_id"],
                    "shift_start": start_time.isoformat(),
                    "shift_end": end_time.isoformat(),
                    "available_minutes": (
                        random.choice([420, 430, 440, 450])
                        if working else 0
                    ),
                    "is_working": working,
                    "downtime_reason": (
                        "PLANNED_MAINTENANCE" if maintenance
                        else "NON_WORKING_DAY" if not working
                        else ""
                    )
                })

    export_csv("machine_calendars.csv", calendars)
    return calendars


                # --------------------------------------------------
                # 6. CHANGEOVER MATRIX
                # --------------------------------------------------

def generate_changeovers(machines):
    changeovers = []

    for machine in machines:
        for from_family in PRODUCT_FAMILIES:
            for to_family in PRODUCT_FAMILIES:

                # Same-family production needs less setup.
                setup = (
                    5 if from_family == to_family
                    else random.randint(15, 60)
                )

                changeovers.append({
                    "changeover_id": (
                        f"CO-{machine['machine_id']}-"
                        f"{PRODUCT_FAMILIES.index(from_family) + 1}-"
                        f"{PRODUCT_FAMILIES.index(to_family) + 1}"
                    ),
                    "machine_id": machine["machine_id"],
                    "from_family": from_family,
                    "to_family": to_family,
                    "setup_minutes": setup
                })

    export_csv("changeover_matrix.csv", changeovers)
    return changeovers


            # --------------------------------------------------
            # MAIN GENERATOR
            # --------------------------------------------------

if __name__ == "__main__":

    print("FORGEIQ: Generating manufacturing master data...")

    products = generate_products()

    machines = generate_machines()

    materials = generate_materials()

    routings, operations, eligibility, requirements = (
        generate_routings(products, machines, materials)
    )

    calendars = generate_calendars(machines)

    changeovers = generate_changeovers(machines)

    print("\nMASTER DATA GENERATION COMPLETE")
    print("--------------------------------")
    print("Products:", len(products))
    print("Machines:", len(machines))
    print("Materials:", len(materials))
    print("Routings:", len(routings))
    print("Routing operations:", len(operations))
    print("Machine eligibility:", len(eligibility))
    print("Material requirements:", len(requirements))
    print("Machine calendar entries:", len(calendars))
    print("Changeover records:", len(changeovers))
    print("--------------------------------")
    print("Random seed:", SEED)
    print("Output directory:", OUTPUT)
