import contextlib
import dataclasses
import io
import unittest

from tests.helpers import (ARCH, UBUNTU, WINDOWS, WINDOWS_NO_WINGET, RecordingRunner,
                           fake_which)
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


class WindowsTests(CliTestCase):
    def run_win(self, *argv, exit_code=0):
        return self.run_vux(*argv, info=WINDOWS, installed=("winget",), exit_code=exit_code)

    def test_install(self):
        code, commands, _, _ = self.run_win("install", "vlc")
        self.assertEqual(code, 0)
        self.assertEqual(commands, [["winget", "install", "vlc"]])

    def test_install_several_runs_winget_once_per_package(self):
        _, commands, _, _ = self.run_win("install", "VideoLAN.VLC", "Git.Git")
        self.assertEqual(commands, [["winget", "install", "VideoLAN.VLC"],
                                    ["winget", "install", "Git.Git"]])

    def test_stops_at_first_failure(self):
        code, commands, _, _ = self.run_win("install", "a", "b", exit_code=5)
        self.assertEqual(code, 5)
        self.assertEqual(commands, [["winget", "install", "a"]])

    def test_bad_name_stops_before_running_anything(self):
        code, commands, _, err = self.run_win("install", "vlc", "--", "--force")
        self.assertEqual(code, 1)
        self.assertEqual(commands, [])
        self.assertIn("invalid package name", err)

    def test_name_with_spaces(self):
        _, commands, _, _ = self.run_win("install", "Google Chrome")
        self.assertEqual(commands, [["winget", "install", "Google Chrome"]])

    def test_other_commands(self):
        cases = [
            (("remove", "vlc"), [["winget", "uninstall", "vlc"]]),
            (("search", "web", "browser"), [["winget", "search", "web browser"]]),
            (("update",), [["winget", "upgrade", "--all"]]),
            (("list",), [["winget", "list"]]),
            (("info", "vlc", "git"), [["winget", "show", "vlc"], ["winget", "show", "git"]]),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                self.assertEqual(self.run_win(*argv)[1], expected)

    def test_yes_accepts_agreements(self):
        _, commands, _, _ = self.run_win("install", "vlc", "-y")
        self.assertEqual(commands, [["winget", "install", "vlc", "--accept-package-agreements",
                                     "--accept-source-agreements"]])

    def test_list_explicit_is_an_error(self):
        code, commands, _, err = self.run_win("list", "--explicit")
        self.assertEqual(code, 1)
        self.assertEqual(commands, [])
        self.assertIn("--explicit", err)

    def test_dry_run_prints_each_command(self):
        code, commands, out, _ = self.run_win("install", "-n", "vlc", "git")
        self.assertEqual(code, 0)
        self.assertEqual(commands, [])
        self.assertEqual(out.splitlines(),
                         ["would run: winget install vlc", "would run: winget install git"])


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

    def test_windows_without_winget(self):
        code, commands, _, err = self.run_vux("install", "vlc", info=WINDOWS_NO_WINGET,
                                              installed=())
        self.assertEqual(code, 1)
        self.assertEqual(commands, [])
        self.assertIn("winget was not found", err)

    def test_aur_on_windows_is_an_error(self):
        code, _, _, err = self.run_vux("install", "--aur", "vlc", info=WINDOWS,
                                       installed=("winget",))
        self.assertEqual(code, 1)
        self.assertIn("--aur only works with the pacman backend", err)

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

    def test_platform_on_windows(self):
        code, _, out, _ = self.run_vux("platform", info=WINDOWS, installed=("winget",))
        self.assertEqual(code, 0)
        self.assertIn("system:  Windows", out)
        self.assertIn("backend: winget", out)

    def test_platform_on_unsupported(self):
        code, _, out, _ = self.run_vux("platform", info=WINDOWS_NO_WINGET, installed=())
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
