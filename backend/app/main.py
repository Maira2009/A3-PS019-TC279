from __future__ import annotations

import csv
import io
import json
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import Body, FastAPI, File, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from . import __version__
from .config import ALLOWED_ORIGINS, DEMO_DIR, MAX_UPLOAD_BYTES, UPLOAD_DIR, ensure_dirs
from .db import audit, connect, init_db, new_id, utcnow
from .errors import AppError, app_error_handler, unexpected_error_handler, validation_error_handler
from .evaluation import load_gold, parse_label_csv, label_template, run_evaluation, save_labels
from .exporting import export_data
from .processing import mask_value, paged_query, read_source, run_scan
from .rules import get_rules, restore_defaults, save_rules

@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_dirs()
    init_db()
    get_rules()
    yield


app = FastAPI(title="DATAQUEST API", version=__version__, docs_url="/docs", redoc_url=None, lifespan=lifespan)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unexpected_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


class WorkspaceIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ScanIn(BaseModel):
    source_ids: list[str]
    options: dict[str, Any] = Field(default_factory=dict)


class ReviewIn(BaseModel):
    decision: Literal["accepted", "rejected", "review_later"]
    reviewer_label: str = Field(default="Local reviewer", max_length=120)
    note: str = Field(default="", max_length=2000)


class MetadataIn(BaseModel):
    source_id: str | None = None
    object_name: str | None = None
    field_name: str | None = None
    class_key: str | None = None
    purpose_text: str | None = None
    retention_duration: str | None = None
    retention_basis: str | None = None
    last_reviewed_at: str | None = None
    owner_label: str | None = None
    evidence_reference: str | None = None


def require_row(con, sql: str, params: tuple[Any, ...], label: str) -> dict[str, Any]:
    row = con.execute(sql, params).fetchone()
    if not row:
        raise AppError("NOT_FOUND", f"{label} not found.", 404)
    return dict(row)


def decode(item: dict[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        if key in item:
            item[key.removesuffix("_json")] = json.loads(item.pop(key) or "null")
    return item


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "version": __version__, "local_only": True}


@app.get("/api/v1/workspaces")
def list_workspaces(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    return paged_query("SELECT id,name,created_at,status,config_json FROM workspaces WHERE status!='deleted' ORDER BY created_at DESC", [], limit, offset)


@app.post("/api/v1/workspaces", status_code=201)
def create_workspace(payload: WorkspaceIn) -> dict[str, Any]:
    workspace = {"id": new_id(), "name": payload.name.strip(), "created_at": utcnow(), "status": "active", "config": {}}
    with connect() as con:
        con.execute("INSERT INTO workspaces VALUES (?,?,?,?,?)",
                    (workspace["id"], workspace["name"], workspace["created_at"], "active", "{}"))
        audit(con, workspace["id"], "workspace_created", "workspace", workspace["id"], {"name": workspace["name"]})
    return workspace


@app.get("/api/v1/workspaces/{workspace_id}")
def get_workspace(workspace_id: str) -> dict[str, Any]:
    with connect() as con:
        item = require_row(con, "SELECT * FROM workspaces WHERE id=? AND status!='deleted'", (workspace_id,), "Workspace")
    return decode(item, "config_json")


@app.delete("/api/v1/workspaces/{workspace_id}")
def delete_workspace(workspace_id: str, confirm: bool = Query(False)) -> dict[str, Any]:
    if not confirm:
        raise AppError("CONFIRMATION_REQUIRED", "Set confirm=true to delete copied uploads and workspace results.", 400)
    with connect() as con:
        require_row(con, "SELECT * FROM workspaces WHERE id=?", (workspace_id,), "Workspace")
        paths = [Path(r[0]) for r in con.execute("SELECT stored_path FROM sources WHERE workspace_id=?", (workspace_id,)).fetchall()]
        counts = {
            "sources": con.execute("SELECT COUNT(*) FROM sources WHERE workspace_id=?", (workspace_id,)).fetchone()[0],
            "scans": con.execute("SELECT COUNT(*) FROM scans WHERE workspace_id=?", (workspace_id,)).fetchone()[0],
        }
        con.execute("DELETE FROM audit_events WHERE workspace_id=?", (workspace_id,))
        con.execute("DELETE FROM workspaces WHERE id=?", (workspace_id,))
    for path in paths:
        if path.is_file() and UPLOAD_DIR in path.resolve().parents:
            path.unlink(missing_ok=True)
    return {"deleted": True, "removed": counts, "original_files_untouched": True}


def extension_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in {".db", ".sqlite", ".sqlite3"}:
        return "sqlite"
    raise AppError("INVALID_FILE", "Supported files are CSV, DB, SQLITE, and SQLITE3.", 400, {"file": Path(filename).name})


async def store_upload(workspace_id: str, upload: UploadFile) -> dict[str, Any]:
    display_name = Path(upload.filename or "upload").name
    source_type = extension_type(display_name)
    source_id = new_id()
    suffix = Path(display_name).suffix.lower()
    target = UPLOAD_DIR / f"{source_id}{suffix}"
    size = 0
    with target.open("wb") as output:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                output.close(); target.unlink(missing_ok=True)
                raise AppError("FILE_TOO_LARGE", f"{display_name} exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.", 413)
            output.write(chunk)
    warnings: list[str] = []
    status = "ready"
    if size == 0:
        warnings.append("EMPTY_SOURCE")
        status = "warning"
    if source_type == "sqlite" and size and target.read_bytes()[:16] != b"SQLite format 3\x00":
        target.unlink(missing_ok=True)
        raise AppError("INVALID_SQLITE", f"{display_name} is not a valid SQLite database.", 400)
    source = {
        "id": source_id, "workspace_id": workspace_id, "display_name": display_name,
        "source_type": source_type, "stored_path": str(target), "file_size_bytes": size,
        "created_at": utcnow(), "status": status, "warnings": warnings,
    }
    with connect() as con:
        require_row(con, "SELECT * FROM workspaces WHERE id=?", (workspace_id,), "Workspace")
        con.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?)",
                    (source_id, workspace_id, display_name, source_type, str(target), size,
                     source["created_at"], status, json.dumps(warnings)))
        audit(con, workspace_id, "source_uploaded", "source", source_id,
              {"display_name": display_name, "source_type": source_type, "file_size_bytes": size})
    return source


