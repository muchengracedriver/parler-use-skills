# 配置 AI Harness 使用 ParlerTech

统一推理主机 `https://api.parlertech.com`。Codex 的 Responses provider 使用此根地址；OpenAI SDK兼容客户端通常填 `https://api.parlertech.com/v1`；Claude Code 的 Anthropic网关填根地址，由客户端追加 `/v1/messages`。账户查询则使用 `https://parlertech.com/site-api/usage`，不是推理主机。

不同套餐、Key分组和模型可能只支持部分协议。先使用用户自己的 API Key 查询当前模型，不把任意 GPT、Claude 或图片模型写成保证可用：

```bash
python3 <skill-dir>/scripts/parler.py configure
python3 <skill-dir>/scripts/parler.py models
```

下文 `<MODEL_ID>` 替换为服务返回且用户选中的模型。合并已有配置，不整文件覆盖。API Key存于本机私有凭据文件或已有安全环境；下面的 `run` 命令只向子进程注入它，不在参数中传递Key。

## Codex CLI / IDE / Desktop

在 `$CODEX_HOME/config.toml`（默认 `~/.codex/config.toml`；Windows `%USERPROFILE%\.codex\config.toml`）合并：

```toml
[model_providers.parlertech]
name = "ParlerTech"
base_url = "https://api.parlertech.com"
env_key = "PARLER_API_KEY"
wire_api = "responses"
requires_openai_auth = false

[profiles.parlertech]
model_provider = "parlertech"
model = "<MODEL_ID>"
```

启动 CLI：

```bash
python3 <skill-dir>/scripts/parler.py run codex -- -p parlertech
```

若用户明确希望默认使用ParlerTech，可将 `model_provider = "parlertech"`、`model = "<MODEL_ID>"` 作为配置文件**根层字段**合并，保留 provider 表；不要误写到前一个表里。`model_reasoning_effort` 仅在模型支持时添加，不默认打开WebSocket、不改审批或沙箱设置。

IDE/桌面进程也必须能读取 `PARLER_API_KEY`；终端中的环境变量不一定被图形应用继承。本工具的 `run` 保证CLI子进程获得凭据，不会自动给已运行的桌面进程设置环境。桌面/IDE按其版本支持的provider与环境设置配置，重启并检查实际选中模型；不要声称仅编辑TOML就已完成连接，也不要覆盖 `auth.json` 或注销原登录。`models`只验证Key和模型列表，不能代替一次真实推理验证；实际推理可能计费，应在用户要开始使用时进行。

来源：[Codex 配置参考](https://learn.chatgpt.com/docs/config-file/config-reference) 与 ParlerTech账户页示例。这里采用独立provider和环境Key，避免把第三方Key写成OpenAI登录。

## Claude Code CLI

确认用户的Key分组支持Anthropic Messages协议，并选用该分组允许的模型：

```bash
python3 <skill-dir>/scripts/parler.py run claude -- --model "<MODEL_ID>"
```

包装器给子进程设置 `ANTHROPIC_BASE_URL=https://api.parlertech.com` 和 `ANTHROPIC_AUTH_TOKEN`，移除子进程中冲突的 `ANTHROPIC_API_KEY`。若账户网关要求不同认证头，按服务实际要求调整。进入CLI后用 `/status` 核对base URL、凭据来源及模型。不要把只有Responses协议的Key直接用于Messages客户端。

Claude Desktop 的第三方推理设置与CLI不同；不能假定其读取上述环境变量。按桌面版本的第三方网关设置填写主机、认证方案及本人Key。

来源：[Claude Code 网关连接](https://code.claude.com/docs/en/llm-gateway-connect)。

## OpenCode

先运行 `opencode --version`，配置格式按主版本区分。以下示例选择Responses协议；若模型仅支持Chat Completions，v1用 `@ai-sdk/openai-compatible`，v2选择对应兼容provider。

OpenCode v1 的 `~/.config/opencode/opencode.json`：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "parlertech/<MODEL_ID>",
  "provider": {
    "parlertech": {
      "npm": "@ai-sdk/openai",
      "name": "ParlerTech",
      "options": {
        "baseURL": "https://api.parlertech.com/v1",
        "apiKey": "{env:PARLER_API_KEY}"
      },
      "models": {"<MODEL_ID>": {"name": "<MODEL_ID>"}}
    }
  }
}
```

OpenCode v2 使用 `providers` / `package` / `settings`（不要直接套用v1字段）：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "parlertech/coder",
  "providers": {
    "parlertech": {
      "env": ["PARLER_API_KEY"],
      "package": "@opencode/ai/providers/openai-compatible",
      "settings": {
        "baseURL": "https://api.parlertech.com/v1",
        "apiKey": "{env:PARLER_API_KEY}"
      },
      "models": {"coder": {"modelID": "<MODEL_ID>"}}
    }
  }
}
```

v2兼容provider须匹配服务器实际支持的协议；若当前版本/模型不能走Responses，用该版本官方OpenAI provider配置，或选择允许Chat Completions的模型。不要凭空声明上下文上限或工具能力。

```bash
python3 <skill-dir>/scripts/parler.py run opencode
```

来源：[OpenCode v1 providers](https://opencode.ai/docs/providers)、[v2 providers](https://opencode.ai/v2/docs/providers)。

## Aider，以及 Cursor / Cline 等编辑器客户端

确认模型和Key支持Chat Completions后，Aider可运行：

```bash
python3 <skill-dir>/scripts/parler.py run aider -- --model "openai/<MODEL_ID>"
```

包装器设置 `OPENAI_API_KEY` 和 `OPENAI_API_BASE=https://api.parlertech.com/v1`。不要把Responses-only模型用于只支持Chat Completions的客户端。

编辑器中选择其版本提供的OpenAI-compatible自定义provider，填写Base URL `https://api.parlertech.com/v1`、本人Key和真实模型ID；如支持Responses协议则选对应模式。Key在编辑器本机安全输入，不写进项目共享settings或聊天。配置项随版本变化，缺少自定义URL或对应协议时需按客户端官方文档确认支持范围。

来源：[Aider OpenAI-compatible APIs](https://aider.chat/docs/llms/openai-compat.html)。

## 为 Codex 用户安装和配置生图

安装器固定从用户指定仓库安装：

- 仓库：`xixia0523/skills`
- 路径：`Custom_Image_Generator_Skill/custom-imagegen`
- 经核对版本：`a06ff55ab9fe712a069bf0760337de2b400895ed`

已有 `custom-imagegen` 时保留，不自行删除、改名或覆盖。内置skill-installer不存在时，安装器会报告未完成并给出标准Codex安装入口，不偷偷运行替代下载脚本。后续更新可核对上游新提交后修改固定版本；不要使用已经被上游移除的旧ZIP链接。

在**接收安装的用户机器**完成配置：

```bash
python3 <skills-root>/custom-imagegen/scripts/image_gen.py check
# 仅当缺少有效配置、用户希望使用其本人的 ParlerTech Key 时：
python3 <skill-dir>/scripts/parler.py image-config --skills-dir <skills-root>
python3 <skills-root>/custom-imagegen/scripts/image_gen.py check
```

默认外部配置路径为 `~/.config/custom-imagegen/.env`，`AI_BASE_URL=https://api.parlertech.com/v1`。每位用户独立配置，不包含发布者的Key。`check`只检查配置；实际生图遵循上游skill的模型发现与用户选择流程。安装器不会自动生图。

以上配置于2026-10-31核对。遇到新版客户端，先查对应官方文档，再做局部合并。
