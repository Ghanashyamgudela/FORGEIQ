
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_project_directories_exist():
    required_dirs = [
        "generator",
        "scheduler",
        "validations",
        "database",
        "dashboard",
        "data/raw",
        "data/processed",
    ]

    for directory in required_dirs:
        assert (ROOT / directory).is_dir(), (
            f"Required project directory is missing: {directory}"
        )


def test_required_generator_files_exist():
    required_files = [
        "generator/config.py",
        "generator/master_data.py",
        "generator/transaction.py",
        "generator/anomaly_generator.py",
        "generator/labor_data.py",
    ]

    for filename in required_files:
        assert (ROOT / filename).is_file(), (
            f"Required generator file is missing: {filename}"
        )


def test_required_application_files_exist():
    required_files = [
        "scheduler/cp_sat_optimizer.py",
        "validations/validators.py",
        "database/models.py",
        "dashboard/app.py",
    ]

    for filename in required_files:
        assert (ROOT / filename).is_file(), (
            f"Required application file is missing: {filename}"
        )
