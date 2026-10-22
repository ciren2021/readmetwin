<!-- readmetwin:section overview -->
# ReadmeTwin

[English](README.md) | [简体中文](README.zh-CN.md)

在本地检查 `README.md` 与 `README.zh-CN.md` 中通过显式 ID 配对的章节，
比较安装命令、代码块、Markdown 链接和章节是否缺失。
内容差异仅作为人工核对的警告，绝不据此声称翻译错误。

第一阶段要求 Python 3.11+，仅提供本地命令行工具。不开发网站，不调用 AI API，
不收集遥测，不请求网络，不执行文档内容，也不改写文档。
检查器只读取指定的两个文件：每个必须是最大 2 MiB 的 UTF-8 普通文件，支持 UTF-8 BOM。
安装依赖是开发者单独执行的操作，可能需要联网。

<!-- readmetwin:section installation -->
## 从本地源码安装

本项目尚未发布到 PyPI，请不要只按包名安装。下载源码或克隆 GitHub 仓库后，
进入包含 `pyproject.toml` 的 `readmetwin/` 目录；上层 `outputs/` 不是仓库的一部分。
使用 Python 3.11 或更新版本的解释器。

在 macOS/Linux 上检查 Python 版本并创建虚拟环境：

```sh
python3 --version
python3 -m venv .venv
```

在 macOS/Linux 上激活环境：

```sh
. .venv/bin/activate
```

在 Windows PowerShell 上使用 Python 启动器创建并激活环境：

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

随后安装：

```sh
python -m pip install .
```

如果 PowerShell 阻止激活，可直接使用虚拟环境中的 Python，无需修改执行策略：

```powershell
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m readmetwin README.md README.zh-CN.md --strict
```

后续示例假定已激活虚拟环境。运行 `python --version` 确认版本至少为 3.11。
如果找不到命令行入口，也可以使用 `python -m readmetwin`。

