from unittest.mock import MagicMock, patch
import pytest
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

def test_max_retries_config_propagation():
    """Verify that max_retries in config reaches the LLM client kwargs."""
    config = DEFAULT_CONFIG.copy()
    config["max_retries"] = 5
    config["llm_provider"] = "openai"
    
    with patch("tradingagents.graph.trading_graph.create_llm_client") as mock_create:
        # Mock the client and its get_llm method
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        
        # Instantiate the graph, which calls create_llm_client
        TradingAgentsGraph(config=config)
        
        # Verify that create_llm_client was called with max_retries=5
        # It's called twice: once for deep_think_llm and once for quick_think_llm
        assert mock_create.call_count == 2
        
        for call in mock_create.call_args_list:
            _, kwargs = call
            assert kwargs["max_retries"] == 5

def test_max_retries_env_override(monkeypatch):
    """Verify that TRADINGAGENTS_MAX_RETRIES env var overrides DEFAULT_CONFIG."""
    import importlib
    import tradingagents.default_config as dc_module
    
    monkeypatch.setenv("TRADINGAGENTS_MAX_RETRIES", "7")
    importlib.reload(dc_module)
    
    assert dc_module.DEFAULT_CONFIG["max_retries"] == 7
    assert isinstance(dc_module.DEFAULT_CONFIG["max_retries"], int)
