import pytest

from readmetwin.parser import parse_document


def parse(text):
    return parse_document(text, "README.md")


def test_extracts_fenced_indented_code_and_reference_links():
    doc = parse('''<!-- readmetwin:section install -->
## Install
```sh
pip install twin
```

    print("hello")

[Docs][ref] and ![Logo](logo.png)

[ref]: https://example.org/docs "Title"
''')
    assert doc.diagnostics == []
    section = doc.sections[0]
    assert (section.id, section.line, section.depth) == ("install", 2, 2)
    assert [(b.language, b.content, b.line) for b in section.blocks] == [
        ("sh", "pip install twin", 3), ("", 'print("hello")', 7),
    ]
    assert [v.value for v in section.links] == ["https://example.org/docs", "logo.png"]


@pytest.mark.parametrize("fence", ["```", "~~~~"])
def test_code_cannot_forge_a_section_marker(fence):
    doc = parse(f'{fence}md\n<!-- readmetwin:section fake -->\n# Fake\n{fence}\n')
    assert doc.sections == []
    assert [d.code for d in doc.diagnostics] == ["NO_SECTION_IDS"]


@pytest.mark.parametrize("text,code", [
    ("<!-- readmetwin:section invalid id -->\n# Title\n", "INVALID_SECTION_ID"),
    ("<!-- readmetwin:section 中文 -->\n# Title\n", "INVALID_SECTION_ID"),
    ("<!-- readmetwin:section orphan -->\nParagraph\n# Title\n", "ORPHAN_SECTION_ID"),
    ("<!-- readmetwin:section orphan -->\n", "ORPHAN_SECTION_ID"),
])
def test_invalid_and_orphan_markers(text, code):
    assert code in [d.code for d in parse(text).diagnostics]


def test_duplicate_ids_have_related_location():
    doc = parse('''<!-- readmetwin:section same -->
# One
<!-- readmetwin:section same -->
# Two
''')
    issue = doc.diagnostics[0]
    assert (issue.code, issue.line, issue.related_line) == ("DUPLICATE_SECTION_ID", 4, 2)


def test_blank_lines_and_setext_headings():
    doc = parse("<!-- readmetwin:section install -->\n\n安装\n====\n")
    assert doc.diagnostics == []
    assert doc.sections[0].id == "install"


def test_scope_inherits_subheadings_and_ends_at_same_level():
    doc = parse('''<!-- readmetwin:section parent -->
## Parent
[a](a)
### Unmarked child
[b](b)
<!-- readmetwin:section child -->
### Marked child
[c](c)
## Outside
[d](d)
''')
    assert [[v.value for v in s.links] for s in doc.sections] == [["a", "b"], ["c"]]
    assert [d.code for d in doc.diagnostics] == ["UNCOVERED_CONTENT"]
    assert doc.diagnostics[0].line == 9


def test_child_scope_returns_to_parent_after_unmarked_peer_heading():
    doc = parse('''<!-- readmetwin:section parent -->
# Parent
<!-- readmetwin:section child -->
## Child
[c](c)
## Peer
[p](p)
''')
    assert [[v.value for v in s.links] for s in doc.sections] == [["p"], ["c"]]


def test_raw_html_is_reported_as_not_checked():
    doc = parse('<!-- readmetwin:section html -->\n# HTML\n<div>hi</div>\n')
    assert [d.code for d in doc.diagnostics] == ["HTML_NOT_CHECKED"]


def test_dangerous_scheme_is_inert_link_data():
    doc = parse('<!-- readmetwin:section links -->\n# Links\n[x](javascript:alert%281%29)\n')
    assert doc.sections[0].links[0].value.startswith("javascript:")


@pytest.mark.parametrize("command", [
    "pip install twin", "pip3.11 install twin", "python3.11 -m pip install twin",
    "uv pip install twin", "uv sync", "uv add twin", "pipx install twin",
    "poetry install", "conda install twin", "npm ci", "npm i twin",
    "pnpm add twin", "yarn install", "brew install twin", "cargo install twin",
    "sudo apt-get install twin",
])
def test_recognizes_common_install_commands(command):
    doc = parse(f"<!-- readmetwin:section install -->\n# Install\n```sh\n$ {command}\n```\n")
    assert [(c.value, c.line) for c in doc.sections[0].commands] == [(command, 4)]


def test_continuations_and_inline_commands_are_data_only():
    doc = parse('''<!-- readmetwin:section install -->
# Install
Run `pip install twin`.
```sh
python -m pip install \\
  twin
```
''')
    assert [(c.value, c.line) for c in doc.sections[0].commands] == [
        ("pip install twin", 3), ("python -m pip install twin", 5),
    ]


def test_does_not_guess_commands_from_prose_or_python_strings():
    doc = parse('''<!-- readmetwin:section install -->
# Install
pip install is a command prefix mentioned in prose.
```python
"pip install twin"
```
```sh
# pip install old
echo 'pip install twin'
pipeline install twin
```
''')
    assert doc.sections[0].commands == []


@pytest.mark.parametrize("depth", [19, 20, 21])
@pytest.mark.parametrize("body", ["[Docs](https://example.org)", "```python\nprint(1)\n```"])
def test_block_nesting_limit_reports_incomplete_coverage(depth, body):
    quoted = "\n".join("> " * depth + line for line in body.splitlines())
    doc = parse("<!-- readmetwin:section s -->\n# Section\n" + quoted + "\n")
    if depth < 20:
        assert doc.diagnostics == []
        assert doc.sections[0].links or doc.sections[0].blocks
    else:
        assert [(d.code, d.severity, d.line, d.section_id) for d in doc.diagnostics] == [
            ("PARSER_LIMIT_REACHED", "warning", 3, "s"),
        ]


@pytest.mark.parametrize("body", [
    "```md\n" + "> " * 30 + "[Docs](docs.md)\n```",
    "    " + "> " * 30 + "[Docs](docs.md)",
    "Use `" + "> " * 30 + "[Docs](docs.md)` as literal text.",
])
def test_literal_nesting_examples_do_not_trigger_limit_warnings(body):
    doc = parse("<!-- readmetwin:section s -->\n# Section\n" + body + "\n")
    assert doc.diagnostics == []


@pytest.mark.parametrize("body", [
    "\n".join("  " * depth + "- item" for depth in range(20)),
    "\n".join("   " * depth + "1. item" for depth in range(20)),
    "> - " * 10 + "[Docs](docs.md)",
])
def test_list_and_mixed_containers_also_report_parser_limit(body):
    doc = parse("<!-- readmetwin:section s -->\n# Section\n" + body + "\n")
    assert [d.code for d in doc.diagnostics] == ["PARSER_LIMIT_REACHED"]


def test_parser_limit_is_reported_once_per_section():
    deep = "> " * 21 + "[Docs](docs.md)\n\n"
    text = ("<!-- readmetwin:section a -->\n# A\n" + deep + deep
            + "<!-- readmetwin:section b -->\n# B\n" + deep)
    assert [d.section_id for d in parse(text).diagnostics] == ["a", "b"]


def test_parser_limit_outside_sections_is_not_silently_ignored():
    doc = parse("> " * 20 + "[Docs](docs.md)\n")
    assert {d.code for d in doc.diagnostics} == {"PARSER_LIMIT_REACHED", "NO_SECTION_IDS"}
    limit = next(d for d in doc.diagnostics if d.code == "PARSER_LIMIT_REACHED")
    assert limit.line == 1
    assert limit.section_id is None
