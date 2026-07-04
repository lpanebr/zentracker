from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from textwrap import dedent
from typing import TypedDict

from zentracker.metrics import (
    METRIC_TYPES,
    DEFAULT_METRIC_TYPE,
    normalize_metric_name,
    validate_integer,
    validate_metric_name,
    validate_metric_type,
    validate_metric_value,
    validate_number,
)
from zentracker.storage import (
    Entry,
    append_entry,
    iter_days,
    list_metric_names,
    metric_path,
    read_metric,
    read_metric_type,
    write_metric,
)


class PlotSeries(TypedDict):
    type: str
    points: list[list[float]]


DATE_TOKEN_PREFIXES = ("on:", "date:", "due:")
TYPE_TOKEN_PREFIX = "as:"


@dataclass(frozen=True)
class BatchItem:
    raw_metric_name: str
    raw_value: str
    raw_type_name: str | None = None


@dataclass(frozen=True)
class BatchGroup:
    raw_date_token: str | None
    items: list[BatchItem]


@dataclass(frozen=True)
class PendingEntry:
    group_index: int
    entry_date: date
    date_label: str
    metric_name: str
    metric_type: str
    value: str


@dataclass(frozen=True)
class SkippedItem:
    date_label: str
    metric_name: str
    reason: str


def package_version() -> str:
    try:
        return version("zentracker")
    except PackageNotFoundError:
        return "0.0.0+unknown"


def parse_iso_date(raw_value: str) -> date:
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid date: {raw_value}. Use YYYY-MM-DD."
        ) from exc


def parse_positive_int(raw_value: str) -> int:
    try:
        value = int(raw_value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid number of days: {raw_value}."
        ) from exc

    if value < 1:
        raise argparse.ArgumentTypeError("number of days must be greater than zero.")
    return value


def parse_data_dir(raw_value: str) -> Path:
    return Path(raw_value).expanduser()


def default_data_dir() -> Path:
    configured = os.environ.get("ZENTRACKER_DATA_DIR")
    if configured:
        return Path(configured).expanduser()

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home).expanduser() / "zentracker"

    return Path.home() / ".local" / "share" / "zentracker"


def program_name() -> str:
    configured = os.environ.get("ZENTRACKER_PROG")
    if configured:
        return configured

    name = Path(sys.argv[0]).name
    if name == "__main__.py":
        return "zentracker"
    return name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=program_name(),
        description="Track anything and everything locally right from your CLI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent(
            """\
            examples:
              zt add weight 92.4 --type number
              zt add gym yes --type bool
              zt add mood "focused"
              zt add +weight 92.4 +gym yes on:2026-07-01
              zt add +café 6 +mood "muito bem"
              zt metrics
              zt --data-dir /tmp/zentracker-demo demo
              zt table 30 weight,gym,mood
              zt export jsxgraph 30 weight,gym
              zt table --from 2026-06-01 --to 2026-06-30 --metrics weight,gym
            """
        ),
    )
    parser.add_argument(
        "--data-dir",
        default=default_data_dir(),
        type=parse_data_dir,
        help="directory where metric files are stored",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {package_version()}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="add one or more metric entries")
    add_parser.add_argument("tokens", nargs="*", help="legacy or batch add tokens")
    add_parser.add_argument(
        "--type",
        dest="metric_type",
        choices=METRIC_TYPES,
        help="metric type when creating a new file; default: text",
    )
    add_parser.add_argument(
        "--date",
        dest="entry_date",
        type=parse_iso_date,
        help="entry date in YYYY-MM-DD; legacy mode only; default: today",
    )
    add_parser.set_defaults(func=handle_add)

    table_parser = subparsers.add_parser("table", help="show a table for a date range")
    table_parser.add_argument(
        "days",
        nargs="?",
        type=parse_positive_int,
        help="number of days through today, for example: 30",
    )
    table_parser.add_argument(
        "metrics_arg",
        nargs="?",
        help="comma-separated metric list, for example: weight,gym",
    )
    table_parser.add_argument("--from", dest="start_date", type=parse_iso_date)
    table_parser.add_argument("--to", dest="end_date", type=parse_iso_date)
    table_parser.add_argument(
        "--metrics",
        help="comma-separated metric list, for example: weight,gym",
    )
    table_parser.set_defaults(func=handle_table)

    metrics_parser = subparsers.add_parser(
        "metrics",
        help="list metrics that already have data",
    )
    metrics_parser.set_defaults(func=handle_metrics)

    demo_parser = subparsers.add_parser(
        "demo",
        help="generate sample metrics relative to today",
    )
    demo_parser.add_argument(
        "--days",
        type=parse_positive_int,
        default=30,
        help="number of days to generate; default: 30",
    )
    demo_parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite demo metrics if this data directory already has metrics",
    )
    demo_parser.set_defaults(func=handle_demo)

    export_parser = subparsers.add_parser(
        "export",
        help="export metric data for external tools",
    )
    export_parser.add_argument("format", choices=("jsxgraph",), help="export format")
    export_parser.add_argument(
        "days",
        nargs="?",
        type=parse_positive_int,
        help="number of days through today, for example: 30",
    )
    export_parser.add_argument(
        "metrics_arg",
        nargs="?",
        help="comma-separated metric list, for example: weight,gym",
    )
    export_parser.add_argument("--from", dest="start_date", type=parse_iso_date)
    export_parser.add_argument("--to", dest="end_date", type=parse_iso_date)
    export_parser.add_argument(
        "--metrics",
        help="comma-separated metric list, for example: weight,gym",
    )
    export_parser.set_defaults(func=handle_export)

    return parser


