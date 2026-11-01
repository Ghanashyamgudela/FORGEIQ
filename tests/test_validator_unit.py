
from validations.validators import ConstraintValidator


import pandas as pd

from validations.validators import check_material_quantity
from validations.validators import check_labor_capacity

def test_detects_inventory_quantity_exceeded():
    schedules = pd.DataFrame([
        {
            "schedule_id": "SCH-015",
            "operation_id": "OP-001",
            "inventory_lot_id": "LOT-001",
            "material_id": "MAT-001",
        },
        {
            "schedule_id": "SCH-016",
            "operation_id": "OP-002",
            "inventory_lot_id": "LOT-001",
            "material_id": "MAT-001",
        },
    ])

    material_demand = pd.DataFrame([
        {"operation_id": "OP-001", "material_id": "MAT-001", "required_quantity": 7},
        {"operation_id": "OP-002", "material_id": "MAT-001", "required_quantity": 6},
    ])

    inventory = pd.DataFrame([
        {"lot_id": "LOT-001", "quantity": 10},
    ])

    violations = check_material_quantity(
        schedules, material_demand, inventory
    )

    assert len(violations) == 1
    assert violations[0]["issue_type"] == "MATERIAL_QUANTITY_EXCEEDED"


def test_accepts_inventory_quantity_within_limit():
    schedules = pd.DataFrame([
        {
            "schedule_id": "SCH-017",
            "operation_id": "OP-001",
            "inventory_lot_id": "LOT-001",
            "material_id": "MAT-001",
        },
    ])

    material_demand = pd.DataFrame([
        {"operation_id": "OP-001", "material_id": "MAT-001", "required_quantity": 7},
    ])

    inventory = pd.DataFrame([
        {"lot_id": "LOT-001", "quantity": 10},
    ])

    violations = check_material_quantity(
        schedules, material_demand, inventory
    )

    assert violations == []

def make_validator(schedules):
    data = {
        "machines": [
            {"machine_id": "MACH-001"}
        ],
        "operations": [
            {
                "operation_id": "OP-001",
                "routing_operation_id": "ROUTE-001",
                "sequence_number": "1",
            },
            {
                "operation_id": "OP-002",
                "routing_operation_id": "ROUTE-002",
                "sequence_number": "2",
            },
        ],
        "eligibility": [
            {"operation_id": "ROUTE-001", "machine_id": "MACH-001"},
            {"operation_id": "ROUTE-002", "machine_id": "MACH-001"},
        ],
        "inventory": [],
        "changeovers": [],
        "calendars": [],
        "schedules": schedules,
    }
    return ConstraintValidator(data)


def test_detects_machine_overlap():
    schedules = [
        {
            "schedule_id": "SCH-001",
            "operation_id": "OP-001",
            "machine_id": "MACH-001",
            "start_time": "2026-11-02T08:00:00",
            "end_time": "2026-11-02T10:00:00",
        },
        {
            "schedule_id": "SCH-002",
            "operation_id": "OP-002",
            "machine_id": "MACH-001",
            "start_time": "2026-11-02T09:00:00",
            "end_time": "2026-11-02T11:00:00",
        },
    ]

    validator = make_validator(schedules)
    validator.check_machine_overlap()

    assert len(validator.violations) == 1
    assert validator.violations[0]["issue_type"] == "MACHINE_OVERLAP"


def test_accepts_non_overlapping_operations():
    schedules = [
        {
            "schedule_id": "SCH-001",
            "operation_id": "OP-001",
            "machine_id": "MACH-001",
            "start_time": "2026-11-02T08:00:00",
            "end_time": "2026-11-02T09:00:00",
        },
        {
            "schedule_id": "SCH-002",
            "operation_id": "OP-002",
            "machine_id": "MACH-001",
            "start_time": "2026-11-02T09:00:00",
            "end_time": "2026-11-02T10:00:00",
        },
    ]

    validator = make_validator(schedules)
    validator.check_machine_overlap()

    assert validator.violations == []

