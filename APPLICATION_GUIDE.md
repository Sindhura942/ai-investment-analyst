# AI Financial Analyst — Plain English Guide

## What Is This Application?

Imagine having a team of four expert analysts you can call on at any time to research any stock — for free, in under 3 minutes. You type in a company's stock symbol (like `NVDA` for Nvidia or `MSFT` for Microsoft), click a button, and the team gets to work. When they are done, you receive a professional investment report telling you whether the stock is a **BUY, SELL, or HOLD** — and exactly why.

This application does that using Artificial Intelligence. The four "analysts" are AI agents, each with a specific job, working one after the other like a real-world research team.

---

## How You Use It

1. Open the app in your browser (it looks like a simple website).
2. Type a stock ticker symbol in the sidebar — for example `AAPL` for Apple.
3. Click **Run Full Analysis**.
4. Wait 1–3 minutes while the AI team works.
5. Read your professional investment report on screen, or download it.

That's it. No finance knowledge required.

---

## The Four AI Agents — Who Does What

### Agent 1 — The Quantitative Analyst ("The Math Brain")

**Job:** Crunch the hard numbers.

This agent behaves like a veteran Wall Street analyst who only trusts data. It pulls live financial figures from the internet and answers these questions:

| What it checks | What that means in plain English |
|---|---|
| P/E Ratio, EPS, Market Cap | Is the company expensive or cheap relative to its earnings? |
| 52-week price range | How has the stock moved over the past year? |
| RSI, MACD, Bollinger Bands | Is the stock on an upward trend or falling? Is it overbought? |
| Earnings history (last 4 quarters) | Has the company been beating or missing Wall Street's expectations? |
| DCF Intrinsic Value | What is the stock actually worth, based on future cash flows? |
| Performance vs S&P 500 | Is this stock beating or lagging the broader market? |

**Output:** A structured data report — numbers, charts descriptions, red flags, and green flags.

---

### Agent 2 — The Risk & Macro Analyst ("The Context Brain")

**Job:** Zoom out and assess the bigger picture.

This agent never looks at a stock in isolation. It asks: *even if the numbers look good, is the world working in this stock's favour right now?*

| What it checks | What that means in plain English |
|---|---|
| Options market (Put/Call Ratio) | Are professional traders placing big bets that the stock will fall? |
| Implied Volatility | How much price swing is the market expecting? |
| Sector performance | Is the whole industry doing well, or is this sector out of favour? |
| Fed Interest Rate | Are interest rates high? (High rates hurt growth stocks.) |
| Inflation (CPI) | Is inflation eating into company profits? |
| Unemployment & Yield Curve | Is the economy heading into a recession? |

It reads the Quantitative Analyst's findings and cross-checks them against these macro signals. For example: *"The P/E looks high — but are rising interest rates making that even riskier?"*

**Output:** A risk context report with a final **Risk Rating: Low / Medium / High**.

---

### Agent 3 — The Investment Strategist ("The Big Picture Brain")

**Job:** Read the news, connect all the dots, and deliver the verdict.

This is the senior agent. It reads everything the first two agents produced, then adds one final layer — **human narrative**. It searches the internet for the latest news, analyst opinions, and market rumours about the stock.

| What it does | Example |
|---|---|
| Reads the last 10 news headlines | "Did Nvidia just win a major government contract?" |
| Searches analyst ratings online | "What are Goldman Sachs and Morgan Stanley saying?" |
| Identifies catalysts | Product launches, lawsuits, leadership changes, earnings surprises |
| Combines numbers + risk + news | Builds the complete investment case |
| Issues a final verdict | **BUY**, **SELL**, or **HOLD** — with a written explanation |

The logic it follows:
- Good numbers + bullish trend + positive news = **BUY**
- Good numbers + high macro risk + mixed news = **HOLD** (with caution)
- Overvalued + bearish trend + negative sentiment = **SELL**

