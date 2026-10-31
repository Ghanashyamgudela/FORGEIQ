
from pathlib import Path

import pandas as pd

from scheduler.data_loader import load_scheduling_data


ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
VIOLATION_COLUMNS = [
    "operation_id",
    "material_id",
    "issue_type",
    "required_quantity",
    "available_quantity",
    "explanation",
]


def check_material_availability(
    schedule,
    material_demand,
    inventory
):
    """
    Validate material availability and allocate inventory
    chronologically across scheduled operations.
    """

    schedule = schedule.copy()
    demand = material_demand.copy()
    stock = inventory.copy()

    schedule["start_time"] = pd.to_datetime(
        schedule["start_time"]
    )

    stock["available_at"] = pd.to_datetime(
        stock["available_at"]
    )

    stock["quantity"] = pd.to_numeric(
        stock["quantity"], errors="coerce"
    ).fillna(0)

    stock["reserved_quantity"] = pd.to_numeric(
        stock["reserved_quantity"], errors="coerce"
    ).fillna(0)

    demand["required_quantity"] = pd.to_numeric(
        demand["required_quantity"], errors="coerce"
    ).fillna(0)

    # Combine duplicate requirements for the same operation/material.
    demand = demand.groupby(
        ["operation_id", "material_id"],
        as_index=False
    )["required_quantity"].sum()

    # Attach material requirements to scheduled operations.
    requirements = schedule.merge(
        demand,
        on="operation_id",
        how="left"
    )

    requirements = requirements.dropna(
        subset=["material_id"]
    )

    requirements = requirements.sort_values(
        "start_time"
    )

    # Calculate remaining stock for every inventory lot.
    stock["remaining_quantity"] = (
        stock["quantity"] - stock["reserved_quantity"]
    ).clip(lower=0)

    stock["quality_status"] = (
        stock["quality_status"].astype(str).str.upper()
    )

    violations = []

    for row in requirements.itertuples(index=False):

        material_id = row.material_id
        required = row.required_quantity
        start_time = row.start_time

        lots = stock[
            stock["material_id"] == material_id
        ]

        if lots.empty:
            violations.append({
                "operation_id": row.operation_id,
                "material_id": material_id,
                "issue_type": "NO_INVENTORY_LOT",
                "required_quantity": required,
                "available_quantity": 0,
                "explanation": "No inventory lot exists."
            })
            continue

        # Only released or approved lots can be consumed.
        released_lots = lots[
            lots["quality_status"].isin(
                ["RELEASED", "APPROVED"]
            )
        ]

        if released_lots.empty:
            violations.append({
                "operation_id": row.operation_id,
                "material_id": material_id,
                "issue_type": "MATERIAL_NOT_RELEASED",
                "required_quantity": required,
                "available_quantity": 0,
                "explanation": "No quality-released inventory exists."
            })
            continue

        # Inventory that has arrived by operation start.
        available_lots = released_lots[
            (released_lots["available_at"] <= start_time) &
            (released_lots["remaining_quantity"] > 0)
        ].sort_values("available_at")

        available_quantity = available_lots[
            "remaining_quantity"
        ].sum()

        total_released_quantity = released_lots[
            "remaining_quantity"
        ].sum()

        # Determine whether the shortage is caused by late arrival.
        if available_quantity < required:
            if total_released_quantity >= required:
                issue_type = "MATERIAL_NOT_AVAILABLE"
                explanation = (
                    "Sufficient stock exists, but some material "
                    "has not arrived by operation start."
                )
            else:
                issue_type = "INSUFFICIENT_MATERIAL"
                explanation = (
                    "Total remaining released inventory is "
                    "insufficient for this requirement."
                )

            violations.append({
                "operation_id": row.operation_id,
                "material_id": material_id,
                "issue_type": issue_type,
                "required_quantity": required,
                "available_quantity": available_quantity,
                "explanation": explanation
            })

            # Do not reserve partial stock for a failed requirement.
            continue

        # Allocate stock across lots in arrival order.
        remaining_required = required

        for lot_index in available_lots.index:
            if remaining_required <= 0:
                break

            lot_available = stock.at[
                lot_index, "remaining_quantity"
            ]
            allocated = min(lot_available, remaining_required)

            stock.at[
                lot_index, "remaining_quantity"
            ] -= allocated
            remaining_required -= allocated

    return pd.DataFrame(violations, columns=VIOLATION_COLUMNS)


if __name__ == "__main__":
    print("FORGEIQ MATERIAL CONSTRAINT VALIDATION")
    print("=" * 45)
    data = load_scheduling_data()
    schedule = pd.read_csv(PROCESSED / "pilot_schedule.csv")
    violations = check_material_availability(
        schedule,
        data["material_demand"],
        data["inventory"],
    )
    PROCESSED.mkdir(parents=True, exist_ok=True)
    output_path = PROCESSED / "material_violations.csv"
    violations.to_csv(output_path, index=False)
    print("Material violations:", len(violations))
    print("Material validation report saved:", output_path)
