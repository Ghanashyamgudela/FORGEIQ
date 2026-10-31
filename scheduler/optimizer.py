
from scheduler.data_loader import load_scheduling_data
from scheduler.scheduling_model import ForgeIQSchedulingModel


def main():

    data = load_scheduling_data()

    scheduling_model = ForgeIQSchedulingModel(data)

    prepared_operations = scheduling_model.prepare_data()

    print("\nSCHEDULER INITIALIZATION SUCCESSFUL")
    print("=" * 40)

    print("Prepared operations:", len(prepared_operations))
    print("Unique orders:", prepared_operations["order_id"].nunique())
    print("Unique machines:", data["machines"]["machine_id"].nunique())


if __name__ == "__main__":
    main()
