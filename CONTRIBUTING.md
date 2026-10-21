# Contributing / 贡献指南

ReadmeTwin is a Python 3.11+ local CLI. Keep changes focused and dependency-light.
本项目仅提供本地命令行检查；请保持改动范围明确、依赖精简。

## Development / 开发

From the project root, create and activate a virtual environment as shown in
either README, then run / 按 README 创建并激活虚拟环境后运行：

```sh
python -m pip install -e ".[dev]"
python -m pytest -q
readmetwin README.md README.zh-CN.md --strict
python -m build
python scripts/check_installed.py dist
```

Run the relevant test first, then the full suite before proposing a change.
CI is configured for Python 3.11–3.14 on Ubuntu, Windows, and macOS (12 jobs).
Each job installs the package, runs pytest and README checks, builds distributions,
and tests the wheel in a fresh environment outside the checkout. The install
smoke test may download dependencies; it does not run any README commands.
No lint/type-check tool is currently configured; do not claim those checks ran.
先运行相关测试，再于提交改动供评审前运行全量测试。CI 已配置三平台、四版本共 12 组任务，
包含独立环境下的安装验证；实际是否通过以 Actions 结果为准。安装测试可能下载依赖，
但不运行文档中的任何命令。当前没有配置 lint 或类型检查工具。

## Design constraints / 设计约束

- Pair sections only by explicit IDs; never guess from translated titles.
  仅使用显式 ID 配对，不猜测翻译后的标题。
- Keep uncertain differences as warnings. Do not describe them as translation
  mistakes. Document normalization and unsupported syntax with regression tests.
  不确定的差异仅作警告；规范化规则和不支持的语法需要文档及回归测试。
- Never execute README content, follow URLs, upload files, rewrite documents,
  or introduce paid AI APIs. Keep the checker offline and read-only.
  禁止执行文档内容、访问链接、上传文件、改写文档或引入付费 AI API。
- Update both READMEs with matching IDs and equivalent commands/examples.
  更新两份 README，并保持 ID、命令和示例对应。

## Tests and reports / 测试及问题报告

Include a small pair of sanitized Markdown snippets, expected behavior, actual
diagnostic codes, Python version, and OS. Add tests for consistent, missing,
conflicting, and intentional differences when changing comparison behavior.
Do not include private READMEs, credentials, or secret URLs in a public report.
报告中提供脱敏后的最小双语片段、预期行为、实际诊断编号及 Python/系统版本；不要包含隐私信息。

The CLI tests invoke fixed commands for the project itself. They never run shell
or Python text extracted from Markdown. The safety test rejects process/network
calls during checking and verifies unchanged input bytes.
CLI 测试只调用固定的项目入口，不运行文档中的 shell/Python 内容。

## Review and release / 评审和发布

Explain the problem, the smallest change, and tests actually run. Submit changes
for review through the host repository when one exists; this source tree does
not invent an upstream repository URL.
说明问题、最小修改及实际运行的测试；仓库创建后再使用其评审流程。

Commit, push, package publication, and release creation require the maintainer's
explicit confirmation. GitHub Actions only tests/builds; it never publishes.
Before a first release, confirm package-name availability, ownership, version,
license attribution, and release contents. Contributions are under the MIT
License in LICENSE.
提交、推送、发布软件包或创建版本前，需要维护者明确确认。GitHub Actions 只测试和构建，
不会发布。首次发布前确认包名、归属、版本、版权信息及发行内容；贡献适用 MIT 许可证。
