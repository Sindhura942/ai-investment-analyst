"""
Crew Orchestration Module.

Assembles the three-agent team, assigns tasks, and runs the sequential
analysis pipeline: Quant → Risk/Macro → Strategist.
"""

from crewai import Crew, Process
from src.agents.agents import create_agents
from src.agents.tasks import create_tasks


def run_financial_crew(ticker: str) -> str:
    """
    Initializes and executes the Financial Analysis Crew for a given stock.

    Args:
        ticker: Stock symbol to analyze (e.g. 'MSFT').

    Returns:
        str: The final Markdown investment report from the Strategist agent.
    """

    quant_agent, risk_agent, strategist_agent, publisher_agent = create_agents()

    tasks = create_tasks(
        quant_agent=quant_agent,
        risk_agent=risk_agent,
        strategist_agent=strategist_agent,
        publisher_agent=publisher_agent,
        ticker=ticker,
    )

    financial_crew = Crew(
        agents=[quant_agent, risk_agent, strategist_agent, publisher_agent],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=True,
    )

    print(f"\n🚀 Kicking off Financial Analysis for {ticker}...")
    result = financial_crew.kickoff()

    return result
