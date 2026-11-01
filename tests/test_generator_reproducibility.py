import hashlib
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def calculate_file_hash(file_path):
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def test_master_data_generation_is_reproducible(tmp_path):
    output_directories = []

    for run_number in range(2):
        working_directory = tmp_path / f"run_{run_number}"
        working_directory.mkdir()

        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(PROJECT_ROOT)

        subprocess.run(
            [sys.executable, "-m", "generator.master_data"],
            cwd=working_directory,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )

        output_directories.append(
            working_directory / "data" / "raw"
        )

    first_files = sorted(
        path.name for path in output_directories[0].glob("*.csv")
    )
    second_files = sorted(
        path.name for path in output_directories[1].glob("*.csv")
    )

    assert first_files
    assert first_files == second_files

    for filename in first_files:
        first_hash = calculate_file_hash(
            output_directories[0] / filename
        )
        second_hash = calculate_file_hash(
            output_directories[1] / filename
        )

        assert first_hash == second_hash, (
            f"Generated file differs between runs: {filename}"
        )
def test_transaction_generation_is_reproducible(tmp_path):
    output_directories = []

    for run_number in range(2):
        working_directory = tmp_path / f"transaction_run_{run_number}"
        working_directory.mkdir()

        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(PROJECT_ROOT)

        # Generate master data first.
        subprocess.run(
            [sys.executable, "-m", "generator.master_data"],
            cwd=working_directory,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )

        # Generate transaction data.
        subprocess.run(
            [sys.executable, "-m", "generator.transaction"],
            cwd=working_directory,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )

        output_directories.append(
            working_directory / "data" / "raw"
        )

    transaction_files = [
        "production_orders.csv",
        "order_operations.csv",
        "inventory_lots.csv",
        "order_material_demand.csv",
        "shared_tooling_assignments.csv",
    ]

    for filename in transaction_files:
        first_hash = calculate_file_hash(
            output_directories[0] / filename
        )
        second_hash = calculate_file_hash(
            output_directories[1] / filename
        )

        assert first_hash == second_hash, (
            f"Transaction output differs between runs: {filename}"
        )
def test_anomaly_generation_is_reproducible(tmp_path):
    output_directories = []

    for run_number in range(2):
        working_directory = tmp_path / f"anomaly_run_{run_number}"
        working_directory.mkdir()

        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(PROJECT_ROOT)

        raw_directory = working_directory / "data" / "raw"
        raw_directory.mkdir(parents=True)

        # Generate the prerequisite master and transaction data.
        subprocess.run(
            [sys.executable, "-m", "generator.master_data"],
            cwd=working_directory,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )

        subprocess.run(
            [sys.executable, "-m", "generator.transaction"],
            cwd=working_directory,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )

        subprocess.run(
            [sys.executable, "-m", "generator.anomaly_generator"],
            cwd=working_directory,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )

        output_directories.append(working_directory / "data")

    files_to_compare = [
        ("test_fixtures", "anomaly_scenarios.csv"),
        ("ground_truth", "ground_truth.csv"),
    ]

    for folder, filename in files_to_compare:
        first_hash = calculate_file_hash(
            output_directories[0] / folder / filename
        )
        second_hash = calculate_file_hash(
            output_directories[1] / folder / filename
        )

        assert first_hash == second_hash, (
            f"Anomaly output differs between runs: {filename}"
        )