from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from .config import DB_PATH, ensure_dirs

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS workspaces (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL,
  status TEXT NOT NULL, config_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, display_name TEXT NOT NULL,
  source_type TEXT NOT NULL, stored_path TEXT NOT NULL, file_size_bytes INTEGER,
  created_at TEXT NOT NULL, status TEXT NOT NULL, warning_json TEXT NOT NULL DEFAULT '[]',
  FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS scans (
  id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, started_at TEXT NOT NULL,
  finished_at TEXT, status TEXT NOT NULL, stage TEXT NOT NULL,
  config_snapshot_json TEXT NOT NULL, summary_json TEXT, error_code TEXT,
  error_message_safe TEXT, FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS profiles (
  id TEXT PRIMARY KEY, scan_id TEXT NOT NULL, source_id TEXT NOT NULL,
  object_name TEXT NOT NULL, field_name TEXT NOT NULL, inferred_type TEXT NOT NULL,
  row_count INTEGER, scanned_count INTEGER, null_count INTEGER, distinct_count INTEGER,
  masked_samples_json TEXT NOT NULL, profile_warnings_json TEXT NOT NULL,
  UNIQUE(scan_id, source_id, object_name, field_name),
  FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS findings (
  id TEXT PRIMARY KEY, scan_id TEXT NOT NULL, source_id TEXT NOT NULL,
  object_name TEXT NOT NULL, field_name TEXT NOT NULL, class_key TEXT NOT NULL,
  rule_strength REAL NOT NULL, confidence_label TEXT NOT NULL,
  reason_codes_json TEXT NOT NULL, explanation TEXT NOT NULL,
  matched_count INTEGER, sample_count INTEGER, masked_samples_json TEXT NOT NULL,
  purpose_status TEXT NOT NULL, retention_status TEXT NOT NULL,
  metadata_scope TEXT, review_status TEXT NOT NULL, created_at TEXT NOT NULL,
  rule_version TEXT NOT NULL, FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS footprints (
  id TEXT PRIMARY KEY, scan_id TEXT NOT NULL, class_key TEXT NOT NULL,
  masked_representative TEXT NOT NULL, source_count INTEGER NOT NULL,
  occurrence_count INTEGER NOT NULL, locations_json TEXT NOT NULL,
  match_method TEXT NOT NULL, ambiguity_note TEXT NOT NULL,
  overlap_type TEXT NOT NULL, review_status TEXT NOT NULL, created_at TEXT NOT NULL,
  FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS metadata_declarations (
  id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, source_id TEXT,
  object_name TEXT, field_name TEXT, class_key TEXT, purpose_text TEXT,
  retention_duration TEXT, retention_basis TEXT, last_reviewed_at TEXT,
  owner_label TEXT, evidence_reference TEXT, created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS review_events (
  id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, scan_id TEXT NOT NULL,
  finding_id TEXT NOT NULL, previous_status TEXT, new_status TEXT NOT NULL,
  reviewer_label TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL,
  FOREIGN KEY(finding_id) REFERENCES findings(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, event_type TEXT NOT NULL,
  entity_type TEXT, entity_id TEXT, details_redacted_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evaluation_runs (
  id TEXT PRIMARY KEY, scan_id TEXT NOT NULL, dataset_key TEXT NOT NULL,
  metrics_json TEXT NOT NULL, created_at TEXT NOT NULL,
  FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS evaluation_labels (
  id TEXT PRIMARY KEY, scan_id TEXT NOT NULL, dataset_key TEXT NOT NULL,
  source_name TEXT NOT NULL, object_name TEXT NOT NULL, field_name TEXT NOT NULL,
  expected_class_key TEXT NOT NULL, label TEXT NOT NULL, annotation_note TEXT NOT NULL,
  UNIQUE(scan_id, source_name, object_name, field_name),
  FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS rule_versions (
  version TEXT PRIMARY KEY, config_json TEXT NOT NULL, created_at TEXT NOT NULL
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id() -> str:
    return str(uuid4())


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    ensure_dirs()
    con = sqlite3.connect(path or DB_PATH, timeout=5)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db() -> None:
    with connect() as con:
        con.executescript(SCHEMA)


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def rows_dict(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def decode_json_fields(item: dict[str, Any], *fields: str) -> dict[str, Any]:
    for field in fields:
        if item.get(field) is not None and isinstance(item[field], str):
            item[field] = json.loads(item[field])
    return item


def audit(con: sqlite3.Connection, workspace_id: str, event_type: str,
          entity_type: str | None = None, entity_id: str | None = None,
          details: dict | None = None) -> None:
    con.execute(
        "INSERT INTO audit_events VALUES (?,?,?,?,?,?,?)",
        (new_id(), workspace_id, event_type, entity_type, entity_id,
         json.dumps(details or {}, sort_keys=True), utcnow()),
    )

