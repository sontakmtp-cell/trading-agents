from typing import Optional
import copy
import os
import datetime
import typer
import questionary
from pathlib import Path
from functools import wraps
from rich.console import Console
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live
from rich.columns import Columns
from rich.markdown import Markdown
from rich.layout import Layout
from rich.text import Text
from rich.table import Table
from collections import deque
import time
from rich.tree import Tree
from rich import box
from rich.align import Align
from rich.rule import Rule

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.graph.analyst_execution import (
    AnalystWallTimeTracker,
    build_analyst_execution_plan,
    get_initial_analyst_node,
    sync_analyst_tracker_from_chunk,
)
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.checkpointer import (
    checkpoint_step,
    clear_checkpoint,
    get_checkpointer,
    list_resumable_checkpoints,
    record_checkpoint_run,
    thread_id,
)
from tradingagents.report_formatting import render_complete_report, save_report_documents
from cli.models import AnalystType
from cli.utils import *
from cli.announcements import fetch_announcements, display_announcements
from cli.stats_handler import StatsCallbackHandler

console = Console()

app = typer.Typer(
    name="TradingAgents",
    help="TradingAgents CLI: Multi-Agents LLM Financial Trading Framework",
    add_completion=True,  # Enable shell completion
)


# Create a deque to store recent messages with a maximum length
class MessageBuffer:
    # Fixed teams that always run (not user-selectable)
    FIXED_AGENTS = {
        "Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
        "Trading Team": ["Trader"],
        "Risk Management": ["Aggressive Analyst", "Neutral Analyst", "Conservative Analyst"],
        "Portfolio Management": ["Portfolio Manager"],
    }

    # Analyst name mapping
    ANALYST_MAPPING = {
        "market": "Market Analyst",
        "social": "Sentiment Analyst",
        "news": "News Analyst",
        "fundamentals": "Fundamentals Analyst",
    }

    # Report section mapping: section -> (analyst_key for filtering, finalizing_agent)
    # analyst_key: which analyst selection controls this section (None = always included)
    # finalizing_agent: which agent must be "completed" for this report to count as done
    REPORT_SECTIONS = {
        "market_report": ("market", "Market Analyst"),
        "sentiment_report": ("social", "Sentiment Analyst"),
        "news_report": ("news", "News Analyst"),
        "fundamentals_report": ("fundamentals", "Fundamentals Analyst"),
        "investment_plan": (None, "Research Manager"),
        "trader_investment_plan": (None, "Trader"),
        "final_trade_decision": (None, "Portfolio Manager"),
    }

    def __init__(self, max_length=100):
        self.messages = deque(maxlen=max_length)
        self.tool_calls = deque(maxlen=max_length)
        self.current_report = None
        self.final_report = None  # Store the complete final report
        self.agent_status = {}
        self.current_agent = None
        self.report_sections = {}
        self.selected_analysts = []
        self.ticker = "TICKER"
        self._processed_message_ids = set()

    def init_for_analysis(self, selected_analysts, ticker="TICKER"):
        """Initialize agent status and report sections based on selected analysts.

        Args:
            selected_analysts: List of analyst type strings (e.g., ["market", "news"])
        """
        self.selected_analysts = [a.lower() for a in selected_analysts]
        self.ticker = ticker

        # Build agent_status dynamically
        self.agent_status = {}

        # Add selected analysts
        for analyst_key in self.selected_analysts:
            if analyst_key in self.ANALYST_MAPPING:
                self.agent_status[self.ANALYST_MAPPING[analyst_key]] = "pending"

        # Add fixed teams
        for team_agents in self.FIXED_AGENTS.values():
            for agent in team_agents:
                self.agent_status[agent] = "pending"

        # Build report_sections dynamically
        self.report_sections = {}
        for section, (analyst_key, _) in self.REPORT_SECTIONS.items():
            if analyst_key is None or analyst_key in self.selected_analysts:
                self.report_sections[section] = None

        # Reset other state
        self.current_report = None
        self.final_report = None
        self.current_agent = None
        self.messages.clear()
        self.tool_calls.clear()
        self._processed_message_ids.clear()

    def get_completed_reports_count(self):
        """Count reports that are finalized (their finalizing agent is completed).

        A report is considered complete when:
        1. The report section has content (not None), AND
        2. The agent responsible for finalizing that report has status "completed"

        This prevents interim updates (like debate rounds) from counting as completed.
        """
        count = 0
        for section in self.report_sections:
            if section not in self.REPORT_SECTIONS:
                continue
            _, finalizing_agent = self.REPORT_SECTIONS[section]
            # Report is complete if it has content AND its finalizing agent is done
            has_content = self.report_sections.get(section) is not None
            agent_done = self.agent_status.get(finalizing_agent) == "completed"
            if has_content and agent_done:
                count += 1
        return count

    def add_message(self, message_type, content):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.messages.append((timestamp, message_type, content))

    def add_tool_call(self, tool_name, args):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.tool_calls.append((timestamp, tool_name, args))

    def update_agent_status(self, agent, status):
        if agent in self.agent_status:
            self.agent_status[agent] = status
            self.current_agent = agent

    def update_report_section(self, section_name, content):
        if section_name in self.report_sections:
            self.report_sections[section_name] = content
            self._update_current_report()

    def _update_current_report(self):
        # For the panel display, only show the most recently updated section
        latest_section = None
        latest_content = None

        # Find the most recently updated section
        for section, content in self.report_sections.items():
            if content is not None:
                latest_section = section
                latest_content = content
               
        if latest_section and latest_content:
            # Format the current section for display
            section_titles = {
                "market_report": "Market Analysis",
                "sentiment_report": "Social Sentiment",
                "news_report": "News Analysis",
                "fundamentals_report": "Fundamentals Analysis",
                "investment_plan": "Research Team Decision",
                "trader_investment_plan": "Trading Team Plan",
                "final_trade_decision": "Portfolio Management Decision",
            }
            self.current_report = (
                f"### {section_titles[latest_section]}\n{latest_content}"
            )

        # Update the final complete report
        self._update_final_report()

    def _update_final_report(self):
        state = dict(self.report_sections)
        state["investment_debate_state"] = {
            "judge_decision": self.report_sections.get("investment_plan") or "",
        }
        state["risk_debate_state"] = {
            "judge_decision": self.report_sections.get("final_trade_decision") or "",
        }
        self.final_report = render_complete_report(state, self.ticker)


