# FORGEIQ
## Manufacturing Production Intelligence

FORGEIQ is a manufacturing production scheduling and intelligence platform designed to optimize production operations while monitoring real-world manufacturing constraints.

It combines reproducible synthetic data generation, relational data management, constraint validation, mathematical optimization using Google OR-Tools CP-SAT, REST APIs, and an interactive Streamlit dashboard.

The platform demonstrates how manufacturing data engineering, operations research, and explainable scheduling can work together in a practical production planning workflow.

## Key Features

- Reproducible synthetic manufacturing data generation.
- Production order and routing management.
- Machine eligibility and working-calendar constraints.
- Sequence-dependent machine changeovers.
- Skill-specific labor capacity constraints.
- Material availability and inventory quantity validation.
- Constraint violation detection and severity classification.
- Pilot production scheduling using Google OR-Tools CP-SAT.
- Schedule decision trace covering selected and alternative machine-shift candidates.
- SQLite database integration using SQLAlchemy.
- FastAPI endpoints for schedules, metrics, violations, and decision traces.
- Streamlit dashboard with production analytics and scheduling explainability.
- Automated tests for data generation, database validation, schedule importing, and constraint validation.

## Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python |
| Optimization | Google OR-Tools CP-SAT |
| Data processing | Pandas, NumPy |
| Database | SQLite, SQLAlchemy |
| Backend API | FastAPI |
| Dashboard | Streamlit, Plotly |
| Testing | Pytest |
| Data generation | Faker |

## Project Structure

```text
FORGEIQ/
├── api/
├── dashboard/
├── data/
│   ├── raw/
│   ├── processed/
│   ├── ground_truth/
│   └── test_fixtures/
├── database/
├── docs/
├── generator/
├── scheduler/
├── validations/
├── tests/
├── main.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Synthetic Manufacturing Dataset

The generated dataset represents a manufacturing environment containing:

| Entity | Count |
|---|---:|
| Products | 100 |
| Machines | 40 |
| Materials | 200 |
| Production orders | 500 |
| Production operations | 2,000 |

Additional datasets represent routing definitions, machine eligibility, machine calendars, labor calendars, inventory lots, material demand, changeover requirements, and shared tooling assignments.

The current pilot optimizer selects 20 production orders, representing 80 operations.

All data is synthetic and intended for development, testing, and demonstration.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Ghanashyamgudela/FORGEIQ.git
cd FORGEIQ
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```cmd
venv\Scripts\activate
```

On macOS or Linux:

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Generate Manufacturing Data

Generate master data:

```bash
python -m generator.master_data
```

Generate transactional data:

```bash
python -m generator.transaction
```

Generate deliberate anomaly scenarios:

```bash
python -m generator.anomaly_generator
```

The generator uses a configured random seed in `generator/config.py` to support reproducible dataset generation across fresh process executions.

## Validate Manufacturing Constraints

Run the constraint validation pipeline:

```bash
python -m validations.validators
```

The validation logic checks manufacturing constraints including:

- Machine eligibility.
- Machine overlap.
- Operation precedence.
- Material availability.
- Machine working calendars.
- Changeover requirements.
- Labor capacity.
- Material quantity.

The validation pipeline produces a report under:

```text
data/processed/validation_report.csv
```

## Evaluate Anomaly Detection

Run:

```bash
python -m validations.evalute
```

The evaluator compares detected findings against the project's injected anomaly fixtures and ground-truth labels.

The current fixture evaluation reports:

| Metric | Result |
|---|---:|
| Expected findings | 7 |
| True positives | 7 |
| False positives | 0 |
| False negatives | 0 |
| Precision | 100% |
| Recall | 100% |
| F1 score | 100% |

These results describe performance against the project's current synthetic fixtures. They should not be interpreted as a guarantee of accuracy on real factory data.

## Run the Scheduling Optimizer

Start the FastAPI service:

```bash
uvicorn api.main:app --reload --port 8001
```

Open the interactive API documentation:

```text
http://127.0.0.1:8001/docs
```

Use `POST /optimize` to execute the pilot optimization workflow.

The optimizer uses Google OR-Tools CP-SAT to assign eligible machines and working shifts while considering:

- Machine non-overlap.
- Machine eligibility.
- Working shift boundaries.
- Shift capacity.
- Material inventory availability.
- Operation precedence.
- Sequence-dependent changeovers.
- Skill-specific labor capacity.

The pilot schedule is exported to:

```text
data/processed/pilot_schedule.csv
```

The candidate decision trace is exported to:

```text
data/processed/schedule_decision_trace.csv
```

The solver operates with a configured time limit. A `FEASIBLE` result means a valid schedule was found, but optimality has not necessarily been proven.

## Database

Initialize and seed the SQLite database:

```bash
python -m database.seed_db
```

The database stores manufacturing master data, transactional records, calendars, inventory, and operation schedules.

Database validation checks primary-key integrity and database relationships.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API information |
| GET | `/health` | Health check |
| GET | `/metrics` | Manufacturing metrics |
| GET | `/products` | Product information |
| GET | `/orders` | Production orders |
| GET | `/machines` | Machine information |
| GET | `/schedules` | Scheduled operations |
| GET | `/violations` | Constraint violations |
| GET | `/decision-trace` | Scheduling candidate trace |
| POST | `/optimize` | Run pilot optimization |

Interactive API documentation:

```text
http://127.0.0.1:8001/docs
```

## Dashboard

In a separate terminal, run:

```bash
streamlit run dashboard/app.py
```

Open:

```text
http://localhost:8501
```

The dashboard provides:

- Production KPIs.
- Schedule monitoring.
- Machine workload and utilization analytics.
- Delivery performance indicators.
- Constraint violation monitoring.
- Schedule history and run details.
- Scheduling decision trace.
- Schedule data export.

## Automated Tests

Run the complete test suite:

```bash
python -m pytest tests/ -v
```

The test suite covers:

- Synthetic data generation reproducibility.
- Database validation.
- Schedule import and data integrity.
- Constraint validator behavior.
- Machine eligibility and overlap.
- Operation precedence.
- Material availability and quantity.
- Changeover requirements.
- Labor capacity.
- Calendar and shift constraints.

**Latest verified full-suite result: 66 passed.**

The tests are designed to verify important application behavior and manufacturing constraints, rather than relying only on successful application startup.

## Reproducibility

FORGEIQ uses a configured random seed for synthetic data generation.

Reproducibility tests execute generators in fresh Python processes and compare generated dataset hashes.

The scheduling optimizer uses a configured solver time limit. Solver status, execution time, and schedule outputs should be considered when comparing optimization runs.

## Current Scope and Limitations

- The current optimizer is a pilot implementation covering 20 orders and 80 operations.
- A feasible solution does not prove global optimality.
- The dashboard reports scheduled production information, not live shop-floor execution.
- Decision traces describe candidate assignments and recorded selection outcomes. They do not expose the solver's complete internal reasoning.
- The generated dataset is synthetic and does not represent a live factory.
- Optimization performance and schedule quality depend on the input data, constraints, and solver configuration.

## Project Goal

FORGEIQ demonstrates how optimization, data engineering, manufacturing constraints, and explainable production intelligence can work together to support more reliable and efficient production planning.