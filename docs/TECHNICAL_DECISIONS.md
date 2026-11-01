# FORGEIQ: Technical Decisions

## 1. Project Architecture

FORGEIQ uses a modular Python architecture to separate data generation, database management, scheduling, validation, API services, and dashboard presentation.

This separation makes individual components easier to test, maintain, and extend.

## 2. Synthetic Data Generation

**Decision:** Use Python-based synthetic data generators with configured random seeds.

**Reasoning:**
- Provides repeatable datasets for development and testing.
- Avoids dependence on confidential factory information.
- Allows controlled manufacturing scenarios and deliberate anomalies.
- Supports reproducibility testing across fresh processes.

## 3. Relational Database

**Decision:** Use SQLite with SQLAlchemy.

**Reasoning:**
- Provides relational data storage without requiring a separate database server.
- Supports structured manufacturing entities and relationships.
- Allows database validation and transactional schedule imports.
- Keeps the pilot environment straightforward to install.

**Trade-off:** SQLite is suitable for this demonstration but may need to be replaced by a server-based database for concurrent production workloads.

## 4. Optimization Engine

**Decision:** Use Google OR-Tools CP-SAT.

**Reasoning:**
- Supports integer and Boolean decision variables.
- Supports optional intervals for machine and shift assignments.
- Provides machine non-overlap constraints.
- Supports cumulative resource constraints for labor.
- Supports sequence-dependent changeover logic.
- Supports precedence constraints and objective optimization.

The pilot model minimizes the production makespan while respecting the modeled manufacturing constraints.

## 5. Machine and Shift Assignment

**Decision:** Represent eligible machine-shift combinations as optional scheduling assignments.

Each operation must select exactly one valid candidate assignment.

This approach allows the optimizer to consider alternative machines and working shifts while respecting machine eligibility and calendar boundaries.

## 6. Material Availability

**Decision:** Model shared material inventory as a time-dependent reservoir constraint.

**Reasoning:**
- Inventory availability depends on when stock becomes available.
- Multiple operations may compete for the same material.
- Inventory must not be consumed before its arrival.
- Total material consumption must remain within available supply.

An independent material validation step checks schedule readiness and quantity requirements.

## 7. Labor Capacity

**Decision:** Use cumulative resource constraints for skill-specific labor capacity.

Each scheduled operation consumes its required number of qualified workers during its processing interval.

The cumulative constraint prevents simultaneous operations from exceeding the modeled workforce capacity.

## 8. Sequence-Dependent Changeovers

**Decision:** Use circuit-based sequencing constraints for machine operations.

The model represents operation ordering on each machine and applies the corresponding setup duration between consecutive product families.

This captures setup requirements that depend on the transition from one product family to another.

## 9. Constraint Validation

**Decision:** Keep independent validation logic separate from optimization.

**Reasoning:**
- Provides an additional check on generated schedules.
- Helps identify invalid assignments and resource conflicts.
- Makes constraint behavior easier to test independently.
- Supports severity classification and anomaly evaluation.

A schedule should not be considered valid solely because the optimization process returned a result.

## 10. API and Dashboard

**Decision:** Use FastAPI for backend services and Streamlit for the interactive dashboard.

FastAPI exposes scheduling and manufacturing information through REST endpoints.

Streamlit provides a visual interface for monitoring schedules, machine workload, delivery indicators, constraint violations, and scheduling decisions.

This separation allows the dashboard and backend to evolve independently.

## 11. Testing Strategy

**Decision:** Use Pytest for automated testing.

Testing covers:
- Generator reproducibility.
- Database validation.
- Schedule importing.
- Constraint validation.
- Manufacturing resource and calendar edge cases.

The latest verified full test-suite result is 66 passing tests.

## 12. Known Trade-offs and Limitations

- The current scheduling model is a pilot covering 20 orders and 80 operations.
- The solver uses a configured time limit and may return a feasible solution without proving optimality.
- SQLite is intended for the demonstration environment.
- Synthetic data does not represent live factory execution.
- The decision trace records candidate assignments and selection outcomes, not the solver's complete internal reasoning.

## 13. Future Improvements

Potential extensions include:
- Larger-scale scheduling benchmarks.
- More detailed inventory allocation and lot-traceability rules.
- Additional resource constraints.
- Improved solver performance and solution-quality comparisons.
- Production database integration.
- Real-time shop-floor data integration.
- More extensive API and end-to-end testing.