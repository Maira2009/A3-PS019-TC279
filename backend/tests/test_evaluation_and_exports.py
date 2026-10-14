import csv
import io

from app.evaluation import calculate_metrics
from app.exporting import csv_bytes


def test_hand_verifiable_metrics():
    gold = [
        {"dataset_key": "tiny", "source_name": "a", "object_name": "a", "field_name": "phone", "expected_class_key": "PHONE", "label": "positive"},
        {"dataset_key": "tiny", "source_name": "a", "object_name": "a", "field_name": "other", "expected_class_key": "NONE", "label": "negative"},
        {"dataset_key": "tiny", "source_name": "b", "object_name": "b", "field_name": "missed", "expected_class_key": "PHONE", "label": "positive"},
    ]
    predictions = [
        {"source_name": "a", "object_name": "a", "field_name": "phone", "class_key": "PHONE"},
        {"source_name": "a", "object_name": "a", "field_name": "other", "class_key": "PHONE"},
    ]
    phone = calculate_metrics(gold, predictions)["per_class"]["PHONE"]
    assert phone["tp"] == 1 and phone["fp"] == 1 and phone["fn"] == 1 and phone["tn"] == 0
    assert phone["precision"] == 0.5 and phone["recall"] == 0.5


def test_formula_injection_is_neutralized():
    data = csv_bytes([{"field": "=HYPERLINK(\"bad\")", "safe": "text"}]).decode("utf-8-sig")
    row = next(csv.DictReader(io.StringIO(data)))
    assert row["field"].startswith("'=")


def test_evaluation_and_masked_exports(client, demo):
    scan_id = demo["scan"]["id"]
    result = client.post(f"/api/v1/scans/{scan_id}/evaluation")
    assert result.status_code == 200
    body = result.json()
    assert body["labelled_count"] >= 15
    assert set(body["per_class"]) == {"PHONE", "EMAIL", "PERSON_NAME", "ADDRESS", "PERSONAL_ID"}
    assert all("tp" in metrics and "precision" in metrics for metrics in body["per_class"].values())

    for export_type in ["inventory_csv", "footprints_json", "footprints_csv", "evidence_gaps_csv", "review_history_csv", "metrics_json", "metrics_csv", "report_md", "report_html"]:
        response = client.get(f"/api/v1/scans/{scan_id}/exports/{export_type}")
        assert response.status_code == 200, (export_type, response.text)
        assert b"9876543210" not in response.content
        assert b"aarav.demo@example.com" not in response.content
        assert b"hmac" not in response.content.lower()

