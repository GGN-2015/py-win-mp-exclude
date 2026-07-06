import inspect

from win_mp_exclude import gui


def test_gui_does_not_expose_powershell_preview_controls():
    source = inspect.getsource(gui.DefenderExclusionsApp)

    assert "Preview Add" not in source
    assert "Preview Remove" not in source
    assert 'text="PowerShell"' not in source
    assert "def preview" not in source
