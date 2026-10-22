<!-- readmetwin:section overview -->
# ReadmeTwin

[English](README.md) | [简体中文](README.zh-CN.md)

Local consistency checks for explicitly paired sections of `README.md` and
`README.zh-CN.md`. Compare installation commands, code blocks, Markdown links,
and section presence. Content differences are review warnings, never claims
that a translation is wrong.

Phase 1: Python 3.11+, local CLI only. No website, AI API, telemetry, network
requests, command execution, or document rewriting. The checker reads only the
two supplied files, each a regular UTF-8 file up to 2 MiB (UTF-8 BOM accepted).
Installing dependencies is a separate developer action and may use the network.

<!-- readmetwin:section installation -->
## Install from this checkout

The project has not been published to PyPI: do not use a bare package-name
install. Download the source or clone the GitHub repository, then enter the
`readmetwin/` directory containing `pyproject.toml`. The surrounding `outputs/`
directory is not part of the repository. Use a Python 3.11+ interpreter.

On macOS/Linux, check the interpreter and create a virtual environment:

```sh
python3 --version
python3 -m venv .venv
```

Activate the environment on macOS/Linux:

```sh
. .venv/bin/activate
```

On Windows PowerShell, use the Python launcher and activate the environment:

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Then install:

```sh
python -m pip install .
```

If PowerShell blocks activation, use the environment's Python directly; no
execution-policy change is needed:

```powershell
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m readmetwin README.md README.zh-CN.md --strict
```

Subsequent examples assume the environment is activated. Run `python --version`
to verify it is 3.11 or newer. `python -m readmetwin` is also useful when the
console command cannot be found on PATH.

