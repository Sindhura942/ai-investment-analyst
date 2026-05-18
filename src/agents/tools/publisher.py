"""
Report Publisher Tools Module.

Provides CrewAI tools that wrap the DatabaseService and StorageService
so the Report Writer agent can persist and upload the final report.
"""

import os
import tempfile
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from src.shared.database import DatabaseService
from src.shared.storage import StorageService
from src.shared.config import settings


class SaveReportToDatabaseInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol, e.g. 'NVDA'.")
    content: str = Field(..., description="Full Markdown report content to save.")


class SaveReportToDatabaseTool(BaseTool):
    name: str = "SaveReportToDatabase"
    description: str = (
        "Saves a financial analysis report to Azure PostgreSQL. "
        "Use this to persist the final Markdown report with the stock ticker."
    )
    args_schema: Type[BaseModel] = SaveReportToDatabaseInput

    def _run(self, ticker: str, content: str) -> str:
        if not settings.azure_postgres_connection_string:
            return "Skipped: AZURE_POSTGRES_CONNECTION_STRING is not configured."
        try:
            db = DatabaseService()
            db.save_report(ticker=ticker, content=content)
            return f"Report for {ticker} saved to Azure PostgreSQL."
        except Exception as e:
            return f"Database save failed: {e}"


class UploadReportToBlobInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol, e.g. 'NVDA'.")
    content: str = Field(..., description="Full Markdown report content to upload.")


class UploadReportToBlobTool(BaseTool):
    name: str = "UploadReportToBlob"
    description: str = (
        "Uploads the final Markdown report to Azure Blob Storage. "
        "Returns the public URL of the uploaded file."
    )
    args_schema: Type[BaseModel] = UploadReportToBlobInput

    def _run(self, ticker: str, content: str) -> str:
        if not settings.azure_blob_storage_connection_string:
            return "Skipped: AZURE_BLOB_STORAGE_CONNECTION_STRING is not configured."
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            destination = f"investment_report_{ticker}.md"
            storage = StorageService()
            url = storage.upload_file(file_path=tmp_path, destination_name=destination)
            os.unlink(tmp_path)
            return f"Report uploaded to Azure Blob Storage: {url}"
        except Exception as e:
            return f"Blob upload failed: {e}"