def test_detects_precedence_violation():
    schedules = [
        {
            "scenario_id": "ANOM-TEST",
            "schedule_id": "SCH-003",
            "order_id": "ORD-001",
            "operation_id": "OP-001",
            "machine_id": "MACH-001",
            "start_time": "2026-11-02T08:00:00",
            "end_time": "2026-11-02T10:00:00",
        },
        {
            "scenario_id": "ANOM-TEST",
            "schedule_id": "SCH-004",
            "order_id": "ORD-001",
            "operation_id": "OP-002",
            "machine_id": "MACH-001",
            "start_time": "2026-11-02T09:00:00",
            "end_time": "2026-11-02T11:00:00",
        },
    ]

    validator = make_validator(schedules)
    validator.check_precedence()

    assert any(
        violation["issue_type"] == "PRECEDENCE_VIOLATION"
        for violation in validator.violations
    )


def test_accepts_valid_precedence():
    schedules = [
        {
            "scenario_id": "ANOM-TEST",
            "schedule_id": "SCH-005",
            "order_id": "ORD-001",
            "operation_id": "OP-001",
            "machine_id": "MACH-001",
            "start_time": "2026-11-02T08:00:00",
            "end_time": "2026-11-02T09:00:00",
        },
        {
            "scenario_id": "ANOM-TEST",
            "schedule_id": "SCH-006",
            "order_id": "ORD-001",
            "operation_id": "OP-002",
            "machine_id": "MACH-001",
            "start_time": "2026-11-02T09:00:00",
            "end_time": "2026-11-02T10:00:00",
        },
    ]

    validator = make_validator(schedules)
    validator.check_precedence()

    assert validator.violations == []

def test_detects_missing_changeover_time():
    data = {
        "machines": [{"machine_id": "MACH-001"}],
        "operations": [],
        "eligibility": [],
        "inventory": [],
        "changeovers": [
            {
                "machine_id": "MACH-001",
                "from_family": "FAMILY-A",
                "to_family": "FAMILY-B",
                "setup_minutes": "30",
            }
        ],
        "calendars": [],
        "schedules": [
            {
                "schedule_id": "SCH-011",
                "operation_id": "OP-001",
                "machine_id": "MACH-001",
                "product_family": "FAMILY-A",
                "start_time": "2026-11-02T08:00:00",
                "end_time": "2026-11-02T09:00:00",
            },
            {
                "schedule_id": "SCH-012",
                "operation_id": "OP-002",
                "machine_id": "MACH-001",
                "product_family": "FAMILY-B",
                "start_time": "2026-11-02T09:10:00",
                "end_time": "2026-11-02T10:00:00",
            },
        ],
    }

    validator = ConstraintValidator(data)
    validator.check_changeovers()

    assert any(
        violation["issue_type"] == "CHANGEOVER_OMITTED"
        for violation in validator.violations
    )

def test_detects_labor_capacity_exceeded():
    schedules = pd.DataFrame([
        {
            "schedule_id": "SCH-020",
            "required_skill": "CUTTING",
            "start_time": "2026-11-02 08:00",
            "end_time": "2026-11-02 10:00",
            "labor_required": 3,
        },
        {
            "schedule_id": "SCH-021",
            "required_skill": "CUTTING",
            "start_time": "2026-11-02 09:00",
            "end_time": "2026-11-02 11:00",
            "labor_required": 3,
        },
    ])

    labor_calendars = pd.DataFrame([
        {
            "skill": "CUTTING",
            "work_date": "2026-11-02",
            "start_time": "08:00",
            "end_time": "16:00",
            "is_working": True,
            "available_workers": 4,
        },
    ])

    violations = check_labor_capacity(schedules, labor_calendars)

    assert len(violations) == 1
    assert violations[0]["issue_type"] == "LABOR_CAPACITY_EXCEEDED"


def test_accepts_labor_within_capacity():
    schedules = pd.DataFrame([
        {
            "schedule_id": "SCH-022",
            "required_skill": "CUTTING",
            "start_time": "2026-11-02 08:00",
            "end_time": "2026-11-02 10:00",
            "labor_required": 2,
        },
        {
            "schedule_id": "SCH-023",
            "required_skill": "CUTTING",
            "start_time": "2026-11-02 09:00",
            "end_time": "2026-11-02 11:00",
            "labor_required": 2,
        },
    ])

    labor_calendars = pd.DataFrame([
        {
            "skill": "CUTTING",
            "work_date": "2026-11-02",
            "start_time": "08:00",
            "end_time": "16:00",
            "is_working": True,
            "available_workers": 4,
        },
    ])

    violations = check_labor_capacity(schedules, labor_calendars)

    assert violations == []


