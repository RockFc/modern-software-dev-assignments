"""Open-Meteo weather MCP server (STDIO + optional HTTP).

stdout carries the JSON-RPC stream in STDIO mode, so all logging goes to stderr.

【中文说明】本文件是 MCP 协议层，只负责“把普通函数暴露成 MCP 工具”。
整体流程（STDIO）：
  1. MCP 客户端（如 Cursor）读取 ~/.cursor/mcp.json，把本脚本作为子进程启动，
     并接管它的 stdin / stdout。
  2. 客户端通过 stdin 发送 JSON-RPC 请求：
       initialize          -> 握手，协商协议版本与能力
       tools/list          -> 获取工具列表（名字、描述、参数 JSON Schema）
       tools/call          -> 调用某个工具
  3. FastMCP 解析请求、校验参数、调用下面用 @mcp.tool() 注册的函数，
     再把返回值序列化成 JSON-RPC 响应写回 stdout。
  4. 真正访问天气 API 的逻辑在 weather.py，本文件不直接发 HTTP 请求。

HTTP（TRANSPORT=http / streamable-http）：同一套工具通过 mcp==1.30 的
streamable-http 传输暴露在 HOST:PORT（默认 0.0.0.0:8765），路径 /mcp。
可选 MCP_API_KEY 只校验入站 Authorization: Bearer / x-api-key，不会转发给 Open-Meteo。
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Annotated, Any

# FastMCP：官方 mcp SDK 提供的高层封装，帮我们处理握手、工具分发、JSON-RPC 编解码。
from mcp.server.fastmcp import FastMCP
# ToolError：抛出后，客户端会收到 isError=true 的工具结果，而不是进程崩溃。
from mcp.server.fastmcp.exceptions import ToolError
# Field：为参数声明约束和描述，FastMCP 会把它们转换成工具的 JSON Schema。
from pydantic import Field

# 业务层：与 MCP 无关的 Open-Meteo 客户端。
import weather

# STDIO 模式的铁律：stdout 只能输出 JSON-RPC 协议消息。
# 任何 print() 或写到 stdout 的日志都会让客户端解析失败，所以日志一律写到 stderr。
# Cursor 会把 stderr 内容显示在 MCP 输出面板中，方便调试。
logging.basicConfig(
    stream=sys.stderr,
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("weather-mcp")

# Host/port are read at construction time so FastMCP does not auto-enable
# localhost-only DNS-rebinding protection when we intend to bind 0.0.0.0.
_HOST = os.environ.get("HOST", "0.0.0.0")
_PORT = int(os.environ.get("PORT", "8765"))

# 创建 MCP 服务器实例。名字会在 initialize 握手时作为 serverInfo 发给客户端。
mcp = FastMCP("open-meteo-weather", host=_HOST, port=_PORT)


# @mcp.tool() 把下面的异步函数注册为一个 MCP 工具，自动生成工具定义：
#   - 函数名 geocode_city          -> 工具名 name
#   - docstring                    -> 工具描述 description（会原样发给大模型，影响模型何时、如何调用）
#   - 参数类型 + Annotated/Field   -> 参数 JSON Schema inputSchema
#     例如 city 会生成 {"type": "string", "minLength": 2, "maxLength": 100, "description": ...}
# 客户端调用 tools/call 时，FastMCP 先按 schema 用 pydantic 校验参数，不合法直接返回错误，不会进入函数体。
@mcp.tool()
async def geocode_city(
    city: Annotated[
        str,
        Field(min_length=2, max_length=100, description="City name, e.g. 'Beijing' or 'Paris'"),
    ],
) -> dict[str, Any]:
    """Look up a city with the Open-Meteo geocoding API.

    Returns the best match (name, country, admin1 region, latitude, longitude,
    timezone) plus up to 4 other candidate matches. Fails if no city matches.
    """
    logger.info("geocode_city city=%r", city)
    try:
        # 返回的 dict 会被 FastMCP 序列化为 JSON，作为工具结果写回 stdout。
        return await weather.geocode_city(city)
    except weather.WeatherAPIError as exc:
        # 把业务异常转换成 ToolError：客户端收到 isError=true 和可读的错误信息，
        # 模型可以据此调整参数重试；服务器进程继续运行。
        logger.warning("geocode_city failed: %s", exc)
        raise ToolError(str(exc)) from exc


# 第二个工具，模式与上面相同。
# Field(ge=..., le=...) 会生成 schema 中的 minimum / maximum，越界参数在校验阶段就被拒绝。
# docstring 中 "Call geocode_city first if you only have a city name" 是写给模型的调用顺序提示：
# 用户只给城市名时，模型会先调用 geocode_city 拿到经纬度，再调用本工具。
@mcp.tool()
async def get_current_weather(
    latitude: Annotated[float, Field(ge=-90, le=90, description="Latitude in decimal degrees")],
    longitude: Annotated[float, Field(ge=-180, le=180, description="Longitude in decimal degrees")],
) -> dict[str, Any]:
    """Get the current temperature and weather condition at a coordinate.

    Uses the Open-Meteo forecast API. Call geocode_city first if you only
    have a city name.
    """
    logger.info("get_current_weather lat=%s lon=%s", latitude, longitude)
    try:
        return await weather.get_current_weather(latitude, longitude)
    except weather.WeatherAPIError as exc:
        logger.warning("get_current_weather failed: %s", exc)
        raise ToolError(str(exc)) from exc


def _normalize_transport(raw: str | None) -> str:
    """Map env TRANSPORT to a FastMCP transport name."""
    value = (raw or "stdio").strip().lower()
    if value in ("http", "streamable-http", "streamable_http"):
        return "streamable-http"
    if value == "sse":
        return "sse"
    return "stdio"


class _ApiKeyGate:
    """ASGI middleware: require Bearer token or x-api-key matching MCP_API_KEY.

    Only gates access to this MCP HTTP app. The key is never forwarded to
    Open-Meteo (weather.py does not read MCP_API_KEY).
    """

    def __init__(self, app: Any, api_key: str) -> None:
        self.app = app
        self.api_key = api_key

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            headers = {
                k.decode("latin-1").lower(): v.decode("latin-1")
                for k, v in scope.get("headers", [])
            }
            provided: str | None = None
            auth = headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                provided = auth[7:].strip()
            elif "x-api-key" in headers:
                provided = headers["x-api-key"].strip()
            if provided != self.api_key:
                body = b'{"error":"unauthorized","hint":"Authorization: Bearer <MCP_API_KEY> or x-api-key"}'
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"www-authenticate", b'Bearer realm="mcp"'),
                            (b"content-length", str(len(body)).encode("ascii")),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


async def _run_http(transport: str) -> None:
    """Serve streamable-http or SSE with optional MCP_API_KEY gate."""
    import uvicorn

    api_key = os.environ.get("MCP_API_KEY")
    if transport == "sse":
        app: Any = mcp.sse_app()
        paths = f"sse={mcp.settings.sse_path} messages={mcp.settings.message_path}"
    else:
        app = mcp.streamable_http_app()
        paths = f"streamable-http={mcp.settings.streamable_http_path}"

    if api_key:
        logger.info(
            "MCP_API_KEY is set: requiring Authorization: Bearer <key> or x-api-key "
            "(key is NOT sent to Open-Meteo)"
        )
        app = _ApiKeyGate(app, api_key)
    else:
        logger.info("MCP_API_KEY unset: HTTP MCP endpoint is unauthenticated")

    logger.info(
        "Starting open-meteo-weather MCP HTTP server transport=%s host=%s port=%s %s",
        transport,
        mcp.settings.host,
        mcp.settings.port,
        paths,
    )
    config = uvicorn.Config(
        app,
        host=mcp.settings.host,
        port=mcp.settings.port,
        log_level=os.environ.get("LOG_LEVEL", "INFO").lower(),
    )
    server = uvicorn.Server(config)
    await server.serve()


def main() -> None:
    transport = _normalize_transport(os.environ.get("TRANSPORT"))
    if transport == "stdio":
        logger.info("Starting open-meteo-weather MCP server on stdio")
        # 进入事件循环：持续从 stdin 读取 JSON-RPC 消息、把响应写到 stdout，
        # 直到客户端关闭管道。
        mcp.run(transport="stdio")
        return

    import anyio

    anyio.run(_run_http, transport)


if __name__ == "__main__":
    main()