def handle_add(args: argparse.Namespace) -> int:
    if is_batch_mode(args.tokens):
        return handle_add_batch(args)
    return handle_add_legacy(args)


def handle_add_legacy(args: argparse.Namespace) -> int:
    if len(args.tokens) != 2:
        raise ValueError(
            "legacy add expects METRIC VALUE [--type TYPE] [--date YYYY-MM-DD]."
        )

    metric_name = validate_metric_name(args.tokens[0])
    metric_type = read_metric_type(args.data_dir, metric_name)
    if args.metric_type is not None:
        requested_type = validate_metric_type(args.metric_type)
        path = metric_path(args.data_dir, metric_name)
        existing_file_with_content = path.exists() and path.stat().st_size > 0
        if existing_file_with_content and requested_type != metric_type:
            raise ValueError(
                f"{metric_name} already exists as {metric_type}; do not use --type to change it."
            )
        metric_type = requested_type

    entry_date = args.entry_date or date.today()
    value = validate_metric_value(metric_type, args.tokens[1])
    append_entry(args.data_dir, metric_name, metric_type, Entry(entry_date, value))
    print(f"recorded: {metric_name} {value} on {entry_date.isoformat()}")
    return 0


def handle_add_batch(args: argparse.Namespace) -> int:
    if args.metric_type is not None or args.entry_date is not None:
        raise ValueError(
            "batch mode does not accept --type or --date; use as:type and on:YYYY-MM-DD."
        )

    groups = parse_batch_groups(args.tokens)
    recorded, skipped = validate_batch_groups(args.data_dir, groups)

    for entry in recorded:
        append_entry(
            args.data_dir,
            entry.metric_name,
            entry.metric_type,
            Entry(entry.entry_date, entry.value),
        )

    if recorded:
        print(format_recorded_summary(recorded))
    if skipped:
        print(format_skipped_summary(skipped))

    if skipped:
        return 1
    return 0


def is_batch_mode(tokens: list[str]) -> bool:
    return any(is_metric_token(token) for token in tokens)


def is_metric_token(token: str) -> bool:
    return token.startswith("+")


def is_date_token(token: str) -> bool:
    return token.startswith(DATE_TOKEN_PREFIXES)


def is_type_token(token: str) -> bool:
    return token.startswith(TYPE_TOKEN_PREFIX)


