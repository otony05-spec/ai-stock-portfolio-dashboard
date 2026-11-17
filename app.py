
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="AI Stock Portfolio Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 AI Stock Portfolio Dashboard")
st.caption("Portfolio Intelligence | Tony · Priyanka · Chitti")

st.sidebar.header("Portfolio Data")
uploaded_file = st.sidebar.file_uploader(
    "Upload your portfolio Excel workbook",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("Please upload your Stock_Portfolio_Active_Portfolios.xlsx workbook to begin.")
    st.stop()

df = pd.read_excel(uploaded_file, sheet_name="Transactions")

# Portfolio filter
portfolio_names = {
    "P01": "Tony",
    "P02": "Priyanka",
    "P05": "Chitti"
}

df["Portfolio_Name"] = df["Portfolio_ID"].map(portfolio_names)

selected = st.sidebar.selectbox(
    "Select Portfolio",
    ["All Portfolios", "Tony", "Priyanka", "Chitti"]
)

if selected != "All Portfolios":
    data = df[df["Portfolio_Name"] == selected].copy()
else:
    data = df.copy()

# KPI calculations
total_transactions = len(data)
buy_count = (data["Transaction_Type"] == "BUY").sum()
sell_count = (data["Transaction_Type"] == "SELL").sum()
unique_stocks = data["Stock_Name"].nunique()

st.subheader("Portfolio Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Transactions", total_transactions)
c2.metric("Buy Trades", buy_count)
c3.metric("Sell Trades", sell_count)
c4.metric("Unique Stocks", unique_stocks)

st.divider()

# Charts
left, right = st.columns(2)

with left:
    st.subheader("Transaction Activity")
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

# Transaction history
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
