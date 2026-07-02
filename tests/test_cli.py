from __future__ import annotations

import os
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path


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

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"^zentracker \d+\.\d+\.\d+")

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
                "2026-06-20 yes\n2026-06-21 no\n2026-06-22 yes\n",
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
                    "2026-06-20  92.4    yes",
                    "2026-06-21  92.1    no",
                    "2026-06-22  -       yes",
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
                f"{today.isoformat()} yes\n",
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
                    f"{today.isoformat()}  92.1    yes",
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
                "# type:bool\n2026-06-23 yes\n",
            )

    def test_add_bool_metric_accepts_legacy_sim_nao_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "--data-dir",
                temp_dir,
                "add",
                "gym",
                "sim",
                "--type",
                "bool",
                "--date",
                "2026-06-23",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (Path(temp_dir) / "gym.txt").read_text(encoding="utf-8"),
                "# type:bool\n2026-06-23 yes\n",
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
            self.assertIn("bool accepts only yes/no, true/false, or 1/0.", result.stderr)

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

    def test_demo_generates_relative_sample_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            today = date.today()

            result = self.run_cli("--data-dir", temp_dir, "demo", "--days", "3")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("generated 3 days of demo data: weight, gym, mood", result.stdout)
            self.assertIn("table 3 weight,gym,mood", result.stdout)
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

            result = self.run_cli("--data-dir", temp_dir, "table", "2", "weight,gym,mood")

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
