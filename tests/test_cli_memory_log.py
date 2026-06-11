from cli.models import AnalystType


class _DummyLive:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_run_analysis_streaming_path_uses_memory_log(monkeypatch, tmp_path):
    import cli.main as cli_main

    graph_holder = {}

    selections = {
        "ticker": "NVDA",
        "analysis_date": "2026-01-10",
        "asset_type": "stock",
        "investor_briefing": "Existing position: 500 shares.",
        "research_depth": 1,
        "shallow_thinker": "quick",
        "deep_thinker": "deep",
        "backend_url": "http://localhost",
        "llm_provider": "openai",
        "google_thinking_level": None,
        "openai_reasoning_effort": None,
        "anthropic_effort": None,
        "output_language": "English",
        "analysts": {AnalystType.MARKET},
    }

    final_chunk = {
        "messages": [],
        "market_report": "Market report.",
        "investment_debate_state": {
            "bull_history": "Bull case.",
            "bear_history": "Bear case.",
            "history": "",
            "current_response": "",
            "judge_decision": "Research decision.",
        },
        "investment_plan": "Investment plan.",
        "trader_investment_plan": "Trader plan.",
        "risk_debate_state": {
            "aggressive_history": "Aggressive view.",
            "conservative_history": "Conservative view.",
            "neutral_history": "Neutral view.",
            "history": "",
            "latest_speaker": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "judge_decision": "Rating: Buy\nFinal decision.",
            "count": 1,
        },
        "final_trade_decision": "Rating: Buy\nFinal decision.",
    }

    class FakeMemoryLog:
        def __init__(self):
            self.stored = []

        def get_past_context(self, ticker):
            self.context_ticker = ticker
            return "prior resolved context"

        def store_decision(self, **kwargs):
            self.stored.append(kwargs)

    class FakePropagator:
        def __init__(self):
            self.initial_state_kwargs = None

        def create_initial_state(self, *args, **kwargs):
            self.initial_state_args = args
            self.initial_state_kwargs = kwargs
            return {"messages": []}

        def get_graph_args(self, callbacks=None):
            self.callbacks = callbacks
            return {}

    class FakeInnerGraph:
        def stream(self, init_agent_state, **args):
            yield final_chunk

    class FakeTradingAgentsGraph:
        def __init__(self, *args, **kwargs):
            self.memory_log = FakeMemoryLog()
            self.propagator = FakePropagator()
            self.graph = FakeInnerGraph()
            self.resolved_pending = []
            graph_holder["graph"] = self

        def _resolve_pending_entries(self, ticker):
            self.resolved_pending.append(ticker)

        def resolve_instrument_context(self, ticker, asset_type):
            return f"{asset_type}:{ticker}"

        def process_signal(self, full_signal):
            return "Buy"

    monkeypatch.setattr(cli_main, "TradingAgentsGraph", FakeTradingAgentsGraph)
    monkeypatch.setattr(cli_main, "get_user_selections", lambda **kwargs: selections)
    monkeypatch.setattr(cli_main, "message_buffer", cli_main.MessageBuffer())
    monkeypatch.setattr(cli_main, "Live", _DummyLive)
    monkeypatch.setattr(cli_main, "create_layout", lambda: object())
    monkeypatch.setattr(cli_main, "update_display", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli_main.typer, "prompt", lambda *args, **kwargs: "N")
    monkeypatch.setitem(cli_main.DEFAULT_CONFIG, "results_dir", str(tmp_path / "results"))

    cli_main.run_analysis(checkpoint=False)

    graph = graph_holder["graph"]
    assert graph.resolved_pending == ["NVDA"]
    assert graph.memory_log.context_ticker == "NVDA"
    assert graph.propagator.initial_state_kwargs["past_context"] == "prior resolved context"
    assert graph.propagator.initial_state_kwargs["investor_briefing"] == "Existing position: 500 shares."
    assert graph.memory_log.stored == [
        {
            "ticker": "NVDA",
            "trade_date": "2026-01-10",
            "final_trade_decision": "Rating: Buy\nFinal decision.",
        }
    ]


def test_run_analysis_clears_checkpoint_after_success(monkeypatch, tmp_path):
    import cli.main as cli_main

    calls = {"record": [], "clear": []}
    selections = {
        "ticker": "GC=F",
        "analysis_date": "2026-06-11",
        "asset_type": "stock",
        "investor_briefing": "",
        "research_depth": 1,
        "shallow_thinker": "quick",
        "deep_thinker": "deep",
        "backend_url": "http://localhost",
        "llm_provider": "openai",
        "google_thinking_level": None,
        "openai_reasoning_effort": None,
        "anthropic_effort": None,
        "output_language": "English",
        "analysts": {AnalystType.MARKET},
    }
    final_chunk = {
        "messages": [],
        "market_report": "Market report.",
        "investment_plan": "Investment plan.",
        "trader_investment_plan": "Trader plan.",
        "risk_debate_state": {},
        "final_trade_decision": "Rating: Hold\nFinal decision.",
    }

    class FakeMemoryLog:
        def get_past_context(self, ticker):
            return ""

        def store_decision(self, **kwargs):
            self.stored = kwargs

    class FakePropagator:
        def create_initial_state(self, *args, **kwargs):
            return {"messages": []}

        def get_graph_args(self, callbacks=None):
            return {}

    class FakeTradingAgentsGraph:
        def __init__(self, *args, **kwargs):
            self.memory_log = FakeMemoryLog()
            self.propagator = FakePropagator()

        def _resolve_pending_entries(self, ticker):
            pass

        def resolve_instrument_context(self, ticker, asset_type):
            return f"{asset_type}:{ticker}"

        def process_signal(self, full_signal):
            return "Hold"

    def fake_stream(*args, **kwargs):
        yield final_chunk

    def fake_record(*args, **kwargs):
        calls["record"].append((args, kwargs))

    def fake_clear(*args, **kwargs):
        calls["clear"].append((args, kwargs))

    monkeypatch.setattr(cli_main, "TradingAgentsGraph", FakeTradingAgentsGraph)
    monkeypatch.setattr(cli_main, "get_user_selections", lambda **kwargs: selections)
    monkeypatch.setattr(cli_main, "_stream_with_optional_checkpoint", fake_stream)
    monkeypatch.setattr(cli_main, "record_checkpoint_run", fake_record)
    monkeypatch.setattr(cli_main, "clear_checkpoint", fake_clear)
    monkeypatch.setattr(cli_main, "message_buffer", cli_main.MessageBuffer())
    monkeypatch.setattr(cli_main, "Live", _DummyLive)
    monkeypatch.setattr(cli_main, "create_layout", lambda: object())
    monkeypatch.setattr(cli_main, "update_display", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli_main.typer, "prompt", lambda *args, **kwargs: "N")
    monkeypatch.setitem(cli_main.DEFAULT_CONFIG, "results_dir", str(tmp_path / "results"))
    monkeypatch.setitem(cli_main.DEFAULT_CONFIG, "data_cache_dir", str(tmp_path / "cache"))

    cli_main.run_analysis(checkpoint=True)

    assert calls["record"]
    assert calls["clear"] == [
        ((str(tmp_path / "cache"), "GC=F", "2026-06-11"), {})
    ]
