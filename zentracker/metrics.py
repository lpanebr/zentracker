from __future__ import annotations

from decimal import Decimal, InvalidOperation
import unicodedata


DEFAULT_METRIC_TYPE = "text"
METRIC_TYPES = ("bool", "integer", "number", "text")
METRIC_TYPE_PREFIX = "# type:"

def normalize_metric_name(metric_name: str) -> str:
    return unicodedata.normalize("NFC", metric_name.strip())


def validate_metric_name(metric_name: str) -> str:
    name = normalize_metric_name(metric_name)
    if not name:
        raise ValueError("metric name cannot be empty.")
    if name.startswith("."):
        raise ValueError(
            "metric name accepts only Unicode letters, numbers, '_' and '-'."
        )
    for char in name:
        if char.isalnum() or char in {"_", "-"}:
            continue
        raise ValueError(
            "metric name accepts only Unicode letters, numbers, '_' and '-'."
        )
    return name


def validate_metric_type(metric_type: str) -> str:
    value = metric_type.strip().lower()
    if value not in METRIC_TYPES:
        valid = ", ".join(METRIC_TYPES)
        raise ValueError(f"unknown metric type: {metric_type}. Options: {valid}.")
    return value


def parse_metric_type_header(line: str) -> str | None:
    if not line.startswith(METRIC_TYPE_PREFIX):
        return None
    return validate_metric_type(line.removeprefix(METRIC_TYPE_PREFIX))


def format_metric_type_header(metric_type: str) -> str:
    return f"{METRIC_TYPE_PREFIX}{validate_metric_type(metric_type)}"


def validate_metric_value(metric_type: str, raw_value: str) -> str:
    value = raw_value.strip()
    if not value:
        raise ValueError("metric value cannot be empty.")

    metric_type = validate_metric_type(metric_type)
    if metric_type == "text":
        return value
    if metric_type == "bool":
        return validate_bool(value)
    if metric_type == "integer":
        return validate_integer(value)
    if metric_type == "number":
        return validate_number(value)

    raise AssertionError(f"metric type without validator: {metric_type}")


def validate_bool(value: str) -> str:
    normalized = value.lower()
    if normalized in {"yes", "true", "1", "sim"}:
        return "yes"
    if normalized in {"no", "false", "0", "nao"}:
        return "no"
    raise ValueError("bool accepts only yes/no, true/false, or 1/0.")


def validate_integer(value: str) -> str:
    try:
        return str(int(value, 10))
    except ValueError as exc:
        raise ValueError("integer requires a whole number.") from exc


def validate_number(value: str) -> str:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("number requires a numeric value.") from exc

    if not parsed.is_finite():
        raise ValueError("number requires a finite numeric value.")

    return value