message_buffer = MessageBuffer()


def create_layout():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3),
    )
    layout["main"].split_column(
        Layout(name="upper", ratio=3), Layout(name="analysis", ratio=5)
    )
    layout["upper"].split_row(
        Layout(name="progress", ratio=2), Layout(name="messages", ratio=3)
    )
    return layout


def format_tokens(n):
    """Format token count for display."""
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def update_display(layout, spinner_text=None, stats_handler=None, start_time=None):
    # Header with welcome message
    layout["header"].update(
        Panel(
            "[bold green]Welcome to TradingAgents CLI[/bold green]\n"
            "[dim]© [Tauric Research](https://github.com/TauricResearch)[/dim]",
            title="Welcome to TradingAgents",
            border_style="green",
            padding=(1, 2),
            expand=True,
        )
    )

    # Progress panel showing agent status
    progress_table = Table(
        show_header=True,
        header_style="bold magenta",
        show_footer=False,
        box=box.SIMPLE_HEAD,  # Use simple header with horizontal lines
        title=None,  # Remove the redundant Progress title
        padding=(0, 2),  # Add horizontal padding
        expand=True,  # Make table expand to fill available space
    )
    progress_table.add_column("Team", style="cyan", justify="center", width=20)
    progress_table.add_column("Agent", style="green", justify="center", width=20)
    progress_table.add_column("Status", style="yellow", justify="center", width=20)

    # Group agents by team - filter to only include agents in agent_status
    all_teams = {
        "Analyst Team": [
            "Market Analyst",
            "Sentiment Analyst",
            "News Analyst",
            "Fundamentals Analyst",
        ],
        "Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
        "Trading Team": ["Trader"],
        "Risk Management": ["Aggressive Analyst", "Neutral Analyst", "Conservative Analyst"],
        "Portfolio Management": ["Portfolio Manager"],
    }

    # Filter teams to only include agents that are in agent_status
    teams = {}
    for team, agents in all_teams.items():
        active_agents = [a for a in agents if a in message_buffer.agent_status]
        if active_agents:
            teams[team] = active_agents

    for team, agents in teams.items():
        # Add first agent with team name
        first_agent = agents[0]
        status = message_buffer.agent_status.get(first_agent, "pending")
        if status == "in_progress":
            spinner = Spinner(
                "dots", text="[blue]in_progress[/blue]", style="bold cyan"
            )
            status_cell = spinner
        else:
            status_color = {
                "pending": "yellow",
                "completed": "green",
                "error": "red",
            }.get(status, "white")
            status_cell = f"[{status_color}]{status}[/{status_color}]"
        progress_table.add_row(team, first_agent, status_cell)

        # Add remaining agents in team
        for agent in agents[1:]:
            status = message_buffer.agent_status.get(agent, "pending")
            if status == "in_progress":
                spinner = Spinner(
                    "dots", text="[blue]in_progress[/blue]", style="bold cyan"
                )
                status_cell = spinner
            else:
                status_color = {
                    "pending": "yellow",
                    "completed": "green",
                    "error": "red",
                }.get(status, "white")
                status_cell = f"[{status_color}]{status}[/{status_color}]"
            progress_table.add_row("", agent, status_cell)

        # Add horizontal line after each team
        progress_table.add_row("─" * 20, "─" * 20, "─" * 20, style="dim")

    layout["progress"].update(
        Panel(progress_table, title="Progress", border_style="cyan", padding=(1, 2))
    )

    # Messages panel showing recent messages and tool calls
    messages_table = Table(
        show_header=True,
        header_style="bold magenta",
        show_footer=False,
        expand=True,  # Make table expand to fill available space
        box=box.MINIMAL,  # Use minimal box style for a lighter look
        show_lines=True,  # Keep horizontal lines
        padding=(0, 1),  # Add some padding between columns
    )
    messages_table.add_column("Time", style="cyan", width=8, justify="center")
    messages_table.add_column("Type", style="green", width=10, justify="center")
    messages_table.add_column(
        "Content", style="white", no_wrap=False, ratio=1
    )  # Make content column expand

    # Combine tool calls and messages
    all_messages = []

    # Add tool calls
    for timestamp, tool_name, args in message_buffer.tool_calls:
        formatted_args = format_tool_args(args)
        all_messages.append((timestamp, "Tool", f"{tool_name}: {formatted_args}"))

    # Add regular messages
    for timestamp, msg_type, content in message_buffer.messages:
        content_str = str(content) if content else ""
        if len(content_str) > 200:
            content_str = content_str[:197] + "..."
        all_messages.append((timestamp, msg_type, content_str))

    # Sort by timestamp descending (newest first)
    all_messages.sort(key=lambda x: x[0], reverse=True)

    # Calculate how many messages we can show based on available space
    max_messages = 12

    # Get the first N messages (newest ones)
    recent_messages = all_messages[:max_messages]

    # Add messages to table (already in newest-first order)
    for timestamp, msg_type, content in recent_messages:
        # Format content with word wrapping
        wrapped_content = Text(content, overflow="fold")
        messages_table.add_row(timestamp, msg_type, wrapped_content)

    layout["messages"].update(
        Panel(
            messages_table,
            title="Messages & Tools",
            border_style="blue",
            padding=(1, 2),
        )
    )

    # Analysis panel showing current report
    if message_buffer.current_report:
        layout["analysis"].update(
            Panel(
                Markdown(message_buffer.current_report),
                title="Current Report",
                border_style="green",
                padding=(1, 2),
            )
        )
    else:
        layout["analysis"].update(
            Panel(
                "[italic]Waiting for analysis report...[/italic]",
                title="Current Report",
                border_style="green",
                padding=(1, 2),
            )
        )

    # Footer with statistics
    # Agent progress - derived from agent_status dict
    agents_completed = sum(
        1 for status in message_buffer.agent_status.values() if status == "completed"
    )
    agents_total = len(message_buffer.agent_status)

    # Report progress - based on agent completion (not just content existence)
    reports_completed = message_buffer.get_completed_reports_count()
    reports_total = len(message_buffer.report_sections)

    # Build stats parts
    stats_parts = [f"Agents: {agents_completed}/{agents_total}"]

    # LLM and tool stats from callback handler
    if stats_handler:
        stats = stats_handler.get_stats()
        stats_parts.append(f"LLM: {stats['llm_calls']}")
        stats_parts.append(f"Tools: {stats['tool_calls']}")

        # Token display with graceful fallback
        if stats["tokens_in"] > 0 or stats["tokens_out"] > 0:
            tokens_str = f"Tokens: {format_tokens(stats['tokens_in'])}\u2191 {format_tokens(stats['tokens_out'])}\u2193"
        else:
            tokens_str = "Tokens: --"
        stats_parts.append(tokens_str)

    stats_parts.append(f"Reports: {reports_completed}/{reports_total}")

    # Elapsed time
    if start_time:
        elapsed = time.time() - start_time
        elapsed_str = f"\u23f1 {int(elapsed // 60):02d}:{int(elapsed % 60):02d}"
        stats_parts.append(elapsed_str)

    stats_table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
    stats_table.add_column("Stats", justify="center")
    stats_table.add_row(" | ".join(stats_parts))

    layout["footer"].update(Panel(stats_table, border_style="grey50"))


