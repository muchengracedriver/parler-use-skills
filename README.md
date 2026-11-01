# parler-use-skills

让安装用户的 Codex / AI harness 接入 ParlerTech，并能用自然语言查询自己的用量、会员有效期和请求错误。

> “我最近5小时用了多少？”  
> “7天额度还剩多少，什么时候重置？”  
> “我的会员什么时候到期？最近付款成功了吗？”  
> “账号最近有什么错误？把502错误详情给我。”

Skill会查询该用户本人的账户，解释时间窗口、金额/Token单位和部分失败；不会携带发布者的账号或Key。

## 安装到 Codex

需要 Python 3.10+。安装生图附加 skill 还需要 Codex 的内置 `skill-installer`。

### 通过 npm 安装（推荐）

需要 Node.js 18+ 和 npm。无需克隆 GitHub 仓库，在自己的终端运行：

```bash
npx parler-use-skills@latest install
npx parler-use-skills@latest configure
```

第一条命令安装 skill、生图附加 skill 和本地 MCP；第二条交互式录入本人凭据。下一轮 Codex 对话即可用自然语言查询。首次 `npx` 提示下载时确认包名为 `parler-use-skills`。

自动安装 `custom-imagegen` 和注册 `parler-usage` MCP 的路径仅适用于 **Codex Desktop 和 Codex CLI**。Claude Code、OpenCode、Aider、Cursor、Cline 等其他客户端安装本 skill 时不会安装生图 skill，也不会更改 Codex 配置。

使用 npm 安装到其他客户端时，指定它自己的 skills 目录，并选择 `other`：

```bash
npx parler-use-skills@latest install --client other --dest /path/to/your/client/skills
```

该模式只安装 `parler-use` 本身。其他客户端若需用量 MCP，请按该客户端文档与 [本地接口说明](skills/parler-use/references/usage-api.md) 手动配置；不会自动安装 Codex 专用 MCP。

也可以全局安装，之后直接使用命令：

```bash
npm install -g parler-use-skills
parler-use-skills install
parler-use-skills configure
```

`npm install -g` 本身只安装命令行工具；运行 `parler-use-skills install` 才会配置 Codex。包没有自动执行的安装钩子。

常用命令：

```bash
npx parler-use-skills@latest usage 7d
npx parler-use-skills@latest usage 5h
npx parler-use-skills@latest usage accountStatus --error-page-size 20
npx parler-use-skills@latest usage membership
npx parler-use-skills@latest usage payments
npx parler-use-skills@latest models
npx parler-use-skills@latest image-config
```

`PARLER_PYTHON` 可指定 Python 可执行文件路径。Codex 安装参数仍可使用，例如 `npx parler-use-skills@latest install --dest /path/to/skills --skip-image --skip-mcp`。`--client other` 需要显式传入目标 skills 目录，且不会安装 image skill 或 Codex MCP。

### 从 GitHub 源码安装

仓库为私有时需要 GitHub 访问权限；npm 安装不需要访问源码仓库。有Git访问权限时：

```bash
git clone https://github.com/muchengracedriver/parler-use-skills.git
cd parler-use-skills
python3 install.py
```

也可用GitHub的 **Code → Download ZIP** 下载解压后运行 `python3 install.py`。

安装器会在**运行它的用户机器**上：

