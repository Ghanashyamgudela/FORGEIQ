
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "raw"


def load_scheduling_data():

    required_files = {
        "orders": "production_orders.csv",
        "operations": "order_operations.csv",
        "machines": "machines.csv",
        "eligibility": "routing_machine_eligibility.csv",
        "calendars": "machine_calendars.csv",
        "materials": "materials.csv",
        "inventory": "inventory_lots.csv",
        "material_demand": "order_material_demand.csv",
        "changeovers": "changeover_matrix.csv",
        "products": "products.csv",
    }

    data = {}

    print("FORGEIQ DATA LOADER")
    print("=" * 40)

    for key, filename in required_files.items():

        file_path = DATA_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Required data file not found: {file_path}"
            )

        data[key] = pd.read_csv(file_path)

    for name, dataframe in data.items():
        print(f"{name:20} : {len(dataframe)} records")

    print("\nAll scheduling datasets loaded successfully.")
    print("\nDATASET COLUMN STRUCTURE")
    print("=" * 60)
    for name, dataframe in data.items():
        print(f"\n{name.upper()}")
        print(list(dataframe.columns))
        print(dataframe.head(2).to_string(index=False))

    return data


if __name__ == "__main__":
    load_scheduling_data()
