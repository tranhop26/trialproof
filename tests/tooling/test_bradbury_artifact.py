import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "trial_proof.py"
ARTIFACT = ROOT / "deploy" / "source" / "trial_proof.py"
EXPECTED_HEADER = '# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }'


def test_builder_preserves_dependency_header_and_is_deterministic(tmp_path):
    from scripts.build_bradbury_contract import build

    first = build(CONTRACT, tmp_path / "first.py")
    second = build(CONTRACT, tmp_path / "second.py")
    assert first == second
    assert first.decode("utf-8").splitlines()[0] == EXPECTED_HEADER
    assert b"\r" not in first
    assert len(first) < 50_000


def test_checked_in_artifact_is_current():
    result = subprocess.run(
        [sys.executable, "scripts/build_bradbury_contract.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert ARTIFACT.is_file()


def test_builder_rejects_output_at_strict_size_limit(tmp_path):
    from scripts.build_bradbury_contract import build

    source = tmp_path / "large.py"
    source.write_text(EXPECTED_HEADER + "\nVALUE = '" + ("x" * 60_000) + "'\n", "utf-8")
    with pytest.raises(ValueError, match="BRADBURY_SOURCE_TOO_LARGE"):
        build(source, tmp_path / "artifact.py", minify=False)


def test_contract_lints_without_warnings():
    environment = dict(os.environ, PYTHONIOENCODING="utf-8")
    result = subprocess.run(
        ["genvm-lint", "check", str(CONTRACT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Warnings:" not in output
    assert "Lint passed" in output