**Output:** A complete, professional Markdown investment report — the full document you see in the app.

---

### Agent 4 — The Report Publisher ("The Archivist") *(New)*

**Job:** Save and store the finished report to the cloud.

Once the Strategist delivers the report, this agent takes over and makes sure nothing is lost. It does two things:

1. **Saves a record to Azure PostgreSQL** (a cloud database) — so you can search and retrieve any past report by stock ticker and date.
2. **Uploads the full Markdown report to Azure Blob Storage** (cloud file storage) — so you have a permanent, shareable link to the document.

If the cloud services are not yet connected, this agent simply skips those steps and logs a note — it never crashes the pipeline.

**Output:** A confirmation message with the Azure Blob Storage URL where your report lives permanently.

---

## What Does the Final Report Look Like?

The report is formatted like a professional investment research note. It contains these sections:

```
# Investment Report: NVDA

## Executive Summary
One-paragraph summary of the key findings and verdict.

## Quantitative Snapshot
Key numbers: P/E, EPS, Beta, Market Cap, 52-week range.

## Technical Analysis Summary
Is the trend bullish or bearish? RSI, MACD, moving averages.

## Risk & Macro Assessment
Risk Rating: Medium. Interest rate environment, sector outlook.

## News & Market Sentiment
Top 3 recent headlines and what they mean for the stock.

## Valuation Assessment (DCF)
Estimated intrinsic value vs current market price. Over or undervalued?

## Final Verdict: BUY / SELL / HOLD
Clear one-line verdict with confidence level.

## Investment Thesis
2–3 paragraphs explaining the full reasoning behind the verdict.

## Key Risks to Watch
Bullet list of things that could make this verdict wrong.
```

You can read it on screen or download it as a Markdown file.

---

## Indian Stock Support

The application fully supports Indian stocks listed on **NSE** (National Stock Exchange) and **BSE** (Bombay Stock Exchange). No extra setup or API keys are needed — just use the correct ticker format.

### Ticker Format for Indian Stocks

| Exchange | Format | Examples |
|---|---|---|
| NSE | `SYMBOL.NS` | `TCS.NS`, `RELIANCE.NS`, `INFY.NS`, `HDFCBANK.NS` |
| BSE | `SYMBOL.BO` | `TCS.BO`, `RELIANCE.BO` |

### What Works vs What's Different for Indian Stocks

| Feature | US Stocks | Indian Stocks |
|---|---|---|
| Fundamentals (P/E, EPS, Market Cap) | S&P 500 companies | NSE/BSE companies |
| Technical Analysis (RSI, MACD, etc.) | Works | Works |
| DCF Valuation | Works | Works |
| Earnings History | Works | Works |
| News & Sentiment | Works | Works |
| Sector Benchmarking | vs US SPDR ETFs + SPY | vs NSE Sectoral Indices + Nifty 50 |
| Macro Indicators | US Fed Rate, US CPI, Unemployment | India CPI, Interest Rate, GDP, Nifty 50, Sensex, India VIX, USD/INR |
| Options Data | Available | Not available on Yahoo Finance — agent skips this step |

### Indian Sector Indices Used for Benchmarking

When you analyse an Indian stock, the app automatically benchmarks it against the correct NSE index:

| Sector | NSE Index Used |
|---|---|
| Technology (IT) | `^CNXIT` — Nifty IT Index |
| Banking / Financial Services | `^NSEBANK` — Nifty Bank Index |
| Healthcare / Pharma | `^CNXPHARMA` — Nifty Pharma Index |
| Consumer Goods (FMCG) | `^CNXFMCG` — Nifty FMCG Index |
| Automobiles | `^CNXAUTO` — Nifty Auto Index |
| Energy | `^CNXENERGY` — Nifty Energy Index |
| Metals & Mining | `^CNXMETAL` — Nifty Metal Index |
| Infrastructure / Industrials | `^CNXINFRA` — Nifty Infrastructure Index |
| Real Estate | `^CNXREALTY` — Nifty Realty Index |

