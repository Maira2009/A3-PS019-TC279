from app.processing import detect_field, field_match, FieldData
from app.rules import DEFAULT_RULES


def rule(key):
    return next(item for item in DEFAULT_RULES if item["class_key"] == key)


def test_phone_aliases_and_negative_control():
    assert field_match("guardian_phone", rule("PHONE")["field_aliases"])[0]
    assert field_match("Phone Data Detected", rule("PHONE")["field_aliases"])[0]
    assert field_match("mobile", rule("PHONE")["field_aliases"])[0]
    assert not field_match("phone_model", rule("PHONE")["field_aliases"])[0]


def test_phone_detection_is_explainable():
    field = FieldData("s", "demo.csv", "demo.csv", "Phone", ["9876543210", "9123456789"], 2, [])
    result = detect_field(field, "phone_like", rule("PHONE"), 50)
    assert result is not None
    assert "FIELD_ALIAS_MATCH" in result["reason_codes"]
    assert "VALUE_PATTERN_MATCH" in result["reason_codes"]
    assert "9876543210" not in str(result["masked_samples"])


def test_invalid_regex_is_rejected(client):
    rules = client.get("/api/v1/rules").json()["items"]
    rules[0]["patterns"] = [{"name": "bad", "regex": "["}]
    response = client.put("/api/v1/rules", json=rules)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REGEX"

