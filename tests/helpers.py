"""Shared fakes so tests never run a real package manager."""

from vux.platform_detect import PlatformInfo

ARCH = PlatformInfo(system="linux", distro_id="arch", distro_name="Arch Linux", has_pacman=True)
UBUNTU = PlatformInfo(system="linux", distro_id="ubuntu", distro_like=("debian",),
                      distro_name="Ubuntu 24.04 LTS")
WINDOWS = PlatformInfo(system="windows", has_winget=True)
WINDOWS_NO_WINGET = PlatformInfo(system="windows")


class RecordingRunner:
    """Pretends to run commands and remembers them."""

    def __init__(self, exit_code=0):
        self.exit_code = exit_code
        self.commands = []

    def __call__(self, command):
        self.commands.append(list(command))
        return self.exit_code


def fake_which(*installed):
    """A stand-in for shutil.which that only 'finds' the given programs."""
    found = set(installed)
    return lambda name: f"/usr/bin/{name}" if name in found else None
