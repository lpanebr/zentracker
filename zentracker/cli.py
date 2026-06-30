from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

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
)


def parse_iso_date(raw_value: str) -> date:
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"data invalida: {raw_value}. Use YYYY-MM-DD."
        ) from exc


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
    parser = argparse.ArgumentParser(prog=program_name())
    parser.add_argument(
        "--data-dir",
        default=default_data_dir(),
        type=parse_data_dir,
        help="diretorio onde os arquivos por metrica sao armazenados",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="adiciona um registro")
    add_parser.add_argument("metric", help="metrica a registrar")
    add_parser.add_argument("value", help="valor da metrica")
    add_parser.add_argument(
        "--type",
        dest="metric_type",
        choices=METRIC_TYPES,
        help="tipo da metrica ao criar arquivo novo; padrao: text",
    )
    add_parser.add_argument(
        "--date",
        dest="entry_date",
        type=parse_iso_date,
        default=date.today(),
        help="data do registro em YYYY-MM-DD; padrao: hoje",
    )
    add_parser.set_defaults(func=handle_add)

    table_parser = subparsers.add_parser("table", help="mostra tabela por periodo")
    table_parser.add_argument("--from", dest="start_date", required=True, type=parse_iso_date)
    table_parser.add_argument("--to", dest="end_date", required=True, type=parse_iso_date)
    table_parser.add_argument(
        "--metrics",
        required=True,
        help="lista separada por virgula, ex: peso,academia",
    )
    table_parser.set_defaults(func=handle_table)

    metrics_parser = subparsers.add_parser(
        "metrics",
        help="lista metricas que ja tem dados",
    )
    metrics_parser.set_defaults(func=handle_metrics)

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
                f"{metric_name} ja existe como {metric_type}; nao use --type para mudar tipo."
            )
        metric_type = requested_type

    value = validate_metric_value(metric_type, args.value)
    append_entry(args.data_dir, metric_name, metric_type, Entry(args.entry_date, value))
    print(f"registrado: {metric_name} {value} em {args.entry_date.isoformat()}")
    return 0


def handle_table(args: argparse.Namespace) -> int:
    if args.start_date > args.end_date:
        raise ValueError("--from nao pode ser maior que --to.")

    metric_names = [item.strip() for item in args.metrics.split(",") if item.strip()]
    if not metric_names:
        raise ValueError("informe ao menos uma metrica em --metrics.")

    for metric_name in metric_names:
        validate_metric_name(metric_name)

    datasets = {metric_name: read_metric(args.data_dir, metric_name) for metric_name in metric_names}
    rows: list[list[str]] = []
    for current_day in iter_days(args.start_date, args.end_date):
        row = [current_day.isoformat()]
        for metric_name in metric_names:
            row.append(datasets[metric_name].get(current_day, "-"))
        rows.append(row)

    print(format_table(["data", *metric_names], rows))
    return 0


def handle_metrics(args: argparse.Namespace) -> int:
    names_with_data = [
        metric_name
        for metric_name in list_metric_names(args.data_dir)
        if read_metric(args.data_dir, metric_name)
    ]

    for metric_name in names_with_data:
        print(metric_name)

    return 0


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
        parser.exit(status=2, message=f"erro: {exc}\n")
