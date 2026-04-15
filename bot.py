import os
import time
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# =========================
# ENV VARIABLES
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.get(url, params=params)
    except:
        pass

# =========================
# SETTINGS
# =========================
SYMBOL = "SPY"   # proxy for XSP
INTERVAL = "1m"

last_signal = None
last_alert_time = 0
ALERT_COOLDOWN = 900  # 15 minutes

# =========================
# TIME FILTER (FIRST 90 MIN)
# =========================
def market_open_filter():
    now = datetime.utcnow() - timedelta(hours=4)  # EST
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    cutoff = market_open + timedelta(minutes=90)
    return market_open <= now <= cutoff

# =========================
# EXPECTED MOVE FILTER
# =========================
def expected_move_filter(data):
    high = data["High"].max()
    low = data["Low"].min()
    current = data["Close"].iloc[-1]

    if current > high * 0.995 or current < low * 1.005:
        return False
    return True

# =========================
# MAIN LOOP
# =========================
while True:
    try:
        if not market_open_filter():
            time.sleep(60)
            continue

        data = yf.download(SYMBOL, period="1d", interval=INTERVAL)

        if data.empty or len(data) < 20:
            time.sleep(60)
            continue

        # =========================
        # VWAP
        # =========================
        data["tp"] = (data["High"] + data["Low"] + data["Close"]) / 3
        data["vwap"] = (data["tp"] * data["Volume"]).cumsum() / data["Volume"].cumsum()

        price = data["Close"].iloc[-1]
        prev = data.iloc[-2]
        vwap = data["vwap"].iloc[-1]

        # =========================
        # MOMENTUM FILTER
        # =========================
        candle_body = abs(data["Close"] - data["Open"])
        candle_range = data["High"] - data["Low"]

        strong_candle = (candle_body / candle_range) > 0.6

        recent_high = data["High"].rolling(5).max()
        recent_low = data["Low"].rolling(5).min()

        breakout_up = price > recent_high.iloc[-2]
        breakout_down = price < recent_low.iloc[-2]

        avg_range = (data["High"] - data["Low"]).rolling(10).mean()
        expansion = candle_range.iloc[-1] > avg_range.iloc[-1]

        strong_momentum = (
            strong_candle.iloc[-1]
            and expansion
            and (breakout_up or breakout_down)
        )

        # =========================
        # RSI FILTER
        # =========================
        delta = data["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()

        rs = gain / loss
        data["rsi"] = 100 - (100 / (1 + rs))
        rsi = data["rsi"].iloc[-1]

        bullish_rsi = rsi > 60
        bearish_rsi = rsi < 40
        chop_rsi = 45 < rsi < 55

        if chop_rsi:
            time.sleep(60)
            continue

        # =========================
        # EXPECTED MOVE FILTER
        # =========================
        if not expected_move_filter(data):
            time.sleep(60)
            continue

        # =========================
        # SIGNAL LOGIC
        # =========================
        setup_type = None
        confidence = 0

        # A+ setups
        if price > vwap and prev["Close"] < prev["vwap"] and strong_momentum and bullish_rsi:
            setup_type = "A+ CALL 🚀"
            confidence = 95

        elif price < vwap and prev["Close"] > prev["vwap"] and strong_momentum and bearish_rsi:
            setup_type = "A+ PUT 🔻"
            confidence = 95

        # A setups
        elif price > vwap and breakout_up and bullish_rsi:
            setup_type = "A CALL ⚡"
            confidence = 78

        elif price < vwap and breakout_down and bearish_rsi:
            setup_type = "A PUT ⚡"
            confidence = 78

        # =========================
        # ALERT SYSTEM (NO DUPES)
        # =========================
        current_time = time.time()

        if setup_type:
            if setup_type == last_signal and (current_time - last_alert_time) < ALERT_COOLDOWN:
                time.sleep(60)
                continue

            size = "2 contracts" if "A+" in setup_type else "1 contract"

            message = f"""
🚨 {setup_type}

Confidence: {confidence}%

💰 Size: {size}
🎯 Target: +50%
🛑 Stop: -30%
"""

            send_alert(message)

            last_signal = setup_type
            last_alert_time = current_time

            time.sleep(300)

        time.sleep(60)

    except Exception as e:
        print("Error:", e)
        time.sleep(60)