运行时依赖为 [markdown-it-py](https://markdown-it-py.readthedocs.io/en/latest/)
及其依赖 `mdurl`；命令行参数、文件读取、比较和 JSON 输出使用 Python 标准库。

<!-- readmetwin:section usage -->
## 使用方法

不传路径时，检查当前目录下的两个约定文件名：

```sh
readmetwin
readmetwin README.md README.zh-CN.md
python -m readmetwin README.md README.zh-CN.md --strict --format json
```

`--strict` 使警告也导致检查失败。默认格式为 `--format text`；
`--format json` 输出 `schema_version`、`diagnostics`、`summary` 和 `exit_code`。
参数语法错误使用 argparse 的标准 stderr 输出，即使选择 JSON 格式也是如此。
检查过程中发生的输入错误使用所选择的格式报告。

| 退出码 | 含义 |
| --- | --- |
| 0 | 没有结构错误；非严格模式允许存在警告 |
| 1 | 存在结构错误，或严格模式下存在任何警告 |
| 2 | 参数错误，或输入文件无法读取、格式不符合要求 |

每条诊断包含编号、严重程度、文件路径、从 1 开始的行号；适用时还包括章节 ID 和对照位置。
行内内容定位到所在段落的首行，块级内容定位到块的首行；
安装命令定位到围栏代码块内命令所在行。缺失的对照章节定位到另一文档的第 1 行。
报告不输出原始命令、代码和 URL，避免不必要地暴露文档内容。

<!-- readmetwin:section pairing -->
## 使用显式 ID 配对章节

在两份文档中使用相同的 ID，区分大小写。独占一行的标记应紧邻 Markdown 标题之前，
中间允许空行。ID 以 ASCII 字母开头，后续可以包含字母、数字、`.`、`_`、`-`，
总长度不超过 64 个字符。列表或引用块中的标题不能引入配对章节。

````md
<!-- readmetwin:section installation -->
## Installation / 安装

```sh
python -m pip install example-package==1.0
```
````

章节遇到下一个同级或更高级标题时结束。没有标记的子标题继承最近的已标记祖先章节。
有标记的子章节独立拥有其中的内容，不会在父章节重复计算。
每份文档的 ID 必须唯一；重复 ID 会报告错误，并跳过该 ID 的内容比较。

标题翻译和章节排列顺序不影响配对。代码块中的 ID 只是示例，不参与配对。
请为所有需要检查的区域添加 ID，包括开头的介绍；未覆盖内容会产生警告。

<!-- readmetwin:section rules -->
## 比较规则和限制

- **结构：** 缺失、重复、格式无效或未关联标题的 ID 属于错误。
  没有 ID 或存在未覆盖内容时发出覆盖范围警告。没有 ID 时跳过内容比较；
  默认模式带警告退出 0，并不表示文档一致。
- **代码块：** 在每对章节中比较 `(language, content)` 多重集合，支持围栏和缩进代码块。
  忽略围栏风格、代码块顺序、CRLF/LF 换行差异和语言标签大小写。
  保留代码内部空格、注释、空行、语言名称差异和重复代码块数量。
  围栏信息只使用第一个词，忽略其他元数据。
- **安装命令：** 比较 shell/文本代码块和行内代码中识别到的不同命令。
  去除可选的 `$ ` 提示符及首尾空白，合并反斜杠续行。
  支持前缀：`pip install`、带版本号的 `pip`、`python -m pip install`（包括带版本号的 Python）、
  `uv pip install`、`uv add`、`uv sync`、`pipx install`、`poetry install/add`、
  `conda install`、`npm install/i/ci`、`pnpm install/add`、`yarn install/add`、
  `brew/cargo/apt/apt-get install`；允许可选的 `sudo`。
  支持的代码块标签为：空标签、`sh`、`bash`、`zsh`、`shell`、`console`、`shell-session`、
  `text`、`powershell`、`ps1`。不推断其他命令、普通正文、环境变量前缀、任意 shell 语法
  或语义等价关系。命令只作为字符串处理，绝不求值。
  代码块内的命令变化可能同时产生安装命令和代码块两类警告。
- **链接：** 比较已解析 Markdown 链接和图片的不同目标，支持引用式链接和尖括号自动链接。
  忽略显示文字、标题、顺序和重复次数。目标使用 Markdown 解析器的 URL 规范化结果。
  查询参数、片段、相对路径及本地化目标可能存在有意差异，因此仅发出警告。
  不请求 URL，也不检查死链或本地目标文件是否存在。
- **不确定性：** 每项内容差异都要求人工核对。原始 HTML 会产生 `HTML_NOT_CHECKED`，
  不比较其中的链接和代码。解析以 CommonMark 为基准；GFM 表格、MDX、文件包含及未定义的
  引用式链接不属于本阶段支持的语法。该工具不检查翻译质量、代码正确性或安全漏洞，
  不比较自然语言正文，也不证明文档等价。
- **嵌套覆盖范围：** 保留解析器 20 层的块级嵌套预算。引用或列表容器触及预算时，
  产生 `PARSER_LIMIT_REACHED`；每个文件的每个章节 ID（或未配对区域）最多报告一次。
  列表项可能消耗多层预算，因此这不等于标题层级或列表层数。
  部分内容可能被跳过，即使两份文档相同也会在此边界发出警告。
  默认模式在没有错误时仍退出 0，严格模式遇到此警告退出 1。
  字面代码示例内的引用符号不计入嵌套深度。

<!-- readmetwin:section diagnostics -->
## 诊断编号

| 编号 | 级别 | 含义 |
| --- | --- | --- |
| MISSING_SECTION | error | ID 只存在于其中一份文档 |
| DUPLICATE_SECTION_ID | error | ID 重复，配对有歧义 |
| INVALID_SECTION_ID | error | 标记或 ID 格式无效 |
| ORPHAN_SECTION_ID | error | 标记之后没有紧邻标题 |
| NO_SECTION_IDS | warning | 没有配对章节，跳过比较 |
| UNCOVERED_CONTENT | warning | 内容位于配对章节之外 |
| HTML_NOT_CHECKED | warning | 原始 HTML 未参与比较 |
| PARSER_LIMIT_REACHED | warning | 块级嵌套触及预算，比较可能不完整 |
| INSTALL_COMMAND_DIFFERENCE | warning | 已识别安装命令的集合不同 |
| CODE_BLOCK_DIFFERENCE | warning | 代码块多重集合不同 |
| LINK_TARGET_DIFFERENCE | warning | Markdown 链接或图片目标集合不同 |
| INPUT_ERROR | error | 文件读取或解析失败，退出码为 2 |

<!-- readmetwin:section examples -->
## 运行示例

一致样例翻译了标题和链接文字，并调整代码块的顺序，仍能通过严格检查。
不一致样例包含安装命令、代码块、链接差异，以及缺失的配对章节，退出码为 1。

```sh
readmetwin examples/consistent/README.md examples/consistent/README.zh-CN.md --strict
readmetwin examples/inconsistent/README.md examples/inconsistent/README.zh-CN.md --format json
```

参见[一致样例](examples/consistent/README.md)和[不一致样例](examples/inconsistent/README.md)。

<!-- readmetwin:section development -->
## 开发

```sh
python -m pip install -e ".[dev]"
python -m pytest -q
python -m build
python scripts/check_installed.py dist
readmetwin README.md README.zh-CN.md --strict
```

测试覆盖一致、缺失、冲突、误报、输入错误及只读离线行为。
CI 已配置 Python 3.11、3.12、3.13、3.14 与 Ubuntu、Windows、macOS 的全部 12 种组合。
仅完成配置不代表这些任务已经通过，实际结果请查看仓库的 Actions 页面；
更新的 Python 版本尚未纳入测试矩阵。不支持 FIFO 的平台会跳过对应测试。
Windows 使用二进制模式读取文件，以保留原始字节。
CI 同时检查本项目的双语 README、构建 wheel 和源码包，并在源码目录外的独立虚拟环境中
安装 wheel，验证两种 CLI 入口、包含中文和空格的路径及退出码。
安装测试会下载依赖，属于开发工具，与离线检查器本身分开。
没有发布工作流。开发和评审规则请见 [CONTRIBUTING.md](CONTRIBUTING.md)。

<!-- readmetwin:section license -->
## 许可证

[MIT](LICENSE)。项目暂名 ReadmeTwin，未来发布前必须检查包名可用性并确定发布归属。
