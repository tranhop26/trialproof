from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

import python_minifier


MAX_SOURCE_BYTES = 50_000
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPOSITORY_ROOT / "contracts" / "trial_proof.py"
ARTIFACT = REPOSITORY_ROOT / "deploy" / "source" / "trial_proof.py"


def build(source: Path, output: Path, *, minify: bool = True) -> bytes:
    readable = source.read_text("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    dependency_header, body = readable.split("\n", 1)
    compact = (
        python_minifier.minify(
            body,
            remove_annotations=False,
            rename_locals=False,
            rename_globals=False,
        )
        if minify
        else body
    )
    data = (dependency_header + "\n" + compact.rstrip() + "\n").encode("utf-8")
    if len(data) >= MAX_SOURCE_BYTES:
        raise ValueError("BRADBURY_SOURCE_TOO_LARGE")
    return data


def write_artifact(output: Path, data: bytes) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as temporary:
        temporary.write(data)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    temporary_path.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = build(SOURCE, ARTIFACT)
    if args.check:
        if not ARTIFACT.is_file() or ARTIFACT.read_bytes() != data:
            raise SystemExit("BRADBURY_SOURCE_ARTIFACT_MISMATCH")
        return 0
    write_artifact(ARTIFACT, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