def parse_batch_groups(tokens: list[str]) -> list[BatchGroup]:
    if not tokens:
        raise ValueError("no metric items found.")

    groups: list[BatchGroup] = []
    current_date_token: str | None = None
    current_items: list[BatchItem] = []
    current_group_started = False
    index = 0

    while index < len(tokens):
        token = tokens[index]
        if is_date_token(token):
            if current_group_started:
                if not current_items:
                    raise ValueError(f"date group {current_date_token or 'today'} has no metric items.")
                groups.append(BatchGroup(current_date_token, current_items))
                current_items = []
            current_date_token = token
            current_group_started = True
            index += 1
            continue

        if is_type_token(token):
            raise ValueError(
                "ambiguous batch syntax; quote tokens like on:, date:, due:, or as: when they are part of the value."
            )

        if not is_metric_token(token):
            raise ValueError(
                f"batch mode expects +metric items and optional on:YYYY-MM-DD groups; got {token!r}."
            )

        if not current_group_started:
            current_group_started = True

        raw_metric_name = token[1:]
        index += 1
        raw_type_name: str | None = None
        if index < len(tokens) and is_type_token(tokens[index]):
            raw_type_name = tokens[index].removeprefix(TYPE_TOKEN_PREFIX)
            index += 1

        if index < len(tokens) and is_date_token(tokens[index]):
            raise ValueError(
                f"ambiguous value for {normalize_metric_label(raw_metric_name)}; "
                "quote tokens like on:, date:, due:, or as: when they are part of the value."
            )

        value_parts: list[str] = []
        while index < len(tokens):
            current = tokens[index]
            if is_metric_token(current) or is_date_token(current):
                break
            if is_type_token(current):
                raise ValueError(
                    f"ambiguous value for {normalize_metric_label(raw_metric_name)}; "
                    "quote tokens like on:, date:, due:, or as: when they are part of the value."
                )
            value_parts.append(current)
            index += 1

        if not value_parts:
            raise ValueError(f"missing value for {normalize_metric_label(raw_metric_name)}.")

        current_items.append(BatchItem(raw_metric_name, " ".join(value_parts), raw_type_name))

    if not current_group_started:
        raise ValueError("no metric items found.")
    if not current_items:
        raise ValueError(f"date group {current_date_token or 'today'} has no metric items.")

    groups.append(BatchGroup(current_date_token, current_items))
    return groups


def validate_batch_groups(
    data_dir: Path,
    groups: list[BatchGroup],
) -> tuple[list[PendingEntry], list[SkippedItem]]:
    recorded: list[PendingEntry] = []
    skipped: list[SkippedItem] = []

    for group_index, group in enumerate(groups):
        entry_date, date_label, date_error = resolve_batch_group_date(group.raw_date_token)

        normalized_names: list[str | None] = []
        for item in group.items:
            if date_error is not None:
                normalized_names.append(None)
                continue
            try:
                normalized_names.append(validate_metric_name(item.raw_metric_name))
            except ValueError:
                normalized_names.append(None)

        duplicate_names = {
            metric_name
            for metric_name, count in Counter(
                name for name in normalized_names if name is not None
            ).items()
            if count > 1
        }

        for item, metric_name in zip(group.items, normalized_names):
            metric_label = metric_name or normalize_metric_label(item.raw_metric_name)
            if date_error is not None:
                skipped.append(SkippedItem(date_label, metric_label, date_error))
                continue
            if metric_name is None:
                skipped.append(
                    SkippedItem(
                        date_label,
                        metric_label,
                        "metric name accepts only Unicode letters, numbers, '_' and '-'.",
                    )
                )
                continue
            if metric_name in duplicate_names:
                skipped.append(
                    SkippedItem(date_label, metric_name, "repeated in same date group")
                )
                continue

            try:
                metric_type = resolve_batch_metric_type(
                    data_dir,
                    metric_name,
                    item.raw_type_name,
                    item.raw_value,
                )
                value = validate_metric_value(metric_type, item.raw_value)
            except ValueError as exc:
                skipped.append(SkippedItem(date_label, metric_name, str(exc)))
                continue

            if entry_date is None:
                raise AssertionError("validated batch group must have a date.")
            recorded.append(
                PendingEntry(
                    group_index=group_index,
                    entry_date=entry_date,
                    date_label=date_label,
                    metric_name=metric_name,
                    metric_type=metric_type,
                    value=value,
                )
            )

    return recorded, skipped


