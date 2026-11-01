# FORGEIQ: Data Dictionary

## 1. Overview

FORGEIQ uses 16 synthetic CSV datasets to represent a manufacturing environment.

The datasets cover:
- Products and materials.
- Machines and machine calendars.
- Production routings and operations.
- Production orders and order-specific operations.
- Machine eligibility.
- Inventory and material demand.
- Labor availability.
- Machine changeovers.
- Shared tooling assignments.

All datasets are stored under `data/raw/`.

## 2. Dataset Reference

| Dataset | Description | Primary Identifier |
|---|---|---|
| products.csv | Product master records | product_id |
| machines.csv | Machine master records | machine_id |
| materials.csv | Material master records | material_id |
| routings.csv | Product routing definitions and versions | routing_id |
| routing_operations.csv | Standard operations within routings | operation_id |
| routing_machine_eligibility.csv | Eligible machines for routing operations | Composite relationship |
| production_orders.csv | Customer or production orders | order_id |
| order_operations.csv | Order-specific production operations | operation_id |
| machine_calendars.csv | Machine working shifts and downtime | calendar_id |
| labor_calendars.csv | Skill-specific workforce availability | labor_calendar_id |
| inventory_lots.csv | Material inventory lots | lot_id |
| operation_material_requirements.csv | Standard material requirements per operation | Composite relationship |
| order_material_demand.csv | Material demand for production orders | demand_id |
| changeover_matrix.csv | Machine-specific product-family setup times | changeover_id |
| shared_tooling_assignments.csv | Tool-sharing requirements for operations | Composite relationship |
## 3. Master Data

### 3.1 products.csv

Stores product master information.

| Column | Description |
|---|---|
| product_id | Unique product identifier |
| sku | Stock keeping unit |
| product_name | Product name |
| family | Product family used for changeover sequencing |
| category | Product category |
| unit | Product measurement unit |
| lifecycle_state | Product lifecycle status |

Primary identifier: `product_id`

### 3.2 machines.csv

Stores manufacturing machine information.

| Column | Description |
|---|---|
| machine_id | Unique machine identifier |
| machine_name | Machine name |
| machine_type | Machine classification |
| capacity_per_shift | Machine capacity per shift |
| status | Machine operational status |
| location | Machine location |

Primary identifier: `machine_id`

### 3.3 materials.csv

Stores raw material master information.

| Column | Description |
|---|---|
| material_id | Unique material identifier |
| material_name | Material name |
| material_type | Material classification |
| unit | Material measurement unit |
| lifecycle_state | Material lifecycle status |

Primary identifier: `material_id`

### 3.4 routings.csv

Defines product manufacturing routing versions.

| Column | Description |
|---|---|
| routing_id | Unique routing identifier |
| product_id | Associated product |
| version | Routing version |
| effective_from | Routing effective start date |
| effective_to | Routing effective end date |
| lifecycle_state | Routing lifecycle status |

Primary identifier: `routing_id`

Relationship: `product_id` references `products.product_id`.

### 3.5 routing_operations.csv

Defines standard operations within manufacturing routings.

| Column | Description |
|---|---|
| operation_id | Routing operation identifier |
| routing_id | Associated routing |
| sequence_number | Operation sequence |
| operation_name | Operation description |
| required_machine_type | Required machine classification |
| duration_minutes | Standard operation duration |
| required_skill | Required workforce skill |
| labor_required | Number of workers required |

Primary identifier: `operation_id`

Relationship: `routing_id` references `routings.routing_id`.

### 3.6 routing_machine_eligibility.csv

Maps routing operations to eligible machines.

| Column | Description |
|---|---|
| routing_id | Associated routing |
| operation_id | Routing operation |
| machine_id | Eligible machine |

Relationship:
- `routing_id` references `routings.routing_id`.
- `operation_id` identifies a routing operation.
- `machine_id` references `machines.machine_id`.

The routing-operation and machine combination defines an eligibility relationship.

## 4. Transactional Data

### 4.1 production_orders.csv

Stores production order information.

| Column | Description |
|---|---|
| order_id | Unique production order identifier |
| product_id | Product being manufactured |
| routing_id | Routing assigned to the order |
| quantity | Production quantity |
| priority | Order priority |
| order_date | Order creation date |
| due_date | Required completion date |
| status | Order status |

Primary identifier: `order_id`

Relationships:
- `product_id` references `products.product_id`.
- `routing_id` references `routings.routing_id`.

### 4.2 order_operations.csv

Stores order-specific manufacturing operations.

| Column | Description |
|---|---|
| operation_id | Unique order operation identifier |
| order_id | Associated production order |
| routing_operation_id | Corresponding standard routing operation |
| sequence_number | Operation sequence |
| duration_minutes | Planned processing duration |
| required_machine_type | Required machine classification |
| required_skill | Required workforce skill |
| labor_required | Required number of workers |
| predecessor_operation_id | Preceding order operation |
| status | Operation status |

Primary identifier: `operation_id`

Relationships:
- `order_id` references `production_orders.order_id`.
- `routing_operation_id` identifies the corresponding standard routing operation.
- `predecessor_operation_id` represents an operation dependency within the order.

Important: `operation_id` identifies an order-specific operation, while `routing_operation_id` identifies its reusable routing definition.

### 4.3 order_material_demand.csv

Stores material requirements for individual production operations.

