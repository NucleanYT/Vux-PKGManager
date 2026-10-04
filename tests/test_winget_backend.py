import unittest

from tests.helpers import RecordingRunner, fake_which
from vux.backends.winget import WingetBackend
from vux.errors import InvalidPackageNameError, VuxError


def backend(**kwargs):
    return WingetBackend(runner=RecordingRunner(), which=fake_which("winget"), **kwargs)


class WingetCommandTests(unittest.TestCase):
    def setUp(self):
        self.winget = backend()

    def test_commands(self):
        self.assertEqual(self.winget.install_command(["VideoLAN.VLC"]),
                         ["winget", "install", "VideoLAN.VLC"])
        self.assertEqual(self.winget.remove_command(["vlc"]), ["winget", "uninstall", "vlc"])
        self.assertEqual(self.winget.search_command(["vlc"]), ["winget", "search", "vlc"])
        self.assertEqual(self.winget.update_command(), ["winget", "upgrade", "--all"])
        self.assertEqual(self.winget.list_command(), ["winget", "list"])
        self.assertEqual(self.winget.info_command(["vlc"]), ["winget", "show", "vlc"])

    def test_never_adds_sudo_even_when_not_admin(self):
        self.assertEqual(backend(root=False).install_command(["vlc"])[0], "winget")

    def test_yes_flags(self):
        winget = backend(assume_yes=True)
        both = ["--accept-package-agreements", "--accept-source-agreements"]
        self.assertEqual(winget.install_command(["vlc"]), ["winget", "install", "vlc", *both])
        self.assertEqual(winget.update_command(), ["winget", "upgrade", "--all", *both])
        self.assertEqual(winget.remove_command(["vlc"]),
                         ["winget", "uninstall", "vlc", "--accept-source-agreements"])
        self.assertEqual(winget.search_command(["vlc"]),
                         ["winget", "search", "vlc", "--accept-source-agreements"])

    def test_search_joins_words_into_one_query(self):
        self.assertEqual(self.winget.search_command(["web", "browser"]),
                         ["winget", "search", "web browser"])

    def test_one_package_per_command(self):
        self.assertTrue(WingetBackend.one_package_per_command)
        with self.assertRaises(VuxError):
            self.winget.install_command(["a", "b"])

    def test_explicit_list_not_supported(self):
        with self.assertRaises(VuxError):
            self.winget.list_command(explicit_only=True)


class WingetNameValidationTests(unittest.TestCase):
    def test_valid(self):
        for name in ["vlc", "VideoLAN.VLC", "Google Chrome", "9NBLGGH4NNS1", "Python.Python.3.12"]:
            with self.subTest(name=name):
                backend().install_command([name])

    def test_invalid(self):
        for name in ["", "   ", "--force", "-h", "vlc\n", "a\tb"]:
            with self.subTest(name=name), self.assertRaises(InvalidPackageNameError):
                backend().install_command([name])

    def test_empty_list(self):
        with self.assertRaises(InvalidPackageNameError):
            backend().install_command([])

    def test_search_rejects_option_like_terms(self):
        with self.assertRaises(InvalidPackageNameError):
            backend().search_command(["--source", "x"])


class AvailabilityTests(unittest.TestCase):
    def test_is_available(self):
        self.assertTrue(WingetBackend.is_available(fake_which("winget")))
        self.assertFalse(WingetBackend.is_available(fake_which()))


if __name__ == "__main__":
    unittest.main()
