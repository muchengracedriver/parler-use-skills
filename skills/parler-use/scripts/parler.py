#!/usr/bin/env python3
"""ParlerTech usage CLI and local stdio MCP server. Python 3.10+, stdlib only."""
import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import getpass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

USAGE_URL = "https://parlertech.com/site-api/usage"
API_URL = "https://api.parlertech.com"
QUERIES = ("all", "account", "membership", "payments", "keys", "7d", "5h", "status", "accountStatus", "tokens", "logs")
INTEGER_OPTIONS = {"page": (1, 1000), "page_size": (1, 50), "error_page": (1, 1000), "error_page_size": (1, 20)}


class ParlerError(Exception):
    pass


def config_path():
    return Path(os.environ.get("PARLER_CONFIG", "~/.config/parler-use/credentials.json")).expanduser()


def load_config():
    path = config_path()
    if path.is_file():
        if os.name != "nt" and path.stat().st_mode & 0o077:
            raise ParlerError("凭据文件权限过宽；请在本机将其权限设为 0600。")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise ParlerError("无法读取本地凭据文件，请重新运行 configure。") from exc
        if not isinstance(data, dict):
            raise ParlerError("凭据文件必须是 JSON 对象。")
    else:
        data = {}
    for field, env in (("email", "PARLER_EMAIL"), ("password", "PARLER_PASSWORD"), ("api_key", "PARLER_API_KEY")):
        if os.environ.get(env):
            data[field] = os.environ[env]
    return data


def configure():
    if not sys.stdin.isatty():
        raise ParlerError("请在本机交互式终端运行 configure；不要在聊天中提供密码或 Key。")
    data = load_config()
    email = input("ParlerTech 注册邮箱（留空保留已有值）: ").strip()
    password = getpass.getpass("ParlerTech 密码（留空保留已有值）: ")
    api_key = getpass.getpass("ParlerTech API Key（可选，留空保留；用于模型/生图配置）: ")
    data.update({k: v for k, v in (("email", email), ("password", password), ("api_key", api_key)) if v})
    if not any(data.get(k) for k in ("email", "api_key")):
        raise ParlerError("至少配置账户或 API Key。查询用量需要邮箱与密码。")
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".parler-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f"已保存到 {path}；查询密码与 API Key 不会输出。")
    if os.name == "nt":
        print("Windows 请使用当前用户专属目录，并检查该文件的 ACL。")


def validate_options(options):
    if not isinstance(options, dict):
        raise ParlerError("查询参数必须是对象。")
    allowed = set(INTEGER_OPTIONS) | {"start_date", "end_date", "timezone"}
    if set(options) - allowed:
        raise ParlerError("存在不支持的查询参数。")
    for name, (minimum, maximum) in INTEGER_OPTIONS.items():
        if name in options and (type(options[name]) is not int or not minimum <= options[name] <= maximum):
            raise ParlerError(f"{name} 必须是 {minimum}..{maximum} 的整数。")
    start, end = options.get("start_date"), options.get("end_date")
    if bool(start) != bool(end):
        raise ParlerError("start_date 和 end_date 需要成对提供。")
    if start:
        try:
            if not all(isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) for v in (start, end)):
                raise ValueError()
            if date.fromisoformat(start) > date.fromisoformat(end):
                raise ValueError()
        except ValueError as exc:
            raise ParlerError("日期需为有效 YYYY-MM-DD，且开始日期不能晚于结束日期。") from exc
    if "timezone" in options:
        try:
            ZoneInfo(options["timezone"])
        except (TypeError, ValueError, ZoneInfoNotFoundError) as exc:
            raise ParlerError("timezone 需为 IANA 时区，例如 Asia/Shanghai 或 UTC。") from exc
    return dict(options)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ParlerError("服务发生重定向；为保护凭据，本次请求已停止。")


def request_json(url, payload=None, api_key=None):
    headers = {"Accept": "application/json", "User-Agent": "parler-use-skills/1.0"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode()
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    request = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=60) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        hints = {400: "参数无效", 401: "邮箱/密码或 API Key 不正确", 403: "无权限", 429: "请求过多，请稍后重试"}
        raise ParlerError(f"ParlerTech HTTP {exc.code}：{hints.get(exc.code, '服务暂不可用')}。") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ParlerError("无法连接 ParlerTech，请检查网络后重试。") from exc
    except ValueError as exc:
        raise ParlerError("服务未返回有效 JSON。") from exc
    if not isinstance(data, dict):
        raise ParlerError("服务返回格式异常。")
    return data


def fetch_usage(options):
    options = validate_options(options)
    credentials = load_config()
    if not credentials.get("email") or not credentials.get("password"):
        raise ParlerError("查询用量需要 ParlerTech 注册邮箱和密码。请在本机运行 configure。")
    data = request_json(USAGE_URL, {**options, "email": credentials["email"], "password": credentials["password"]})
    if data.get("ok") is not True:
        raise ParlerError("ParlerTech 未确认查询成功。")
    return data


