import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from expertwiki.cli import main
from expertwiki.authoring import init_bundle


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

    def test_status_does_not_initialize_compiler_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "wiki"
            init_bundle(root, title="Read Only Status")

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = main(["status", str(root), "--json"])

            self.assertEqual(exit_code, 0)
            self.assertFalse((root / ".expertwiki" / "state.sqlite").exists())

    def test_view_starts_read_only_server_with_requested_options(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch("expertwiki.cli.serve_viewer") as serve_viewer:
                exit_code = main(
                    [
                        "view",
                        temp_dir,
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "9123",
                        "--no-open",
                    ]
                )

            self.assertEqual(exit_code, 0)
            serve_viewer.assert_called_once_with(
                temp_dir,
                host="127.0.0.1",
                port=9123,
                open_browser=False,
            )


if __name__ == "__main__":
    unittest.main()
