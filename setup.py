#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from setuptools import Command, setup


class RunTests(Command):
    """Compatibility test command for `python setup.py test`."""

    description = "run project tests with unittest discovery"
    user_options: list[tuple[str, str | None, str]] = []

    def initialize_options(self) -> None:  # pragma: no cover - setuptools API
        return None

    def finalize_options(self) -> None:  # pragma: no cover - setuptools API
        return None

    def run(self) -> None:
        root = Path(__file__).resolve().parent
        cmd = [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test*.py",
        ]
        raise SystemExit(subprocess.call(cmd, cwd=root))


setup(cmdclass={"test": RunTests})