def resolve_batch_group_date(raw_date_token: str | None) -> tuple[date | None, str, str | None]:
    if raw_date_token is None:
        today = date.today()
        return today, today.isoformat(), None

    raw_date = raw_date_token.split(":", maxsplit=1)[1]
    try:
        parsed = parse_iso_date(raw_date)
    except argparse.ArgumentTypeError as exc:
        return None, raw_date_token, str(exc)
    return parsed, parsed.isoformat(), None


def resolve_batch_metric_type(
    data_dir: Path,
    metric_name: str,
    raw_type_name: str | None,
    raw_value: str,
) -> str:
    existing_type = read_metric_type(data_dir, metric_name)
    path = metric_path(data_dir, metric_name)
    existing_file_with_content = path.exists() and path.stat().st_size > 0

    requested_type: str | None = None
    if raw_type_name is not None:
        requested_type = validate_metric_type(raw_type_name)

    if existing_file_with_content:
        if requested_type is not None and requested_type != existing_type:
            raise ValueError(
                f"{metric_name} already exists as {existing_type}; do not use as:type to change it."
            )
        return existing_type

    if requested_type is not None:
        return requested_type

    return infer_metric_type(raw_value)


def infer_metric_type(raw_value: str) -> str:
    value = raw_value.strip().lower()
    if value in {"yes", "no", "true", "false", "sim", "nao"}:
        return "bool"

    try:
        validate_integer(raw_value)
        return "integer"
    except ValueError:
        pass

    try:
        validate_number(raw_value)
        return "number"
    except ValueError:
        pass

    return DEFAULT_METRIC_TYPE


def normalize_metric_label(metric_name: str) -> str:
    normalized = normalize_metric_name(metric_name)
    return normalized or metric_name.strip() or metric_name


def format_recorded_summary(recorded: list[PendingEntry]) -> str:
    grouped_entries = group_recorded_entries(recorded)
    lines = [
        f"recorded {len(recorded)} {pluralize(len(recorded), 'metric')} across "
        f"{len(grouped_entries)} {pluralize(len(grouped_entries), 'date group')}:"
    ]
    for date_label, metric_names in grouped_entries:
        lines.append(f"- {date_label}: {', '.join(metric_names)}")
    return "\n".join(lines)


def group_recorded_entries(recorded: list[PendingEntry]) -> list[tuple[str, list[str]]]:
    groups: list[tuple[tuple[int, str], list[str]]] = []
    for entry in recorded:
        group_key = (entry.group_index, entry.date_label)
        if groups and groups[-1][0] == group_key:
            groups[-1][1].append(entry.metric_name)
            continue
        groups.append((group_key, [entry.metric_name]))
    return [(group_key[1], metric_names) for group_key, metric_names in groups]


def format_skipped_summary(skipped: list[SkippedItem]) -> str:
    lines = [f"skipped {len(skipped)} {pluralize(len(skipped), 'metric')}:"]
    for item in skipped:
        lines.append(f"- {item.date_label} {item.metric_name}: {item.reason}")
    return "\n".join(lines)


def pluralize(count: int, noun: str) -> str:
    if count == 1:
        return noun
    return f"{noun}s"


def handle_table(args: argparse.Namespace) -> int:
    start_date, end_date, raw_metrics = resolve_table_args(args)

    metric_names = [item.strip() for item in raw_metrics.split(",") if item.strip()]
    if not metric_names:
        raise ValueError("provide at least one metric.")

    for metric_name in metric_names:
        validate_metric_name(metric_name)

    datasets = {metric_name: read_metric(args.data_dir, metric_name) for metric_name in metric_names}
    rows: list[list[str]] = []
    for current_day in iter_days(start_date, end_date):
        row = [current_day.isoformat()]
        for metric_name in metric_names:
            row.append(datasets[metric_name].get(current_day, "-"))
        rows.append(row)

    print(format_table(["date", *metric_names], rows))
    return 0


