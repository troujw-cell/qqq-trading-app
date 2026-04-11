
import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(layout="wide")
st.title("QQQ One-Screen Trading Dashboard")

ticker = "QQQ"
import time

data = None

for i in range(3):  # retry 3 times
    try:
        data = yf.download(ticker, period="1d", interval="1m")
        if not data.empty:
            break
    except:
        time.sleep(2)

if data is None or data.empty:
    st.error("⚠️ Failed to load market data. Refresh in a moment.")
    st.stop()

data = data.dropna()

# Opening Range
opening = data.between_time("09:30", "09:45")
or_high = opening["High"].max()
or_low = opening["Low"].min()

# VWAP
data['tp'] = (data['High'] + data['Low'] + data['Close']) / 3
data['vwap'] = (data['tp'] * data['Volume']).cumsum() / data['Volume'].cumsum()

latest = data.iloc[-1]
prev = data.iloc[-2]

price = latest["Close"]
vwap = latest["vwap"]

signal = "NO TRADE"

if price > or_high and price > vwap:
    signal = "BUY CALL 🚀"
elif price < or_low and price < vwap:
    signal = "BUY PUT 🔻"
elif price > vwap and prev["Close"] < prev["vwap"]:
    signal = "VWAP RECLAIM → CALL"
elif price < vwap and prev["Close"] > prev["vwap"]:
    signal = "VWAP REJECT → PUT"

col1, col2, col3 = st.columns(3)
col1.metric("Price", round(price,2))
col2.metric("VWAP", round(vwap,2))
col3.metric("Signal", signal)

st.markdown("---")
st.write(f"OR High: {round(or_high,2)} | OR Low: {round(or_low,2)}")

st.line_chart(data[['Close','vwap']].tail(50))

# Performance
try:
    df = pd.read_csv("results.csv")
    total = len(df)
    wins = len(df[df["result"]=="win"])
    win_rate = (wins/total)*100 if total>0 else 0

    st.markdown("---")
    st.subheader("Performance")
    st.metric("Trades", total)
    st.metric("Win Rate", f"{win_rate:.1f}%")
except:
    st.write("No trade data yet.")
