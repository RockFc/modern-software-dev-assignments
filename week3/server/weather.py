"""Thin async client for the Open-Meteo geocoding and forecast APIs.

Everything here is transport-agnostic: no MCP imports, no printing.
Failures are surfaced as ``WeatherAPIError`` with a user-facing message.

【中文说明】本文件是业务层，完全不知道 MCP 的存在（不导入 mcp、不 print）。
它只负责调用 Open-Meteo 的两个 HTTP 接口，并处理超时、重试、限流和空结果。
所有失败都统一抛出 WeatherAPIError，由 main.py 转换成 MCP 的 ToolError。
这样分层的好处：同一份业务代码可以被 STDIO 服务器、HTTP 服务器或单元测试直接复用。
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Open-Meteo 的两个免费接口，无需 API Key。
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"  # 城市名 -> 经纬度
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"  # 经纬度 -> 当前天气

# 弹性策略相关配置：
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("OPEN_METEO_TIMEOUT", "10"))  # 单次请求超时（秒）
MAX_ATTEMPTS = 3  # 总尝试次数（含第一次）
BASE_BACKOFF_SECONDS = 0.5  # 指数退避基数：0.5s、1s、2s...
MAX_RETRY_AFTER_SECONDS = 10.0  # 服务器 Retry-After 头的等待上限，避免卡住客户端太久
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}  # 限流和服务端错误才值得重试
USER_AGENT = "cs146s-week3-weather-mcp/0.1"

# WMO weather interpretation codes, as documented by Open-Meteo.
# 天气代码 -> 文字描述，例如 0 = 晴，2 = 多云，61 = 小雨。
WMO_WEATHER_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherAPIError(Exception):
    """Raised when Open-Meteo cannot produce a usable answer."""


def describe_weather_code(code: int | None) -> str:
    if code is None:
        return "Unknown"
    return WMO_WEATHER_CODES.get(code, f"Unknown weather code {code}")


def _retry_delay(attempt: int, response: httpx.Response | None) -> float:
    # 优先遵守服务器返回的 Retry-After（仅支持秒数格式），并设置上限；
    # 否则使用指数退避：第 1 次失败等 0.5s，第 2 次等 1s。
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            return min(float(retry_after), MAX_RETRY_AFTER_SECONDS)
    return BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))


def _error_reason(response: httpx.Response) -> str:
    # Open-Meteo 出错时通常返回 {"error": true, "reason": "..."}，优先取 reason 给用户看。
    try:
        body = response.json()
    except ValueError:
        return response.text[:200] or response.reason_phrase
    if isinstance(body, dict) and body.get("reason"):
        return str(body["reason"])
    return response.reason_phrase


async def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET ``url`` with retries on timeouts, network errors, 429 and 5xx."""
    # 通用请求函数，两个业务函数都通过它访问 Open-Meteo。
    # 错误分类：
    #   - 超时 / 网络错误 / 429 / 5xx：可能是暂时性问题，退避后重试
    #   - 其他 4xx：请求本身有问题，重试无意义，立即报错
    #   - 200 但 JSON 无效：立即报错
    last_error = "unknown error"
    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            response: httpx.Response | None = None
            try:
                response = await client.get(url, params=params)
            except httpx.TimeoutException:
                last_error = f"request timed out after {REQUEST_TIMEOUT_SECONDS:g}s"
            except httpx.TransportError as exc:
                last_error = f"network error: {exc.__class__.__name__}"
            else:
                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise WeatherAPIError("Open-Meteo returned invalid JSON") from exc
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    raise WeatherAPIError(
                        f"Open-Meteo rejected the request "
                        f"(HTTP {response.status_code}): {_error_reason(response)}"
                    )
                if response.status_code == 429:
                    last_error = "rate limited by Open-Meteo (HTTP 429)"
                else:
                    last_error = f"Open-Meteo server error (HTTP {response.status_code})"

            # 走到这里说明本次失败但可重试；最后一次失败则跳出循环直接报错。
            if attempt < MAX_ATTEMPTS:
                delay = _retry_delay(attempt, response)
                logger.warning(
                    "Attempt %d/%d to %s failed (%s); retrying in %.1fs",
                    attempt, MAX_ATTEMPTS, url, last_error, delay,
                )
                # 用 asyncio.sleep 而不是 time.sleep，等待期间不阻塞事件循环。
                await asyncio.sleep(delay)

    raise WeatherAPIError(f"Open-Meteo request failed after {MAX_ATTEMPTS} attempts: {last_error}")


async def geocode_city(city: str, max_results: int = 5) -> dict[str, Any]:
    """Resolve a city name to coordinates. Raises if nothing matches."""
    # 第二层校验：即使不经过 MCP 的 schema 校验被直接调用，也保证输入合法。
    query = city.strip()
    if len(query) < 2:
        raise WeatherAPIError("City name must contain at least 2 characters")

    data = await _get_json(
        GEOCODING_URL,
        {"name": query, "count": max_results, "language": "en", "format": "json"},
    )
    # 空结果明确报错，而不是返回空数据让模型猜。
    results = data.get("results") or []
    if not results:
        raise WeatherAPIError(f"No location found for city '{query}'")

    # 只保留模型需要的字段，减少返回给客户端的噪音。
    matches = [
        {
            "name": item.get("name"),
            "country": item.get("country"),
            "admin1": item.get("admin1"),
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude"),
            "timezone": item.get("timezone"),
        }
        for item in results
    ]
    # 第一条作为最佳匹配平铺在顶层，其余放进 other_matches，便于处理重名城市。
    best, *others = matches
    return {"query": query, **best, "other_matches": others}


async def get_current_weather(latitude: float, longitude: float) -> dict[str, Any]:
    """Fetch current temperature and weather condition for a coordinate."""
    # 第二层校验：经纬度范围。
    if not -90.0 <= latitude <= 90.0:
        raise WeatherAPIError(f"Latitude must be between -90 and 90, got {latitude}")
    if not -180.0 <= longitude <= 180.0:
        raise WeatherAPIError(f"Longitude must be between -180 and 180, got {longitude}")

    data = await _get_json(
        FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,weather_code",  # 只请求当前气温和天气代码
            "timezone": "auto",  # 返回时间按当地时区显示
        },
    )
    current = data.get("current")
    if not current or current.get("temperature_2m") is None:
        raise WeatherAPIError("Open-Meteo returned no current weather for this location")

    units = data.get("current_units") or {}
    weather_code = current.get("weather_code")
    # 返回的经纬度是 Open-Meteo 网格点坐标，会与输入略有偏差，属正常现象。
    return {
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "timezone": data.get("timezone"),
        "time": current.get("time"),
        "temperature": current.get("temperature_2m"),
        "temperature_unit": units.get("temperature_2m", "°C"),
        "weather_code": weather_code,
        "weather_description": describe_weather_code(weather_code),
    }
