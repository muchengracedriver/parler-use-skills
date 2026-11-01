---
name: parler-use
description: 配置 Codex、Claude Code、OpenCode、Aider 等 AI harness 使用 ParlerTech API，在 Codex Desktop 和 Codex CLI 中安装 custom-imagegen 和本地查询接口。用户自然语言询问自己的 5h/7d 用量、剩余额度、重置时间、会员到期、支付、API Key 状态、Token、缓存、费用或请求错误时，通过此 skill 查询实时数据。
---

# ParlerTech 使用助手

把 `<skill-dir>` 解析为本文件所在目录。每位用户使用自己的 ParlerTech 账户和 Key；不要读取开发者账户或其他工程的凭据。

## 初次安装与配置

仅在目标客户端是 Codex Desktop 或 Codex CLI 时，运行配套安装器：

```bash
python3 <skill-dir>/scripts/install.py
```

这条 Codex 安装路径会通过 Codex 内置 `skill-installer` 安装 [xixia0523/skills 的 custom-imagegen](https://github.com/xixia0523/skills/tree/a06ff55ab9fe712a069bf0760337de2b400895ed/Custom_Image_Generator_Skill/custom-imagegen)，保留已有安装和外部配置，并注册 Codex 本地 MCP。仅复制 `SKILL.md` 不会自动执行安装。

Claude Code、OpenCode、Aider、Cursor、Cline 和其他非 Codex 客户端**不得运行上述 Codex 安装器，不会安装 custom-imagegen，也不会注册 Codex MCP**。用该客户端自带的 skill 安装方式安装 `parler-use` 即可；如使用 npm 安装器，必须指定该客户端的 skills 目录和 `--client other`：

```bash
npx parler-use-skills@latest install --client other --dest /path/to/your/client/skills
```

其他客户端可按 [usage-api.md](references/usage-api.md) 配置本地查询 MCP，或直接使用本 skill 的 CLI。

查询凭据由用户在本机交互式终端输入：

```bash
python3 <skill-dir>/scripts/parler.py configure
```

注册邮箱与密码用于 `https://parlertech.com/site-api/usage`；API Key 用于模型推理和生图，两种认证不可混用。凭据只存于用户本机 `~/.config/parler-use/credentials.json`，或 `PARLER_CONFIG` 指定的路径；POSIX 权限 0600。不要让用户把密码或 Key 发到聊天、命令参数或仓库中。不要把 MCP 参数设计成让模型接收密码。

## 自然语言查询

不要让用户记命令或字段。直接把问题映射到 `parler_usage` MCP 的 `query` 参数；若 MCP 尚未加载，用 CLI 查询同一接口：

```bash
python3 <skill-dir>/scripts/parler.py usage 7d
```

| 用户表达 | query | 解释口径 |
| --- | --- | --- |
| 最近5小时/5h用了多少、花了多少 | `5h` | 滚动5h请求日志汇总的请求数、Token、实际费用；读 `complete` 和 `message` |
| 7天/7d用量、还剩多少、多久重置 | `7d` | `usage7d` / `rateLimit7d` / `remaining7d` 是消费金额与金额额度；读 `reset` 和各 Key 的重置时间 |
| 会员何时到期、订阅状态 | `membership` | `user.membership`；到期边界为 UTC，按用户时区展示 |
| 我的账户信息 | `account` | `user` |
| 付款/订单记录 | `payments` | 支付记录 |
| 我的Key/Key是否可用 | `keys` | 脱敏 Key 元数据，禁止把完整 Key 回显到对话 |
| 请求是否正常、最近为什么失败 | `status` | 最近滚动24h未恢复错误，独立分页 |
| Token、缓存命中、费用、模型/Endpoint统计 | `tokens` | `tokenUsage.stats`，保留服务返回的统计字段 |
| 最近请求、某日期请求明细 | `logs` | `tokenUsage.logs` 和分页 |
| 所有用量/账户概览 | `all` | 全部直接查询字段；只有问到5h时再额外查 `5h` |

执行查询后，用用户的语言报告数值、单位、查询时间、统计窗口和需要注意的服务消息。不要把 HTTP 200、空数组、`matched: false` 或 `configured: false` 解读成用量为零。`remaining7d: null` 表示接口没有可用的有限额度，不能说剩余为零。多 Key 的重置时间可能不同。

5h 是客户端从当前账户日志汇总，最多读取20页，每页50条。`complete: false` 时只能说“已读记录小计/不完整”；`snapshot: false` 表示分页期间仍可能新增记录。**当前 `/site-api/usage` 没有上游官方5h配额、剩余配额或配额百分比，不能用日志金额/7d额度推算它们。** 对“5h配额用了百分之几”明确说明接口暂不提供，可给出5h日志用量。不要编造官方5h重置时间。

`accountStatus.status` 为 `unavailable`、`healthy: null` 或 `truncated: true` 时不得回答“一切正常”。会员状态与请求健康状态分开解释。日期范围只影响 Token；错误窗口固定最近24h。精确参数、部分失败语义及分页用法见 [usage-api.md](references/usage-api.md)。

## Harness 与生图设置

按用户实际使用的 harness 和版本阅读 [harnesses.md](references/harnesses.md)，合并所需 provider 配置，保留原有项目、插件和登录信息。模型 ID 必须来自用户选择或当前 `models` 查询，不把示例模型当成所有用户都可用。不要为接入服务放宽沙箱或关闭审批。

Codex 的生图 skill 是 `custom-imagegen`。仅在用户需要配置生图且没有有效配置时，可在本机运行以下命令，从其个人 ParlerTech 配置导入 Key：

```bash
python3 <skill-dir>/scripts/parler.py image-config
```

生图时加载已安装的 `custom-imagegen/SKILL.md`，按其模型发现、选择和生成流程执行。本 skill 的安装、用量查询和配置检查不会自动生成图片或消费推理额度。
