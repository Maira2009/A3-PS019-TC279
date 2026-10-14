from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import DEMO_DIR
from .db import audit, connect, new_id, utcnow
from .errors import AppError

CLASSES = ["PHONE", "EMAIL", "PERSON_NAME", "ADDRESS", "PERSONAL_ID"]


def load_gold(path: Path | None = None) -> list[dict[str, str]]:
    target = path or DEMO_DIR / "gold_labels.csv"
    with target.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def calculate_metrics(gold: list[dict[str, str]], predictions: list[dict[str, str]]) -> dict[str, Any]:
    predicted = {(p["source_name"], p["object_name"], p["field_name"], p["class_key"]) for p in predictions}
    field_universe = {(g["source_name"], g["object_name"], g["field_name"]) for g in gold}
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
        for source, obj, field, predicted_class in predicted:
            if predicted_class == class_key and (source, obj, field) not in field_universe:
                fp += 1
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
        "caveat": "Metrics reflect the included small synthetic labelled sample and do not establish production-wide detection accuracy.",
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
        metrics = calculate_metrics(load_gold(), predictions)
        run_id = new_id()
        con.execute("INSERT INTO evaluation_runs VALUES (?,?,?,?,?)",
                    (run_id, scan_id, metrics["dataset_key"], json.dumps(metrics), utcnow()))
        audit(con, scan["workspace_id"], "evaluation_run", "evaluation", run_id,
              {"dataset_key": metrics["dataset_key"], "labelled_count": metrics["labelled_count"]})
    return {"id": run_id, "scan_id": scan_id, **metrics}
