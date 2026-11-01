# FORGEIQ: Validation and Testing Report

## 1. Purpose

This report summarizes the automated testing, manufacturing constraint validation, anomaly fixture evaluation, and independent schedule verification performed in FORGEIQ.

The objective is to demonstrate that the platform checks both software behavior and manufacturing schedule feasibility.

## 2. Automated Test Suite

The project uses Pytest for automated testing.

The test suite covers:

- Synthetic data generation reproducibility.
- Database primary-key and relationship validation.
- Schedule importer behavior.
- Constraint validator behavior.
- Manufacturing resource and calendar edge cases.

**Latest verified full-suite result: 66 passed.**

The test suite is designed to verify important application behavior, data integrity, and manufacturing constraint handling.

## 3. Manufacturing Constraint Validation

The validation pipeline checks the following constraints:

| Constraint | Validation objective |
|---|---|
| Machine eligibility | Operations use eligible machines |
| Machine overlap | A machine does not process overlapping operations |
| Operation precedence | Predecessor operations finish before dependent operations begin |
| Material availability | Required materials are available before operations start |
| Material quantity | Total consumption does not exceed available inventory |
| Machine calendar | Operations fit within working machine shifts |
| Changeover | Required setup time exists between consecutive operations |
| Labor capacity | Simultaneous workforce demand does not exceed available workers |

Violations are classified by issue type and severity to support investigation and corrective action.

## 4. Anomaly Fixture Evaluation

The anomaly evaluation compares detected findings against predefined synthetic ground-truth fixtures.

Current fixture evaluation:

| Metric | Result |
|---|---:|
| Expected findings | 7 |
| True positives | 7 |
| False positives | 0 |
| False negatives | 0 |
| Precision | 100% |
| Recall | 100% |
| F1 score | 100% |

These results represent performance against the current synthetic test fixtures. They do not establish general anomaly-detection accuracy on real manufacturing data.

## 5. Independent Pilot Schedule Validation

The generated pilot schedule is checked independently of the optimizer.

The validation process examines:
- Duplicate schedule records.
- Unknown operations and machines.
- Machine eligibility.
- Working machine shifts.
- Machine overlaps.
- Operation precedence.
- Shift capacity.
- Material availability and quantity.
- Changeover requirements.
- Labor capacity.

### Recorded pilot evidence

| Validation area | Recorded result |
|---|---|
| Scheduled operations | 80 |
| Production orders | 20 |
| Machine overlap validation | 0 violations |
| Material validation | 0 violations |
| Changeover validation | 0 violations |
| Labor validation | 0 violations |

The recorded independent validation runs reported no violations in these areas.

## 6. Optimization Result

The pilot optimization uses Google OR-Tools CP-SAT.

A recorded pilot execution produced:

| Metric | Result |
|---|---:|
| Solver status | FEASIBLE |
| Scheduled operations | 80 |
| Production orders | 20 |
| Makespan | 41,933 minutes |
| Solver time | Approximately 300.59 seconds |

A feasible solution satisfies the modeled constraints but does not prove that the globally optimal solution has been found.

## 7. Schedule Decision Trace

The optimizer exports a candidate decision trace containing machine-shift assignment outcomes.

Recorded trace:

| Outcome | Count |
|---|---:|
| Selected candidates | 80 |
| Valid candidates not selected | 18,935 |
| Rejected candidates | 0 |
| Total records | 19,015 |

The trace records the candidate assignments, selection outcomes, and associated decision reasons. It does not expose the solver's complete internal reasoning.

## 8. Reproducibility

Generator reproducibility is tested by executing generators in fresh Python processes and comparing generated dataset hashes.

The configured random seed supports repeatable synthetic dataset generation.

## 9. Fresh Environment Verification

A fresh project clone was used to verify the installation workflow.

The verification process included:

- Cloning the GitHub repository.
- Creating a new Python virtual environment.
- Installing dependencies from `requirements.txt`.
- Importing core project dependencies.
- Running dependency consistency checks.
- Running the project test suite.

The fresh-clone test result should be recorded separately once its exact Pytest summary has been confirmed.

## 10. Scope and Limitations

- The evaluation dataset is synthetic.
- Fixture metrics measure agreement with predefined scenarios, not real-world detection performance.
- The pilot optimizer covers 20 orders and 80 operations.
- Solver feasibility does not imply proven optimality.
- Independent validation covers the implemented constraints and should not be interpreted as proof of every possible factory condition.
- The dashboard presents planned scheduling information, not live shop-floor execution.

## 11. Conclusion

FORGEIQ combines automated software testing, manufacturing constraint validation, anomaly fixture evaluation, and independent schedule verification.

The recorded results demonstrate a working pilot workflow for generating manufacturing data, constructing feasible schedules, and checking important manufacturing constraints.