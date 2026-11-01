# 本地用量接口与账户查询

本地接口为 **stdio MCP 服务**，与命令行共用同一查询实现，Python 3.10+、无第三方依赖，无后台 HTTP 端口。远端固定调用 `POST https://parlertech.com/site-api/usage`，邮箱和密码仅放在 HTTPS JSON body。API Key 不能代替该接口的注册密码。

## 首次配置

在安装用户自己的本机终端中运行（`<skill-dir>` 为其实际安装路径）：

```bash
python3 <skill-dir>/scripts/parler.py configure
```

邮箱使用可见输入，密码和 API Key 使用隐藏输入。API Key 可选，模型配置/生图时才需要。凭据保存在 `~/.config/parler-use/credentials.json`；`PARLER_CONFIG` 可更改位置。POSIX 文件权限为0600，Windows 用户应设置当前用户专属 ACL。也可从用户现有安全环境注入 `PARLER_EMAIL`、`PARLER_PASSWORD`、`PARLER_API_KEY`，环境变量优先；不要把值写入 MCP 配置或命令行。

## MCP 接入

仓库安装器会尝试注册 Codex 的 `parler-usage`，保留同名已有配置。若只用标准 skill-installer 安装了本 skill，还需运行 `scripts/install.py` 才会安装生图 skill 和注册 MCP；skill 文件没有自动执行钩子。

手动注册：

```bash
codex mcp add parler-usage -- python3 /absolute/path/to/parler-use/scripts/parler.py mcp
codex mcp list
```

CLI 不存在时，将以下配置合并到 Codex 的 `config.toml`，Windows 路径使用 TOML 支持的转义或正斜杠：

```toml
[mcp_servers.parler-usage]
command = "python3"
args = ["/absolute/path/to/parler-use/scripts/parler.py", "mcp"]
```

通用 MCP 客户端（例如支持 `mcpServers` 的客户端）配置：

```json
{
  "mcpServers": {
    "parler-usage": {
      "command": "python3",
      "args": ["/absolute/path/to/parler-use/scripts/parler.py", "mcp"]
    }
  }
}
```

不同客户端的顶层配置键可能不同，以客户端版本为准。Claude Code 可用 `claude mcp add --transport stdio --scope user parler-usage -- python3 /absolute/path/to/parler.py mcp`；OpenCode 的本地 MCP 使用 `mcp` 对象、`type: "local"` 和包含命令及参数的 `command` 数组。其他无 MCP 的 harness 直接运行 CLI。重新加载 MCP 或开启下一轮对话后验证 `parler_usage` 可用。

本地工具 `parler_usage` 的参数示例（不接受凭据参数）：

```json
{"query":"7d"}
{"query":"5h"}
{"query":"accountStatus","error_page":2,"error_page_size":10}
{"query":"logs","start_date":"2026-10-01","end_date":"2026-10-31","timezone":"Asia/Shanghai","page":1,"page_size":50}
```

## 完整查询覆盖

| query | 原始字段 | 可回答的问题 |
| --- | --- | --- |
| `all` | 全部字段 | 账户综合概览（不额外扫描5h日志） |
| `account` | `user` | 账户资料、昵称及服务返回的其他资料 |
| `membership` | `user.membership` | 付费会员是否有效、何时到期、`expiresAt` |
| `payments` | `payments` | 成功支付记录、金额、币种、付款日期、服务返回的订单/付款引用 |
| `keys` | `apiKeys` | Key 名称、状态、使用时间等元数据；Key 值脱敏 |
| `7d` | `rateLimit` | `usage7d`、`rateLimit7d`、`remaining7d`、各Key重置时间、`reset` 倒计时 |
| `status` / `accountStatus` | `accountStatus` | 请求健康状态及最近24h未恢复错误 |
| `tokens` / `logs` | `tokenUsage` | 输入/输出/缓存Token、总Token、费用、模型/Endpoint统计、请求明细和分页 |
| `5h` | 客户端计算 | 从本人 `tokenUsage.logs` 汇总最近滚动5h的请求数、Token及实际费用 |

