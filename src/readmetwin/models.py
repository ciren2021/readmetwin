"""Small data models shared by parsing, checking, and reporting."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Literal["error", "warning"]
    message: str
    path: str
    line: int
    section_id: str | None = None
    related_path: str | None = None
    related_line: int | None = None


@dataclass(frozen=True)
class Value:
    value: str
    line: int


@dataclass(frozen=True)
class CodeBlock:
    language: str
    content: str
    line: int


@dataclass
class Section:
    id: str
    line: int
    depth: int
    blocks: list[CodeBlock] = field(default_factory=list)
    links: list[Value] = field(default_factory=list)
    commands: list[Value] = field(default_factory=list)


@dataclass
class Document:
    path: str
    sections: list[Section]
    diagnostics: list[Diagnostic]
