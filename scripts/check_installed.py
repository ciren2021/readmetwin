"""Test a built wheel outside the checkout, in a fresh virtual environment.

This developer/CI script installs dependencies from the configured package
index. The ReadmeTwin checker itself remains offline and read-only.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import venv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path, help="Directory containing exactly one built wheel.")
    args = parser.parse_args()
    wheels = list(args.dist.resolve().glob("*.whl"))
    if len(wheels) != 1:
        parser.error("expected exactly one wheel; remove stale builds before retrying")

    with tempfile.TemporaryDirectory(prefix="readmetwin-install-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        scripts = environment / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        console = scripts / ("readmetwin.exe" if os.name == "nt" else "readmetwin")
        isolated = [str(python), "-I", "-X", "utf8"]
        process_env = dict(os.environ, PYTHONUTF8="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
        process_env.pop("PYTHONPATH", None)
        process_env.pop("PYTHONHOME", None)

        def run(arguments: list[str], *, expected: int = 0) -> subprocess.CompletedProcess:
            result = subprocess.run(arguments, cwd=root, env=process_env,
                                    capture_output=True, encoding="utf-8", timeout=180)
            if result.returncode != expected:
                raise RuntimeError(
                    f"Expected exit {expected}, got {result.returncode}: "
                    f"{arguments!r}\n{result.stdout}\n{result.stderr}"
                )
            return result

        # These commands are fixed developer tooling, never extracted from Markdown.
        run([str(python), "-m", "pip", "install", str(wheels[0])])
        run([str(python), "-m", "pip", "check"])
        location = run([*isolated, "-c",
                        "import readmetwin; print(readmetwin.__file__)"]).stdout.strip()
        if not Path(location).resolve().is_relative_to(environment.resolve()):
            raise RuntimeError(f"Imported from outside the installed environment: {location}")

        fixtures = root / "documents with spaces 文档"
        fixtures.mkdir()
        left = fixtures / "README.md"
        right = fixtures / "README.zh-CN.md"
        header = "<!-- readmetwin:section installation -->\n# Installation\n"
        content = header + "```sh\npython -m pip install example-package==1.0\n```\n"
        left.write_text(content, encoding="utf-8", newline="\n")
        right.write_text(content.replace("# Installation", "# 安装"), encoding="utf-8", newline="\n")

        for command in ([*isolated, "-m", "readmetwin"], [str(console)]):
            if not run([*command, "--version"]).stdout.startswith("readmetwin "):
                raise RuntimeError("Missing version output")
            arguments = [*command, str(left), str(right), "--strict", "--format", "json"]
            payload = json.loads(run(arguments).stdout)
            if payload["diagnostics"] or payload["exit_code"] != 0:
                raise RuntimeError(f"Consistent pair failed: {payload}")

        right.write_text(content.replace("==1.0", "==2.0"), encoding="utf-8", newline="\n")
        arguments = [*isolated, "-m", "readmetwin", str(left), str(right), "--format", "json"]
        for strict, expected in ((False, 0), (True, 1)):
            payload = json.loads(run(arguments + (["--strict"] if strict else []), expected=expected).stdout)
            if (payload["summary"] != {"errors": 0, "warnings": 2}
                    or payload["exit_code"] != expected):
                raise RuntimeError(f"Unexpected difference report: {payload}")

        right.unlink()
        payload = json.loads(run(arguments, expected=2).stdout)
        if payload["diagnostics"][0]["code"] != "INPUT_ERROR":
            raise RuntimeError(f"Unexpected input error report: {payload}")
        if left.read_bytes() != content.encode("utf-8"):
            raise RuntimeError("Checker modified input")
    print("Wheel install passed: isolated import, both entry points, version, paths with spaces, "
          "translated headings, JSON, warning/strict/input exit codes, unchanged input.")


if __name__ == "__main__":
    main()
