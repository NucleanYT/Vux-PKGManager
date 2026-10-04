import contextlib
import dataclasses
import io
import unittest

from tests.helpers import ARCH, UBUNTU, WINDOWS, RecordingRunner, fake_which
from vux import __version__
from vux.cli import main


class CliTestCase(unittest.TestCase):
    def run_vux(self, *argv, info=ARCH, installed=("pacman", "sudo"), root=False, exit_code=0):
        """Run vux with a fake machine; returns (exit code, commands, stdout, stderr)."""
        runner = RecordingRunner(exit_code)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv), platform_info=info, runner=runner,
                        which=fake_which(*installed), root=root)
        return code, runner.commands, out.getvalue(), err.getvalue()


class CommandTests(CliTestCase):
    def test_install(self):
        code, commands, _, _ = self.run_vux("install", "firefox")
        self.assertEqual(code, 0)
        self.assertEqual(commands, [["sudo", "pacman", "-S", "--needed", "firefox"]])

    def test_remove(self):
        _, commands, _, _ = self.run_vux("remove", "firefox", "vim")
        self.assertEqual(commands, [["sudo", "pacman", "-Rs", "firefox", "vim"]])

    def test_search(self):
        _, commands, _, _ = self.run_vux("search", "browser")
        self.assertEqual(commands, [["pacman", "-Ss", "browser"]])

    def test_update(self):
        _, commands, _, _ = self.run_vux("update")
        self.assertEqual(commands, [["sudo", "pacman", "-Syu"]])

    def test_list(self):
        _, commands, _, _ = self.run_vux("list")
        self.assertEqual(commands, [["pacman", "-Q"]])
        _, commands, _, _ = self.run_vux("list", "--explicit")
        self.assertEqual(commands, [["pacman", "-Qe"]])

    def test_info(self):
        _, commands, _, _ = self.run_vux("info", "firefox")
        self.assertEqual(commands, [["pacman", "-Si", "firefox"]])

    def test_aliases(self):
        for alias, expected in [("i", "-S"), ("rm", "-Rs"), ("uninstall", "-Rs"),
                                ("s", "-Ss")]:
            with self.subTest(alias=alias):
                _, commands, _, _ = self.run_vux(alias, "vim")
                self.assertIn(expected, commands[0])
        for alias in ["upgrade", "up"]:
            with self.subTest(alias=alias):
                _, commands, _, _ = self.run_vux(alias)
                self.assertEqual(commands, [["sudo", "pacman", "-Syu"]])
        _, commands, _, _ = self.run_vux("ls")
        self.assertEqual(commands, [["pacman", "-Q"]])

    def test_yes_flag(self):
        _, commands, _, _ = self.run_vux("install", "vim", "-y")
        self.assertEqual(commands, [["sudo", "pacman", "-S", "--needed", "--noconfirm", "vim"]])

    def test_aur_flag(self):
        _, commands, _, _ = self.run_vux("install", "--aur", "spotify",
                                         installed=("pacman", "sudo", "paru"))
        self.assertEqual(commands, [["paru", "-S", "--needed", "spotify"]])

    def test_aur_helper_choice(self):
        _, commands, _, _ = self.run_vux("search", "--aur", "--aur-helper", "yay", "x",
                                         installed=("pacman", "paru", "yay"))
        self.assertEqual(commands, [["yay", "-Ss", "x"]])

    def test_exit_code_is_passed_through(self):
        code, _, _, _ = self.run_vux("install", "doesnotexist", exit_code=1)
        self.assertEqual(code, 1)


class DryRunTests(CliTestCase):
    def test_dry_run_prints_and_runs_nothing(self):
        code, commands, out, _ = self.run_vux("install", "--dry-run", "firefox")
        self.assertEqual(code, 0)
        self.assertEqual(commands, [])
        self.assertEqual(out.strip(), "would run: sudo pacman -S --needed firefox")


class ErrorTests(CliTestCase):
    def test_invalid_package_name(self):
        code, commands, _, err = self.run_vux("install", "--", "--root=/")
        self.assertEqual(code, 1)
        self.assertEqual(commands, [])
        self.assertIn("invalid package name", err)

    def test_unsupported_linux(self):
        code, commands, _, err = self.run_vux("install", "vim", info=UBUNTU, installed=())
        self.assertEqual(code, 1)
        self.assertEqual(commands, [])
        self.assertIn("not supported yet", err)

    def test_windows_not_built_yet(self):
        code, _, _, err = self.run_vux("install", "vim", info=WINDOWS, installed=())
        self.assertEqual(code, 1)
        self.assertIn("Windows support is planned", err)

    def test_pacman_present_on_unknown_distro_still_works(self):
        info = dataclasses.replace(UBUNTU, has_pacman=True)
        _, commands, _, _ = self.run_vux("search", "vim", info=info, installed=("pacman",))
        self.assertEqual(commands, [["pacman", "-Ss", "vim"]])

    def test_backend_override(self):
        _, commands, _, _ = self.run_vux("search", "--backend", "pacman", "vim", info=WINDOWS)
        self.assertEqual(commands, [["pacman", "-Ss", "vim"]])

    def test_aur_without_helper(self):
        code, _, _, err = self.run_vux("install", "--aur", "spotify")
        self.assertEqual(code, 1)
        self.assertIn("AUR helper", err)

    def test_missing_arguments_is_usage_error(self):
        with self.assertRaises(SystemExit) as ctx, \
                contextlib.redirect_stderr(io.StringIO()):
            main(["install"], platform_info=ARCH, runner=RecordingRunner())
        self.assertEqual(ctx.exception.code, 2)

    def test_no_command_is_usage_error(self):
        with self.assertRaises(SystemExit) as ctx, \
                contextlib.redirect_stderr(io.StringIO()):
            main([], platform_info=ARCH, runner=RecordingRunner())
        self.assertEqual(ctx.exception.code, 2)


class InfoCommandsTests(CliTestCase):
    def test_platform_on_arch(self):
        code, commands, out, _ = self.run_vux("platform")
        self.assertEqual(code, 0)
        self.assertEqual(commands, [])
        self.assertIn("Arch Linux (Arch-based)", out)
        self.assertIn("backend: pacman", out)

    def test_platform_on_unsupported(self):
        code, _, out, _ = self.run_vux("platform", info=WINDOWS, installed=())
        self.assertEqual(code, 0)
        self.assertIn("backend: none", out)

    def test_version(self):
        out = io.StringIO()
        with self.assertRaises(SystemExit) as ctx, contextlib.redirect_stdout(out):
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn(__version__, out.getvalue())


if __name__ == "__main__":
    unittest.main()