def get_user_selections(checkpoint_enabled: bool = False):
    """Get all user selections before starting the analysis display."""
    # Display ASCII art welcome message
    with open(Path(__file__).parent / "static" / "welcome.txt", "r", encoding="utf-8") as f:
        welcome_ascii = f.read()

    # Create welcome box content
    welcome_content = f"{welcome_ascii}\n"
    welcome_content += "[bold green]TradingAgents: Multi-Agents LLM Financial Trading Framework - CLI[/bold green]\n\n"
    welcome_content += "[bold]Workflow Steps:[/bold]\n"
    welcome_content += "I. Analyst Team → II. Research Team → III. Trader → IV. Risk Management → V. Portfolio Management\n\n"
    welcome_content += (
        "[dim]Built by [Tauric Research](https://github.com/TauricResearch)[/dim]"
    )

    # Create and center the welcome box
    welcome_box = Panel(
        welcome_content,
        border_style="green",
        padding=(1, 2),
        title="Welcome to TradingAgents",
        subtitle="Multi-Agents LLM Financial Trading Framework",
    )
    console.print(Align.center(welcome_box))
    console.print()
    console.print()  # Add vertical space before announcements

    # Fetch and display announcements (silent on failure)
    announcements = fetch_announcements()
    display_announcements(console, announcements)

    # Create a boxed questionnaire for each step
    def create_question_box(title, prompt, default=None):
        box_content = f"[bold]{title}[/bold]\n"
        box_content += f"[dim]{prompt}[/dim]"
        if default:
            box_content += f"\n[dim]Default: {default}[/dim]"
        return Panel(box_content, border_style="blue", padding=(1, 2))

    default_date = datetime.datetime.now().strftime("%Y-%m-%d")
    resume_checkpoint = None
    resumable = []
    if checkpoint_enabled:
        resumable = list_resumable_checkpoints(DEFAULT_CONFIG["data_cache_dir"])
    if resumable:
        choices = [
            questionary.Choice(
                f"Resume {item['ticker']} on {item['date']} (step {item.get('step', '?')})",
                value=item,
            )
            for item in resumable
        ]
        choices.append(questionary.Choice("Start a new analysis", value="__NEW__"))
        selected_resume = questionary.select(
            "Unfinished checkpoint found. What do you want to do?",
            choices=choices,
            instruction="\n- Choose a checkpoint to continue, or start fresh",
        ).ask()
        if isinstance(selected_resume, dict):
            resume_checkpoint = selected_resume
            analysts = resume_checkpoint.get("selected_analysts") or ["market"]
            analyst_labels = ", ".join(analysts)
            console.print(
                Panel(
                    "\n".join(
                        [
                            f"Ticker: {resume_checkpoint['ticker']}",
                            f"Date: {resume_checkpoint['date']}",
                            f"Saved step: {resume_checkpoint.get('step', '?')}",
                            f"Analysts: {analyst_labels}",
                            "Next: choose provider/model; you may switch away from the rate-limited provider.",
                        ]
                    ),
                    title="Resume Checkpoint",
                    border_style="yellow",
                )
            )
        else:
            resume_checkpoint = None

    # State machine variables
    selected_ticker = resume_checkpoint["ticker"] if resume_checkpoint else "SPY"
    asset_type = (
        detect_asset_type(selected_ticker)
        if resume_checkpoint
        else AssetType.STOCK
    )
    analysis_date = resume_checkpoint["date"] if resume_checkpoint else default_date
    output_language = (
        resume_checkpoint.get("output_language", "English")
        if resume_checkpoint
        else "English"
    )
    resume_analysts = resume_checkpoint.get("selected_analysts") if resume_checkpoint else []
    if resume_checkpoint and not resume_analysts:
        resume_analysts = ["market"]
    selected_analysts = [
        AnalystType(a)
        for a in resume_analysts
    ] if resume_checkpoint else []
    selected_research_depth = resume_checkpoint.get("research_depth", 1) if resume_checkpoint else 3
    selected_llm_provider = "google"
    backend_url = None
    selected_shallow_thinker = None
    selected_deep_thinker = None
    thinking_level = None
    reasoning_effort = None
    anthropic_effort = None
    investor_briefing = ""

    env_configured_run = (
        bool(os.environ.get("TRADINGAGENTS_LLM_PROVIDER"))
        and bool(os.environ.get("TRADINGAGENTS_OUTPUT_LANGUAGE"))
        and (
            bool(os.environ.get("TRADINGAGENTS_QUICK_THINK_LLM"))
            or bool(os.environ.get("TRADINGAGENTS_DEEP_THINK_LLM"))
        )
    )

    if resume_checkpoint:
        active_steps = [
            "PROVIDER",
            "THINKING_AGENTS",
            "PROVIDER_CONFIG",
        ]
    else:
        active_steps = [
            "TICKER",
            "DATE",
            "LANGUAGE",
            "ANALYSTS",
            "DEPTH",
            "PROVIDER",
            "THINKING_AGENTS",
            "PROVIDER_CONFIG",
        ]
        if not env_configured_run:
            active_steps.append("BRIEFING")

    current_idx = 0
    direction = 1  # 1 for forward, -1 for backward

    while current_idx < len(active_steps):
        step_name = active_steps[current_idx]

        if step_name == "TICKER":
            console.print(
                create_question_box(
                    "Step 1: Ticker Symbol",
                    "Enter the ticker, with exchange suffix when needed (e.g. SPY, 0700.HK, BTCUSDT)",
                    "SPY",
                )
            )
            selected_ticker = get_ticker()
            if not selected_ticker or selected_ticker == "__BACK__":
                console.print("\n[red]No ticker symbol provided. Exiting...[/red]")
                exit(1)
            asset_type = detect_asset_type(selected_ticker)
            if asset_type.value != "stock":
                console.print(
                    f"[green]Detected asset type:[/green] {asset_type.value}"
                )
            direction = 1
            current_idx += direction

        elif step_name == "DATE":
            console.print(
                create_question_box(
                    "Step 2: Analysis Date",
                    "Enter the analysis date (YYYY-MM-DD)",
                    default_date,
                )
            )
            res = get_analysis_date()
            if res == "__BACK__":
                direction = -1
                current_idx += direction
                continue
            analysis_date = res
            direction = 1
            current_idx += direction

        elif step_name == "LANGUAGE":
            if os.environ.get("TRADINGAGENTS_OUTPUT_LANGUAGE"):
                output_language = DEFAULT_CONFIG["output_language"]
                console.print(
                    f"[green]✓ Output language from environment:[/green] {output_language}"
                )
                current_idx += direction
                continue

            console.print(
                create_question_box(
                    "Step 3: Output Language",
                    "Select the language for analyst reports and final decision"
                )
            )
            res = ask_output_language()
            if res == "__BACK__":
                direction = -1
                current_idx += direction
                continue
            output_language = res
            direction = 1
            current_idx += direction

        elif step_name == "ANALYSTS":
            console.print(
                create_question_box(
                    "Step 4: Analysts Team", "Select your LLM analyst agents for the analysis"
                )
            )
            res = select_analysts(asset_type)
            if res == "__BACK__":
                direction = -1
                current_idx += direction
                continue
            selected_analysts = res
            console.print(
                f"[green]Selected analysts:[/green] {', '.join(analyst.value for analyst in selected_analysts)}"
            )
            direction = 1
            current_idx += direction

        elif step_name == "DEPTH":
            console.print(
                create_question_box(
                    "Step 5: Research Depth", "Select your research depth level"
                )
            )
            res = select_research_depth()
            if res == "__BACK__":
                direction = -1
                current_idx += direction
                continue
            selected_research_depth = res
            direction = 1
            current_idx += direction

        elif step_name == "PROVIDER":
            provider_from_env = bool(os.environ.get("TRADINGAGENTS_LLM_PROVIDER")) and not resume_checkpoint
            if provider_from_env:
                selected_llm_provider = DEFAULT_CONFIG["llm_provider"].lower()
                backend_url = DEFAULT_CONFIG["backend_url"] or provider_default_url(selected_llm_provider)
                console.print(f"[green]✓ LLM provider from environment:[/green] {selected_llm_provider}")
                console.print(f"[green]✓ Backend URL:[/green] {backend_url}")
                ensure_api_key(selected_llm_provider)
                current_idx += direction
                continue

            provider_ok = False
            while not provider_ok:
                console.print(
                    create_question_box(
                        "Step 6: LLM Provider", "Select your LLM provider"
                    )
                )
                res = select_llm_provider()
                if res == "__BACK__":
                    direction = -1
                    break

                prov, url = res

                region_back = False
                if prov == "qwen":
                    res_region = ask_qwen_region()
                    if res_region == "__BACK__":
                        region_back = True
                    else:
                        prov, url = res_region
                elif prov == "minimax":
                    res_region = ask_minimax_region()
                    if res_region == "__BACK__":
                        region_back = True
                    else:
                        prov, url = res_region
                elif prov == "glm":
                    res_region = ask_glm_region()
                    if res_region == "__BACK__":
                        region_back = True
                    else:
                        prov, url = res_region
                elif prov == "ollama":
                    confirm_ollama_endpoint(url)

                if region_back:
                    continue

                api_key = ensure_api_key(prov)
                api_key_env = get_api_key_env(prov)
                if api_key is None and api_key_env and not os.environ.get(api_key_env):
                    continue

                selected_llm_provider = prov
                backend_url = url
                provider_ok = True
                direction = 1

            if not provider_ok:
                current_idx += direction
                continue

            current_idx += direction

        elif step_name == "THINKING_AGENTS":
            if (
                not resume_checkpoint
                and (
                    os.environ.get("TRADINGAGENTS_QUICK_THINK_LLM")
                    or os.environ.get("TRADINGAGENTS_DEEP_THINK_LLM")
                )
            ):
                selected_shallow_thinker = DEFAULT_CONFIG["quick_think_llm"]
                selected_deep_thinker = DEFAULT_CONFIG["deep_think_llm"]
                console.print(
                    f"[green]✓ Thinking agents from environment:[/green] "
                    f"quick={selected_shallow_thinker}, deep={selected_deep_thinker}"
                )
                current_idx += direction
                continue

            agents_ok = False
            while not agents_ok:
                console.print(
                    create_question_box(
                        "Step 7: Thinking Agents", "Select your thinking agents for analysis"
                    )
                )
                res_shallow = select_shallow_thinking_agent(selected_llm_provider)
                if res_shallow == "__BACK__":
                    direction = -1
                    break

                res_deep = select_deep_thinking_agent(selected_llm_provider)
                if res_deep == "__BACK__":
                    continue

                selected_shallow_thinker = res_shallow
                selected_deep_thinker = res_deep
                agents_ok = True
                direction = 1

            if not agents_ok:
                current_idx += direction
                continue

            current_idx += direction

        elif step_name == "PROVIDER_CONFIG":
            provider_from_env = bool(os.environ.get("TRADINGAGENTS_LLM_PROVIDER")) and not resume_checkpoint
            if provider_from_env:
                thinking_level = DEFAULT_CONFIG["google_thinking_level"]
                reasoning_effort = DEFAULT_CONFIG["openai_reasoning_effort"]
                anthropic_effort = DEFAULT_CONFIG["anthropic_effort"]
                current_idx += direction
                continue

            provider_lower = selected_llm_provider.lower()
            if provider_lower == "google":
                console.print(
                    create_question_box(
                        "Step 8: Thinking Mode",
                        "Configure Gemini thinking mode"
                    )
                )
                res = ask_gemini_thinking_config()
                if res == "__BACK__":
                    direction = -1
                    current_idx += direction
                    continue
                thinking_level = res
                direction = 1
            elif provider_lower == "openai":
                console.print(
                    create_question_box(
                        "Step 8: Reasoning Effort",
                        "Configure OpenAI reasoning effort level"
                    )
                )
                res = ask_openai_reasoning_effort()
                if res == "__BACK__":
                    direction = -1
                    current_idx += direction
                    continue
                reasoning_effort = res
                direction = 1
            elif provider_lower == "anthropic":
                console.print(
                    create_question_box(
                        "Step 8: Effort Level",
                        "Configure Claude effort level"
                    )
                )
                res = ask_anthropic_effort()
                if res == "__BACK__":
                    direction = -1
                    current_idx += direction
                    continue
                anthropic_effort = res
                direction = 1
            else:
                current_idx += direction
                continue

            current_idx += direction

        elif step_name == "BRIEFING":
            add_briefing = questionary.confirm(
                "Add investor briefing? (positions, thesis, constraints)",
                default=False,
            ).ask()

            if add_briefing is None:
                direction = -1
                current_idx += direction
                continue

            if add_briefing:
                briefing_method = questionary.select(
                    "How would you like to provide the briefing?",
                    choices=[
                        questionary.Choice("<- Back to previous step", value="__BACK__"),
                        "Type directly in terminal",
                        "Load from file",
                    ],
                ).ask()

                if briefing_method is None or briefing_method == "__BACK__":
                    direction = -1
                    current_idx += direction
                    continue

                if briefing_method == "Load from file":
                    briefing_path = questionary.path(
                        "Path to briefing file (.md or .txt):",
                    ).ask()
                    if briefing_path is None or briefing_path.strip().lower() in ("back", "b", "<"):
                        direction = -1
                        current_idx += direction
                        continue

                    try:
                        with open(briefing_path, "r", encoding="utf-8") as f:
                            investor_briefing = f.read().strip()
                    except Exception as e:
                        console.print(f"[red]Error loading file: {e}[/red]")
                        continue
                else:
                    console.print(
                        "[dim]Enter your briefing below. "
                        "Press Enter twice on an empty line to finish (or type 'back' on a line by itself to go back).[/dim]"
                    )
                    lines = []
                    empty_count = 0
                    user_cancelled = False
                    while True:
                        line = input()
                        if line.strip().lower() == "back":
                            user_cancelled = True
                            break
                        if line == "":
                            empty_count += 1
                            if empty_count >= 2:
                                break
                            lines.append("")
                        else:
                            empty_count = 0
                            lines.append(line)

                    if user_cancelled:
                        direction = -1
                        current_idx += direction
                        continue

                    investor_briefing = "\n".join(lines).strip()
            else:
                investor_briefing = ""

            if investor_briefing:
                console.print(
                    Panel(
                        Markdown(investor_briefing),
                        title="Investor Briefing",
                        subtitle="[dim]Internal context; may appear in generated reports[/dim]",
                        border_style="yellow",
                    )
                )

            direction = 1
            current_idx += direction

    return {
        "ticker": selected_ticker,
        "asset_type": asset_type.value,
        "analysis_date": analysis_date,
        "investor_briefing": investor_briefing,
        "analysts": selected_analysts,
        "research_depth": selected_research_depth,
        "llm_provider": selected_llm_provider.lower(),
        "backend_url": backend_url,
        "shallow_thinker": selected_shallow_thinker,
        "deep_thinker": selected_deep_thinker,
        "google_thinking_level": thinking_level,
        "openai_reasoning_effort": reasoning_effort,
        "anthropic_effort": anthropic_effort,
        "output_language": output_language,
        "resume_checkpoint": bool(resume_checkpoint),
    }


