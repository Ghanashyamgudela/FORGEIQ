
from pathlib import Path

import pandas as pd

from scheduler.data_loader import load_scheduling_data


ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
VIOLATION_COLUMNS = [
    "machine_id",
    "previous_operation",
    "next_operation",
    "from_family",
    "to_family",
    "required_setup",
    "available_gap",
    "issue",
]


def validate_changeovers():

    print("\nFORGEIQ CHANGEOVER VALIDATION")
    print("=" * 50)

    # Load datasets
    data = load_scheduling_data()
    print("\nDEBUG: Data loading completed.")

    schedule = pd.read_csv("data/processed/pilot_schedule.csv")
    print("DEBUG: Pilot schedule loaded:", len(schedule), "operations")

    print("DEBUG: Starting product family mapping...")

    schedule = pd.read_csv(
        "data/processed/pilot_schedule.csv"
    )

    orders = data["orders"]
    products = data["products"]
    changeovers = data["changeovers"]

    # --------------------------------------------------
    # 1. Connect each scheduled operation to its product family
    # --------------------------------------------------

    order_products = orders[
        ["order_id", "product_id"]
    ].drop_duplicates()

    product_families = products[
        ["product_id", "family"]
    ].drop_duplicates()

    if "product_id" not in schedule.columns:
        schedule = schedule.merge(
            order_products,
            on="order_id",
            how="left"
        )

    if "family" not in schedule.columns:
        schedule = schedule.merge(
            product_families,
            on="product_id",
            how="left"
        )

    if schedule["family"].isna().any():
        raise ValueError(
            "Some scheduled operations have no product family."
        )

    print("DEBUG: Product family mapping completed.")
    print("DEBUG: Starting changeover lookup...")

    # --------------------------------------------------
    # 2. Build changeover lookup
    # --------------------------------------------------

    changeover_lookup = {
        (
            row.machine_id,
            row.from_family,
            row.to_family
        ): int(row.setup_minutes)

        for row in changeovers.itertuples(index=False)
    }
    print(
        "DEBUG: Changeover lookup created:",
        len(changeover_lookup),
        "records",
    )

    # Convert schedule timestamps
    schedule["start_time"] = pd.to_datetime(
        schedule["start_time"]
    )

    schedule["end_time"] = pd.to_datetime(
        schedule["end_time"]
    )

    # --------------------------------------------------
    # 3. Check consecutive operations on each machine
    # --------------------------------------------------

    violations = []
    transitions_checked = 0

    for machine_id, machine_schedule in schedule.groupby(
        "machine_id"
    ):

        machine_schedule = machine_schedule.sort_values(
            "start_time"
        ).reset_index(drop=True)

        for index in range(len(machine_schedule) - 1):

            previous = machine_schedule.iloc[index]
            current = machine_schedule.iloc[index + 1]

            from_family = previous["family"]
            to_family = current["family"]

            lookup_key = (
                machine_id,
                from_family,
                to_family
            )

            if lookup_key not in changeover_lookup:

                violations.append({
                    "machine_id": machine_id,
                    "previous_operation": previous["operation_id"],
                    "next_operation": current["operation_id"],
                    "from_family": from_family,
                    "to_family": to_family,
                    "required_setup": None,
                    "available_gap": None,
                    "issue": "MISSING_CHANGEOVER_DATA"
                })

                continue

            required_setup = changeover_lookup[lookup_key]

            available_gap = (
                current["start_time"] - previous["end_time"]
            ).total_seconds() / 60

            transitions_checked += 1

            if available_gap < required_setup:

                violations.append({
                    "machine_id": machine_id,
                    "previous_operation": previous["operation_id"],
                    "next_operation": current["operation_id"],
                    "from_family": from_family,
                    "to_family": to_family,
                    "required_setup": required_setup,
                    "available_gap": round(available_gap, 2),
                    "issue": "INSUFFICIENT_CHANGEOVER_TIME"
                })

    # --------------------------------------------------
    # 4. Display results
    # --------------------------------------------------
    print("\nCHANGEOVER VALIDATION RESULTS")
    print("-" * 50)
    print("Scheduled operations:", len(schedule))
    print("Machine transitions checked:", transitions_checked)
    print("Changeover violations:", len(violations))

    if violations:
        print("\nVIOLATIONS FOUND")
        print("-" * 50)
        for violation in violations:
            print(violation)
    else:
        print("\nNo changeover violations detected.")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    report_path = PROCESSED / "changeover_violations.csv"
    pd.DataFrame(violations, columns=VIOLATION_COLUMNS).to_csv(
        report_path,
        index=False,
    )
    print("\nChangeover report saved to", report_path)
    print("\nVALIDATION COMPLETE")



if __name__ == "__main__":
    validate_changeovers()
