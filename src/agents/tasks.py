"""
Task Definitions Module.

Defines the three-stage analysis workflow. Each task feeds its output
as context into the next, ensuring every layer of analysis is data-driven.

Execution order (sequential):
    Task 1 — Quantitative Analysis   (quant_agent)
    Task 2 — Risk & Macro Analysis   (risk_agent)   ← receives Task 1 output
    Task 3 — Strategic Synthesis     (strategist_agent) ← receives Task 1 + 2 output
"""

from crewai import Task, Agent


def create_tasks(
    quant_agent: Agent,
    risk_agent: Agent,
    strategist_agent: Agent,
    publisher_agent: Agent,
    ticker: str,
) -> list[Task]:
    """
    Creates the ordered task list for the financial analysis crew.

    Args:
        quant_agent:       Agent responsible for quantitative metrics.
        risk_agent:        Agent responsible for risk and macro context.
        strategist_agent:  Agent responsible for synthesis and recommendation.
        publisher_agent:   Agent responsible for saving and uploading the report.
        ticker:            Stock ticker symbol (e.g. 'NVDA').

    Returns:
        list[Task]: Tasks in sequential execution order [quant, risk, recommendation, publish].
    """

    # ==========================================================================
    # Task 1: Quantitative Deep-Dive
    # ==========================================================================
    quant_task = Task(
        description=(
            f"Perform a full quantitative analysis of '{ticker}'. Complete ALL steps:\n\n"
            f"1. FUNDAMENTALS — Use FundamentalAnalysisTool to fetch P/E, Forward P/E, "
            f"   PEG, Beta, EPS, Market Cap, 52-week range, and analyst recommendation.\n\n"
            f"2. RELATIVE PERFORMANCE — Use CompareStocksTool to compare '{ticker}' vs "
            f"   'SPY' over the last year. Is it beating or lagging the market?\n\n"
            f"3. TECHNICAL SIGNALS — Use TechnicalIndicatorsTool (period='6mo') to get "
            f"   RSI, MACD, SMA-20, SMA-50, EMA-20, and Bollinger Bands. "
            f"   State clearly: is the stock overbought, oversold, or neutral? "
            f"   Is the trend bullish or bearish?\n\n"
            f"4. EARNINGS TRACK RECORD — Use EarningsTool to find the next earnings date "
            f"   and the last 4 quarters of EPS surprise history. "
            f"   Has the company been beating or missing estimates?\n\n"
            f"5. INTRINSIC VALUE — Use DCFValuationTool with default assumptions "
            f"   (growth_rate=0.05, discount_rate=0.10) to estimate intrinsic value per share. "
            f"   Compare to current price and state if the stock appears over or undervalued.\n\n"
            f"Flag any major red flags: negative FCF, very high P/E, RSI above 75, "
            f"consistent earnings misses, or intrinsic value far below market price."
        ),
        expected_output=(
            "A structured quantitative report covering: fundamentals snapshot, "
            "1-year relative performance vs SPY, technical indicator signals, "
            "earnings surprise history, DCF intrinsic value estimate, and a "
            "bullet-point list of key red flags or green flags."
        ),
        agent=quant_agent,
    )

    # ==========================================================================
    # Task 2: Risk & Macro Context
    # ==========================================================================
    risk_task = Task(
        description=(
            f"Assess the risk environment for '{ticker}'. Complete ALL steps:\n\n"
            f"1. OPTIONS SENTIMENT — Use OptionChainTool (nearest expiry) to get "
            f"   the put/call ratio and implied volatility at the money. "
            f"   A high PCR (>1.2) signals bearish bets; low PCR (<0.7) signals bullish bets. "
            f"   State what the options market is pricing in.\n\n"
            f"2. SECTOR BENCHMARKING — Use SectorBenchmarkTool (period='1y') to compare "
            f"   '{ticker}' against its sector ETF and SPY. "
            f"   Is it an outperformer or laggard within its own industry?\n\n"
            f"3. MACRO OVERLAY — Use MacroIndicatorsTool to get the current Fed Funds Rate, "
            f"   CPI inflation, unemployment rate, and yield curve spread. "
            f"   Assess whether the macro backdrop is supportive or headwinds for this stock.\n\n"
            f"Cross-reference the Quantitative Analyst's findings with macro context. "
            f"For example: if P/E is high, is the rate environment supportive of growth valuations?"
        ),
        expected_output=(
            "A risk context report covering: options market sentiment (PCR + IV), "
            "sector relative performance, and macro environment assessment. "
            "Include a brief 'Risk Rating': Low / Medium / High, with justification."
        ),
        agent=risk_agent,
        context=[quant_task],
    )

    # ==========================================================================
    # Task 3: Final Investment Recommendation
    # ==========================================================================
    recommendation_task = Task(
        description=(
            f"Write a professional investment report and final recommendation for '{ticker}'.\n\n"
            f"1. NEWS & SENTIMENT — Use NewsAndSentimentTool to analyse the last 10 headlines. "
            f"   What is the market mood? Are there any catalysts (product launches, lawsuits, "
            f"   earnings beats, leadership changes)?\n\n"
            f"2. DEEP RESEARCH — Use SentimentSearchTool to search for "
            f"   '{ticker} analyst rating 2025' and '{ticker} investment thesis'. "
            f"   Summarise the top 3 findings.\n\n"
            f"3. SYNTHESIS — Combine ALL inputs:\n"
            f"   - Quantitative data (Task 1): fundamentals, technicals, DCF, earnings\n"
            f"   - Risk & macro context (Task 2): options PCR, sector performance, macro\n"
            f"   - Your news findings (above)\n\n"
            f"4. VERDICT — Issue a clear final verdict: BUY, SELL, or HOLD. "
            f"   Apply these logic rules:\n"
            f"   - Good fundamentals + bullish technicals + positive news = BUY\n"
            f"   - Good numbers but high macro risk or bad news = HOLD with caution\n"
            f"   - Overvalued DCF + bearish technicals + negative sentiment = SELL\n\n"
            f"Format the output as a professional Markdown investment report."
        ),
        expected_output=(
            "A complete Markdown investment report with the following sections:\n"
            "# Investment Report: {ticker}\n"
            "## Executive Summary\n"
            "## Quantitative Snapshot (key numbers only)\n"
            "## Technical Analysis Summary\n"
            "## Risk & Macro Assessment\n"
            "## News & Market Sentiment\n"
            "## Valuation Assessment (DCF)\n"
            "## Final Verdict: BUY / SELL / HOLD\n"
            "## Investment Thesis (2-3 paragraphs)\n"
            "## Key Risks to Watch\n"
        ),
        agent=strategist_agent,
        context=[quant_task, risk_task],
        output_file=f"investment_report_{ticker}.md",
    )

    # ==========================================================================
    # Task 4: Publish Report to Azure
    # ==========================================================================
    publish_task = Task(
        description=(
            f"Persist the completed investment report for '{ticker}' to Azure.\n\n"
            f"1. DATABASE — Use SaveReportToDatabase with ticker='{ticker}' and the full "
            f"   Markdown report from Task 3 as the content. Confirm the row was saved.\n\n"
            f"2. BLOB STORAGE — Use UploadReportToBlob with ticker='{ticker}' and the same "
            f"   Markdown content. Return the Azure Blob Storage URL.\n\n"
            f"If either service is not configured (connection string missing), "
            f"log the skip message and continue — do not raise an error."
        ),
        expected_output=(
            "A short confirmation message stating:\n"
            "- Whether the report was saved to Azure PostgreSQL (success or skipped).\n"
            "- Whether the report was uploaded to Azure Blob Storage (success + URL, or skipped)."
        ),
        agent=publisher_agent,
        context=[recommendation_task],
    )

    return [quant_task, risk_task, recommendation_task, publish_task]
