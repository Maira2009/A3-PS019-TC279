from __future__ import annotations

import csv
import hashlib
import hmac
import json
import math
import re
import secrets
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .config import DEFAULT_ROW_LIMIT, DEFAULT_SAMPLE_LIMIT
from .db import audit, connect, new_id, utcnow
from .errors import AppError
from .rules import get_rules

PLACEHOLDERS = {"", "n/a", "na", "none", "unknown", "tbd", "not available", "not applicable"}
NEGATIVE_FIELD_TOKENS = {"model", "template", "count", "counter", "amount", "price", "total"}


@dataclass
class FieldData:
    source_id: str
    source_name: str
    object_name: str
    field_name: str
    values: list[Any]
    row_count: int
    warnings: list[str]


def safe_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def text_values(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            continue
        text = str(value).strip()
        if text:
            result.append(text)
    return result


def mask_value(value: Any, class_key: str | None = None) -> str:
    value = "" if value is None else str(value).strip()
    if not value:
        return ""
    kind = class_key
    if not kind:
        if "@" in value:
            kind = "EMAIL"
        elif len(re.sub(r"\D", "", value)) >= 8 and re.fullmatch(r"[+0-9 ()-]+", value):
            kind = "PHONE"
        else:
            kind = "TEXT"
    if kind == "EMAIL" and "@" in value:
        local, domain = value.split("@", 1)
        host, dot, suffix = domain.partition(".")
        return f"{local[:1] or '*'}***@{host[:1] or '*'}*****{dot}{suffix}"
    if kind == "PHONE":
        digits = re.sub(r"\D", "", value)
        return digits[:2] + "*" * max(4, len(digits) - 4) + digits[-2:]
    if kind == "PERSON_NAME":
        return " ".join(part[:1] + "***" for part in value.split())
    if kind == "ADDRESS":
        return value[:3] + "***" if len(value) > 3 else "***"
    if kind == "PERSONAL_ID":
        return value[:2] + "*" * max(4, len(value) - 4) + value[-2:]
    return value[:1] + "***" if len(value) > 1 else "*"


def infer_type(values: list[Any]) -> str:
    vals = text_values(values)
    if not vals:
        return "empty"
    sample = vals[:200]
    lower = [v.lower() for v in sample]
    if all(v in {"true", "false", "yes", "no", "0", "1"} for v in lower):
        return "boolean"
    try:
        nums = [float(v.replace(",", "")) for v in sample]
        return "integer" if all(value.is_integer() for value in nums) else "number"
    except ValueError:
        pass
    email_re = re.compile(r"^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$")
    phone_re = re.compile(r"^\+?[0-9][0-9 ()-]{7,17}[0-9]$")
    if sum(bool(email_re.fullmatch(v)) for v in sample) / len(sample) >= 0.7:
        return "email_like"
    if sum(bool(phone_re.fullmatch(v)) for v in sample) / len(sample) >= 0.7:
        return "phone_like"
    parsed = pd.to_datetime(pd.Series(sample), errors="coerce", format="mixed")
    if parsed.notna().mean() >= 0.8:
        return "date"
    return "text"


def read_csv_fields(path: Path, source_id: str, source_name: str, row_limit: int) -> list[FieldData]:
    if path.stat().st_size == 0:
        return []
    warnings: list[str] = []
    try:
        frame = pd.read_csv(path, dtype=object, nrows=row_limit, encoding="utf-8-sig", on_bad_lines="skip")
    except UnicodeDecodeError:
        warnings.append("UTF-8 decoding failed; Windows-1252 fallback used.")
        frame = pd.read_csv(path, dtype=object, nrows=row_limit, encoding="cp1252", on_bad_lines="skip")
    except pd.errors.EmptyDataError:
        return []
    if len(frame) >= row_limit:
        warnings.append(f"Row scan limit reached at {row_limit} rows.")
    duplicate_counts: Counter[str] = Counter()
    fields: list[FieldData] = []
    for raw_name in frame.columns:
        name = str(raw_name)
        base = re.sub(r"\.\d+$", "", name)
        duplicate_counts[base] += 1
        display = base if duplicate_counts[base] == 1 else f"{base} [occurrence {duplicate_counts[base]}]"
        fields.append(FieldData(source_id, source_name, source_name, display,
                                frame[raw_name].tolist(), len(frame), list(warnings)))
    return fields


def read_sqlite_fields(path: Path, source_id: str, source_name: str, row_limit: int) -> list[FieldData]:
    if path.read_bytes()[:16] != b"SQLite format 3\x00":
        raise AppError("INVALID_SQLITE", f"{source_name} does not have a valid SQLite signature.", 400)
    uri = f"file:{path.as_posix()}?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True, timeout=2)
        con.row_factory = sqlite3.Row
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()]
        fields: list[FieldData] = []
        for table in tables:
            quoted = safe_identifier(table)
            columns = [r[1] for r in con.execute(f"PRAGMA table_info({quoted})").fetchall()]
            total = int(con.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0])
            rows = con.execute(f"SELECT * FROM {quoted} LIMIT ?", (row_limit,)).fetchall()
            warnings = [f"Row scan limit reached at {row_limit} rows."] if total > row_limit else []
            for column in columns:
                fields.append(FieldData(source_id, source_name, table, column,
                                        [row[column] for row in rows], total, warnings))
        return fields
    except sqlite3.Error as exc:
        raise AppError("SQLITE_UNREADABLE", f"Could not read {source_name}: {exc}.", 400) from exc
    finally:
        if "con" in locals():
            con.close()


