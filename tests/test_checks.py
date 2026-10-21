import pytest

from readmetwin.checks import compare_documents
from readmetwin.parser import parse_document


def compare(left, right):
    return compare_documents(parse_document(left, "README.md"),
                             parse_document(right, "README.zh-CN.md"))


def section(section_id, body="", title="Title"):
    return f"<!-- readmetwin:section {section_id} -->\n## {title}\n{body}\n"


def test_translated_headings_pair_by_id():
    assert compare(section("install", title="Install"),
                   section("install", title="安装")) == []


def test_missing_sections_are_detected_in_both_directions():
    issues = compare(section("one"), section("two"))
    assert [(d.code, d.section_id, d.severity) for d in issues] == [
        ("MISSING_SECTION", "one", "error"), ("MISSING_SECTION", "two", "error"),
    ]


def test_section_order_is_irrelevant():
    assert compare(section("a") + section("b"), section("b") + section("a")) == []


def test_install_version_conflict_warns_without_claiming_translation_error():
    issues = compare(section("install", "```sh\npip install twin==1\n```"),
                     section("install", "```sh\npip install twin==2\n```"))
    assert {d.code for d in issues} == {"INSTALL_COMMAND_DIFFERENCE", "CODE_BLOCK_DIFFERENCE"}
    assert all(d.severity == "warning" and "review manually" in d.message for d in issues)
    assert issues[0].line == 4
    assert issues[0].related_line == 4


@pytest.mark.parametrize("left,right,code", [
    ("```python\nx = 1\n```", "```python\nx = 2\n```", "CODE_BLOCK_DIFFERENCE"),
    ("```python\nx = 1\n```", "", "CODE_BLOCK_DIFFERENCE"),
    ("```sh\nx\n```", "```python\nx\n```", "CODE_BLOCK_DIFFERENCE"),
    ("[Docs](https://example.org/v1)", "[文档](https://example.org/v2)", "LINK_TARGET_DIFFERENCE"),
    ("[Docs](docs.md)", "", "LINK_TARGET_DIFFERENCE"),
    ("`pip install twin`", "", "INSTALL_COMMAND_DIFFERENCE"),
    ("![Logo](a.png)", "![标志](b.png)", "LINK_TARGET_DIFFERENCE"),
    ("[a](docs.md#a)", "[a](docs.md#b)", "LINK_TARGET_DIFFERENCE"),
])
def test_content_missing_and_conflict_cases(left, right, code):
    assert code in [d.code for d in compare(section("s", left), section("s", right))]


def test_translated_link_labels_titles_and_repetition_are_ignored():
    assert compare(section("s", '[Docs](docs.md "English") [Again](docs.md)'),
                   section("s", '[文档](docs.md "中文")')) == []


def test_reference_links_and_autolinks_equal_inline_links():
    assert compare(section("s", "[Docs][d]\n\n[d]: https://example.org\n"),
                   section("s", "<https://example.org>")) == []


def test_code_fences_and_block_order_are_ignored():
    assert compare(section("s", "```py\nx\n```\n\n```sh\ny\n```"),
                   section("s", "~~~sh\ny\n~~~\n\n~~~py\nx\n~~~")) == []


def test_code_indentation_and_duplicate_blocks_are_preserved():
    block = "```python\nif x:\n    y()\n```\n\n"
    assert compare(section("s", block), section("s", block.replace("    y", "  y")))
    assert compare(section("s", block * 2), section("s", block))


def test_line_endings_do_not_cause_warnings():
    text = section("s", "```sh\npip install twin\n```")
    assert compare(text, text.replace("\n", "\r\n")) == []


def test_links_and_fake_markers_inside_code_are_not_links_or_sections():
    issues = compare(section("s", "```md\n[x](one)\n<!-- readmetwin:section fake -->\n```"),
                     section("s", "```md\n[x](two)\n<!-- readmetwin:section fake -->\n```"))
    assert [d.code for d in issues] == ["CODE_BLOCK_DIFFERENCE"]


def test_duplicate_ids_are_not_arbitrarily_matched():
    issues = compare(section("s", "[a](a)") + section("s", "[b](b)"), section("s", "[c](c)"))
    assert [d.code for d in issues] == ["DUPLICATE_SECTION_ID"]
