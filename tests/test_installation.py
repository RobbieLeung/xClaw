"""Exercise the documented installer against disposable targets."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = (ROOT / "docs/usage.md").read_text().split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.target = Path(self.temp.name)

    def install(self):
        return subprocess.run([sys.executable, "-", str(ROOT), str(self.target)],
                              input=INSTALLER, text=True, capture_output=True, timeout=10)

    def test_clean_install_carries_the_script_and_three_roles(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        relative_paths = [".agents/skills/dev-team/SKILL.md",
                          ".agents/skills/dev-team/scripts/run-checks.py",
                          ".codex/config.toml"]
        relative_paths += [".codex/agents/" + name + ".toml"
                           for name in ("architect", "developer", "checker")]
        for relative in relative_paths:
            self.assertEqual((self.target / relative).read_bytes(), (ROOT / relative).read_bytes())

    def test_existing_role_aborts_before_any_installation(self):
        existing = self.target / ".codex/agents/checker.toml"
        existing.parent.mkdir(parents=True)
        existing.write_text("existing configuration")
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(existing.read_text(), "existing configuration")
        self.assertFalse((self.target / ".agents/skills/dev-team").exists())
        self.assertFalse((existing.parent / "architect.toml").exists())

    def test_existing_user_config_is_preserved(self):
        config = self.target / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text('model = "user-selected-model"\n')
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(config.read_text(), 'model = "user-selected-model"\n')
        self.assertIn("merge [agents] manually", result.stdout)


if __name__ == "__main__":
    unittest.main()