| Column | Description |
|---|---|
| demand_id | Unique material demand identifier |
| order_id | Associated production order |
| operation_id | Associated order operation |
| material_id | Required material |
| required_quantity | Total required quantity |
| unit | Measurement unit |

Primary identifier: `demand_id`

Relationships:
- `order_id` references `production_orders.order_id`.
- `operation_id` references `order_operations.operation_id`.
- `material_id` references `materials.material_id`.

### 4.4 inventory_lots.csv

Stores inventory lot quantities and availability information.

| Column | Description |
|---|---|
| lot_id | Unique inventory lot identifier |
| material_id | Associated material |
| quantity | Total lot quantity |
| reserved_quantity | Already reserved quantity |
| available_at | Inventory availability timestamp |
| quality_status | Inventory quality or release status |
| is_delayed | Indicates delayed inventory |

Primary identifier: `lot_id`

Relationship: `material_id` references `materials.material_id`.

Available inventory is determined using lot quantity, reserved quantity, quality status, and availability time.

## 5. Resource Calendars

### 5.1 machine_calendars.csv

Defines machine working periods and availability.

| Column | Description |
|---|---|
| calendar_id | Unique machine calendar identifier |
| machine_id | Associated machine |
| shift_start | Shift start timestamp |
| shift_end | Shift end timestamp |
| available_minutes | Available production minutes |
| is_working | Indicates whether the machine is working |
| downtime_reason | Reason for unavailable time |

Primary identifier: `calendar_id`

Relationship: `machine_id` references `machines.machine_id`.

### 5.2 labor_calendars.csv

Defines workforce availability by skill and shift.

| Column | Description |
|---|---|
| labor_calendar_id | Unique labor calendar identifier |
| work_date | Working date |
| skill | Workforce skill |
| shift | Shift identifier |
| start_time | Shift start time |
| end_time | Shift end time |
| available_workers | Number of available workers |
| is_working | Indicates workforce availability |

Primary identifier: `labor_calendar_id`

The skill and shift information is used to match operation requirements against available labor capacity.

## 6. Manufacturing Constraints and Relationships

### 6.1 changeover_matrix.csv

Defines sequence-dependent machine setup requirements.

| Column | Description |
|---|---|
| changeover_id | Unique changeover identifier |
| machine_id | Associated machine |
| from_family | Previous product family |
| to_family | Next product family |
| setup_minutes | Required setup duration |

Primary identifier: `changeover_id`

Relationship: `machine_id` references `machines.machine_id`.

### 6.2 operation_material_requirements.csv

Defines standard material consumption for routing operations.

| Column | Description |
|---|---|
| operation_id | Routing operation identifier |
| material_id | Required material |
| quantity_per_unit | Material required per production unit |
| unit | Measurement unit |

Relationship:
- `operation_id` identifies a routing operation.
- `material_id` references `materials.material_id`.

### 6.3 shared_tooling_assignments.csv

Stores tooling requirements and sharing information.

| Column | Description |
|---|---|
| operation_id | Associated order operation |
| tool_id | Tool identifier |
| tool_sharing | Tool-sharing configuration or indicator |

The `operation_id` identifies an order-specific operation. The `tool_id` identifies the assigned tool.

A separate tool master dataset is not included in the current raw dataset.

## 7. High-Level Entity Relationships

The main manufacturing data flow is:

```text
PRODUCTS
   |
   v
ROUTINGS
   |
   v
ROUTING_OPERATIONS
   |
   +------ ROUTING_MACHINE_ELIGIBILITY ------ MACHINES
   |
   +------ OPERATION_MATERIAL_REQUIREMENTS -- MATERIALS
   |
   v
PRODUCTION_ORDERS
   |
   v
ORDER_OPERATIONS
   |
   +------ ORDER_MATERIAL_DEMAND ------------ MATERIALS
   |
   +------ SHARED_TOOLING_ASSIGNMENTS
   |
   v
SCHEDULED_OPERATIONS
```

Additional resource relationships:

```text
MACHINES
   |
   +------ MACHINE_CALENDARS
   |
   +------ CHANGEOVER_MATRIX

MATERIALS
   |
   +------ INVENTORY_LOTS

LABOR_CALENDARS
   |
   +------ SKILL-BASED LABOR CAPACITY
```

## 8. Important Identifier Distinctions

FORGEIQ uses separate identifiers for reusable routing definitions and order-specific operations.

| Identifier | Meaning |
|---|---|
| routing_id | Manufacturing routing |
| routing_operations.operation_id | Standard routing operation |
| order_operations.operation_id | Order-specific operation |
| routing_operation_id | Link from an order operation to its standard routing operation |
| predecessor_operation_id | Preceding order-specific operation |

This distinction is important when connecting production orders, routing definitions, machine eligibility, and material requirements.

## 9. Data Quality and Validation

The project includes automated checks for:
- Missing and duplicate primary identifiers.
- Database primary-key and foreign-key integrity.
- Schedule operation integrity.
- Machine eligibility.
- Machine overlaps.
- Operation precedence.
- Material availability and quantity.
- Working calendar boundaries.
- Changeover requirements.
- Labor capacity.

## 10. Dataset Scope

The current synthetic manufacturing dataset contains:

| Entity | Count |
|---|---:|
| Products | 100 |
| Machines | 40 |
| Materials | 200 |
| Production orders | 500 |
| Production operations | 2,000 |

The pilot scheduling workflow selects 20 production orders and their associated 80 operations.

All data is synthetic and intended for engineering demonstration, development, and automated testing.