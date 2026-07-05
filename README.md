# py-win-mp-exclude

`py-win-mp-exclude` is a Windows package for adding, removing, and listing
Microsoft Defender path exclusions from a CLI, a small GUI, or Python code.

The tool uses PowerShell's Defender cmdlets:

- `Add-MpPreference -ExclusionPath`
- `Remove-MpPreference -ExclusionPath`
- `Get-MpPreference`

When a mutating CLI command or the GUI starts without administrator privileges,
the program relaunches itself once through
[`py-admin-launch`](https://pypi.org/project/py-admin-launch/). A hidden startup
flag prevents repeated elevation attempts.

## Installation

```powershell
pip install py-win-mp-exclude
```

## CLI

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

## GUI

Launch the graphical interface:

```powershell
win-mp-exclude-gui
```

The GUI can add exclusions, remove exclusions, remove a selected exclusion, list
current exclusions, and preview the PowerShell command it will run. The package
also installs the alias `py-win-mp-exclude-gui`.

## Python API

The Python API exposes the same add, remove, list, and dry-run capabilities used
by the CLI and GUI:

```python
from win_mp_exclude import add_exclusion, list_exclusions, remove_exclusion

add_result = add_exclusion(r"C:\path\to\folder")
print(add_result.message)

for path in list_exclusions().exclusions:
    print(path)

remove_result = remove_exclusion(r"C:\path\to\folder")
print(remove_result.message)
```

Use `dry_run=True` to inspect the PowerShell script without applying a change:

```python
from win_mp_exclude import add_exclusion

result = add_exclusion(r"C:\path\to\folder", dry_run=True)
print(result.script)
```

By default, Python mutating calls can request administrator elevation once. Pass
`elevate=False` if your program wants to handle elevation itself.

## Development

Build with Poetry:

```powershell
poetry build
```

Publish with Poetry:

```powershell
poetry publish
```
