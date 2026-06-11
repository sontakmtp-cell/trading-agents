"""LangGraph checkpoint support for resumable analysis runs.

Per-ticker SQLite databases so concurrent tickers don't contend.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from langgraph.checkpoint.sqlite import SqliteSaver

from tradingagents.dataflows.utils import safe_ticker_component


def _db_path(data_dir: str | Path, ticker: str) -> Path:
    """Return the SQLite checkpoint DB path for a ticker."""
    # Reject ticker values that would escape the checkpoints directory.
    safe = safe_ticker_component(ticker).upper()
    p = Path(data_dir) / "checkpoints"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{safe}.db"


def _checkpoint_dir(data_dir: str | Path) -> Path:
    return Path(data_dir) / "checkpoints"


def _index_path(data_dir: str | Path) -> Path:
    return _checkpoint_dir(data_dir) / "_resume_index.json"


def thread_id(ticker: str, date: str) -> str:
    """Deterministic thread ID for a ticker+date pair."""
    return hashlib.sha256(f"{ticker.upper()}:{date}".encode()).hexdigest()[:16]


def _read_index(data_dir: str | Path) -> dict:
    path = _index_path(data_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_index(data_dir: str | Path, index: dict) -> None:
    path = _index_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def record_checkpoint_run(
    data_dir: str | Path,
    ticker: str,
    date: str,
    *,
    asset_type: str,
    selected_analysts: list[str],
    research_depth: int,
    output_language: str,
) -> None:
    """Record resume metadata that LangGraph's checkpoint key cannot expose."""
    tid = thread_id(ticker, str(date))
    index = _read_index(data_dir)
    index[tid] = {
        "thread_id": tid,
        "ticker": ticker,
        "date": str(date),
        "asset_type": asset_type,
        "selected_analysts": selected_analysts,
        "research_depth": research_depth,
        "output_language": output_language,
    }
    _write_index(data_dir, index)


def _drop_index_entry(data_dir: str | Path, ticker: str, date: str) -> None:
    index = _read_index(data_dir)
    if not index:
        return
    tid = thread_id(ticker, str(date))
    if tid in index:
        del index[tid]
        _write_index(data_dir, index)


@contextmanager
def get_checkpointer(data_dir: str | Path, ticker: str) -> Generator[SqliteSaver, None, None]:
    """Context manager yielding a SqliteSaver backed by a per-ticker DB."""
    db = _db_path(data_dir, ticker)
    conn = sqlite3.connect(str(db), check_same_thread=False)
    try:
        saver = SqliteSaver(conn)
        saver.setup()
        yield saver
    finally:
        conn.close()


def has_checkpoint(data_dir: str | Path, ticker: str, date: str) -> bool:
    """Check whether a resumable checkpoint exists for ticker+date."""
    return checkpoint_step(data_dir, ticker, date) is not None


def checkpoint_step(data_dir: str | Path, ticker: str, date: str) -> int | None:
    """Return the step number of the latest checkpoint, or None if none exists."""
    db = _db_path(data_dir, ticker)
    if not db.exists():
        return None
    tid = thread_id(ticker, date)
    with get_checkpointer(data_dir, ticker) as saver:
        config = {"configurable": {"thread_id": tid}}
        cp = saver.get_tuple(config)
        if cp is None:
            return None
        return cp.metadata.get("step")


def list_resumable_checkpoints(data_dir: str | Path) -> list[dict]:
    """Return unfinished checkpoints with enough metadata for CLI resume."""
    cp_dir = _checkpoint_dir(data_dir)
    if not cp_dir.exists():
        return []

    index = _read_index(data_dir)
    items: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for db in cp_dir.glob("*.db"):
        ticker_from_db = db.stem
        try:
            conn = sqlite3.connect(str(db))
            thread_ids = [
                row[0]
                for row in conn.execute(
                    "SELECT DISTINCT thread_id FROM checkpoints ORDER BY thread_id"
                ).fetchall()
            ]
        except sqlite3.OperationalError:
            continue
        finally:
            try:
                conn.close()
            except UnboundLocalError:
                pass

        with get_checkpointer(data_dir, ticker_from_db) as saver:
            for tid in thread_ids:
                cp = saver.get_tuple({"configurable": {"thread_id": tid}})
                if cp is None:
                    continue
                channel_values = cp.checkpoint.get("channel_values", {})
                metadata = dict(index.get(tid, {}))
                ticker = metadata.get("ticker") or channel_values.get("company_of_interest") or ticker_from_db
                date = metadata.get("date") or channel_values.get("trade_date")
                if not ticker or not date:
                    continue

                selected_analysts = metadata.get("selected_analysts")
                if not selected_analysts:
                    report_keys = {
                        "market_report": "market",
                        "sentiment_report": "social",
                        "news_report": "news",
                        "fundamentals_report": "fundamentals",
                    }
                    selected_analysts = [
                        key for report, key in report_keys.items() if channel_values.get(report)
                    ]

                key = (str(ticker), str(date))
                if key in seen:
                    continue
                seen.add(key)
                items.append(
                    {
                        "thread_id": tid,
                        "ticker": str(ticker),
                        "date": str(date),
                        "asset_type": metadata.get("asset_type")
                        or channel_values.get("asset_type")
                        or "stock",
                        "selected_analysts": selected_analysts,
                        "research_depth": metadata.get("research_depth", 1),
                        "output_language": metadata.get("output_language", "English"),
                        "step": cp.metadata.get("step"),
                        "updated_at": cp.checkpoint.get("ts", ""),
                    }
                )

    return sorted(items, key=lambda item: item.get("updated_at", ""), reverse=True)


def clear_all_checkpoints(data_dir: str | Path) -> int:
    """Remove all checkpoint DBs. Returns number of files deleted."""
    cp_dir = Path(data_dir) / "checkpoints"
    if not cp_dir.exists():
        return 0
    dbs = list(cp_dir.glob("*.db"))
    for db in dbs:
        db.unlink()
    index = _index_path(data_dir)
    if index.exists():
        index.unlink()
    return len(dbs)


def clear_checkpoint(data_dir: str | Path, ticker: str, date: str) -> None:
    """Remove checkpoint for a specific ticker+date by deleting the thread's rows."""
    db = _db_path(data_dir, ticker)
    if not db.exists():
        return
    tid = thread_id(ticker, date)
    conn = sqlite3.connect(str(db))
    try:
        for table in ("writes", "checkpoints"):
            conn.execute(f"DELETE FROM {table} WHERE thread_id = ?", (tid,))
        conn.commit()
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()
    _drop_index_entry(data_dir, ticker, date)
