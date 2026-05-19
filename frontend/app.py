import sys
import os
import streamlit as st

# Make src/ importable when running from Streamlit Cloud (repo root = /mount/src/<repo>)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# === Page Setup ===
st.set_page_config(
    page_title="AI Financial Analyst Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
    h1 { color: #0066cc; }
</style>
""", unsafe_allow_html=True)


def _detect_market(ticker: str) -> str:
    upper = ticker.upper()
    if upper.endswith(".NS") or upper.endswith(".BO"):
        return "India (NSE/BSE)"
    return "US"


def _extract_blob_url(report_text: str) -> str:
    for line in report_text.splitlines():
        if "blob.core.windows.net" in line:
            parts = line.split("https://", 1)
            if len(parts) == 2:
                return "https://" + parts[1].strip()
    return ""


def _check_db_saved(report_text: str) -> bool:
    lower = report_text.lower()
    return "saved to azure postgresql" in lower or "saved" in lower


def run_analysis(ticker: str) -> dict:
    from src.agents.crew import run_financial_crew
    result_object = run_financial_crew(ticker)
    report_text = str(result_object)
    return {
        "status": "success",
        "ticker": ticker,
        "market": _detect_market(ticker),
        "report_content": report_text,
        "report_url": _extract_blob_url(report_text),
        "db_saved": _check_db_saved(report_text),
        "message": f"Analysis complete for {ticker} ({_detect_market(ticker)}).",
    }


# === Main Header ===
st.title("🤖 AI Agent Financial Analyst")
st.markdown(
    """
    Welcome! This tool leverages a **multi-agent AI team** (powered by CrewAI) to perform
    comprehensive financial research on a given stock ticker.

    It fetches live data, analyzes market sentiment, and generates a professional investment report,
    saving everything to **Azure Cloud**.
    """
)
st.divider()

# === Sidebar ===
with st.sidebar:
    st.header("⚙️ Control Panel")

    ticker_input = st.text_input(
        "Enter Stock Ticker Symbol",
        value="",
        placeholder="e.g., NVDA, MSFT, TSLA",
        max_chars=10,
        help="Enter the standard ticker symbol. Add .NS or .BO suffix for Indian stocks."
    ).upper().strip()

    run_button = st.button("🚀 Run Full Analysis", type="primary")

    st.markdown("---")
    st.info("**Note:** A full analysis typically takes 1-3 minutes.")

# === Main Logic ===
if run_button:
    if not ticker_input:
        st.error("⚠️ Please enter a ticker symbol before running the analysis.")
    else:
        if 'analysis_result' in st.session_state:
            del st.session_state['analysis_result']

        with st.spinner(f"🧠 AI Agents are researching '{ticker_input}'... Please hold..."):
            try:
                data = run_analysis(ticker_input)
                st.session_state['analysis_result'] = data
                st.success(f"✅ Analysis for {ticker_input} complete!")
            except Exception as e:
                st.error(f"❌ Analysis failed: {e}")

# === Display Results ===
if 'analysis_result' in st.session_state:
    data = st.session_state['analysis_result']
    ticker_name = data.get("ticker", ticker_input)

    tab1, tab2 = st.tabs(["📄 Final Investment Report", "🔍 Metadata & Logs"])

    with tab1:
        st.subheader(f"Investment Analysis: {ticker_name}")
        report_content = data.get("report_content", "*No report content found.*")
        st.markdown(report_content)
        st.divider()
        st.download_button(
            label="📥 Download Report as Markdown",
            data=report_content,
            file_name=f"{ticker_name}_Investment_Report.md",
            mime="text/markdown"
        )

    with tab2:
        st.subheader("Backend Execution Details")
        blob_url = data.get('report_url', '')
        if blob_url:
            st.markdown(f"**Azure Blob Storage URL:** [Link to File]({blob_url})")
        else:
            st.markdown("**Azure Blob Storage URL:** Not available")
        st.markdown(f"**Market:** {data.get('market')}")
        st.markdown(f"**Status:** {data.get('status')}")
        st.markdown(f"**Message:** {data.get('message')}")

        with st.expander("See Raw Response (JSON)"):
            st.json(data)
