from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from datetime import date, timedelta
from pathlib import Path

from zentracker.storage import Entry, write_metric


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def parse_jsxgraph_blocks(output: str) -> list[dict[str, object]]:
    blocks = []
    for raw_block in output.strip().split("\n\n"):
        blocks.append(json.loads(raw_block.removeprefix("```jsxgraph\n").removesuffix("\n```")))
    return blocks


class ZentrackerCliTest(unittest.TestCase):
    def run_cli(
        self,
        *args: str,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "zentracker", *args],
            cwd=cwd or PROJECT_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_version_option_reports_package_version(self) -> None:
        result = self.run_cli("--version")
        with (PROJECT_ROOT / "pyproject.toml").open("rb") as handle:
            expected_version = tomllib.load(handle)["project"]["version"]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), f"zentracker {expected_version}")

    def test_add_records_multiple_metrics_with_type_inference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "on:2026-07-01",
                "+peso",
                "97.5",
                "+academia",
                "yes",
                "+café",
                "6",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("recorded 3 metrics across 1 date group:", result.stdout)
            self.assertIn("- 2026-07-01: peso, academia, café", result.stdout)
            self.assertEqual(
                (Path(temp_dir) / "peso.txt").read_text(encoding="utf-8"),
                "# type:number\n2026-07-01 97.5\n",
            )
            self.assertEqual(
                (Path(temp_dir) / "academia.txt").read_text(encoding="utf-8"),
                "# type:bool\n2026-07-01 yes\n",
            )
            self.assertEqual(
                (Path(temp_dir) / "café.txt").read_text(encoding="utf-8"),
                "# type:integer\n2026-07-01 6\n",
            )

    def test_add_uses_environment_data_dir_when_data_dir_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            env["ZENTRACKER_DATA_DIR"] = temp_dir

            result = self.run_cli(
                "add",
                "on:2026-06-23",
                "+mood",
                "focused",
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (Path(temp_dir) / "mood.txt").read_text(encoding="utf-8"),
                "# type:text\n2026-06-23 focused\n",
            )

    def test_add_removes_legacy_metric_value_flags_form(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "mood",
                "focused",
                "--date",
                "2026-06-23",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("unrecognized arguments: --date", result.stderr)

    def test_add_supports_unicode_normalization_for_metric_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            decomposed_name = "cafe\u0301"

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "on:2026-07-01",
                f"+{decomposed_name}",
                "2",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(temp_dir) / "café.txt").exists())
            self.assertFalse((Path(temp_dir) / f"{decomposed_name}.txt").exists())

    def test_add_accepts_unquoted_multiword_text_with_explicit_type(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "on:2026-07-01",
                "+humor",
                "as:text",
                "muito",
                "bem",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (Path(temp_dir) / "humor.txt").read_text(encoding="utf-8"),
                "# type:text\n2026-07-01 muito bem\n",
            )

    def test_add_override_replaces_existing_same_day_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "peso.txt").write_text(
                "# type:number\n2026-07-01 97.5\n2026-07-01 97.4\n2026-07-02 97.2\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "--override",
                "on:2026-07-01",
                "+peso",
                "96.8",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("recorded 1 metric across 1 date group:", result.stdout)
            self.assertEqual(
                (data_dir / "peso.txt").read_text(encoding="utf-8"),
                "# type:number\n2026-07-01 96.8\n2026-07-02 97.2\n",
            )

    def test_add_without_override_preserves_existing_same_day_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "peso.txt").write_text(
                "# type:number\n2026-07-01 97.5\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "on:2026-07-01",
                "+peso",
                "96.8",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (data_dir / "peso.txt").read_text(encoding="utf-8"),
                "# type:number\n2026-07-01 97.5\n2026-07-01 96.8\n",
            )

    def test_add_backfill_reorders_dates_but_preserves_same_day_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "peso.txt").write_text(
                "# type:number\n2026-07-03 97.5\n2026-07-03 97.4\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "on:2026-07-01",
                "+peso",
                "96.8",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (data_dir / "peso.txt").read_text(encoding="utf-8"),
                "# type:number\n2026-07-01 96.8\n2026-07-03 97.5\n2026-07-03 97.4\n",
            )

    def test_add_rejects_type_change_for_existing_metric_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text("# type:number\n", encoding="utf-8")

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "+weight",
                "as:integer",
                "92",
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("weight already exists as number", result.stdout)

    def test_add_integer_metric_rejects_decimal_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "+water-cups",
                "as:integer",
                "1.5",
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("integer requires a whole number.", result.stdout)

    def test_add_rejects_invalid_metric_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli("--data-dir", temp_dir, "add", "+../weight", "92.4")

            self.assertEqual(result.returncode, 1)
            self.assertIn("metric name accepts only", result.stdout)

    def test_add_supports_partial_success_and_duplicate_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "on:2026-07-01",
                "+peso",
                "as:number",
                "abc",
                "+academia",
                "yes",
                "+peso",
                "97.5",
                "on:2026-07-02",
                "+peso",
                "97.2",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("recorded 2 metrics across 2 date groups:", result.stdout)
            self.assertIn("- 2026-07-01: academia", result.stdout)
            self.assertIn("- 2026-07-02: peso", result.stdout)
            self.assertIn("skipped 2 metrics:", result.stdout)
            self.assertEqual(result.stdout.count("repeated in same date group"), 2)
            self.assertEqual(
                (Path(temp_dir) / "academia.txt").read_text(encoding="utf-8"),
                "# type:bool\n2026-07-01 yes\n",
            )
            self.assertEqual(
                (Path(temp_dir) / "peso.txt").read_text(encoding="utf-8"),
                "# type:number\n2026-07-02 97.2\n",
            )

    def test_add_parse_errors_record_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "+peso",
                "97.5",
                "on:2026-07-01",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("date group on:2026-07-01 has no metric items", result.stderr)
            self.assertFalse((Path(temp_dir) / "peso.txt").exists())

    def test_add_rejects_ambiguous_reserved_value_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "+nota",
                "due:ruim",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("ambiguous value for nota", result.stderr)

    def test_list_shows_raw_entries_and_preserves_same_day_repeats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "humor.txt").write_text(
                "# type:text\n2026-07-01 bom\n2026-07-01 otimo\n",
                encoding="utf-8",
            )
            (data_dir / "peso.txt").write_text(
                "# type:number\n2026-07-01 97.5\n2026-07-02 97.2\n",
                encoding="utf-8",
            )

            result = self.run_cli("--data-dir", temp_dir, "list", "from:data", "to:data")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "2026-07-01 humor bom",
                    "2026-07-01 humor otimo",
                    "2026-07-01 peso 97.5",
                    "2026-07-02 peso 97.2",
                ],
            )

    def test_list_stays_raw_while_table_aggregates_same_day_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "peso.txt").write_text(
                "# type:number\n2026-07-01 97.5\n2026-07-01 97.2\n",
                encoding="utf-8",
            )

            list_result = self.run_cli(
                "--data-dir",
                temp_dir,
                "list",
                "from:2026-07-01",
                "to:2026-07-01",
                "+peso",
            )
            table_result = self.run_cli(
                "--data-dir",
                temp_dir,
                "table",
                "from:2026-07-01",
                "to:2026-07-01",
                "+peso",
            )

            self.assertEqual(list_result.returncode, 0, list_result.stderr)
            self.assertEqual(
                list_result.stdout.strip().splitlines(),
                [
                    "2026-07-01 peso 97.5",
                    "2026-07-01 peso 97.2",
                ],
            )
            self.assertEqual(table_result.returncode, 0, table_result.stderr)
            self.assertEqual(
                table_result.stdout.strip().splitlines(),
                [
                    "date        peso",
                    "2026-07-01  194.70",
                ],
            )

    def test_list_accepts_days_and_metric_filters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            today = date.today()
            yesterday = today - timedelta(days=1)
            data_dir = Path(temp_dir)
            (data_dir / "humor.txt").write_text(
                f"{yesterday.isoformat()} bom\n{today.isoformat()} otimo\n",
                encoding="utf-8",
            )
            (data_dir / "peso.txt").write_text(
                f"{today.isoformat()} 97.5\n",
                encoding="utf-8",
            )

            result = self.run_cli("--data-dir", temp_dir, "list", "2", "+humor")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    f"{yesterday.isoformat()} humor bom",
                    f"{today.isoformat()} humor otimo",
                ],
            )

    def test_list_accepts_multiple_views_and_extra_metrics_with_stable_deduplication(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "humor.txt").write_text("2026-07-01 bom\n", encoding="utf-8")
            (data_dir / "peso.txt").write_text("2026-07-01 97.5\n", encoding="utf-8")
            (data_dir / "café.txt").write_text("2026-07-01 3\n", encoding="utf-8")

            self.run_cli(
                "--data-dir",
                temp_dir,
                "view",
                "save",
                "@saúde",
                "table",
                "+humor",
                "+peso",
            )
            self.run_cli(
                "--data-dir",
                temp_dir,
                "view",
                "save",
                "@trabalho",
                "list",
                "+peso",
                "+café",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "list",
                "from:data",
                "to:data",
                "@saúde",
                "@trabalho",
                "+café",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "2026-07-01 humor bom",
                    "2026-07-01 peso 97.5",
                    "2026-07-01 café 3",
                ],
            )

    def test_query_rejects_unknown_view_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli("--data-dir", temp_dir, "table", "30", "@missing")

            self.assertEqual(result.returncode, 2)
            self.assertIn("unknown view: @missing", result.stderr)

    def test_table_aggregates_same_day_entries_by_type(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "gym.txt").write_text(
                "# type:bool\n2026-06-23 yes\n2026-06-23 no\n",
                encoding="utf-8",
            )
            (data_dir / "mood.txt").write_text(
                "# type:text\n2026-06-23 bom\n2026-06-23 triste\n",
                encoding="utf-8",
            )
            (data_dir / "count.txt").write_text(
                "# type:integer\n2026-06-23 1\n2026-06-23 2\n2026-06-23 3\n",
                encoding="utf-8",
            )
            (data_dir / "weight.txt").write_text(
                "# type:number\n2026-06-23 92.4\n2026-06-23 92.1\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "table",
                "from:2026-06-23",
                "to:2026-06-23",
                "+gym",
                "+mood",
                "+count",
                "+weight",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "date        gym      mood         count  weight",
                    "2026-06-23  yes, no  bom, triste  6      184.50",
                ],
            )

    def test_table_preserves_same_day_order_when_storage_is_sorted_by_date(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            write_metric(
                data_dir,
                "mood",
                "text",
                [
                    Entry(date(2026, 7, 3), "terceiro"),
                    Entry(date(2026, 7, 1), "primeiro"),
                    Entry(date(2026, 7, 1), "segundo"),
                ],
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "table",
                "from:2026-07-01",
                "to:2026-07-03",
                "+mood",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "date        mood",
                    "2026-07-01  primeiro, segundo",
                    "2026-07-02  -",
                    "2026-07-03  terceiro",
                ],
            )

    def test_table_number_with_single_value_renders_two_decimals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text(
                "# type:number\n2026-06-23 1.5\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "table",
                "from:2026-06-23",
                "to:2026-06-23",
                "+weight",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "date        weight",
                    "2026-06-23  1.50",
                ],
            )

    def test_table_legacy_metric_without_type_uses_text_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text(
                "2026-06-23 1.5\n2026-06-23 2.25\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "table",
                "from:2026-06-23",
                "to:2026-06-23",
                "+weight",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "date        weight",
                    "2026-06-23  1.5, 2.25",
                ],
            )

    def test_table_combines_metrics_and_marks_missing_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text(
                "2026-06-20 92.4\n2026-06-21 92.1\n",
                encoding="utf-8",
            )
            (data_dir / "gym.txt").write_text(
                "2026-06-20 yes\n2026-06-21 no\n2026-06-22 yes\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "table",
                "from:2026-06-20",
                "to:2026-06-22",
                "+weight",
                "+gym",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "date        weight  gym",
                    "2026-06-20  92.4    yes",
                    "2026-06-21  92.1    no",
                    "2026-06-22  -       yes",
                ],
            )

    def test_table_accepts_days_and_metric_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            today = date.today()
            yesterday = today - timedelta(days=1)
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text(
                f"{yesterday.isoformat()} 92.4\n{today.isoformat()} 92.1\n",
                encoding="utf-8",
            )
            (data_dir / "gym.txt").write_text(
                f"{today.isoformat()} yes\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "table",
                "2",
                "+weight",
                "+gym",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "date        weight  gym",
                    f"{yesterday.isoformat()}  92.4    -",
                    f"{today.isoformat()}  92.1    yes",
                ],
            )

    def test_table_accepts_multiple_views_and_extra_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "humor.txt").write_text("2026-07-01 bom\n", encoding="utf-8")
            (data_dir / "peso.txt").write_text("2026-07-01 97.5\n", encoding="utf-8")
            (data_dir / "café.txt").write_text("2026-07-01 3\n", encoding="utf-8")

            self.run_cli(
                "--data-dir",
                temp_dir,
                "view",
                "save",
                "@saúde",
                "table",
                "+humor",
                "+peso",
            )
            self.run_cli(
                "--data-dir",
                temp_dir,
                "view",
                "save",
                "@trabalho",
                "list",
                "+peso",
                "+café",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "table",
                "from:data",
                "to:data",
                "@saúde",
                "@trabalho",
                "+café",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "date        humor  peso  café",
                    "2026-07-01  bom    97.5  3",
                ],
            )

    def test_table_combines_view_expansion_with_same_day_aggregation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "mood.txt").write_text(
                "# type:text\n2026-07-01 bom\n2026-07-01 triste\n",
                encoding="utf-8",
            )
            (data_dir / "peso.txt").write_text(
                "# type:number\n2026-07-01 97.5\n2026-07-01 97.2\n",
                encoding="utf-8",
            )

            self.run_cli(
                "--data-dir",
                temp_dir,
                "view",
                "save",
                "@saude",
                "table",
                "+mood",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "table",
                "from:2026-07-01",
                "to:2026-07-01",
                "@saude",
                "+peso",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "date        mood         peso",
                    "2026-07-01  bom, triste  194.70",
                ],
            )

    def test_table_defaults_to_all_metrics_with_data_and_data_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text("2026-06-20 92.4\n", encoding="utf-8")
            (data_dir / "gym.txt").write_text("2026-06-22 yes\n", encoding="utf-8")
            (data_dir / "empty.txt").write_text("# type:text\n", encoding="utf-8")

            result = self.run_cli("--data-dir", temp_dir, "table", "from:data", "to:data")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "date        gym  weight",
                    "2026-06-20  -    92.4",
                    "2026-06-21  -    -",
                    "2026-06-22  yes  -",
                ],
            )

    def test_query_data_bounds_respect_filtered_metric_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text(
                "2026-06-20 92.4\n2026-06-21 92.1\n",
                encoding="utf-8",
            )
            (data_dir / "gym.txt").write_text("2026-06-22 yes\n", encoding="utf-8")

            result = self.run_cli("--data-dir", temp_dir, "table", "from:data", "to:data", "+gym")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "date        gym",
                    "2026-06-22  yes",
                ],
            )

    def test_query_with_empty_filtered_dataset_prints_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli("--data-dir", temp_dir, "list", "from:data", "+missing")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")

    def test_query_rejects_mixed_days_and_explicit_range(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "table",
                "30",
                "from:2026-06-01",
                "+weight",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("DIAS cannot be combined with from: or to:", result.stderr)

    def test_query_rejects_invalid_metric_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli("--data-dir", temp_dir, "table", "+../weight")

            self.assertEqual(result.returncode, 2)
            self.assertIn("metric name accepts only", result.stderr)

    def test_view_save_table_view(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "view",
                "save",
                "@pessoal",
                "table",
                "+academia",
                "+peso",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "saved view @pessoal: table +academia +peso\n")
            self.assertEqual(
                json.loads((Path(temp_dir) / ".zentracker" / "views.json").read_text(encoding="utf-8")),
                {
                    "pessoal": {
                        "command": "table",
                        "tokens": ["+academia", "+peso"],
                    }
                },
            )

    def test_view_save_list_view(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "view",
                "save",
                "@humor",
                "list",
                "+humor",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "saved view @humor: list +humor\n")

    def test_view_save_replaces_existing_view(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_cli("--data-dir", temp_dir, "view", "save", "@pessoal", "table", "+peso")

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "view",
                "save",
                "@pessoal",
                "list",
                "+humor",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "replaced view @pessoal: list +humor\n")

    def test_view_list_sorts_views_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_cli("--data-dir", temp_dir, "view", "save", "@pessoal", "table", "+peso")
            self.run_cli("--data-dir", temp_dir, "view", "save", "@humor", "list", "+humor")

            result = self.run_cli("--data-dir", temp_dir, "view", "list")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "@humor list +humor",
                    "@pessoal table +peso",
                ],
            )

    def test_view_list_prints_nothing_without_views(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli("--data-dir", temp_dir, "view", "list")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")

    def test_view_delete_removes_view_and_leaves_empty_object(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_cli("--data-dir", temp_dir, "view", "save", "@pessoal", "table", "+peso")

            result = self.run_cli("--data-dir", temp_dir, "view", "delete", "@pessoal")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "deleted view @pessoal\n")
            self.assertEqual(
                json.loads((Path(temp_dir) / ".zentracker" / "views.json").read_text(encoding="utf-8")),
                {},
            )

    def test_view_execute_uses_default_30_days(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            today = date.today()
            old_day = today - timedelta(days=30)
            data_dir = Path(temp_dir)
            (data_dir / "humor.txt").write_text(
                f"{old_day.isoformat()} antigo\n{today.isoformat()} atual\n",
                encoding="utf-8",
            )
            self.run_cli("--data-dir", temp_dir, "view", "save", "@humor", "list", "+humor")

            result = self.run_cli("--data-dir", temp_dir, "view", "@humor")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip().splitlines(), [f"{today.isoformat()} humor atual"])

    def test_view_execute_accepts_days(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            today = date.today()
            yesterday = today - timedelta(days=1)
            data_dir = Path(temp_dir)
            (data_dir / "peso.txt").write_text(
                f"{yesterday.isoformat()} 97.5\n{today.isoformat()} 97.2\n",
                encoding="utf-8",
            )
            self.run_cli("--data-dir", temp_dir, "view", "save", "@peso", "table", "+peso")

            result = self.run_cli("--data-dir", temp_dir, "view", "@peso", "2")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "date        peso",
                    f"{yesterday.isoformat()}  97.5",
                    f"{today.isoformat()}  97.2",
                ],
            )

    def test_view_execute_accepts_from_and_to(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "peso.txt").write_text(
                "2026-07-01 97.5\n2026-07-02 97.2\n2026-07-03 97.0\n",
                encoding="utf-8",
            )
            self.run_cli("--data-dir", temp_dir, "view", "save", "@peso", "list", "+peso")

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "view",
                "@peso",
                "from:2026-07-02",
                "to:2026-07-03",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "2026-07-02 peso 97.2",
                    "2026-07-03 peso 97.0",
                ],
            )

    def test_view_execute_accepts_additional_view_references_for_metric_expansion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "peso.txt").write_text("2026-07-01 97.5\n", encoding="utf-8")
            (data_dir / "humor.txt").write_text("2026-07-01 bom\n", encoding="utf-8")

            self.run_cli("--data-dir", temp_dir, "view", "save", "@peso", "table", "+peso")
            self.run_cli("--data-dir", temp_dir, "view", "save", "@humor", "list", "+humor")

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "view",
                "@peso",
                "@humor",
                "from:data",
                "to:data",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "date        peso  humor",
                    "2026-07-01  97.5  bom",
                ],
            )

    def test_view_execute_rejects_save_without_at_ref(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli("--data-dir", temp_dir, "view", "save", "pessoal", "table", "+peso")

            self.assertEqual(result.returncode, 2)
            self.assertIn("view references must start with @", result.stderr)

    def test_view_save_rejects_missing_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli("--data-dir", temp_dir, "view", "save", "@pessoal", "table")

            self.assertEqual(result.returncode, 2)
            self.assertIn("at least one +metric", result.stderr)

    def test_view_save_rejects_saved_days(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli("--data-dir", temp_dir, "view", "save", "@pessoal", "table", "30", "+peso")

            self.assertEqual(result.returncode, 2)
            self.assertIn("accepts only +metric tokens", result.stderr)

    def test_view_save_rejects_saved_range_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "view",
                "save",
                "@pessoal",
                "table",
                "from:data",
                "+peso",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("accepts only +metric tokens", result.stderr)

    def test_view_save_rejects_unsupported_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli("--data-dir", temp_dir, "view", "save", "@pessoal", "export", "+peso")

            self.assertEqual(result.returncode, 2)
            self.assertIn("support only list and table", result.stderr)

    def test_view_execute_rejects_unknown_view(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli("--data-dir", temp_dir, "view", "@missing")

            self.assertEqual(result.returncode, 2)
            self.assertIn("unknown view: @missing", result.stderr)

    def test_view_execute_rejects_metric_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_cli("--data-dir", temp_dir, "view", "save", "@pessoal", "table", "+peso")

            result = self.run_cli("--data-dir", temp_dir, "view", "@pessoal", "+sono")

            self.assertEqual(result.returncode, 2)
            self.assertIn("metrics cannot be changed", result.stderr)

    def test_view_names_use_unicode_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            decomposed_name = "cafe\u0301"

            self.run_cli("--data-dir", temp_dir, "view", "save", f"@{decomposed_name}", "list", "+humor")
            result = self.run_cli("--data-dir", temp_dir, "view", "@café", "from:data", "to:data")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("café", json.loads((Path(temp_dir) / ".zentracker" / "views.json").read_text(encoding="utf-8")))

    def test_view_reports_invalid_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            views_file = Path(temp_dir) / ".zentracker" / "views.json"
            views_file.parent.mkdir(parents=True)
            views_file.write_text("{invalid", encoding="utf-8")

            result = self.run_cli("--data-dir", temp_dir, "view", "list")

            self.assertEqual(result.returncode, 2)
            self.assertIn(f"invalid saved views file: {views_file}", result.stderr)

    def test_view_reports_invalid_saved_view_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            views_file = Path(temp_dir) / ".zentracker" / "views.json"
            views_file.parent.mkdir(parents=True)
            views_file.write_text("[]\n", encoding="utf-8")

            result = self.run_cli("--data-dir", temp_dir, "view", "list")

            self.assertEqual(result.returncode, 2)
            self.assertIn("expected an object of view definitions", result.stderr)

    def test_view_uses_data_dir_for_saved_views(self) -> None:
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            self.run_cli("--data-dir", first_dir, "view", "save", "@pessoal", "table", "+peso")

            first_result = self.run_cli("--data-dir", first_dir, "view", "list")
            second_result = self.run_cli("--data-dir", second_dir, "view", "list")

            self.assertEqual(first_result.returncode, 0, first_result.stderr)
            self.assertEqual(second_result.returncode, 0, second_result.stderr)
            self.assertEqual(first_result.stdout, "@pessoal table +peso\n")
            self.assertEqual(second_result.stdout, "")

    def test_metrics_lists_metric_files_with_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text("2026-06-23 92.4\n", encoding="utf-8")
            (data_dir / "gym.txt").write_text("", encoding="utf-8")
            (data_dir / "mood.txt").write_text("# type:text\n2026-06-23 focused\n", encoding="utf-8")

            result = self.run_cli("--data-dir", temp_dir, "metrics")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip().splitlines(), ["mood", "weight"])

    def test_demo_generates_relative_sample_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            today = date.today()

            result = self.run_cli("--data-dir", temp_dir, "demo", "--days", "3")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("generated 3 days of demo data: weight, gym, mood", result.stdout)
            self.assertIn("table 3 +weight +gym +mood", result.stdout)
            self.assertEqual(
                (Path(temp_dir) / "weight.txt").read_text(encoding="utf-8").splitlines()[0],
                "# type:number",
            )
            self.assertEqual(
                (Path(temp_dir) / "gym.txt").read_text(encoding="utf-8").splitlines()[0],
                "# type:bool",
            )
            self.assertIn(
                today.isoformat(),
                (Path(temp_dir) / "mood.txt").read_text(encoding="utf-8"),
            )

    def test_demo_data_is_useful_with_table_shorthand(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_cli("--data-dir", temp_dir, "demo", "--days", "2")

            result = self.run_cli("--data-dir", temp_dir, "table", "2", "+weight", "+gym", "+mood")

            self.assertEqual(result.returncode, 0, result.stderr)
            lines = result.stdout.strip().splitlines()
            self.assertEqual(lines[0], "date        weight  gym  mood")
            self.assertEqual(len(lines), 3)
            self.assertNotIn("  -       -    -", result.stdout)

    def test_demo_refuses_existing_metrics_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text("# type:number\n2026-06-23 92.4\n", encoding="utf-8")

            result = self.run_cli("--data-dir", temp_dir, "demo")

            self.assertEqual(result.returncode, 2)
            self.assertIn("data directory already has metrics", result.stderr)

    def test_demo_force_overwrites_demo_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text("# type:number\n2026-06-23 92.4\n", encoding="utf-8")

            result = self.run_cli("--data-dir", temp_dir, "demo", "--days", "1", "--force")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(date.today().isoformat(), (data_dir / "weight.txt").read_text(encoding="utf-8"))

    def test_export_jsxgraph_outputs_zennotes_code_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text(
                "# type:number\n2026-06-20 92.4\n2026-06-21 92.1\n",
                encoding="utf-8",
            )
            (data_dir / "gym.txt").write_text(
                "# type:bool\n2026-06-20 yes\n2026-06-21 no\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "export",
                "jsxgraph",
                "--from",
                "2026-06-20",
                "--to",
                "2026-06-21",
                "--metrics",
                "weight,gym",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.startswith("```jsxgraph\n"))
            self.assertTrue(result.stdout.rstrip().endswith("```"))
            numeric_payload, bool_payload = parse_jsxgraph_blocks(result.stdout)
            self.assertEqual(numeric_payload["dates"], ["2026-06-20", "2026-06-21"])
            self.assertEqual(bool_payload["dates"], ["2026-06-20", "2026-06-21"])
            self.assertTrue(numeric_payload["axis"])
            curves = [obj for obj in numeric_payload["objects"] if obj["type"] == "curve"]
            self.assertEqual(curves[0]["attributes"]["name"], "weight")
            self.assertEqual(len(curves), 1)
            gym_points = [
                obj
                for obj in bool_payload["objects"]
                if obj["type"] == "point" and obj["args"] in ([0.0, 1.0], [1.0, 0.0])
            ]
            self.assertEqual(len(gym_points), 2)
            labels = [obj for obj in numeric_payload["objects"] if obj["type"] == "text"]
            self.assertEqual(labels[0]["attributes"]["anchorX"], "left")
            self.assertEqual(labels[1]["attributes"]["anchorX"], "right")
            self.assertEqual(labels[0]["args"][1], labels[1]["args"][1])

    def test_export_jsxgraph_splits_numeric_curves_at_missing_dates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text(
                "# type:number\n"
                "2026-06-20 92.4\n"
                "2026-06-21 92.1\n"
                "2026-06-23 91.9\n"
                "2026-06-24 91.7\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "export",
                "jsxgraph",
                "--from",
                "2026-06-20",
                "--to",
                "2026-06-24",
                "--metrics",
                "weight",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = parse_jsxgraph_blocks(result.stdout)[0]
            curves = [obj for obj in payload["objects"] if obj["type"] == "curve"]
            self.assertEqual(
                [curve["args"] for curve in curves],
                [
                    [[0.0, 1.0], [92.4, 92.1]],
                    [[3.0, 4.0], [91.9, 91.7]],
                ],
            )

    def test_export_jsxgraph_rejects_text_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "mood.txt").write_text(
                "# type:text\n2026-06-20 focused\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "export",
                "jsxgraph",
                "--from",
                "2026-06-20",
                "--to",
                "2026-06-20",
                "--metrics",
                "mood",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("mood has non-numeric value", result.stderr)


if __name__ == "__main__":
    unittest.main()