@app.post("/api/v1/workspaces/{workspace_id}/sources", status_code=201)
async def upload_sources(workspace_id: str, files: list[UploadFile] = File(...)) -> dict[str, Any]:
    items = [await store_upload(workspace_id, upload) for upload in files]
    return {"items": items, "total": len(items)}


@app.get("/api/v1/workspaces/{workspace_id}/sources")
def list_sources(workspace_id: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    result = paged_query("SELECT id,workspace_id,display_name,source_type,file_size_bytes,created_at,status,warning_json FROM sources WHERE workspace_id=? ORDER BY created_at", [workspace_id], limit, offset)
    return result


@app.get("/api/v1/sources/{source_id}")
def get_source(source_id: str) -> dict[str, Any]:
    with connect() as con:
        item = require_row(con, "SELECT id,workspace_id,display_name,source_type,file_size_bytes,created_at,status,warning_json FROM sources WHERE id=?", (source_id,), "Source")
    return decode(item, "warning_json")


@app.delete("/api/v1/sources/{source_id}")
def delete_source(source_id: str, confirm: bool = Query(False)) -> dict[str, Any]:
    if not confirm:
        raise AppError("CONFIRMATION_REQUIRED", "Set confirm=true to remove the copied source and related scan results.", 400)
    with connect() as con:
        source = require_row(con, "SELECT * FROM sources WHERE id=?", (source_id,), "Source")
        scan_ids = [r[0] for r in con.execute("SELECT DISTINCT scan_id FROM profiles WHERE source_id=?", (source_id,)).fetchall()]
        for scan_id in scan_ids:
            con.execute("DELETE FROM scans WHERE id=?", (scan_id,))
        con.execute("DELETE FROM sources WHERE id=?", (source_id,))
        audit(con, source["workspace_id"], "source_deleted", "source", source_id, {"display_name": source["display_name"]})
    path = Path(source["stored_path"])
    if path.is_file() and UPLOAD_DIR in path.resolve().parents:
        path.unlink(missing_ok=True)
    return {"deleted": True, "original_file_untouched": True}


def source_profile(source_id: str) -> dict[str, Any]:
    with connect() as con:
        source = require_row(con, "SELECT * FROM sources WHERE id=?", (source_id,), "Source")
    fields = read_source(source, 1000)
    items = []
    for field in fields:
        values = [v for v in field.values if v is not None and str(v).strip()]
        items.append({
            "object_name": field.object_name, "field_name": field.field_name,
            "row_count": field.row_count, "null_count": len(field.values) - len(values),
            "distinct_count": len({str(v) for v in values}), "masked_samples": [mask_value(v) for v in values[:3]],
            "warnings": field.warnings,
        })
    return {"source_id": source_id, "items": items, "total": len(items)}


@app.post("/api/v1/sources/{source_id}/profile")
def profile_source(source_id: str) -> dict[str, Any]:
    return source_profile(source_id)


@app.get("/api/v1/sources/{source_id}/schema")
def get_source_schema(source_id: str) -> dict[str, Any]:
    return source_profile(source_id)


@app.get("/api/v1/rules")
def rules_get() -> dict[str, Any]:
    version, rules = get_rules()
    return {"version": version, "items": rules}


@app.put("/api/v1/rules")
def rules_put(payload: list[dict[str, Any]] = Body(...)) -> dict[str, Any]:
    version, rules = save_rules(payload)
    return {"version": version, "items": rules}


@app.post("/api/v1/rules/restore-defaults")
def rules_restore(confirm: bool = Query(False)) -> dict[str, Any]:
    if not confirm:
        raise AppError("CONFIRMATION_REQUIRED", "Set confirm=true to restore default rules.", 400)
    version, rules = restore_defaults()
    return {"version": version, "items": rules}


@app.post("/api/v1/workspaces/{workspace_id}/scans", status_code=201)
def create_scan(workspace_id: str, payload: ScanIn) -> dict[str, Any]:
    version, rules = get_rules()
    scan_id = new_id()
    config = {"source_ids": payload.source_ids, "options": payload.options, "rule_version": version, "rules": rules}
    with connect() as con:
        require_row(con, "SELECT * FROM workspaces WHERE id=?", (workspace_id,), "Workspace")
        con.execute("INSERT INTO scans VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (scan_id, workspace_id, utcnow(), None, "queued", "queued", json.dumps(config), None, None, None))
    try:
        summary = run_scan(scan_id, workspace_id, payload.source_ids, payload.options)
    except AppError as exc:
        with connect() as con:
            con.execute("UPDATE scans SET status='failed',stage='failed',finished_at=?,error_code=?,error_message_safe=? WHERE id=?",
                        (utcnow(), exc.code, exc.message, scan_id))
        raise
    status = "failed" if summary["failed_sources"] and summary["successful_source_count"] == 0 else "partial" if summary["failed_sources"] else "completed"
    return {"id": scan_id, "status": status, "summary": summary}


def scan_item(scan_id: str) -> dict[str, Any]:
    with connect() as con:
        item = require_row(con, "SELECT * FROM scans WHERE id=?", (scan_id,), "Scan")
    return decode(item, "config_snapshot_json", "summary_json")


@app.get("/api/v1/scans/{scan_id}")
def get_scan(scan_id: str) -> dict[str, Any]:
    return scan_item(scan_id)


@app.get("/api/v1/scans/{scan_id}/progress")
def get_scan_progress(scan_id: str) -> dict[str, Any]:
    item = scan_item(scan_id)
    return {key: item.get(key) for key in ("id", "status", "stage", "started_at", "finished_at", "error_code", "error_message_safe")}


@app.get("/api/v1/scans/{scan_id}/summary")
def get_scan_summary(scan_id: str) -> dict[str, Any]:
    item = scan_item(scan_id)
    return item.get("summary") or {}


@app.get("/api/v1/scans/{scan_id}/profiles")
def scan_profiles(scan_id: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    return paged_query("SELECT * FROM profiles WHERE scan_id=? ORDER BY source_id,object_name,field_name", [scan_id], limit, offset)


@app.get("/api/v1/scans/{scan_id}/findings")
def scan_findings(scan_id: str, limit: int = 100, offset: int = 0,
                  class_key: str | None = None, review_status: str | None = None,
                  purpose_status: str | None = None, retention_status: str | None = None) -> dict[str, Any]:
    clauses = ["f.scan_id=?"]
    params: list[Any] = [scan_id]
    for column, value in (("class_key", class_key), ("review_status", review_status),
                          ("purpose_status", purpose_status), ("retention_status", retention_status)):
        if value:
            clauses.append(f"f.{column}=?"); params.append(value)
    sql = """SELECT f.*,s.display_name source_name FROM findings f JOIN sources s ON s.id=f.source_id
             WHERE """ + " AND ".join(clauses) + " ORDER BY f.rule_strength DESC,f.field_name"
    return paged_query(sql, params, limit, offset)


@app.get("/api/v1/scans/{scan_id}/footprints")
def scan_footprints(scan_id: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    return paged_query("SELECT * FROM footprints WHERE scan_id=? ORDER BY source_count DESC,occurrence_count DESC", [scan_id], limit, offset)


@app.get("/api/v1/scans/{scan_id}/evidence-gaps")
def evidence_gaps(scan_id: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    return paged_query("SELECT * FROM findings WHERE scan_id=? AND (purpose_status!='present' OR retention_status!='present') ORDER BY field_name", [scan_id], limit, offset)


@app.get("/api/v1/findings/{finding_id}")
def get_finding(finding_id: str) -> dict[str, Any]:
    with connect() as con:
        item = require_row(con, "SELECT f.*,s.display_name source_name FROM findings f JOIN sources s ON s.id=f.source_id WHERE f.id=?", (finding_id,), "Finding")
    return decode(item, "reason_codes_json", "masked_samples_json")


@app.post("/api/v1/findings/{finding_id}/review")
def review_finding(finding_id: str, payload: ReviewIn) -> dict[str, Any]:
    with connect() as con:
        finding = require_row(con, "SELECT f.*,sc.workspace_id FROM findings f JOIN scans sc ON sc.id=f.scan_id WHERE f.id=?", (finding_id,), "Finding")
        event = {"id": new_id(), "previous_status": finding["review_status"], "new_status": payload.decision,
                 "reviewer_label": payload.reviewer_label.strip() or "Local reviewer", "note": payload.note, "created_at": utcnow()}
        con.execute("UPDATE findings SET review_status=? WHERE id=?", (payload.decision, finding_id))
        con.execute("INSERT INTO review_events VALUES (?,?,?,?,?,?,?,?,?)",
                    (event["id"], finding["workspace_id"], finding["scan_id"], finding_id,
                     event["previous_status"], event["new_status"], event["reviewer_label"], event["note"], event["created_at"]))
        audit(con, finding["workspace_id"], "finding_reviewed", "finding", finding_id,
              {"previous_status": event["previous_status"], "new_status": event["new_status"]})
    return event


@app.get("/api/v1/findings/{finding_id}/review-history")
def review_history(finding_id: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    return paged_query("SELECT * FROM review_events WHERE finding_id=? ORDER BY created_at", [finding_id], limit, offset)


@app.get("/api/v1/workspaces/{workspace_id}/metadata")
def metadata_list(workspace_id: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    return paged_query("SELECT * FROM metadata_declarations WHERE workspace_id=? ORDER BY updated_at DESC", [workspace_id], limit, offset)


def insert_metadata(workspace_id: str, payload: MetadataIn) -> dict[str, Any]:
    item = {"id": new_id(), "workspace_id": workspace_id, **payload.model_dump(), "created_at": utcnow(), "updated_at": utcnow()}
    with connect() as con:
        require_row(con, "SELECT * FROM workspaces WHERE id=?", (workspace_id,), "Workspace")
        con.execute("INSERT INTO metadata_declarations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", tuple(item.values()))
        audit(con, workspace_id, "metadata_created", "metadata", item["id"], {"scope": {k: item[k] for k in ("source_id", "object_name", "field_name", "class_key")}})
    return item


@app.post("/api/v1/workspaces/{workspace_id}/metadata", status_code=201)
def metadata_create(workspace_id: str, payload: MetadataIn) -> dict[str, Any]:
    return insert_metadata(workspace_id, payload)


@app.put("/api/v1/metadata/{metadata_id}")
def metadata_update(metadata_id: str, payload: MetadataIn) -> dict[str, Any]:
    values = payload.model_dump()
    with connect() as con:
        current = require_row(con, "SELECT * FROM metadata_declarations WHERE id=?", (metadata_id,), "Metadata declaration")
        fields = list(values)
        con.execute("UPDATE metadata_declarations SET " + ",".join(f"{f}=?" for f in fields) + ",updated_at=? WHERE id=?",
                    [*[values[f] for f in fields], utcnow(), metadata_id])
        audit(con, current["workspace_id"], "metadata_updated", "metadata", metadata_id, {})
    return {"id": metadata_id, **values}


@app.delete("/api/v1/metadata/{metadata_id}")
def metadata_delete(metadata_id: str) -> dict[str, Any]:
    with connect() as con:
        current = require_row(con, "SELECT * FROM metadata_declarations WHERE id=?", (metadata_id,), "Metadata declaration")
        con.execute("DELETE FROM metadata_declarations WHERE id=?", (metadata_id,))
        audit(con, current["workspace_id"], "metadata_deleted", "metadata", metadata_id, {})
    return {"deleted": True}


@app.post("/api/v1/workspaces/{workspace_id}/metadata/import")
async def metadata_import(workspace_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    text = (await file.read(MAX_UPLOAD_BYTES + 1)).decode("utf-8-sig")
    if len(text.encode()) > MAX_UPLOAD_BYTES:
        raise AppError("FILE_TOO_LARGE", "Metadata import exceeds the upload limit.", 413)
    rows = list(csv.DictReader(io.StringIO(text)))
    source_map: dict[str, str] = {}
    with connect() as con:
        source_map = {r["display_name"]: r["id"] for r in con.execute("SELECT id,display_name FROM sources WHERE workspace_id=?", (workspace_id,))}
    items = []
    for row in rows:
        payload = MetadataIn(
            source_id=source_map.get(row.get("source_name", "")), object_name=row.get("object_name") or None,
            field_name=row.get("field_name") or None, class_key=row.get("class_key") or None,
            purpose_text=row.get("purpose_text") or None, retention_duration=row.get("retention_duration") or None,
            retention_basis=row.get("retention_basis") or None, last_reviewed_at=row.get("last_reviewed_at") or None,
            owner_label=row.get("owner_label") or None, evidence_reference=row.get("evidence_reference") or None,
        )
        items.append(insert_metadata(workspace_id, payload))
    return {"items": items, "total": len(items)}


@app.get("/api/v1/workspaces/{workspace_id}/metadata/export")
def metadata_export(workspace_id: str) -> Response:
    with connect() as con:
        rows = [dict(r) for r in con.execute(
            """SELECT COALESCE(s.display_name,'') source_name,m.object_name,m.field_name,m.class_key,
                      m.purpose_text,m.retention_duration,m.retention_basis,m.last_reviewed_at,m.owner_label,m.evidence_reference
               FROM metadata_declarations m LEFT JOIN sources s ON s.id=m.source_id WHERE m.workspace_id=?""", (workspace_id,)
        )]
    out = io.StringIO(newline="")
    headers = ["source_name", "object_name", "field_name", "class_key", "purpose_text", "retention_duration", "retention_basis", "last_reviewed_at", "owner_label", "evidence_reference"]
    writer = csv.DictWriter(out, fieldnames=headers); writer.writeheader(); writer.writerows(rows)
    return Response(out.getvalue().encode("utf-8-sig"), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=metadata.csv"})


@app.get("/api/v1/evaluation/datasets")
def evaluation_datasets() -> dict[str, Any]:
    gold = load_gold()
    return {"items": [{"dataset_key": gold[0]["dataset_key"] if gold else "demo-v1", "labelled_count": len(gold), "description": "Small synthetic manually labelled field set"}]}


@app.post("/api/v1/scans/{scan_id}/evaluation")
def evaluation_start(scan_id: str) -> dict[str, Any]:
    return run_evaluation(scan_id)


@app.get("/api/v1/scans/{scan_id}/evaluation/labels-template")
def evaluation_label_template(scan_id: str) -> Response:
    return Response(label_template(scan_id).encode("utf-8-sig"), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=dataquest-labels-template.csv"})


@app.get("/api/v1/scans/{scan_id}/evaluation/labels")
def evaluation_label_status(scan_id: str) -> dict[str, Any]:
    with connect() as con:
        require_row(con, "SELECT id FROM scans WHERE id=?", (scan_id,), "Scan")
        row = con.execute("SELECT dataset_key,COUNT(*) AS labelled_count FROM evaluation_labels WHERE scan_id=?", (scan_id,)).fetchone()
    return {"scan_id": scan_id, "dataset_key": row["dataset_key"] if row["labelled_count"] else None,
            "labelled_count": row["labelled_count"]}


@app.post("/api/v1/scans/{scan_id}/evaluation/labels")
async def evaluation_upload_labels(scan_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise AppError("INVALID_LABELS", "Choose a CSV label file.", 400)
    content = await file.read(1024 * 1024 + 1)
    return save_labels(scan_id, parse_label_csv(content))


@app.get("/api/v1/evaluation/runs/{run_id}")
def evaluation_get(run_id: str) -> dict[str, Any]:
    with connect() as con:
        item = require_row(con, "SELECT * FROM evaluation_runs WHERE id=?", (run_id,), "Evaluation run")
    return decode(item, "metrics_json")


@app.get("/api/v1/workspaces/{workspace_id}/audit")
def audit_list(workspace_id: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    return paged_query("SELECT * FROM audit_events WHERE workspace_id=? ORDER BY created_at DESC", [workspace_id], limit, offset)


@app.get("/api/v1/scans/{scan_id}/exports/{export_type}")
def scan_export(scan_id: str, export_type: str) -> Response:
    payload, media_type, filename = export_data(scan_id, export_type)
    return Response(payload, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.get("/api/v1/scans/{scan_id}/export")
def scan_export_alias(scan_id: str, format: str = Query("inventory_csv")) -> Response:
    return scan_export(scan_id, format)


@app.post("/api/v1/demo", status_code=201)
def load_demo() -> dict[str, Any]:
    workspace = create_workspace(WorkspaceIn(name="Synthetic demo workspace"))
    source_items = []
    for source_path in (DEMO_DIR / "admissions.csv", DEMO_DIR / "events.csv", DEMO_DIR / "support.db"):
        source_id = new_id()
        target = UPLOAD_DIR / f"{source_id}{source_path.suffix}"
        shutil.copy2(source_path, target)
        source_type = "csv" if source_path.suffix == ".csv" else "sqlite"
        item = {"id": source_id, "workspace_id": workspace["id"], "display_name": source_path.name,
                "source_type": source_type, "stored_path": str(target), "file_size_bytes": target.stat().st_size,
                "created_at": utcnow(), "status": "ready", "warnings": []}
        with connect() as con:
            con.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?)",
                        (source_id, workspace["id"], source_path.name, source_type, str(target), target.stat().st_size,
                         item["created_at"], "ready", "[]"))
        source_items.append(item)
    metadata_path = DEMO_DIR / "metadata.csv"
    source_map = {item["display_name"]: item["id"] for item in source_items}
    with metadata_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            insert_metadata(workspace["id"], MetadataIn(
                source_id=source_map.get(row["source_name"]), object_name=row["object_name"] or None,
                field_name=row["field_name"] or None, class_key=row["class_key"] or None,
                purpose_text=row["purpose_text"] or None, retention_duration=row["retention_duration"] or None,
                retention_basis=row["retention_basis"] or None, last_reviewed_at=row["last_reviewed_at"] or None,
                owner_label=row["owner_label"] or None, evidence_reference=row["evidence_reference"] or None,
            ))
    scan = create_scan(workspace["id"], ScanIn(source_ids=[item["id"] for item in source_items], options={"include_footprints": True}))
    save_labels(scan["id"], load_gold())
    return {"workspace": workspace, "sources": source_items, "scan": scan}