def read_source(source: dict[str, Any], row_limit: int) -> list[FieldData]:
    path = Path(source["stored_path"])
    if source["source_type"] == "csv":
        return read_csv_fields(path, source["id"], source["display_name"], row_limit)
    return read_sqlite_fields(path, source["id"], source["display_name"], row_limit)


def field_match(field_name: str, aliases: list[str]) -> tuple[bool, str | None]:
    normalized = re.sub(r"[^a-z0-9]+", "_", field_name.lower()).strip("_")
    tokens = set(normalized.split("_"))
    if tokens & NEGATIVE_FIELD_TOKENS:
        return False, None
    for alias in aliases:
        alias_norm = re.sub(r"[^a-z0-9]+", "_", alias.lower()).strip("_")
        if normalized == alias_norm:
            return True, alias
        if "_" not in alias_norm and alias_norm in tokens:
            return True, alias
    return False, None


def normalize_for_class(value: str, class_key: str) -> str:
    value = value.strip()
    if class_key == "PHONE":
        return re.sub(r"\D", "", value)
    if class_key == "EMAIL":
        return value.casefold()
    return re.sub(r"\s+", " ", value).casefold()


def metadata_status(value: str | None, secondary: str | None = None) -> str:
    primary = (value or "").strip().lower()
    secondary_text = (secondary or "").strip().lower()
    if not primary and not secondary_text:
        return "missing"
    if (primary and primary in PLACEHOLDERS) or (secondary_text and secondary_text in PLACEHOLDERS):
        return "partial"
    return "present"


def resolve_metadata(declarations: list[dict[str, Any]], source_id: str,
                     object_name: str, field_name: str, class_key: str) -> dict[str, str]:
    candidates: list[tuple[int, dict[str, Any], str]] = []
    for decl in declarations:
        if decl.get("source_id") not in (None, "", source_id):
            continue
        if decl.get("object_name") not in (None, "", object_name):
            continue
        if decl.get("field_name") not in (None, "", field_name):
            continue
        if decl.get("class_key") not in (None, "", class_key):
            continue
        score = sum(bool(decl.get(k)) for k in ("source_id", "object_name", "field_name", "class_key"))
        scope = "exact field" if score >= 3 else "source field" if score == 2 else "class" if decl.get("class_key") else "workspace"
        candidates.append((score, decl, scope))
    if not candidates:
        return {"purpose_status": "missing", "retention_status": "missing", "metadata_scope": "none"}
    _, match, scope = max(candidates, key=lambda item: item[0])
    return {
        "purpose_status": metadata_status(match.get("purpose_text")),
        "retention_status": metadata_status(match.get("retention_duration"), match.get("retention_basis")),
        "metadata_scope": scope,
    }


