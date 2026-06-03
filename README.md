<div align="center">
  <img src="assets/TauricResearch.png" alt="TradingAgents Logo" width="200">
  <h1>TradingAgents</h1>
  <p><b>Multi-Agent LLM Financial Trading Framework</b></p>

  [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
  [![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/downloads/release/python-3130/)
  [![arXiv](https://img.shields.io/badge/arXiv-2412.20138-b31b1b.svg)](https://arxiv.org/abs/2412.20138)
</div>

---

**TradingAgents** is an open-source, multi-agent financial trading framework built on **LangGraph**. It mimics a real-world trading firm by orchestrating specialized LLM-powered agents to collaboratively analyze market conditions, debate strategies, and execute trading decisions.

> [!WARNING]
> This framework is designed for **research purposes only**. It is not intended as financial, investment, or trading advice.

---

## ✨ Key Features

- **🤖 Specialized Agents:** Structured-output agents for fundamentals, sentiment, news, and technical analysis.
- **⚖️ Collaborative Research:** Bullish and bearish agents engage in structured debates to balance risks and gains.
- **🌐 Multi-Model Support:** Native integration with OpenAI, Anthropic, Google Gemini, DeepSeek, Azure, Ollama, and more.
- **🔄 State Persistence:** LangGraph-powered checkpointing allows resuming interrupted runs.
- **📊 Real-time Data:** Seamlessly integrates with Yahoo Finance, Alpha Vantage, and Binance. Supports global tickers like `AAPL` (US), `0700.HK` (HK), and `BTC-USD` (Crypto).
- **🐳 Docker Ready:** Quick deployment using Docker Compose.

---

## 📈 Recent Updates

- **v0.2.5:** Grounded Sentiment Analyst, expanded model coverage (GPT-5.5, Qwen/GLM/MiniMax dual-region), remote Ollama support.
- **v0.2.4:** Structured-output agents, LangGraph checkpoint resume, persistent decision logging.
- **v0.2.0 - v0.2.3:** Multi-provider LLM support, multi-language support, backtesting date fidelity.

---

## 🏗️ Framework Architecture

TradingAgents decomposes complex trading tasks into specialized roles, following a production-grade workflow:

<div align="center">
  <img src="assets/schema.png" alt="Framework Architecture" width="800">
</div>

### 👥 The Team
- **Analyst Team:**
    - **Fundamentals Analyst:** Evaluates financial statements and company health.
    - **Sentiment Analyst:** Measures market mood (News, StockTwits, Reddit).
    - **News Analyst:** Tracks global macro events and news.
    - **Technical Analyst:** Utilizes indicators (MACD, RSI) to detect price patterns.
- **Researcher Team:** Bullish and bearish agents engage in structured debates to balance risks and gains.
- **Trader Agent:** Aggregates research reports to propose trading strategies.
- **Risk & Portfolio Manager:** Assesses portfolio volatility, adjusts strategies, and executes orders via simulated exchanges.

---

## 🚀 Getting Started

### 1. Local Installation
```bash
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents

# Using Conda
conda create -n tradingagents python=3.13 -y
conda activate tradingagents

# Install dependencies
pip install .
```

### 2. Docker Setup
```bash
cp .env.example .env  # Add your API keys here
docker compose run --rm tradingagents
```

### 3. API Configuration
Set your API keys in a `.env` file or export them:
```bash
export OPENAI_API_KEY=your_key
export GOOGLE_API_KEY=your_key
export ALPHA_VANTAGE_API_KEY=your_key
```

---

## 🛠️ Usage

### Command Line Interface (CLI)
Launch the interactive terminal interface to select tickers, dates, and LLM backbones:
```bash
tradingagents
```

<div align="center">
  <img src="assets/cli/cli_init.png" alt="CLI Interface" width="600">
</div>

### Python API
Integrate the trading graph directly into your Python workflows:
```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# Configuration
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"
config["deep_think_llm"] = "gpt-4o"

# Initialize and run
ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("NVDA", "2026-01-15")
print(decision)
```

---

## ⚙️ Advanced Features

- **💾 State Persistence:** Automatically logs outcomes to `~/.tradingagents/memory/trading_memory.md`.
- **⏯️ Checkpoint Resume:** Save state after each agent node to resume interrupted runs:
  ```bash
  tradingagents analyze --checkpoint
  ```
- **🧪 Reproducibility:** Support for fixed analysis dates and low-temperature settings to ground price indicators and ensure consistency.

---

## 📝 Citation & Contributing

We welcome community contributions! If you use this framework in your research, please cite:

```bibtex
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
      title={TradingAgents: Multi-Agents LLM Financial Trading Framework}, 
      author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
      year={2025},
      eprint={2412.20138},
      archivePrefix={arXiv},
      primaryClass={q-fin.TR},
      url={https://arxiv.org/abs/2412.20138}, 
}
```

---
<div align="center">
  Built with ❤️ by <b>Tauric Research</b>
</div>
