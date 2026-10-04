"""The contract every package backend must follow.

Vux itself never installs anything. It translates a friendly command such as
``vux install firefox`` into the right command for the system's real package
manager (pacman on Arch, winget later on Windows) and runs it. Each of those
translators is a "backend". Adding a new platform means writing one new
subclass of :class:`Backend`; the CLI does not change.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from abc import ABC, abstractmethod
from typing import Callable, List, Optional, Sequence

from vux.errors import InvalidPackageNameError, VuxError

Command = List[str]
# A runner takes a command (list of arguments) and returns its exit code.
Runner = Callable[[Sequence[str]], int]

# Letters, digits and @ . _ + - ; must not start with "-" (that would be read
# as an option) or "." . An optional "repo/" prefix such as "extra/" is allowed.
_PACKAGE_NAME = re.compile(r"(?:[A-Za-z0-9][A-Za-z0-9._-]*/)?[A-Za-z0-9@_+][A-Za-z0-9@._+-]*")


def validate_packages(packages: Sequence[str]) -> List[str]:
    """Reject anything that is not a plain package name.

    This stops input like ``--root=/`` from being passed through as an option.
    """
    if not packages:
        raise InvalidPackageNameError("no package names given")
    for name in packages:
        if not _PACKAGE_NAME.fullmatch(name):
            raise InvalidPackageNameError(f"invalid package name: {name!r}")
    return list(packages)


def validate_search_terms(terms: Sequence[str]) -> List[str]:
    if not terms:
        raise InvalidPackageNameError("no search terms given")
    for term in terms:
        if not term or term.startswith("-"):
            raise InvalidPackageNameError(f"invalid search term: {term!r}")
    return list(terms)


def subprocess_runner(command: Sequence[str]) -> int:
    """Run a command, letting it use this terminal (so prompts still work)."""
    try:
        code = subprocess.run(list(command), check=False).returncode
    except FileNotFoundError:
        raise VuxError(f"command not found: {command[0]}") from None
    except KeyboardInterrupt:
        return 130
    # A negative code means the program was killed by a signal; report it the
    # way shells do (128 + signal number).
    return 128 - code if code < 0 else code


def dry_run_runner(command: Sequence[str]) -> int:
    """Print what would run instead of running it."""
    print("would run:", " ".join(command))
    return 0


def is_root() -> bool:
    geteuid = getattr(os, "geteuid", None)  # Windows has no geteuid
    return geteuid is not None and geteuid() == 0


class Backend(ABC):
    """Base class for package backends."""

    #: Short name used by ``--backend`` (e.g. "pacman").
    name: str = ""
    #: True if the tool only accepts one package per command; Vux then runs
    #: the command once for each package.
    one_package_per_command: bool = False

    def __init__(
        self,
        runner: Optional[Runner] = None,
        assume_yes: bool = False,
        which: Callable[[str], Optional[str]] = shutil.which,
        root: Optional[bool] = None,
    ) -> None:
        self.runner: Runner = runner or subprocess_runner
        self.assume_yes = assume_yes
        self.which = which
        self.root = is_root() if root is None else root

    # Each method returns the exact command it would run; ``run`` executes it.
    # Keeping them separate makes the translation easy to test and to show
    # with ``--dry-run``.
    @abstractmethod
    def install_command(self, packages: Sequence[str]) -> Command: ...

    @abstractmethod
    def remove_command(self, packages: Sequence[str]) -> Command: ...

    @abstractmethod
    def search_command(self, terms: Sequence[str]) -> Command: ...

    @abstractmethod
    def update_command(self) -> Command: ...

    @abstractmethod
    def list_command(self, explicit_only: bool = False) -> Command: ...

    @abstractmethod
    def info_command(self, packages: Sequence[str]) -> Command: ...

    def run(self, command: Sequence[str]) -> int:
        return self.runner(command)

    @classmethod
    def is_available(cls, which: Callable[[str], Optional[str]] = shutil.which) -> bool:
        """True if this backend's tools are installed on this machine."""
        return False