def detect_field(field: FieldData, inferred: str, rule: dict[str, Any], sample_limit: int) -> dict[str, Any] | None:
    values = text_values(field.values)[:sample_limit]
    alias_match, alias = field_match(field.field_name, rule["field_aliases"])
    compiled = [(p["name"], re.compile(p["regex"])) for p in rule["patterns"]]
    matched_values = [value for value in values if any(rx.fullmatch(value) for _, rx in compiled)]
    ratio = len(matched_values) / len(values) if values else 0
    pattern_match = ratio >= 0.5 and len(matched_values) >= min(2, len(values))
    type_support = (rule["class_key"] == "EMAIL" and inferred == "email_like") or (
        rule["class_key"] == "PHONE" and inferred == "phone_like") or inferred == "text"
    strength = (rule["field_name_weight"] if alias_match else 0) + (
        rule["pattern_weight"] * ratio if pattern_match else 0) + (
        rule["type_weight"] if type_support and (alias_match or pattern_match) else 0)
    if rule["class_key"] in {"PERSON_NAME", "ADDRESS"} and not alias_match:
        strength = min(strength, float(rule["threshold"]) - 0.01)
    if strength + 1e-9 < float(rule["threshold"]):
        return None
    reasons = []
    if alias_match:
        reasons.append("FIELD_ALIAS_MATCH" if re.sub(r"\W", "", field.field_name.lower()) == re.sub(r"\W", "", str(alias).lower()) else "FIELD_TOKEN_MATCH")
    if pattern_match:
        reasons.append("VALUE_PATTERN_MATCH")
    if type_support:
        reasons.append("TYPE_SUPPORTS_CLASS")
    if len(values) < 3:
        reasons.append("LOW_SAMPLE_SIZE")
    if rule["class_key"] in {"PERSON_NAME", "ADDRESS"}:
        reasons.append("AMBIGUOUS_PATTERN")
    confidence = "high" if strength >= 0.80 else "medium" if strength >= 0.60 else "low"
    clue = f"field name matches `{alias}`" if alias_match else "value shape matches the configured pattern"
    explanation = (
        f"Potential {rule['display_name']} field because {clue} and {len(matched_values)}/{len(values)} "
        f"sampled non-empty values matched. Rule strength: {confidence}. This heuristic finding requires human review."
    )
    return {
        "class_key": rule["class_key"], "rule_strength": round(min(strength, 1.0), 3),
        "confidence_label": confidence, "reason_codes": reasons, "explanation": explanation,
        "matched_count": len(matched_values), "sample_count": len(values),
        "masked_samples": [mask_value(v, rule["class_key"]) for v in matched_values[:3]],
        "matched_values": matched_values, "rule_version": rule.get("version", "unknown"),
    }


