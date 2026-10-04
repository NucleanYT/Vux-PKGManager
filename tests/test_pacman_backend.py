import unittest

from tests.helpers import RecordingRunner, fake_which
from vux.backends.pacman import PacmanBackend
from vux.errors import InvalidPackageNameError, VuxError


def backend(*installed, root=False, **kwargs):
    return PacmanBackend(runner=RecordingRunner(), which=fake_which(*installed), root=root,
                         **kwargs)


class PacmanCommandTests(unittest.TestCase):
    def setUp(self):
        self.pacman = backend("pacman", "sudo")

    def test_install_uses_sudo_and_needed(self):
        self.assertEqual(self.pacman.install_command(["firefox", "git"]),
                         ["sudo", "pacman", "-S", "--needed", "firefox", "git"])

    def test_remove(self):
        self.assertEqual(self.pacman.remove_command(["firefox"]),
                         ["sudo", "pacman", "-Rs", "firefox"])

    def test_update(self):
        self.assertEqual(self.pacman.update_command(), ["sudo", "pacman", "-Syu"])

    def test_search_needs_no_root(self):
        self.assertEqual(self.pacman.search_command(["web", "browser"]),
                         ["pacman", "-Ss", "web", "browser"])

    def test_list(self):
        self.assertEqual(self.pacman.list_command(), ["pacman", "-Q"])
        self.assertEqual(self.pacman.list_command(explicit_only=True), ["pacman", "-Qe"])

    def test_info(self):
        self.assertEqual(self.pacman.info_command(["firefox"]), ["pacman", "-Si", "firefox"])

    def test_yes_adds_noconfirm(self):
        pacman = backend("pacman", "sudo", assume_yes=True)
        self.assertEqual(pacman.install_command(["vim"]),
                         ["sudo", "pacman", "-S", "--needed", "--noconfirm", "vim"])
        self.assertEqual(pacman.remove_command(["vim"]),
                         ["sudo", "pacman", "-Rs", "--noconfirm", "vim"])
        self.assertEqual(pacman.update_command(), ["sudo", "pacman", "-Syu", "--noconfirm"])

    def test_no_sudo_when_already_root(self):
        pacman = backend("pacman", "sudo", root=True)
        self.assertEqual(pacman.install_command(["vim"]), ["pacman", "-S", "--needed", "vim"])

    def test_falls_back_to_doas(self):
        pacman = backend("pacman", "doas")
        self.assertEqual(pacman.update_command(), ["doas", "pacman", "-Syu"])

    def test_error_without_root_or_sudo(self):
        pacman = backend("pacman")
        with self.assertRaises(VuxError):
            pacman.install_command(["vim"])

    def test_repo_prefixed_name_is_allowed(self):
        self.assertEqual(self.pacman.install_command(["extra/firefox"])[-1], "extra/firefox")

    def test_run_passes_command_to_runner(self):
        runner = RecordingRunner(exit_code=3)
        pacman = PacmanBackend(runner=runner, which=fake_which("pacman"), root=True)
        self.assertEqual(pacman.run(pacman.update_command()), 3)
        self.assertEqual(runner.commands, [["pacman", "-Syu"]])


class PackageNameValidationTests(unittest.TestCase):
    def setUp(self):
        self.pacman = backend("pacman", "sudo")

    def test_valid_names(self):
        for name in ["firefox", "lib32-glibc", "python-pip", "gtk+", "c++utilities",
                     "@scope", "foo.bar", "foo_bar", "r8168-dkms"]:
            with self.subTest(name=name):
                self.pacman.install_command([name])

    def test_rejects_options_and_odd_input(self):
        for name in ["--root=/", "-Syu", "", ".hidden", "foo bar", "foo;rm", "a/b/c", "../x", "vim\n"]:
            with self.subTest(name=name), self.assertRaises(InvalidPackageNameError):
                self.pacman.install_command([name])

    def test_rejects_empty_list(self):
        with self.assertRaises(InvalidPackageNameError):
            self.pacman.remove_command([])

    def test_search_rejects_option_like_terms(self):
        with self.assertRaises(InvalidPackageNameError):
            self.pacman.search_command(["--config=/tmp/x"])


class AurTests(unittest.TestCase):
    def test_auto_prefers_paru(self):
        self.assertEqual(backend("pacman", "paru", "yay", use_aur=True).aur_helper, "paru")

    def test_auto_finds_yay(self):
        self.assertEqual(backend("pacman", "yay", use_aur=True).aur_helper, "yay")

    def test_explicit_helper(self):
        self.assertEqual(backend("paru", "yay", use_aur=True, aur_helper="yay").aur_helper, "yay")

    def test_helper_runs_without_sudo(self):
        pacman = backend("pacman", "sudo", "yay", use_aur=True)
        self.assertEqual(pacman.install_command(["visual-studio-code-bin"]),
                         ["yay", "-S", "--needed", "visual-studio-code-bin"])
        self.assertEqual(pacman.update_command(), ["yay", "-Syu"])
        self.assertEqual(pacman.search_command(["spotify"]), ["yay", "-Ss", "spotify"])

    def test_list_still_uses_pacman(self):
        self.assertEqual(backend("yay", use_aur=True).list_command(), ["pacman", "-Q"])

    def test_missing_helper_is_a_clear_error(self):
        with self.assertRaises(VuxError) as ctx:
            backend("pacman", use_aur=True)
        self.assertIn("paru", str(ctx.exception))

    def test_requested_helper_not_installed(self):
        with self.assertRaises(VuxError):
            backend("paru", use_aur=True, aur_helper="yay")

    def test_unknown_helper(self):
        with self.assertRaises(VuxError):
            backend("trizen", use_aur=True, aur_helper="trizen")

    def test_helper_ignored_without_aur_flag(self):
        self.assertIsNone(backend("pacman", "sudo", "yay").aur_helper)


class AvailabilityTests(unittest.TestCase):
    def test_is_available(self):
        self.assertTrue(PacmanBackend.is_available(fake_which("pacman")))
        self.assertFalse(PacmanBackend.is_available(fake_which()))


if __name__ == "__main__":
    unittest.main()
