"""The ``vux`` command line: reads what you typed and calls the right backend."""

from __future__ import annotations

import argparse
import shutil
import sys
from typing import Callable, List, Optional, Sequence

from vux import __version__
from vux.backends import BACKENDS, auto_backend_name, get_backend
from vux.backends.base import Backend, Runner, dry_run_runner
from vux.errors import VuxError
from vux.platform_detect import PlatformInfo, detect_platform


def _common_options() -> argparse.ArgumentParser:
    """Options every command accepts, e.g. ``vux install firefox --yes``."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-n", "--dry-run", action="store_true",
        help="show the command Vux would run, without running it",
    )
    common.add_argument(
        "-y", "--yes", action="store_true",
        help="don't ask for confirmation",
    )
    common.add_argument(
        "--backend", choices=sorted(BACKENDS),
        help="force a backend instead of detecting one",
    )
    common.add_argument(
        "--aur", action="store_true",
        help="(Arch) also use the AUR, through paru or yay",
    )
    common.add_argument(
        "--aur-helper", default="auto", choices=["auto", "paru", "yay"],
        help="(Arch) which AUR helper --aur uses (default: auto)",
    )
    return common


def build_parser() -> argparse.ArgumentParser:
    common = _common_options()
    parser = argparse.ArgumentParser(
        prog="vux",
        description="Vux PKG Manager: one simple command for installing software.",
    )
    parser.add_argument("--version", action="version", version=f"vux {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    p = sub.add_parser("install", aliases=["i"], parents=[common], help="install packages")
    p.add_argument("packages", nargs="+", metavar="PACKAGE")

    p = sub.add_parser("remove", aliases=["rm", "uninstall"], parents=[common],
                       help="remove packages")
    p.add_argument("packages", nargs="+", metavar="PACKAGE")

    p = sub.add_parser("search", aliases=["s"], parents=[common], help="search for packages")
    p.add_argument("terms", nargs="+", metavar="TERM")

    sub.add_parser("update", aliases=["upgrade", "up"], parents=[common],
                   help="update the package list and upgrade everything")

    p = sub.add_parser("list", aliases=["ls"], parents=[common], help="list installed packages")
    p.add_argument("-e", "--explicit", action="store_true",
                   help="only packages you installed yourself (not dependencies)")

    p = sub.add_parser("info", parents=[common], help="show details about packages")
    p.add_argument("packages", nargs="+", metavar="PACKAGE")

    sub.add_parser("platform", parents=[common],
                   help="show the detected system and which backend Vux would use")
    return parser


# Aliases resolve to these canonical names.
_ALIASES = {
    "i": "install",
    "rm": "remove", "uninstall": "remove",
    "s": "search",
    "upgrade": "update", "up": "update",
    "ls": "list",
}


def _make_backend(
    args: argparse.Namespace,
    info: PlatformInfo,
    runner: Optional[Runner],
    which: Callable[[str], Optional[str]],
    root: Optional[bool],
) -> Backend:
    name = args.backend or auto_backend_name(info)
    options = {
        "runner": dry_run_runner if args.dry_run else runner,
        "assume_yes": args.yes,
        "which": which,
        "root": root,
    }
    if args.aur:
        if name != "pacman":
            raise VuxError("--aur only works with the pacman backend")
        options.update(use_aur=True, aur_helper=args.aur_helper)
    return get_backend(name, **options)


def _command_for(backend: Backend, command: str, args: argparse.Namespace) -> List[str]:
    if command == "install":
        return backend.install_command(args.packages)
    if command == "remove":
        return backend.remove_command(args.packages)
    if command == "search":
        return backend.search_command(args.terms)
    if command == "update":
        return backend.update_command()
    if command == "list":
        return backend.list_command(explicit_only=args.explicit)
    if command == "info":
        return backend.info_command(args.packages)
    raise VuxError(f"unknown command: {command}")  # argparse prevents this


def _show_platform(info: PlatformInfo) -> int:
    print(f"system:  {info.describe()}")
    try:
        print(f"backend: {auto_backend_name(info)}")
    except VuxError as exc:
        print(f"backend: none ({exc})")
    return 0


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    platform_info: Optional[PlatformInfo] = None,
    runner: Optional[Runner] = None,
    which: Callable[[str], Optional[str]] = shutil.which,
    root: Optional[bool] = None,
) -> int:
    """Entry point. Returns the exit code.

    The keyword arguments let tests fake the machine and capture commands
    instead of really running them.
    """
    args = build_parser().parse_args(argv)
    command = _ALIASES.get(args.command, args.command)
    try:
        info = platform_info or detect_platform(which=which)
        if command == "platform":
            return _show_platform(info)
        backend = _make_backend(args, info, runner, which, root)
        return backend.run(_command_for(backend, command, args))
    except VuxError as exc:
        print(f"vux: error: {exc}", file=sys.stderr)
        return 1
