"""
API Routes.
Handles incoming HTTP requests and triggers the AI Crew.
Supports US stocks (e.g. NVDA) and Indian stocks (e.g. TCS.NS, RELIANCE.BO).
"""

import asyncio
from fastapi import APIRouter, HTTPException, Query
from src.api.models import (
    AnalysisRequest,
    AnalysisResponse,
    ReportsListResponse,
    ReportSummary,
    ErrorResponse,
)
from src.agents.crew import run_financial_crew
from src.shared.config import settings

router = APIRouter()


def _detect_market(ticker: str) -> str:
    """Return human-readable market label from ticker suffix."""
    upper = ticker.upper()
    if upper.endswith(".NS") or upper.endswith(".BO"):
        return "India (NSE/BSE)"
    return "US"


def _extract_blob_url(report_text: str) -> str:
    """
    Pull the Azure Blob Storage URL out of the Publisher agent's output.
    The publisher tool returns a line like:
    'Report uploaded to Azure Blob Storage: https://...'
    """
    for line in report_text.splitlines():
        if "blob.core.windows.net" in line:
            parts = line.split("https://", 1)
            if len(parts) == 2:
                return "https://" + parts[1].strip()
    return ""


def _check_db_saved(report_text: str) -> bool:
    """Infer whether the Publisher agent confirmed a DB save."""
    lower = report_text.lower()
    return "saved to azure postgresql" in lower or "saved" in lower


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Run full investment analysis for a stock ticker",
    tags=["Analysis"],
)
async def analyze_stock(request: AnalysisRequest):
    """
    Triggers the four-agent Financial Analysis Crew for a given ticker.

    - **Agent 1 — Quantitative Analyst:** fundamentals, technicals, DCF, earnings
    - **Agent 2 — Risk & Macro Analyst:** options, sector benchmark, macro indicators
      (uses India macro data automatically for .NS / .BO tickers)
    - **Agent 3 — Investment Strategist:** news, sentiment, BUY/SELL/HOLD verdict
    - **Agent 4 — Report Publisher:** saves to Azure PostgreSQL + Blob Storage

    Returns the full Markdown investment report and the Azure Blob URL.
    """
    ticker = request.ticker
    market = _detect_market(ticker)

    try:
        print(f"API: analysis started — {ticker} ({market})")

        # Run the blocking CrewAI crew in a thread so FastAPI stays responsive
        result_object = await asyncio.get_event_loop().run_in_executor(
            None, run_financial_crew, ticker
        )
        report_text = str(result_object)

        blob_url = _extract_blob_url(report_text)
        db_saved = _check_db_saved(report_text)

        print(f"API: analysis complete — {ticker} | blob_url={blob_url or 'none'}")

        return AnalysisResponse(
            status="success",
            ticker=ticker,
            market=market,
            report_content=report_text,
            report_url=blob_url,
            db_saved=db_saved,
            message=f"Analysis complete for {ticker} ({market}).",
        )

    except Exception as e:
        print(f"API error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/reports",
    response_model=ReportsListResponse,
    summary="List all past analysis reports stored in the database",
    tags=["Reports"],
)
async def list_reports(limit: int = Query(default=20, le=100)):
    """
    Returns a paginated list of past reports saved to Azure PostgreSQL.
    Requires AZURE_POSTGRES_CONNECTION_STRING to be configured in .env.
    Returns empty list (not an error) if DB is not configured or unreachable.
    """
    if not settings.azure_postgres_connection_string:
        return ReportsListResponse(reports=[], total=0)

    try:
        from src.shared.database import DatabaseService, FinancialReport
        db = DatabaseService()
        session = db.SessionLocal()
        rows = (
            session.query(FinancialReport)
            .order_by(FinancialReport.created_at.desc())
            .limit(limit)
            .all()
        )
        session.close()

        return ReportsListResponse(
            reports=[
                ReportSummary(id=r.id, ticker=r.ticker, created_at=r.created_at)
                for r in rows
            ],
            total=len(rows),
        )

    except Exception as e:
        # DB unreachable — return empty list with warning, don't crash the API
        print(f"DB warning (list_reports): {e}")
        return ReportsListResponse(reports=[], total=0)


@router.get(
    "/reports/{report_id}",
    summary="Fetch a single past report by ID",
    tags=["Reports"],
)
async def get_report(report_id: int):
    """
    Returns the full content of a saved report by its database ID.
    Requires AZURE_POSTGRES_CONNECTION_STRING to be configured in .env.
    """
    if not settings.azure_postgres_connection_string:
        raise HTTPException(
            status_code=503,
            detail="Database not configured. Set AZURE_POSTGRES_CONNECTION_STRING in .env.",
        )

    try:
        from src.shared.database import DatabaseService, FinancialReport
        db = DatabaseService()
        session = db.SessionLocal()
        row = session.query(FinancialReport).filter(FinancialReport.id == report_id).first()
        session.close()

        if not row:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found.")

        return {
            "id": row.id,
            "ticker": row.ticker,
            "content": row.content,
            "created_at": row.created_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database unreachable. Check AZURE_POSTGRES_CONNECTION_STRING. Error: {str(e)}"
        )
