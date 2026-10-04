import contextlib
import io
import sys
import unittest

from vux.backends.base import dry_run_runner, subprocess_runner
from vux.errors import VuxError


class SubprocessRunnerTests(unittest.TestCase):
    def test_returns_exit_code(self):
        self.assertEqual(subprocess_runner([sys.executable, "-c", "raise SystemExit(4)"]), 4)

    def test_missing_program_is_a_clear_error(self):
        with self.assertRaises(VuxError):
            subprocess_runner(["vux-no-such-program-xyz"])

    @unittest.skipIf(sys.platform == "win32", "POSIX signals only")
    def test_killed_by_signal_maps_to_shell_style_code(self):
        code = subprocess_runner(
            [sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"])
        self.assertEqual(code, 128 + 15)


class DryRunRunnerTests(unittest.TestCase):
    def test_prints_command(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(dry_run_runner(["pacman", "-Syu"]), 0)
        self.assertEqual(out.getvalue(), "would run: pacman -Syu\n")


if __name__ == "__main__":
    unittest.main()
