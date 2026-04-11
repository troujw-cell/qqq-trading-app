
import yfinance as yf
import pandas as pd
import requests
import time

BOT_TOKEN = "PASTE_TOKEN"
CHAT_ID = "PASTE_CHAT_ID"

trade_count = 0
losses = 0

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def run():
    global trade_count

    if trade_count >= 3:
        send("STOP: Max trades hit")
        return

    data = yf.download("QQQ", period="1d", interval="1m").dropna()

    opening = data.between_time("09:30","09:45")
    or_high = opening["High"].max()
    or_low = opening["Low"].min()

    data['tp'] = (data['High']+data['Low']+data['Close'])/3
    data['vwap'] = (data['tp']*data['Volume']).cumsum()/data['Volume'].cumsum()

    latest = data.iloc[-1]
    prev = data.iloc[-2]

    price = latest["Close"]
    vwap = latest["vwap"]

    signal = None

    if price > or_high and price > vwap:
        signal = "CALL"
    elif price < or_low and price < vwap:
        signal = "PUT"

    if signal:
        msg = f"QQQ ALERT: BUY {signal} at {round(price,2)}"
        send(msg)
        trade_count += 1

while True:
    run()
    time.sleep(60)