def test_accepts_sufficient_changeover_time():
    data = {
        "machines": [{"machine_id": "MACH-001"}],
        "operations": [],
        "eligibility": [],
        "inventory": [],
        "changeovers": [
            {
                "machine_id": "MACH-001",
                "from_family": "FAMILY-A",
                "to_family": "FAMILY-B",
                "setup_minutes": "30",
            }
        ],
        "calendars": [],
        "schedules": [
            {
                "schedule_id": "SCH-013",
                "operation_id": "OP-001",
                "machine_id": "MACH-001",
                "product_family": "FAMILY-A",
                "start_time": "2026-11-02T08:00:00",
                "end_time": "2026-11-02T09:00:00",
            },
            {
                "schedule_id": "SCH-014",
                "operation_id": "OP-002",
                "machine_id": "MACH-001",
                "product_family": "FAMILY-B",
                "start_time": "2026-11-02T09:30:00",
                "end_time": "2026-11-02T10:30:00",
            },
        ],
    }

    validator = ConstraintValidator(data)
    validator.check_changeovers()

    assert validator.violations == []

def test_detects_operation_outside_machine_shift():
    data = {
        "machines": [{"machine_id": "MACH-001"}],
        "operations": [],
        "eligibility": [],
        "inventory": [],
        "changeovers": [],
        "calendars": [
            {
                "machine_id": "MACH-001",
                "is_working": "true",
                "shift_start": "2026-11-02T08:00:00",
                "shift_end": "2026-11-02T16:00:00",
                "available_minutes": "480",
            }
        ],
        "schedules": [
            {
                "schedule_id": "SCH-009",
                "operation_id": "OP-004",
                "machine_id": "MACH-001",
                "start_time": "2026-11-02T17:00:00",
                "end_time": "2026-11-02T18:00:00",
            }
        ],
    }

    validator = ConstraintValidator(data)
    validator.check_machine_calendar()

    assert any(
        violation["issue_type"] == "OUTSIDE_SHIFT"
        for violation in validator.violations
    )


def test_accepts_operation_inside_machine_shift():
    data = {
        "machines": [{"machine_id": "MACH-001"}],
        "operations": [],
        "eligibility": [],
        "inventory": [],
        "changeovers": [],
        "calendars": [
            {
                "machine_id": "MACH-001",
                "is_working": "true",
                "shift_start": "2026-11-02T08:00:00",
                "shift_end": "2026-11-02T16:00:00",
                "available_minutes": "480",
            }
        ],
        "schedules": [
            {
                "schedule_id": "SCH-010",
                "operation_id": "OP-004",
                "machine_id": "MACH-001",
                "start_time": "2026-11-02T09:00:00",
                "end_time": "2026-11-02T10:00:00",
            }
        ],
    }

    validator = ConstraintValidator(data)
    validator.check_machine_calendar()

    assert validator.violations == []

def test_detects_material_unavailable():
    data = {
        "machines": [{"machine_id": "MACH-001"}],
        "operations": [],
        "eligibility": [],
        "inventory": [
            {
                "lot_id": "LOT-001",
                "material_id": "MAT-001",
                "available_at": "2026-11-02T10:00:00",
            }
        ],
        "changeovers": [],
        "calendars": [],
        "schedules": [
            {
                "schedule_id": "SCH-007",
                "operation_id": "OP-003",
                "machine_id": "MACH-001",
                "inventory_lot_id": "LOT-001",
                "material_id": "MAT-001",
                "start_time": "2026-11-02T08:00:00",
                "end_time": "2026-11-02T09:00:00",
            }
        ],
    }

    validator = ConstraintValidator(data)
    validator.check_material_availability()

    assert any(
        violation["issue_type"] == "MATERIAL_UNAVAILABLE"
        for violation in validator.violations
    )