All Indian stocks are also benchmarked against **Nifty 50 (`^NSEI`)** as the overall market index (equivalent to how US stocks are benchmarked against the S&P 500).

### Indian Macro Data Fetched Automatically

When analysing an Indian stock, Agent 2 (Risk & Macro Analyst) fetches:

| Indicator | Source |
|---|---|
| India CPI (Inflation Index) | FRED API (existing key) |
| India Long-Term Interest Rate | FRED API (existing key) |
| India GDP Growth Rate | FRED API (existing key) |
| Nifty 50 current level | Yahoo Finance (no key needed) |
| BSE Sensex current level | Yahoo Finance (no key needed) |
| India VIX (market fear index) | Yahoo Finance (no key needed) |
| USD/INR Exchange Rate | Yahoo Finance (no key needed) |

> **Note on RBI Repo Rate:** The RBI repo rate is not available via any free API. The app uses India's Long-Term Interest Rate as a proxy. For the exact current rate, visit [rbi.org.in](https://www.rbi.org.in).

### Example Indian Tickers to Try

| Company | Ticker |
|---|---|
| Tata Consultancy Services | `TCS.NS` |
| Reliance Industries | `RELIANCE.NS` |
| Infosys | `INFY.NS` |
| HDFC Bank | `HDFCBANK.NS` |
| Wipro | `WIPRO.NS` |
| ICICI Bank | `ICICIBANK.NS` |
| Tata Motors | `TATAMOTORS.NS` |
| Sun Pharmaceutical | `SUNPHARMA.NS` |
| Bajaj Finance | `BAJFINANCE.NS` |
| Larsen & Toubro | `LT.NS` |

---

## Where Does the Data Come From?

| Data Source | What It Provides |
|---|---|
| **Yahoo Finance** | Live stock prices, financials, earnings, Indian & US market data |
| **FRED (Federal Reserve)** | US economic data (rates, CPI) + India CPI, interest rate, GDP |
| **Firecrawl / Web Search** | Live news articles and analyst opinions from across the internet |
| **Azure PostgreSQL** | Your cloud database — stores every report you generate |
| **Azure Blob Storage** | Your cloud file store — keeps a permanent copy of every report |

---

## The Full Flow — From Click to Report

```
You type "NVDA" and click Run
          │
          ▼
  ┌─────────────────────┐
  │  Agent 1: Quant     │  ← Fetches numbers (P/E, RSI, DCF, earnings)
  └──────────┬──────────┘
             │ passes findings down
             ▼
  ┌─────────────────────┐
  │  Agent 2: Risk      │  ← Adds macro & options risk context
  └──────────┬──────────┘
             │ passes findings down
             ▼
  ┌─────────────────────┐
  │  Agent 3: Strategist│  ← Reads news, synthesises, issues BUY/SELL/HOLD
  └──────────┬──────────┘
             │ passes finished report down
             ▼
  ┌─────────────────────┐
  │  Agent 4: Publisher │  ← Saves to Azure DB + uploads to Blob Storage
  └──────────┬──────────┘
             │
             ▼
  Report displayed in browser
  Download button available
  Permanent cloud URL generated
```

---

## Technology Stack (for the curious)

| Component | Technology | Role |
|---|---|---|
| AI Agents | CrewAI + OpenAI GPT-4o | The "brains" that think and reason |
| Backend API | FastAPI (Python) | The server that runs everything |
| Frontend UI | Streamlit | The website you interact with |
| Database | Azure PostgreSQL | Stores report records |
| File Storage | Azure Blob Storage | Stores report files |
| Observability | LangSmith | Logs every agent's reasoning step |

---

## Disclaimer

This application is a research and learning tool. It does **not** constitute financial advice. Always consult a qualified financial advisor before making investment decisions.