def get_analysis_date():
    """Get the analysis date from user input."""
    while True:
        date_str = typer.prompt(
            "Enter the analysis date (YYYY-MM-DD) (or type 'back' to go back)", default=datetime.datetime.now().strftime("%Y-%m-%d")
        )
        if date_str.strip().lower() in ("back", "b", "<"):
            return "__BACK__"
        try:
            # Validate date format and ensure it's not in the future
            analysis_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            if analysis_date.date() > datetime.datetime.now().date():
                console.print("[red]Error: Analysis date cannot be in the future[/red]")
                continue
            return date_str
        except ValueError:
            console.print(
                "[red]Error: Invalid date format. Please use YYYY-MM-DD[/red]"
            )


def save_report_to_disk(final_state, ticker: str, save_path: Path):
    """Save complete analysis report to disk with organized subfolders."""
    return save_report_documents(final_state, ticker, save_path)


def display_complete_report(final_state, ticker=None):
    """Display the complete analysis report sequentially (avoids truncation)."""
    console.print()
    console.print(Rule("Complete Analysis Report", style="bold green"))
    report_ticker = str(ticker or final_state.get("company_of_interest", "TICKER"))
    console.print(Markdown(render_complete_report(final_state, report_ticker)))


def update_research_team_status(status):
    """Update status for research team members (not Trader)."""
    research_team = ["Bull Researcher", "Bear Researcher", "Research Manager"]
    for agent in research_team:
        message_buffer.update_agent_status(agent, status)


