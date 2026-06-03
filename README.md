TradingAgents: Multi-Agents LLM Financial Trading FrameworkTradingAgents is an open-source, multi-agent financial trading framework built on LangGraph. It mimics a real-world trading firm by orchestrating specialized LLM-powered agents to collaboratively analyze market conditions, debate strategies, and execute trading decisions.⚠️ Disclaimer: This framework is designed for research purposes only. It is not intended as financial, investment, or trading advice.Key Features & Updatesv0.2.5 (Latest): Grounded Sentiment Analyst, expanded model coverage (GPT-5.5, Qwen/GLM/MiniMax dual-region), remote Ollama support, and environment variable configuration.v0.2.4: Structured-output agents, LangGraph checkpoint resume, persistent decision logging, and Docker support.v0.2.0 - v0.2.3: Multi-provider LLM support, multi-language support, backtesting date fidelity, and proxy support.Framework ArchitectureTradingAgents decomposes complex trading tasks into specialized roles:[Analyst Team] ──> [Researcher Team (Debate)] ──> [Trader Agent] ──> [Risk & Portfolio Manager]
Analyst Team:Fundamentals Analyst: Evaluates financial statements and company health.Sentiment Analyst: Measures market mood (News, StockTwits, Reddit).News Analyst: Tracks global macro events and news.Technical Analyst: Utilizes indicators (MACD, RSI) to detect price patterns.Researcher Team: Bullish and bearish agents engage in structured debates to balance risks and gains.Trader Agent: Aggregates research reports to propose trading strategies.Risk & Portfolio Manager: Assesses portfolio volatility, adjusts strategies, and executes orders via simulated exchanges.Installation & Setup1. Local Installationgit clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents

conda create -n tradingagents python=3.13 -y
conda activate tradingagents

pip install .
2. Docker Setupcp .env.example .env  # Add your API keys here
docker compose run --rm tradingagents
3. API ConfigurationSet the API key for your preferred LLM provider in your environment or .env file:export OPENAI_API_KEY=...       # OpenAI (GPT)
export ANTHROPIC_API_KEY=...    # Anthropic (Claude)
export GOOGLE_API_KEY=...       # Google (Gemini)
export DEEPSEEK_API_KEY=...     # DeepSeek
export ALPHA_VANTAGE_API_KEY=...# Market Data (Alpha Vantage)
Supports Azure OpenAI, AWS Bedrock, Ollama (local), OpenRouter, Qwen, GLM, xAI, and MiniMax.UsageCommand Line Interface (CLI)Launch the interactive terminal interface to select tickers, dates, and LLM backbones:tradingagents
Supports Yahoo Finance tickers globally: AAPL (US), 0700.HK (HK), BTC-USD (Crypto), etc.Python Package UsageIntegrate the trading graph directly into your Python workflows:from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# Configuration
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"
config["deep_think_llm"] = "gpt-5.5"
config["quick_think_llm"] = "gpt-5.4-mini"

# Initialize and run
ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("NVDA", "2026-01-15")
print(decision)
Advanced FeaturesState Persistence & ResumeDecision Log: Automatically logs outcomes to ~/.tradingagents/memory/trading_memory.md to help agents reflect on past performance.Checkpoint Resume: Save state after each agent node to resume interrupted runs:tradingagents analyze --checkpoint
Reproducibility NotesLLM outputs can vary due to non-deterministic sampling. To improve reproducibility:Use a fixed analysis date to ground price indicators.Set a lower temperature in your configuration.Use non-reasoning models (e.g., gpt-4.1) for strict execution consistency.Citation & ContributingWe welcome community contributions (bug fixes, documentation, features). If you use this framework in your research, please cite:@misc{xiao2025tradingagentsmultiagentsllmfinancial,
      title={TradingAgents: Multi-Agents LLM Financial Trading Framework}, 
      author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
      year={2025},
      eprint={2412.20138},
      archivePrefix={arXiv},
      primaryClass={q-fin.TR},
      url={https://arxiv.org/abs/2412.20138}, 
}
