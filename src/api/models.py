"""
API Data Models.
Defines the structure of Requests and Responses using Pydantic.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class AnalysisRequest(BaseModel):
    ticker: str = Field(
        ...,
        description=(
            "Stock ticker symbol. "
            "US stocks: 'NVDA', 'MSFT'. "
            "Indian NSE stocks: 'TCS.NS', 'RELIANCE.NS'. "
            "Indian BSE stocks: 'TCS.BO'."
        )
    )

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Ticker symbol cannot be empty.")
        if len(cleaned) > 20:
            raise ValueError("Ticker symbol too long.")
        return cleaned


class AnalysisResponse(BaseModel):
    status: str
    ticker: str
    market: str                        # "US" or "India (NSE/BSE)"
    report_content: str
    report_url: str                    # Azure Blob Storage URL (empty if not configured)
    db_saved: bool                     # Whether report was saved to PostgreSQL
    message: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ReportSummary(BaseModel):
    id: int
    ticker: str
    created_at: datetime


class ReportsListResponse(BaseModel):
    reports: list[ReportSummary]
    total: int


class ErrorResponse(BaseModel):
    status: str = "error"
    detail: str