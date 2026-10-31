
from pathlib import Path

import pandas as pd


PROCESSED_DIR = Path("data/processed")


def test_material_constraints_have_no_violations():
    path = PROCESSED_DIR / "material_violations.csv"

    assert path.exists(), (
        "Material validation output not found. "
        "Run scheduler.material_constraints first."
    )

    violations = pd.read_csv(path)

    assert violations.empty, (
        f"Material violations found: {len(violations)}"
    )


def test_changeover_constraints_have_no_violations():
    path = PROCESSED_DIR / "changeover_violations.csv"

    assert path.exists(), (
        "Changeover validation output not found. "
        "Run scheduler.validate_changeovers first."
    )

    violations = pd.read_csv(path)

    assert violations.empty, (
        f"Changeover violations found: {len(violations)}"
    )


def test_labor_constraints_have_no_violations():
    path = PROCESSED_DIR / "pilot_labor_violations.csv"

    assert path.exists(), (
        "Labor validation output not found. "
        "Run scheduler.validate_labor first."
    )

    violations = pd.read_csv(path)

    assert violations.empty, (
        f"Labor capacity violations found: {len(violations)}"
    )
