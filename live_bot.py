import yfinance as yf
import pandas as pd
import ta
import requests
import time
from datetime import datetime
import pytz

# ==========================
# TELEGRAM SETTINGS
# ==========================

TELEGRAM_TOKEN = "8795889545:AAF-N-CIRcEiIA80I1QSiQAPPTCJ2f1BZZE"
CHAT_ID = "5305099132"

def send_telegram(message):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    requests.post(url, data=payload)


# ==========================
# MARKETS TO SCAN
# ==========================

markets = {

    "GC=F": {
        "name": "GOLD",
        "session": (6, 15)
    },

    "EURUSD=X": {
        "name": "EURUSD",
        "session": (2, 10)
    },

    "USDJPY=X": {
        "name": "USDJPY",
        "session": (19, 3)
    },

    "GBPUSD=X": {
        "name": "GBPUSD",
        "session": (2, 10)
    }
}


last_signal_candle = {}


# ==========================
# SIGNAL FUNCTION
# ==========================

def check_market(symbol, info):

    global last_signal_candle

    try:

        data = yf.download(
            symbol,
            interval="5m",
            period="1d",
            progress=False
        )

        if data.empty:
            print(symbol, "No data")
            return

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        if data.index.tz is None:
            data.index = data.index.tz_localize("UTC").tz_convert("US/Eastern")
        else:
            data.index = data.index.tz_convert("US/Eastern")

        # indicators
        data["EMA50"] = data["Close"].ewm(span=50).mean()

        data["RSI"] = ta.momentum.RSIIndicator(
            data["Close"], window=14
        ).rsi()

        data["ATR"] = ta.volatility.AverageTrueRange(
            data["High"],
            data["Low"],
            data["Close"],
            window=14
        ).average_true_range()

        last = data.iloc[-2]
        prev = data.iloc[-3]

        candle_time = data.index[-2]

        price = last["Close"]
        ema = last["EMA50"]
        rsi = last["RSI"]
        atr = last["ATR"]

        print(
            info["name"],
            "Price:", round(price,2),
            "EMA:", round(ema,2),
            "RSI:", round(rsi,2)
        )

        # ==========================
        # SESSION CHECK
        # ==========================

        hour = candle_time.hour
        start, end = info["session"]

        if start < end:
            if not (start <= hour < end):
                return
        else:
            if not (hour >= start or hour < end):
                return

        # ==========================
        # TREND
        # ==========================

        ema_slope = last["EMA50"] - data["EMA50"].iloc[-6]

        bullish = price > ema and ema_slope > 0
        bearish = price < ema and ema_slope < 0

        pullback = abs(price - ema) / ema < 0.01

        rsi_up = last["RSI"] > prev["RSI"]
        rsi_down = last["RSI"] < prev["RSI"]

        # prevent duplicate signals
        if symbol in last_signal_candle:

            if last_signal_candle[symbol] == candle_time:
                return

        # ==========================
        # BUY SIGNAL
        # ==========================

        if bullish and rsi > 52 and pullback and rsi_up:

            stop = price - atr
            target = price + (2 * atr)

            message = f"""
🟢 {info['name']} BUY SIGNAL

Entry: {round(price,2)}
Stop: {round(stop,2)}
Target: {round(target,2)}
RR: 1:2
Time: {datetime.now(pytz.timezone("Asia/Kolkata"))}
"""

            send_telegram(message)

            last_signal_candle[symbol] = candle_time

        # ==========================
        # SELL SIGNAL
        # ==========================

        elif bearish and rsi < 48 and pullback and rsi_down:

            stop = price + atr
            target = price - (2 * atr)

            message = f"""
🔴 {info['name']} SELL SIGNAL

Entry: {round(price,2)}
Stop: {round(stop,2)}
Target: {round(target,2)}
RR: 1:2
Time: {datetime.now(pytz.timezone("Asia/Kolkata"))}
"""

            send_telegram(message)

            last_signal_candle[symbol] = candle_time

    except Exception as e:

        print(symbol, "error:", e)


# ==========================
# MAIN LOOP
# ==========================

print("Multi-Market Trading Bot Started")

while True:

    for symbol, info in markets.items():

        check_market(symbol, info)

    time.sleep(300)