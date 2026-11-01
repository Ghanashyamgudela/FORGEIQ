# FORGEIQ - Validation and Testing Report

## 1. Overview

This document describes the validation and testing activities performed on the FORGEIQ manufacturing scheduling prototype.

The validation approach combines synthetic data checks, deliberate anomaly detection, independent schedule validation, API verification, database checks, and automated tests.

## 2. Dataset Validation

The synthetic dataset contains the following records:

| Dataset | Records |
|---|---:|
| Products | 100 |
| Machines | 40 |
| Materials | 200 |
| Production orders | 500 |
| Production operations | 2,000 |
| Machine calendars | 2,400 |
| Inventory lots | 200 |
| Labor calendars | 240 |
| Routing machine eligibility | 1,837 |
| Order material demand | 13,511 |
| Changeover matrix | 2,560 |
| Operation material requirements | 2,763 |
| Shared tooling assignments | 2,000 |

The dataset is generated using a fixed random seed to support reproducibility.

## 3. Deliberate Anomaly Detection

Five deliberate manufacturing anomaly scenarios were injected into the test data.

| Scenario | Description | Detection result |
|---|---|---|
| Machine overlap | Two operations overlap on one machine | Detected |
| Precedence violation | Downstream operation starts too early | Detected |
| Material unavailable | Production starts before material arrival | Detected |
| Outside shift | Operation falls outside a valid working shift | Detected |
| Missing changeover | Required setup time is omitted | Detected |

The validator also identified a labor-capacity violation associated with the overlapping operations.

This additional finding is a secondary consequence of the injected overlap, not a sixth deliberate anomaly scenario.

## 4. Anomaly Detection Evaluation

The evaluator compared the five injected scenarios against the validator findings.

| Metric | Result |
|---|---:|
| Expected scenarios | 5 |
| True positives | 5 |
| False positives | 0 |
| False negatives | 0 |
| Precision | 100% |
| Recall | 100% |
| F1 score | 100% |

These metrics apply only to the five deliberately injected test scenarios. They do not represent general-purpose anomaly detection performance on real manufacturing data.

## 5. Pilot Scheduling Results

The OR-Tools optimizer was executed on a pilot subset.

| Metric | Result |
|---|---:|
| Pilot production orders | 20 |
| Pilot operations | 80 |
| Scheduled operations | 80 |
| Unscheduled operations | 0 |
| Scheduling coverage | 100% |
| Solver status | FEASIBLE |
| Makespan | 22,294 minutes |
| Solver time | Approximately 300 seconds |

The solver found a feasible schedule but did not prove global optimality.

## 6. Independent Schedule Validation

The generated pilot schedule was checked independently.

| Validation | Violations | Result |
|---|---:|---|
| Duplicate operations | 0 | PASS |
| Ineligible machine assignments | 0 | PASS |
| Outside shift boundaries | 0 | PASS |
| Non-working calendar assignments | 0 | PASS |
| Machine overlaps | 0 | PASS |
| Shift capacity violations | 0 | PASS |
| Operation precedence violations | 0 | PASS |
| Material availability and quantity | 0 | PASS |
| Changeover violations | 0 | PASS |
| Labor capacity violations | 0 | PASS |

## 7. API and Database Verification

The following integration checks were performed:

- API health endpoint returned HTTP 200.
- Manufacturing metrics endpoint returned the expected dataset counts.
- Constraint violations endpoint returned six findings.
- Optimization endpoint generated a feasible pilot schedule.
- The successful schedule was imported into SQLite.
- The schedules endpoint returned 80 schedule records.
- Database foreign-key verification returned zero violations.

## 8. Automated Test Results

Command executed:

`python -m pytest tests/ -v`

Final recorded result:

**15 passed in 0.74 seconds.**

The automated tests cover:

- Dataset sizes and unique identifiers.
- Material constraint validation.
- Changeover validation.
- Labor constraint validation.
- Schedule completeness.
- Unique operation scheduling.
- Required schedule fields.
- Valid start and end times.
- Machine eligibility.
- Operation precedence.

## 9. Explainability Verification

The decision trace contains 19,015 candidate records.

| Decision status | Records |
|---|---:|
| Selected | 80 |
| Not selected | 18,935 |
| Rejected | 0 |
| Total | 19,015 |

Each of the 80 pilot operations has exactly one selected assignment.

The trace records candidate assignments and factual selection statuses. It does not claim to expose the solver's complete internal reasoning.

## 10. Known Limitations

- The pilot covers 20 orders and 80 operations, not the complete 500-order dataset.
- The solver returned FEASIBLE rather than OPTIMAL.
- The synthetic dataset does not establish real-world manufacturing performance.
- Shop-floor execution and actual completion tracking are not integrated.
- The anomaly detection evaluation uses five deliberately injected scenarios.
- Dashboard machine allocation and utilization metrics should be interpreted according to their current calculation logic.

## 11. Conclusion

The recorded test results demonstrate that the FORGEIQ pilot can generate a feasible manufacturing schedule, persist it in SQLite, expose it through FastAPI, and display it through Streamlit.

The independent validation scripts and automated tests provide evidence that the tested pilot schedule respects the implemented manufacturing constraints.

Further testing with larger datasets and real manufacturing data is required before production deployment.