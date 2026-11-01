
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GROUND_TRUTH_FILE = ROOT / "data" / "ground_truth" / "ground_truth.csv"
VALIDATION_FILE = ROOT / "data" / "processed" / "validation_report.csv"
OUTPUT_DIR = ROOT / "data" / "processed"


def load_csv(file_path):
    with open(file_path, "r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def parse_schedule_ids(value):
    return {
        item.strip()
        for item in (value or "").split("|")
        if item.strip()
    }


def evaluate():

    # Check input files
    if not GROUND_TRUTH_FILE.exists():
        raise FileNotFoundError(
            f"Ground truth not found: {GROUND_TRUTH_FILE}"
        )

    if not VALIDATION_FILE.exists():
        raise FileNotFoundError(
            f"Validation report not found: {VALIDATION_FILE}. "
            "Run python -m validations.validators first."
        )

    ground_truth = load_csv(GROUND_TRUTH_FILE)
    detections = load_csv(VALIDATION_FILE)

    # Remove incomplete rows
    ground_truth = [
        row for row in ground_truth
        if row.get("scenario_id") and row.get("issue_type")
    ]

    detections = [
        row for row in detections
        if row.get("issue_type") and row.get("affected_schedule_ids")
    ]

    primary_ground_truth = [
        row for row in ground_truth
        if row["scenario_id"].startswith("ANOM-")
    ]
    secondary_ground_truth = [
        row for row in ground_truth
        if row["scenario_id"].startswith("SEC-")
    ]
    expected_issue_types = {
        row["issue_type"] for row in ground_truth
    }

    matched_detection_indexes = set()
    scenario_results = []

    # Match each expected anomaly with a detected violation
    for expected in ground_truth:

        expected_type = expected["issue_type"]
        expected_ids = parse_schedule_ids(
            expected.get("affected_schedule_ids", "")
        )

        match_index = None

        # Search all detections for this expected scenario
        for index, detected in enumerate(detections):

            if index in matched_detection_indexes:
                continue

            detected_type = detected["issue_type"]
            detected_ids = parse_schedule_ids(
                detected["affected_schedule_ids"]
            )

            if (
                detected_type == expected_type
                and detected_ids == expected_ids
            ):
                match_index = index
                break

        # Process the result after searching all detections.
        if match_index is not None:
            matched_detection_indexes.add(match_index)
            result = "DETECTED"
            detected_ids_text = detections[match_index]["affected_schedule_ids"]
        else:
            result = "MISSED"
            detected_ids_text = ""

        # Append exactly one result per expected scenario.
        scenario_results.append({
            "scenario_id": expected["scenario_id"],
            "finding_class": (
                "SECONDARY"
                if expected["scenario_id"].startswith("SEC-")
                else "PRIMARY"
            ),
            "issue_type": expected_type,
            "expected_schedule_ids": expected.get("affected_schedule_ids", ""),
            "detected_schedule_ids": detected_ids_text,
            "result": result,
        })

    # Calculate metrics once, after all scenarios are checked.
    relevant_detection_indexes = set(range(len(detections)))
    true_positives = len(matched_detection_indexes)
    false_positives = len(
        relevant_detection_indexes - matched_detection_indexes
    )
    false_negatives = len(ground_truth) - true_positives
    primary_true_positives = sum(
        1 for row in scenario_results
        if row["finding_class"] == "PRIMARY"
        and row["result"] == "DETECTED"
    )
    secondary_true_positives = sum(
        1 for row in scenario_results
        if row["finding_class"] == "SECONDARY"
        and row["result"] == "DETECTED"
    )

    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives > 0 else 0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives > 0 else 0
    )
    f1_score = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0 else 0
    )

    additional_findings = [
        row for row in detections
        if row["issue_type"] not in expected_issue_types
    ]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save scenario results.
    scenario_file = OUTPUT_DIR / "scenario_evaluation.csv"
    with open(scenario_file, "w", newline="", encoding="utf-8") as file:
        fieldnames = [
            "scenario_id",
            "finding_class",
            "issue_type",
            "expected_schedule_ids",
            "detected_schedule_ids",
            "result",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(scenario_results)

    # Save metrics.
    summary_file = OUTPUT_DIR / "evaluation_summary.csv"
    metrics = [
        ("Total expected findings", len(ground_truth)),
        ("Primary expected findings", len(primary_ground_truth)),
        ("Secondary expected findings", len(secondary_ground_truth)),
        ("True positives", true_positives),
        ("Primary true positives", primary_true_positives),
        ("Secondary true positives", secondary_true_positives),
        ("False positives", false_positives),
        ("False negatives", false_negatives),
        ("Precision", round(precision, 4)),
        ("Recall", round(recall, 4)),
        ("F1 score", round(f1_score, 4)),
    ]
    with open(summary_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["metric", "value"])
        writer.writerows(metrics)

    # Display report.
    print("\nFORGEIQ ANOMALY EVALUATION")
    print("=" * 45)
    print(f"Expected scenarios : {len(ground_truth)}")
    print(f"True positives     : {true_positives}")
    print(f"False positives    : {false_positives}")
    print(f"False negatives    : {false_negatives}")
    print("\nEVALUATION METRICS")
    print("-" * 45)
    print(f"Precision          : {precision:.2%}")
    print(f"Recall             : {recall:.2%}")
    print(f"F1 Score           : {f1_score:.2%}")
    print("\nSCENARIO RESULTS")
    print("-" * 45)
    for result in scenario_results:
        print(
            f"{result['scenario_id']} | "
            f"{result['issue_type']} | "
            f"{result['result']}"
        )

    if additional_findings:
        print("\nADDITIONAL CONSTRAINT FINDINGS")
        print("-" * 45)
        for finding in additional_findings:
            print(
                f"{finding['issue_type']} | "
                f"{finding['affected_schedule_ids']}"
            )

    print("\nFILES SAVED")
    print("-" * 45)
    print(scenario_file)
    print(summary_file)



if __name__ == "__main__":
    evaluate()
