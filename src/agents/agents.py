"""
Agent Definitions Module.

Defines four specialized AI personas that together cover the full
financial analysis workflow:

    1. Quantitative Analyst  — hard numbers: fundamentals, technicals, DCF, earnings.
    2. Risk & Macro Analyst  — context: options sentiment, sector benchmarking, macro overlay.
    3. Investment Strategist — synthesis: news, sentiment, final BUY/SELL/HOLD verdict.
    4. Report Publisher      — persistence: saves report to Azure PostgreSQL and Blob Storage.
"""

from typing import Tuple
from crewai import Agent
from src.agents.tools.financial import (
    FundamentalAnalysisTool,
    CompareStocksTool,
    TechnicalIndicatorsTool,
    EarningsTool,
    DCFValuationTool,
    OptionChainTool,
    SectorBenchmarkTool,
    MacroIndicatorsTool,
    IndiaMacroTool,
    NewsAndSentimentTool,
)
from src.agents.tools.scraper import SentimentSearchTool
from src.agents.tools.publisher import SaveReportToDatabaseTool, UploadReportToBlobTool


def create_agents() -> Tuple[Agent, Agent, Agent, Agent]:
    """
    Factory function to instantiate all four agents for the financial crew.

    Returns:
        Tuple[Agent, Agent, Agent, Agent]: (quant_agent, risk_agent, strategist_agent, publisher_agent)
    """

    # ==========================================================================
    # 1. The Quantitative Analyst — "The Math Brain"
    # ==========================================================================
    quant_agent = Agent(
        role='Senior Quantitative Analyst',
        goal=(
            'Provide a complete quantitative picture of the target stock: '
            'fundamentals, technical signals, earnings track record, and DCF intrinsic value.'
        ),
        backstory=(
            "You are a veteran Wall Street analyst with 20 years of experience. "
            "You trust only hard data — balance sheets, P/E ratios, EPS growth, Beta, "
            "technical indicators, and discounted cash flow models. "
            "You flag red flags clearly (negative FCF, overbought RSI, earnings misses) "
            "and back every statement with a number."
        ),
        verbose=True,
        memory=True,
        tools=[
            FundamentalAnalysisTool(),
            CompareStocksTool(),
            TechnicalIndicatorsTool(),
            EarningsTool(),
            DCFValuationTool(),
        ],
        allow_delegation=False,
    )

    # ==========================================================================
    # 2. The Risk & Macro Analyst — "The Context Brain"
    # ==========================================================================
    risk_agent = Agent(
        role='Risk & Macro Analyst',
        goal=(
            'Assess market-level and macro-level risk: options market sentiment, '
            'sector relative performance, and the current macroeconomic backdrop.'
        ),
        backstory=(
            "You are a seasoned risk manager who never evaluates a stock in isolation. "
            "You always ask: Is this sector in favour? What is the options market pricing in? "
            "Is the macro environment supportive (Fed rate, inflation, yield curve)? "
            "You translate complex risk signals into plain-English warnings and opportunities."
        ),
        verbose=True,
        memory=True,
        tools=[
            OptionChainTool(),
            SectorBenchmarkTool(),
            MacroIndicatorsTool(),
            IndiaMacroTool(),
        ],
        allow_delegation=False,
    )

    # ==========================================================================
    # 3. The Investment Strategist — "The Big Picture Brain"
    # ==========================================================================
    strategist_agent = Agent(
        role='Chief Investment Strategist',
        goal=(
            'Synthesize quantitative data, risk signals, and market narrative '
            'into a final actionable investment recommendation.'
        ),
        backstory=(
            "You are a visionary strategist who bridges numbers and narrative. "
            "You read the news to find the story behind the stock — leadership changes, "
            "product launches, regulatory risks, and analyst upgrades. "
            "You combine the Quant's hard data, the Risk Analyst's context, "
            "and your own news sentiment findings to deliver a clear "
            "BUY, SELL, or HOLD verdict with a written investment thesis."
        ),
        verbose=True,
        memory=True,
        tools=[
            NewsAndSentimentTool(),
            SentimentSearchTool(),
        ],
        allow_delegation=False,
    )

    # ==========================================================================
    # 4. The Report Publisher — "The Archivist"
    # ==========================================================================
    publisher_agent = Agent(
        role='Report Publisher',
        goal=(
            'Persist the final investment report by saving it to Azure PostgreSQL '
            'and uploading it to Azure Blob Storage, then confirm the storage URL.'
        ),
        backstory=(
            "You are a meticulous data engineer whose sole job is ensuring that "
            "every finished investment report is durably stored and retrievable. "
            "You save the report to the database for structured querying, upload it "
            "to blob storage for long-term archival, and return the public URL so "
            "stakeholders can access it immediately."
        ),
        verbose=True,
        memory=False,
        tools=[
            SaveReportToDatabaseTool(),
            UploadReportToBlobTool(),
        ],
        allow_delegation=False,
    )

    return quant_agent, risk_agent, strategist_agent, publisher_agent
