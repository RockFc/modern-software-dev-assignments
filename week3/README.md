# Week 3 — Open-Meteo Weather MCP Server (STDIO + optional HTTP)

English | [中文](README.zh-CN.md)

A small MCP server that wraps the free, key-less [Open-Meteo](https://open-meteo.com/) APIs and exposes two tools:

| Tool | Upstream endpoint |
| --- | --- |
| `geocode_city(city: str)` | `GET https://geocoding-api.open-meteo.com/v1/search` |
| `get_current_weather(latitude: float, longitude: float)` | `GET https://api.open-meteo.com/v1/forecast?current=temperature_2m,weather_code` |

Default transport is **STDIO** (stdout = JSON-RPC, logs on **stderr**). Optional **HTTP** transport uses mcp 1.30 `streamable-http` (path `/mcp`) or `sse`. Open-Meteo itself needs no API key; optional `MCP_API_KEY` only gates the MCP HTTP endpoint.

```
week3/
├── README.md
└── server/
    ├── main.py           # FastMCP server, tools, stderr logging, STDIO + HTTP entrypoint
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
| `TRANSPORT` | `stdio` | `stdio` (default, Cursor docker exec), `http` / `streamable-http` (streamable-http on `/mcp`), or `sse` |
| `HOST` | `0.0.0.0` | Bind address for HTTP/SSE (ignored for STDIO) |
| `PORT` | `8765` | Bind port for HTTP/SSE (container publishes `8765:8765`) |
| `MCP_API_KEY` | (unset) | If set, HTTP/SSE require `Authorization: Bearer <key>` or `x-api-key: <key>`. Unset = no auth. Never forwarded to Open-Meteo. Local demo example (not for production): `mcp_f3bbd13d122f0febabca92495ce7bdc2`. |
| `LOG_LEVEL` | `INFO` | Python log level for stderr logs (`DEBUG`, `INFO`, `WARNING`, ...) |
| `OPEN_METEO_TIMEOUT` | `10` | Per-request timeout in seconds |
| `HTTPS_PROXY` / `ALL_PROXY` / `NO_PROXY` | (inherited) | Standard proxy variables, honored by httpx. Set `NO_PROXY=*` to bypass a broken proxy. |


## HTTP transport (optional / extra credit)

STDIO remains the primary way Cursor talks to this server (`docker exec -i`). HTTP is for remote MCP clients or agents.

Chosen transport: **streamable-http** (mcp 1.30 official transport: `transport="streamable-http"`, default path `/mcp`). `TRANSPORT=sse` is also supported (`/sse` + `/messages/`).

### Start inside the container

Unauthenticated (default when `MCP_API_KEY` is unset):

```bash
docker exec -d   -e PYTHONDONTWRITEBYTECODE=1   -e TRANSPORT=http   -e HOST=0.0.0.0   -e PORT=8765   -e LOG_LEVEL=INFO   cs146s-dev   /opt/venvs/week3-mcp/bin/python /workspace/modern-software-dev-assignments/week3/server/main.py
```

With optional API key (gates MCP only; Open-Meteo still key-less):

> **Local demo key (example for local testing only — not for production):** `mcp_f3bbd13d122f0febabca92495ce7bdc2`

Docker (`-e MCP_API_KEY=...`):

```bash
docker exec -d   -e PYTHONDONTWRITEBYTECODE=1   -e TRANSPORT=http   -e HOST=0.0.0.0   -e PORT=8765   -e MCP_API_KEY='mcp_f3bbd13d122f0febabca92495ce7bdc2'   cs146s-dev   /opt/venvs/week3-mcp/bin/python /workspace/modern-software-dev-assignments/week3/server/main.py
```

Or `export` then start (plain local / same shell):

```bash
export MCP_API_KEY='mcp_f3bbd13d122f0febabca92495ce7bdc2'
TRANSPORT=http HOST=0.0.0.0 PORT=8765 python server/main.py
```

Foreground (logs on stderr): drop `-d` and add `-i` if you want.

Port `8765` is already published on `cs146s-dev` (`0.0.0.0:8765->8765/tcp`).

### Curl / self-check (streamable-http initialize)

```bash
# From the host (or any machine that can reach the published port):
curl -sS -D - -o /tmp/mcp-init.body -X POST "http://127.0.0.1:8765/mcp"   -H "Content-Type: application/json"   -H "Accept: application/json, text/event-stream"   -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl-check","version":"0"}}}'
# Expect HTTP 200 and a JSON-RPC initialize result (or SSE-framed result).
# With MCP_API_KEY set, add: -H "Authorization: Bearer mcp_f3bbd13d122f0febabca92495ce7bdc2"  # local demo key only
# Missing/wrong key -> HTTP 401.
```

Confirm the process is listening, then stop the test server:

```bash
docker exec cs146s-dev sh -c 'ss -ltnp | grep 8765 || netstat -ltnp 2>/dev/null | grep 8765'
docker exec cs146s-dev pkill -f "week3/server/main.py" || true
```

### Cursor `mcp.json` (HTTP)

Full Cursor setups for **STDIO only**, **HTTP only**, and **both together** are in [Cursor configuration](#cursor-configuration) below. Reminder: start the HTTP server before enabling the HTTP entry; if the listener is down, use STDIO instead.

### Auth notes

- Official FastMCP 1.30 `AuthSettings` + `TokenVerifier` path is OAuth-oriented (requires issuer/resource URLs). This server instead uses a small ASGI gate when `MCP_API_KEY` is set: accepts `Authorization: Bearer <key>` or `x-api-key: <key>`.
- If `MCP_API_KEY` is unset, HTTP works without authentication (fine for local lab use; do not expose publicly).
- The examples above use the **local demo key** `mcp_f3bbd13d122f0febabca92495ce7bdc2` for local testing only. Generate your own key for anything beyond a private lab; **never use this demo value in production**.
- The key is never passed to Open-Meteo.

## Cursor configuration

Add entries to `~/.cursor/mcp.json` (global) or `<project>/.cursor/mcp.json` (project) on the **host**. Cursor runs `docker`; the server runs in the container. Pass server environment variables with `-e` in `args`. Cursor's `env` block only reaches the host-side `docker` process, not the container.

Choose one of the three setups below.

### 1) STDIO only (recommended default)

Cursor starts the process with `docker exec -i`. No separate HTTP listener is required. Use this for everyday Cursor chat when you want the client to own the server lifecycle.

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

### 2) HTTP only

**Start the HTTP server first** (see [HTTP transport](#http-transport-optional--extra-credit) above). If nothing is listening on port `8765`, Cursor cannot connect.

```json
{
  "mcpServers": {
    "open-meteo-weather-http": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

With optional `MCP_API_KEY` (must match the key used when starting the HTTP server; local demo key below — not for production):

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

Use HTTP when a long-running server should be shared with remote MCP clients or other agents, or when you prefer not to have Cursor spawn a new STDIO process each session. Client support for remote `url` entries depends on the Cursor/MCP version (streamable-http).

**When not to use HTTP:** if the HTTP process is not running (or port `8765` is closed), disable the HTTP entry and use STDIO instead—STDIO does not need a pre-started listener.

### 3) Both together (one `mcp.json`, two server names)

List STDIO as `open-meteo-weather` and HTTP as `open-meteo-weather-http` in the same file:

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

Omit the `headers` object if `MCP_API_KEY` is unset. For HTTP, still **start the HTTP server first**.

**How to choose / toggle:** In Cursor Settings → MCP, enable or disable each server independently. Prefer enabling **only one** at a time: both expose the same tools (`geocode_city`, `get_current_weather`), and having both enabled can confuse the agent with duplicate tools.

| Situation | Prefer |
| --- | --- |
| Everyday Cursor chat; no HTTP process running | STDIO (`open-meteo-weather`) |
| HTTP server already up; remote or shared clients | HTTP (`open-meteo-weather-http`) |
| Comparing transports in one project | Both in `mcp.json`, but enable only one in Settings → MCP |

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
