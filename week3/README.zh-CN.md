# 第 3 周 — Open-Meteo 天气 MCP 服务器（本地 STDIO）

[English](README.md) | 中文

这是一个小型 MCP（Model Context Protocol）服务器，封装了免费、无需 API Key 的 [Open-Meteo](https://open-meteo.com/) 接口，对外提供两个工具：

| 工具 | 上游接口 |
| --- | --- |
| `geocode_city(city: str)` | `GET https://geocoding-api.open-meteo.com/v1/search` |
| `get_current_weather(latitude: float, longitude: float)` | `GET https://api.open-meteo.com/v1/forecast?current=temperature_2m,weather_code` |

传输方式**仅支持 STDIO**：stdout 只承载 JSON-RPC 协议消息，所有日志都写到 **stderr**。没有 HTTP 传输，也没有鉴权（Open-Meteo 不需要 API Key）。

```
week3/
├── README.md          # 英文文档
├── README.zh-CN.md    # 中文文档（本文件）
└── server/
    ├── main.py           # MCP 协议层：FastMCP 实例、工具定义、stderr 日志、stdio 入口
    ├── weather.py        # 业务层：Open-Meteo HTTP 客户端，含重试/退避、超时、错误映射
    └── requirements.txt
```

## MCP 接入原理

### 整体架构

```
Cursor（宿主机）
  │ 1. 读取 ~/.cursor/mcp.json
  │ 2. 启动子进程：docker exec -i cs146s-dev python main.py
  ▼
stdin  ──JSON-RPC 请求──►  main.py（FastMCP：协议层、工具注册）
stdout ◄──JSON-RPC 响应──        │ 调用
stderr ◄── 日志                  ▼
                           weather.py（httpx：调用 Open-Meteo HTTP API）
```

- **STDIO 传输**：服务器不监听任何端口。客户端把服务器作为子进程启动，通过管道读写它的 stdin/stdout 进行通信。
- **分层设计**：`main.py` 只处理 MCP 协议，`weather.py` 只负责调用天气 API，不导入任何 MCP 代码。业务代码因此可以直接复用到 HTTP 服务器或单元测试中。

### 协议交互过程

客户端与服务器之间的消息都是一行一个的 JSON-RPC 2.0 消息：

| 顺序 | 方向 | 方法 | 作用 |
| --- | --- | --- | --- |
| 1 | 客户端 → 服务器 | `initialize` | 握手，协商协议版本和能力 |
| 2 | 客户端 → 服务器 | `notifications/initialized` | 客户端确认握手完成（通知，没有 `id`） |
| 3 | 客户端 → 服务器 | `tools/list` | 获取工具列表：名字、描述、参数 JSON Schema |
| 4 | 客户端 → 服务器 | `tools/call` | 调用某个工具，服务器返回结果或 `isError: true` |

握手、分发和编解码都由 `FastMCP` 完成，我们只需要编写工具函数。

### `@mcp.tool()` 如何生成工具定义

`main.py` 中用 `@mcp.tool()` 装饰一个普通的异步函数，FastMCP 会自动从函数生成工具定义：

| 函数中的元素 | 生成的 MCP 工具字段 |
| --- | --- |
| 函数名，如 `geocode_city` | `name` |
| docstring | `description`（原样发给大模型） |
| 参数类型 + `Annotated[..., Field(...)]` | `inputSchema`（JSON Schema） |

例如：

```python
city: Annotated[str, Field(min_length=2, max_length=100, description="City name, ...")]
```

会生成：

```json
"city": {"type": "string", "minLength": 2, "maxLength": 100, "description": "City name, ..."}
```

docstring 写得好不好，直接影响模型能否正确使用工具。`get_current_weather` 的描述里写了 "Call geocode_city first if you only have a city name"，用于提示模型先做地理编码再查天气。

### 三条关键规则

1. **stdout 只能输出协议消息。** 一个 `print()` 就会让客户端收到无法解析的内容。所以 `main.py` 把 `logging` 配置为输出到 `sys.stderr`。
2. **错误要转换成 `ToolError`。** `weather.py` 抛出 `WeatherAPIError`，`main.py` 捕获后转换成 `ToolError`。客户端收到 `isError: true` 和可读的错误信息，服务器进程不会崩溃，模型可以据此调整参数重试。
3. **参数做两层校验。** 第一层是 pydantic schema，参数不合法时不会进入函数体；第二层是 `weather.py` 内部的范围检查，即使被直接调用也能保证输入合法。

## 环境要求

- Python **>= 3.10**（`mcp` SDK 的要求）
- 能访问 `*.open-meteo.com` 的 HTTPS 出网

## 当前部署方式：Cursor 在宿主机，服务器在容器内

宿主机的系统 Python 版本过低，所以服务器运行在 `cs146s-dev` 容器中（`continuumio/miniconda3`，Python 3.14）。宿主机目录 `~/workspace/cs146s` 挂载到容器的 `/workspace`。Cursor 运行在宿主机上，用 `docker exec -i` 启动服务器。`docker exec` 会透传 stdin 和 stdout，所以 STDIO 传输无需任何改动。

虚拟环境放在**容器内**的 `/opt/venvs/week3-mcp`，而不是挂载的仓库目录中，避免在工作区留下 root 所有的文件。容器重建后需要重新执行安装步骤。

### 安装（在宿主机执行一次）

```bash
docker exec cs146s-dev sh -c '
  python3 -m venv /opt/venvs/week3-mcp &&
  /opt/venvs/week3-mcp/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r /workspace/modern-software-dev-assignments/week3/server/requirements.txt'
```

`-i` 指定的清华镜像是可选的。这里使用它是因为容器访问 `files.pythonhosted.org` 很慢。

### 运行

```bash
docker exec -i -e PYTHONDONTWRITEBYTECODE=1 cs146s-dev \
  /opt/venvs/week3-mcp/bin/python /workspace/modern-software-dev-assignments/week3/server/main.py
```

启动后进程会等待 stdin 上的 MCP JSON-RPC 消息。通常不需要手动运行，由 MCP 客户端（Cursor、Claude Desktop、MCP Inspector）自动启动。

- `-i` 必须加，否则 stdin 不会接入容器，协议无法通信。
- `PYTHONDONTWRITEBYTECODE=1` 防止在挂载的仓库中生成 root 所有的 `__pycache__/`。

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
| `LOG_LEVEL` | `INFO` | 写到 stderr 的日志级别（`DEBUG`、`INFO`、`WARNING` 等） |
| `OPEN_METEO_TIMEOUT` | `10` | 单次请求超时时间（秒） |
| `HTTPS_PROXY` / `ALL_PROXY` / `NO_PROXY` | （继承） | 标准代理变量，httpx 会自动读取。代理异常时可设置 `NO_PROXY=*` 绕过 |

## Cursor 配置

在**宿主机**的 `~/.cursor/mcp.json`（全局）或 `<项目>/.cursor/mcp.json`（项目级）中添加：

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

字段说明：

- `"open-meteo-weather"`：服务器在 Cursor 中的名字，即工具所在的命名空间。
- `command` + `args`：Cursor 用它们启动子进程并接管其 stdin/stdout。
- `-e`：服务器的环境变量必须通过 `docker exec -e` 传入。如果写在 Cursor 的 `env` 字段中，只会传给宿主机上的 `docker` 进程，到不了容器内的 Python。

不使用容器时，把 `"command"` 设为 `/绝对路径/week3/.venv/bin/python`，`"args"` 设为 `["/绝对路径/week3/server/main.py"]`。

保存后打开 Cursor Settings → MCP，确认 `open-meteo-weather` 显示 2 个工具。服务器的 stderr 日志会出现在 MCP 输出面板中。容器必须处于运行状态（`docker start cs146s-dev`）。

Claude Desktop 在 `claude_desktop_config.json` 中使用相同的 `mcpServers` 配置。

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

`weather_code` 是 WMO 天气代码，`weather_description` 是对应的文字描述。返回的经纬度是 Open-Meteo 网格点坐标，与输入略有偏差属正常现象。

### 在 Cursor 中的调用流程示例

以输入 *"上海现在天气怎么样"* 为例：

1. Cursor 启动时已运行服务器，完成 `initialize` 握手，并通过 `tools/list` 获取了两个工具的定义。
2. 模型根据工具描述判断需要先获取坐标，Cursor 向 stdin 写入 `tools/call`，调用 `geocode_city`，参数为 `{"city": "Shanghai"}`。
3. FastMCP 用 pydantic 校验参数，调用 `main.geocode_city`，它再调用 `weather.geocode_city`，后者通过 httpx 请求 Open-Meteo。结果序列化为 JSON-RPC 响应写回 stdout，日志同时写到 stderr。
4. 模型拿到经纬度 `31.22, 121.46` 后调用 `get_current_weather`，得到气温和天气代码（例如 `2` 表示多云）。
5. 模型把结果整理成自然语言回答用户。

也可以直接指定工具：*"用 get_current_weather 查询纬度 31.23、经度 121.47 的天气。"*

## 可靠性设计

- **输入校验**：参数类型和范围由工具的 JSON Schema（pydantic）强制约束，`weather.py` 中还会再检查一次。
- **超时与网络错误**：每个请求都有超时限制（`OPEN_METEO_TIMEOUT`），超时和网络错误会重试。
- **限流与 5xx 错误**：HTTP 429/500/502/503/504 最多尝试 3 次，使用指数退避（0.5 秒、1 秒）。如果响应带有数字格式的 `Retry-After` 头，按它等待，最长 10 秒。
- **其他 4xx 错误**：立即报错，并附上 Open-Meteo 返回的 `reason` 字段。
- **空结果**：地理编码没有匹配，或天气响应缺少 `current` 字段时，返回明确的工具错误，不返回空数据。
- 所有失败都以 MCP 工具错误（`isError: true`）和可读信息返回给客户端。stdout 上除了协议消息不会有任何其他输出。

## 自检

### 用 Python MCP 客户端自检

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
            ("geocode_city", {"city": "zzzzqqqxx"}),                 # 预期 isError=True
            ("get_current_weather", {"latitude": 200, "longitude": 0}),  # 预期 isError=True
        ]:
            res = await s.call_tool(name, args)
            print(name, args, "isError=", res.isError, "->", res.content[0].text[:200])

asyncio.run(main())
EOF
```

预期输出：`tools: ['geocode_city', 'get_current_weather']`，两次成功调用，两次 `isError= True`。服务器日志会穿插输出在 stderr 上。不使用容器时，在 `week3/` 目录下激活 `.venv` 后，用 `python -B -` 运行同样的脚本。

### 手动发送 JSON-RPC 消息

在宿主机上模拟 Cursor 启动服务器的方式，直接向 stdin 写入原始协议消息，并检查 stdout 的每一行都能解析为 JSON-RPC：

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

预期输出：`1 ok` 和 `2 ok`。这个检查同时证明了没有日志混入 stdout。
