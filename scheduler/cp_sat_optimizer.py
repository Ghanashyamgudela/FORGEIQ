
import pandas as pd
from pathlib import Path
from datetime import timedelta
from ortools.sat.python import cp_model

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

PILOT_ORDER_COUNT = 20
SOLVER_TIME_LIMIT = 300


def load_data():
    return {
        "orders": pd.read_csv(RAW / "production_orders.csv"),
        "operations": pd.read_csv(RAW / "order_operations.csv"),
        "machines": pd.read_csv(RAW / "machines.csv"),
        "eligibility": pd.read_csv(
            RAW / "routing_machine_eligibility.csv"
        ),
        "calendars": pd.read_csv(
            RAW / "machine_calendars.csv"
        ),
        "labor_calendars": pd.read_csv(
            RAW / "labor_calendars.csv"
        ),
        "material_demand": pd.read_csv(
            RAW / "order_material_demand.csv"
        ),
        "inventory": pd.read_csv(
            RAW / "inventory_lots.csv"
        ),
        "changeovers": pd.read_csv(
            RAW / "changeover_matrix.csv"
        ),
        "products": pd.read_csv(
            RAW / "products.csv"
        ),
    }



def calculate_material_ready_times(operations, material_demand, inventory):
    """
    Allocate released inventory chronologically across operations.

    Returns the earliest material-ready timestamp for each operation.
    Each inventory lot can only be allocated once.
    """

    demand = material_demand.copy()
    stock = inventory.copy()

    # Convert columns to correct data types
    stock["available_at"] = pd.to_datetime(stock["available_at"])
    stock["quantity"] = pd.to_numeric(
        stock["quantity"], errors="coerce"
    ).fillna(0)

    stock["reserved_quantity"] = pd.to_numeric(
        stock["reserved_quantity"], errors="coerce"
    ).fillna(0)

    demand["required_quantity"] = pd.to_numeric(
        demand["required_quantity"], errors="coerce"
    ).fillna(0)

    # Keep only released or approved inventory
    stock["quality_status"] = (
        stock["quality_status"].astype(str).str.upper()
    )

    stock["remaining_quantity"] = (
        stock["quantity"] - stock["reserved_quantity"]
    ).clip(lower=0)

    stock = stock[
        stock["quality_status"].isin(["RELEASED", "APPROVED"])
    ].copy()

    # Keep only operations included in this scheduling run
    operation_ids = set(operations["operation_id"])

    demand = demand[
        demand["operation_id"].isin(operation_ids)
    ]

    # Combine duplicate material requirements
    demand = demand.groupby(
        ["operation_id", "material_id"],
        as_index=False
    )["required_quantity"].sum()

    # Determine chronological operation order
    operation_order = operations[
        ["operation_id", "order_id", "sequence_number"]
    ].copy()

    operation_order = operation_order.drop_duplicates(
        subset=["operation_id"]
    )

    operation_order["order_id"] = operation_order["order_id"].astype(str)

    demand = demand.merge(
        operation_order,
        on="operation_id",
        how="left"
    )

    # Sort by operation sequence, then operation ID
    demand = demand.sort_values(
        ["order_id", "sequence_number", "operation_id", "material_id"]
    )

    # Track shared inventory balances
    ready_times = {}

    for requirement in demand.itertuples(index=False):

        required_quantity = requirement.required_quantity

        if required_quantity <= 0:
            continue

        operation_id = requirement.operation_id
        material_id = requirement.material_id

        material_lots = stock[
            stock["material_id"] == material_id
        ].sort_values("available_at")

        if material_lots.empty:
            raise ValueError(
                f"No released inventory for material {material_id} "
                f"required by {operation_id}"
            )

        remaining_requirement = required_quantity
        material_ready_time = None

        # Allocate from shared stock, earliest available lot first
        for lot_index in material_lots.index:

            available_quantity = stock.at[
                lot_index, "remaining_quantity"
            ]

            if available_quantity <= 0:
                continue

            allocated_quantity = min(
                available_quantity,
                remaining_requirement
            )

            stock.at[lot_index, "remaining_quantity"] -= allocated_quantity

            remaining_requirement -= allocated_quantity

            lot_ready_time = stock.at[lot_index, "available_at"]
            if material_ready_time is None:
                material_ready_time = lot_ready_time
            else:
                material_ready_time = max(
                    material_ready_time,
                    lot_ready_time,
                )

                if remaining_requirement <= 0:
                    break

                if remaining_requirement > 0:
                    raise ValueError(
                        f"Insufficient shared inventory for material {material_id} "
                        f"required by {operation_id}. "
                        f"Shortage: {remaining_requirement}"
                    )

                # An operation must wait for all its required materials.
                if operation_id not in ready_times:
                    ready_times[operation_id] = material_ready_time
                else:
                    ready_times[operation_id] = max(
                        ready_times[operation_id],
                        material_ready_time,
                    )

                    return ready_times

