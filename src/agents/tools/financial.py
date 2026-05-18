"""
Financial Data Extraction Module.

This module provides CrewAI tools for fetching structured financial data
from the Yahoo Finance API. It is designed to be the "Quantitative Analyst"
component of the system, handling hard numbers and performance metrics.

Classes:
    FundamentalAnalysisTool:  Fetches snapshot metrics (P/E, Beta, Cap).
    CompareStocksTool:        Calculates relative performance over time.
    TechnicalIndicatorsTool:  RSI, MACD, SMA, EMA, Bollinger Bands.
    EarningsTool:             Upcoming earnings dates, EPS estimates vs actuals, surprise history.
    OptionChainTool:          Put/call data, implied volatility, open interest.
    SectorBenchmarkTool:      Stock vs. its sector ETF over a chosen period.
    MacroIndicatorsTool:      Fed rate, CPI, unemployment, yield curve via FRED API.
    NewsAndSentimentTool:     Recent headlines + VADER sentiment scoring.
    DCFValuationTool:         Discounted cash flow intrinsic value estimate.

Dependencies (core — no install needed beyond existing requirements):
    - yfinance, pandas

Optional dependencies (install to unlock the marked tools):
    - fredapi        → MacroIndicatorsTool   (pip install fredapi)
    - vaderSentiment → NewsAndSentimentTool  (pip install vaderSentiment)
    Also set FRED_API_KEY env var for MacroIndicatorsTool.
"""

import os
from typing import Type, Dict, Any, List, Optional
from statistics import mean
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import yfinance as yf
import pandas as pd

try:
    from fredapi import Fred
    _FRED_AVAILABLE = True
except ImportError:
    _FRED_AVAILABLE = False

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER_AVAILABLE = True
except ImportError:
    _VADER_AVAILABLE = False

# Sector → SPDR ETF mapping for US stocks (SectorBenchmarkTool)
_SECTOR_ETF: Dict[str, str] = {
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Healthcare": "XLV",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Basic Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Communication Services": "XLC",
}

# Sector → NSE sectoral index mapping for Indian stocks (SectorBenchmarkTool)
_INDIAN_SECTOR_INDEX: Dict[str, str] = {
    "Technology": "^CNXIT",
    "Financial Services": "^NSEBANK",
    "Healthcare": "^CNXPHARMA",
    "Consumer Cyclical": "^CNXAUTO",
    "Consumer Defensive": "^CNXFMCG",
    "Energy": "^CNXENERGY",
    "Industrials": "^CNXINFRA",
    "Basic Materials": "^CNXMETAL",
    "Real Estate": "^CNXREALTY",
    "Utilities": "^CNXINFRA",
    "Communication Services": "^CNXMEDIA",
}

# ==============================================================================
# Input Schemas (Pydantic Models)
# ==============================================================================

class StockAnalysisInput(BaseModel):
    """
    Input schema for the FundamentalAnalysisTool.
    Enforces that a ticker symbol is provided as a string.
    """
    ticker: str = Field(
        ...,
        description="The stock ticker symbol (e.g., 'AAPL','NVDA','MSFT')."
    )

class CompareStockInput(BaseModel):
    """
    Input schema for the CompareStocksTool.
    Requires two distinct tickers for side-by-side comparison.
    """
    ticker_a: str = Field(
        ...,
        description="The stock ticker symbol for the first stock (e.g., 'AAPL')."
    )
    ticker_b: str = Field(
        ...,
        description="The stock ticker symbol for the second stock (e.g., 'MSFT')."
    )

class TechnicalIndicatorsInput(BaseModel):
    """Input schema for TechnicalIndicatorsTool."""
    ticker: str = Field(..., description="The stock ticker symbol (e.g., 'AAPL', 'TSLA').")
    period: str = Field(
        default="6mo",
        description="Lookback period. Accepts yfinance strings: '1mo','3mo','6mo','1y','2y'. Default '6mo'."
    )

class EarningsInput(BaseModel):
    """Input schema for EarningsTool."""
    ticker: str = Field(..., description="The stock ticker symbol (e.g., 'AAPL').")

class OptionChainInput(BaseModel):
    """Input schema for OptionChainTool."""
    ticker: str = Field(..., description="The stock ticker symbol (e.g., 'TSLA').")
    expiry: str = Field(
        default="nearest",
        description="Option expiration date as 'YYYY-MM-DD', or 'nearest' to use the closest available expiry."
    )

