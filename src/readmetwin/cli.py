"""Read-only local CLI. No command execution, rendering, or network clients."""

import argparse
from dataclasses import asdict
from importlib.metadata import version
import json
import os
from pathlib import Path
import stat
import sys

from .checks import compare_documents
from .models import Diagnostic
from .parser import parse_document

MAX_FILE_BYTES = 2 * 1024 * 1024


def _read_document(path: Path) -> str:
    # Nonblocking open prevents a supplied FIFO from hanging the process.
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
                         | getattr(os, "O_BINARY", 0))
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("expected a regular local file")
        if metadata.st_size > MAX_FILE_BYTES:
            raise ValueError("file exceeds the 2 MiB limit")
        content = stream.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            raise ValueError("file exceeds the 2 MiB limit")
    return content.decode("utf-8-sig")


def _terminal_safe(text: str) -> str:
    # Paths can contain terminal escapes; never emit control characters.
    return "".join(char if char.isprintable() else ascii(char)[1:-1] for char in text)


def _report(diagnostics: list[Diagnostic], output_format: str, status: int) -> None:
    errors = sum(issue.severity == "error" for issue in diagnostics)
    warnings = len(diagnostics) - errors
    if output_format == "json":
        print(json.dumps({
            "schema_version": 1,
            "diagnostics": [asdict(issue) for issue in diagnostics],
            "summary": {"errors": errors, "warnings": warnings},
            "exit_code": status,
        }, ensure_ascii=True, indent=2))
        return
    for issue in diagnostics:
        section = f" [{issue.section_id}]" if issue.section_id else ""
        related = (f" (other: {issue.related_path}:{issue.related_line})"
                   if issue.related_path is not None else "")
        print(_terminal_safe(
            f"{issue.path}:{issue.line}: {issue.severity} {issue.code}{section}: "
            f"{issue.message}{related}"
        ))
    print(f"ReadmeTwin: {errors} error(s), {warnings} warning(s).")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="readmetwin",
        description="Compare explicitly paired sections of two local Markdown files.",
    )
    parser.add_argument("left", nargs="?", type=Path, default=Path("README.md"))
    parser.add_argument("right", nargs="?", type=Path, default=Path("README.zh-CN.md"))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--strict", action="store_true", help="Exit 1 for warnings as well as errors.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {version('readmetwin')}")
    args = parser.parse_args(argv)

    documents = []
    diagnostics = []
    for path in (args.left, args.right):
        try:
            text = _read_document(path)
            documents.append(parse_document(text, str(path)))
        except (OSError, UnicodeError, ValueError, RecursionError) as error:
            if isinstance(error, UnicodeError):
                reason = "expected UTF-8 text"
            elif isinstance(error, RecursionError):
                reason = "Markdown nesting exceeds parser limits"
            elif isinstance(error, OSError):
                reason = error.strerror or "unable to read file"
            else:
                reason = str(error)
            diagnostics.append(Diagnostic("INPUT_ERROR", "error", reason, str(path), 1))
    if diagnostics:
        _report(diagnostics, args.format, 2)
        return 2
    diagnostics = compare_documents(*documents)
    status = int(any(issue.severity == "error" or args.strict for issue in diagnostics))
    _report(diagnostics, args.format, status)
    return status


if __name__ == "__main__":
    sys.exit(main())