Runtime dependencies: [markdown-it-py](https://markdown-it-py.readthedocs.io/en/latest/)
and its `mdurl` dependency. CLI arguments, file I/O, comparison, and JSON use the
Python standard library.

<!-- readmetwin:section usage -->
## Usage

With no paths, check the two conventional filenames in the current directory:

```sh
readmetwin
readmetwin README.md README.zh-CN.md
python -m readmetwin README.md README.zh-CN.md --strict --format json
```

`--strict` makes warnings fail the check. `--format text` is the default;
`--format json` emits `schema_version`, `diagnostics`, `summary`, and `exit_code`.
Argument syntax errors use argparse's standard stderr output, even with JSON
selected. Input errors during checking are reported in the selected format.

| Exit code | Meaning |
| --- | --- |
| 0 | No structural errors; warnings allowed unless strict |
| 1 | Structural errors, or any warning in strict mode |
| 2 | Invalid arguments or unreadable/invalid input |

Each diagnostic includes a code, severity, source path, 1-based line, and, when
available, section ID and counterpart location. Inline artifacts point to their
containing paragraph's first line; block artifacts point to their block's first
line. Command diagnostics point to the command line inside a fence. Missing
counterparts use line 1 of the other document. Raw commands, code, and URLs are
omitted from reports to avoid exposing document contents unnecessarily.

<!-- readmetwin:section pairing -->
## Pair sections with explicit IDs

Use the same case-sensitive ID in both documents. Place a standalone marker
immediately before a Markdown heading; blank lines are allowed. IDs start with
an ASCII letter, followed by letters, digits, `.`, `_`, or `-`, up to 64 characters.
Headings inside lists or blockquotes cannot introduce paired sections.

````md
<!-- readmetwin:section installation -->
## Installation / 安装

```sh
python -m pip install example-package==1.0
```
````

A section ends at the next same-level or higher-level heading. Unmarked
subheadings inherit the nearest marked ancestor. A marked child owns its own
artifacts; they are not counted again in the parent. IDs must be unique per
document. Duplicate IDs are reported and excluded from content comparison.

Translated titles and section order do not affect pairing. IDs appearing inside
code blocks are inert examples. Add IDs to all areas you want checked, including
introductory content; uncovered content produces a warning.

<!-- readmetwin:section rules -->
## Comparison rules and limits

- **Structure:** missing, duplicate, malformed, or orphan section IDs are errors.
  No IDs or uncovered content produces a coverage warning. Without IDs, content
  comparison is skipped; default exit 0 with warnings does not imply equality.
- **Code blocks:** compare a multiset of `(language, content)` in each paired
  section. Both fenced and indented blocks are supported. Fence style, block
  order, CRLF/LF, and language capitalization are ignored. Internal spaces,
  comments, blank lines, language names, and duplicate block counts are preserved.
  Only the first word of fence info is used; additional metadata is ignored.
- **Installation commands:** compare distinct recognized commands in shell/text
  blocks and inline code. Strip an optional `$ ` prompt and outer whitespace;
  join backslash continuations. Recognized prefixes: `pip install`, versioned
  `pip`, `python -m pip install` (including versioned Python), `uv pip install`,
  `uv add`, `uv sync`, `pipx install`, `poetry install/add`, `conda install`,
  `npm install/i/ci`, `pnpm install/add`, `yarn install/add`, and
  `brew/cargo/apt/apt-get install`; optional `sudo` is accepted. Supported block
  labels: empty, `sh`, `bash`, `zsh`, `shell`, `console`, `shell-session`, `text`,
  `powershell`, `ps1`. Other commands, prose, environment prefixes, arbitrary
  shell syntax, and semantic equivalence are not inferred. Commands are strings
  only; nothing is evaluated. A command change in a block can produce both
  installation and code warnings.
- **Links:** compare distinct targets of parsed Markdown links and images,
  including reference links and angle-bracket autolinks. Labels, titles, order,
  and repetition are ignored. Targets use the Markdown parser's URL normalization;
  queries, fragments, relative paths, and localized targets may differ
  intentionally and therefore only warn. No URL is fetched; no broken-link or
  local-file existence check is performed.
- **Uncertainty:** every content mismatch is a warning requiring manual review.
  Raw HTML emits `HTML_NOT_CHECKED`; its links/code are not compared. CommonMark
  is the parsing baseline; GFM tables, MDX, includes, and undefined reference
  links are outside this phase's supported syntax. This is not a translation
  quality, code correctness, or security scanner. It does not compare prose or
  prove documents equivalent.
- **Nesting coverage:** the parser retains its block nesting budget of 20.
  Quote/list containers that reach the budget emit `PARSER_LIMIT_REACHED` once
  per section ID (or unpaired area) per file. Lists can consume multiple levels
  per item; this is a parser budget, not a count of heading levels. Content may
  have been skipped, so even identical documents warn at this boundary. Default
  mode still exits 0 unless there are errors; strict mode exits 1 for this
  warning. Quotation characters inside literal code examples do not count.

<!-- readmetwin:section diagnostics -->
## Diagnostic codes

| Code | Severity | Meaning |
| --- | --- | --- |
| MISSING_SECTION | error | ID exists only in one document |
| DUPLICATE_SECTION_ID | error | Ambiguous repeated ID |
| INVALID_SECTION_ID | error | Malformed marker or invalid ID |
| ORPHAN_SECTION_ID | error | Marker is not followed by a heading |
| NO_SECTION_IDS | warning | No paired sections; comparison skipped |
| UNCOVERED_CONTENT | warning | Content lies outside paired sections |
| HTML_NOT_CHECKED | warning | Raw HTML is not compared |
| PARSER_LIMIT_REACHED | warning | Block nesting budget reached; comparison may be incomplete |
| INSTALL_COMMAND_DIFFERENCE | warning | Recognized command sets differ |
| CODE_BLOCK_DIFFERENCE | warning | Code block multisets differ |
| LINK_TARGET_DIFFERENCE | warning | Markdown link/image target sets differ |
| INPUT_ERROR | error | File reading or parsing failed; exit 2 |

<!-- readmetwin:section examples -->
## Try the examples

The consistent pair has translated headings and link labels and reordered code
blocks; it passes strict checking. The inconsistent pair has installation/code
and link differences and an unpaired section; it exits 1.

```sh
readmetwin examples/consistent/README.md examples/consistent/README.zh-CN.md --strict
readmetwin examples/inconsistent/README.md examples/inconsistent/README.zh-CN.md --format json
```

See [consistent example](examples/consistent/README.md) and
[inconsistent example](examples/inconsistent/README.md).

<!-- readmetwin:section development -->
## Development

```sh
python -m pip install -e ".[dev]"
python -m pytest -q
python -m build
python scripts/check_installed.py dist
readmetwin README.md README.zh-CN.md --strict
```

Tests cover consistent, missing, conflicting, false-positive, input-error, and
read-only/offline behavior. CI is configured for all 12 combinations of Python
3.11, 3.12, 3.13, and 3.14 with Ubuntu, Windows, and macOS. Configuration alone
does not establish that those jobs passed; check the repository's Actions tab.
Newer Python versions are not yet in the test matrix. The FIFO test is skipped
where FIFOs are unavailable. Windows reads use binary mode to preserve bytes.
CI also checks this README pair, builds wheel/source distributions, and installs
the wheel in a fresh virtual environment outside the checkout, testing both CLI
entry points, Unicode/space-containing paths, and exit codes. The installation
test downloads dependencies and is developer tooling, separate from the offline
checker. There is no publishing workflow. See [CONTRIBUTING.md](CONTRIBUTING.md).

<!-- readmetwin:section license -->
## License

[MIT](LICENSE). The working name is ReadmeTwin; package-name availability and
release ownership must be checked before any future publication.