def redact(value, secrets=()):
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if re.sub(r"[^a-z]", "", k.lower()) in
                {"key", "apikey", "password", "authorization", "accesstoken", "refreshtoken", "secret"}
                else redact(v, secrets)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
        value = re.sub(r"\bsk-[A-Za-z0-9_-]+", "[REDACTED]", value)
        return re.sub(r"(?i)Bearer\s+[^\s\"'<>]+", "Bearer [REDACTED]", value)
    return value


def parse_timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (AttributeError, TypeError, ValueError):
        return None


def rolling_five_hours(fetch=fetch_usage, now=None, max_pages=20):
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(hours=5)
    options = {"start_date": start.date().isoformat(), "end_date": now.date().isoformat(), "timezone": "UTC", "page_size": 50}
    rows, seen, complete, message = [], set(), False, ""
    checked_pages = 0
    for page in range(1, max_pages + 1):
        usage = fetch({**options, "page": page}).get("tokenUsage")
        if not isinstance(usage, dict) or not usage.get("configured") or not usage.get("matched") or usage.get("message"):
            message = (usage or {}).get("message") or "用量服务未配置、未匹配账户或暂不可用。"
            break
        checked_pages = page
        logs, pagination = usage.get("logs"), usage.get("pagination") or {}
        if not isinstance(logs, list) or not isinstance(pagination.get("totalPages"), int):
            message = "请求记录或分页信息不完整。"
            break
        for row in logs:
            # Deduplicate overlapping pages; live usage is not an atomic snapshot.
            identity = (row.get("id"), row.get("apiKeyId"), row.get("requestId"))
            if not identity[0] and not identity[2]:
                message = "部分请求缺少唯一标识；无法确认完整性。"
                continue
            if identity not in seen:
                seen.add(identity)
                rows.append(row)
        if page >= pagination["totalPages"]:
            complete = len(seen) >= pagination.get("total", len(seen)) and not message
            break
        if not logs:
            message = "分页尚未结束但没有返回记录。"
            break
    missing_time = any(parse_timestamp(row.get("createdAt")) is None for row in rows)
    selected = [row for row in rows if (stamp := parse_timestamp(row.get("createdAt"))) and start <= stamp <= now]
    def total(field):
        try:
            return sum((Decimal(str(row.get(field, 0))) for row in selected), Decimal(0))
        except InvalidOperation as exc:
            raise ParlerError("用量记录包含无效数值。") from exc
    return {"period": "rolling-5h", "source": "tokenUsage.logs", "windowStart": start.isoformat(),
            "checkedAt": now.isoformat(), "complete": complete and not missing_time,
            "snapshot": False, "pagesFetched": checked_pages, "requests": len(selected),
            "totalTokens": int(total("totalTokens")), "actualCostUSD": float(total("actualCost")),
            "quotaLimit": None, "quotaRemaining": None, "quotaUsedPercent": None,
            "message": message or ("日志分页未全部读取或时间缺失，结果仅为已读记录小计。" if not complete or missing_time else
            "按实时日志汇总；不是事务快照。接口未提供官方 5h 配额、剩余量或配额百分比。")}


def query_usage(query="all", options=None, fetch=fetch_usage):
    if query not in QUERIES:
        raise ParlerError("不支持的查询类型。")
    options = validate_options(options or {})
    if query == "5h":
        if options:
            raise ParlerError("5h 使用固定滚动窗口，不接受日期或分页参数。")
        return rolling_five_hours(fetch)
    data = fetch(options)
    if query == "all":
        return data
    if query == "membership":
        return {"membership": (data.get("user") or {}).get("membership")}
    field = {"account": "user", "7d": "rateLimit", "status": "accountStatus", "accountStatus": "accountStatus", "tokens": "tokenUsage", "logs": "tokenUsage", "keys": "apiKeys", "payments": "payments"}[query]
    return {field: data.get(field)}


def safe_query(query, options):
    result = query_usage(query, options)
    config = load_config()
    return redact(result, (config.get("password"), config.get("api_key")))


PROPERTIES = {name: {"type": "integer", "minimum": low, "maximum": high} for name, (low, high) in INTEGER_OPTIONS.items()}
PROPERTIES.update({name: {"type": "string"} for name in ("start_date", "end_date", "timezone")})
TOOL = {"name": "parler_usage", "description": "查询用户自己的 ParlerTech 5h 日志用量、7d 额度与重置、会员到期、支付、Key 元数据、Token/缓存/费用/日志及近24h错误。5h不含官方配额百分比；密钥已脱敏。",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "enum": list(QUERIES)}, **PROPERTIES}, "required": ["query"], "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": True}}


