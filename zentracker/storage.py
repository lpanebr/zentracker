from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from zentracker.metrics import (
    DEFAULT_METRIC_TYPE,
    format_metric_type_header,
    parse_metric_type_header,
    validate_metric_name,
)


@dataclass(frozen=True)
class Entry:
    entry_date: date
    value: str


def ensure_data_dir(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)


def metric_path(data_dir: Path, metric_name: str) -> Path:
    return data_dir / f"{validate_metric_name(metric_name)}.txt"


def append_entry(data_dir: Path, metric_name: str, metric_type: str, entry: Entry) -> None:
    ensure_data_dir(data_dir)
    path = metric_path(data_dir, metric_name)
    should_write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8") as handle:
        if should_write_header:
            handle.write(f"{format_metric_type_header(metric_type)}\n")
        handle.write(f"{entry.entry_date.isoformat()} {entry.value}\n")


def write_metric(data_dir: Path, metric_name: str, metric_type: str, entries: list[Entry]) -> None:
    ensure_data_dir(data_dir)
    path = metric_path(data_dir, metric_name)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(f"{format_metric_type_header(metric_type)}\n")
        for entry in entries:
            handle.write(f"{entry.entry_date.isoformat()} {entry.value}\n")


def read_metric_type(data_dir: Path, metric_name: str) -> str:
    path = metric_path(data_dir, metric_name)
    if not path.exists():
        return DEFAULT_METRIC_TYPE

    with path.open("r", encoding="utf-8") as handle:
        first_line = handle.readline().strip()

    if not first_line:
        return DEFAULT_METRIC_TYPE

    metric_type = parse_metric_type_header(first_line)
    return metric_type or DEFAULT_METRIC_TYPE


def read_metric(data_dir: Path, metric_name: str) -> dict[date, str]:
    path = metric_path(data_dir, metric_name)
    if not path.exists():
        return {}

    latest_by_date: dict[date, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for index, raw_line in enumerate(handle):
            line = raw_line.strip()
            if not line:
                continue
            if index == 0 and parse_metric_type_header(line) is not None:
                continue

            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                raise ValueError(f"invalid line in {path}: {raw_line.rstrip()}")

            raw_date, value = parts
            latest_by_date[date.fromisoformat(raw_date)] = value

    return latest_by_date


def list_metric_names(data_dir: Path) -> list[str]:
    if not data_dir.exists():
        return []

    names = []
    for path in data_dir.glob("*.txt"):
        try:
            names.append(validate_metric_name(path.stem))
        except ValueError:
            continue
    return sorted(names)


def iter_days(start_date: date, end_date: date) -> list[date]:
    days: list[date] = []
    current = start_date
    while current <= end_date:
        days.append(current)
        current += timedelta(days=1)
    return days
