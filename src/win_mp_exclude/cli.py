from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from . import __version__
from .api import (
    ELEVATION_FLAG,
    AdministratorRequiredError,
    PowerShellError,
    UnsupportedPlatformError,
    add_exclusion,
    build_exclusion_script,
    build_list_script,
    ensure_windows,
    is_admin,
    list_exclusions,
    remove_exclusion,
    request_elevation,
    resolve_target,
)


def print_error(exc: Exception) -> None:
    print(str(exc), file=sys.stderr)


def handle_add_or_remove(
    action: str,
    path: str,
    *,
    dry_run: bool,
    elevation_attempted: bool,
) -> int:
    operation = add_exclusion if action == "add" else remove_exclusion
    result = operation(
        path,
        dry_run=dry_run,
        elevate=False,
        elevation_attempted=elevation_attempted,
    )

    if result.dry_run:
        print(result.script)
        return 0
    if result.elevation_requested:
        print("Administrator elevation was requested. Continue in the elevated window.")
        return 0
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    print(result.message)
    return 0


def handle_list(dry_run: bool) -> int:
    result = list_exclusions(dry_run=dry_run)
    if result.dry_run:
        print(result.script)
        return 0
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.exclusions:
        print("\n".join(result.exclusions))
    else:
        print("No Microsoft Defender path exclusions are configured.")
    return 0


def command_requires_elevation(command: str, *, dry_run: bool) -> bool:
    return command in {"add", "remove", "list"} and not dry_run


def ensure_cli_elevation(args: argparse.Namespace, argv: Sequence[str]) -> bool:
    """Return True when an elevated CLI replacement process was launched."""

    ensure_windows()
    if not command_requires_elevation(args.command, dry_run=args.dry_run):
        return False
    if is_admin():
        return False
    if args.elevation_attempted:
        raise AdministratorRequiredError(
            "This CLI command is not running as administrator after one elevation attempt."
        )
    request_elevation(argv)
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="win-mp-exclude",
        description="Add, remove, or list Microsoft Defender path exclusions.",
    )
    parser.add_argument(
        ELEVATION_FLAG,
        dest="elevation_attempted",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the PowerShell command without running it.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a Defender exclusion path.")
    add_parser.add_argument("path", help="File or folder path to exclude.")

    remove_parser = subparsers.add_parser("remove", help="Remove a Defender exclusion path.")
    remove_parser.add_argument("path", help="File or folder path to remove from exclusions.")

    subparsers.add_parser("list", help="List configured Defender exclusion paths.")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    args = parser.parse_args(list(argv))

    try:
        launched = ensure_cli_elevation(args, argv)
        if launched:
            print("Administrator elevation was requested. Continue in the elevated window.")
            return 0

        if args.command == "add":
            return handle_add_or_remove(
                "add",
                args.path,
                dry_run=args.dry_run,
                elevation_attempted=args.elevation_attempted,
            )
        if args.command == "remove":
            return handle_add_or_remove(
                "remove",
                args.path,
                dry_run=args.dry_run,
                elevation_attempted=args.elevation_attempted,
            )
        if args.command == "list":
            return handle_list(args.dry_run)
    except (AdministratorRequiredError, PowerShellError, UnsupportedPlatformError) as exc:
        print_error(exc)
        return 1

    parser.error("unknown command")
    return 2


__all__ = [
    "ELEVATION_FLAG",
    "add_exclusion",
    "build_exclusion_script",
    "build_list_script",
    "list_exclusions",
    "remove_exclusion",
    "resolve_target",
]
