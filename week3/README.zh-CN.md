# 第 3 周 — Open-Meteo 天气 MCP 服务器（STDIO + 可选 HTTP）

[English](README.md) | 中文

这是一个小型 MCP 服务器，封装了免费、无需 API Key 的 [Open-Meteo](https://open-meteo.com/) 接口，对外提供两个工具：

| 工具 | 上游接口 |
| --- | --- |
| `geocode_city(city: str)` | `GET https://geocoding-api.open-meteo.com/v1/search` |
| `get_current_weather(latitude: float, longitude: float)` | `GET https://api.open-meteo.com/v1/forecast?current=temperature_2m,weather_code` |

默认传输为 **STDIO**（stdout = JSON-RPC，日志写到 **stderr**）。可选 **HTTP** 传输使用 mcp 1.30 的 `streamable-http`（路径 `/mcp`）或 `sse`。Open-Meteo 本身不需要 API Key；可选的 `MCP_API_KEY` 仅用于保护 MCP 的 HTTP 端点。

```
week3/
├── README.md
├── README.zh-CN.md
└── server/
    ├── main.py           # FastMCP 服务器、工具、stderr 日志、STDIO + HTTP 入口
    ├── weather.py        # Open-Meteo HTTP 客户端：重试/退避、超时、错误映射
    └── requirements.txt
```

## 环境要求

- Python **>= 3.10**（`mcp` SDK 要求）
- 能访问 `*.open-meteo.com` 的 HTTPS 出网

## 当前部署方式：Cursor 在宿主机，服务器在容器内

宿主机的系统 Python 版本过低，所以服务器运行在 `cs146s-dev` 容器中（`continuumio/miniconda3`，Python 3.14）。宿主机目录 `~/workspace/cs146s` 挂载到容器的 `/workspace`。Cursor 运行在宿主机上，用 `docker exec -i` 启动服务器。`docker exec` 会透传 stdin 和 stdout，所以 STDIO 传输无需改动。

虚拟环境放在**容器内**的 `/opt/venvs/week3-mcp`，而不是挂载的仓库目录中，避免在工作区留下 root 所有的文件。容器重建后需要重新执行安装步骤。

### 安装（在宿主机执行一次）

```bash
docker exec cs146s-dev sh -c '
  python3 -m venv /opt/venvs/week3-mcp &&
  /opt/venvs/week3-mcp/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r /workspace/modern-software-dev-assignments/week3/server/requirements.txt'
```

`-i` 指定的镜像是可选的。这里使用它是因为容器访问 `files.pythonhosted.org` 很慢。

### 运行

```bash
docker exec -i -e PYTHONDONTWRITEBYTECODE=1 cs146s-dev \
  /opt/venvs/week3-mcp/bin/python /workspace/modern-software-dev-assignments/week3/server/main.py
```

启动后进程会等待 stdin 上的 MCP JSON-RPC 消息。通常由 MCP 客户端（Cursor、Claude Desktop、MCP Inspector）自动启动。`-i` 必须加，否则 stdin 不会接入。`PYTHONDONTWRITEBYTECODE=1` 防止在挂载的仓库中生成 root 所有的 `__pycache__/`。

### 不使用容器的本地方式

```bash
cd week3
python3 -m venv .venv && source .venv/bin/activate   # Python >= 3.10
pip install -r server/requirements.txt
python server/main.py
```

### 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `TRANSPORT` | `stdio` | `stdio`（默认，Cursor docker exec）、`http` / `streamable-http`（在 `/mcp` 上使用 streamable-http），或 `sse` |
| `HOST` | `0.0.0.0` | HTTP/SSE 绑定地址（STDIO 时忽略） |
| `PORT` | `8765` | HTTP/SSE 绑定端口（容器已发布 `8765:8765`） |
| `MCP_API_KEY` | （未设置） | 若设置，HTTP/SSE 需要 `Authorization: Bearer <key>` 或 `x-api-key: <key>`。未设置则无鉴权。绝不会转发给 Open-Meteo。本地演示示例（勿用于生产）：`mcp_f3bbd13d122f0febabca92495ce7bdc2`。 |
| `LOG_LEVEL` | `INFO` | 写到 stderr 的 Python 日志级别（`DEBUG`、`INFO`、`WARNING` 等） |
| `OPEN_METEO_TIMEOUT` | `10` | 单次请求超时时间（秒） |
| `HTTPS_PROXY` / `ALL_PROXY` / `NO_PROXY` | （继承） | 标准代理变量，httpx 会自动读取。代理异常时可设置 `NO_PROXY=*` 绕过 |


## HTTP 传输（可选 / 加分项）

STDIO 仍是 Cursor 与本服务器通信的主要方式（`docker exec -i`）。HTTP 面向远程 MCP 客户端或 agent。

选用的传输：**streamable-http**（mcp 1.30 官方传输：`transport="streamable-http"`，默认路径 `/mcp`）。也支持 `TRANSPORT=sse`（`/sse` + `/messages/`）。

### 在容器内启动

未鉴权（`MCP_API_KEY` 未设置时的默认行为）：

```bash
docker exec -d   -e PYTHONDONTWRITEBYTECODE=1   -e TRANSPORT=http   -e HOST=0.0.0.0   -e PORT=8765   -e LOG_LEVEL=INFO   cs146s-dev   /opt/venvs/week3-mcp/bin/python /workspace/modern-software-dev-assignments/week3/server/main.py
```

带可选 API Key（仅保护 MCP 端点；Open-Meteo 仍无需 Key）：

```bash
docker exec -d   -e PYTHONDONTWRITEBYTECODE=1   -e TRANSPORT=http   -e HOST=0.0.0.0   -e PORT=8765   -e MCP_API_KEY='mcp_f3bbd13d122f0febabca92495ce7bdc2'   cs146s-dev   /opt/venvs/week3-mcp/bin/python /workspace/modern-software-dev-assignments/week3/server/main.py
```

前台运行（日志在 stderr）：去掉 `-d`，如需交互可再加 `-i`。

端口 `8765` 已在 `cs146s-dev` 上发布（`0.0.0.0:8765->8765/tcp`）。

### Curl / 自检（streamable-http initialize）

```bash
# 在宿主机（或能访问已发布端口的任意机器）上：
curl -sS -D - -o /tmp/mcp-init.body -X POST "http://127.0.0.1:8765/mcp"   -H "Content-Type: application/json"   -H "Accept: application/json, text/event-stream"   -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl-check","version":"0"}}}'
# 预期 HTTP 200，以及 JSON-RPC initialize 结果（或 SSE 帧格式结果）。
# 若设置了 MCP_API_KEY，请加上： -H "Authorization: Bearer mcp_f3bbd13d122f0febabca92495ce7bdc2"
# Key 缺失或错误 -> HTTP 401。
```

确认进程在监听，然后停止测试服务器：

```bash
docker exec cs146s-dev sh -c 'ss -ltnp | grep 8765 || netstat -ltnp 2>/dev/null | grep 8765'
docker exec cs146s-dev pkill -f "week3/server/main.py" || true
```

### Cursor `mcp.json`（HTTP）

**仅 STDIO**、**仅 HTTP**、以及**两者同时配置**的完整 Cursor 写法见下文 [Cursor 配置](#cursor-配置)。提醒：启用 HTTP 条目前请先启动 HTTP 服务器；若监听未运行，请改用 STDIO。

### 鉴权说明

- 官方 FastMCP 1.30 的 `AuthSettings` + `TokenVerifier` 路径面向 OAuth（需要 issuer/resource URL）。本服务器在设置了 `MCP_API_KEY` 时改用小型 ASGI 网关：接受 `Authorization: Bearer <key>` 或 `x-api-key: <key>`。
- 若未设置 `MCP_API_KEY`，HTTP 无需鉴权即可工作（适合本地实验；请勿公网暴露）。
- 上文示例使用**本地演示 Key** `mcp_f3bbd13d122f0febabca92495ce7bdc2`，仅供本地测试。超出私有实验环境时请自行生成新 Key；**切勿在生产环境使用该演示值**。
- 该 Key 绝不会传给 Open-Meteo。

## Cursor 配置

在**宿主机**的 `~/.cursor/mcp.json`（全局）或 `<项目>/.cursor/mcp.json`（项目级）中添加。Cursor 运行 `docker`，服务器跑在容器内。用 `args` 里的 `-e` 传入服务器环境变量。Cursor 的 `env` 块只会到达宿主机侧的 `docker` 进程，到不了容器内。

下面三种写法任选其一。

### 1）仅 STDIO（推荐默认）

Cursor 通过 `docker exec -i` 启动进程，无需单独的 HTTP 监听。适合日常在 Cursor 对话中使用，由客户端管理服务器生命周期。

```json
{
  "mcpServers": {
    "open-meteo-weather": {
      "command": "docker",
      "args": [
        "exec", "-i",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", "LOG_LEVEL=INFO",
        "-e", "OPEN_METEO_TIMEOUT=10",
        "cs146s-dev",
        "/opt/venvs/week3-mcp/bin/python",
        "/workspace/modern-software-dev-assignments/week3/server/main.py"
      ]
    }
  }
}
```

不使用容器时，把 `"command"` 设为 `/abs/path/to/week3/.venv/bin/python`，`"args"` 设为 `["/abs/path/to/week3/server/main.py"]`。

保存后打开 Cursor Settings → MCP，确认 `open-meteo-weather` 显示 2 个工具。服务器的 stderr 日志会出现在 MCP 输出面板中。容器必须处于运行状态（`docker start cs146s-dev`）。

### 2）仅 HTTP

**请先启动 HTTP 服务器**（见上文 [HTTP 传输](#http-传输可选--加分项)）。若 `8765` 端口无人监听，Cursor 无法连接。

```json
{
  "mcpServers": {
    "open-meteo-weather-http": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

若设置了可选的 `MCP_API_KEY`（须与启动 HTTP 服务器时使用的 Key 一致；下方为本地演示 Key — 勿用于生产）：

```json
{
  "mcpServers": {
    "open-meteo-weather-http": {
      "url": "http://127.0.0.1:8765/mcp",
      "headers": {
        "Authorization": "Bearer mcp_f3bbd13d122f0febabca92495ce7bdc2"
      }
    }
  }
}
```

适合需要与远程 MCP 客户端或其他 agent 共享长时间运行的服务器，或不希望 Cursor 每次会话都新拉起 STDIO 进程的场景。客户端对远程 `url` 条目的支持取决于 Cursor/MCP 版本（streamable-http）。

**何时不要用 HTTP：** 若 HTTP 进程未运行（或 `8765` 端口未开放），请关掉 HTTP 条目，改用 STDIO——STDIO 不需要预先启动监听进程。

### 3）两者同时写在一个 `mcp.json`（两个服务器名）

在同一文件中同时配置 STDIO（`open-meteo-weather`）与 HTTP（`open-meteo-weather-http`）：

```json
{
  "mcpServers": {
    "open-meteo-weather": {
      "command": "docker",
      "args": [
        "exec", "-i",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", "LOG_LEVEL=INFO",
        "-e", "OPEN_METEO_TIMEOUT=10",
        "cs146s-dev",
        "/opt/venvs/week3-mcp/bin/python",
        "/workspace/modern-software-dev-assignments/week3/server/main.py"
      ]
    },
    "open-meteo-weather-http": {
      "url": "http://127.0.0.1:8765/mcp",
      "headers": {
        "Authorization": "Bearer mcp_f3bbd13d122f0febabca92495ce7bdc2"
      }
    }
  }
}
```

未设置 `MCP_API_KEY` 时可省略 `headers`。使用 HTTP 时仍须**先启动 HTTP 服务器**。

**如何选择 / 切换：** 在 Cursor Settings → MCP 中分别启用或禁用各个服务器。建议**同一时间只启用其中一个**：二者暴露相同的工具（`geocode_city`、`get_current_weather`），同时启用可能导致 agent 因重复工具而混淆。

| 场景 | 优先选择 |
| --- | --- |
| 日常 Cursor 对话；HTTP 进程未运行 | STDIO（`open-meteo-weather`） |
| HTTP 服务器已启动；远程或共享客户端 | HTTP（`open-meteo-weather-http`） |
| 在同一项目中对比两种传输 | `mcp.json` 里都写上，但在 Settings → MCP 中只启用一个 |

Claude Desktop 在 `claude_desktop_config.json` 中使用相同的 `mcpServers` 配置块。

## 工具说明

### `geocode_city`

| 参数 | 类型 | 约束 |
| --- | --- | --- |
| `city` | `str` | 2–100 个字符 |

返回最佳匹配，以及最多 4 个 `other_matches`（用于处理重名城市，例如 "Springfield"）。

输入示例：

```json
{ "city": "Beijing" }
```

输出示例：

```json
{
  "query": "Beijing",
  "name": "Beijing",
  "country": "China",
  "admin1": "Beijing Municipality",
  "latitude": 39.9075,
  "longitude": 116.39723,
  "timezone": "Asia/Shanghai",
  "other_matches": [ { "name": "Beijing", "country": "China", "admin1": "Shanxi", "...": "..." } ]
}
```

错误示例（工具结果带 `isError: true`）：

```
Error executing tool geocode_city: No location found for city 'zzzzqqqxx'
```

### `get_current_weather`

| 参数 | 类型 | 约束 |
| --- | --- | --- |
| `latitude` | `float` | -90 … 90 |
| `longitude` | `float` | -180 … 180 |

输入示例：

```json
{ "latitude": 39.9075, "longitude": 116.39723 }
```

输出示例：

```json
{
  "latitude": 39.89455,
  "longitude": 116.35983,
  "timezone": "Asia/Shanghai",
  "time": "2026-10-09T11:15",
  "temperature": 22.1,
  "temperature_unit": "°C",
  "weather_code": 0,
  "weather_description": "Clear sky"
}
```

`weather_code` 是 WMO 天气代码，`weather_description` 是对应的文字描述。

### 在 Cursor 对话中的调用流程示例

1. 输入：*"What's the weather in Paris right now?"*
2. Agent 调用 `geocode_city`，参数 `{"city": "Paris"}`，得到经纬度 `48.85341, 2.3488`。
3. 再调用 `get_current_weather`，参数 `{"latitude": 48.85341, "longitude": 2.3488}`，并报告气温与天气状况。

也可以直接指定工具：*"Use get_current_weather for latitude 31.23, longitude 121.47."*

## 可靠性设计

- **输入校验**：参数类型和范围由工具的 JSON Schema（pydantic）强制约束，`weather.py` 中还会再检查一次。
- **超时与网络错误**：每个请求都有超时限制（`OPEN_METEO_TIMEOUT`），超时和传输错误会重试。
- **限流与 5xx 错误**：HTTP 429/500/502/503/504 最多共尝试 3 次，使用指数退避（0.5s、1s）。若响应带有数字格式的 `Retry-After` 头，按它等待，最长 10s。
- **其他 4xx 错误**：立即报错，并附上 Open-Meteo 返回的 `reason` 字段。
- **空结果**：地理编码没有匹配，或天气响应缺少 `current` 字段时，返回明确的工具错误，不返回空数据。
- 所有失败都以 MCP 工具错误（`isError: true`）和可读信息返回给客户端。stdout 上除了协议消息不会有任何其他输出。

## 自检

用真实的 MCP stdio 客户端启动服务器并调用两个工具，包括两个失败用例：

```bash
docker exec -i -w /workspace/modern-software-dev-assignments/week3 cs146s-dev \
  /opt/venvs/week3-mcp/bin/python -B - <<'EOF'
import asyncio, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(command=sys.executable, args=["-B", "server/main.py"])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        print("tools:", [t.name for t in (await s.list_tools()).tools])
        for name, args in [
            ("geocode_city", {"city": "Beijing"}),
            ("get_current_weather", {"latitude": 39.9075, "longitude": 116.39723}),
            ("geocode_city", {"city": "zzzzqqqxx"}),                 # expect isError=True
            ("get_current_weather", {"latitude": 200, "longitude": 0}),  # expect isError=True
        ]:
            res = await s.call_tool(name, args)
            print(name, args, "isError=", res.isError, "->", res.content[0].text[:200])

asyncio.run(main())
EOF
```

预期输出：`tools: ['geocode_city', 'get_current_weather']`，两次成功调用，两次 `isError= True`。服务器日志会穿插输出在 stderr 上。不使用容器时，在 `week3/` 目录下激活 `.venv` 后，用 `python -B -` 运行同样的脚本。

在宿主机上模拟 Cursor 启动服务器的方式。stdout 的每一行都必须能解析为 JSON-RPC：

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"host-check","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"geocode_city","arguments":{"city":"Shanghai"}}}' \
| (cat; sleep 4) \
| docker exec -i -e PYTHONDONTWRITEBYTECODE=1 cs146s-dev \
    /opt/venvs/week3-mcp/bin/python /workspace/modern-software-dev-assignments/week3/server/main.py 2>/dev/null \
| python3 -c 'import sys,json; [print(json.loads(l).get("id"), "ok") for l in sys.stdin]'
```

预期输出：`1 ok` 和 `2 ok`。