1. 安装 `parler-use` 到 `$CODEX_HOME/skills`（默认 `~/.codex/skills`）。
2. 通过内置skill-installer安装 [xixia0523/skills 的 custom-imagegen](https://github.com/xixia0523/skills/tree/a06ff55ab9fe712a069bf0760337de2b400895ed/Custom_Image_Generator_Skill/custom-imagegen)，固定已核对版本；已有生图skill时保留。
3. 有Codex CLI时注册本地 `parler-usage` MCP；无CLI时打印应合并的配置。接口随skill安装，无监听端口、无需额外依赖。

已有不同版本 `parler-use` 时停止，避免覆盖；相同版本可重复运行。可用 `--dest /path/to/skills` 指定skills根目录，或 `--skip-image` / `--skip-mcp` 跳过对应步骤。安装过程中若某一步失败会返回非零状态；修复后可重新运行，已有内容保留。

也支持在Codex中说：

```text
$skill-installer install https://github.com/muchengracedriver/parler-use-skills/tree/main/skills/parler-use
然后按 parler-use/SKILL.md 运行 scripts/install.py，安装生图skill并接入本地MCP。
```

仅复制skill目录不会自动执行安装器。下一轮对话可发现新skill，MCP如未出现则重新加载客户端。

## 录入本人的凭据

在本机交互式终端运行（自定义安装目录时替换实际路径）：

```bash
python3 ~/.codex/skills/parler-use/scripts/parler.py configure
```

输入本人ParlerTech注册邮箱、密码，以及可选的API Key。密码/Key隐藏输入，保存在仓库外的 `~/.config/parler-use/credentials.json`；POSIX权限0600。不要把密码、Key或此配置文件发给AI聊天或上传仓库。用量查询使用邮箱+密码，推理/生图使用API Key。

开启下一轮对话后，直接问用量问题即可；也可以显式说 `$parler-use 查一下我的7d用量和会员到期时间`。未配置凭据时，助手会引导在本机配置。

## 可查询信息

| 问题 | 数据来源 |
| --- | --- |
| 最近滚动5h请求数、Token、实际费用 | 本人请求日志分页汇总，注明完整性 |
| 7d已用金额、额度、剩余和重置 | `rateLimit` |
| 会员状态、付费有效期 | `user.membership` |
| 成功付款记录、金额、币种、时间 | `payments` |
| 账户资料、Key状态与元数据 | `user`、脱敏 `apiKeys` |
| 输入/输出/缓存Token、费用、模型与Endpoint统计、请求明细 | `tokenUsage` |
| 最近24h未恢复错误、状态码、模型、详细错误体与上游错误 | `accountStatus` |

当前远端接口没有上游官方 **5h配额百分比、5h剩余配额或重置时间**；5h结果是日志用量。若分页不完整，助手必须说明结果只是小计。7d金额额度与会员到期、上游配额是不同概念。

`accountStatus` 的 `normal` / `error` / `unavailable` 分别表示无未恢复错误、有错误、无法确认；`truncated` 表示扫描不完整。会员有效期单独读取 `user.membership`，不会从“最近付款”推断仍有效。

## Harness、生图和本地接口说明

- [Codex、Claude Code、OpenCode、Aider配置及生图安装](skills/parler-use/references/harnesses.md)
- [MCP、CLI、全部查询参数、错误语义与分页](skills/parler-use/references/usage-api.md)
- [Skill行为和自然语言映射](skills/parler-use/SKILL.md)

生图skill为安装用户独立配置其本人Key；仓库不替换发布者当前机器的生图配置。使用其他harness时可把完整 `skills/parler-use` 目录安装到该客户端的skill目录，然后按文档接入MCP或CLI；生图附加安装器面向Codex。

```bash
# CLI也可独立使用，不依赖MCP：
python3 skills/parler-use/scripts/parler.py usage 7d
python3 skills/parler-use/scripts/parler.py usage accountStatus --error-page-size 20
python3 skills/parler-use/scripts/parler.py usage membership
```

## 开发验证

```bash
npm test
python3 -m unittest discover -s tests -v
npm pack --dry-run
```

测试使用本地模拟数据和临时目录，不登录真实账户、不修改开发者的Codex配置、不生成图片。接口和客户端格式依据2026-10-31的服务实现与官方文档，版本变化时请重新核对。
# parler-use-skills

让安装用户的 Codex / AI harness 接入 ParlerTech，并能用自然语言查询自己的用量、会员有效期和请求错误。

> “我最近5小时用了多少？”  
> “7天额度还剩多少，什么时候重置？”  
> “我的会员什么时候到期？最近付款成功了吗？”  
> “账号最近有什么错误？把502错误详情给我。”

Skill会查询该用户本人的账户，解释时间窗口、金额/Token单位和部分失败；不会携带发布者的账号或Key。

## 安装到 Codex

需要 Python 3.10+。安装生图附加 skill 还需要 Codex 的内置 `skill-installer`。

### 通过 npm 安装（推荐）

需要 Node.js 18+ 和 npm。无需克隆 GitHub 仓库，在自己的终端运行：

```bash
npx parler-use-skills@latest install
npx parler-use-skills@latest configure
```

第一条命令安装 skill、生图附加 skill 和本地 MCP；第二条交互式录入本人凭据。下一轮 Codex 对话即可用自然语言查询。首次 `npx` 提示下载时确认包名为 `parler-use-skills`。

也可以全局安装，之后直接使用命令：

```bash
npm install -g parler-use-skills
parler-use-skills install
parler-use-skills configure
```

`npm install -g` 本身只安装命令行工具；运行 `parler-use-skills install` 才会配置 Codex。包没有自动执行的安装钩子。

常用命令：

```bash
npx parler-use-skills@latest usage 7d
npx parler-use-skills@latest usage 5h
npx parler-use-skills@latest usage accountStatus --error-page-size 20
npx parler-use-skills@latest usage membership
npx parler-use-skills@latest usage payments
npx parler-use-skills@latest models
npx parler-use-skills@latest image-config
```

`PARLER_PYTHON` 可指定 Python 可执行文件路径。全部安装参数仍可使用，例如 `npx parler-use-skills@latest install --dest /path/to/skills --skip-image --skip-mcp`。

### 从 GitHub 源码安装

仓库为私有时需要 GitHub 访问权限；npm 安装不需要访问源码仓库。有Git访问权限时：

```bash
git clone https://github.com/muchengracedriver/parler-use-skills.git
cd parler-use-skills
python3 install.py
```

也可用GitHub的 **Code → Download ZIP** 下载解压后运行 `python3 install.py`。

安装器会在**运行它的用户机器**上：

1. 安装 `parler-use` 到 `$CODEX_HOME/skills`（默认 `~/.codex/skills`）。
2. 通过内置skill-installer安装 [xixia0523/skills 的 custom-imagegen](https://github.com/xixia0523/skills/tree/a06ff55ab9fe712a069bf0760337de2b400895ed/Custom_Image_Generator_Skill/custom-imagegen)，固定已核对版本；已有生图skill时保留。
3. 有Codex CLI时注册本地 `parler-usage` MCP；无CLI时打印应合并的配置。接口随skill安装，无监听端口、无需额外依赖。

已有不同版本 `parler-use` 时停止，避免覆盖；相同版本可重复运行。可用 `--dest /path/to/skills` 指定skills根目录，或 `--skip-image` / `--skip-mcp` 跳过对应步骤。安装过程中若某一步失败会返回非零状态；修复后可重新运行，已有内容保留。

也支持在Codex中说：

```text
$skill-installer install https://github.com/muchengracedriver/parler-use-skills/tree/main/skills/parler-use
然后按 parler-use/SKILL.md 运行 scripts/install.py，安装生图skill并接入本地MCP。
```

仅复制skill目录不会自动执行安装器。下一轮对话可发现新skill，MCP如未出现则重新加载客户端。

## 录入本人的凭据

在本机交互式终端运行（自定义安装目录时替换实际路径）：

```bash
python3 ~/.codex/skills/parler-use/scripts/parler.py configure
```

输入本人ParlerTech注册邮箱、密码，以及可选的API Key。密码/Key隐藏输入，保存在仓库外的 `~/.config/parler-use/credentials.json`；POSIX权限0600。不要把密码、Key或此配置文件发给AI聊天或上传仓库。用量查询使用邮箱+密码，推理/生图使用API Key。

开启下一轮对话后，直接问用量问题即可；也可以显式说 `$parler-use 查一下我的7d用量和会员到期时间`。未配置凭据时，助手会引导在本机配置。

## 可查询信息

| 问题 | 数据来源 |
| --- | --- |
| 最近滚动5h请求数、Token、实际费用 | 本人请求日志分页汇总，注明完整性 |
| 7d已用金额、额度、剩余和重置 | `rateLimit` |
| 会员状态、付费有效期 | `user.membership` |
| 成功付款记录、金额、币种、时间 | `payments` |
| 账户资料、Key状态与元数据 | `user`、脱敏 `apiKeys` |
| 输入/输出/缓存Token、费用、模型与Endpoint统计、请求明细 | `tokenUsage` |
| 最近24h未恢复错误、状态码、模型、详细错误体与上游错误 | `accountStatus` |

当前远端接口没有上游官方 **5h配额百分比、5h剩余配额或重置时间**；5h结果是日志用量。若分页不完整，助手必须说明结果只是小计。7d金额额度与会员到期、上游配额是不同概念。

`accountStatus` 的 `normal` / `error` / `unavailable` 分别表示无未恢复错误、有错误、无法确认；`truncated` 表示扫描不完整。会员有效期单独读取 `user.membership`，不会从“最近付款”推断仍有效。

## Harness、生图和本地接口说明

- [Codex、Claude Code、OpenCode、Aider配置及生图安装](skills/parler-use/references/harnesses.md)
- [MCP、CLI、全部查询参数、错误语义与分页](skills/parler-use/references/usage-api.md)
- [Skill行为和自然语言映射](skills/parler-use/SKILL.md)

生图skill为安装用户独立配置其本人Key；仓库不替换发布者当前机器的生图配置。使用其他harness时可把完整 `skills/parler-use` 目录安装到该客户端的skill目录，然后按文档接入MCP或CLI；生图附加安装器面向Codex。

```bash
# CLI也可独立使用，不依赖MCP：
python3 skills/parler-use/scripts/parler.py usage 7d
python3 skills/parler-use/scripts/parler.py usage accountStatus --error-page-size 20
python3 skills/parler-use/scripts/parler.py usage membership
```

## 开发验证

```bash
npm test
python3 -m unittest discover -s tests -v
npm pack --dry-run
```

测试使用本地模拟数据和临时目录，不登录真实账户、不修改开发者的Codex配置、不生成图片。接口和客户端格式依据2026-10-31的服务实现与官方文档，版本变化时请重新核对。
