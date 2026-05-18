"""
FastAPI Entry Point.
Initializes the application and includes the routers.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router

app = FastAPI(
    title="AI Financial Analyst API",
    description=(
        "A Production-Grade Multi-Agent API for Stock Analysis. "
        "Supports US stocks (e.g. NVDA) and Indian stocks (e.g. TCS.NS, RELIANCE.BO). "
        "Powered by 4 specialized AI agents: Quantitative Analyst, Risk & Macro Analyst, "
        "Investment Strategist, and Report Publisher."
    ),
    version="2.0.0",
)

# Allow Streamlit frontend (localhost:8501) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def health_check():
    """Health check — confirms the server is running."""
    return {
        "status": "healthy",
        "service": "AI Financial Analyst (4-Agent Crew)",
        "version": "2.0.0",
        "agents": [
            "Senior Quantitative Analyst",
            "Risk & Macro Analyst",
            "Chief Investment Strategist",
            "Report Publisher",
        ],
        "markets_supported": ["US", "India (NSE/BSE)"],
        "docs": "/docs",
    }