# Ordered list of analysts for status transitions
ANALYST_ORDER = ["market", "social", "news", "fundamentals"]
ANALYST_AGENT_NAMES = {
    "market": "Market Analyst",
    "social": "Sentiment Analyst",
    "news": "News Analyst",
    "fundamentals": "Fundamentals Analyst",
}
ANALYST_REPORT_MAP = {
    "market": "market_report",
    "social": "sentiment_report",
    "news": "news_report",
    "fundamentals": "fundamentals_report",
}


def update_analyst_statuses(message_buffer, chunk, wall_time_tracker=None):
    """Update analyst statuses based on accumulated report state.

    Logic:
    - Store new report content from the current chunk if present
    - Check accumulated report_sections (not just current chunk) for status
    - Analysts with reports = completed
    - First analyst without report = in_progress
    - Remaining analysts without reports = pending
    - When all analysts done, set Bull Researcher to in_progress
    """
    selected = message_buffer.selected_analysts
    found_active = False

    if wall_time_tracker is not None:
        sync_analyst_tracker_from_chunk(wall_time_tracker, chunk)

    for analyst_key in ANALYST_ORDER:
        if analyst_key not in selected:
            continue

        agent_name = ANALYST_AGENT_NAMES[analyst_key]
        report_key = ANALYST_REPORT_MAP[analyst_key]

        # Capture new report content from current chunk
        if chunk.get(report_key):
            message_buffer.update_report_section(report_key, chunk[report_key])

        # Determine status from accumulated sections, not just current chunk
        has_report = bool(message_buffer.report_sections.get(report_key))

        if has_report:
            message_buffer.update_agent_status(agent_name, "completed")
        elif not found_active:
            message_buffer.update_agent_status(agent_name, "in_progress")
            found_active = True
        else:
            message_buffer.update_agent_status(agent_name, "pending")

    # When all analysts complete, transition research team to in_progress
    if not found_active and selected:
        if message_buffer.agent_status.get("Bull Researcher") == "pending":
            message_buffer.update_agent_status("Bull Researcher", "in_progress")

