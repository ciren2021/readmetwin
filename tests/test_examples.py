import json
from pathlib import Path

import pytest

from readmetwin.cli import main

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("directory,expected", [("consistent", 0), ("inconsistent", 1)])
def test_shipped_examples(directory, expected, capsys):
    base = ROOT / "examples" / directory
    assert main([str(base / "README.md"), str(base / "README.zh-CN.md"),
                 "--strict", "--format", "json"]) == expected
    diagnostics = json.loads(capsys.readouterr().out)["diagnostics"]
    if expected:
        assert {issue["code"] for issue in diagnostics} == {
            "MISSING_SECTION", "INSTALL_COMMAND_DIFFERENCE",
            "CODE_BLOCK_DIFFERENCE", "LINK_TARGET_DIFFERENCE",
        }
    else:
        assert diagnostics == []


def test_projects_own_readmes_pass_strict_check(capsys):
    assert main([str(ROOT / "README.md"), str(ROOT / "README.zh-CN.md"), "--strict"]) == 0
    assert "0 error(s), 0 warning(s)" in capsys.readouterr().out
