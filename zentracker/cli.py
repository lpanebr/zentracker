from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from textwrap import dedent

from zentracker.metrics import (
    METRIC_TYPES,
    validate_metric_name,
    validate_metric_type,
    validate_metric_value,
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
              zt metrics
              zt demo --data-dir /tmp/zentracker-demo
              zt table 30 weight,gym,mood
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

    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="add one metric entry")
    add_parser.add_argument("metric", help="metric name")
    add_parser.add_argument("value", help="metric value")
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
        default=date.today(),
        help="entry date in YYYY-MM-DD; default: today",
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

    return parser


def handle_add(args: argparse.Namespace) -> int:
    metric_name = validate_metric_name(args.metric)
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

    value = validate_metric_value(metric_type, args.value)
    append_entry(args.data_dir, metric_name, metric_type, Entry(args.entry_date, value))
    print(f"recorded: {metric_name} {value} on {args.entry_date.isoformat()}")
    return 0


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