def extract_content_string(content):
    """Extract string content from various message formats.
    Returns None if no meaningful text content is found.
    """
    import ast

    def is_empty(val):
        """Check if value is empty using Python's truthiness."""
        if val is None or val == '':
            return True
        if isinstance(val, str):
            s = val.strip()
            if not s:
                return True
            try:
                return not bool(ast.literal_eval(s))
            except (ValueError, SyntaxError):
                return False  # Can't parse = real text
        return not bool(val)

    if is_empty(content):
        return None

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, dict):
        text = content.get('text', '')
        return text.strip() if not is_empty(text) else None

    if isinstance(content, list):
        text_parts = [
            item.get('text', '').strip() if isinstance(item, dict) and item.get('type') == 'text'
            else (item.strip() if isinstance(item, str) else '')
            for item in content
        ]
        result = ' '.join(t for t in text_parts if t and not is_empty(t))
        return result if result else None

    return str(content).strip() if not is_empty(content) else None


def classify_message_type(message) -> tuple[str, str | None]:
    """Classify LangChain message into display type and extract content.

    Returns:
        (type, content) - type is one of: User, Agent, Data, Control
                        - content is extracted string or None
    """
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    content = extract_content_string(getattr(message, 'content', None))

    if isinstance(message, HumanMessage):
        if content and content.strip() == "Continue":
            return ("Control", content)
        return ("User", content)

    if isinstance(message, ToolMessage):
        return ("Data", content)

    if isinstance(message, AIMessage):
        return ("Agent", content)

    # Fallback for unknown types
    return ("System", content)


def format_tool_args(args, max_length=80) -> str:
    """Format tool arguments for terminal display."""
    result = str(args)
    if len(result) > max_length:
        return result[:max_length - 3] + "..."
    return result


def _stream_with_optional_checkpoint(
    graph,
    init_agent_state,
    args,
    *,
    enabled: bool,
    ticker: str,
    analysis_date: str,
):
    """Stream the CLI graph, resuming completed nodes when enabled."""
    if not enabled:
        yield from graph.graph.stream(init_agent_state, **args)
        return

    with get_checkpointer(graph.config["data_cache_dir"], ticker) as saver:
        checkpointed_graph = graph.workflow.compile(checkpointer=saver)
        step = checkpoint_step(graph.config["data_cache_dir"], ticker, analysis_date)
        stream_input = None if step is not None else init_agent_state
        args.setdefault("config", {}).setdefault("configurable", {})["thread_id"] = (
            thread_id(ticker, analysis_date)
        )
        if step is not None:
            console.print(
                f"[yellow]Resuming saved analysis from checkpoint step {step}.[/yellow]"
            )
        yield from checkpointed_graph.stream(stream_input, **args)


def _is_rate_limit_error(exc: Exception) -> bool:
    """Return True for provider HTTP 429/rate-limit failures."""
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True
    response = getattr(exc, "response", None)
    if getattr(response, "status_code", None) == 429:
        return True
    return "rate limit" in str(exc).lower()


