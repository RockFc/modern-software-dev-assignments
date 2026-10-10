# Week 3 — Open-Meteo Weather MCP Server (local STDIO)

English | [中文](README.zh-CN.md)

A small MCP server that wraps the free, key-less [Open-Meteo](https://open-meteo.com/) APIs and exposes two tools:

| Tool | Upstream endpoint |
| --- | --- |
| `geocode_city(city: str)` | `GET https://geocoding-api.open-meteo.com/v1/search` |
| `get_current_weather(latitude: float, longitude: float)` | `GET https://api.open-meteo.com/v1/forecast?current=temperature_2m,weather_code` |

Transport is **STDIO only**: stdout carries the JSON-RPC stream, and all logs go to **stderr**. There is no HTTP transport and no auth (Open-Meteo needs no API key).

```
week3/
├── README.md
└── server/
    ├── main.py           # FastMCP server, tool definitions, stderr logging, stdio entrypoint
    ├── weather.py        # Open-Meteo HTTP client: retries/backoff, timeouts, error mapping
    └── requirements.txt
```

## Prerequisites

- Python **>= 3.10** (required by the `mcp` SDK)
- Outbound HTTPS access to `*.open-meteo.com`

## Setup used here: Cursor on the host, server in a container

The host's system Python is too old, so the server runs inside the `cs146s-dev` container (`continuumio/miniconda3`, Python 3.14). The host directory `~/workspace/cs146s` is mounted at `/workspace`. Cursor runs on the host and starts the server with `docker exec -i`. stdin and stdout pass through `docker exec`, so STDIO transport works unchanged.

The venv lives **inside the container** at `/opt/venvs/week3-mcp`, not in the bind-mounted repo. That keeps root-owned files out of the working tree. Re-run the install step if the container is recreated.

### Install (once, from the host)

```bash
docker exec cs146s-dev sh -c '
  python3 -m venv /opt/venvs/week3-mcp &&
  /opt/venvs/week3-mcp/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r /workspace/modern-software-dev-assignments/week3/server/requirements.txt'
```

The `-i` mirror is optional. Use it because `files.pythonhosted.org` is very slow from this container.

### Run

```bash
docker exec -i -e PYTHONDONTWRITEBYTECODE=1 cs146s-dev \
  /opt/venvs/week3-mcp/bin/python /workspace/modern-software-dev-assignments/week3/server/main.py
```

The process then waits for MCP JSON-RPC messages on stdin. Normally an MCP client (Cursor, Claude Desktop, MCP Inspector) launches it for you. `-i` is required, because without it stdin is not attached. `PYTHONDONTWRITEBYTECODE=1` keeps root-owned `__pycache__/` out of the mounted repo.

### Plain local setup (no container)

```bash
cd week3
python3 -m venv .venv && source .venv/bin/activate   # Python >= 3.10
pip install -r server/requirements.txt
python server/main.py
```

### Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | Python log level for stderr logs (`DEBUG`, `INFO`, `WARNING`, ...) |
| `OPEN_METEO_TIMEOUT` | `10` | Per-request timeout in seconds |
| `HTTPS_PROXY` / `ALL_PROXY` / `NO_PROXY` | (inherited) | Standard proxy variables, honored by httpx. Set `NO_PROXY=*` to bypass a broken proxy. |

## Cursor configuration

Add this to `~/.cursor/mcp.json` (global) or `<project>/.cursor/mcp.json` (project) on the **host**. Cursor runs `docker`, and the server runs in the container. Pass server environment variables with `-e` in `args`. Cursor's `env` block would only reach the host-side `docker` process, not the container.

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

Without the container, set `"command"` to `/abs/path/to/week3/.venv/bin/python` and `"args"` to `["/abs/path/to/week3/server/main.py"]`.

After saving, open Cursor Settings → MCP and confirm `open-meteo-weather` shows 2 tools. Server stderr logs appear in the MCP output panel. The container must be running (`docker start cs146s-dev`).

Claude Desktop uses the same `mcpServers` block in `claude_desktop_config.json`.

## Tool reference

### `geocode_city`

| Param | Type | Constraints |
| --- | --- | --- |
| `city` | `str` | 2–100 characters |

Returns the best match plus up to 4 `other_matches` (useful for ambiguous names like "Springfield").

Example input:

```json
{ "city": "Beijing" }
```

Example output:

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

Error example (tool result has `isError: true`):

```
Error executing tool geocode_city: No location found for city 'zzzzqqqxx'
```

### `get_current_weather`

| Param | Type | Constraints |
| --- | --- | --- |
| `latitude` | `float` | -90 … 90 |
| `longitude` | `float` | -180 … 180 |

Example input:

```json
{ "latitude": 39.9075, "longitude": 116.39723 }
```

Example output:

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

`weather_code` is a WMO code; `weather_description` is its human-readable label.

### Example flow in Cursor chat

1. Type: *"What's the weather in Paris right now?"*
2. The agent calls `geocode_city` with `{"city": "Paris"}` and gets lat/lon `48.85341, 2.3488`.
3. It then calls `get_current_weather` with `{"latitude": 48.85341, "longitude": 2.3488}` and reports the temperature and condition.

You can also call a tool directly: *"Use get_current_weather for latitude 31.23, longitude 121.47."*

## Reliability behavior

- **Input validation**: argument types and ranges are enforced in the tool JSON schema (pydantic), and checked again in `weather.py`.
- **Timeouts and network errors**: each request has a timeout (`OPEN_METEO_TIMEOUT`). Timeouts and transport errors are retried.
- **Rate limits and 5xx errors**: HTTP 429/500/502/503/504 are retried up to 3 attempts in total, with exponential backoff (0.5s, 1s). A numeric `Retry-After` header is honored, capped at 10s.
- **Other 4xx errors**: reported immediately with Open-Meteo's `reason` field.
- **Empty results**: no geocoding match, or a missing `current` block, produces an explicit tool error instead of empty data.
- All failures reach the client as MCP tool errors (`isError: true`) with a readable message. Nothing is written to stdout except protocol messages.

## Self-check

Runs a real MCP stdio client against the server and calls both tools, including two failure cases:

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

Expected: `tools: ['geocode_city', 'get_current_weather']`, two successful calls, and two `isError= True` calls. Server logs are interleaved on stderr. Without the container, run the same heredoc with `python -B -` inside `week3/` after activating `.venv`.

Host-side check that mirrors how Cursor launches the server. Every stdout line must parse as JSON-RPC:

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

Expected output: `1 ok` and `2 ok`.