def add_material_inventory_constraints(
    model,
    operations,
    start_vars,
    material_demand,
    inventory,
    origin,
):
    """Enforce chronological material inventory availability."""
    scale = 100
    pilot_operation_ids = set(operations["operation_id"])
    demand = material_demand[
        material_demand["operation_id"].isin(pilot_operation_ids)
    ].copy()
    stock = inventory.copy()
    stock["quality_status"] = stock["quality_status"].astype(str).str.upper().str.strip()
    stock = stock[
        stock["quality_status"].isin(["RELEASED", "APPROVED"])
    ].copy()
    stock["available_at"] = pd.to_datetime(stock["available_at"])
    stock["quantity"] = pd.to_numeric(
        stock["quantity"], errors="coerce"
    ).fillna(0)
    stock["reserved_quantity"] = pd.to_numeric(
        stock["reserved_quantity"], errors="coerce"
    ).fillna(0)
    stock["remaining_quantity"] = (
        stock["quantity"] - stock["reserved_quantity"]
    ).clip(lower=0)
    demand["required_quantity"] = pd.to_numeric(
        demand["required_quantity"], errors="coerce"
    ).fillna(0)
    demand = demand.groupby(
        ["operation_id", "material_id"],
        as_index=False
    )["required_quantity"].sum()

    for material_id in demand["material_id"].dropna().unique():
        material_demand_rows = demand[demand["material_id"] == material_id]
        material_stock_rows = stock[
            (stock["material_id"] == material_id)
            & (stock["remaining_quantity"] > 0)
        ]
        times = []
        level_changes = []
        for requirement in material_demand_rows.itertuples(index=False):
            quantity = int(round(requirement.required_quantity * scale))
            if quantity <= 0:
                continue
            times.append(start_vars[requirement.operation_id])
            level_changes.append(-quantity)

        for lot in material_stock_rows.itertuples(index=False):
            quantity = int(round(lot.remaining_quantity * scale))
            if quantity <= 0:
                continue
            arrival_minute = int(
                (lot.available_at - origin).total_seconds() // 60
            )
            times.append(max(0, arrival_minute))
            level_changes.append(quantity)

        total_supply = sum(change for change in level_changes if change > 0)
        total_demand = -sum(change for change in level_changes if change < 0)
        if total_supply < total_demand:
            raise ValueError(
                f"Insufficient inventory for {material_id}. "
                f"Required: {total_demand / scale}, "
                f"Available: {total_supply / scale}"
            )

        if times:
            model.AddReservoirConstraint(
                times,
                level_changes,
                0,
                total_supply,
            )