def resolve_table_args(args: argparse.Namespace) -> tuple[date, date, str]:
    if args.days is not None or args.metrics_arg is not None:
        if args.days is None or args.metrics_arg is None:
            raise ValueError("use the shorthand format as: table 30 weight,gym.")
        if args.start_date is not None or args.end_date is not None or args.metrics is not None:
            raise ValueError("do not mix table DAYS METRICS with --from/--to/--metrics.")

        end_date = date.today()
        start_date = end_date - timedelta(days=args.days - 1)
        return start_date, end_date, args.metrics_arg

    if args.start_date is None or args.end_date is None or args.metrics is None:
        raise ValueError(
            "use table DAYS METRICS or provide --from, --to, and --metrics."
        )

    if args.start_date > args.end_date:
        raise ValueError("--from cannot be later than --to.")

    return args.start_date, args.end_date, args.metrics


def handle_metrics(args: argparse.Namespace) -> int:
    names_with_data = [
        metric_name
        for metric_name in list_metric_names(args.data_dir)
        if read_metric(args.data_dir, metric_name)
    ]

    for metric_name in names_with_data:
        print(metric_name)

    return 0


def handle_demo(args: argparse.Namespace) -> int:
    existing_metrics = list_metric_names(args.data_dir)
    if existing_metrics and not args.force:
        raise ValueError(
            "data directory already has metrics; use --force or choose another --data-dir."
        )

    end_date = date.today()
    start_date = end_date - timedelta(days=args.days - 1)
    days = iter_days(start_date, end_date)

    demo_metrics = build_demo_metrics(days)
    for metric_name, metric_type, entries in demo_metrics:
        write_metric(args.data_dir, metric_name, metric_type, entries)

    display_names = ", ".join(metric_name for metric_name, _, _ in demo_metrics)
    metrics_arg = ",".join(metric_name for metric_name, _, _ in demo_metrics)
    print(f"generated {args.days} days of demo data: {display_names}")
    print(f"try: {program_name()} --data-dir {args.data_dir} table {args.days} {metrics_arg}")
    return 0


def handle_export(args: argparse.Namespace) -> int:
    start_date, end_date, raw_metrics = resolve_table_args(args)
    metric_names = [item.strip() for item in raw_metrics.split(",") if item.strip()]
    if not metric_names:
        raise ValueError("provide at least one metric.")

    for metric_name in metric_names:
        validate_metric_name(metric_name)

    if args.format == "jsxgraph":
        print(build_jsxgraph_embed(args.data_dir, start_date, end_date, metric_names))
        return 0

    raise AssertionError(f"unknown export format: {args.format}")


def build_jsxgraph_embed(
    data_dir: Path,
    start_date: date,
    end_date: date,
    metric_names: list[str],
) -> str:
    days = iter_days(start_date, end_date)
    dates = [current_day.isoformat() for current_day in days]
    numeric_series: dict[str, PlotSeries] = {}
    bool_series: dict[str, PlotSeries] = {}

    for metric_name in metric_names:
        metric_type = read_metric_type(data_dir, metric_name)
        dataset = read_metric(data_dir, metric_name)
        points: list[list[float]] = []

        for index, current_day in enumerate(days):
            raw_value = dataset.get(current_day)
            if raw_value is None:
                continue
            points.append([float(index), parse_plot_value(metric_name, metric_type, current_day, raw_value)])

        if not points:
            raise ValueError(f"{metric_name} has no numeric data in the selected range.")

        series = bool_series if metric_type == "bool" else numeric_series
        series[metric_name] = {"type": metric_type, "points": points}

    blocks = []
    if numeric_series:
        blocks.append(format_jsxgraph_embed(dates, numeric_series))
    if bool_series:
        blocks.append(format_jsxgraph_embed(dates, bool_series))
    return "\n\n".join(blocks)


def parse_plot_value(metric_name: str, metric_type: str, entry_date: date, raw_value: str) -> float:
    normalized = raw_value.strip().lower()
    if metric_type == "bool":
        if normalized in {"yes", "true", "1", "sim"}:
            return 1.0
        if normalized in {"no", "false", "0", "nao"}:
            return 0.0

    try:
        parsed = Decimal(raw_value)
    except InvalidOperation as exc:
        raise ValueError(
            f"{metric_name} has non-numeric value on {entry_date.isoformat()}: {raw_value}"
        ) from exc

    if not parsed.is_finite():
        raise ValueError(
            f"{metric_name} has non-finite value on {entry_date.isoformat()}: {raw_value}"
        )

    return float(parsed)


