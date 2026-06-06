"""Shared collection, cleanup, rendering, and saving for Markdown reports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


MISSING_REPORT = "N/A - no report data was produced for this role"
UNSTRUCTURED_WARNING = (
    "> [!WARNING]\n"
    "> The agent output did not follow the requested report heading structure; "
    "the original content is preserved below."
)


@dataclass(frozen=True)
class RoleSpec:
    group_dir: str
    file_name: str
    group_title: str
    role_title: str
    state_path: tuple[str, ...]


ROLE_SPECS = (
    RoleSpec("1_analysts", "market.md", "I. Analyst Team", "Market Analyst", ("market_report",)),
    RoleSpec("1_analysts", "sentiment.md", "I. Analyst Team", "Sentiment Analyst", ("sentiment_report",)),
    RoleSpec("1_analysts", "news.md", "I. Analyst Team", "News Analyst", ("news_report",)),
    RoleSpec("1_analysts", "fundamentals.md", "I. Analyst Team", "Fundamentals Analyst", ("fundamentals_report",)),
    RoleSpec("2_research", "bull.md", "II. Research Team", "Bull Researcher", ("investment_debate_state", "bull_history")),
    RoleSpec("2_research", "bear.md", "II. Research Team", "Bear Researcher", ("investment_debate_state", "bear_history")),
    RoleSpec("2_research", "manager.md", "II. Research Team", "Research Manager", ("investment_debate_state", "judge_decision")),
    RoleSpec("3_trading", "trader.md", "III. Trading Team", "Trader", ("trader_investment_plan",)),
    RoleSpec("4_risk", "aggressive.md", "IV. Risk Management", "Aggressive Analyst", ("risk_debate_state", "aggressive_history")),
    RoleSpec("4_risk", "neutral.md", "IV. Risk Management", "Neutral Analyst", ("risk_debate_state", "neutral_history")),
    RoleSpec("4_risk", "conservative.md", "IV. Risk Management", "Conservative Analyst", ("risk_debate_state", "conservative_history")),
    RoleSpec("5_portfolio", "decision.md", "V. Portfolio Management", "Portfolio Manager", ("risk_debate_state", "judge_decision")),
)

_ROLE_PREFIX_RE = re.compile(
    r"(?m)^\s*(?:Bull|Bear|Aggressive|Neutral|Conservative) Analyst:\s*"
)
_H1_H2_RE = re.compile(r"(?m)^#{1,2}\s+")
_STRUCTURED_H3_RE = re.compile(r"(?m)^### \*\*\d+\.\s+.+\*\*\s*$")


def _get_path(state: Mapping[str, Any], path: tuple[str, ...]) -> str:
    value: Any = state
    for key in path:
        if not isinstance(value, Mapping):
            return ""
        value = value.get(key, "")
    return value if isinstance(value, str) else ""


def format_role_body(content: str) -> str:
    """Clean presentation-only role prefixes and preserve noncompliant output."""
    cleaned = _ROLE_PREFIX_RE.sub("", content or "").strip()
    if not cleaned:
        return MISSING_REPORT
    if _H1_H2_RE.search(cleaned) or not _STRUCTURED_H3_RE.search(cleaned):
        return f"{UNSTRUCTURED_WARNING}\n\n#### **A. Original Agent Output**\n\n{cleaned}"
    return cleaned


def collect_role_reports(state: Mapping[str, Any]) -> list[tuple[RoleSpec, str]]:
    return [(spec, format_role_body(_get_path(state, spec.state_path))) for spec in ROLE_SPECS]


def render_complete_report(state: Mapping[str, Any], ticker: str) -> str:
    parts = [f"# Trading Analysis Report: {ticker}"]
    current_group = None
    for spec, body in collect_role_reports(state):
        if spec.group_title != current_group:
            parts.append(f"## {spec.group_title}")
            current_group = spec.group_title
        parts.append(f"### {spec.role_title}\n\n{body}")
    return "\n\n".join(parts) + "\n"


def render_role_document(ticker: str, spec: RoleSpec, body: str) -> str:
    return (
        f"# Trading Analysis Report: {ticker}\n\n"
        f"## {spec.group_title}\n\n"
        f"### {spec.role_title}\n\n"
        f"{body}\n"
    )


def save_report_documents(state: Mapping[str, Any], ticker: str, save_path: Path) -> Path:
    save_path.mkdir(parents=True, exist_ok=True)
    reports = collect_role_reports(state)
    for spec, body in reports:
        group_dir = save_path / spec.group_dir
        group_dir.mkdir(exist_ok=True)
        (group_dir / spec.file_name).write_text(
            render_role_document(ticker, spec, body),
            encoding="utf-8",
        )
    complete_path = save_path / "complete_report.md"
    complete_path.write_text(render_complete_report(state, ticker), encoding="utf-8")
    return complete_path
