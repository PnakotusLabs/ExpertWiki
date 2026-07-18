import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from expertwiki.cli import main


class CliTest(unittest.TestCase):
    def test_init_defaults_to_home_dot_expertwiki_directory(self) -> None:
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                output = io.StringIO()
                with (
                    mock.patch("expertwiki.cli.Path.home", return_value=Path(temp_dir)),
                    contextlib.redirect_stdout(output),
                ):
                    exit_code = main(["init", "--title", "Default Wiki"])
            finally:
                os.chdir(previous_cwd)

            root = Path(temp_dir) / ".expertwiki"
            self.assertEqual(exit_code, 0)
            self.assertTrue(root.is_dir())
            self.assertTrue((root / "AGENTS.md").exists())
            self.assertIn("Initialized ExpertWiki bundle", output.getvalue())


if __name__ == "__main__":
    unittest.main()