账户会员到期与 API 额度重置是两个不同时间，不能混用。`payments` 仅反映接口返回的付款记录；有付款不代表当前仍有效，判断有效期以 `user.membership.status` 和 `expiresAt` 为准，不从支付日期自行推算。`expiresAt` 为 UTC 边界，展示时应同时给用户时区。空值、`unset` 或未知状态需如实报告。

`rateLimit` 的7d用量与额度单位为美元消费金额；不要标成Token数或上游官方用量百分比。若要计算金额额度使用率，只有 `rateLimit7d > 0` 时计算 `usage7d / rateLimit7d` 并注明“金额额度使用率”。`remaining7d: null` 不是零。多 Key 的每个重置时间均保留。

### accountStatus 错误信息

保留服务返回的所有字段，包括：`configured`、`matched`、`nickname`、`status`、`healthy`、`hours`、`checkedAt`、`errorCount`、`errors`、`pagination`、`truncated`、`message`。错误项可包含时间、Key ID、HTTP状态码、模型、`message`、`errorBody`、`upstreamErrorDetail`、`resolved` 和Endpoint等诊断字段；工具会脱敏已知密码、Key和Bearer凭据。

| 状态 | 解读 |
| --- | --- |
| `normal`, `healthy: true` | 本次完整检查未找到匹配Key在最近24h的未恢复错误 |
| `error`, `healthy: false` | 有未恢复错误；`errorCount` 为总数，`errors` 为当前页 |
| `unavailable`, `healthy: null` | 无法确认；展示服务消息，不当成正常 |
| `truncated: true` | 扫描不完整，错误数量可能只是下界 |

`accountStatus` 只针对与当前账户昵称精确匹配的Key，排除共用上游账户的其他成员。错误窗口固定为 `checkedAt` 之前24h，不受 Token 日期或分页影响。

### 参数与分页

| 参数 | 默认 | 约束 |
| --- | --- | --- |
| `page` | 1 | 请求日志页，1–1000 |
| `page_size` | 10 | 请求日志每页，1–50 |
| `error_page` | 1 | 错误页，1–1000（本地工具限制） |
| `error_page_size` | 10 | 每页错误，1–20 |
| `start_date`, `end_date` | 不传 | 必须成对传入有效 YYYY-MM-DD，开始不晚于结束 |
| `timezone` | 服务默认 | IANA时区，例如 `Asia/Shanghai` 或 `UTC` |

不传日期时，当前服务的Token查询采用 `period=week`；不要把它描述为滚动7天额度窗口。指定日期只影响 `tokenUsage`。页码各自独立，不默认拉取所有付款/Token/错误之外的其他接口。

5h查询固定采用UTC日期范围覆盖整个滚动窗口，逐条比较带时区时间戳，跨午夜仍有效；最多20页/1000条。去除分页重复记录；分页不足、时间缺失、未匹配或部分服务不可用均令 `complete: false`。工具不提供官方5h配额上限、剩余额度、百分比或配额重置；这些字段为 `null`。滚动日志是动态查询而非事务快照。

## 命令行与验证

```bash
python3 <skill-dir>/scripts/parler.py usage 5h
python3 <skill-dir>/scripts/parler.py usage 7d
python3 <skill-dir>/scripts/parler.py usage membership
python3 <skill-dir>/scripts/parler.py usage payments
python3 <skill-dir>/scripts/parler.py usage accountStatus --error-page 2 --error-page-size 10
python3 <skill-dir>/scripts/parler.py usage tokens --start-date 2026-10-01 --end-date 2026-10-31 --timezone Asia/Shanghai
```

安装与离线测试不调用真实用户账户。首次真实查询必须使用安装用户本人的凭据。HTTP400检查日期及分页；401检查注册邮箱/密码（不是API Key）；403检查权限；429稍后重试。HTTP200也可能包含 `configured: false`、`matched: false`、服务错误消息或部分失败，按字段解释。查询只读账户业务信息，但远端会更新最后登录时间。

接口依据：ParlerTech `/usage` 文档及 `parlertechWebPages/server/index.mjs` 的 `scriptUsageLookup`、`publicSub2apiRateLimit`、`tokenUsageOptionsFromBody`、`publicSub2apiUsageLog`（2026-10-31核对）。[在线接口说明](https://parlertech.com/usage)。[Codex MCP 官方文档](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。
