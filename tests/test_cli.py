from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


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

    def test_add_metric_writes_text_metric_file_by_default(self) -> None:
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

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("recorded: mood focused on 2026-06-23", result.stdout)
            self.assertEqual(
                (Path(temp_dir) / "mood.txt").read_text(encoding="utf-8"),
                "# type:text\n2026-06-23 focused\n",
            )

    def test_add_uses_environment_data_dir_when_data_dir_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            env["ZENTRACKER_DATA_DIR"] = temp_dir

            result = self.run_cli(
                "add",
                "mood",
                "focused",
                "--date",
                "2026-06-23",
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (Path(temp_dir) / "mood.txt").read_text(encoding="utf-8"),
                "# type:text\n2026-06-23 focused\n",
            )

    def test_table_uses_latest_entry_for_same_day(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text(
                "2026-06-23 92.4\n2026-06-23 92.1\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "table",
                "--from",
                "2026-06-23",
                "--to",
                "2026-06-23",
                "--metrics",
                "weight",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("2026-06-23  92.1", result.stdout)

    def test_table_combines_metrics_and_marks_missing_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text(
                "2026-06-20 92.4\n2026-06-21 92.1\n",
                encoding="utf-8",
            )
            (data_dir / "gym.txt").write_text(
                "2026-06-20 sim\n2026-06-21 nao\n2026-06-22 sim\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "table",
                "--from",
                "2026-06-20",
                "--to",
                "2026-06-22",
                "--metrics",
                "weight,gym",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "date        weight  gym",
                    "2026-06-20  92.4    sim",
                    "2026-06-21  92.1    nao",
                    "2026-06-22  -       sim",
                ],
            )

    def test_table_accepts_days_and_metrics_shorthand(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            today = date.today()
            yesterday = today - timedelta(days=1)
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text(
                f"{yesterday.isoformat()} 92.4\n{today.isoformat()} 92.1\n",
                encoding="utf-8",
            )
            (data_dir / "gym.txt").write_text(
                f"{today.isoformat()} sim\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "table",
                "2",
                "weight,gym",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "date        weight  gym",
                    f"{yesterday.isoformat()}  92.4    -",
                    f"{today.isoformat()}  92.1    sim",
                ],
            )

    def test_table_rejects_mixed_shorthand_and_explicit_period(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "table",
                "30",
                "weight",
                "--from",
                "2026-06-01",
                "--to",
                "2026-06-30",
                "--metrics",
                "weight",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("do not mix table DAYS METRICS", result.stderr)

    def test_add_bool_metric_normalizes_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "gym",
                "true",
                "--type",
                "bool",
                "--date",
                "2026-06-23",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (Path(temp_dir) / "gym.txt").read_text(encoding="utf-8"),
                "# type:bool\n2026-06-23 sim\n",
            )

    def test_add_bool_metric_rejects_invalid_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "gym",
                "maybe",
                "--type",
                "bool",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("bool accepts only sim/nao, true/false, or 1/0.", result.stderr)

    def test_add_number_metric_rejects_non_numeric_value_after_header_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text("# type:number\n", encoding="utf-8")

            result = self.run_cli("--data-dir", temp_dir, "add", "weight", "abc")

            self.assertEqual(result.returncode, 2)
            self.assertIn("number requires a numeric value.", result.stderr)

    def test_add_rejects_type_change_for_existing_metric_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text("# type:number\n", encoding="utf-8")

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "weight",
                "92",
                "--type",
                "integer",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("weight already exists as number", result.stderr)

    def test_add_integer_metric_rejects_decimal_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "water-cups",
                "1.5",
                "--type",
                "integer",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("integer requires a whole number.", result.stderr)

    def test_add_rejects_invalid_metric_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli("--data-dir", temp_dir, "add", "../weight", "92.4")

            self.assertEqual(result.returncode, 2)
            self.assertIn("metric name accepts only", result.stderr)

    def test_metrics_lists_metric_files_with_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "weight.txt").write_text("2026-06-23 92.4\n", encoding="utf-8")
            (data_dir / "gym.txt").write_text("", encoding="utf-8")
            (data_dir / "mood.txt").write_text("# type:text\n2026-06-23 focused\n", encoding="utf-8")

            result = self.run_cli("--data-dir", temp_dir, "metrics")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip().splitlines(), ["mood", "weight"])


if __name__ == "__main__":
    unittest.main()
