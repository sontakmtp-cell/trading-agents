from tradingagents.report_formatting import (
    MISSING_REPORT,
    ROLE_SPECS,
    format_role_body,
    render_complete_report,
    save_report_documents,
)
from tradingagents.agents.researchers.bull_researcher import create_bull_researcher
from tradingagents.agents.risk_mgmt.aggressive_debator import create_aggressive_debator
from tradingagents.agents.utils.agent_utils import get_report_output_instruction
from unittest.mock import MagicMock


def _complete_state():
    structured = "### **1. Overview**\n\n#### **A. Evidence**\n\n1. **Price**: $123.45 (+6.7%)\n\n| Metric | Value |\n|---|---:|\n| Price | $123.45 |"
    return {
        "market_report": structured,
        "sentiment_report": structured,
        "news_report": structured,
        "fundamentals_report": structured,
        "investment_debate_state": {
            "bull_history": f"Bull Analyst: {structured}",
            "bear_history": f"Bear Analyst: {structured}",
            "judge_decision": structured,
        },
        "trader_investment_plan": structured,
        "risk_debate_state": {
            "aggressive_history": f"Aggressive Analyst: {structured}",
            "neutral_history": f"Neutral Analyst: {structured}",
            "conservative_history": f"Conservative Analyst: {structured}",
            "judge_decision": structured,
        },
    }


def test_complete_report_has_fixed_groups_roles_and_risk_order():
    report = render_complete_report(_complete_state(), "NVDA")

    groups = [
        "## I. Analyst Team",
        "## II. Research Team",
        "## III. Trading Team",
        "## IV. Risk Management",
        "## V. Portfolio Management",
    ]
    assert [report.index(group) for group in groups] == sorted(report.index(group) for group in groups)
    assert report.index("### Aggressive Analyst") < report.index("### Neutral Analyst")
    assert report.index("### Neutral Analyst") < report.index("### Conservative Analyst")
    for spec in ROLE_SPECS:
        assert f"### {spec.role_title}" in report


def test_missing_roles_are_rendered_and_saved(tmp_path):
    complete_path = save_report_documents({}, "NVDA", tmp_path)

    assert complete_path.read_text(encoding="utf-8").count(MISSING_REPORT) == len(ROLE_SPECS)
    for spec in ROLE_SPECS:
        role_file = tmp_path / spec.group_dir / spec.file_name
        assert role_file.exists()
        assert MISSING_REPORT in role_file.read_text(encoding="utf-8")


def test_saved_complete_report_uses_shared_rendered_content(tmp_path):
    state = _complete_state()
    complete_path = save_report_documents(state, "NVDA", tmp_path)
    assert complete_path.read_text(encoding="utf-8") == render_complete_report(state, "NVDA")


def test_role_prefix_cleanup_preserves_numbers_percentages_and_table():
    content = (
        "Bull Analyst: ### **1. Thesis**\n\n"
        "#### **A. Evidence**\n\n"
        "1. **Price**: $123.45 (+6.7%)\n\n"
        "| Metric | Value |\n|---|---:|\n| Price | $123.45 |"
    )
    cleaned = format_role_body(content)

    assert "Bull Analyst:" not in cleaned
    assert "$123.45 (+6.7%)" in cleaned
    assert "| Price | $123.45 |" in cleaned


def test_noncompliant_output_is_preserved_under_warning():
    original = "# Model Heading\n\nPlain content with 42%."
    formatted = format_role_body(original)

    assert "[!WARNING]" in formatted
    assert "#### **A. Original Agent Output**" in formatted
    assert original in formatted


def test_shared_instruction_uses_requested_round_number():
    instruction = get_report_output_instruction(3)
    assert "This is round 3" in instruction
    assert "### **3. ...**" in instruction


def test_debate_agents_derive_continuous_round_number_from_state():
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="### **2. View**")
    state = {
        "company_of_interest": "NVDA",
        "market_report": "",
        "sentiment_report": "",
        "news_report": "",
        "fundamentals_report": "",
        "trader_investment_plan": "",
        "investment_debate_state": {"count": 2},
        "risk_debate_state": {"count": 3},
    }

    create_bull_researcher(llm)(state)
    assert "This is round 2" in llm.invoke.call_args.args[0]

    create_aggressive_debator(llm)(state)
    assert "This is round 2" in llm.invoke.call_args.args[0]
