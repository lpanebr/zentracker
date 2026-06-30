from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
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
                "humor",
                "bom",
                "--date",
                "2026-06-23",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("registrado: humor bom em 2026-06-23", result.stdout)
            self.assertEqual(
                (Path(temp_dir) / "humor.txt").read_text(encoding="utf-8"),
                "# type:text\n2026-06-23 bom\n",
            )

    def test_add_uses_environment_data_dir_when_data_dir_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            env["ZENTRACKER_DATA_DIR"] = temp_dir

            result = self.run_cli(
                "add",
                "humor",
                "bom",
                "--date",
                "2026-06-23",
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (Path(temp_dir) / "humor.txt").read_text(encoding="utf-8"),
                "# type:text\n2026-06-23 bom\n",
            )

    def test_table_uses_latest_entry_for_same_day(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "peso.txt").write_text(
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
                "peso",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("2026-06-23  92.1", result.stdout)

    def test_table_combines_metrics_and_marks_missing_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "peso.txt").write_text(
                "2026-06-20 92.4\n2026-06-21 92.1\n",
                encoding="utf-8",
            )
            (data_dir / "academia.txt").write_text(
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
                "peso,academia",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip().splitlines(),
                [
                    "data        peso  academia",
                    "2026-06-20  92.4  sim",
                    "2026-06-21  92.1  nao",
                    "2026-06-22  -     sim",
                ],
            )

    def test_add_bool_metric_normalizes_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "academia",
                "true",
                "--type",
                "bool",
                "--date",
                "2026-06-23",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (Path(temp_dir) / "academia.txt").read_text(encoding="utf-8"),
                "# type:bool\n2026-06-23 sim\n",
            )

    def test_add_bool_metric_rejects_invalid_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "academia",
                "talvez",
                "--type",
                "bool",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("bool aceita apenas sim/nao, true/false ou 1/0.", result.stderr)

    def test_add_number_metric_rejects_non_numeric_value_after_header_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "peso.txt").write_text("# type:number\n", encoding="utf-8")

            result = self.run_cli("--data-dir", temp_dir, "add", "peso", "abc")

            self.assertEqual(result.returncode, 2)
            self.assertIn("number exige um valor numerico.", result.stderr)

    def test_add_rejects_type_change_for_existing_metric_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "peso.txt").write_text("# type:number\n", encoding="utf-8")

            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "peso",
                "92",
                "--type",
                "integer",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("peso ja existe como number", result.stderr)

    def test_add_integer_metric_rejects_decimal_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "copos-agua",
                "1.5",
                "--type",
                "integer",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("integer exige um numero inteiro.", result.stderr)

    def test_add_rejects_invalid_metric_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli("--data-dir", temp_dir, "add", "../peso", "92.4")

            self.assertEqual(result.returncode, 2)
            self.assertIn("nome da metrica aceita apenas", result.stderr)

    def test_metrics_lists_metric_files_with_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "peso.txt").write_text("2026-06-23 92.4\n", encoding="utf-8")
            (data_dir / "academia.txt").write_text("", encoding="utf-8")
            (data_dir / "humor.txt").write_text("# type:text\n2026-06-23 bom\n", encoding="utf-8")

            result = self.run_cli("--data-dir", temp_dir, "metrics")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip().splitlines(), ["humor", "peso"])


if __name__ == "__main__":
    unittest.main()
