"""Parse CommonMark tokens without rendering HTML or executing content."""

import re

from markdown_it import MarkdownIt

from .models import CodeBlock, Diagnostic, Document, Section, Value

_MARKER = re.compile(r"<!--\s*readmetwin:section\s+([A-Za-z][A-Za-z0-9._-]{0,63})\s*-->")
_DIRECTIVE = re.compile(r"<!--\s*readmetwin:section\b")
_SHELL_LANGUAGES = {"", "sh", "bash", "zsh", "shell", "console", "shell-session", "text", "powershell", "ps1"}
_INSTALL = re.compile(
    r"^(?:sudo\s+)?(?:"
    r"(?:python(?:\d+(?:\.\d+)*)?\s+-m\s+)?pip(?:\d+(?:\.\d+)*)?\s+install"
    r"|uv\s+(?:pip\s+install|add|sync)"
    r"|pipx\s+install|poetry\s+(?:install|add)|conda\s+install"
    r"|npm\s+(?:install|i|ci)|pnpm\s+(?:install|add)|yarn\s+(?:install|add)"
    r"|(?:brew|cargo|apt|apt-get)\s+install)(?:\s|$)"
)


def _install_commands(content: str, first_line: int) -> list[Value]:
    """Recognize conservative command prefixes, without evaluating a shell."""
    commands: list[Value] = []
    pending = ""
    start = first_line
    for offset, raw in enumerate(content.split("\n")):
        line = raw.strip()
        if not pending:
            start = first_line + offset
            if line.startswith("$ "):
                line = line[2:].lstrip()
        pending += line[:-1].rstrip() + " " if line.endswith("\\") else line
        if line.endswith("\\"):
            continue
        if _INSTALL.match(pending):
            commands.append(Value(pending, start))
        pending = ""
    if pending and _INSTALL.match(pending):
        commands.append(Value(pending.rstrip(), start))
    return commands


def parse_document(text: str, path: str) -> Document:
    """Assign each artifact to its innermost explicit section, once.

    A marker is a standalone HTML comment immediately before a top-level
    Markdown heading (blank lines allowed). Unmarked subheadings inherit
    their marked ancestor; a same/higher heading closes that scope.
    """
    md = MarkdownIt("commonmark")
    # This parser never renders or follows URLs; include even unsafe schemes
    # as inert comparison data instead of silently excluding their targets.
    md.validateLink = lambda url: True
    tokens = md.parse(text)
    source_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    doc = Document(path, [], [])
    markers: dict[int, str] = {}
    directive_tokens: set[int] = set()

    for index, token in enumerate(tokens):
        if token.type != "html_block" or not _DIRECTIVE.match(token.content.strip()):
            continue
        directive_tokens.add(index)
        line = token.map[0] + 1
        match = _MARKER.fullmatch(token.content.strip())
        if match is None or token.level != 0:
            doc.diagnostics.append(Diagnostic(
                "INVALID_SECTION_ID", "error",
                "Use a standalone section marker with an ASCII ID of 1–64 characters.",
                path, line,
            ))
            continue
        following = tokens[index + 1] if index + 1 < len(tokens) else None
        if (following is None or following.type != "heading_open"
                or following.level != 0
                or any(part.strip() for part in source_lines[token.map[1]:following.map[0]])):
            doc.diagnostics.append(Diagnostic(
                "ORPHAN_SECTION_ID", "error",
                "Section marker must immediately precede a heading (blank lines allowed).",
                path, line, match[1],
            ))
            continue
        markers[index + 1] = match[1]

    active: list[Section] = []
    seen: dict[str, int] = {}
    uncovered: int | None = None
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.level == 0:
            depth = int(token.tag[1:])
            while active and active[-1].depth >= depth:
                active.pop()
            if index in markers:
                section_id = markers[index]
                section = Section(section_id, token.map[0] + 1, depth)
                if section_id in seen:
                    doc.diagnostics.append(Diagnostic(
                        "DUPLICATE_SECTION_ID", "error",
                        "Section ID is duplicated; this ID will not be compared.",
                        path, section.line, section_id, path, seen[section_id],
                    ))
                else:
                    seen[section_id] = section.line
                doc.sections.append(section)
                active.append(section)

        if index in directive_tokens:
            continue
        if not active:
            if (uncovered is None and token.map is not None
                    and token.type != "hr"
                    and not (token.type == "html_block" and token.content.lstrip().startswith("<!--"))):
                uncovered = token.map[0] + 1
            continue
        section = active[-1]
        if token.type in {"fence", "code_block"}:
            language = token.info.strip().split()[0].lower() if token.info.strip() else ""
            section.blocks.append(CodeBlock(
                language, token.content.removesuffix("\n"), token.map[0] + 1,
            ))
            if language in _SHELL_LANGUAGES:
                first_line = token.map[0] + (2 if token.type == "fence" else 1)
                section.commands.extend(_install_commands(token.content, first_line))
        elif token.type == "inline":
            for child in token.children or []:
                if child.type in {"link_open", "image"}:
                    target = child.attrGet("href" if child.type == "link_open" else "src")
                    if target is not None:
                        section.links.append(Value(target, token.map[0] + 1))
                elif child.type == "code_inline":
                    section.commands.extend(_install_commands(child.content, token.map[0] + 1))
                elif child.type == "html_inline" and not child.content.startswith("<!--"):
                    doc.diagnostics.append(Diagnostic(
                        "HTML_NOT_CHECKED", "warning",
                        "Raw HTML content is outside Markdown artifact comparison.",
                        path, token.map[0] + 1, section.id,
                    ))
        elif token.type == "html_block" and not token.content.lstrip().startswith("<!--"):
            doc.diagnostics.append(Diagnostic(
                "HTML_NOT_CHECKED", "warning",
                "Raw HTML content is outside Markdown artifact comparison.",
                path, token.map[0] + 1, section.id,
            ))

    if not doc.sections:
        doc.diagnostics.append(Diagnostic(
            "NO_SECTION_IDS", "warning",
            "No paired section IDs found; no content comparison was possible.", path, 1,
        ))
    elif uncovered is not None:
        doc.diagnostics.append(Diagnostic(
            "UNCOVERED_CONTENT", "warning",
            "Content outside an explicit section was not compared.", path, uncovered,
        ))
    return doc
