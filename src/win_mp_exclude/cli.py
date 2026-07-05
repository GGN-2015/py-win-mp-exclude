from __future__ import annotations

import argparse
import ctypes
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from . import __version__

ELEVATION_FLAG = "--elevation-attempted"
WINDOWS_POWERSHELL = "powershell.exe"


@dataclass(frozen=True)
class DefenderTarget:
    """A path that can be passed to Microsoft Defender's ExclusionPath setting."""

    raw: str
    path: Path
    kind: str
    exists: bool

    @property
    def display_path(self) -> str:
        return str(self.path)


def is_windows() -> bool:
    return os.name == "nt"


def is_admin() -> bool:
    if not is_windows():
        return False

    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def resolve_target(raw_path: str) -> DefenderTarget:
    expanded = Path(raw_path).expanduser()
    absolute = expanded if expanded.is_absolute() else Path.cwd() / expanded

    try:
        resolved = absolute.resolve(strict=False)
    except OSError:
        resolved = absolute.absolute()

    exists = resolved.exists()
    if exists:
        kind = "folder" if resolved.is_dir() else "file"
    elif raw_path.endswith(("\\", "/")):
        kind = "folder"
    elif resolved.suffix:
        kind = "file"
    else:
        kind = "path"

    return DefenderTarget(raw=raw_path, path=resolved, kind=kind, exists=exists)


def quote_powershell_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_exclusion_script(action: str, target: DefenderTarget) -> str:
    cmdlet = {
        "add": "Add-MpPreference",
        "remove": "Remove-MpPreference",
    }[action]

    return "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            f"{cmdlet} -ExclusionPath {quote_powershell_string(target.display_path)}",
        ]
    )


def build_list_script() -> str:
    return "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            "$paths = (Get-MpPreference).ExclusionPath",
            "if ($null -ne $paths) { $paths | ForEach-Object { $_ } }",
        ]
    )


def run_powershell(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            WINDOWS_POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def request_elevation(argv: Sequence[str]) -> int:
    from py_admin_launch import AdminLaunchError, launch

    command = [
        sys.executable,
        "-m",
        "win_mp_exclude",
        ELEVATION_FLAG,
        *argv,
    ]

    try:
        launch(command, cwd=os.getcwd(), wait=True)
    except AdminLaunchError as exc:
        print(f"Administrator elevation failed: {exc}", file=sys.stderr)
        return 1

    print("Administrator elevation was requested. Continue in the elevated window.")
    return 0


def ensure_admin(args: argparse.Namespace, original_argv: Sequence[str]) -> Optional[int]:
    if args.command not in {"add", "remove"}:
        return None

    if args.dry_run:
        return None

    if is_admin():
        return None

    if args.elevation_attempted:
        print(
            "This command is not running as administrator after one elevation attempt.",
            file=sys.stderr,
        )
        return 1

    return request_elevation(original_argv)


def print_process_output(completed: subprocess.CompletedProcess[str]) -> None:
    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr)


def handle_add_or_remove(action: str, path: str, dry_run: bool) -> int:
    target = resolve_target(path)
    script = build_exclusion_script(action, target)

    if dry_run:
        print(script)
        return 0

    completed = run_powershell(script)
    print_process_output(completed)
    if completed.returncode != 0:
        return completed.returncode

    status = "Added" if action == "add" else "Removed"
    existence_note = "" if target.exists else " (path does not currently exist)"
    print(f"{status} Defender exclusion for {target.kind}: {target.display_path}{existence_note}")
    return 0


def handle_list(dry_run: bool) -> int:
    script = build_list_script()
    if dry_run:
        print(script)
        return 0

    completed = run_powershell(script)
    print_process_output(completed)
    if completed.returncode != 0:
        return completed.returncode
    if not completed.stdout.strip():
        print("No Microsoft Defender path exclusions are configured.")
    return 0


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

    if not is_windows():
        print("This tool only supports Windows.", file=sys.stderr)
        return 1

    elevation_result = ensure_admin(args, argv)
    if elevation_result is not None:
        return elevation_result

    if args.command == "add":
        return handle_add_or_remove("add", args.path, args.dry_run)
    if args.command == "remove":
        return handle_add_or_remove("remove", args.path, args.dry_run)
    if args.command == "list":
        return handle_list(args.dry_run)

    parser.error("unknown command")
    return 2
