from typing import TypedDict

import pytest
from langgraph.graph import END, StateGraph

from tradingagents.graph.checkpointer import (
    get_checkpointer,
    list_resumable_checkpoints,
    record_checkpoint_run,
    thread_id,
)


class _State(TypedDict):
    company_of_interest: str
    trade_date: str
    asset_type: str
    market_report: str


def _node(state: _State) -> dict:
    return {"market_report": "done"}


def _crash(state: _State) -> dict:
    raise RuntimeError("stop after checkpoint")


def test_recorded_checkpoint_metadata_is_listed(tmp_path):
    record_checkpoint_run(
        tmp_path,
        "GC=F",
        "2026-06-11",
        asset_type="stock",
        selected_analysts=["market", "news"],
        research_depth=3,
        output_language="Vietnamese",
    )

    # No LangGraph checkpoint rows exist yet, so this should not show a false
    # resumable item.
    assert list_resumable_checkpoints(tmp_path) == []


def test_list_resumable_checkpoints_with_recorded_metadata(tmp_path):
    builder = StateGraph(_State)
    builder.add_node("market", _node)
    builder.add_node("crash", _crash)
    builder.set_entry_point("market")
    builder.add_edge("market", "crash")
    builder.add_edge("crash", END)

    ticker = "GC=F"
    date = "2026-06-11"
    record_checkpoint_run(
        tmp_path,
        ticker,
        date,
        asset_type="stock",
        selected_analysts=["market", "news"],
        research_depth=3,
        output_language="Vietnamese",
    )

    with get_checkpointer(tmp_path, ticker) as saver:
        graph = builder.compile(checkpointer=saver)
        with pytest.raises(RuntimeError):
            graph.invoke(
                {
                    "company_of_interest": ticker,
                    "trade_date": date,
                    "asset_type": "stock",
                    "market_report": "",
                },
                config={"configurable": {"thread_id": thread_id(ticker, date)}},
            )

    items = list_resumable_checkpoints(tmp_path)

    assert len(items) == 1
    assert items[0]["ticker"] == ticker
    assert items[0]["date"] == date
    assert items[0]["selected_analysts"] == ["market", "news"]
    assert items[0]["research_depth"] == 3
    assert items[0]["output_language"] == "Vietnamese"