def run_analysis(checkpoint: bool = False):
    # First get all user selections
    selections = get_user_selections(checkpoint_enabled=checkpoint)

    # Create config with selected research depth
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["max_debate_rounds"] = selections["research_depth"]
    config["max_risk_discuss_rounds"] = selections["research_depth"]
    config["quick_think_llm"] = selections["shallow_thinker"]
    config["deep_think_llm"] = selections["deep_thinker"]
    config["backend_url"] = selections["backend_url"]
    config["llm_provider"] = selections["llm_provider"].lower()
    # Provider-specific thinking configuration
    config["google_thinking_level"] = selections.get("google_thinking_level")
    config["openai_reasoning_effort"] = selections.get("openai_reasoning_effort")
    config["anthropic_effort"] = selections.get("anthropic_effort")
    config["output_language"] = selections.get("output_language", "English")
    config["checkpoint_enabled"] = checkpoint
    if selections["asset_type"] == "crypto":
        config["data_vendors"]["core_stock_apis"] = "binance"
        config["data_vendors"]["technical_indicators"] = "binance"
    if checkpoint:
        record_checkpoint_run(
            config["data_cache_dir"],
            selections["ticker"],
            selections["analysis_date"],
            asset_type=selections["asset_type"],
            selected_analysts=[analyst.value for analyst in selections["analysts"]],
            research_depth=selections["research_depth"],
            output_language=selections.get("output_language", "English"),
        )

    # Create stats callback handler for tracking LLM/tool calls
    stats_handler = StatsCallbackHandler()

    # Normalize analyst selection to predefined order (selection is a 'set', order is fixed)
    selected_set = {analyst.value for analyst in selections["analysts"]}
    selected_analyst_keys = [a for a in ANALYST_ORDER if a in selected_set]
    analyst_execution_plan = build_analyst_execution_plan(
        selected_analyst_keys,
        concurrency_limit=config["analyst_concurrency_limit"],
    )
    analyst_wall_time_tracker = AnalystWallTimeTracker(analyst_execution_plan)

    # Initialize the graph with callbacks bound to LLMs
    graph = TradingAgentsGraph(
        selected_analyst_keys,
        config=config,
        debug=True,
        callbacks=[stats_handler],
    )

    # Initialize message buffer with selected analysts
    message_buffer.init_for_analysis(selected_analyst_keys, selections["ticker"])

    # Track start time for elapsed display
    start_time = time.time()

    # Create result directory
    results_dir = Path(config["results_dir"]) / selections["ticker"] / selections["analysis_date"]
    results_dir.mkdir(parents=True, exist_ok=True)
    report_dir = results_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    log_file = results_dir / "message_tool.log"
    log_file.touch(exist_ok=True)

    def save_message_decorator(obj, func_name):
        func = getattr(obj, func_name)
        @wraps(func)
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            timestamp, message_type, content = obj.messages[-1]
            content = content.replace("\n", " ")  # Replace newlines with spaces
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} [{message_type}] {content}\n")
        return wrapper
    
    def save_tool_call_decorator(obj, func_name):
        func = getattr(obj, func_name)
        @wraps(func)
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            timestamp, tool_name, args = obj.tool_calls[-1]
            args_str = ", ".join(f"{k}={v}" for k, v in args.items())
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} [Tool Call] {tool_name}({args_str})\n")
        return wrapper

    def save_report_section_decorator(obj, func_name):
        func = getattr(obj, func_name)
        @wraps(func)
        def wrapper(section_name, content):
            func(section_name, content)
            if section_name in obj.report_sections and obj.report_sections[section_name] is not None:
                content = obj.report_sections[section_name]
                if content:
                    file_name = f"{section_name}.md"
                    text = "\n".join(str(item) for item in content) if isinstance(content, list) else content
                    with open(report_dir / file_name, "w", encoding="utf-8") as f:
                        f.write(text)
        return wrapper

    message_buffer.add_message = save_message_decorator(message_buffer, "add_message")
    message_buffer.add_tool_call = save_tool_call_decorator(message_buffer, "add_tool_call")
    message_buffer.update_report_section = save_report_section_decorator(message_buffer, "update_report_section")

    # Memory Log: resolve pending outcomes before this run, matching propagate().
    message_buffer.add_message("System", "Resolving prior pending decisions...")
    graph._resolve_pending_entries(selections["ticker"])

    # Now start the display layout
    layout = create_layout()

    with Live(layout, refresh_per_second=4) as live:
        # Initial display
        update_display(layout, stats_handler=stats_handler, start_time=start_time)

        # Add initial messages
        message_buffer.add_message("System", f"Selected ticker: {selections['ticker']}")
        if selections["asset_type"] != "stock":
            message_buffer.add_message("System", f"Detected asset type: {selections['asset_type']}")
        message_buffer.add_message(
            "System", f"Analysis date: {selections['analysis_date']}"
        )
        message_buffer.add_message(
            "System",
            f"Selected analysts: {', '.join(analyst.value for analyst in selections['analysts'])}",
        )
        update_display(layout, stats_handler=stats_handler, start_time=start_time)

        # Update agent status to in_progress for the first analyst
        first_analyst = get_initial_analyst_node(analyst_execution_plan)
        message_buffer.update_agent_status(first_analyst, "in_progress")
        analyst_wall_time_tracker.mark_started(selected_analyst_keys[0])
        update_display(layout, stats_handler=stats_handler, start_time=start_time)

        # Create spinner text
        spinner_text = (
            f"Analyzing {selections['ticker']} on {selections['analysis_date']}..."
        )
        update_display(layout, spinner_text, stats_handler=stats_handler, start_time=start_time)

        # Initialize state and get graph args with callbacks.
        # Resolve the instrument identity once here so all agents anchor to
        # the real company (#814); the CLI builds state directly rather than
        # going through propagate(), so this must happen on the CLI path too.
        instrument_context = graph.resolve_instrument_context(
            selections["ticker"], selections["asset_type"]
        )
        past_context = graph.memory_log.get_past_context(selections["ticker"])
        init_agent_state = graph.propagator.create_initial_state(
            selections["ticker"],
            selections["analysis_date"],
            asset_type=selections["asset_type"],
            past_context=past_context,
            instrument_context=instrument_context,
            investor_briefing=selections.get("investor_briefing", ""),
        )
        # Pass callbacks to graph config for tool execution tracking
        # (LLM tracking is handled separately via LLM constructor)
        args = graph.propagator.get_graph_args(callbacks=[stats_handler])

        # Stream the analysis
        trace = []
        for chunk in _stream_with_optional_checkpoint(
            graph,
            init_agent_state,
            args,
            enabled=checkpoint,
            ticker=selections["ticker"],
            analysis_date=selections["analysis_date"],
        ):
            # Process all messages in chunk, deduplicating by message ID
            for message in chunk.get("messages", []):
                msg_id = getattr(message, "id", None)
                if msg_id is not None:
                    if msg_id in message_buffer._processed_message_ids:
                        continue
                    message_buffer._processed_message_ids.add(msg_id)

                msg_type, content = classify_message_type(message)
                if content and content.strip():
                    message_buffer.add_message(msg_type, content)

                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tool_call in message.tool_calls:
                        if isinstance(tool_call, dict):
                            message_buffer.add_tool_call(tool_call["name"], tool_call["args"])
                        else:
                            message_buffer.add_tool_call(tool_call.name, tool_call.args)

            # Update analyst statuses based on report state (runs on every chunk)
            update_analyst_statuses(
                message_buffer,
                chunk,
                wall_time_tracker=analyst_wall_time_tracker,
            )

            # Research Team - Handle Investment Debate State
            if chunk.get("investment_debate_state"):
                debate_state = chunk["investment_debate_state"]
                bull_hist = debate_state.get("bull_history", "").strip()
                bear_hist = debate_state.get("bear_history", "").strip()
                judge = debate_state.get("judge_decision", "").strip()

                # Only update status when there's actual content
                if bull_hist or bear_hist:
                    update_research_team_status("in_progress")
                if bull_hist:
                    message_buffer.update_report_section(
                        "investment_plan", f"### Bull Researcher Analysis\n{bull_hist}"
                    )
                if bear_hist:
                    message_buffer.update_report_section(
                        "investment_plan", f"### Bear Researcher Analysis\n{bear_hist}"
                    )
                if judge:
                    message_buffer.update_report_section(
                        "investment_plan", f"### Research Manager Decision\n{judge}"
                    )
                    update_research_team_status("completed")
                    message_buffer.update_agent_status("Trader", "in_progress")

            # Trading Team
            if chunk.get("trader_investment_plan"):
                message_buffer.update_report_section(
                    "trader_investment_plan", chunk["trader_investment_plan"]
                )
                if message_buffer.agent_status.get("Trader") != "completed":
                    message_buffer.update_agent_status("Trader", "completed")
                    message_buffer.update_agent_status("Aggressive Analyst", "in_progress")

            # Risk Management Team - Handle Risk Debate State
            if chunk.get("risk_debate_state"):
                risk_state = chunk["risk_debate_state"]
                agg_hist = risk_state.get("aggressive_history", "").strip()
                con_hist = risk_state.get("conservative_history", "").strip()
                neu_hist = risk_state.get("neutral_history", "").strip()
                judge = risk_state.get("judge_decision", "").strip()

                if agg_hist:
                    if message_buffer.agent_status.get("Aggressive Analyst") != "completed":
                        message_buffer.update_agent_status("Aggressive Analyst", "in_progress")
                    message_buffer.update_report_section(
                        "final_trade_decision", f"### Aggressive Analyst Analysis\n{agg_hist}"
                    )
                if con_hist:
                    if message_buffer.agent_status.get("Conservative Analyst") != "completed":
                        message_buffer.update_agent_status("Conservative Analyst", "in_progress")
                    message_buffer.update_report_section(
                        "final_trade_decision", f"### Conservative Analyst Analysis\n{con_hist}"
                    )
                if neu_hist:
                    if message_buffer.agent_status.get("Neutral Analyst") != "completed":
                        message_buffer.update_agent_status("Neutral Analyst", "in_progress")
                    message_buffer.update_report_section(
                        "final_trade_decision", f"### Neutral Analyst Analysis\n{neu_hist}"
                    )
                if judge:
                    if message_buffer.agent_status.get("Portfolio Manager") != "completed":
                        message_buffer.update_agent_status("Portfolio Manager", "in_progress")
                        message_buffer.update_report_section(
                            "final_trade_decision", f"### Portfolio Manager Decision\n{judge}"
                        )
                        message_buffer.update_agent_status("Aggressive Analyst", "completed")
                        message_buffer.update_agent_status("Conservative Analyst", "completed")
                        message_buffer.update_agent_status("Neutral Analyst", "completed")
                        message_buffer.update_agent_status("Portfolio Manager", "completed")

            # Update the display
            update_display(layout, stats_handler=stats_handler, start_time=start_time)

            trace.append(chunk)

        # Streamed chunks are per-node deltas, not full state. Merge them
        # so every report field populated across the run is present.
        final_state = {}
        for chunk in trace:
            final_state.update(chunk)
        decision = graph.process_signal(final_state["final_trade_decision"])
        graph.memory_log.store_decision(
            ticker=selections["ticker"],
            trade_date=selections["analysis_date"],
            final_trade_decision=final_state["final_trade_decision"],
        )
        if checkpoint:
            clear_checkpoint(
                config["data_cache_dir"],
                selections["ticker"],
                selections["analysis_date"],
            )

        # Update all agent statuses to completed
        for agent in message_buffer.agent_status:
            message_buffer.update_agent_status(agent, "completed")

        message_buffer.add_message(
            "System", f"Completed analysis for {selections['analysis_date']}"
        )
        message_buffer.add_message("System", analyst_wall_time_tracker.format_summary())

        # Update final report sections
        for section in message_buffer.report_sections.keys():
            if section in final_state:
                message_buffer.update_report_section(section, final_state[section])

        update_display(layout, stats_handler=stats_handler, start_time=start_time)

    # Post-analysis prompts (outside Live context for clean interaction)
    console.print("\n[bold cyan]Analysis Complete![/bold cyan]\n")
    console.print(f"[dim]{analyst_wall_time_tracker.format_summary()}[/dim]")

    # Prompt to save report
    save_choice = typer.prompt("Save report?", default="Y").strip().upper()
    if save_choice in ("Y", "YES", ""):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = Path.cwd() / "reports" / f"{selections['ticker']}_{timestamp}"
        save_path_str = typer.prompt(
            "Save path (press Enter for default)",
            default=str(default_path)
        ).strip()
        save_path = Path(save_path_str)
        try:
            report_file = save_report_to_disk(final_state, selections["ticker"], save_path)
            console.print(f"\n[green]✓ Report saved to:[/green] {save_path.resolve()}")
            console.print(f"  [dim]Complete report:[/dim] {report_file.name}")
        except Exception as e:
            console.print(f"[red]Error saving report: {e}[/red]")

    # Prompt to display full report
    display_choice = typer.prompt("\nDisplay full report on screen?", default="Y").strip().upper()
    if display_choice in ("Y", "YES", ""):
        display_complete_report(final_state, selections["ticker"])


@app.command()
def analyze(
    checkpoint: bool = typer.Option(
        False,
        "--checkpoint",
        help="Enable checkpoint/resume: save state after each node so a crashed run can resume.",
    ),
    clear_checkpoints: bool = typer.Option(
        False,
        "--clear-checkpoints",
        help="Delete all saved checkpoints before running (force fresh start).",
    ),
):
    if clear_checkpoints:
        from tradingagents.graph.checkpointer import clear_all_checkpoints
        n = clear_all_checkpoints(DEFAULT_CONFIG["data_cache_dir"])
        console.print(f"[yellow]Cleared {n} checkpoint(s).[/yellow]")
    try:
        run_analysis(checkpoint=checkpoint)
    except Exception as exc:
        if not _is_rate_limit_error(exc):
            raise
        console.print(
            "\n[bold red]The AI provider rejected the request because its rate limit was reached.[/bold red]"
        )
        console.print(
            "[yellow]Wait for the provider quota to reset or choose another provider/model, then run start.bat again.[/yellow]"
        )
        if checkpoint:
            console.print(
                "[green]Completed analysis steps were saved and will be resumed on the next run.[/green]"
            )
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
