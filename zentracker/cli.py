from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from zentracker.metrics import get_metric
from zentracker.storage import Entry, append_entry, iter_days, read_metric


def parse_iso_date(raw_value: str) -> date:
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"data invalida: {raw_value}. Use YYYY-MM-DD."
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zentracker")
    parser.add_argument(
        "--data-dir",
        default="data",
        type=Path,
        help="diretorio onde os arquivos por metrica sao armazenados",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="adiciona um registro")
    add_parser.add_argument("metric", help="metrica a registrar")
    add_parser.add_argument("value", help="valor da metrica")
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

    return parser


def handle_add(args: argparse.Namespace) -> int:
    metric = get_metric(args.metric)
    value = metric.validate(args.value)
    append_entry(args.data_dir, metric.name, Entry(args.entry_date, value))
    print(f"registrado: {metric.name} {value} em {args.entry_date.isoformat()}")
    return 0


def handle_table(args: argparse.Namespace) -> int:
    if args.start_date > args.end_date:
        raise ValueError("--from nao pode ser maior que --to.")

    metric_names = [item.strip() for item in args.metrics.split(",") if item.strip()]
    if not metric_names:
        raise ValueError("informe ao menos uma metrica em --metrics.")

    for metric_name in metric_names:
        get_metric(metric_name)

    datasets = {metric_name: read_metric(args.data_dir, metric_name) for metric_name in metric_names}
    rows: list[list[str]] = []
    for current_day in iter_days(args.start_date, args.end_date):
        row = [current_day.isoformat()]
        for metric_name in metric_names:
            row.append(datasets[metric_name].get(current_day, "-"))
        rows.append(row)

    print(format_table(["data", *metric_names], rows))
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
