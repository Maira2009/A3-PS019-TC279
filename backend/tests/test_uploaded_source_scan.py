import io


def test_uploaded_csv_scans_and_unreadable_csv_is_reported_per_source(client):
    workspace = client.post("/api/v1/workspaces", json={"name": "Uploaded CSV scan"}).json()
    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/sources",
        files=[
            ("files", ("contacts.csv", io.BytesIO(b"name,phone\nAlice,9876543210\nBob,9876543211\n"), "text/csv")),
            ("files", ("broken.csv", io.BytesIO(b"name,phone\n\x81,9876543210\n"), "text/csv")),
        ],
    )
    assert response.status_code == 201
    sources = response.json()["items"]

    scan = client.post(
        f"/api/v1/workspaces/{workspace['id']}/scans",
        json={"source_ids": [source["id"] for source in sources], "options": {}},
    )
    assert scan.status_code == 201, scan.text
    result = scan.json()
    assert result["status"] == "partial"
    assert result["summary"]["successful_source_count"] == 1
    assert result["summary"]["failed_sources"][0]["source"] == "broken.csv"
    assert "encoding" in result["summary"]["failed_sources"][0]["error"]
    findings = client.get(f"/api/v1/scans/{result['id']}/findings").json()["items"]
    assert any(item["field_name"] == "phone" and item["class_key"] == "PHONE" for item in findings)

    failed_scan = client.post(
        f"/api/v1/workspaces/{workspace['id']}/scans",
        json={"source_ids": [sources[1]["id"]], "options": {}},
    )
    assert failed_scan.status_code == 201
    assert failed_scan.json()["status"] == "failed"
    saved = client.get(f"/api/v1/scans/{failed_scan.json()['id']}").json()
    assert saved["status"] == "failed"
