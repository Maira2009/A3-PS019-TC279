import hashlib
from pathlib import Path


def test_demo_end_to_end(client, demo):
    workspace_id = demo["workspace"]["id"]
    scan_id = demo["scan"]["id"]
    sources = client.get(f"/api/v1/workspaces/{workspace_id}/sources").json()["items"]
    assert {s["display_name"] for s in sources} == {"admissions.csv", "events.csv", "support.db"}

    findings = client.get(f"/api/v1/scans/{scan_id}/findings?limit=500").json()["items"]
    keys = {(f["source_name"], f["field_name"], f["class_key"]) for f in findings}
    assert ("admissions.csv", "guardian_phone", "PHONE") in keys
    assert ("events.csv", "Phone Data Detected", "PHONE") in keys
    assert ("support.db", "mobile", "PHONE") in keys
    assert not any(field in {"phone_model", "email_template_name", "fee_amount", "retry_count"} for _, field, _ in keys)
    assert all("9876543210" not in str(f) for f in findings)

    footprints = client.get(f"/api/v1/scans/{scan_id}/footprints?limit=500").json()["items"]
    phone_groups = [f for f in footprints if f["class_key"] == "PHONE" and f["source_count"] == 3]
    assert phone_groups
    assert phone_groups[0]["overlap_type"] == "cross_source"
    assert "proof of identity" in phone_groups[0]["ambiguity_note"]

    gaps = client.get(f"/api/v1/scans/{scan_id}/evidence-gaps?limit=500").json()["items"]
    assert any(f["purpose_status"] == "missing" and f["retention_status"] == "present" for f in gaps)
    assert any(f["purpose_status"] == "present" and f["retention_status"] == "missing" for f in gaps)


def test_sqlite_demo_source_is_not_modified(client, demo):
    source = next(s for s in demo["sources"] if s["display_name"] == "support.db")
    from app.db import connect
    with connect() as con:
        path = Path(con.execute("SELECT stored_path FROM sources WHERE id=?", (source["id"],)).fetchone()[0])
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    response = client.post(f"/api/v1/sources/{source['id']}/profile")
    assert response.status_code == 200
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    assert before == after


def test_review_history_is_append_only(client, demo):
    scan_id = demo["scan"]["id"]
    finding = client.get(f"/api/v1/scans/{scan_id}/findings").json()["items"][0]
    first = client.post(f"/api/v1/findings/{finding['id']}/review", json={"decision": "accepted", "reviewer_label": "Tester", "note": "First decision"})
    second = client.post(f"/api/v1/findings/{finding['id']}/review", json={"decision": "review_later", "reviewer_label": "Tester", "note": "Needs owner evidence"})
    assert first.status_code == second.status_code == 200
    history = client.get(f"/api/v1/findings/{finding['id']}/review-history").json()["items"]
    assert [event["new_status"] for event in history] == ["accepted", "review_later"]
    assert history[1]["previous_status"] == "accepted"

