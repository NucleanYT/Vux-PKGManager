import os
import tempfile
import unittest

from tests.helpers import fake_which
from vux.platform_detect import detect_platform, parse_os_release, read_os_release

ARCH_OS_RELEASE = """\
NAME="Arch Linux"
PRETTY_NAME="Arch Linux"
ID=arch
BUILD_ID=rolling
"""

MANJARO_OS_RELEASE = """\
NAME="Manjaro Linux"
PRETTY_NAME="Manjaro Linux"
ID=manjaro
ID_LIKE=arch
"""

UBUNTU_OS_RELEASE = """\
# comment line
PRETTY_NAME="Ubuntu 24.04 LTS"
ID=ubuntu
ID_LIKE=debian

VERSION_ID="24.04"
"""


class ParseOsReleaseTests(unittest.TestCase):
    def test_quoted_and_bare_values(self):
        data = parse_os_release(ARCH_OS_RELEASE)
        self.assertEqual(data["ID"], "arch")
        self.assertEqual(data["NAME"], "Arch Linux")
        self.assertEqual(data["BUILD_ID"], "rolling")

    def test_skips_comments_and_blank_lines(self):
        data = parse_os_release(UBUNTU_OS_RELEASE)
        self.assertEqual(data["VERSION_ID"], "24.04")
        self.assertNotIn("# comment line", data)

    def test_unbalanced_quote_does_not_crash(self):
        self.assertEqual(parse_os_release('NAME="Broken\n')["NAME"], "Broken")

    def test_read_falls_back_to_second_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "os-release")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(ARCH_OS_RELEASE)
            data = read_os_release((os.path.join(tmp, "missing"), path))
        self.assertEqual(data["ID"], "arch")

    def test_read_returns_empty_when_nothing_exists(self):
        self.assertEqual(read_os_release(("/nonexistent/os-release",)), {})


class DetectPlatformTests(unittest.TestCase):
    def detect(self, text, *installed):
        return detect_platform("Linux", parse_os_release(text), fake_which(*installed))

    def test_arch(self):
        info = self.detect(ARCH_OS_RELEASE, "pacman")
        self.assertTrue(info.is_arch_based)
        self.assertTrue(info.has_pacman)
        self.assertEqual(info.describe(), "Linux: Arch Linux (Arch-based)")

    def test_manjaro_counts_as_arch_based(self):
        self.assertTrue(self.detect(MANJARO_OS_RELEASE).is_arch_based)

    def test_endeavouros_counts_as_arch_based(self):
        self.assertTrue(self.detect("ID=endeavouros\nID_LIKE=arch\n").is_arch_based)

    def test_id_like_with_several_values(self):
        self.assertTrue(self.detect('ID=foo\nID_LIKE="bar arch"\n').is_arch_based)

    def test_ubuntu_is_not_arch_based(self):
        info = self.detect(UBUNTU_OS_RELEASE)
        self.assertFalse(info.is_arch_based)
        self.assertFalse(info.has_pacman)

    def test_windows_with_winget(self):
        info = detect_platform("Windows", which=fake_which("winget"))
        self.assertTrue(info.is_windows)
        self.assertTrue(info.has_winget)

    def test_windows(self):
        info = detect_platform("Windows", which=fake_which())
        self.assertFalse(info.has_winget)
        self.assertTrue(info.is_windows)
        self.assertFalse(info.is_linux)
        self.assertFalse(info.is_arch_based)
        self.assertEqual(info.describe(), "Windows")


if __name__ == "__main__":
    unittest.main()