class SectorBenchmarkInput(BaseModel):
    """Input schema for SectorBenchmarkTool."""
    ticker: str = Field(..., description="The stock ticker symbol to benchmark (e.g., 'NVDA').")
    period: str = Field(
        default="1y",
        description="Comparison period. Accepts yfinance strings: '3mo','6mo','1y','2y'. Default '1y'."
    )

class MacroIndicatorsInput(BaseModel):
    """Input schema for MacroIndicatorsTool — no arguments required."""
    pass

class IndiaMacroInput(BaseModel):
    """Input schema for IndiaMacroTool — no arguments required."""
    pass

class NewsAndSentimentInput(BaseModel):
    """Input schema for NewsAndSentimentTool."""
    ticker: str = Field(..., description="The stock ticker symbol (e.g., 'AMZN').")
    num_articles: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Number of recent news articles to analyse (1-20). Default is 10."
    )

class DCFValuationInput(BaseModel):
    """Input schema for DCFValuationTool."""
    ticker: str = Field(..., description="The stock ticker symbol (e.g., 'MSFT').")
    growth_rate: float = Field(
        default=0.05,
        ge=-0.5,
        le=1.0,
        description="Expected annual free-cash-flow growth rate as a decimal (e.g., 0.05 = 5%). Default 5%."
    )
    discount_rate: float = Field(
        default=0.10,
        ge=0.01,
        le=1.0,
        description="Discount rate / WACC as a decimal (e.g., 0.10 = 10%). Default 10%."
    )
    terminal_growth: float = Field(
        default=0.025,
        ge=-0.05,
        le=0.10,
        description="Perpetual terminal growth rate as a decimal (e.g., 0.025 = 2.5%). Default 2.5%."
    )
    years: int = Field(
        default=10,
        ge=1,
        le=30,
        description="Projection horizon in years. Default 10."
    )

# ==============================================================================
# Tool Definitions
# ==============================================================================

class FundamentalAnalysisTool(BaseTool):
    """
    A CrewAI tool that extracts key fundamental financial metrics for stocks.

    This tool acts as a "Screening Analyst", providing the raw data needed
    to determine if a stock is overvalued, undervalued, or volatile.
    """

    name: str = "Fetch Fundamental Metrics"
    description: str = (
        "Fetches key financial metrics for a specific stock ticker. "
        "Useful for quantitative analysis. Returns JSON-formatted data including "
        "P/E Ratio, Beta, Market Cap, EPS, and 52-week High/Low."
    )
    args_schema: Type[BaseModel] = StockAnalysisInput

    def _run(self, ticker: str) -> str:
        """
        Executes the data fetch from Yahoo Finance using the yfinance library.

        Args:
            ticker (str): The stock ticker symbol to fetch data for.

        Returns:
            str: A stringified JSON dictionary containing selected metrics,
                 or an error message string if the fetch fails.
        """
        try:
            stock = yf.Ticker(ticker)
            info: Dict[str, Any] = stock.info

            # We explicitly select only robust metrics to avoid context-window bloat.
            # Sending ALL yfinance data (100+ keys) often confuses the LLM.
            metrics = {
                "Ticker": ticker.upper(),
                "Current Price": info.get("currentPrice", "N/A"),
                "Market Cap": info.get("marketCap", "N/A"),
                "P/E Ratio (Trailing)": info.get("trailingPE", "N/A"),
                "Forward P/E": info.get("forwardPE", "N/A"),
                "PEG Ratio": info.get("pegRatio", "N/A"),
                "Beta (Volatility)": info.get("beta", "N/A"),
                "EPS (Trailing)": info.get("trailingEps", "N/A"),
                "52 Week High": info.get("fiftyTwoWeekHigh", "N/A"),
                "52 Week Low": info.get("fiftyTwoWeekLow", "N/A"),
                "Analyst Recommendation": info.get("recommendationKey", "none")
            }
            return str(metrics)

        except Exception as e:
            # Graceful error handling allows the Agent to self-correct
            # (e.g., by retrying with a corrected ticker symbol)
            return f"Error fetching fundamental data for '{ticker}': {str(e)}"


