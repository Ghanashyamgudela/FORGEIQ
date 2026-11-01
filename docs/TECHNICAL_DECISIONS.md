# FORGEIQ - Technical Decisions and Engineering Rationale

## 1. Project Objective

FORGEIQ is a pilot manufacturing production scheduling platform designed to generate feasible production schedules while respecting operational constraints.

The project demonstrates synthetic data generation, manufacturing validation, constraint-based optimization, database persistence, API development, and dashboard visualization.

## 2. Technology Selection

| Technology | Purpose | Reason for selection |
|---|---|---|
| Python | Core development | Suitable for data processing and optimization |
| Pandas | Dataset processing | Convenient CSV and tabular data manipulation |
| Faker | Synthetic data | Generates realistic sample manufacturing data |
| Google OR-Tools | Scheduling optimization | Supports constraint-based scheduling |
| FastAPI | Backend API | Provides structured REST endpoints |
| SQLite | Database | Lightweight persistence for a pilot |
| SQLAlchemy | Database access | ORM-based database integration |
| Streamlit | Dashboard | Rapid development of an interactive interface |
| Plotly | Visualization | Interactive charts and timelines |
| Pytest | Testing | Automated verification of project behavior |

## 3. Architecture Decisions

FORGEIQ uses a modular architecture:

1. Generator: creates synthetic manufacturing data.
2. Validations: identifies manufacturing constraint violations.
3. Scheduler: builds and solves the scheduling optimization model.
4. Database: stores manufacturing entities and generated schedules.
5. API: exposes data, validation findings and optimization functionality.
6. Dashboard: visualizes production and scheduling information.
7. Tests: verifies key data and scheduling behavior.

This separation makes the prototype easier to understand, test, and extend.

## 4. Scheduling Model Decisions

### 4.1 Constraint Programming

Google OR-Tools CP-SAT was selected because manufacturing scheduling contains multiple interacting discrete decisions and constraints.

The model uses:

- Integer start and end time variables.
- Boolean machine and shift assignment variables.
- Optional intervals for candidate assignments.
- An objective function that minimizes makespan.

### 4.2 Machine Eligibility

An operation can only be assigned to machines listed as eligible for its routing operation.

This prevents the optimizer from selecting an incompatible machine.

### 4.3 Machine Non-overlap

`AddNoOverlap()` prevents multiple operations from using the same machine simultaneously.

### 4.4 Operation Precedence

Precedence constraints ensure that a downstream operation cannot begin before its predecessor finishes.

### 4.5 Labor Capacity

`AddCumulative()` models the combined labor demand of operations over time.

The total simultaneous demand must not exceed the available capacity for the corresponding skill and shift.

### 4.6 Material Availability

Reservoir constraints represent material arrivals and consumption over the scheduling timeline.

Material availability is modeled as a shared inventory balance rather than treating every operation as if it had an independent stock allocation.

### 4.7 Sequence-dependent Changeovers

`AddCircuit()` models the sequence of operations assigned to each machine.

Transition-specific setup times are enforced between consecutive operations.

## 5. Objective Function

The pilot model minimizes makespan, representing the elapsed time until all scheduled pilot operations are completed.

This provides a measurable scheduling objective.

However, minimizing makespan alone does not necessarily minimize total production cost, energy consumption, tardiness, or changeover count.

These objectives could be introduced in future versions.

## 6. Solver Configuration and Trade-offs

The pilot uses:

- 20 production orders.
- 80 production operations.
- A 300-second solver time limit.
- Eight search workers.

The solver returned a FEASIBLE solution.

This means a valid solution was found, but global optimality was not proven within the time limit.

The 300-second limit is a trade-off between solution quality and execution time.

## 7. Database and API Decisions

SQLite was selected to keep the prototype lightweight and easy to run locally.

SQLAlchemy provides structured access to database tables.

FastAPI exposes endpoints for manufacturing metrics, schedules, violations, decision traces, and optimization.

A successful optimization imports the generated schedule into SQLite.

## 8. Explainability Decision

The decision trace records candidate machine and shift assignments, their selection status, and factual reasons for rejection where applicable.

It is designed to help users inspect the scheduling alternatives.

It does not claim to reproduce the solver's complete internal search reasoning.

## 9. Validation Strategy

Validation is performed at multiple levels:

- Synthetic dataset integrity checks.
- Manufacturing anomaly detection.
- Independent pilot schedule validation.
- Material, labor and changeover checks.
- API endpoint verification.
- Database foreign-key checks.
- Automated Pytest tests.

## 10. Known Limitations

- The current optimizer schedules a pilot subset of 20 orders rather than all 500 orders.
- The solver has not proven global optimality.
- The prototype uses synthetic manufacturing data.
- Live shop-floor execution integration is not implemented.
- Dashboard completion and in-progress figures are not connected to real execution events.
- The objective currently focuses on makespan rather than multiple competing business objectives.
- Production-scale performance has not yet been established.

## 11. Future Improvements

Potential improvements include:

- Scaling optimization to larger order volumes.
- Adding due-date and tardiness objectives.
- Adding machine maintenance and downtime updates.
- Integrating real inventory and ERP systems.
- Connecting shop-floor execution data.
- Adding schedule revision and rescheduling workflows.
- Improving solver performance and benchmarking.
- Adding user authentication and role-based access.

## 12. Engineering Principle

The primary design principle is to produce a schedule that is explainable, constraint-aware, reproducible, and independently verifiable rather than simply producing a timetable.