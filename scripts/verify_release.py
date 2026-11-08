
"""Readback verification in a fresh temporary extraction.

Does not recollect HTTP campaigns.
Preserves exact source checksums while allowing insignificant
floating-point serialization differences in reproduced CSVs.
"""

from pathlib import Path
import sys
import subprocess
import tempfile
import shutil
import json
import csv
import hashlib
import time
import math
import re

ROOT = Path(__file__).resolve().parents[1]

FLOAT_REL_TOL = 1e-12
FLOAT_ABS_TOL = 1e-12

INTEGER_PATTERN = re.compile(r"^[+-]?[0-9]+$")


def run(cmd, cwd):
    print("RUN " + " ".join(map(str, cmd)), flush=True)
    subprocess.run(
        [sys.executable, *map(str, cmd)],
        cwd=cwd,
        check=True,
    )


def compare_csv(reference, reproduced, label):
    """Compare CSVs with strict structure and tolerant float values."""

    with Path(reference).open(
        newline="", encoding="utf-8-sig"
    ) as f:
        old = list(csv.reader(f))

    with Path(reproduced).open(
        newline="", encoding="utf-8-sig"
    ) as f:
        new = list(csv.reader(f))

    assert old and new, (label, "Empty CSV")

    assert len(old) == len(new), (
        label,
        "Row count differs",
        len(old),
        len(new),
    )

    assert old[0] == new[0], (
        label,
        "Headers differ",
    )

    expected_columns = len(old[0])
    tolerated_differences = 0

    for row_number, (a, b) in enumerate(zip(old, new), 1):
        assert len(a) == expected_columns, (
            label,
            row_number,
            "Reference column count differs",
        )

        assert len(b) == expected_columns, (
            label,
            row_number,
            "Reproduced column count differs",
        )

        for column_number, (x, y) in enumerate(zip(a, b), 1):

            if x == y:
                continue

            # Reject differences involving integer-valued cells.
            # Counts must match exactly.
            if INTEGER_PATTERN.fullmatch(x) or INTEGER_PATTERN.fullmatch(y):
                raise AssertionError(
                    (
                        label,
                        row_number,
                        column_number,
                        "Integer/text mismatch",
                        x,
                        y,
                    )
                )

            try:
                fx = float(x)
                fy = float(y)
            except ValueError:
                raise AssertionError(
                    (
                        label,
                        row_number,
                        column_number,
                        "Text mismatch",
                        x,
                        y,
                    )
                )

            assert math.isfinite(fx) and math.isfinite(fy), (
                label,
                row_number,
                column_number,
                "Non-finite numeric mismatch",
            )

            assert math.isclose(
                fx,
                fy,
                rel_tol=FLOAT_REL_TOL,
                abs_tol=FLOAT_ABS_TOL,
            ), (
                label,
                row_number,
                column_number,
                "Numeric mismatch",
                x,
                y,
            )

            tolerated_differences += 1

    print(
        f"CSV PASS: {label} "
        f"({len(old) - 1} data rows, "
        f"{tolerated_differences} tolerated float differences)",
        flush=True,
    )


def verify_checksums():
    manifest_path = ROOT / "CHECKSUMS.json"

    if not manifest_path.exists():
        raise FileNotFoundError(
            "CHECKSUMS.json is missing"
        )

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    print(
        f"Checking {len(manifest)} SHA-256 entries...",
        flush=True,
    )

    for name, expected_hash in manifest.items():
        file_path = ROOT / name

        assert file_path.is_file(), (
            "Missing checksum file",
            name,
        )

        actual_hash = hashlib.sha256(
            file_path.read_bytes()
        ).hexdigest()

        assert actual_hash == expected_hash, (
            "Checksum mismatch",
            name,
        )

    print(
        f"CHECKSUM PASS: {len(manifest)} files",
        flush=True,
    )