def test_accepts_available_material():
    data = {
        "machines": [{"machine_id": "MACH-001"}],
        "operations": [],
        "eligibility": [],
        "inventory": [
            {
                "lot_id": "LOT-001",
                "material_id": "MAT-001",
                "available_at": "2026-11-02T08:00:00",
            }
        ],
        "changeovers": [],
        "calendars": [],
        "schedules": [
            {
                "schedule_id": "SCH-008",
                "operation_id": "OP-003",
                "machine_id": "MACH-001",
                "inventory_lot_id": "LOT-001",
                "material_id": "MAT-001",
                "start_time": "2026-11-02T09:00:00",
                "end_time": "2026-11-02T10:00:00",
            }
        ],
    }

    validator = ConstraintValidator(data)
    validator.check_material_availability()

    assert validator.violations == []

def test_detects_duplicate_schedule_id():
    schedules = [
        {
            "schedule_id": "SCH-100",
            "operation_id": "OP-001",
            "machine_id": "MACH-001",
            "start_time": "2026-11-02T08:00:00",
            "end_time": "2026-11-02T09:00:00",
        },
        {
            "schedule_id": "SCH-100",
            "operation_id": "OP-002",
            "machine_id": "MACH-001",
            "start_time": "2026-11-02T09:00:00",
            "end_time": "2026-11-02T10:00:00",
        },
    ]

    validator = make_validator(schedules)
    validator.check_schedule_integrity()

    assert any(
        v["issue_type"] == "DUPLICATE_SCHEDULE_ID"
        for v in validator.violations
    )


def test_detects_invalid_time_range():
    schedules = [
        {
            "schedule_id": "SCH-101",
            "operation_id": "OP-001",
            "machine_id": "MACH-001",
            "start_time": "2026-11-02T10:00:00",
            "end_time": "2026-11-02T09:00:00",
        },
    ]

    validator = make_validator(schedules)
    validator.check_schedule_integrity()

    assert any(
        v["issue_type"] == "INVALID_TIME_RANGE"
        for v in validator.violations
    )


def test_detects_unknown_machine():
    schedules = [
        {
            "schedule_id": "SCH-102",
            "operation_id": "OP-001",
            "machine_id": "MACH-999",
            "start_time": "2026-11-02T08:00:00",
            "end_time": "2026-11-02T09:00:00",
        },
    ]

    validator = make_validator(schedules)
    validator.check_schedule_integrity()

    assert any(
        v["issue_type"] == "UNKNOWN_MACHINE"
        for v in validator.violations
    )

def test_detects_unknown_operation():
    schedules = [
        {
            "schedule_id": "SCH-103",
            "operation_id": "OP-999",
            "machine_id": "MACH-001",
            "start_time": "2026-11-02T08:00:00",
            "end_time": "2026-11-02T09:00:00",
        },
    ]

    validator = make_validator(schedules)
    validator.check_machine_eligibility()

    assert any(
        v["issue_type"] == "UNKNOWN_OPERATION"
        for v in validator.violations
    )


def test_detects_ineligible_machine():
    schedules = [
        {
            "schedule_id": "SCH-104",
            "operation_id": "OP-001",
            "machine_id": "MACH-999",
            "start_time": "2026-11-02T08:00:00",
            "end_time": "2026-11-02T09:00:00",
        },
    ]

    validator = make_validator(schedules)
    validator.check_machine_eligibility()

    assert any(
        v["issue_type"] == "MACHINE_INELIGIBLE"
        for v in validator.violations
    )

def test_detects_unknown_inventory_lot():
    data = {
        "machines": [{"machine_id": "MACH-001"}],
        "operations": [],
        "eligibility": [],
        "inventory": [],
        "changeovers": [],
        "calendars": [],
        "schedules": [
            {
                "schedule_id": "SCH-105",
                "operation_id": "OP-001",
                "machine_id": "MACH-001",
                "inventory_lot_id": "LOT-999",
                "material_id": "MAT-001",
                "start_time": "2026-11-02T08:00:00",
                "end_time": "2026-11-02T09:00:00",
            }
        ],
    }

    validator = ConstraintValidator(data)
    validator.check_material_availability()

    assert any(
        v["issue_type"] == "UNKNOWN_INVENTORY_LOT"
        for v in validator.violations
    )


