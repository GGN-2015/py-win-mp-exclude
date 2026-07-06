"""Manage Microsoft Defender exclusion paths from Python, CLI, or GUI."""

from .api import (
    AdministratorRequiredError,
    DefenderTarget,
    ExclusionListResult,
    ExclusionResult,
    PowerShellError,
    UnsupportedPlatformError,
    WinMpExcludeError,
    add_exclusion,
    change_exclusion,
    is_admin,
    is_windows,
    list_exclusions,
    remove_exclusion,
    resolve_target,
)

__all__ = [
    "__version__",
    "AdministratorRequiredError",
    "DefenderTarget",
    "ExclusionListResult",
    "ExclusionResult",
    "PowerShellError",
    "UnsupportedPlatformError",
    "WinMpExcludeError",
    "add_exclusion",
    "change_exclusion",
    "is_admin",
    "is_windows",
    "list_exclusions",
    "remove_exclusion",
    "resolve_target",
]

__version__ = "0.2.1"