def _legacy_build_and_solve(data):

    model = cp_model.CpModel()

    # --------------------------------------------------
    # 1. SELECT PILOT ORDERS AND OPERATIONS
    # --------------------------------------------------

    orders = data["orders"].head(PILOT_ORDER_COUNT)

    selected_order_ids = orders["order_id"].tolist()

    operations = data["operations"][
        data["operations"]["order_id"].isin(selected_order_ids)
    ].copy().reset_index(drop=True)

    # Attach product family to every operation.
    order_products = orders[
        ["order_id", "product_id"]
    ].drop_duplicates()

    product_families = data["products"][
        ["product_id", "family"]
    ].drop_duplicates()

    operations = operations.merge(
        order_products,
        on="order_id",
        how="left"
    )

    operations = operations.merge(
        product_families,
        on="product_id",
        how="left"
    )

    if operations["family"].isna().any():
        missing = operations[
            operations["family"].isna()
        ]["operation_id"].tolist()

        raise ValueError(
            f"Missing product family for operations: {missing}"
        )

    print("Product families connected:", operations["family"].nunique())

    print("Operation family mapping:")
    print(
        operations[
            ["operation_id", "product_id", "family"]
        ].head(20).to_string(index=False)
    )

    eligibility = data["eligibility"]
    calendars = data["calendars"].copy()

    # --------------------------------------------------
    # 2. PREPARE MACHINE CALENDARS
    # --------------------------------------------------

    calendars["shift_start"] = pd.to_datetime(
        calendars["shift_start"]
    )

    calendars["shift_end"] = pd.to_datetime(
        calendars["shift_end"]
    )

    calendars["is_working"] = calendars[
        "is_working"
    ].astype(str).str.lower().isin(["true", "1", "yes"])

    calendars["available_minutes"] = calendars[
        "available_minutes"
    ].astype(int)

    working_calendars = calendars[
        calendars["is_working"]
        & (calendars["available_minutes"] > 0)
    ].copy()

    origin = calendars["shift_start"].min()

    horizon = int(
        (calendars["shift_end"].max() - origin).total_seconds()
        // 60
    )

    # --------------------------------------------------
    # 3. BUILD MACHINE ELIGIBILITY LOOKUP
    # --------------------------------------------------

    eligible_machines = (
        eligibility.groupby("operation_id")["machine_id"]
        .apply(lambda values: values.unique().tolist())
        .to_dict()
    )

    machine_shifts = {
        machine_id: group.to_dict("records")
        for machine_id, group in working_calendars.groupby("machine_id")
    }

    # --------------------------------------------------
    # 4. INITIALIZE MODEL VARIABLES
    # --------------------------------------------------

    start_vars = {}
    end_vars = {}
    assignment_vars = {}
    assignment_details = {}
    candidate_trace = []
    machine_intervals = {}
    shift_assignments = {}
    labor_assignments = {}
    candidate_count = 0
    missing_candidates = []

    # --------------------------------------------------
    # 5. CREATE OPERATION AND MACHINE ASSIGNMENTS
    # --------------------------------------------------

    for row in operations.itertuples(index=False):

        operation_id = row.operation_id
        duration = int(row.duration_minutes)

        start = model.NewIntVar(
            0,
            horizon,
            f"start_{operation_id}"
        )

        end = model.NewIntVar(
            0,
            horizon,
            f"end_{operation_id}"
        )

        model.Add(end == start + duration)

        start_vars[operation_id] = start
        end_vars[operation_id] = end

        # Eligibility uses routing_operation_id.
        eligible = eligible_machines.get(
            row.routing_operation_id,
            []
        )

        operation_candidates = []

        for machine_id in eligible:

            for shift in machine_shifts.get(machine_id, []):

                available = int(shift["available_minutes"])

                if duration > available:
                    continue

                shift_start = int(
                    (shift["shift_start"] - origin).total_seconds()
                    // 60
                )

                shift_end = int(
                    (shift["shift_end"] - origin).total_seconds()
                    // 60
                )

                if shift_end - shift_start < duration:
                    continue

                presence = model.NewBoolVar(
                    f"assign_{operation_id}_{machine_id}_"
                    f"{shift['calendar_id']}"
                )

                interval = model.NewOptionalIntervalVar(
                    start,
                    duration,
                    end,
                    presence,
                    f"interval_{operation_id}_{machine_id}_"
                    f"{shift['calendar_id']}"
                )

                model.Add(
                    start >= shift_start
                ).OnlyEnforceIf(presence)

                model.Add(
                    start <= shift_end - duration
                ).OnlyEnforceIf(presence)

                assignment_key = (
                    operation_id,
                    candidate_count
                )

                assignment_vars[assignment_key] = presence

                assignment_details[assignment_key] = {
                    "machine_id": machine_id,
                    "calendar_id": shift["calendar_id"],
                    "shift_start": shift["shift_start"],
                    "shift_end": shift["shift_end"],
                }

                operation_candidates.append(presence)

                machine_intervals.setdefault(
                    machine_id, []
                ).append(interval)

                shift_key = (
                    machine_id,
                    shift["calendar_id"]
                )

                shift_assignments.setdefault(
                    shift_key, []
                ).append(
                    (duration, presence, available)
                )

                candidate_count += 1

                # Exactly one machine/shift must be selected per operation.
                if not operation_candidates:

                    missing_candidates.append(operation_id)

                else:

                    model.Add(
                        sum(operation_candidates) == 1
                    )

                    if missing_candidates:

                        raise ValueError(
                            "Operations without valid machine/shift candidates: "
                            + ", ".join(missing_candidates)
                        )

                    # --------------------------------------------------
                    # 6. ADD MATERIAL INVENTORY CONSTRAINTS
                    # --------------------------------------------------

                    add_material_inventory_constraints(
                        model,
                        operations,
                        start_vars,
                        data["material_demand"],
                        data["inventory"],
                        origin,
                    )

                    # --------------------------------------------------
                    # 7. ADD MACHINE NON-OVERLAP CONSTRAINTS
                    # --------------------------------------------------

                    for machine_id, intervals in machine_intervals.items():

                        model.AddNoOverlap(intervals)

                        # --------------------------------------------------
                        # 8. ADD SHIFT CAPACITY CONSTRAINTS
                        # --------------------------------------------------

                        for shift_key, assignments in shift_assignments.items():

                            available = assignments[0][2]

                            model.Add(
                                sum(
                                    duration * presence
                                    for duration, presence, _ in assignments
                                ) <= available
                            )

                            # --------------------------------------------------
                            # 9. ADD OPERATION PRECEDENCE CONSTRAINTS
                            # --------------------------------------------------

                            operation_ids = set(operations["operation_id"])

                            for row in operations.itertuples(index=False):

                                predecessor = row.predecessor_operation_id

                                if (
                                    pd.notna(predecessor)
                                    and predecessor in operation_ids
                                ):

                                    model.Add(
                                        end_vars[predecessor]
                                        <= start_vars[row.operation_id]
                                    )

                                    # --------------------------------------------------
                                    # 10. MINIMIZE MAKESPAN
                                    # --------------------------------------------------

                                    makespan = model.NewIntVar(
                                        0,
                                        horizon,
                                        "makespan"
                                    )

                                    model.AddMaxEquality(
                                        makespan,
                                        list(end_vars.values())
                                    )

                                    model.Minimize(makespan)

                                    # --------------------------------------------------
                                    # 11. DISPLAY MODEL SUMMARY
                                    # --------------------------------------------------

                                    print("\nBUILDING CP-SAT MODEL")
                                    print("=" * 45)

                                    print("Pilot orders:", len(selected_order_ids))
                                    print("Pilot operations:", len(operations))
                                    print("Candidate assignments:", candidate_count)
                                    print("Machines with working calendars:", len(machine_shifts))
                                    print("Shift capacity constraints:", len(shift_assignments))
                                    print("Machine non-overlap constraints:", len(machine_intervals))

                                    # --------------------------------------------------
                                    # 12. SOLVE MODEL
                                    # --------------------------------------------------

                                    print("\nSolving model...")

                                    solver = cp_model.CpSolver()

                                    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT
                                    solver.parameters.num_search_workers = 8
                                    solver.parameters.log_search_progress = True

                                    status = solver.Solve(model)

                                    print("\nSOLVER RESULT")
                                    print("=" * 45)

                                    print("Status:", solver.StatusName(status))

                                    if status not in (
                                        cp_model.OPTIMAL,
                                        cp_model.FEASIBLE
                                    ):

                                        print("No feasible pilot schedule was found.")
                                        return

                                    print(
                                        "Objective makespan:",
                                        solver.Value(makespan),
                                        "minutes"
                                    )

                                    print(
                                        "Solver time:",
                                        round(solver.WallTime(), 2),
                                        "seconds"
                                    )

                                    # --------------------------------------------------
                                    # 13. EXTRACT SCHEDULE RESULTS
                                    # --------------------------------------------------

                                    results = []

                                    for row in operations.itertuples(index=False):

                                        operation_id = row.operation_id

                                        selected_assignment = next(
                                            (
                                                assignment_details[key]
                                                for key, presence in assignment_vars.items()
                                                if (
                                                    key[0] == operation_id
                                                    and solver.Value(presence) == 1
                                                )
                                            ),
                                            None,
                                        )

                                        if selected_assignment is None:

                                            raise ValueError(
                                                f"No selected machine found for {operation_id}"
                                            )

                                        results.append({

                                            "operation_id": operation_id,
                                            "order_id": row.order_id,
                                            "product_id": row.product_id,
                                            "family": row.family,

                                            "routing_operation_id": row.routing_operation_id,

                                            "machine_id": selected_assignment["machine_id"],
                                            "calendar_id": selected_assignment["calendar_id"],

                                            "shift_start": selected_assignment["shift_start"],
                                            "shift_end": selected_assignment["shift_end"],

                                            "duration_minutes": int(row.duration_minutes),

                                            "start_time": (
                                                origin
                                                + timedelta(
                                                    minutes=solver.Value(start_vars[operation_id])
                                                )
                                            ).isoformat(),

                                            "end_time": (
                                                origin
                                                + timedelta(
                                                    minutes=solver.Value(end_vars[operation_id])
                                                )
                                            ).isoformat(),

                                            "status": "SCHEDULED",
                                        })

                                        # --------------------------------------------------
                                        # 14. SAVE PILOT SCHEDULE
                                        # --------------------------------------------------

                                        PROCESSED.mkdir(
                                            parents=True,
                                            exist_ok=True
                                        )

                                        output_path = PROCESSED / "pilot_schedule.csv"

                                        schedule_df = pd.DataFrame(results)

                                        schedule_df.to_csv(
                                            output_path,
                                            index=False
                                        )

                                        print("\nPilot schedule saved:", output_path)
                                        print("Scheduled operations:", len(schedule_df))


