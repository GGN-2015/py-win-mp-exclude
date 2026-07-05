from pathlib import Path

from win_mp_exclude.cli import (
    build_exclusion_script,
    quote_powershell_string,
    resolve_target,
)


def test_quote_powershell_string_escapes_single_quotes():
    assert quote_powershell_string("C:\\Users\\O'Brien\\file.txt") == "'C:\\Users\\O''Brien\\file.txt'"


def test_build_exclusion_script_uses_add_mp_preference(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("sample", encoding="utf-8")
    target = resolve_target(str(file_path))

    script = build_exclusion_script("add", target)

    assert "Add-MpPreference -ExclusionPath" in script
    assert str(file_path.resolve()) in script


def test_resolve_target_detects_existing_file(tmp_path, monkeypatch):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("sample", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    target = resolve_target("sample.txt")

    assert target.exists is True
    assert target.kind == "file"
    assert target.path == file_path.resolve()


def test_resolve_target_detects_existing_folder(tmp_path):
    folder_path = tmp_path / "folder"
    folder_path.mkdir()

    target = resolve_target(str(folder_path))

    assert target.exists is True
    assert target.kind == "folder"
    assert target.path == folder_path.resolve()


def test_resolve_target_guesses_missing_file_by_suffix(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    target = resolve_target("missing.exe")

    assert target.exists is False
    assert target.kind == "file"
    assert target.path == Path(tmp_path / "missing.exe").resolve()
