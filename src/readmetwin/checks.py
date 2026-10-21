"""Deterministic checks; content differences are review warnings."""

from collections import Counter

from .models import Diagnostic, Document, Section


def _compare_section(left: Section, right: Section, left_path: str, right_path: str) -> list[Diagnostic]:
    checks = [
        ("INSTALL_COMMAND_DIFFERENCE", "Recognized installation commands differ",
         left.commands, right.commands, lambda item: item.value, False),
        ("CODE_BLOCK_DIFFERENCE", "Code blocks differ in language, content, or count",
         left.blocks, right.blocks, lambda item: (item.language, item.content), True),
        ("LINK_TARGET_DIFFERENCE", "Markdown link/image targets differ",
         left.links, right.links, lambda item: item.value, False),
    ]
    diagnostics = []
    for code, message, left_items, right_items, key, count_duplicates in checks:
        left_values = Counter(map(key, left_items))
        right_values = Counter(map(key, right_items))
        if not count_duplicates:
            left_values = Counter({value: 1 for value in left_values})
            right_values = Counter({value: 1 for value in right_values})
        if left_values == right_values:
            continue
        left_diff, right_diff = left_values - right_values, right_values - left_values
        left_line = next((item.line for item in left_items if key(item) in left_diff), left.line)
        right_line = next((item.line for item in right_items if key(item) in right_diff), right.line)
        diagnostics.append(Diagnostic(
            code, "warning",
            f"{message} (left-only: {sum(left_diff.values())}, "
            f"right-only: {sum(right_diff.values())}); review manually, "
            "this does not establish a translation error.",
            left_path, left_line, left.id, right_path, right_line,
        ))
    return diagnostics


def compare_documents(left: Document, right: Document) -> list[Diagnostic]:
    diagnostics = [*left.diagnostics, *right.diagnostics]
    left_counts = Counter(section.id for section in left.sections)
    right_counts = Counter(section.id for section in right.sections)
    for source, target, target_counts in (
        (left, right, right_counts), (right, left, left_counts),
    ):
        reported: set[str] = set()
        for section in source.sections:
            if section.id not in target_counts and section.id not in reported:
                reported.add(section.id)
                diagnostics.append(Diagnostic(
                    "MISSING_SECTION", "error",
                    "Explicit section ID has no counterpart in the other document.",
                    source.path, section.line, section.id, target.path, 1,
                ))
    right_sections = {section.id: section for section in right.sections}
    for section in left.sections:
        if left_counts[section.id] == 1 and right_counts[section.id] == 1:
            diagnostics.extend(_compare_section(
                section, right_sections[section.id], left.path, right.path,
            ))
    return diagnostics
