"""Choosing the right backend for this machine.

To add a backend, write a new ``Backend`` subclass and add it to
``BACKENDS`` and to ``auto_backend_name``.
"""

from __future__ import annotations

from typing import Dict, Type

from vux.backends.base import Backend
from vux.backends.pacman import PacmanBackend
from vux.backends.winget import WingetBackend
from vux.errors import UnsupportedPlatformError, VuxError
from vux.platform_detect import PlatformInfo

BACKENDS: Dict[str, Type[Backend]] = {
    PacmanBackend.name: PacmanBackend,
    WingetBackend.name: WingetBackend,
}


def auto_backend_name(info: PlatformInfo) -> str:
    """Pick a backend name from the detected platform."""
    if info.is_linux:
        # Trust pacman being installed even if os-release is unusual.
        if info.is_arch_based or info.has_pacman:
            return PacmanBackend.name
        raise UnsupportedPlatformError(
            f"{info.describe()} is not supported yet; Vux currently supports "
            "Arch-based Linux (pacman) and Windows (winget)"
        )
    if info.is_windows:
        if info.has_winget:
            return WingetBackend.name
        raise UnsupportedPlatformError(
            "winget was not found. Install or update \"App Installer\" from the "
            "Microsoft Store: https://aka.ms/getwinget"
        )
    raise UnsupportedPlatformError(f"{info.describe()} is not supported yet")


def get_backend(name: str, **options) -> Backend:
    try:
        cls = BACKENDS[name]
    except KeyError:
        raise VuxError(
            f"unknown backend {name!r} (available: {', '.join(sorted(BACKENDS))})"
        ) from None
    return cls(**options)
