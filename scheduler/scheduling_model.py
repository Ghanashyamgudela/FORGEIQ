
from ortools.sat.python import cp_model


class ForgeIQSchedulingModel:

    def __init__(self, data):
        self.data = data
        self.model = cp_model.CpModel()

        self.operations = data["operations"]
        self.orders = data["orders"]
        self.machines = data["machines"]
        self.products = data["products"]
        self.eligibility = data["eligibility"]
        self.calendars = data["calendars"]

        self.start_vars = {}
        self.end_vars = {}
        self.machine_vars = {}
        self.interval_vars = {}

        print("FORGEIQ SCHEDULING MODEL")
        print("=" * 40)
        print("Operations:", len(self.operations))
        print("Machines:", len(self.machines))
        print("Products:", len(self.products))

    def prepare_data(self):
        print("\nPreparing scheduling data...")
        self.operations = self.operations.merge(
            self.orders[["order_id", "product_id", "priority", "due_date"]],
            on="order_id",
            how="left",
        )
        self.operations = self.operations.merge(
            self.products[["product_id", "family"]],
            on="product_id",
            how="left",
        )
        print("Operations enriched with order and product information.")
        print("Product families:", self.operations["family"].nunique())

        print("\nMACHINE ELIGIBILITY CHECK")
        print("=" * 40)

        eligibility_counts = self.eligibility.groupby(
            "operation_id"
        )["machine_id"].nunique()

        print("Routing operations with eligible machines:",
              len(eligibility_counts))

        print("Minimum eligible machines:",
              eligibility_counts.min())

        print("Maximum eligible machines:",
              eligibility_counts.max())

        print("\nRequired machine types:")
        print(self.operations["required_machine_type"].value_counts())

        print("\nAvailable machine types:")
        print(self.machines["machine_type"].value_counts())

        print("\nData preparation completed.")

        return self.operations
