"""Backend for Arch Linux and Arch-based distros (Manjaro, EndeavourOS, ...).

It turns Vux commands into pacman commands:

==============  ======================  ===========================================
Vux             pacman                  What it does
==============  ======================  ===========================================
install         pacman -S --needed      install, skipping ones already up to date
remove          pacman -Rs              remove, plus dependencies nothing else needs
search          pacman -Ss              search the package databases
update          pacman -Syu             refresh databases and upgrade everything
list            pacman -Q  (-Qe)        list installed (explicitly installed) packages
info            pacman -Si              show details about a package
==============  ======================  ===========================================

Commands that change the system need root, so Vux adds ``sudo`` in front when
you are not already root.

With ``--aur`` Vux uses an AUR helper (paru or yay) instead of pacman, which
also covers the community-run Arch User Repository. Helpers call sudo
themselves, so Vux does not add it for them.
"""

from __future__ import annotations

import shutil
from typing import Callable, List, Optional, Sequence

from vux.backends.base import Backend, Command, validate_packages, validate_search_terms
from vux.errors import VuxError

#: AUR helpers we know how to drive, in order of preference for "auto".
AUR_HELPERS = ("paru", "yay")
#: Programs that can give us root, in order of preference.
PRIVILEGE_TOOLS = ("sudo", "doas")


class PacmanBackend(Backend):
    name = "pacman"

    def __init__(self, *args, use_aur: bool = False, aur_helper: str = "auto", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.use_aur = use_aur
        self.aur_helper = self._pick_aur_helper(aur_helper) if use_aur else None

    @classmethod
    def is_available(cls, which: Callable[[str], Optional[str]] = shutil.which) -> bool:
        return which("pacman") is not None

    # -- helpers --------------------------------------------------------

    def _pick_aur_helper(self, wanted: str) -> str:
        if wanted != "auto":
            if wanted not in AUR_HELPERS:
                raise VuxError(
                    f"unknown AUR helper {wanted!r} (supported: {', '.join(AUR_HELPERS)})"
                )
            if not self.which(wanted):
                raise VuxError(f"AUR helper {wanted!r} is not installed")
            return wanted
        for helper in AUR_HELPERS:
            if self.which(helper):
                return helper
        raise VuxError(
            "--aur needs an AUR helper, but neither paru nor yay is installed. "
            "See https://wiki.archlinux.org/title/AUR_helpers"
        )

    def _privileged(self, args: Sequence[str]) -> Command:
        """Build a command that changes the system (needs root)."""
        if self.aur_helper:
            # paru/yay must NOT run as root; they ask for sudo when needed.
            return [self.aur_helper, *args]
        if self.root:
            return ["pacman", *args]
        for tool in PRIVILEGE_TOOLS:
            if self.which(tool):
                return [tool, "pacman", *args]
        raise VuxError("this command needs root: run it as root, or install sudo")

    def _read_only(self, args: Sequence[str]) -> Command:
        """Build a command that only reads (no root needed)."""
        return [self.aur_helper or "pacman", *args]

    def _confirm_flag(self) -> List[str]:
        return ["--noconfirm"] if self.assume_yes else []

    # -- the Backend contract -------------------------------------------

    def install_command(self, packages: Sequence[str]) -> Command:
        names = validate_packages(packages)
        return self._privileged(["-S", "--needed", *self._confirm_flag(), *names])

    def remove_command(self, packages: Sequence[str]) -> Command:
        names = validate_packages(packages)
        return self._privileged(["-Rs", *self._confirm_flag(), *names])

    def search_command(self, terms: Sequence[str]) -> Command:
        return self._read_only(["-Ss", *validate_search_terms(terms)])

    def update_command(self) -> Command:
        return self._privileged(["-Syu", *self._confirm_flag()])

    def list_command(self, explicit_only: bool = False) -> Command:
        # Listing installed packages is the same with or without an AUR
        # helper, so always ask pacman directly.
        return ["pacman", "-Qe" if explicit_only else "-Q"]

    def info_command(self, packages: Sequence[str]) -> Command:
        return self._read_only(["-Si", *validate_packages(packages)])
