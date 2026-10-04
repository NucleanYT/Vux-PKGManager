"""Figure out which operating system (and Linux distro) we are running on.

On Linux, every modern distro ships ``/etc/os-release``, a small text file of
``KEY=value`` lines. Two keys matter to us:

* ``ID``       the distro itself, e.g. ``arch``, ``manjaro``, ``endeavouros``
* ``ID_LIKE``  distros it is based on, e.g. ``arch`` for Manjaro

A system counts as "Arch-based" when either of those mentions ``arch``.
"""

from __future__ import annotations

import platform as _stdlib_platform
import shlex
import shutil
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Tuple

OS_RELEASE_PATHS = ("/etc/os-release", "/usr/lib/os-release")


@dataclass(frozen=True)
class PlatformInfo:
    """What we know about the machine Vux is running on."""

    system: str  # "linux", "windows", "darwin", ...
    distro_id: str = ""  # from os-release ID, Linux only
    distro_like: Tuple[str, ...] = field(default_factory=tuple)
    distro_name: str = ""  # human-friendly PRETTY_NAME
    has_pacman: bool = False

    @property
    def is_linux(self) -> bool:
        return self.system == "linux"

    @property
    def is_windows(self) -> bool:
        return self.system == "windows"

    @property
    def is_arch_based(self) -> bool:
        if not self.is_linux:
            return False
        return self.distro_id == "arch" or "arch" in self.distro_like

    def describe(self) -> str:
        if self.is_linux:
            name = self.distro_name or self.distro_id or "unknown distro"
            family = " (Arch-based)" if self.is_arch_based else ""
            return f"Linux: {name}{family}"
        if self.is_windows:
            return "Windows"
        return self.system or "unknown"


def parse_os_release(text: str) -> Dict[str, str]:
    """Parse the contents of an os-release file into a dict.

    Values may be quoted ("...") or bare; comments and blank lines are skipped.
    """
    result: Dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        try:
            parts = shlex.split(value)
        except ValueError:
            # Unbalanced quotes: keep the raw text rather than crash.
            parts = [value.strip("\"'")]
        result[key.strip()] = parts[0] if parts else ""
    return result


def read_os_release(paths=OS_RELEASE_PATHS) -> Dict[str, str]:
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                return parse_os_release(handle.read())
        except OSError:
            continue
    return {}


def detect_platform(
    system: Optional[str] = None,
    os_release: Optional[Dict[str, str]] = None,
    which: Callable[[str], Optional[str]] = shutil.which,
) -> PlatformInfo:
    """Detect the current platform.

    Every argument is optional and only exists so tests can pretend to be a
    different machine.
    """
    system = (system or _stdlib_platform.system()).lower()
    if system != "linux":
        return PlatformInfo(system=system)

    if os_release is None:
        os_release = read_os_release()
    return PlatformInfo(
        system="linux",
        distro_id=os_release.get("ID", "").lower(),
        distro_like=tuple(os_release.get("ID_LIKE", "").lower().split()),
        distro_name=os_release.get("PRETTY_NAME", ""),
        has_pacman=which("pacman") is not None,
    )
