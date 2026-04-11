import streamlit as st
import yfinance as yf

st.title("QQQ Quick Dashboard")

data = yf.download("QQQ", period="1d", interval="5m")

if data.empty:
    st.write("Waiting for data...")
else:
    price = data["Close"].iloc[-1]
    prev = data["Close"].iloc[-2]

    if price > prev:
        signal = "CALL 🚀"
    elif price < prev:
        signal = "PUT 🔻"
    else:
        signal = "WAIT ❌"

    st.metric("Price", round(price,2))
    st.write("Signal:", signal)