def _pairwise_build_and_solve(data):
    model = cp_model.CpModel()

    orders = data["orders"].head(PILOT_ORDER_COUNT)
    selected_order_ids = orders["order_id"].tolist()
    operations = data["operations"][
        data["operations"]["order_id"].isin(selected_order_ids)
    ].copy().reset_index(drop=True)

    order_products = orders[["order_id", "product_id"]].drop_duplicates()
    product_families = data["products"][
        ["product_id", "family"]
    ].drop_duplicates()
    operations = operations.merge(
        order_products,
        on="order_id",
        how="left",
    ).merge(
        product_families,
        on="product_id",
        how="left",
    )
    if operations["family"].isna().any():
        missing_operations = operations.loc[
            operations["family"].isna(), "operation_id"
        ].tolist()
        raise ValueError(
            f"Missing product family for operations: {missing_operations}"
        )

    eligibility = data["eligibility"]
    calendars = data["calendars"].copy()
    calendars["shift_start"] = pd.to_datetime(calendars["shift_start"])
    calendars["shift_end"] = pd.to_datetime(calendars["shift_end"])
    calendars["is_working"] = calendars["is_working"].astype(str).str.lower().isin(
        ["true", "1", "yes"]
    )
    calendars["available_minutes"] = calendars["available_minutes"].astype(int)
    working_calendars = calendars[
        calendars["is_working"] & (calendars["available_minutes"] > 0)
    ].copy()
    origin = calendars["shift_start"].min()
    horizon = int(
        (calendars["shift_end"].max() - origin).total_seconds() // 60
    )

    eligible_machines = (
        eligibility.groupby("operation_id")["machine_id"]
        .apply(lambda values: values.unique().tolist())
        .to_dict()
    )
    machine_shifts = {
        machine_id: group.to_dict("records")
        for machine_id, group in working_calendars.groupby("machine_id")
    }

    print("\nBUILDING CP-SAT MODEL")
    print("=" * 45)
    print("Pilot orders:", len(selected_order_ids))
    print("Pilot operations:", len(operations))

    start_vars = {}
    end_vars = {}
    assignment_vars = {}
    assignment_details = {}
    machine_intervals = {}
    shift_assignments = {}
    candidate_count = 0
    missing_candidates = []

    for row in operations.itertuples(index=False):
        operation_id = row.operation_id
        duration = int(row.duration_minutes)
        start = model.NewIntVar(0, horizon, f"start_{operation_id}")
        end = model.NewIntVar(0, horizon, f"end_{operation_id}")
        model.Add(end == start + duration)
        start_vars[operation_id] = start
        end_vars[operation_id] = end
        operation_candidates = []

        for machine_id in eligible_machines.get(row.routing_operation_id, []):
            for shift in machine_shifts.get(machine_id, []):
                available = int(shift["available_minutes"])
                if duration > available:
                    continue
                shift_start = int(
                    (shift["shift_start"] - origin).total_seconds() // 60
                )
                shift_end = int(
                    (shift["shift_end"] - origin).total_seconds() // 60
                )
                if shift_end - shift_start < duration:
                    candidate_trace.append({
                        "operation_id": operation_id,
                        "order_id": row.order_id,
                        "routing_operation_id": row.routing_operation_id,
                        "machine_id": machine_id,
                        "calendar_id": shift["calendar_id"],
                        "duration_minutes": duration,
                        "available_minutes": available,
                        "candidate_status": "REJECTED",
                        "reason": (
                            "Operation duration exceeds the time "
                            "span of this shift."
                        ),
                    })
                    continue

                presence = model.NewBoolVar(
                    f"assign_{operation_id}_{machine_id}_"
                    f"{shift['calendar_id']}"
                )
                interval = model.NewOptionalIntervalVar(
                    start,
                    duration,
                    end,
                    presence,
                    f"interval_{operation_id}_{machine_id}_"
                    f"{shift['calendar_id']}",
                )
                model.Add(start >= shift_start).OnlyEnforceIf(presence)
                model.Add(start <= shift_end - duration).OnlyEnforceIf(presence)

                assignment_key = (operation_id, candidate_count)
                assignment_vars[assignment_key] = presence
                assignment_details[assignment_key] = {
                    "machine_id": machine_id,
                    "calendar_id": shift["calendar_id"],
                    "shift_start": shift["shift_start"],
                    "shift_end": shift["shift_end"],
                }
                candidate_trace.append({
                    "operation_id": operation_id,
                    "order_id": row.order_id,
                    "routing_operation_id": row.routing_operation_id,
                    "machine_id": machine_id,
                    "calendar_id": shift["calendar_id"],
                    "duration_minutes": duration,
                    "available_minutes": available,
                    "candidate_status": "CANDIDATE",
                    "reason": (
                        "Eligible machine and working shift; "
                        "operation duration fits available capacity."
                    ),
                })
                operation_candidates.append(presence)
                machine_intervals.setdefault(machine_id, []).append(interval)
                shift_key = (machine_id, shift["calendar_id"])
                shift_assignments.setdefault(shift_key, []).append(
                    (duration, presence, available)
                )
                candidate_count += 1

                if not operation_candidates:
                    missing_candidates.append(operation_id)
                else:
                    model.Add(sum(operation_candidates) == 1)

                    if missing_candidates:
                        raise ValueError(
                            "Operations without valid machine/shift candidates: "
                            + ", ".join(missing_candidates)
                        )

                    add_material_inventory_constraints(
                        model,
                        operations,
                        start_vars,
                        data["material_demand"],
                        data["inventory"],
                        origin,
                    )

                    # 7. ADD MACHINE NON-OVERLAP CONSTRAINTS
                    for intervals in machine_intervals.values():
                        model.AddNoOverlap(intervals)

                        # --------------------------------------------------
                        # 8. ADD SEQUENCE-DEPENDENT CHANGEOVER CONSTRAINTS
                        # --------------------------------------------------
                        changeover_lookup = {
                            (row.machine_id, row.from_family, row.to_family): int(row.setup_minutes)
                            for row in data["changeovers"].itertuples(index=False)
                        }
                        operation_families = dict(
                            zip(operations["operation_id"], operations["family"])
                        )
                        for machine_id in machine_intervals:
                            machine_operations = {}
                            for key, presence in assignment_vars.items():
                                if assignment_details[key]["machine_id"] == machine_id:
                                    machine_operations.setdefault(key[0], []).append(presence)

                                    machine_operation_presence = {}
                                    for operation_id, candidates in machine_operations.items():
                                        assigned_to_machine = model.NewBoolVar(
                                            f"uses_{operation_id}_{machine_id}"
                                        )
                                        model.Add(sum(candidates) == assigned_to_machine)
                                        machine_operation_presence[operation_id] = assigned_to_machine

                                        operation_ids_on_machine = list(machine_operation_presence)
                                        for first_index, first_operation in enumerate(operation_ids_on_machine):
                                            for second_operation in operation_ids_on_machine[first_index + 1:]:
                                                first_family = operation_families[first_operation]
                                                second_family = operation_families[second_operation]
                                                first_to_second = changeover_lookup.get(
                                                    (machine_id, first_family, second_family), 0
                                                )
                                                second_to_first = changeover_lookup.get(
                                                    (machine_id, second_family, first_family), 0
                                                )
                                                first_presence = machine_operation_presence[first_operation]
                                                second_presence = machine_operation_presence[second_operation]
                                                first_before_second = model.NewBoolVar(
                                                    f"order_{first_operation}_{second_operation}_{machine_id}"
                                                )
                                                model.Add(
                                                    start_vars[second_operation]
                                                    >= end_vars[first_operation] + first_to_second
                                                ).OnlyEnforceIf(
                                                    [first_presence, second_presence, first_before_second]
                                                )
                                                model.Add(
                                                    start_vars[first_operation]
                                                    >= end_vars[second_operation] + second_to_first
                                                ).OnlyEnforceIf(
                                                    [first_presence, second_presence, first_before_second.Not()]
                                                )

                                                for assignments in shift_assignments.values():
                                                    available = assignments[0][2]
                                                    model.Add(
                                                        sum(duration * presence for duration, presence, _ in assignments)
                                                        <= available
                                                    )

                                                    operation_ids = set(operations["operation_id"])
                                                    for row in operations.itertuples(index=False):
                                                        predecessor = row.predecessor_operation_id
                                                        if pd.notna(predecessor) and predecessor in operation_ids:
                                                            model.Add(end_vars[predecessor] <= start_vars[row.operation_id])

                                                            makespan = model.NewIntVar(0, horizon, "makespan")
                                                            model.AddMaxEquality(makespan, list(end_vars.values()))
                                                            model.Minimize(makespan)

                                                            print("Candidate assignments:", candidate_count)
                                                            print("Machines with working calendars:", len(machine_shifts))
                                                            print("Shift capacity constraints:", len(shift_assignments))
                                                            print("Machine non-overlap constraints:", len(machine_intervals))
                                                            print("\nSolving model...")

                                                            solver = cp_model.CpSolver()
                                                            solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT
                                                            solver.parameters.num_search_workers = 8
                                                            solver.parameters.log_search_progress = True
                                                            status = solver.Solve(model)

                                                            print("\nSOLVER RESULT")
                                                            print("=" * 45)
                                                            print("Status:", solver.StatusName(status))
                                                            if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                                                                print("No feasible pilot schedule was found.")
                                                                return

                                                            print("Objective makespan:", solver.Value(makespan), "minutes")
                                                            print("Solver time:", round(solver.WallTime(), 2), "seconds")

                                                            results = []
                                                            for row in operations.itertuples(index=False):
                                                                operation_id = row.operation_id
                                                                selected_assignment = next(
                                                                    (
                                                                        assignment_details[key]
                                                                        for key, presence in assignment_vars.items()
                                                                        if key[0] == operation_id and solver.Value(presence) == 1
                                                                    ),
                                                                    None,
                                                                )
                                                                if selected_assignment is None:
                                                                    raise ValueError(f"No selected machine found for {operation_id}")

                                                                results.append({
                                                                    "operation_id": operation_id,
                                                                    "order_id": row.order_id,
                                                                    "product_id": row.product_id,
                                                                    "family": row.family,
                                                                    "routing_operation_id": row.routing_operation_id,
                                                                    "machine_id": selected_assignment["machine_id"],
                                                                    "calendar_id": selected_assignment["calendar_id"],
                                                                    "shift_start": selected_assignment["shift_start"],
                                                                    "shift_end": selected_assignment["shift_end"],
                                                                    "duration_minutes": int(row.duration_minutes),
                                                                    "start_time": (
                                                                        origin + timedelta(minutes=solver.Value(start_vars[operation_id]))
                                                                    ).isoformat(),
                                                                    "end_time": (
                                                                        origin + timedelta(minutes=solver.Value(end_vars[operation_id]))
                                                                    ).isoformat(),
                                                                    "status": "SCHEDULED",
                                                                })

                                                                PROCESSED.mkdir(parents=True, exist_ok=True)
                                                                output_path = PROCESSED / "pilot_schedule.csv"
                                                                schedule_df = pd.DataFrame(results)
                                                                schedule_df.to_csv(output_path, index=False)
                                                                print("\nPilot schedule saved:", output_path)
                                                                print("Scheduled operations:", len(schedule_df))


