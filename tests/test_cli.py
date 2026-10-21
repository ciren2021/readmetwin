import builtins
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import sysconfig
import urllib.request

import pytest

from readmetwin.cli import _read_document, main


def pair(tmp_path, left_body="", right_body=""):
    paths = [tmp_path / "README.md", tmp_path / "README.zh-CN.md"]
    for path, body in zip(paths, (left_body, right_body)):
        path.write_text(f"<!-- readmetwin:section install -->\n# Install\n{body}\n", encoding="utf-8")
    return paths


def test_default_filenames_pass(tmp_path, monkeypatch, capsys):
    pair(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main([]) == 0
    assert "0 error(s), 0 warning(s)" in capsys.readouterr().out


@pytest.mark.parametrize("strict,expected", [(False, 0), (True, 1)])
def test_warning_exit_status_and_json(tmp_path, capsys, strict, expected):
    paths = pair(tmp_path, "`pip install twin==1`", "`pip install twin==2`")
    arguments = [*map(str, paths), "--format", "json"]
    if strict:
        arguments.append("--strict")
    assert main(arguments) == expected
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == 1
    assert payload["summary"] == {"errors": 0, "warnings": 1}
    assert payload["exit_code"] == expected
    assert payload["diagnostics"][0]["section_id"] == "install"


def test_missing_section_exits_one(tmp_path, capsys):
    paths = pair(tmp_path)
    paths[1].write_text("<!-- readmetwin:section usage -->\n# Usage\n", encoding="utf-8")
    assert main([*map(str, paths)]) == 1
    assert "MISSING_SECTION" in capsys.readouterr().out


def test_unmarked_documents_warn_instead_of_claiming_full_coverage(tmp_path, capsys):
    paths = pair(tmp_path)
    for path in paths:
        path.write_text("# Plain\n", encoding="utf-8")
    assert main([*map(str, paths), "--strict"]) == 1
    assert "NO_SECTION_IDS" in capsys.readouterr().out


@pytest.mark.parametrize("kind", ["missing", "directory", "encoding", "oversize"])
def test_bad_inputs_produce_json_without_tracebacks(tmp_path, monkeypatch, capsys, kind):
    paths = pair(tmp_path)
    if kind == "missing":
        paths[0].unlink()
    elif kind == "directory":
        paths[0] = tmp_path
    elif kind == "encoding":
        paths[0].write_bytes(b"\xff\xfe")
    elif kind == "oversize":
        monkeypatch.setattr("readmetwin.cli.MAX_FILE_BYTES", 1)
    assert main([*map(str, paths), "--format", "json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["exit_code"] == 2
    assert all(d["code"] == "INPUT_ERROR" for d in payload["diagnostics"])


def test_utf8_bom_is_accepted(tmp_path, capsys):
    paths = pair(tmp_path)
    paths[0].write_bytes(b"\xef\xbb\xbf" + paths[0].read_bytes())
    assert main([*map(str, paths)]) == 0


def test_file_reading_preserves_crlf_and_control_z(tmp_path):
    path = tmp_path / "README.md"
    text = "# Readme\r\nBefore\x1aAfter\r\n"
    path.write_bytes(text.encode("utf-8"))
    assert _read_document(path) == text


def test_binary_flag_is_requested_on_platforms_that_need_it(tmp_path, monkeypatch):
    paths = pair(tmp_path)
    binary_flag = 1 << 28
    requested = []
    original_open = os.open

    def capture_flags(path, flags):
        requested.append(flags)
        return original_open(path, flags & ~binary_flag)

    monkeypatch.setattr(os, "O_BINARY", binary_flag, raising=False)
    monkeypatch.setattr(os, "open", capture_flags)
    _read_document(paths[0])
    assert requested[0] & binary_flag


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO not available")
def test_fifo_is_rejected_without_waiting_for_writer(tmp_path, capsys):
    paths = pair(tmp_path)
    paths[0].unlink()
    os.mkfifo(paths[0])
    assert main([*map(str, paths)]) == 2
    assert "regular local file" in capsys.readouterr().out


def test_document_contents_are_never_executed_uploaded_or_rewritten(tmp_path, monkeypatch, capsys):
    sentinel = tmp_path / "executed"
    body = f'''```sh
pip install twin; touch {sentinel}
curl https://example.org/upload --data-binary @README.md
```
```python
from pathlib import Path
Path({str(sentinel)!r}).touch()
```
[remote](https://example.org)
<script>fetch('https://example.org')</script>
'''
    paths = pair(tmp_path, body, body)
    original = [path.read_bytes() for path in paths]

    def forbidden(*args, **kwargs):
        pytest.fail("Checking a README must not execute commands or access the network")

    original_open = builtins.open
    original_os_open = os.open

    def readonly_open(file, mode="r", *args, **kwargs):
        assert not any(flag in mode for flag in "wax+")
        return original_open(file, mode, *args, **kwargs)

    def readonly_os_open(path, flags, *args, **kwargs):
        assert not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        return original_os_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", readonly_open)
    monkeypatch.setattr(os, "open", readonly_os_open)
    monkeypatch.setattr(os, "system", forbidden)
    monkeypatch.setattr(os, "popen", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(http.client.HTTPConnection, "connect", forbidden)
    assert main([*map(str, paths)]) == 0  # Identical raw HTML still emits coverage warnings.
    assert [path.read_bytes() for path in paths] == original
    assert not sentinel.exists()


def test_terminal_control_characters_in_filenames_are_escaped(tmp_path, capsys):
    paths = pair(tmp_path)
    evil = tmp_path / "missing\x1b[31m.md"
    assert main([str(evil), str(paths[1])]) == 2
    output = capsys.readouterr().out
    assert "\x1b" not in output
    assert r"\x1b" in output


def test_permission_error_is_reported(tmp_path, monkeypatch, capsys):
    paths = pair(tmp_path)

    def denied(*args, **kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(os, "open", denied)
    assert main([*map(str, paths)]) == 2
    assert "Permission denied" in capsys.readouterr().out


@pytest.mark.parametrize("arguments,code", [(["--help"], 0), (["--version"], 0),
                                          (["--format", "xml"], 2), (["--unknown"], 2)])
def test_help_version_and_invalid_arguments(arguments, code, capsys):
    with pytest.raises(SystemExit) as error:
        main(arguments)
    assert error.value.code == code


def test_installed_module_and_console_entry_points(tmp_path):
    paths = pair(tmp_path, "[Docs](docs.md)", "[文档](docs.md)")
    # These are fixed test invocations of our CLI, never README-derived commands.
    console = Path(sysconfig.get_path("scripts")) / ("readmetwin.exe" if os.name == "nt" else "readmetwin")
    for command in ([sys.executable, "-m", "readmetwin"], [str(console)]):
        result = subprocess.run([*command, *map(str, paths), "--strict", "--format", "json"],
                                capture_output=True, text=True, check=False, timeout=10)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["diagnostics"] == []
