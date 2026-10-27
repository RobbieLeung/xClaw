"""Behavioral checks for the deterministic runner, using only local processes."""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / ".agents/skills/dev-team/scripts/run-checks.py"


@unittest.skipUnless(os.name == "posix", "runner supports macOS/Linux")
class RunChecksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.work = self.root / "work with spaces"
        self.work.mkdir()
        self.output = self.root / "artifacts"

    def command(self, *command, timeout="5"):
        return [sys.executable, str(SCRIPT), "--cwd", str(self.work),
                "--timeout", timeout, "--output-dir", str(self.output), "--", *command]

    def run_check(self, code, *arguments, timeout="5"):
        result = subprocess.run(self.command(sys.executable, "-c", code, *arguments,
                                             timeout=timeout),
                                capture_output=True, text=True, timeout=15)
        report = json.loads(result.stdout)
        persisted = json.loads(Path(report["result_path"]).read_text())
        self.assertEqual(persisted, {k: v for k, v in report.items() if k != "result_path"})
        return result, report

    def test_pass_captures_output_and_uses_requested_cwd(self):
        result, report = self.run_check("import os; print(os.getcwd()); print('hello')")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["cwd"], str(self.work))
        self.assertEqual(Path(report["stdout_path"]).read_text(), str(self.work) + "\nhello\n")
        self.assertGreaterEqual(report["elapsed_seconds"], 0)

    def test_failure_preserves_exit_code_and_stderr(self):
        result, report = self.run_check("import sys; print('failure', file=sys.stderr); sys.exit(7)")
        self.assertEqual(result.returncode, 7)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["exit_code"], 7)
        self.assertEqual(Path(report["stderr_path"]).read_text(), "failure\n")

    def test_arguments_are_literal_and_not_persisted_in_report(self):
        marker = self.work / "should-not-exist"
        value = "$(touch " + str(marker) + "); literal * $HOME"
        result, report = self.run_check("import sys; print(sys.argv[1])", value)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(Path(report["stdout_path"]).read_text().strip(), value)
        self.assertNotIn(value, Path(report["result_path"]).read_text())
        self.assertFalse(marker.exists())

    def test_missing_executable_is_not_a_pass(self):
        result = subprocess.run(self.command(str(self.work / "absent")),
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 127)
        self.assertEqual(json.loads(result.stdout)["status"], "launch_failed")

    def test_non_executable_file_is_launch_failure(self):
        executable = self.work / "not executable"
        executable.write_text("no executable permission")
        executable.chmod(0o600)
        result = subprocess.run(self.command(str(executable)),
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 126)
        self.assertEqual(json.loads(result.stdout)["status"], "launch_failed")

    def test_missing_command_fails_before_execution(self):
        result = subprocess.run(self.command(), capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.output.exists())

    def test_invalid_cwd_with_command_does_not_execute(self):
        command = self.command(sys.executable, "-c", "raise RuntimeError('must not execute')")
        command[command.index("--cwd") + 1] = str(self.root / "absent")
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.output.exists())

    def test_invalid_timeouts_are_rejected(self):
        for value in ["0", "-1", "nan", "inf", "not-a-number"]:
            with self.subTest(timeout=value):
                result = subprocess.run(self.command(sys.executable, "-c", "pass", timeout=value),
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(self.output.exists())

    def test_runs_do_not_overwrite_previous_artifacts(self):
        _, first = self.run_check("print('first')")
        _, second = self.run_check("print('second')")
        self.assertNotEqual(first["result_path"], second["result_path"])
        self.assertEqual(Path(first["stdout_path"]).read_text(), "first\n")

    def test_signal_exit_is_reported_as_failure(self):
        result, report = self.run_check("import os, signal; os.kill(os.getpid(), signal.SIGTERM)")
        self.assertEqual(result.returncode, 128 + signal.SIGTERM)
        self.assertEqual(report["status"], "failed")

    def test_timeout_kills_children_even_when_leader_exits_on_term(self):
        marker = self.work / "orphan-wrote-file"
        child = ("import signal,time,pathlib; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
                 "time.sleep(1.5); pathlib.Path(" + repr(str(marker)) + ").touch()")
        parent = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c'," + repr(child) + "]); time.sleep(30)"
        result, report = self.run_check(parent, timeout="0.5")
        self.assertEqual(result.returncode, 124)
        self.assertEqual(report["status"], "timed_out")
        time.sleep(1.6)
        self.assertFalse(marker.exists(), "a child survived the check timeout")

    def test_interrupt_stops_the_running_check(self):
        ready = self.work / "ready"
        marker = self.work / "continued-after-interrupt"
        code = ("import pathlib,time; pathlib.Path(" + repr(str(ready)) + ").touch(); "
                "time.sleep(1); pathlib.Path(" + repr(str(marker)) + ").touch()")
        process = subprocess.Popen(self.command(sys.executable, "-c", code),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(ready.exists())
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 130, stderr)
            self.assertEqual(json.loads(stdout)["status"], "interrupted")
            time.sleep(1.1)
            self.assertFalse(marker.exists())
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


if __name__ == "__main__":
    unittest.main()
