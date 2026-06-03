from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta
from stockstats import wrap

from .symbol_utils import NoMarketDataError

BASE_URL = "https://api.binance.com"
REQUEST_TIMEOUT = 10
SUPPORTED_QUOTES = ("USDT",)


def normalize_binance_symbol(raw: str) -> str:
    """Normalize common crypto pair spellings to Binance Spot form."""
    if not isinstance(raw, str) or not raw.strip():
        return raw

    symbol = raw.strip().upper().replace("-", "").replace("/", "").replace("_", "")
    if symbol.endswith("USD") and not symbol.endswith("USDT"):
        symbol = f"{symbol[:-3]}USDT"
    return symbol


def _request_json(path: str, params: dict | None = None):
    response = requests.get(
        f"{BASE_URL}{path}",
        params=params or {},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def validate_symbol(symbol: str) -> str:
    """Return a Binance Spot symbol only when it exists and is trading."""
    canonical = normalize_binance_symbol(symbol)
    if not canonical or not canonical.endswith(SUPPORTED_QUOTES):
        raise NoMarketDataError(symbol, canonical, "only Binance Spot USDT pairs are supported")

    try:
        info = _request_json("/api/v3/exchangeInfo", {"symbol": canonical})
    except requests.HTTPError as exc:
        raise NoMarketDataError(symbol, canonical, "symbol not found on Binance Spot") from exc

    symbols = info.get("symbols") or []
    if not symbols or symbols[0].get("status") != "TRADING":
        raise NoMarketDataError(symbol, canonical, "symbol is not trading on Binance Spot")
    return canonical


def _date_to_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def parse_klines(klines: list, curr_date: str | None = None) -> pd.DataFrame:
    """Convert Binance kline rows to Date/Open/High/Low/Close/Volume."""
    rows = []
    for item in klines:
        rows.append(
            {
                "Date": pd.to_datetime(item[0], unit="ms", utc=True).tz_localize(None).normalize(),
                "Open": item[1],
                "High": item[2],
                "Low": item[3],
                "Close": item[4],
                "Volume": item[5],
            }
        )

    data = pd.DataFrame(rows)
    if data.empty:
        return data

    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    for column in ("Open", "High", "Low", "Close", "Volume"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=["Date", "Close"]).sort_values("Date")

    if curr_date:
        data = data[data["Date"] <= pd.to_datetime(curr_date)]

    return data.reset_index(drop=True)


def load_ohlcv(symbol: str, curr_date: str) -> pd.DataFrame:
    canonical = validate_symbol(symbol)
    curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    start_dt = curr_dt - relativedelta(years=5)

    klines = _request_json(
        "/api/v3/klines",
        {
            "symbol": canonical,
            "interval": "1d",
            "startTime": _date_to_ms(start_dt.strftime("%Y-%m-%d")),
            "endTime": _date_to_ms(curr_date),
            "limit": 1000,
        },
    )
    data = parse_klines(klines, curr_date)
    if data.empty:
        raise NoMarketDataError(symbol, canonical, f"no daily klines on or before {curr_date}")
    return data


def get_stock_data(
    symbol: Annotated[str, "Binance Spot pair symbol such as BTCUSDT"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    canonical = validate_symbol(symbol)
    klines = _request_json(
        "/api/v3/klines",
        {
            "symbol": canonical,
            "interval": "1d",
            "startTime": _date_to_ms(start_date),
            "endTime": _date_to_ms(end_date),
            "limit": 1000,
        },
    )
    data = parse_klines(klines, end_date)
    data = data[data["Date"] >= pd.to_datetime(start_date)] if not data.empty else data
    if data.empty:
        raise NoMarketDataError(symbol, canonical, f"no daily klines between {start_date} and {end_date}")

    csv_string = data.to_csv(index=False)
    header = f"# Binance Spot data for {canonical} from {start_date} to {end_date}\n"
    header += f"# Total records: {len(data)}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    return header + csv_string


def get_indicator(
    symbol: Annotated[str, "Binance Spot pair symbol such as BTCUSDT"],
    indicator: Annotated[str, "technical indicator to calculate"],
    curr_date: Annotated[str, "current trading date in YYYY-mm-dd format"],
    look_back_days: Annotated[int, "how many days to look back"],
) -> str:
    curr_date_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    before = curr_date_dt - relativedelta(days=look_back_days)

    data = load_ohlcv(symbol, curr_date)
    df = wrap(data)
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    df[indicator]

    values = {}
    for _, row in df.iterrows():
        value = row[indicator]
        values[row["Date"]] = "N/A" if pd.isna(value) else str(value)

    lines = []
    cursor = curr_date_dt
    while cursor >= before:
        date_str = cursor.strftime("%Y-%m-%d")
        lines.append(f"{date_str}: {values.get(date_str, 'N/A: Not a trading day')}")
        cursor = cursor - relativedelta(days=1)

    return (
        f"## Binance Spot {indicator} values for {normalize_binance_symbol(symbol)} "
        f"from {before.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
        + "\n".join(lines)
    )
