# FORGEIQ Data Dictionary

## 1. Overview

FORGEIQ uses synthetic manufacturing data to demonstrate production planning, machine scheduling, resource allocation, constraint validation, and schedule explainability.

The dataset is generated using a fixed random seed to support reproducibility.

## 2. Raw Data (`data/raw/`)

### Master data

| File | Description | Key columns |
|---|---|---|
| `products.csv` | Product and SKU information | product_id, sku, product_name, family, category, unit, lifecycle_state |
| `machines.csv` | Manufacturing machine details | machine_id, machine_name, machine_type, capacity_per_shift, status, location |
| `materials.csv` | Material master records | material_id, material_name, material_type, unit, lifecycle_state |
| `routings.csv` | Product manufacturing routing versions | routing_id, product_id, version, effective_from, effective_to, lifecycle_state |
| `routing_operations.csv` | Operations defined in each routing | operation_id, routing_id, sequence_number, operation_name, required_machine_type, duration_minutes, required_skill, labor_required |
| `routing_machine_eligibility.csv` | Machines eligible for routing operations | routing_id, operation_id, machine_id |

### Resource and capacity data

| File | Description | Key columns |
|---|---|---|
| `machine_calendars.csv` | Machine working shifts and downtime | calendar_id, machine_id, shift_start, shift_end, available_minutes, is_working, downtime_reason |
| `labor_calendars.csv` | Workforce availability by skill and shift | labor_calendar_id, work_date, skill, shift, start_time, end_time, available_workers, is_working |
| `changeover_matrix.csv` | Sequence-dependent setup times between product families | changeover_id, machine_id, from_family, to_family, setup_minutes |
| `shared_tooling_assignments.csv` | Shared tooling requirements for operations | operation_id, tool_id, tool_sharing |

### Production and material transactions

| File | Description | Key columns |
|---|---|---|
| `production_orders.csv` | Customer or production order records | order_id, product_id, routing_id, quantity, priority, order_date, due_date, status |
| `order_operations.csv` | Operations required by production orders | operation_id, order_id, routing_operation_id, sequence_number, duration_minutes, required_machine_type, required_skill, labor_required, predecessor_operation_id, status |
| `inventory_lots.csv` | Material inventory lots and availability | lot_id, material_id, quantity, reserved_quantity, available_at, quality_status, is_delayed |
| `order_material_demand.csv` | Material requirements for order operations | demand_id, order_id, operation_id, material_id, required_quantity, unit |
| `operation_material_requirements.csv` | Standard material consumption per operation | operation_id, material_id, quantity_per_unit, unit |

## 3. Processed Data (`data/processed/`)

| File | Description | Key columns |
|---|---|---|
| `pilot_schedule.csv` | Optimized schedule for the pilot orders | operation_id, order_id, product_id, family, machine_id, calendar_id, shift_start, shift_end, duration_minutes, start_time, end_time, status |
| `schedule_decision_trace.csv` | Candidate machine and shift decisions | operation_id, order_id, routing_operation_id, machine_id, calendar_id, duration_minutes, available_minutes, candidate_status, reason |
| `validation_report.csv` | Manufacturing constraint violations | violation_id, issue_type, affected_schedule_ids, severity, explanation, recommended_action, status |
| `material_violations.csv` | Material availability and quantity validation results | operation_id, material_id, issue_type, required_quantity, available_quantity, explanation |
| `changeover_violations.csv` | Changeover constraint validation results | machine_id, previous_operation, next_operation, from_family, to_family, required_setup, available_gap, issue |
| `pilot_labor_violations.csv` | Labor capacity validation results | issue_type, skill, work_date, shift, timestamp, required_workers, available_workers, affected_operations, explanation |
| `evaluation_summary.csv` | Summary of anomaly detection evaluation metrics | metric, value |
| `scenario_evaluation.csv` | Expected versus detected anomaly scenarios | scenario_id, issue_type, expected_schedule_ids, detected_schedule_ids, result |

## 4. Ground Truth (`data/ground_truth/`)

### `ground_truth.csv`

Contains the expected labels for deliberately injected manufacturing anomalies.

Columns:
- `scenario_id`: Unique anomaly scenario identifier.
- `issue_type`: Type of manufacturing constraint violation.
- `affected_schedule_ids`: Schedule records associated with the scenario.
- `expected_label`: Expected detection label.
- `severity`: Expected severity classification.
- `explanation`: Description of the injected anomaly.

Ground-truth data is used to evaluate the validator against the five deliberately injected anomaly scenarios.

## 5. Test Fixtures (`data/test_fixtures/`)

### `anomaly_scenarios.csv`

Contains deliberately constructed anomalous schedule records for testing.

Columns:
- `schedule_id`: Unique test schedule identifier.
- `order_id`: Associated production order.
- `operation_id`: Associated operation.
- `routing_operation_id`: Associated routing operation.
- `product_id`: Associated product.
- `product_family`: Product family.
- `machine_id`: Assigned machine.
- `start_time`: Scheduled start timestamp.
- `end_time`: Scheduled end timestamp.
- `status`: Schedule status.
- `material_id`: Associated material.
- `inventory_lot_id`: Associated inventory lot.
- `scenario_id`: Injected anomaly scenario identifier.

## 6. Important Identifiers and Relationships

- `product_id` connects products with routings and production orders.
- `routing_id` connects a product to its manufacturing routing.
- `routing_operation_id` connects order operations to routing operations.
- `order_id` identifies a production order and its operations.
- `operation_id` identifies an individual production operation.
- `machine_id` identifies the machine assigned to an operation.
- `material_id` identifies materials and their inventory records.
- `calendar_id` identifies a machine shift calendar.
- `predecessor_operation_id` represents operation precedence.
- `scenario_id` connects injected anomalies to their ground-truth labels.

## 7. Dataset Notes

- The generated datasets are synthetic and intended for demonstration and testing.
- The generator uses a fixed seed for reproducibility.
- The pilot optimizer schedules a subset of 20 production orders, containing 80 operations.
- The processed validation reports are generated by the project's validation modules.
- The five injected anomaly scenarios are evaluated separately from the pilot schedule's independent constraint checks.
- A feasible schedule does not necessarily mean that the solver has proven global optimality.