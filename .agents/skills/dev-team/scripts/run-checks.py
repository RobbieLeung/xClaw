#!/usr/bin/env python3
"""Run one explicit check and record its result; Python 3.9+, macOS/Linux."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


def positive_seconds(value: str) -> float:
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("timeout must be a finite positive number")
    return seconds


def stop_process_group(process: subprocess.Popen) -> None:
    """Terminate the whole check, including children that outlive its leader."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--timeout", type=positive_seconds, default=300)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        parser.error("an explicit check command is required after --")
    if os.name != "posix":
        parser.error("process-group cleanup requires macOS or Linux")
    cwd = args.cwd.expanduser().resolve()
    if not cwd.is_dir():
        parser.error("--cwd must be an existing directory")
    try:
        output_dir = args.output_dir.expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        run_dir = Path(tempfile.mkdtemp(prefix="check-", dir=output_dir))
    except OSError:
        parser.error("cannot create --output-dir")

    started = time.monotonic()
    status, exit_code = "launch_failed", 126
    stdout_path, stderr_path = run_dir / "stdout.log", run_dir / "stderr.log"
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            try:
                process = subprocess.Popen(
                    command, cwd=cwd, stdin=subprocess.DEVNULL,
                    stdout=stdout, stderr=stderr, start_new_session=True,
                )
            except FileNotFoundError:
                exit_code = 127
            except OSError:
                pass
            else:
                try:
                    code = process.wait(timeout=args.timeout)
                    exit_code = code if code >= 0 else 128 - code
                    status = "passed" if code == 0 else "failed"
                except subprocess.TimeoutExpired:
                    stop_process_group(process)
                    status, exit_code = "timed_out", 124
                except KeyboardInterrupt:
                    stop_process_group(process)
                    status, exit_code = "interrupted", 130
    except OSError:
        print("could not record check output", file=sys.stderr)
        return 126

    # Do not persist command arguments or the environment: either can contain
    # credentials. The caller supplies a non-sensitive command in its handoff.
    result = {
        "status": status,
        "exit_code": exit_code,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "cwd": str(cwd),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }
    result_path = run_dir / "result.json"
    try:
        result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except OSError:
        print("could not record check result", file=sys.stderr)
        return 126
    print(json.dumps({**result, "result_path": str(result_path)}))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
