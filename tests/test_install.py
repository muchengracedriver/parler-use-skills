import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("parler_install", ROOT / "skills/parler-use/scripts/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class Installation(unittest.TestCase):
    def test_full_skill_is_copied_idempotently_and_changed_target_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "parler-use"
            installer.install_skill(target)
            self.assertTrue((target / "scripts/parler.py").is_file())
            self.assertTrue((target / "references/usage-api.md").is_file())
            installer.install_skill(target)
            (target / "SKILL.md").write_text("user customizations")
            with self.assertRaises(RuntimeError):
                installer.install_skill(target)
            self.assertEqual((target / "SKILL.md").read_text(), "user customizations")

    def test_existing_image_skill_is_untouched_and_no_network_is_attempted(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "custom-imagegen"
            target.mkdir()
            marker = target / "custom.txt"
            marker.write_text("keep")
            with patch.object(installer.subprocess, "run") as run:
                installer.install_image(Path(directory), Path(directory))
            run.assert_not_called()
            self.assertEqual(marker.read_text(), "keep")

    def test_image_install_uses_official_helper_correct_path_and_pinned_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            helper = home / "skills/.system/skill-installer/scripts/install-skill-from-github.py"
            helper.parent.mkdir(parents=True)
            helper.write_text("# installer fixture")
            with patch.object(installer.subprocess, "run") as run:
                installer.install_image(home / "skills", home)
            command = run.call_args.args[0]
            self.assertIn(str(helper), command)
            self.assertEqual(command[command.index("--ref") + 1], installer.IMAGE_REF)
            self.assertEqual(command[command.index("--path") + 1], "Custom_Image_Generator_Skill/custom-imagegen")

    def test_existing_mcp_not_overwritten(self):
        with patch.object(installer.shutil, "which", return_value="/usr/bin/codex"), \
             patch.object(installer.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            installer.register_mcp(Path("/tmp/parler.py"))
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0], ["codex", "mcp", "get", "parler-usage"])


if __name__ == "__main__":
    unittest.main()