def run_scan(scan_id: str, workspace_id: str, source_ids: list[str], options: dict[str, Any]) -> dict[str, Any]:
    row_limit = max(1, min(int(options.get("row_limit_per_table", DEFAULT_ROW_LIMIT)), 1_000_000))
    sample_limit = max(1, min(int(options.get("sample_limit_per_field", DEFAULT_SAMPLE_LIMIT)), 10_000))
    include_footprints = bool(options.get("include_footprints", True))
    version, rules = get_rules()
    with connect() as con:
        sources = [dict(row) for row in con.execute(
            f"SELECT * FROM sources WHERE workspace_id=? AND id IN ({','.join('?' for _ in source_ids)})",
            [workspace_id, *source_ids],
        ).fetchall()] if source_ids else []
        declarations = [dict(row) for row in con.execute(
            "SELECT * FROM metadata_declarations WHERE workspace_id=?", (workspace_id,)
        ).fetchall()]
        con.execute("UPDATE scans SET status='running', stage='profile' WHERE id=?", (scan_id,))
        audit(con, workspace_id, "scan_started", "scan", scan_id, {"source_count": len(sources)})
    if not sources:
        raise AppError("NO_SOURCES", "Select at least one source for the scan.", 422)

    all_fields: list[FieldData] = []
    failures: list[dict[str, str]] = []
    for source in sources:
        try:
            all_fields.extend(read_source(source, row_limit))
        except AppError as exc:
            failures.append({"source_id": source["id"], "source": source["display_name"], "error": exc.message})

    footprint_occurrences: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    finding_count = 0
    object_keys: set[tuple[str, str]] = set()
    with connect() as con:
        con.execute("UPDATE scans SET stage='detect' WHERE id=?", (scan_id,))
        for field in all_fields:
            object_keys.add((field.source_id, field.object_name))
            inferred = infer_type(field.values)
            values = text_values(field.values)
            masked_samples = [mask_value(v) for v in values[:3]]
            con.execute(
                "INSERT INTO profiles VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (new_id(), scan_id, field.source_id, field.object_name, field.field_name, inferred,
                 field.row_count, min(field.row_count, row_limit), len(field.values) - len(values),
                 len(set(values)), json.dumps(masked_samples), json.dumps(field.warnings)),
            )
            for rule in rules:
                if not rule["enabled"]:
                    continue
                found = detect_field(field, inferred, rule, sample_limit)
                if not found:
                    continue
                finding_id = new_id()
                meta = resolve_metadata(declarations, field.source_id, field.object_name, field.field_name, found["class_key"])
                con.execute(
                    "INSERT INTO findings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (finding_id, scan_id, field.source_id, field.object_name, field.field_name,
                     found["class_key"], found["rule_strength"], found["confidence_label"],
                     json.dumps(found["reason_codes"]), found["explanation"], found["matched_count"],
                     found["sample_count"], json.dumps(found["masked_samples"]), meta["purpose_status"],
                     meta["retention_status"], meta["metadata_scope"], "needs_review", utcnow(), version),
                )
                finding_count += 1
                if include_footprints:
                    for raw in found["matched_values"]:
                        norm = normalize_for_class(raw, found["class_key"])
                        if norm:
                            footprint_occurrences[(found["class_key"], norm)].append({
                                "source_id": field.source_id, "source_name": field.source_name,
                                "object_name": field.object_name, "field_name": field.field_name,
                                "finding_id": finding_id, "masked": mask_value(raw, found["class_key"]),
                                **meta,
                            })

        con.execute("UPDATE scans SET stage='footprint' WHERE id=?", (scan_id,))
        secret = secrets.token_bytes(32)
        footprint_count = 0
        for (class_key, normalized), occurrences in footprint_occurrences.items():
            location_counts: dict[tuple[str, str, str, str], dict[str, Any]] = {}
            for occurrence in occurrences:
                key = (occurrence["source_id"], occurrence["source_name"], occurrence["object_name"], occurrence["field_name"])
                if key not in location_counts:
                    location_counts[key] = {k: v for k, v in occurrence.items() if k != "masked"}
                    location_counts[key]["matched_count"] = 0
                location_counts[key]["matched_count"] += 1
            locations = list(location_counts.values())
            source_count = len({loc["source_id"] for loc in locations})
            if len(occurrences) < 2:
                continue
            overlap_type = "cross_source" if source_count > 1 else "within_source"
            group_id = hmac.new(secret, f"{scan_id}:{class_key}:{normalized}".encode(), hashlib.sha256).hexdigest()[:24]
            con.execute(
                "INSERT INTO footprints VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (group_id, scan_id, class_key, occurrences[0]["masked"], source_count,
                 len(occurrences), json.dumps(locations), "equal conservative normalized value",
                 "Potential overlap is not proof of identity. Shared, recycled, placeholder, or incorrect values may match.",
                 overlap_type, "needs_review", utcnow()),
            )
            footprint_count += 1

        status = "partial" if failures and all_fields else "failed" if failures else "completed"
        summary = {
            "source_count": len(sources), "successful_source_count": len(sources) - len(failures),
            "failed_sources": failures, "object_count": len(object_keys), "profiled_field_count": len(all_fields),
            "finding_count": finding_count, "footprint_count": footprint_count,
            "row_limit_per_table": row_limit, "sample_limit_per_field": sample_limit,
        }
        con.execute(
            "UPDATE scans SET status=?, stage='persist', finished_at=?, summary_json=? WHERE id=?",
            (status, utcnow(), json.dumps(summary), scan_id),
        )
        audit(con, workspace_id, "scan_finished", "scan", scan_id,
              {"status": status, "finding_count": finding_count, "failure_count": len(failures)})
    return summary


def paged_query(sql: str, params: list[Any], limit: int, offset: int) -> dict[str, Any]:
    bounded = max(1, min(limit, 500))
    with connect() as con:
        items = [dict(row) for row in con.execute(sql + " LIMIT ? OFFSET ?", [*params, bounded, max(0, offset)]).fetchall()]
        count_sql = f"SELECT COUNT(*) FROM ({sql})"
        total = int(con.execute(count_sql, params).fetchone()[0])
    for item in items:
        for key in list(item):
            if key.endswith("_json"):
                clean = key[:-5]
                item[clean] = json.loads(item.pop(key) or "null")
    return {"items": items, "total": total, "limit": bounded, "offset": max(0, offset)}