class CompareStocksTool(BaseTool):
    """
    A CrewAI tool that calculates relative performance between two assets.

    This tool is used to answer questions like 'Did Nvidia beat Apple last year?'
    by calculating the percentage change in price over a 1-year period.
    """

    name: str = "Compare Stock Performance"
    description: str = (
        "Compares the historical performance of two stocks over the last 365 days. "
        "Returns the percentage gain or loss for both assets."
    )
    args_schema: Type[BaseModel] = CompareStockInput

    def _run(self, ticker_a: str, ticker_b: str) -> str:
        """
        Fetches historical data and calculates percentage return.

        Formula: ((Last Price - First Price) / First Price) * 100

        Args:
            ticker_a (str): First stock symbol.
            ticker_b (str): Second stock symbol.

        Returns:
            str: A formatted summary of the 1-year performance comparison.
        """
        try:
            tickers = f"{ticker_a} {ticker_b}"
            data = yf.download(tickers, period="1y", progress=False)['Close']

            def calculate_return(symbol: str) -> float:
                start_price = data[symbol].iloc[0]
                end_price = data[symbol].iloc[-1]
                return ((end_price - start_price) / start_price) * 100

            perf_a = calculate_return(ticker_a)
            perf_b = calculate_return(ticker_b)

            return (
                f"Performance Comparison (Last 1 Year):\n"
                f"- {ticker_a.upper()}: {perf_a:.2f}%\n"
                f"- {ticker_b.upper()}: {perf_b:.2f}%"
            )

        except Exception as e:
            return f"Error comparing stocks '{ticker_a}' and '{ticker_b}': {str(e)}"


class TechnicalIndicatorsTool(BaseTool):
    """
    A CrewAI tool that computes key technical indicators from historical price data.

    Covers momentum (RSI), trend-following (MACD, SMA, EMA), and volatility
    (Bollinger Bands) — the standard toolkit for chart-based trading signals.
    All calculations are done in-process using pandas; no external TA library needed.
    """

    name: str = "Fetch Technical Indicators"
    description: str = (
        "Calculates technical analysis indicators for a stock ticker over a given period. "
        "Returns RSI (momentum), MACD (trend/momentum crossover), SMA-20 & SMA-50 "
        "(simple moving averages), EMA-20 (exponential moving average), and "
        "Bollinger Bands (volatility envelope). Useful for identifying overbought/oversold "
        "conditions, trend direction, and price volatility."
    )
    args_schema: Type[BaseModel] = TechnicalIndicatorsInput

    # ------------------------------------------------------------------
    # Private calculation helpers
    # ------------------------------------------------------------------

    def _compute_rsi(self, close: pd.Series, window: int = 14) -> float:
        """Wilder's RSI. Returns the most recent RSI value (0-100)."""
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(window).mean()
        loss = (-delta.clip(upper=0)).rolling(window).mean()
        rs = gain / loss.replace(0, float("inf"))
        rsi = 100 - (100 / (1 + rs))
        return round(float(rsi.iloc[-1]), 2)

    def _compute_macd(self, close: pd.Series) -> Dict[str, float]:
        """Standard 12/26/9 MACD. Returns line, signal, and histogram."""
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        return {
            "MACD Line": round(float(macd_line.iloc[-1]), 4),
            "Signal Line": round(float(signal_line.iloc[-1]), 4),
            "Histogram": round(float(histogram.iloc[-1]), 4),
        }

    def _compute_bollinger_bands(self, close: pd.Series, window: int = 20) -> Dict[str, float]:
        """20-day Bollinger Bands (±2 std deviations)."""
        sma = close.rolling(window).mean()
        std = close.rolling(window).std()
        upper = sma + 2 * std
        lower = sma - 2 * std
        return {
            "Upper Band": round(float(upper.iloc[-1]), 2),
            "Middle Band (SMA-20)": round(float(sma.iloc[-1]), 2),
            "Lower Band": round(float(lower.iloc[-1]), 2),
        }

    # ------------------------------------------------------------------
    # Main run
    # ------------------------------------------------------------------

    def _run(self, ticker: str, period: str = "6mo") -> str:
        try:
            hist = yf.download(ticker, period=period, progress=False, auto_adjust=True)

            if hist.empty or len(hist) < 30:
                return f"Insufficient historical data for '{ticker}' over period '{period}'."

            close: pd.Series = hist["Close"].squeeze()
            current_price = round(float(close.iloc[-1]), 2)

            rsi = self._compute_rsi(close)
            macd = self._compute_macd(close)
            bb = self._compute_bollinger_bands(close)

            sma20 = round(float(close.rolling(20).mean().iloc[-1]), 2)
            sma50 = round(float(close.rolling(50).mean().iloc[-1]), 2) if len(close) >= 50 else "N/A"
            ema20 = round(float(close.ewm(span=20, adjust=False).mean().iloc[-1]), 2)

            # Derived signals for quick agent interpretation
            rsi_signal = "Overbought" if rsi > 70 else ("Oversold" if rsi < 30 else "Neutral")
            macd_signal = "Bullish crossover" if macd["Histogram"] > 0 else "Bearish crossover"
            bb_position = (
                "Near upper band (overbought risk)" if current_price >= bb["Upper Band"]
                else "Near lower band (oversold opportunity)" if current_price <= bb["Lower Band"]
                else "Within bands (normal range)"
            )

            result = {
                "Ticker": ticker.upper(),
                "Period": period,
                "Current Price": current_price,
                "RSI (14)": rsi,
                "RSI Signal": rsi_signal,
                "MACD": macd,
                "MACD Signal": macd_signal,
                "SMA-20": sma20,
                "SMA-50": sma50,
                "EMA-20": ema20,
                "Bollinger Bands": bb,
                "Price vs Bollinger": bb_position,
            }
            return str(result)

        except Exception as e:
            return f"Error computing technical indicators for '{ticker}': {str(e)}"


