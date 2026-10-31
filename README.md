# FORGEIQ
## Manufacturing Production Intelligence

FORGEIQ is a manufacturing production scheduling and intelligence platform designed to optimize production operations while monitoring manufacturing constraints.

It combines synthetic manufacturing data generation, constraint validation, optimization using Google OR-Tools CP-SAT, a relational database, REST APIs, and an interactive Streamlit dashboard.

## Key Features

- Reproducible synthetic manufacturing data generation.
- Production order and routing management.
- Machine eligibility and calendar constraints.
- Sequence-dependent machine changeovers.
- Labor capacity constraints.
- Material availability and quantity validation.
- Constraint violation detection and severity classification.
- Pilot production scheduling using OR-Tools CP-SAT.
- Schedule decision trace with selected and alternative machine-shift candidates.
- SQLite database integration.
- FastAPI endpoints for schedules, metrics, violations, and decision traces.
- Streamlit dashboard with production analytics and explainability.

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

## Dataset

The synthetic dataset represents a manufacturing environment containing:

- 100 products
- 40 machines
- 200 materials
- 500 production orders
- 2,000 production operations

Additional datasets cover routing definitions, machine eligibility, working calendars, inventory, labor calendars, material demand, changeovers, and shared tooling.

The current pilot optimizer schedules a subset of 20 production orders, representing 80 operations.

## Installation

Clone the repository:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd FORGEIQ
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Generate Manufacturing Data

Generate master data:

```bash
python -m generator.master_data
```

Generate transactional data:

```bash
python -m generator.transaction_data
```

Generate deliberate anomaly scenarios:

```bash
python -m generator.anomaly_generator
```

The generator uses a fixed random seed configured in `generator/config.py` to support reproducibility.

## Validate Manufacturing Constraints

Run:

```bash
python -m validations.validators
```

The validation pipeline checks:

- Machine eligibility
- Machine overlap
- Operation precedence
- Material availability
- Machine working calendars
- Changeover requirements
- Labor capacity
- Material quantity

The validation report is written to:

```text
data/processed/validation_report.csv
```

## Evaluate Anomaly Detection

Run:

```bash
python -m validations.evalute
```

The evaluator compares detected violations against the five injected anomaly scenarios.

## Run the Scheduling Optimizer

Start the API:

```bash
uvicorn api.main:app --reload
```

Open the interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

Use `POST /optimize` to execute the pilot optimization workflow.

The optimizer uses Google OR-Tools CP-SAT to assign eligible machines and working shifts while considering production constraints.

The pilot schedule is exported to:

```text
data/processed/pilot_schedule.csv
```

The candidate decision trace is exported to:

```text
data/processed/schedule_decision_trace.csv
```

The API workflow also imports a successful schedule into the SQLite database.

A feasible solution means the solver found a valid schedule. It does not necessarily mean optimality has been proven.

## Database

Initialize and seed the SQLite database:

```bash
python -m database.seed_db
```

The database stores manufacturing master data, transactional data, calendars, inventory, and operation schedules.

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

API documentation:

```text
http://127.0.0.1:8000/docs
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

The dashboard provides production KPIs, machine workload, scheduling timelines, utilization analytics, schedule explainability, and constraint monitoring.

## Automated Tests

Run the complete test suite:

```bash
python -m pytest tests/ -v
```

The current test suite contains 15 passing tests covering:

- Dataset sizes and unique identifiers
- Schedule completeness and validity
- Machine eligibility
- Operation precedence
- Material availability
- Changeover constraints
- Labor capacity

**Latest verified result: 15 passed.**

## Reproducibility

The synthetic data generator uses a fixed seed. Generated datasets and optimization results should be inspected using the project's validation and evaluation scripts.

The pilot optimizer uses a configured solver time limit. Solver status and execution time should be recorded when comparing runs.

## Current Scope and Limitations

- The current optimizer is a pilot implementation covering 20 orders and 80 operations.
- A feasible solution does not prove global optimality.
- The dashboard reports scheduled operations, not live shop-floor execution.
- Decision traces show valid candidates, selected assignments, and recorded rejection reasons. They do not expose the solver's complete internal reasoning.
- The generated dataset is synthetic and does not represent a live factory.

## Project Goal

FORGEIQ demonstrates how optimization, data engineering, manufacturing constraints, and explainable production intelligence can work together in a practical scheduling platform.
