from pathlib import Path

from win_mp_exclude import __version__
from win_mp_exclude.api import (
    ELEVATION_FLAG,
    ExclusionListResult,
    build_exclusion_script,
    build_list_script,
    change_exclusion,
    quote_powershell_string,
    resolve_target,
)
from win_mp_exclude.cli import build_parser


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


def test_change_exclusion_dry_run_uses_shared_api(tmp_path):
    folder_path = tmp_path / "folder"
    folder_path.mkdir()

    result = change_exclusion("remove", str(folder_path), dry_run=True)

    assert result.dry_run is True
    assert result.completed is True
    assert "Remove-MpPreference -ExclusionPath" in result.script


def test_list_result_dry_run_shape():
    result = ExclusionListResult(exclusions=[], script=build_list_script(), dry_run=True)

    assert result.exclusions == []
    assert "Get-MpPreference" in result.script


def test_cli_parser_accepts_hidden_elevation_flag():
    args = build_parser().parse_args([ELEVATION_FLAG, "add", "C:\\Temp"])

    assert args.elevation_attempted is True
    assert args.command == "add"


def test_version_is_bumped_for_second_publish():
    assert __version__ == "0.2.0"