# ==============================================================================
# EarningsTool
# ==============================================================================

class EarningsTool(BaseTool):
    """
    Fetches upcoming earnings date, EPS estimates vs. actuals, and
    earnings surprise history for a given ticker.
    """

    name: str = "Fetch Earnings Data"
    description: str = (
        "Returns the next earnings date, analyst EPS estimate, and historical "
        "EPS surprise data (actual vs. estimated) for a stock. Useful for "
        "event-driven analysis and assessing management's track record of "
        "beating or missing Wall Street expectations."
    )
    args_schema: Type[BaseModel] = EarningsInput

    def _run(self, ticker: str) -> str:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Next earnings date
            next_earnings = info.get("earningsTimestamp")
            if next_earnings:
                import datetime
                next_date = datetime.datetime.fromtimestamp(next_earnings).strftime("%Y-%m-%d")
            else:
                next_date = "N/A"

            # EPS estimates
            eps_fwd = info.get("forwardEps", "N/A")
            eps_trail = info.get("trailingEps", "N/A")
            eps_next_qtr = info.get("epsCurrentYear", "N/A")

            # Historical earnings surprise (last 4 quarters)
            surprise_history = []
            try:
                hist_earnings = stock.earnings_history
                if hist_earnings is not None and not hist_earnings.empty:
                    for _, row in hist_earnings.tail(4).iterrows():
                        eps_est = row.get("epsEstimate", None)
                        eps_act = row.get("epsActual", None)
                        if eps_est is not None and eps_act is not None and eps_est != 0:
                            surprise_pct = round(((eps_act - eps_est) / abs(eps_est)) * 100, 2)
                            surprise_history.append({
                                "Quarter": str(row.name.date()) if hasattr(row.name, "date") else str(row.name),
                                "EPS Estimate": round(float(eps_est), 4),
                                "EPS Actual": round(float(eps_act), 4),
                                "Surprise %": surprise_pct,
                            })
            except Exception:
                surprise_history = "Earnings history unavailable"

            result = {
                "Ticker": ticker.upper(),
                "Next Earnings Date": next_date,
                "Forward EPS (Estimate)": eps_fwd,
                "Trailing EPS (TTM)": eps_trail,
                "EPS Current Year Estimate": eps_next_qtr,
                "Earnings Surprise History (Last 4 Quarters)": surprise_history,
            }
            return str(result)

        except Exception as e:
            return f"Error fetching earnings data for '{ticker}': {str(e)}"


# ==============================================================================
# OptionChainTool
# ==============================================================================