def test_detects_material_lot_mismatch():
    data = {
        "machines": [{"machine_id": "MACH-001"}],
        "operations": [],
        "eligibility": [],
        "inventory": [
            {
                "lot_id": "LOT-001",
                "material_id": "MAT-002",
                "available_at": "2026-11-02T07:00:00",
            }
        ],
        "changeovers": [],
        "calendars": [],
        "schedules": [
            {
                "schedule_id": "SCH-106",
                "operation_id": "OP-001",
                "machine_id": "MACH-001",
                "inventory_lot_id": "LOT-001",
                "material_id": "MAT-001",
                "start_time": "2026-11-02T08:00:00",
                "end_time": "2026-11-02T09:00:00",
            }
        ],
    }

    validator = ConstraintValidator(data)
    validator.check_material_availability()

    assert any(
        v["issue_type"] == "MATERIAL_LOT_MISMATCH"
        for v in validator.violations
    )

def test_detects_operation_during_non_working_shift():
    data = {
        "machines": [{"machine_id": "MACH-001"}],
        "operations": [],
        "eligibility": [],
        "inventory": [],
        "changeovers": [],
        "calendars": [
            {
                "machine_id": "MACH-001",
                "is_working": "false",
                "shift_start": "2026-11-02T08:00:00",
                "shift_end": "2026-11-02T16:00:00",
                "available_minutes": "480",
            }
        ],
        "schedules": [
            {
                "schedule_id": "SCH-107",
                "operation_id": "OP-001",
                "machine_id": "MACH-001",
                "start_time": "2026-11-02T09:00:00",
                "end_time": "2026-11-02T10:00:00",
            }
        ],
    }

    validator = ConstraintValidator(data)
    validator.check_machine_calendar()

    assert any(
        v["issue_type"] == "OUTSIDE_SHIFT"
        for v in validator.violations
    )


def test_detects_insufficient_shift_available_minutes():
    data = {
        "machines": [{"machine_id": "MACH-001"}],
        "operations": [],
        "eligibility": [],
        "inventory": [],
        "changeovers": [],
        "calendars": [
            {
                "machine_id": "MACH-001",
                "is_working": "true",
                "shift_start": "2026-11-02T08:00:00",
                "shift_end": "2026-11-02T16:00:00",
                "available_minutes": "30",
            }
        ],
        "schedules": [
            {
                "schedule_id": "SCH-108",
                "operation_id": "OP-001",
                "machine_id": "MACH-001",
                "start_time": "2026-11-02T09:00:00",
                "end_time": "2026-11-02T10:00:00",
            }
        ],
    }

    validator = ConstraintValidator(data)
    validator.check_machine_calendar()

    assert any(
        v["issue_type"] == "OUTSIDE_SHIFT"
        for v in validator.violations
    )

def test_detects_unknown_inventory_lot_in_quantity_check():
    schedules = pd.DataFrame([
        {
            "schedule_id": "SCH-109",
            "operation_id": "OP-001",
            "inventory_lot_id": "LOT-999",
            "material_id": "MAT-001",
        }
    ])

    material_demand = pd.DataFrame([
        {
            "operation_id": "OP-001",
            "material_id": "MAT-001",
            "required_quantity": 5,
        }
    ])

    inventory = pd.DataFrame(columns=["lot_id", "quantity"])

    violations = check_material_quantity(
        schedules, material_demand, inventory
    )

    assert len(violations) == 1
    assert violations[0]["issue_type"] == "UNKNOWN_INVENTORY_LOT"

def test_accepts_exact_changeover_time():
    data = {
        "machines": [{"machine_id": "MACH-001"}],
        "operations": [],
        "eligibility": [],
        "inventory": [],
        "changeovers": [
            {
                "machine_id": "MACH-001",
                "from_family": "FAMILY-A",
                "to_family": "FAMILY-B",
                "setup_minutes": "30",
            }
        ],
        "calendars": [],
        "schedules": [
            {
                "schedule_id": "SCH-110",
                "operation_id": "OP-001",
                "machine_id": "MACH-001",
                "product_family": "FAMILY-A",
                "start_time": "2026-11-02T08:00:00",
                "end_time": "2026-11-02T09:00:00",
            },
            {
                "schedule_id": "SCH-111",
                "operation_id": "OP-002",
                "machine_id": "MACH-001",
                "product_family": "FAMILY-B",
                "start_time": "2026-11-02T09:30:00",
                "end_time": "2026-11-02T10:30:00",
            },
        ],
    }

    validator = ConstraintValidator(data)
    validator.check_changeovers()

    assert validator.violations == []
