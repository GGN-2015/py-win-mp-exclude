from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

ELEVATION_FLAG = "--elevation-attempted"
WINDOWS_POWERSHELL = "powershell.exe"


class WinMpExcludeError(RuntimeError):
    """Base exception for py-win-mp-exclude."""


class UnsupportedPlatformError(WinMpExcludeError):
    """Raised when the package is used outside Windows."""


class AdministratorRequiredError(WinMpExcludeError):
    """Raised when an operation still is not elevated after one attempt."""


class PowerShellError(WinMpExcludeError):
    """Raised when a Defender PowerShell command fails."""

    def __init__(self, message: str, returncode: int, stdout: str = "", stderr: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


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


@dataclass(frozen=True)
class ExclusionResult:
    """Result for add/remove operations."""

    action: str
    target: DefenderTarget
    script: str
    returncode: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    dry_run: bool = False
    elevation_requested: bool = False
    completed: bool = True

    @property
    def message(self) -> str:
        if self.dry_run:
            return self.script
        if self.elevation_requested:
            return "Administrator elevation was requested."
        status = "Added" if self.action == "add" else "Removed"
        existence_note = "" if self.target.exists else " (path does not currently exist)"
        return f"{status} Defender exclusion for {self.target.kind}: {self.target.display_path}{existence_note}"


@dataclass(frozen=True)
class ExclusionListResult:
    """Result for list operations."""

    exclusions: List[str]
    script: str
    returncode: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    dry_run: bool = False


def is_windows() -> bool:
    return os.name == "nt"


def is_admin() -> bool:
    if not is_windows():
        return False

    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def ensure_windows() -> None:
    if not is_windows():
        raise UnsupportedPlatformError("This tool only supports Windows.")


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
    try:
        cmdlet = {
            "add": "Add-MpPreference",
            "remove": "Remove-MpPreference",
        }[action]
    except KeyError as exc:
        raise ValueError(f"unsupported action: {action}") from exc

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


def request_elevation(argv: Sequence[str]) -> None:
    from py_admin_launch import AdminLaunchError, launch

    command = [sys.executable, "-m", "win_mp_exclude", ELEVATION_FLAG, *argv]

    try:
        launch(command, cwd=os.getcwd(), wait=True)
    except AdminLaunchError as exc:
        raise AdministratorRequiredError(f"Administrator elevation failed: {exc}") from exc


def request_gui_elevation(argv: Sequence[str]) -> None:
    from py_admin_launch import AdminLaunchError, launch

    command = [sys.executable, "-m", "win_mp_exclude.gui", ELEVATION_FLAG, *argv]

    try:
        launch(command, cwd=os.getcwd(), wait=True)
    except AdminLaunchError as exc:
        raise AdministratorRequiredError(f"Administrator elevation failed: {exc}") from exc


def ensure_admin_for_mutation(
    argv: Sequence[str],
    *,
    elevation_attempted: bool = False,
    dry_run: bool = False,
) -> bool:
    """Return True when an elevated replacement process was launched."""

    ensure_windows()
    if dry_run or is_admin():
        return False
    if elevation_attempted:
        raise AdministratorRequiredError(
            "This command is not running as administrator after one elevation attempt."
        )
    request_elevation(argv)
    return True


def _check_completed(completed: subprocess.CompletedProcess[str]) -> None:
    if completed.returncode == 0:
        return

    details = completed.stderr.strip() or completed.stdout.strip() or "PowerShell command failed."
    raise PowerShellError(details, completed.returncode, completed.stdout, completed.stderr)


def change_exclusion(
    action: str,
    path: str,
    *,
    dry_run: bool = False,
    elevate: bool = True,
    elevation_attempted: bool = False,
) -> ExclusionResult:
    ensure_windows()
    target = resolve_target(path)
    script = build_exclusion_script(action, target)

    if dry_run:
        return ExclusionResult(action=action, target=target, script=script, dry_run=True)

    if action not in {"add", "remove"}:
        raise ValueError(f"unsupported action: {action}")

    if not is_admin():
        if elevation_attempted or not elevate:
            raise AdministratorRequiredError(
                "Adding or removing Defender exclusions requires administrator privileges."
            )
        request_elevation([action, path])
        return ExclusionResult(
            action=action,
            target=target,
            script=script,
            elevation_requested=True,
            completed=False,
        )

    completed = run_powershell(script)
    _check_completed(completed)
    return ExclusionResult(
        action=action,
        target=target,
        script=script,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def add_exclusion(
    path: str,
    *,
    dry_run: bool = False,
    elevate: bool = True,
    elevation_attempted: bool = False,
) -> ExclusionResult:
    """Add a file or folder path to Microsoft Defender exclusions."""

    return change_exclusion(
        "add",
        path,
        dry_run=dry_run,
        elevate=elevate,
        elevation_attempted=elevation_attempted,
    )


def remove_exclusion(
    path: str,
    *,
    dry_run: bool = False,
    elevate: bool = True,
    elevation_attempted: bool = False,
) -> ExclusionResult:
    """Remove a file or folder path from Microsoft Defender exclusions."""

    return change_exclusion(
        "remove",
        path,
        dry_run=dry_run,
        elevate=elevate,
        elevation_attempted=elevation_attempted,
    )


def list_exclusions(*, dry_run: bool = False) -> ExclusionListResult:
    """List Microsoft Defender path exclusions."""

    ensure_windows()
    script = build_list_script()
    if dry_run:
        return ExclusionListResult(exclusions=[], script=script, dry_run=True)

    completed = run_powershell(script)
    _check_completed(completed)
    exclusions = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return ExclusionListResult(
        exclusions=exclusions,
        script=script,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