def handle_rpc(message):
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}
    if "id" not in message:
        return None
    result, method, params = {}, message["method"], message.get("params") or {}
    response = {"jsonrpc": "2.0", "id": message["id"]}
    if not isinstance(params, dict):
        return {**response, "error": {"code": -32602, "message": "Invalid params"}}
    if method == "initialize":
        supported = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
        requested = params.get("protocolVersion")
        result = {"protocolVersion": requested if requested in supported else supported[-1], "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "parler-usage", "version": "1.0.0"}}
    elif method == "ping":
        pass
    elif method == "tools/list":
        result = {"tools": [TOOL]}
    elif method == "tools/call":
        arguments = params.get("arguments") or {}
        try:
            if params.get("name") != TOOL["name"] or not isinstance(arguments, dict):
                raise ParlerError("未知工具或参数格式不正确。")
            query = arguments.get("query", "all")
            result = {"content": [{"type": "text", "text": json.dumps(safe_query(query, {k: v for k, v in arguments.items() if k != "query"}), ensure_ascii=False)}], "isError": False}
        except (ParlerError, OSError) as exc:
            text = str(exc) if isinstance(exc, ParlerError) else "无法访问本地凭据文件；请检查权限。"
            result = {"content": [{"type": "text", "text": text}], "isError": True}
    else:
        return {**response, "error": {"code": -32601, "message": "Method not found"}}
    return {**response, "result": result}


def serve_mcp():
    # MCP stdio uses newline-delimited JSON; stdout is protocol-only.
    for line in sys.stdin:
        try:
            response = handle_rpc(json.loads(line))
        except ValueError:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


def require_key():
    key = load_config().get("api_key")
    if not key:
        raise ParlerError("请先在本机 configure 中设置 API Key，或设置 PARLER_API_KEY 环境变量。")
    return key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("configure", help="在本机安全录入账户凭据和可选 API Key")
    sub.add_parser("mcp", help="启动本地 stdio MCP 服务")
    sub.add_parser("models", help="使用 API Key 查询当前可用模型")
    image = sub.add_parser("image-config", help="为已安装的 custom-imagegen 导入 ParlerTech API Key")
    image.add_argument("--skills-dir", type=Path, default=Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser() / "skills")
    usage = sub.add_parser("usage", help="查询自己的用量")
    usage.add_argument("query", choices=QUERIES, nargs="?", default="all")
    for name in PROPERTIES:
        usage.add_argument("--" + name.replace("_", "-"), type=int if name in INTEGER_OPTIONS else str)
    run = sub.add_parser("run", help="向 harness 子进程注入本地 API Key")
    run.add_argument("harness", choices=("codex", "claude", "opencode", "aider"))
    run.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.command == "configure":
            configure()
        elif args.command == "mcp":
            serve_mcp()
        elif args.command == "usage":
            options = {name: getattr(args, name) for name in PROPERTIES if getattr(args, name) is not None}
            print(json.dumps(safe_query(args.query, options), indent=2, ensure_ascii=False))
        elif args.command == "models":
            data = request_json(API_URL + "/v1/models", api_key=require_key())
            print(json.dumps({"models": [item["id"] for item in data.get("data", []) if isinstance(item, dict) and "id" in item]}, indent=2))
        elif args.command == "image-config":
            script = args.skills_dir.expanduser() / "custom-imagegen/scripts/image_gen.py"
            if not script.is_file():
                raise ParlerError("custom-imagegen 尚未安装。请运行安装器。")
            env = {**os.environ, "PARLER_IMAGE_SETUP_KEY": require_key()}
            result = subprocess.run([sys.executable, str(script), "configure", "--base-url", API_URL + "/v1", "--api-key-env", "PARLER_IMAGE_SETUP_KEY"], env=env)
            if result.returncode:
                raise ParlerError("生图配置未完成；请查看 custom-imagegen 提示。")
        else:
            env = {**os.environ, "PARLER_API_KEY": require_key()}
            if args.harness == "claude":
                env.update(ANTHROPIC_BASE_URL=API_URL, ANTHROPIC_AUTH_TOKEN=env["PARLER_API_KEY"])
                env.pop("ANTHROPIC_API_KEY", None)
            else:
                env.update(OPENAI_API_KEY=env["PARLER_API_KEY"], OPENAI_BASE_URL=API_URL + "/v1", OPENAI_API_BASE=API_URL + "/v1")
            forwarded = args.args[1:] if args.args[:1] == ["--"] else args.args
            return subprocess.run([args.harness, *forwarded], env=env).returncode
    except ParlerError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except OSError:
        print("本地文件或命令无法访问，请检查权限和 harness 是否安装。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
