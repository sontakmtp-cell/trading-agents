import os
from unittest import mock


def test_start_new_analysis_does_not_resume_checkpoint(monkeypatch):
    import cli.main as m

    fake_cfg = dict(m.DEFAULT_CONFIG)
    fake_cfg.update({
        "llm_provider": "openai",
        "backend_url": "https://opencode.ai/zen/go/v1",
        "quick_think_llm": "deepseek-v4-pro",
        "deep_think_llm": "kimi-k2.5",
        "output_language": "Japanese",
    })

    env = {
        "TRADINGAGENTS_LLM_PROVIDER": "openai",
        "TRADINGAGENTS_DEEP_THINK_LLM": "kimi-k2.5",
        "TRADINGAGENTS_QUICK_THINK_LLM": "deepseek-v4-pro",
        "TRADINGAGENTS_LLM_BACKEND_URL": "https://opencode.ai/zen/go/v1",
        "TRADINGAGENTS_OUTPUT_LANGUAGE": "Japanese",
        "OPENAI_API_KEY": "sk-test",
    }

    class _FakePrompt:
        def __init__(self, value):
            self.value = value

        def ask(self):
            return self.value

    with mock.patch.dict(os.environ, env, clear=False), \
         mock.patch.object(m, "DEFAULT_CONFIG", fake_cfg), \
         mock.patch.object(m, "list_resumable_checkpoints", return_value=[{
             "ticker": "GC=F",
             "date": "2026-06-11",
             "step": 30,
             "selected_analysts": ["market", "news"],
             "research_depth": 3,
             "output_language": "Vietnamese",
         }]), \
         mock.patch.object(m.questionary, "select", return_value=_FakePrompt("__NEW__")), \
         mock.patch.object(m, "get_ticker", return_value="AAPL"), \
         mock.patch.object(m, "get_analysis_date", return_value="2026-06-12"), \
         mock.patch.object(m, "select_analysts", return_value=[]), \
         mock.patch.object(m, "select_research_depth", return_value=1), \
         mock.patch.object(m, "ensure_api_key", return_value="sk-test"), \
         mock.patch.object(m, "fetch_announcements", return_value=None), \
         mock.patch.object(m, "display_announcements"):
        selections = m.get_user_selections(checkpoint_enabled=True)

    assert selections["ticker"] == "AAPL"
    assert selections["analysis_date"] == "2026-06-12"
    assert selections["resume_checkpoint"] is False