def build_and_solve(data):
    model = cp_model.CpModel()

    # 1. Select pilot orders and connect product families.
    orders = data["orders"].head(PILOT_ORDER_COUNT)
    selected_order_ids = orders["order_id"].tolist()
    operations = data["operations"][
        data["operations"]["order_id"].isin(selected_order_ids)
    ].copy().reset_index(drop=True)

    order_products = orders[["order_id", "product_id"]].drop_duplicates()
    product_families = data["products"][
        ["product_id", "family"]
    ].drop_duplicates()
    operations = operations.merge(
        order_products,
        on="order_id",
        how="left",
    ).merge(
        product_families,
        on="product_id",
        how="left",
    )
    if operations["family"].isna().any():
        missing_operations = operations.loc[
            operations["family"].isna(), "operation_id"
        ].tolist()
        raise ValueError(
            f"Missing product family for operations: {missing_operations}"
        )

    eligibility = data["eligibility"]
    calendars = data["calendars"].copy()
    calendars["shift_start"] = pd.to_datetime(calendars["shift_start"])
    calendars["shift_end"] = pd.to_datetime(calendars["shift_end"])
    calendars["is_working"] = calendars["is_working"].astype(str).str.lower().isin(
        ["true", "1", "yes"]
    )
    calendars["available_minutes"] = calendars["available_minutes"].astype(int)
    working_calendars = calendars[
        calendars["is_working"] & (calendars["available_minutes"] > 0)
    ].copy()

    # Prepare skill-specific labor calendars.
    labor_calendars = data["labor_calendars"].copy()
    labor_calendars["work_date"] = pd.to_datetime(
        labor_calendars["work_date"]
    ).dt.date
    labor_calendars["is_working"] = (
        labor_calendars["is_working"]
        .astype(str)
        .str.lower()
        .isin(["true", "1", "yes"])
    )
    labor_calendars["shift_start_dt"] = labor_calendars.apply(
        lambda row: pd.Timestamp(
            f"{row['work_date']} {row['start_time']}"
        ),
        axis=1,
    )
    labor_calendars["shift_end_dt"] = labor_calendars.apply(
        lambda row: pd.Timestamp(
            f"{row['work_date']} {row['end_time']}"
        ),
        axis=1,
    )
    working_labor = labor_calendars[
        labor_calendars["is_working"]
        & (labor_calendars["available_workers"] > 0)
    ].copy()
    labor_shift_lookup = {
        (row.skill, row.shift_start_dt, row.shift_end_dt): row
        for row in working_labor.itertuples(index=False)
    }
    origin = calendars["shift_start"].min()
    horizon = int(
        (calendars["shift_end"].max() - origin).total_seconds() // 60
    )

    # 2. Build machine and calendar lookups.
    eligible_machines = (
        eligibility.groupby("operation_id")["machine_id"]
        .apply(lambda values: values.unique().tolist())
        .to_dict()
    )
    machine_shifts = {
        machine_id: group.to_dict("records")
        for machine_id, group in working_calendars.groupby("machine_id")
    }

    print("\nBUILDING CP-SAT MODEL")
    print("=" * 45)
    print("Pilot orders:", len(selected_order_ids))
    print("Pilot operations:", len(operations))

    start_vars = {}
    end_vars = {}
    assignment_vars = {}
    assignment_details = {}
    machine_intervals = {}
    shift_assignments = {}
    labor_assignments = {}
    candidate_count = 0
    candidate_trace = []
    missing_candidates = []

    # 3. Create operation variables and eligible machine/shift assignments.
    for row in operations.itertuples(index=False):
        operation_id = row.operation_id
        duration = int(row.duration_minutes)
        start = model.NewIntVar(0, horizon, f"start_{operation_id}")
        end = model.NewIntVar(0, horizon, f"end_{operation_id}")
        model.Add(end == start + duration)
        start_vars[operation_id] = start
        end_vars[operation_id] = end
        operation_candidates = []

        for machine_id in eligible_machines.get(row.routing_operation_id, []):
            for shift in machine_shifts.get(machine_id, []):
                available = int(shift["available_minutes"])
                if duration > available:
                    candidate_trace.append({
                        "operation_id": operation_id,
                        "order_id": row.order_id,
                        "routing_operation_id": row.routing_operation_id,
                        "machine_id": machine_id,
                        "calendar_id": shift["calendar_id"],
                        "duration_minutes": duration,
                        "available_minutes": available,
                        "candidate_status": "REJECTED",
                        "reason": (
                            "Operation duration exceeds available "
                            "minutes in this shift."
                        ),
                    })
                    continue
                shift_start = int(
                    (shift["shift_start"] - origin).total_seconds() // 60
                )
                shift_end = int(
                    (shift["shift_end"] - origin).total_seconds() // 60
                )
                if shift_end - shift_start < duration:
                    candidate_trace.append({
                        "operation_id": operation_id,
                        "order_id": row.order_id,
                        "routing_operation_id": row.routing_operation_id,
                        "machine_id": machine_id,
                        "calendar_id": shift["calendar_id"],
                        "duration_minutes": duration,
                        "available_minutes": available,
                        "candidate_status": "REJECTED",
                        "reason": (
                            "Operation duration exceeds the time "
                            "span of this shift."
                        ),
                    })
                    continue

                presence = model.NewBoolVar(
                    f"assign_{operation_id}_{machine_id}_"
                    f"{shift['calendar_id']}"
                )
                interval = model.NewOptionalIntervalVar(
                    start,
                    duration,
                    end,
                    presence,
                    f"interval_{operation_id}_{machine_id}_"
                    f"{shift['calendar_id']}",
                )

                # Connect this optional machine assignment to its labor shift.
                labor_key = (
                    row.required_skill,
                    shift["shift_start"],
                    shift["shift_end"],
                )
                if labor_key not in labor_shift_lookup:
                    raise ValueError(
                        f"No matching labor calendar for skill "
                        f"{row.required_skill}, machine shift "
                        f"{shift['calendar_id']}"
                    )
                labor_shift = labor_shift_lookup[labor_key]
                labor_assignments.setdefault(
                    labor_key,
                    {
                        "intervals": [],
                        "demands": [],
                        "capacity": int(labor_shift.available_workers),
                    },
                )
                labor_assignments[labor_key]["intervals"].append(interval)
                labor_assignments[labor_key]["demands"].append(
                    int(row.labor_required)
                )

                model.Add(start >= shift_start).OnlyEnforceIf(presence)
                model.Add(start <= shift_end - duration).OnlyEnforceIf(presence)

                assignment_key = (operation_id, candidate_count)
                assignment_vars[assignment_key] = presence
                assignment_details[assignment_key] = {
                    "machine_id": machine_id,
                    "calendar_id": shift["calendar_id"],
                    "shift_start": shift["shift_start"],
                    "shift_end": shift["shift_end"],
                }
                candidate_trace.append({
                    "operation_id": operation_id,
                    "order_id": row.order_id,
                    "routing_operation_id": row.routing_operation_id,
                    "machine_id": machine_id,
                    "calendar_id": shift["calendar_id"],
                    "duration_minutes": duration,
                    "available_minutes": available,
                    "candidate_status": "CANDIDATE",
                    "reason": (
                        "Eligible machine and working shift; "
                        "operation duration fits available capacity."
                    ),
                })
                operation_candidates.append(presence)
                machine_intervals.setdefault(machine_id, []).append(interval)
                shift_key = (machine_id, shift["calendar_id"])
                shift_assignments.setdefault(shift_key, []).append(
                    (duration, presence, available)
                )
                candidate_count += 1

        if not operation_candidates:
            missing_candidates.append(operation_id)
        else:
            model.Add(sum(operation_candidates) == 1)

    if missing_candidates:
        raise ValueError(
            "Operations without valid machine/shift candidates: "
            + ", ".join(missing_candidates)
        )

    # 4. Enforce shared material inventory over the schedule timeline.
    add_material_inventory_constraints(
        model,
        operations,
        start_vars,
        data["material_demand"],
        data["inventory"],
        origin,
    )

    # 5. Prevent machine overlaps.
    for intervals in machine_intervals.values():
        model.AddNoOverlap(intervals)

    # 6. Sequence-dependent setup using one circuit per machine.
    changeover_lookup = {
        (row.machine_id, row.from_family, row.to_family): int(row.setup_minutes)
        for row in data["changeovers"].itertuples(index=False)
    }
    operation_families = dict(
        zip(operations["operation_id"], operations["family"])
    )
    changeover_arcs = 0

    for machine_id in machine_intervals:
        machine_operations = {}
        for key, presence in assignment_vars.items():
            if assignment_details[key]["machine_id"] == machine_id:
                machine_operations.setdefault(key[0], []).append(presence)

        machine_operation_presence = {}
        for operation_id, candidates in machine_operations.items():
            assigned = model.NewBoolVar(f"uses_{operation_id}_{machine_id}")
            model.Add(sum(candidates) == assigned)
            machine_operation_presence[operation_id] = assigned

        operation_ids_on_machine = list(machine_operation_presence)
        machine_used = model.NewBoolVar(f"machine_used_{machine_id}")
        model.AddMaxEquality(
            machine_used,
            list(machine_operation_presence.values()),
        )
        arcs = [(0, 0, machine_used.Not())]
        node_by_operation = {
            operation_id: index + 1
            for index, operation_id in enumerate(operation_ids_on_machine)
        }

        for operation_id, node in node_by_operation.items():
            assigned = machine_operation_presence[operation_id]
            arcs.append((node, node, assigned.Not()))
            first_arc = model.NewBoolVar(
                f"first_{operation_id}_{machine_id}"
            )
            last_arc = model.NewBoolVar(
                f"last_{operation_id}_{machine_id}"
            )
            arcs.extend([(0, node, first_arc), (node, 0, last_arc)])
            changeover_arcs += 2

        for first_index, first_operation in enumerate(operation_ids_on_machine):
            for second_operation in operation_ids_on_machine[first_index + 1:]:
                for from_operation, to_operation in (
                    (first_operation, second_operation),
                    (second_operation, first_operation),
                ):
                    arc = model.NewBoolVar(
                        f"arc_{from_operation}_{to_operation}_{machine_id}"
                    )
                    arcs.append((
                        node_by_operation[from_operation],
                        node_by_operation[to_operation],
                        arc,
                    ))
                    setup_minutes = changeover_lookup.get(
                        (
                            machine_id,
                            operation_families[from_operation],
                            operation_families[to_operation],
                        ),
                        0,
                    )
                    model.Add(
                        start_vars[to_operation]
                        >= end_vars[from_operation] + setup_minutes
                    ).OnlyEnforceIf(arc)
                    changeover_arcs += 1

        model.AddCircuit(arcs)

    # 7. Respect shift capacity.
    for assignments in shift_assignments.values():
        available = assignments[0][2]
        model.Add(
            sum(duration * presence for duration, presence, _ in assignments)
            <= available
        )

    # 8. Respect skill-specific labor capacity for each shift.
    for assignments in labor_assignments.values():
        model.AddCumulative(
            assignments["intervals"],
            assignments["demands"],
            assignments["capacity"],
        )

    # 9. Enforce operation precedence.
    operation_ids = set(operations["operation_id"])
    for row in operations.itertuples(index=False):
        predecessor = row.predecessor_operation_id
        if pd.notna(predecessor) and predecessor in operation_ids:
            model.Add(end_vars[predecessor] <= start_vars[row.operation_id])

    # 10. Minimize makespan.
    makespan = model.NewIntVar(0, horizon, "makespan")
    model.AddMaxEquality(makespan, list(end_vars.values()))
    model.Minimize(makespan)

    print("Candidate assignments:", candidate_count)
    print("Machines with working calendars:", len(machine_shifts))
    print("Shift capacity constraints:", len(shift_assignments))
    print("Machine non-overlap constraints:", len(machine_intervals))
    print("Changeover circuit arcs:", changeover_arcs)
    print("\nSolving model...")

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT
    solver.parameters.num_search_workers = 8
    solver.parameters.log_search_progress = True
    status = solver.Solve(model)

    print("\nSOLVER RESULT")
    print("=" * 45)
    print("Status:", solver.StatusName(status))
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("No feasible pilot schedule was found.")
        return {
            "status": solver.StatusName(status),
            "makespan_minutes": None,
            "solver_time_seconds": round(solver.WallTime(), 2),
            "scheduled_operations": 0,
            "output_path": None,
        }

    print("Objective makespan:", solver.Value(makespan), "minutes")
    print("Solver time:", round(solver.WallTime(), 2), "seconds")

    results = []
    for row in operations.itertuples(index=False):
        operation_id = row.operation_id
        selected_assignment = next(
            (
                assignment_details[key]
                for key, presence in assignment_vars.items()
                if key[0] == operation_id and solver.Value(presence) == 1
            ),
            None,
        )
        if selected_assignment is None:
            raise ValueError(f"No selected machine found for {operation_id}")

        results.append({
            "operation_id": operation_id,
            "order_id": row.order_id,
            "product_id": row.product_id,
            "family": row.family,
            "routing_operation_id": row.routing_operation_id,
            "machine_id": selected_assignment["machine_id"],
            "calendar_id": selected_assignment["calendar_id"],
            "shift_start": selected_assignment["shift_start"],
            "shift_end": selected_assignment["shift_end"],
            "duration_minutes": int(row.duration_minutes),
            "start_time": (
                origin + timedelta(minutes=solver.Value(start_vars[operation_id]))
            ).isoformat(),
            "end_time": (
                origin + timedelta(minutes=solver.Value(end_vars[operation_id]))
            ).isoformat(),
            "status": "SCHEDULED",
        })

    selected_assignments = {
        row["operation_id"]: (
            row["machine_id"],
            row["calendar_id"],
        )
        for row in results
    }
    for candidate in candidate_trace:
        if candidate["candidate_status"] == "REJECTED":
            continue
        selected = selected_assignments.get(
            candidate["operation_id"]
        )
        if selected == (
            candidate["machine_id"],
            candidate["calendar_id"],
        ):
            candidate["candidate_status"] = "SELECTED"
            candidate["reason"] = (
                "Selected by the global optimization solution."
            )
        else:
            candidate["candidate_status"] = "NOT_SELECTED"
            candidate["reason"] = (
                "Valid candidate, but not selected by the "
                "global optimization."
            )

    PROCESSED.mkdir(parents=True, exist_ok=True)
    output_path = PROCESSED / "pilot_schedule.csv"
    schedule_df = pd.DataFrame(results)
    schedule_df.to_csv(output_path, index=False)
    trace_path = PROCESSED / "schedule_decision_trace.csv"
    trace_df = pd.DataFrame(candidate_trace)
    trace_df.to_csv(trace_path, index=False)
    print("Schedule decision trace saved:", trace_path)
    print("Total candidate records:", len(trace_df))
    print(
        "Selected candidates:",
        (trace_df["candidate_status"] == "SELECTED").sum()
    )
    print(
        "Unselected candidates:",
        (trace_df["candidate_status"] == "NOT_SELECTED").sum()
    )
    print(
        "Rejected candidates:",
        (trace_df["candidate_status"] == "REJECTED").sum()
    )
    print("\nPilot schedule saved:", output_path)
    print("Scheduled operations:", len(schedule_df))
    return {
        "status": solver.StatusName(status),
        "makespan_minutes": solver.Value(makespan),
        "solver_time_seconds": round(solver.WallTime(), 2),
        "scheduled_operations": len(schedule_df),
        "output_path": str(output_path.resolve()),
    }


def main():
    data = load_data()
    build_and_solve(data)

if __name__ == "__main__":
    main()
