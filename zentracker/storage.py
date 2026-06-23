from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


@dataclass(frozen=True)
class Entry:
    entry_date: date
    value: str


def ensure_data_dir(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)


def metric_path(data_dir: Path, metric_name: str) -> Path:
    return data_dir / f"{metric_name}.txt"


def append_entry(data_dir: Path, metric_name: str, entry: Entry) -> None:
    ensure_data_dir(data_dir)
    path = metric_path(data_dir, metric_name)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{entry.entry_date.isoformat()} {entry.value}\n")


def read_metric(data_dir: Path, metric_name: str) -> dict[date, str]:
    path = metric_path(data_dir, metric_name)
    if not path.exists():
        return {}

    latest_by_date: dict[date, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                raise ValueError(f"linha invalida em {path}: {raw_line.rstrip()}")

            raw_date, value = parts
            latest_by_date[date.fromisoformat(raw_date)] = value

    return latest_by_date


def iter_days(start_date: date, end_date: date) -> list[date]:
    days: list[date] = []
    current = start_date
    while current <= end_date:
        days.append(current)
        current += timedelta(days=1)
    return days
