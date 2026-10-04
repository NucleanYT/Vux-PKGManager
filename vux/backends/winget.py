"""Backend for Windows 10 and 11, using winget (the Windows Package Manager).

winget ships with Windows as part of "App Installer". Vux commands map to:

==============  ======================  ===========================================
Vux             winget                  What it does
==============  ======================  ===========================================
install         winget install          install a package
remove          winget uninstall        uninstall a package
search          winget search           search the package sources
update          winget upgrade --all    upgrade everything that has an update
list            winget list             list installed software
info            winget show             show details about a package
==============  ======================  ===========================================

A package can be given by its ID (``VideoLAN.VLC``), its short name
(``vlc``) or its display name (``"Google Chrome"``); winget works out which
one you mean and asks you to be more specific if several match.

winget handles admin rights itself (Windows shows a UAC prompt when an
installer needs it), so Vux never adds anything like sudo here.
"""

from __future__ import annotations

import shutil
from typing import Callable, List, Optional, Sequence

from vux.backends.base import Backend, Command, validate_search_terms
from vux.errors import InvalidPackageNameError, VuxError


def validate_winget_packages(packages: Sequence[str]) -> List[str]:
    """winget IDs and names can contain spaces and dots, so only reject what
    could be mistaken for an option, or is empty / contains control characters.
    """
    if not packages:
        raise InvalidPackageNameError("no package names given")
    for name in packages:
        if (not name.strip() or name.startswith("-")
                or any(ord(ch) < 32 for ch in name)):
            raise InvalidPackageNameError(f"invalid package name: {name!r}")
    return list(packages)


class WingetBackend(Backend):
    name = "winget"
    # winget handles one package per command, so Vux runs it once per package.
    one_package_per_command = True

    @classmethod
    def is_available(cls, which: Callable[[str], Optional[str]] = shutil.which) -> bool:
        return which("winget") is not None

    def _source_agreement(self) -> List[str]:
        # Without this, winget may ask you to accept a source's terms (e.g. the
        # Microsoft Store's) first. --yes means "don't ask me", so accept it.
        return ["--accept-source-agreements"] if self.assume_yes else []

    def _agreements(self) -> List[str]:
        # Installing also asks you to accept the package's own license terms.
        if self.assume_yes:
            return ["--accept-package-agreements", *self._source_agreement()]
        return []

    def _single(self, packages: Sequence[str]) -> str:
        names = validate_winget_packages(packages)
        if len(names) != 1:
            raise VuxError("winget takes one package at a time")
        return names[0]

    def install_command(self, packages: Sequence[str]) -> Command:
        return ["winget", "install", self._single(packages), *self._agreements()]

    def remove_command(self, packages: Sequence[str]) -> Command:
        return ["winget", "uninstall", self._single(packages), *self._source_agreement()]

    def search_command(self, terms: Sequence[str]) -> Command:
        # winget search takes a single query, so join the words into one.
        query = " ".join(validate_search_terms(terms))
        return ["winget", "search", query, *self._source_agreement()]

    def update_command(self) -> Command:
        return ["winget", "upgrade", "--all", *self._agreements()]

    def list_command(self, explicit_only: bool = False) -> Command:
        if explicit_only:
            raise VuxError("--explicit is only supported on Arch Linux")
        return ["winget", "list", *self._source_agreement()]

    def info_command(self, packages: Sequence[str]) -> Command:
        return ["winget", "show", self._single(packages), *self._source_agreement()]
