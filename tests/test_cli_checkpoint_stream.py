from contextlib import contextmanager


def test_stream_with_checkpoint_resumes_from_saved_step(monkeypatch, tmp_path):
    import cli.main as cli_main

    seen = {}

    class CompiledGraph:
        def stream(self, stream_input, **args):
            seen["stream_input"] = stream_input
            seen["args"] = args
            yield {"messages": []}

    class Workflow:
        def compile(self, checkpointer):
            seen["checkpointer"] = checkpointer
            return CompiledGraph()

    class Graph:
        config = {"data_cache_dir": str(tmp_path)}
        workflow = Workflow()

    @contextmanager
    def fake_get_checkpointer(data_dir, ticker):
        yield "saver"

    monkeypatch.setattr(cli_main, "get_checkpointer", fake_get_checkpointer)
    monkeypatch.setattr(cli_main, "checkpoint_step", lambda *args: 7)
    monkeypatch.setattr(cli_main, "thread_id", lambda ticker, date: "thread-id")

    chunks = list(
        cli_main._stream_with_optional_checkpoint(
            Graph(),
            {"messages": ["fresh input"]},
            {},
            enabled=True,
            ticker="GC=F",
            analysis_date="2026-06-11",
        )
    )

    assert chunks == [{"messages": []}]
    assert seen["stream_input"] is None
    assert seen["args"]["config"]["configurable"]["thread_id"] == "thread-id"


def test_rate_limit_detection():
    import cli.main as cli_main

    class RateLimited(Exception):
        status_code = 429

    assert cli_main._is_rate_limit_error(RateLimited("request rejected"))
    assert cli_main._is_rate_limit_error(Exception("Rate limit exceeded"))
    assert not cli_main._is_rate_limit_error(Exception("unrelated failure"))
