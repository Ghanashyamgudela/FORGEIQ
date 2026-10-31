
from scheduler.data_loader import load_scheduling_data
from scheduler.material_constraints import check_material_availability
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

print("\nFORGEIQ MATERIAL CONSTRAINT TEST")
print("=" * 45)

# Load generated datasets
data = load_scheduling_data()

# Load pilot schedule
schedule = pd.read_csv(
    PROCESSED / "pilot_schedule.csv"
)

# Run material validation
violations = check_material_availability(
    schedule,
    data["material_demand"],
    data["inventory"]
)

print("\nMATERIAL VALIDATION RESULTS")
print("-" * 45)

if violations.empty:
    print("No material violations detected.")
else:
    print("Material violations:", len(violations))
    print(violations.to_string(index=False))

    print("\nTEST COMPLETED")
print("\nMATERIAL QUANTITY TYPES")
print(data["material_demand"]["required_quantity"].dtype)
print(data["inventory"]["quantity"].dtype)
print(data["inventory"]["reserved_quantity"].dtype)

print("\nSAMPLE MATERIAL DEMANDS")
print(data["material_demand"][[
    "operation_id", "material_id", "required_quantity"
]].head())

print("\nSAMPLE INVENTORY")
print(data["inventory"][[
    "material_id", "quantity", "reserved_quantity",
    "available_at", "quality_status"
]].head())