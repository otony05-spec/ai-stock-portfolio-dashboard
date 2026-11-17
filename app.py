
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json

st.set_page_config(
    page_title="AI Stock Portfolio Dashboard",
    page_icon="📈",
    layout="wide"
)

# ---------------- CONFIGURATION ----------------

st.title("📈 AI Stock Portfolio Dashboard")
st.caption("Portfolio Intelligence | Tony · Priyanka · Chitti")

try:
    API_KEY = st.secrets["OPENROUTER_API_KEY"]
except Exception:
    API_KEY = None

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"

# ---------------- DATA UPLOAD ----------------

st.sidebar.header("Portfolio Data")

uploaded_file = st.sidebar.file_uploader(
    "Upload updated Excel workbook",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("Upload your Stock_Portfolio_Active_Portfolios.xlsx workbook to begin.")
    st.stop()

try:
    df = pd.read_excel(
        uploaded_file,
        sheet_name="Transactions"
    )
except Exception as e:
    st.error(f"Unable to read workbook: {e}")
    st.stop()

required = [
    "Portfolio_ID", "Trade_Date", "Stock_Name",
    "Transaction_Type", "Quantity",
    "Price_Per_Share", "Net_Amount"
]

if not all(col in df.columns for col in required):
    st.error("Workbook is missing required transaction columns.")
    st.stop()

portfolio_names = {
    "P01": "Tony",
    "P02": "Priyanka",
    "P05": "Chitti"
}

df["Portfolio_Name"] = df["Portfolio_ID"].map(portfolio_names)
df["Trade_Date"] = pd.to_datetime(
    df["Trade_Date"], errors="coerce"
)

# ---------------- PORTFOLIO FILTER ----------------

st.sidebar.subheader("Portfolio Filter")

selected = st.sidebar.selectbox(
    "Select Portfolio",
    ["All Portfolios", "Tony", "Priyanka", "Chitti"]
)

if selected == "All Portfolios":
    data = df.copy()
else:
    data = df[df["Portfolio_Name"] == selected].copy()

# ---------------- KPI CARDS ----------------

st.subheader("Portfolio Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Transactions", len(data))
c2.metric(
    "Buy Trades",
    int((data["Transaction_Type"] == "BUY").sum())
)
c3.metric(
    "Sell Trades",
    int((data["Transaction_Type"] == "SELL").sum())
)
c4.metric("Unique Stocks", data["Stock_Name"].nunique())

st.divider()

# ---------------- CHARTS ----------------

left, right = st.columns(2)

with left:
    st.subheader("Buy / Sell Distribution")

    activity = (
        data.groupby("Transaction_Type")
        .size()
        .reset_index(name="Count")
    )

    fig = px.pie(
        activity,
        names="Transaction_Type",
        values="Count",
        hole=0.45
    )

    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Portfolio Comparison")

    comparison = (
        df.groupby("Portfolio_Name")
        .size()
        .reset_index(name="Transactions")
    )

    fig = px.bar(
        comparison,
        x="Portfolio_Name",
        y="Transactions",
        color="Portfolio_Name"
    )

    st.plotly_chart(fig, use_container_width=True)

# ---------------- TRANSACTION HISTORY ----------------

st.subheader("Transaction History")

search = st.text_input("Search stock name")

if search:
    data = data[
        data["Stock_Name"].str.contains(
            search, case=False, na=False
        )
    ]

st.dataframe(
    data.sort_values("Trade_Date", ascending=False),
    use_container_width=True,
    hide_index=True
)

# ---------------- AI PYTHON TOOLS ----------------

def portfolio_summary():
    output = []

    for pid, name in portfolio_names.items():
        rows = df[df["Portfolio_ID"] == pid]

        output.append({
            "portfolio": name,
            "transactions": len(rows),
            "buys": int((rows["Transaction_Type"] == "BUY").sum()),
            "sells": int((rows["Transaction_Type"] == "SELL").sum()),
            "unique_stocks": int(rows["Stock_Name"].nunique())
        })

    return output


def stock_history(stock_name):
    rows = df[
        df["Stock_Name"].str.lower()
        == stock_name.lower()
    ]

    columns = [
        "Portfolio_Name",
        "Trade_Date",
        "Stock_Name",
        "Transaction_Type",
        "Quantity",
        "Price_Per_Share",
        "Net_Amount"
    ]

    result = rows[columns].copy()
    result["Trade_Date"] = result["Trade_Date"].astype(str)

    return {
        "transactions": result.fillna("Not recorded").to_dict("records"),
        "total_transactions": len(result),
        "buy_count": int((result["Transaction_Type"] == "BUY").sum()),
        "sell_count": int((result["Transaction_Type"] == "SELL").sum())
    }


def data_quality_report():
    return df.isnull().sum().to_dict()


available_tools = {
    "portfolio_summary": portfolio_summary,
    "stock_history": stock_history,
    "data_quality_report": data_quality_report
}

tools = [
    {
        "type": "function",
        "function": {
            "name": "portfolio_summary",
            "description": "Get transaction summaries for all portfolios.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stock_history",
            "description": "Get transaction history for a specific stock across all portfolios.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_name": {
                        "type": "string",
                        "description": "Name of the stock, such as HAL or Tata Motors."
                    }
                },
                "required": ["stock_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "data_quality_report",
            "description": "Get missing-value counts from the workbook.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

SYSTEM_PROMPT = """
You are a professional stock portfolio analysis assistant.

The workbook contains three portfolios:
Tony (P01), Priyanka (P02), and Chitti (P05).

Use the available Python tools to retrieve portfolio facts.

Rules:
- Never invent transactions, quantities, prices or totals.
- Use tool results as the source of transaction facts.
- Calculate counts only from actual returned records.
- Distinguish recorded data from calculated values.
- Do not claim current market prices.
- Do not treat missing values as zero.
- Explain when information is unavailable.
- Present financial information clearly.
"""

# ---------------- AI ASSISTANT ----------------

st.divider()
st.subheader("🤖 AI Portfolio Assistant")

if not API_KEY:
    st.warning(
        "OpenRouter API key not found. "
        "Configure OPENROUTER_API_KEY in Streamlit Secrets."
    )
else:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]):
            st.markdown(chat["content"])

    question = st.chat_input(
        "Ask about your stock portfolio..."
    )

    if question:
        st.session_state.chat_history.append({
            "role": "user",
            "content": question
        })

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Analysing your portfolio..."):

                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT}
                ]

                messages.extend(
                    st.session_state.chat_history[-10:]
                )

                try:
                    answer = None

                    for _ in range(4):
                        payload = {
                            "model": MODEL,
                            "messages": messages,
                            "tools": tools,
                            "tool_choice": "auto"
                        }

                        response = requests.post(
                            API_URL,
                            headers={
                                "Authorization": f"Bearer {API_KEY}",
                                "Content-Type": "application/json"
                            },
                            json=payload,
                            timeout=120
                        )

                        response.raise_for_status()

                        assistant_message = response.json()[
                            "choices"
                        ][0]["message"]

                        tool_calls = assistant_message.get(
                            "tool_calls"
                        )

                        if not tool_calls:
                            answer = assistant_message.get(
                                "content"
                            ) or "No response generated."
                            break

                        messages.append(assistant_message)

                        for call in tool_calls:
                            name = call["function"]["name"]

                            if name not in available_tools:
                                raise ValueError(
                                    "Requested tool is not permitted."
                                )

                            arguments = json.loads(
                                call["function"]["arguments"]
                            )

                            result = available_tools[name](
                                **arguments
                            )

                            messages.append({
                                "role": "tool",
                                "tool_call_id": call["id"],
                                "content": json.dumps(
                                    result, default=str
                                )
                            })

                    if answer is None:
                        answer = (
                            "I could not complete the analysis. "
                            "Please try a simpler question."
                        )

                except Exception as e:
                    answer = f"AI request failed: {str(e)}"

                st.markdown(answer)

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": answer
        })

    if st.button("Clear chat"):
        st.session_state.chat_history = []
        st.rerun()

