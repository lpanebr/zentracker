from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ZentrackerCliTest(unittest.TestCase):
    def run_cli(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "zentracker", *args],
            cwd=cwd or PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_add_weight_writes_metric_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "peso",
                "92.4",
                "--date",
                "2026-06-23",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("registrado: peso 92.4 em 2026-06-23", result.stdout)
            self.assertEqual(
                (Path(temp_dir) / "peso.txt").read_text(encoding="utf-8"),
                "2026-06-23 92.4\n",
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

    def test_add_academia_rejects_invalid_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli("--data-dir", temp_dir, "add", "academia", "talvez")

            self.assertEqual(result.returncode, 2)
            self.assertIn("academia aceita apenas 'sim' ou 'nao'.", result.stderr)


if __name__ == "__main__":
    unittest.main()