def main():
    begin = time.monotonic()

    # Validate frozen source and release integrity.
    verify_checksums()

    with tempfile.TemporaryDirectory(
        prefix="syscon-reproduce-"
    ) as tmp:

        work = Path(tmp) / "artifact"

        shutil.copytree(
            ROOT,
            work,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                ".git",
                ".venv",
            ),
        )

        # No pip installation, package import side effects,
        # or services outside loopback.

        # Stage 4 unit tests.
        run(
            [
                "-m",
                "unittest",
                "discover",
                "-s",
                "stage4",
                "-p",
                "test_*.py",
            ],
            work,
        )

        # Independent nonlinear plant unit tests.
        run(
            [
                "independent_v8/experiment/test_plant.py",
            ],
            work,
        )

        # Reproduce original HTTP analysis.
        original = work / "reproduced_original"

        run(
            [
                "original_http/analysis/analyze_stage5.py",
                "--archive",
                "original_http/stage4_results_full_windows_v1.zip",
                "--out",
                original,
            ],
            work,
        )

        original_csv_files = [
            "strategy_summary.csv",
            "scenario_outcomes.csv",
            "paired_gate_v2_gate_v3.csv",
            "paired_intervals.csv",
            "latency_by_scenario.csv",
            "scenario_weight_sensitivity.csv",
        ]

        for name in original_csv_files:
            compare_csv(
                work / "original_http/analysis/outputs" / name,
                original / name,
                name,
            )

        # Window sensitivity analysis.
        run(
            [
                "scripts/window_sensitivity.py",
                "--input",
                original / "input/stage4_results_full_windows_v1",
                "--out",
                work / "sensitivity_reproduced.json",
            ],
            work,
        )

        # Held-out HTTP analysis.
        held_path = work / "validation/analysis.json"

        held = json.loads(
            held_path.read_text(encoding="utf-8")
        )

        run(
            [
                "validation/analyze_validation.py",
            ],
            work,
        )

        assert held == json.loads(
            held_path.read_text(encoding="utf-8")
        ), "Held-out analysis differs"

        print("HELD-OUT ANALYSIS PASS", flush=True)

        # Independent nonlinear two-tank experiment.
        nl = work / "independent_v8/experiment"

        old_nonlinear = json.loads(
            (nl / "analysis.json").read_text(
                encoding="utf-8"
            )
        )

        run(
            [
                "independent_v8/experiment/audit_analyze.py",
            ],
            work,
        )

        assert old_nonlinear == json.loads(
            (nl / "analysis.json").read_text(
                encoding="utf-8"
            )
        ), "Nonlinear analysis differs"

        print("NONLINEAR ANALYSIS PASS", flush=True)

        # Physical trajectory and measurement checks.
        run(
            [
                "independent_v8/experiment/check_trajectories.py",
            ],
            work,
        )

        run(
            [
                "independent_v8/experiment/check_measurement_cases.py",
            ],
            work,
        )

        run(
            [
                "independent_v8/experiment/make_outputs.py",
            ],
            work,
        )

        # Reproduce manuscript tables.
        paper = work / "reproduced_paper"

        run(
            [
                "scripts/reproduce_paper_tables.py",
                "--out",
                paper,
            ],
            work,
        )

        paper_tables = [
            "table_IV.csv",
            "table_V.csv",
            "table_VI.csv",
            "table_VII.csv",
            "table_VIII.csv",
        ]

        for name in paper_tables:
            compare_csv(
                work / "paper_outputs" / name,
                paper / name,
                name,
            )

    print(
        json.dumps(
            {
                "status": "PASS",
                "elapsed_seconds": round(
                    time.monotonic() - begin, 2
                ),
                "original_samples": 27300,
                "heldout_samples": 19200,
                "nonlinear_samples": 1733760,
                "assessments": 50040,
                "new_http_campaign_collected": False,
                "nonlinear_process_trajectories_numerically_checked": 320,
                "csv_relative_tolerance": FLOAT_REL_TOL,
                "csv_absolute_tolerance": FLOAT_ABS_TOL,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
