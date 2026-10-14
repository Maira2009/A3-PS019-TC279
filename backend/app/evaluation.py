from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from .config import DEMO_DIR
from .db import audit, connect, new_id, utcnow
from .errors import AppError

CLASSES = ["PHONE", "EMAIL", "PERSON_NAME", "ADDRESS", "PERSONAL_ID"]
LABEL_COLUMNS = ["dataset_key", "source_name", "object_name", "field_name", "expected_class_key", "label", "annotation_note"]


def load_gold(path: Path | None = None) -> list[dict[str, str]]:
    target = path or DEMO_DIR / "gold_labels.csv"
    with target.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def scan_fields(con, scan_id: str) -> set[tuple[str, str, str]]:
    return {(row[0], row[1], row[2]) for row in con.execute(
        """SELECT s.display_name,p.object_name,p.field_name FROM profiles p
           JOIN sources s ON s.id=p.source_id WHERE p.scan_id=?""", (scan_id,)
    )}


def save_labels(scan_id: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    if not 1 <= len(rows) <= 10000:
        raise AppError("INVALID_LABELS", "Provide between 1 and 10,000 labelled fields.", 400)
    with connect() as con:
        scan = con.execute("SELECT workspace_id FROM scans WHERE id=?", (scan_id,)).fetchone()
        if not scan:
            raise AppError("NOT_FOUND", "Scan not found.", 404)
        fields = scan_fields(con, scan_id)
        if not fields:
            raise AppError("NO_PROFILED_FIELDS", "This scan has no profiled fields to evaluate.", 409)
        seen: set[tuple[str, str, str]] = set()
        dataset_keys: set[str] = set()
        normalized: list[dict[str, str]] = []
        for number, original in enumerate(rows, 2):
            row = {key: str(original.get(key) or "").strip() for key in LABEL_COLUMNS}
            field = (row["source_name"], row["object_name"], row["field_name"])
            if not row["dataset_key"] or any(not value for value in field):
                raise AppError("INVALID_LABELS", f"Row {number}: dataset key, source, object, and field are required.", 400)
            if field not in fields:
                raise AppError("LABEL_FIELD_MISMATCH", f"Row {number}: source/object/field does not match this scan: {' / '.join(field)}.", 400)
            if field in seen:
                raise AppError("DUPLICATE_LABEL", f"Row {number}: field is labelled more than once.", 400)
            if (row["label"], row["expected_class_key"]) not in (
                {("positive", class_key) for class_key in CLASSES} | {("negative", "NONE")}
            ):
                raise AppError("INVALID_LABELS", f"Row {number}: use positive with one of the five classes, or negative with NONE.", 400)
            seen.add(field)
            dataset_keys.add(row["dataset_key"])
            normalized.append(row)
        if len(dataset_keys) != 1:
            raise AppError("INVALID_LABELS", "All label rows must use the same dataset_key.", 400)
        con.execute("DELETE FROM evaluation_labels WHERE scan_id=?", (scan_id,))
        con.execute("DELETE FROM evaluation_runs WHERE scan_id=?", (scan_id,))
        con.executemany("INSERT INTO evaluation_labels VALUES (?,?,?,?,?,?,?,?,?)", [
            (new_id(), scan_id, row["dataset_key"], row["source_name"], row["object_name"],
             row["field_name"], row["expected_class_key"], row["label"], row["annotation_note"])
            for row in normalized
        ])
        audit(con, scan["workspace_id"], "evaluation_labels_saved", "scan", scan_id,
              {"dataset_key": next(iter(dataset_keys)), "labelled_count": len(normalized)})
    return {"scan_id": scan_id, "dataset_key": next(iter(dataset_keys)), "labelled_count": len(normalized)}


def parse_label_csv(content: bytes) -> list[dict[str, str]]:
    if not content or len(content) > 1024 * 1024:
        raise AppError("INVALID_LABELS", "The label CSV must be non-empty and no larger than 1 MB.", 400)
    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        if not reader.fieldnames or any(key not in reader.fieldnames for key in LABEL_COLUMNS[:-1]):
            raise AppError("INVALID_LABELS", "The label CSV is missing required columns. Download the scan template.", 400)
        return list(reader)
    except (UnicodeError, csv.Error) as exc:
        raise AppError("INVALID_LABELS", "The label CSV must be valid UTF-8 CSV.", 400) from exc


def label_template(scan_id: str) -> str:
    with connect() as con:
        if not con.execute("SELECT 1 FROM scans WHERE id=?", (scan_id,)).fetchone():
            raise AppError("NOT_FOUND", "Scan not found.", 404)
        fields = sorted(scan_fields(con, scan_id))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=LABEL_COLUMNS)
    writer.writeheader()
    for source, obj, field in fields:
        writer.writerow({"dataset_key": "my-dataset-v1", "source_name": source, "object_name": obj,
                         "field_name": field, "expected_class_key": "", "label": "", "annotation_note": ""})
    return output.getvalue()


def calculate_metrics(gold: list[dict[str, str]], predictions: list[dict[str, str]]) -> dict[str, Any]:
    predicted = {(p["source_name"], p["object_name"], p["field_name"], p["class_key"]) for p in predictions}
    per_class: dict[str, Any] = {}
    for class_key in CLASSES:
        tp = fp = fn = tn = 0
        misses: list[dict[str, str]] = []
        false_positives: list[dict[str, str]] = []
        for case in gold:
            field = (case["source_name"], case["object_name"], case["field_name"])
            expected = case["expected_class_key"] == class_key and case["label"] == "positive"
            actual = (*field, class_key) in predicted
            if expected and actual:
                tp += 1
            elif expected and not actual:
                fn += 1; misses.append(case)
            elif not expected and actual:
                fp += 1; false_positives.append(case)
            else:
                tn += 1
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        per_class[class_key] = {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "support": tp + fn,
            "false_positives": false_positives, "missed_detections": misses,
        }
    return {
        "dataset_key": gold[0]["dataset_key"] if gold else "unknown",
        "labelled_count": len(gold), "per_class": per_class,
        "caveat": "Metrics cover only manually labelled fields in this scan. Unlabelled fields are excluded; small samples do not establish production-wide accuracy.",
    }


def run_evaluation(scan_id: str) -> dict[str, Any]:
    with connect() as con:
        scan = con.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone()
        if not scan:
            raise AppError("NOT_FOUND", "Scan not found.", 404)
        predictions = [dict(row) for row in con.execute(
            """SELECT s.display_name source_name, f.object_name, f.field_name, f.class_key
               FROM findings f JOIN sources s ON s.id=f.source_id WHERE f.scan_id=?""", (scan_id,)
        ).fetchall()]
        gold = [dict(row) for row in con.execute(
            """SELECT dataset_key,source_name,object_name,field_name,expected_class_key,label,annotation_note
               FROM evaluation_labels WHERE scan_id=? ORDER BY source_name,object_name,field_name""", (scan_id,)
        )]
        if not gold:
            raise AppError("LABELS_REQUIRED", "This scan has no manual labels. Upload a label CSV for this scan before evaluating.", 409)
        metrics = calculate_metrics(gold, predictions)
        run_id = new_id()
        con.execute("INSERT INTO evaluation_runs VALUES (?,?,?,?,?)",
                    (run_id, scan_id, metrics["dataset_key"], json.dumps(metrics), utcnow()))
        audit(con, scan["workspace_id"], "evaluation_run", "evaluation", run_id,
              {"dataset_key": metrics["dataset_key"], "labelled_count": metrics["labelled_count"]})
    return {"id": run_id, "scan_id": scan_id, **metrics}
