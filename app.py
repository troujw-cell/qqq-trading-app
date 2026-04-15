import time
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RISK_PER_TRADE = 100  # 🔥 YOU CAN CHANGE THIS

def send_alert(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

def get_data(symbol):
    for _ in range(3):
        try:
            df = yf.download(symbol, period="1d", interval="1m", progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                return df.dropna()
        except:
            time.sleep(2)
    return None

last_alert = ""
last_trade_time = 0

while True:
    try:
        spy = get_data("SPY")

        if spy is None or len(spy) < 5:
            time.sleep(60)
            continue

        now = datetime.now()

        # ⏰ FIRST 90 MINUTES ONLY
        if not (9 <= now.hour < 11):
            time.sleep(60)
            continue

        # ===== OPENING RANGE =====
        opening = spy.between_time("09:30", "09:45")
        if opening.empty:
            time.sleep(60)
            continue

        or_high = float(opening["High"].max())
        or_low = float(opening["Low"].min())

        # ===== VWAP =====
        tp = (spy["High"] + spy["Low"] + spy["Close"]) / 3
        spy["vwap"] = (tp * spy["Volume"]).cumsum() / spy["Volume"].cumsum()

        latest = spy.iloc[-1]
        prev = spy.iloc[-2]

        price = float(latest["Close"])
        vwap = float(latest["vwap"])

        # ===== MOMENTUM (A+ FILTER) =====
        momentum = abs(price - prev["Close"])

        # ===== EXPECTED MOVE FILTER =====
        expected_move = spy["Close"].std() * 2
        move_from_open = abs(price - spy["Open"].iloc[0])
        valid_day = move_from_open > expected_move * 0.4  # stricter

        if not valid_day:
            time.sleep(60)
            continue

        # ===== SIGNAL =====
        signal = None

        if price > or_high and price > vwap and momentum > 0.15:
            signal = "XSP CALL 🚀"

        elif price < or_low and price < vwap and momentum > 0.15:
            signal = "XSP PUT 🔻"

        if signal is None:
            time.sleep(60)
            continue

        # ===== CONFIDENCE (STRICT) =====
        score = 0

        if price > or_high or price < or_low:
            score += 30

        if abs(price - vwap) > 0.25:
            score += 25

        if momentum > 0.2:
            score += 25

        if spy["Volume"].iloc[-1] > spy["Volume"].mean():
            score += 20

        confidence = min(score, 100)

        # 🔥 A+ ONLY
        if confidence < 85:
            time.sleep(60)
            continue

        # ===== COOLDOWN =====
        if time.time() - last_trade_time < 900:
            time.sleep(60)
            continue

        # ===== MONEY MANAGEMENT =====
        # Assume option costs ~$1.50 (can adjust)
        option_price = 1.5
        contracts = int(RISK_PER_TRADE / (option_price * 100))

        target = option_price * 1.5   # 50% gain
        stop = option_price * 0.7     # 30% loss

        msg = (
            f"🚨 A+ {signal}\n"
            f"SPY: {price:.2f}\n"
            f"Confidence: {confidence}%\n\n"
            f"💰 Size: {contracts} contracts\n"
            f"🎯 Target: +50%\n"
            f"🛑 Stop: -30%\n\n"
            f"Time: {now.strftime('%H:%M')}"
        )

        if msg != last_alert:
            send_alert(msg)
            last_alert = msg
            last_trade_time = time.time()

        time.sleep(60)

    except Exception as e:
        print("Error:", e)
        time.sleep(60)