class OptionChainTool(BaseTool):
    """
    Fetches option chain data (calls and puts) for a given ticker and expiry,
    surfacing implied volatility, open interest, and at-the-money strikes.
    """

    name: str = "Fetch Option Chain"
    description: str = (
        "Returns a summary of the options market for a stock: available expiry dates, "
        "at-the-money call and put details (strike, bid/ask, implied volatility, open interest), "
        "and total put/call open interest ratio. Useful for gauging market sentiment, "
        "hedging costs, and identifying unusual options activity."
    )
    args_schema: Type[BaseModel] = OptionChainInput

    def _run(self, ticker: str, expiry: str = "nearest") -> str:
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options
            if not expirations:
                return f"No options data available for '{ticker}'."

            exp_date = expirations[0] if expiry == "nearest" else expiry
            if exp_date not in expirations:
                return (
                    f"Expiry '{expiry}' not found for '{ticker}'. "
                    f"Available: {', '.join(expirations[:5])}"
                )

            chain = stock.option_chain(exp_date)
            current_price = stock.info.get("currentPrice", None)

            def summarize_side(df: pd.DataFrame, side: str) -> Dict[str, Any]:
                if df.empty:
                    return {"error": "No data"}
                # Find ATM strike (closest to current price)
                if current_price:
                    atm_idx = (df["strike"] - current_price).abs().idxmin()
                    atm = df.loc[atm_idx]
                else:
                    atm = df.iloc[len(df) // 2]

                top_oi = df.nlargest(3, "openInterest")[["strike", "openInterest", "impliedVolatility"]].to_dict("records")
                return {
                    f"ATM {side} Strike": round(float(atm["strike"]), 2),
                    "Bid": round(float(atm.get("bid", 0)), 2),
                    "Ask": round(float(atm.get("ask", 0)), 2),
                    "Implied Volatility (ATM)": f"{round(float(atm.get('impliedVolatility', 0)) * 100, 2)}%",
                    "Open Interest (ATM)": int(atm.get("openInterest", 0)),
                    "Top 3 by Open Interest": top_oi,
                }

            calls_summary = summarize_side(chain.calls, "Call")
            puts_summary = summarize_side(chain.puts, "Put")

            total_call_oi = int(chain.calls["openInterest"].sum()) if not chain.calls.empty else 0
            total_put_oi = int(chain.puts["openInterest"].sum()) if not chain.puts.empty else 0
            pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else "N/A"
            pcr_signal = (
                "Bearish (high put demand)" if isinstance(pcr, float) and pcr > 1.2
                else "Bullish (low put demand)" if isinstance(pcr, float) and pcr < 0.7
                else "Neutral"
            )

            result = {
                "Ticker": ticker.upper(),
                "Expiry Date": exp_date,
                "Current Price": current_price,
                "Available Expiries (next 5)": list(expirations[:5]),
                "Calls": calls_summary,
                "Puts": puts_summary,
                "Total Call OI": total_call_oi,
                "Total Put OI": total_put_oi,
                "Put/Call OI Ratio": pcr,
                "PCR Signal": pcr_signal,
            }
            return str(result)

        except Exception as e:
            return f"Error fetching option chain for '{ticker}': {str(e)}"


# ==============================================================================
# SectorBenchmarkTool
# ==============================================================================

class SectorBenchmarkTool(BaseTool):
    """
    Compares a stock's price performance against its sector SPDR ETF
    and the broad S&P 500 (SPY) over a chosen period.
    """

    name: str = "Sector Benchmark Comparison"
    description: str = (
        "Compares a stock's return against its sector ETF (e.g., XLK for Technology) "
        "and SPY (S&P 500) over a given period. Indicates whether the stock is an "
        "outperformer or laggard within its own industry, which is critical for "
        "relative-value analysis."
    )
    args_schema: Type[BaseModel] = SectorBenchmarkInput

    def _run(self, ticker: str, period: str = "1y") -> str:
        try:
            is_indian = ticker.upper().endswith(".NS") or ticker.upper().endswith(".BO")
            stock = yf.Ticker(ticker)
            sector = stock.info.get("sector", "Unknown")

            if is_indian:
                sector_index = _INDIAN_SECTOR_INDEX.get(sector, "^NSEI")
                market_benchmark = "^NSEI"
                market_label = "Nifty 50"
            else:
                sector_index = _SECTOR_ETF.get(sector, "SPY")
                market_benchmark = "SPY"
                market_label = "S&P 500 (SPY)"

            symbols = [ticker.upper(), sector_index, market_benchmark]
            data = yf.download(symbols, period=period, progress=False, auto_adjust=True)["Close"]

            if data.empty:
                return f"No historical data returned for period '{period}'."

            def pct_return(sym: str) -> Optional[float]:
                if sym not in data.columns:
                    return None
                series = data[sym].dropna()
                if len(series) < 2:
                    return None
                return round(((series.iloc[-1] - series.iloc[0]) / series.iloc[0]) * 100, 2)

            stock_ret = pct_return(ticker.upper())
            sector_ret = pct_return(sector_index)
            market_ret = pct_return(market_benchmark)

            vs_sector = (
                f"+{round(stock_ret - sector_ret, 2)}% outperformance"
                if stock_ret is not None and sector_ret is not None and stock_ret >= sector_ret
                else f"{round(stock_ret - sector_ret, 2)}% underperformance"
                if stock_ret is not None and sector_ret is not None
                else "N/A"
            )
            vs_market = (
                f"+{round(stock_ret - market_ret, 2)}% outperformance"
                if stock_ret is not None and market_ret is not None and stock_ret >= market_ret
                else f"{round(stock_ret - market_ret, 2)}% underperformance"
                if stock_ret is not None and market_ret is not None
                else "N/A"
            )

            result = {
                "Ticker": ticker.upper(),
                "Market": "India (NSE/BSE)" if is_indian else "US",
                "Sector": sector,
                "Sector Index": sector_index,
                "Market Benchmark": f"{market_benchmark} ({market_label})",
                "Period": period,
                f"{ticker.upper()} Return": f"{stock_ret}%",
                f"{sector_index} (Sector) Return": f"{sector_ret}%",
                f"{market_benchmark} ({market_label}) Return": f"{market_ret}%",
                f"vs Sector Index": vs_sector,
                f"vs {market_label}": vs_market,
            }
            return str(result)

        except Exception as e:
            return f"Error benchmarking '{ticker}': {str(e)}"


# ==============================================================================
# MacroIndicatorsTool
# ==============================================================================

class MacroIndicatorsTool(BaseTool):
    """
    Fetches key macroeconomic indicators from the Federal Reserve FRED API:
    Fed Funds Rate, CPI, Unemployment Rate, and the 10Y-2Y yield curve spread.

    Requires: pip install fredapi  and  FRED_API_KEY environment variable.
    Free API key: https://fred.stlouisfed.org/docs/api/api_key.html
    """

    name: str = "Fetch Macro Economic Indicators"
    description: str = (
        "Returns the latest US macroeconomic data from the FRED API: "
        "Federal Funds Rate, CPI (inflation), Unemployment Rate, and the "
        "10Y-2Y Treasury yield curve spread (recession indicator). "
        "Use this to overlay macro conditions onto any equity or portfolio analysis."
    )
    args_schema: Type[BaseModel] = MacroIndicatorsInput

    # FRED series IDs
    _SERIES: Dict[str, str] = {
        "Federal Funds Rate (%)": "DFF",
        "CPI YoY Inflation (%)": "CPIAUCSL",
        "Unemployment Rate (%)": "UNRATE",
        "10Y-2Y Yield Curve Spread (%)": "T10Y2Y",
        "Real GDP Growth (Quarterly %)": "A191RL1Q225SBEA",
    }

    def _run(self) -> str:
        if not _FRED_AVAILABLE:
            return (
                "fredapi is not installed. Run: pip install fredapi\n"
                "Then set the FRED_API_KEY environment variable.\n"
                "Free key: https://fred.stlouisfed.org/docs/api/api_key.html"
            )

        api_key = os.getenv("FRED_API_KEY")
        if not api_key:
            return (
                "FRED_API_KEY environment variable is not set. "
                "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html "
                "and set it with: export FRED_API_KEY=your_key_here"
            )

        try:
            fred = Fred(api_key=api_key)
            result: Dict[str, Any] = {"Source": "Federal Reserve FRED API"}

            for label, series_id in self._SERIES.items():
                try:
                    series = fred.get_series(series_id)
                    latest_value = round(float(series.dropna().iloc[-1]), 3)
                    latest_date = str(series.dropna().index[-1].date())
                    result[label] = {"Value": latest_value, "As Of": latest_date}
                except Exception:
                    result[label] = "Unavailable"

            # Derived signal: yield curve inversion is a recession warning
            try:
                yc = result.get("10Y-2Y Yield Curve Spread (%)", {})
                if isinstance(yc, dict):
                    spread = yc["Value"]
                    result["Yield Curve Signal"] = (
                        "Inverted — historical recession warning" if spread < 0
                        else "Flat — caution" if spread < 0.5
                        else "Normal — no immediate recession signal"
                    )
            except Exception:
                pass

            return str(result)

        except Exception as e:
            return f"Error fetching macro indicators: {str(e)}"


# ==============================================================================
# IndiaMacroTool
# ==============================================================================

class IndiaMacroTool(BaseTool):
    """
    Fetches key Indian macroeconomic indicators:
    - India CPI and Long-Term Interest Rate via FRED (uses existing FRED_API_KEY)
    - India GDP Growth via FRED
    - USD/INR exchange rate and India VIX via yfinance (no extra key needed)
    - Nifty 50 and Sensex levels via yfinance

    No additional API keys required beyond FRED_API_KEY already in .env.
    """

    name: str = "Fetch India Macro Economic Indicators"
    description: str = (
        "Returns key Indian macroeconomic data: India CPI (inflation), "
        "India long-term interest rate, India GDP growth rate, USD/INR exchange rate, "
        "India VIX (fear index), and current Nifty 50 / Sensex levels. "
        "Use this instead of the US MacroIndicatorsTool when analysing NSE/BSE stocks."
    )
    args_schema: Type[BaseModel] = IndiaMacroInput

    _FRED_SERIES: Dict[str, str] = {
        "India CPI (Index)": "INDCPIALLMINMEI",
        "India Long-Term Interest Rate (%)": "INDIRLTLT01STM",
        "India GDP Growth Rate (%)": "INDGDPRQPSMEI",
    }

    def _run(self) -> str:
        result: Dict[str, Any] = {}

        # --- FRED data (uses existing FRED_API_KEY) ---
        if _FRED_AVAILABLE:
            api_key = os.getenv("FRED_API_KEY")
            if api_key:
                try:
                    fred = Fred(api_key=api_key)
                    for label, series_id in self._FRED_SERIES.items():
                        try:
                            series = fred.get_series(series_id)
                            latest_value = round(float(series.dropna().iloc[-1]), 3)
                            latest_date = str(series.dropna().index[-1].date())
                            result[label] = {"Value": latest_value, "As Of": latest_date}
                        except Exception:
                            result[label] = "Unavailable"
                except Exception as e:
                    result["FRED Error"] = str(e)
            else:
                result["FRED Data"] = "Skipped — FRED_API_KEY not set"
        else:
            result["FRED Data"] = "Skipped — fredapi not installed (pip install fredapi)"

        # --- yfinance data (no API key needed) ---
        yf_symbols = {
            "Nifty 50 (^NSEI)": "^NSEI",
            "BSE Sensex (^BSESN)": "^BSESN",
            "India VIX (^INDIAVIX)": "^INDIAVIX",
            "USD/INR Exchange Rate": "USDINR=X",
        }
        for label, symbol in yf_symbols.items():
            try:
                hist = yf.Ticker(symbol).history(period="5d")
                if not hist.empty:
                    val = round(float(hist["Close"].iloc[-1]), 2)
                    result[label] = val
                else:
                    result[label] = "Unavailable"
            except Exception:
                result[label] = "Unavailable"

        # Derived signal: India VIX interpretation
        try:
            vix = result.get("India VIX (^INDIAVIX)")
            if isinstance(vix, float):
                result["India VIX Signal"] = (
                    "High fear — market expects large swings" if vix > 20
                    else "Moderate — some uncertainty" if vix > 14
                    else "Low fear — market is calm"
                )
        except Exception:
            pass

        result["Note"] = (
            "RBI Repo Rate is not available via free APIs. "
            "Use India Long-Term Interest Rate as a proxy. "
            "For the latest RBI rate, visit: https://www.rbi.org.in"
        )

        return str(result)


# ==============================================================================
# NewsAndSentimentTool
# ==============================================================================

class NewsAndSentimentTool(BaseTool):
    """
    Fetches recent news headlines for a ticker via yfinance and scores each
    using VADER sentiment analysis (compound score: -1 bearish → +1 bullish).

    Requires: pip install vaderSentiment
    """

    name: str = "Fetch News and Sentiment"
    description: str = (
        "Retrieves recent news headlines for a stock and returns a VADER sentiment "
        "score for each article (compound score: +1 = very positive, -1 = very negative). "
        "Also returns an average sentiment label (Positive / Neutral / Negative). "
        "Useful for gauging current market mood, detecting PR crises, or supplementing "
        "fundamental analysis with narrative context."
    )
    args_schema: Type[BaseModel] = NewsAndSentimentInput

    def _run(self, ticker: str, num_articles: int = 10) -> str:
        if not _VADER_AVAILABLE:
            return (
                "vaderSentiment is not installed. Run: pip install vaderSentiment"
            )

        try:
            stock = yf.Ticker(ticker)
            raw_news = stock.news or []

            if not raw_news:
                return f"No recent news found for '{ticker}'."

            analyzer = SentimentIntensityAnalyzer()
            scored_articles: List[Dict[str, Any]] = []

            for article in raw_news[:num_articles]:
                title = article.get("title", "")
                if not title:
                    continue
                scores = analyzer.polarity_scores(title)
                compound = round(scores["compound"], 4)
                label = (
                    "Positive" if compound >= 0.05
                    else "Negative" if compound <= -0.05
                    else "Neutral"
                )
                scored_articles.append({
                    "Headline": title,
                    "Publisher": article.get("publisher", "Unknown"),
                    "Sentiment": label,
                    "Compound Score": compound,
                })

            if not scored_articles:
                return f"No scoreable headlines found for '{ticker}'."

            scores_list = [a["Compound Score"] for a in scored_articles]
            avg_score = round(mean(scores_list), 4)
            overall_label = (
                "Positive" if avg_score >= 0.05
                else "Negative" if avg_score <= -0.05
                else "Neutral"
            )

            result = {
                "Ticker": ticker.upper(),
                "Articles Analysed": len(scored_articles),
                "Average Sentiment Score": avg_score,
                "Overall Sentiment": overall_label,
                "Articles": scored_articles,
            }
            return str(result)

        except Exception as e:
            return f"Error fetching news/sentiment for '{ticker}': {str(e)}"


# ==============================================================================
# DCFValuationTool
# ==============================================================================

class DCFValuationTool(BaseTool):
    """
    Estimates intrinsic value per share using a simplified Discounted Cash Flow
    model based on trailing free cash flow from yfinance.

    Model: project FCF for N years at growth_rate, discount at discount_rate,
    add Gordon Growth terminal value, divide by shares outstanding.
    """

    name: str = "DCF Intrinsic Value Estimate"
    description: str = (
        "Calculates a simplified DCF (Discounted Cash Flow) intrinsic value per share "
        "for a stock using its trailing free cash flow, a user-supplied growth rate, "
        "discount rate, terminal growth rate, and projection horizon. "
        "Returns intrinsic value per share, comparison to current price, "
        "implied margin of safety, and a buy/hold/sell signal. "
        "NOTE: DCF is sensitive to assumptions — treat the output as a directional "
        "estimate, not a precise target."
    )
    args_schema: Type[BaseModel] = DCFValuationInput

    def _run(
        self,
        ticker: str,
        growth_rate: float = 0.05,
        discount_rate: float = 0.10,
        terminal_growth: float = 0.025,
        years: int = 10,
    ) -> str:
        try:
            if discount_rate <= terminal_growth:
                return (
                    "Invalid inputs: discount_rate must be greater than terminal_growth "
                    "to avoid division by zero in the Gordon Growth terminal value."
                )

            stock = yf.Ticker(ticker)
            info = stock.info

            fcf = info.get("freeCashflow")
            shares = info.get("sharesOutstanding")
            current_price = info.get("currentPrice")

            if not fcf:
                return f"Free cash flow data unavailable for '{ticker}'. DCF cannot be calculated."
            if not shares:
                return f"Shares outstanding data unavailable for '{ticker}'. DCF cannot be calculated."
            if not current_price:
                return f"Current price unavailable for '{ticker}'."

            if fcf <= 0:
                return (
                    f"'{ticker}' has negative free cash flow ({fcf:,}). "
                    "A standard DCF model is not meaningful for loss-making companies."
                )

            # Project and discount FCF over the horizon
            projected_pv = sum(
                fcf * (1 + growth_rate) ** yr / (1 + discount_rate) ** yr
                for yr in range(1, years + 1)
            )

            # Terminal value (Gordon Growth Model) discounted to present
            terminal_fcf = fcf * (1 + growth_rate) ** years * (1 + terminal_growth)
            terminal_value = terminal_fcf / (discount_rate - terminal_growth)
            terminal_pv = terminal_value / (1 + discount_rate) ** years

            intrinsic_total = projected_pv + terminal_pv
            intrinsic_per_share = round(intrinsic_total / shares, 2)
            current_price = round(current_price, 2)

            margin_of_safety = round(
                ((intrinsic_per_share - current_price) / intrinsic_per_share) * 100, 2
            )

            signal = (
                "Buy — significant undervaluation" if margin_of_safety > 20
                else "Buy — modest undervaluation" if margin_of_safety > 0
                else "Hold / Fairly valued" if margin_of_safety > -10
                else "Caution — potential overvaluation" if margin_of_safety > -30
                else "Sell — significant overvaluation"
            )

            result = {
                "Ticker": ticker.upper(),
                "Assumptions": {
                    "FCF Growth Rate": f"{growth_rate * 100}%",
                    "Discount Rate (WACC)": f"{discount_rate * 100}%",
                    "Terminal Growth Rate": f"{terminal_growth * 100}%",
                    "Projection Years": years,
                },
                "Trailing Free Cash Flow": f"${fcf:,}",
                "PV of Projected FCFs": f"${round(projected_pv):,}",
                "PV of Terminal Value": f"${round(terminal_pv):,}",
                "Total Intrinsic Value": f"${round(intrinsic_total):,}",
                "Intrinsic Value per Share": f"${intrinsic_per_share}",
                "Current Market Price": f"${current_price}",
                "Margin of Safety": f"{margin_of_safety}%",
                "Signal": signal,
                "Warning": (
                    "DCF outputs are highly sensitive to growth and discount rate assumptions. "
                    "Use alongside fundamental and technical analysis."
                ),
            }
            return str(result)

        except Exception as e:
            return f"Error running DCF valuation for '{ticker}': {str(e)}"
