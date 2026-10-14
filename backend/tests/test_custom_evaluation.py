import csv
import io


def test_custom_scan_requires_its_own_labels_and_evaluates_uploaded_csv(client):
    workspace = client.post("/api/v1/workspaces", json={"name": "My data"}).json()
    upload = client.post(
        f"/api/v1/workspaces/{workspace['id']}/sources",
        files={"files": ("contacts.csv", b"name,phone\nAlice,9876543210\nBob,9876543211\n", "text/csv")},
    )
    assert upload.status_code == 201
    source_id = upload.json()["items"][0]["id"]
    scan = client.post(f"/api/v1/workspaces/{workspace['id']}/scans", json={"source_ids": [source_id]})
    assert scan.status_code == 201
    scan_id = scan.json()["id"]

    status = client.get(f"/api/v1/scans/{scan_id}/evaluation/labels")
    assert status.status_code == 200
    assert status.json()["labelled_count"] == 0
    blocked = client.post(f"/api/v1/scans/{scan_id}/evaluation")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "LABELS_REQUIRED"

    template = client.get(f"/api/v1/scans/{scan_id}/evaluation/labels-template")
    assert template.status_code == 200
    rows = list(csv.DictReader(io.StringIO(template.content.decode("utf-8-sig"))))
    assert {row["field_name"] for row in rows} == {"name", "phone"}
    for row in rows:
        row["expected_class_key"] = "PHONE" if row["field_name"] == "phone" else "NONE"
        row["label"] = "positive" if row["field_name"] == "phone" else "negative"
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    labels = client.post(
        f"/api/v1/scans/{scan_id}/evaluation/labels",
        files={"file": ("labels.csv", output.getvalue().encode(), "text/csv")},
    )
    assert labels.status_code == 200, labels.text
    assert labels.json()["labelled_count"] == 2
    evaluation = client.post(f"/api/v1/scans/{scan_id}/evaluation")
    assert evaluation.status_code == 200, evaluation.text
    assert evaluation.json()["labelled_count"] == 2
    assert evaluation.json()["dataset_key"] == "my-dataset-v1"
    assert evaluation.json()["per_class"]["PHONE"]["tp"] == 1

    wrong = output.getvalue().replace("contacts.csv", "unrelated.csv")
    rejected = client.post(
        f"/api/v1/scans/{scan_id}/evaluation/labels",
        files={"file": ("wrong.csv", wrong.encode(), "text/csv")},
    )
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "LABEL_FIELD_MISMATCH"
    assert client.get(f"/api/v1/scans/{scan_id}/evaluation/labels").json()["labelled_count"] == 2


def test_demo_scan_has_bundled_labels_only_on_that_scan(client, demo):
    demo_scan = demo["scan"]["id"]
    labels = client.get(f"/api/v1/scans/{demo_scan}/evaluation/labels").json()
    assert labels["dataset_key"] == "demo-v1"
    assert labels["labelled_count"] == 19
