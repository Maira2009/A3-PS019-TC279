from __future__ import annotations

import csv
import io
import json
from typing import Any

from .db import audit, connect, utcnow
from .errors import AppError


def neutralize(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    out = io.StringIO(newline="")
    if rows:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: neutralize(json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in row.items()})
    return out.getvalue().encode("utf-8-sig")


def _scan_workspace(con, scan_id: str) -> str:
    row = con.execute("SELECT workspace_id FROM scans WHERE id=?", (scan_id,)).fetchone()
    if not row:
        raise AppError("NOT_FOUND", "Scan not found.", 404)
    return row[0]


def export_data(scan_id: str, export_type: str) -> tuple[bytes, str, str]:
    with connect() as con:
        workspace_id = _scan_workspace(con, scan_id)
        findings = [dict(r) for r in con.execute(
            """SELECT f.id,f.class_key,s.display_name source,f.object_name,f.field_name,
                      f.rule_strength,f.confidence_label,f.reason_codes_json,f.masked_samples_json,
                      f.purpose_status,f.retention_status,f.review_status,f.rule_version
               FROM findings f JOIN sources s ON s.id=f.source_id WHERE f.scan_id=? ORDER BY source,object_name,field_name""",
            (scan_id,),
        ).fetchall()]
        footprints = [dict(r) for r in con.execute(
            """SELECT id,class_key,masked_representative,source_count,occurrence_count,
                      locations_json,match_method,ambiguity_note,overlap_type,review_status
               FROM footprints WHERE scan_id=?""", (scan_id,)
        ).fetchall()]
        reviews = [dict(r) for r in con.execute(
            "SELECT finding_id,previous_status,new_status,reviewer_label,note,created_at FROM review_events WHERE scan_id=?",
            (scan_id,),
        ).fetchall()]
        latest_eval = con.execute(
            "SELECT metrics_json FROM evaluation_runs WHERE scan_id=? ORDER BY created_at DESC LIMIT 1", (scan_id,)
        ).fetchone()
        metrics = json.loads(latest_eval[0]) if latest_eval else None
        summary_row = con.execute("SELECT started_at,finished_at,summary_json,status FROM scans WHERE id=?", (scan_id,)).fetchone()
        summary = json.loads(summary_row["summary_json"] or "{}")

        for row in findings:
            row["reason_codes"] = json.loads(row.pop("reason_codes_json"))
            row["masked_samples"] = json.loads(row.pop("masked_samples_json"))
        for row in footprints:
            row["locations"] = json.loads(row.pop("locations_json"))
        if export_type == "inventory_csv":
            payload, media, ext = csv_bytes(findings), "text/csv", "csv"
        elif export_type == "footprints_json":
            payload, media, ext = json.dumps(footprints, indent=2).encode(), "application/json", "json"
        elif export_type == "footprints_csv":
            payload, media, ext = csv_bytes(footprints), "text/csv", "csv"
        elif export_type == "evidence_gaps_csv":
            gaps = [f for f in findings if f["purpose_status"] != "present" or f["retention_status"] != "present"]
            payload, media, ext = csv_bytes(gaps), "text/csv", "csv"
        elif export_type == "review_history_csv":
            payload, media, ext = csv_bytes(reviews), "text/csv", "csv"
        elif export_type in {"metrics_json", "metrics_csv"}:
            if metrics is None:
                raise AppError("NOT_EVALUATED", "Run evaluation before exporting metrics.", 409)
            if export_type.endswith("json"):
                payload, media, ext = json.dumps(metrics, indent=2).encode(), "application/json", "json"
            else:
                rows = [{"class_key": key, **{k: v for k, v in value.items() if not isinstance(v, list)}} for key, value in metrics["per_class"].items()]
                payload, media, ext = csv_bytes(rows), "text/csv", "csv"
        elif export_type in {"report_md", "report_html"}:
            md = report_markdown(scan_id, summary_row, summary, findings, footprints, metrics)
            if export_type == "report_html":
                import html
                body = "<br>".join(html.escape(line) for line in md.splitlines())
                payload, media, ext = f"<!doctype html><meta charset='utf-8'><title>DATAQUEST report</title><body><pre>{body}</pre></body>".encode(), "text/html", "html"
            else:
                payload, media, ext = md.encode(), "text/markdown", "md"
        else:
            raise AppError("INVALID_EXPORT", "Unknown export type.", 400)
        audit(con, workspace_id, "export_created", "scan", scan_id, {"export_type": export_type})
    return payload, media, f"dataquest-{scan_id[:8]}-{export_type}.{ext}"


def report_markdown(scan_id: str, scan: Any, summary: dict[str, Any], findings: list[dict[str, Any]],
                    footprints: list[dict[str, Any]], metrics: dict[str, Any] | None) -> str:
    gaps = sum(f["purpose_status"] != "present" or f["retention_status"] != "present" for f in findings)
    pending = sum(f["review_status"] in {"needs_review", "review_later"} for f in findings)
    lines = [
        "# DATAQUEST scan report", "", f"Generated: {utcnow()}", f"Scan ID: {scan_id}",
        f"Scan status: {scan['status']}", f"Started: {scan['started_at']}", f"Finished: {scan['finished_at']}", "",
        "## Summary", "", f"Sources: {summary.get('source_count', 0)}",
        f"Profiled fields: {summary.get('profiled_field_count', 0)}", f"Potential findings: {len(findings)}",
        f"Potential overlap groups: {len(footprints)}", f"Evidence gaps: {gaps}", f"Awaiting review: {pending}", "",
        "## Findings", "",
    ]
    for item in findings:
        lines.append(f"- {item['class_key']} | {item['source']} / {item['object_name']} / {item['field_name']} | strength {item['rule_strength']:.2f} | purpose {item['purpose_status']} | retention {item['retention_status']} | review {item['review_status']}")
    lines += ["", "## Evaluation", ""]
    if metrics:
        for key, value in metrics["per_class"].items():
            p = "N/A" if value["precision"] is None else f"{value['precision']:.2%}"
            r = "N/A" if value["recall"] is None else f"{value['recall']:.2%}"
            lines.append(f"- {key}: precision {p}, recall {r}, TP {value['tp']}, FP {value['fp']}, FN {value['fn']}, TN {value['tn']}")
        lines.append("")
        lines.append(metrics["caveat"])
    else:
        lines.append("Not evaluated.")
    lines += ["", "## Limitations", "", "Detections are heuristic and may miss or misclassify fields.",
              "Potential overlap does not prove identity, ownership, authorization, or recency.",
              "Purpose and retention entries record declared evidence and do not establish legal sufficiency.",
              "This prototype has not undergone a security audit and does not provide compliance certification."]
    return "\n".join(lines) + "\n"