def format_jsxgraph_embed(dates: list[str], series: dict[str, PlotSeries]) -> str:
    all_values = [
        point[1]
        for metric in series.values()
        for point in metric["points"]
    ]
    min_y = min(all_values)
    max_y = max(all_values)
    padding = max((max_y - min_y) * 0.1, 1.0)
    right = max(len(dates) - 0.5, 0.5)
    bounding_box = [-0.5, max_y + padding, right, min_y - padding]
    width = bounding_box[2] - bounding_box[0]
    height = bounding_box[1] - bounding_box[3]
    label_y = bounding_box[1] - (height * 0.08)
    left_label_x = max(0.15, bounding_box[0] + (width * 0.08))
    right_label_x = bounding_box[2] - (width * 0.04)
    colors = [
        "#2563eb",
        "#16a34a",
        "#dc2626",
        "#9333ea",
        "#ea580c",
        "#0891b2",
    ]

    objects = []

    for index, (name, metric) in enumerate(series.items()):
        metric_type = metric["type"]
        points = metric["points"]
        color = colors[index % len(colors)]
        if metric_type != "bool":
            for segment in contiguous_segments(points):
                if len(segment) < 2:
                    continue
                objects.append(
                    {
                        "type": "curve",
                        "args": [
                            [point[0] for point in segment],
                            [point[1] for point in segment],
                        ],
                        "attributes": {
                            "strokeColor": color,
                            "strokeWidth": 3,
                            "name": name,
                        },
                    }
                )
        for point in points:
            objects.append(
                {
                    "type": "point",
                    "args": point,
                    "attributes": {
                        "fixed": True,
                        "name": "",
                        "size": 3 if metric_type == "bool" else 2,
                        "strokeColor": color,
                        "fillColor": color,
                    },
                }
            )

    objects.append(
        {
            "type": "text",
            "args": [
                left_label_x,
                label_y,
                " | ".join(series),
            ],
            "attributes": {
                "fixed": True,
                "fontSize": 14,
                "anchorX": "left",
                "anchorY": "top",
            },
        }
    )
    objects.append(
        {
            "type": "text",
            "args": [
                right_label_x,
                label_y,
                f"{dates[0]} to {dates[-1]}",
            ],
            "attributes": {
                "fixed": True,
                "fontSize": 12,
                "anchorX": "right",
                "anchorY": "top",
            },
        }
    )

    payload = {
        "dates": dates,
        "boundingbox": bounding_box,
        "axis": True,
        "showCopyright": False,
        "showNavigation": True,
        "objects": objects,
    }
    payload_json = json.dumps(payload, indent=2)
    return f"```jsxgraph\n{payload_json}\n```"


def contiguous_segments(points: list[list[float]]) -> list[list[list[float]]]:
    if not points:
        return []

    segments = [[points[0]]]
    for point in points[1:]:
        previous = segments[-1][-1]
        if point[0] == previous[0] + 1:
            segments[-1].append(point)
        else:
            segments.append([point])
    return segments


def build_demo_metrics(days: list[date]) -> list[tuple[str, str, list[Entry]]]:
    mood_values = ["focused", "calm", "tired", "energetic", "scattered"]
    weight_entries: list[Entry] = []
    gym_entries: list[Entry] = []
    mood_entries: list[Entry] = []

    for index, current_day in enumerate(days):
        weight = 92.8 - (index * 0.04) + ((index % 5) - 2) * 0.05
        weight_entries.append(Entry(current_day, f"{weight:.1f}"))

        went_to_gym = index % 3 != 1
        gym_entries.append(Entry(current_day, "yes" if went_to_gym else "no"))

        mood_entries.append(Entry(current_day, mood_values[index % len(mood_values)]))

    return [
        ("weight", "number", weight_entries),
        ("gym", "bool", gym_entries),
        ("mood", "text", mood_entries),
    ]


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    formatted_rows = []
    formatted_rows.append(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(headers)).rstrip()
    )
    for row in rows:
        formatted_rows.append(
            "  ".join(value.ljust(widths[index]) for index, value in enumerate(row)).rstrip()
        )
    return "\n".join(formatted_rows)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        return args.func(args)
    except ValueError as exc:
        parser.exit(status=2, message=f"error: {exc}\n")
