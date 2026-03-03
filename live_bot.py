import yfinance as yf
import pandas as pd
import ta
import requests
import time
from datetime import datetime
import pytz

# =======================
# 🔐 TELEGRAM SETTINGS
# =======================

TELEGRAM_TOKEN = "8795889545:AAF-N-CIRcEiIA80I1QSiQAPPTCJ2f1BZZE"
CHAT_ID = "5305099132"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload)

# =======================
# 📊 STRATEGY FUNCTION
# =======================

def check_signal():
    data = yf.download(
        "GC=F",
        interval="5m",
        period="1d",
        auto_adjust=True,
        progress=False
    )

    if data is None or data.empty:
        return

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Convert to EST
    if data.index.tz is None:
        data.index = data.index.tz_localize("UTC").tz_convert("US/Eastern")
    else:
        data.index = data.index.tz_convert("US/Eastern")

    data["EMA50"] = data["Close"].ewm(span=50).mean()
    data["RSI"] = ta.momentum.RSIIndicator(data["Close"], window=14).rsi()
    data["ATR"] = ta.volatility.AverageTrueRange(
        data["High"],
        data["Low"],
        data["Close"],
        window=14
    ).average_true_range()

    last = data.iloc[-1]
    prev = data.iloc[-2]

    current_time = data.index[-1].time()

    # Session filter (7–13 EST)
   # if not (7 <= current_time.hour < 13):
   #     return

    price = last["Close"]
    ema = last["EMA50"]
    rsi = last["RSI"]
    atr = last["ATR"]

    ema_slope = last["EMA50"] - data["EMA50"].iloc[-5]
    pullback = abs(price - ema) / ema < 0.002

    range_size = last["High"] - last["Low"]
    body_size = abs(last["Close"] - last["Open"])

    if range_size == 0 or atr == 0:
        return

    strong_bull = body_size > range_size * 0.65 and last["Close"] > last["Open"]
    strong_bear = body_size > range_size * 0.65 and last["Close"] < last["Open"]

    rsi_up = last["RSI"] > prev["RSI"]
    rsi_down = last["RSI"] < prev["RSI"]

    # ================= BULLISH =================
    if (
        price > ema
        and rsi > 55
        and ema_slope > 0
        and pullback
        and strong_bull
        and rsi_up
    ):
        stop = price - atr
        target = price + (2 * atr)

        message = f"""
🟢 GOLD BUY SIGNAL

Entry: {round(price,2)}
Stop: {round(stop,2)}
Target: {round(target,2)}
RR: 1:2
Time: {datetime.now()}
"""
        send_telegram(message)

    # ================= BEARISH =================
    elif (
        price < ema
        and rsi < 45
        and ema_slope < 0
        and pullback
        and strong_bear
        and rsi_down
    ):
        stop = price + atr
        target = price - (2 * atr)

        message = f"""
🔴 GOLD SELL SIGNAL

Entry: {round(price,2)}
Stop: {round(stop,2)}
Target: {round(target,2)}
RR: 1:2
Time: {datetime.now()}
"""
        send_telegram(message)


# =======================
# 🔄 LOOP EVERY 5 MIN
# =======================

print("Gold Live Bot Started...")

while True:
    try:
        check_signal()
        time.sleep(300)  # 5 minutes
    except Exception as e:
        print("Error:", e)
        time.sleep(60)