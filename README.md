# py-win-mp-exclude

`py-win-mp-exclude` is a Windows command line tool for adding, removing, and
listing Microsoft Defender path exclusions.

The tool uses PowerShell's Defender cmdlets:

- `Add-MpPreference -ExclusionPath`
- `Remove-MpPreference -ExclusionPath`
- `Get-MpPreference`

When an `add` or `remove` command starts without administrator privileges, the
program relaunches itself once through
[`py-admin-launch`](https://pypi.org/project/py-admin-launch/). A hidden startup
flag prevents repeated elevation attempts.

## Installation

```powershell
pip install py-win-mp-exclude
```

## Usage

Add a file or folder exclusion:

```powershell
win-mp-exclude add C:\path\to\file.exe
win-mp-exclude add C:\path\to\folder
```

Remove a file or folder exclusion:

```powershell
win-mp-exclude remove C:\path\to\file.exe
win-mp-exclude remove C:\path\to\folder
```

List configured path exclusions:

```powershell
win-mp-exclude list
```

Preview the PowerShell command without running it:

```powershell
win-mp-exclude --dry-run add C:\path\to\folder
```

The package also installs the alias `py-win-mp-exclude`.

## Development

Build with Poetry:

```powershell
poetry build
```

Publish with Poetry:

```powershell
poetry publish
```
