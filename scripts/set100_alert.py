#!/usr/bin/env python3
"""Send SET100 top gainers/losers to ntfy using the SET index-composition API."""

from __future__ import annotations

import asyncio
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from settfex.services.set import get_index_composition

BANGKOK = ZoneInfo("Asia/Bangkok")
EXPECTED_INDEX = "SET100"
EXPECTED_CONSTITUENTS = 100


class DataValidationError(RuntimeError):
    """Raised when source data is incomplete, stale, or inconsistent."""


@dataclass(frozen=True)
class Mover:
    symbol: str
    percent_change: float
    last: float | None


@dataclass(frozen=True)
class MarketSnapshot:
    market_datetime: datetime
    market_status: str
    constituents_count: int
    gainers: list[Mover]
    losers: list[Mover]


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None


async def fetch_snapshot() -> MarketSnapshot:
    """Fetch and validate the SET100 constituent quote table."""
    response = await get_index_composition(EXPECTED_INDEX, lang="en")

    index_symbol = (response.composition.symbol or "").strip().upper()
    if index_symbol != EXPECTED_INDEX:
        raise DataValidationError(
            f"API returned index {index_symbol!r}, expected {EXPECTED_INDEX}"
        )

    rows = response.constituents
    if len(rows) != EXPECTED_CONSTITUENTS:
        raise DataValidationError(
            f"Expected {EXPECTED_CONSTITUENTS} constituents, received {len(rows)}"
        )

    symbols = [str(row.symbol).strip().upper() for row in rows]
    if any(not symbol for symbol in symbols) or len(set(symbols)) != EXPECTED_CONSTITUENTS:
        raise DataValidationError("Constituent symbols are blank or duplicated")

    index_info = response.index_info
    market_datetime = index_info.market_date_time if index_info else None
    if market_datetime is None:
        row_times = [row.market_date_time for row in rows if row.market_date_time]
        market_datetime = max(row_times) if row_times else None

    if market_datetime is None or market_datetime.tzinfo is None:
        raise DataValidationError("API did not provide a timezone-aware market timestamp")

    market_datetime = market_datetime.astimezone(BANGKOK)
    now = datetime.now(BANGKOK)
    if market_datetime.date() != now.date():
        raise DataValidationError(
            "The latest market data is not from today "
            f"(source date: {market_datetime:%Y-%m-%d}, today: {now:%Y-%m-%d})"
        )

    market_status = (
        str(index_info.market_status or "Unknown") if index_info else "Unknown"
    )

    movers: list[Mover] = []
    for row in rows:
        pct = _number(row.percent_change)
        if pct is None:
            continue
        movers.append(
            Mover(
                symbol=str(row.symbol).strip().upper(),
                percent_change=pct,
                last=_number(row.last),
            )
        )

    if len(movers) < 90:
        raise DataValidationError(
            f"Only {len(movers)} of 100 constituents have valid percentage changes"
        )

    gainers = sorted(
        (item for item in movers if item.percent_change > 0),
        key=lambda item: (-item.percent_change, item.symbol),
    )[:3]
    losers = sorted(
        (item for item in movers if item.percent_change < 0),
        key=lambda item: (item.percent_change, item.symbol),
    )[:3]

    return MarketSnapshot(
        market_datetime=market_datetime,
        market_status=market_status,
        constituents_count=len(rows),
        gainers=gainers,
        losers=losers,
    )


def _format_mover(item: Mover) -> str:
    price = f" | ล่าสุด {item.last:,.2f} บาท" if item.last is not None else ""
    return f"{item.symbol}: {item.percent_change:+.2f}%{price}"


def build_alert_message(snapshot: MarketSnapshot, generated_at: datetime) -> str:
    lines = [
        "📊 SET100: Top Gainers & Losers",
        f"ข้อมูลตลาด ณ {snapshot.market_datetime:%d/%m/%Y %H:%M:%S} น.",
        f"สถานะตลาด: {snapshot.market_status}",
        f"ส่งแจ้งเตือน ณ {generated_at.astimezone(BANGKOK):%d/%m/%Y %H:%M:%S} น.",
        "",
        "📈 Top 3 Gainers",
    ]
    lines.extend(
        f"{rank}. {_format_mover(item)}"
        for rank, item in enumerate(snapshot.gainers, start=1)
    )
    if not snapshot.gainers:
        lines.append("ไม่มีหุ้นที่ปรับขึ้น")

    lines.extend(["", "📉 Top 3 Losers"])
    lines.extend(
        f"{rank}. {_format_mover(item)}"
        for rank, item in enumerate(snapshot.losers, start=1)
    )
    if not snapshot.losers:
        lines.append("ไม่มีหุ้นที่ปรับลง")

    lines.extend(["", "แหล่งข้อมูล: SET Index Composition API"])
    return "\n".join(lines)


def send_ntfy(message: str, title: str) -> None:
    topic = os.getenv("NTFY_TOPIC", "").strip()
    if not topic:
        raise RuntimeError("Missing GitHub Actions secret: NTFY_TOPIC")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", topic):
        raise RuntimeError("NTFY_TOPIC must contain only letters, numbers, _ or -")

    url = f"https://ntfy.sh/{quote(topic, safe='-_')}"
    headers = {
        "Title": title,
        "Priority": "default",
        "Tags": "chart_with_upwards_trend",
        "Content-Type": "text/plain; charset=utf-8",
    }
    token = os.getenv("NTFY_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, data=message.encode("utf-8"), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=20) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(f"ntfy returned HTTP {response.status}")
            print(f"ntfy notification sent (HTTP {response.status})")
    except HTTPError as exc:
        raise RuntimeError(f"ntfy returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach ntfy: {exc.reason}") from exc


def run(mode: str) -> None:
    if mode == "test-ntfy":
        now = datetime.now(BANGKOK)
        message = (
            "ntfy เชื่อมต่อ GitHub สำเร็จ\n"
            f"วันที่ {now:%d/%m/%Y}\nเวลา {now:%H:%M:%S} น. (เวลาไทย)"
        )
        send_ntfy(message, "GitHub Connection Test")
        return

    if mode not in {"alert", "check-data"}:
        raise ValueError(f"Unknown mode: {mode}")

    try:
        snapshot = asyncio.run(fetch_snapshot())
    except Exception as exc:
        print(f"Market data check failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        if mode == "alert":
            now = datetime.now(BANGKOK)
            warning = (
                "⚠️ SET100 Alert: ไม่สามารถยืนยันข้อมูลตลาดได้\n"
                f"วันที่ {now:%d/%m/%Y} เวลา {now:%H:%M:%S} น.\n"
                "ระบบงดจัดอันดับเพื่อป้องกันการแจ้งข้อมูลผิดพลาด "
                "โปรดตรวจสอบ GitHub Actions"
            )
            send_ntfy(warning, "SET100 Data Warning")
        raise

    print(
        f"Validated {snapshot.constituents_count} constituents; "
        f"market timestamp={snapshot.market_datetime.isoformat()}; "
        f"status={snapshot.market_status}"
    )
    print("Gainers:", ", ".join(_format_mover(x) for x in snapshot.gainers) or "none")
    print("Losers:", ", ".join(_format_mover(x) for x in snapshot.losers) or "none")

    if mode == "alert":
        message = build_alert_message(snapshot, datetime.now(BANGKOK))
        send_ntfy(message, "SET100 Top Gainers & Losers")


if __name__ == "__main__":
    selected_mode = sys.argv[1] if len(sys.argv) > 1 else "alert"
    run(selected_mode)
