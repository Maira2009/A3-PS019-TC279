import io
from pathlib import Path


def test_rejects_unsupported_and_corrupt_files(client):
    workspace = client.post("/api/v1/workspaces", json={"name": "Validation"}).json()
    unsupported = client.post(
        f"/api/v1/workspaces/{workspace['id']}/sources",
        files=[("files", ("notes.txt", io.BytesIO(b"hello"), "text/plain"))],
    )
    assert unsupported.status_code == 400
    assert unsupported.json()["error"]["code"] == "INVALID_FILE"
    corrupt = client.post(
        f"/api/v1/workspaces/{workspace['id']}/sources",
        files=[("files", ("bad.db", io.BytesIO(b"not sqlite"), "application/octet-stream"))],
    )
    assert corrupt.status_code == 400
    assert corrupt.json()["error"]["code"] == "INVALID_SQLITE"


def test_empty_csv_warns_without_crashing(client):
    workspace = client.post("/api/v1/workspaces", json={"name": "Empty source"}).json()
    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/sources",
        files=[("files", ("empty.csv", io.BytesIO(b""), "text/csv"))],
    )
    assert response.status_code == 201
    source = response.json()["items"][0]
    assert source["status"] == "warning" and "EMPTY_SOURCE" in source["warnings"]
    profile = client.post(f"/api/v1/sources/{source['id']}/profile")
    assert profile.status_code == 200 and profile.json()["total"] == 0


def test_workspace_deletion_requires_confirmation_and_removes_copy(client, demo):
    workspace_id = demo["workspace"]["id"]
    from app.db import connect
    with connect() as con:
        path = Path(con.execute("SELECT stored_path FROM sources WHERE workspace_id=? LIMIT 1", (workspace_id,)).fetchone()[0])
    assert path.exists()
    assert client.delete(f"/api/v1/workspaces/{workspace_id}").status_code == 400
    response = client.delete(f"/api/v1/workspaces/{workspace_id}?confirm=true")
    assert response.status_code == 200 and response.json()["original_files_untouched"] is True
    assert not path.exists()
