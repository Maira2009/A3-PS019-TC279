from __future__ import annotations

import copy
import json
import re
from typing import Any

from .db import connect, utcnow
from .errors import AppError

DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "class_key": "PHONE", "display_name": "Phone", "enabled": True,
        "field_aliases": ["phone", "mobile", "telephone", "guardian_phone", "contact_number"],
        "patterns": [{"name": "phone_shape", "regex": r"^\+?[0-9][0-9 ()-]{7,17}[0-9]$"}],
        "field_name_weight": 0.55, "pattern_weight": 0.35, "type_weight": 0.10,
        "threshold": 0.55, "mask_strategy": "phone", "notes": "Prototype default; plausibility only.", "version": "default-1"
    },
    {
        "class_key": "EMAIL", "display_name": "Email", "enabled": True,
        "field_aliases": ["email", "e_mail", "mail_id", "email_address"],
        "patterns": [{"name": "email_shape", "regex": r"^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$"}],
        "field_name_weight": 0.55, "pattern_weight": 0.35, "type_weight": 0.10,
        "threshold": 0.55, "mask_strategy": "email", "notes": "Prototype default.", "version": "default-1"
    },
    {
        "class_key": "PERSON_NAME", "display_name": "Person name", "enabled": True,
        "field_aliases": ["name", "full_name", "first_name", "last_name", "guardian_name", "customer_name"],
        "patterns": [{"name": "name_shape", "regex": r"^[A-Za-z][A-Za-z .'-]{1,79}$"}],
        "field_name_weight": 0.65, "pattern_weight": 0.20, "type_weight": 0.05,
        "threshold": 0.60, "mask_strategy": "name", "notes": "Value shape is weak without a field clue.", "version": "default-1"
    },
    {
        "class_key": "ADDRESS", "display_name": "Address", "enabled": True,
        "field_aliases": ["address", "street", "locality", "city", "postal_code", "pincode"],
        "patterns": [{"name": "postal_shape", "regex": r"^[1-9][0-9]{5}$"}],
        "field_name_weight": 0.65, "pattern_weight": 0.20, "type_weight": 0.05,
        "threshold": 0.60, "mask_strategy": "address", "notes": "Context required; postal values are ambiguous.", "version": "default-1"
    },
    {
        "class_key": "PERSONAL_ID", "display_name": "Personal identifier", "enabled": True,
        "field_aliases": ["personal_id", "student_id", "customer_id", "government_id", "aadhaar", "identifier"],
        "patterns": [{"name": "id_shape", "regex": r"^(?:STU|CUS|PID|ID)[-_]?[A-Z0-9]{4,16}$"}],
        "field_name_weight": 0.60, "pattern_weight": 0.30, "type_weight": 0.05,
        "threshold": 0.60, "mask_strategy": "id", "notes": "Does not validate government identifiers.", "version": "default-1"
    },
]


def validate_rules(rules: list[dict[str, Any]]) -> None:
    required = {"class_key", "display_name", "enabled", "field_aliases", "patterns",
                "field_name_weight", "pattern_weight", "type_weight", "threshold",
                "mask_strategy", "notes"}
    if len(rules) != 5:
        raise AppError("INVALID_RULES", "Exactly five prototype rule classes are required.", 422)
    seen: set[str] = set()
    for rule in rules:
        missing = required - set(rule)
        if missing:
            raise AppError("INVALID_RULES", f"Rule is missing: {', '.join(sorted(missing))}.", 422)
        key = str(rule["class_key"]).upper()
        if key in seen:
            raise AppError("INVALID_RULES", f"Duplicate class key: {key}.", 422)
        seen.add(key)
        weights = [float(rule[name]) for name in ("field_name_weight", "pattern_weight", "type_weight")]
        threshold = float(rule["threshold"])
        if any(value < 0 or value > 1 for value in weights + [threshold]) or sum(weights) > 1.01:
            raise AppError("INVALID_RULES", f"Weights/threshold for {key} must be between 0 and 1; weights sum to at most 1.", 422)
        for pattern in rule["patterns"]:
            try:
                re.compile(pattern["regex"])
            except (re.error, KeyError) as exc:
                raise AppError("INVALID_REGEX", f"Invalid regex in {key}: {exc}.", 422) from exc


def get_rules() -> tuple[str, list[dict[str, Any]]]:
    with connect() as con:
        row = con.execute("SELECT version, config_json FROM rule_versions ORDER BY created_at DESC LIMIT 1").fetchone()
        if row:
            return row["version"], json.loads(row["config_json"])
        rules = copy.deepcopy(DEFAULT_RULES)
        con.execute("INSERT INTO rule_versions VALUES (?,?,?)", ("default-1", json.dumps(rules), utcnow()))
        return "default-1", rules


def save_rules(rules: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    validate_rules(rules)
    version = f"rules-{utcnow().replace(':', '').replace('+00:00', 'Z')}"
    normalized = copy.deepcopy(rules)
    for rule in normalized:
        rule["class_key"] = str(rule["class_key"]).upper()
        rule["version"] = version
    with connect() as con:
        con.execute("INSERT INTO rule_versions VALUES (?,?,?)", (version, json.dumps(normalized), utcnow()))
    return version, normalized


def restore_defaults() -> tuple[str, list[dict[str, Any]]]:
    rules = copy.deepcopy(DEFAULT_RULES)
    version = f"defaults-{utcnow().replace(':', '').replace('+00:00', 'Z')}"
    for rule in rules:
        rule["version"] = version
    with connect() as con:
        con.execute("INSERT INTO rule_versions VALUES (?,?,?)", (version, json.dumps(rules), utcnow()))
    return version, rules
