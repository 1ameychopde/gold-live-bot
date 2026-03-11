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
# GLOBAL MEMORY
# ==========================

last_signal_candle = None


# ==========================
# SIGNAL LOGIC
# ==========================

def check_signal():

    global last_signal_candle

    try:

        data = yf.download(
            "GC=F",
            interval="5m",
            period="1d",
            progress=False
        )

        if data.empty:
            print("No data")
            return

        # Fix columns
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Convert timezone to EST
        if data.index.tz is None:
            data.index = data.index.tz_localize("UTC").tz_convert("US/Eastern")
        else:
            data.index = data.index.tz_convert("US/Eastern")

        # ==========================
        # INDICATORS
        # ==========================

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

        # Use CLOSED candles only
        last = data.iloc[-2]
        prev = data.iloc[-3]

        candle_time = data.index[-2]

        price = last["Close"]
        ema = last["EMA50"]
        rsi = last["RSI"]
        atr = last["ATR"]

        print(
            "Price:", round(price,2),
            "EMA:", round(ema,2),
            "RSI:", round(rsi,2),
            "ATR:", round(atr,2)
        )

        # ==========================
        # SESSION FILTER
        # ==========================

        current_time = candle_time.time()

        if not (6 <= current_time.hour < 15):
            print("Outside session")
            return

        # ==========================
        # TREND CONDITIONS
        # ==========================

        ema_slope = last["EMA50"] - data["EMA50"].iloc[-6]

        bullish_trend = price > ema and ema_slope > 0
        bearish_trend = price < ema and ema_slope < 0

        # ==========================
        # PULLBACK CONDITION
        # ==========================

        pullback = abs(price - ema) / ema < 0.01

        rsi_up = last["RSI"] > prev["RSI"]
        rsi_down = last["RSI"] < prev["RSI"]

        # ==========================
        # PREVENT DUPLICATE SIGNALS
        # ==========================

        if candle_time == last_signal_candle:
            print("Signal already sent for this candle")
            return

        # ==========================
        # BUY SIGNAL
        # ==========================

        if bullish_trend and rsi > 52 and pullback and rsi_up:

            stop = price - atr
            target = price + (2 * atr)

            message = f"""
🟢 GOLD BUY SIGNAL

Entry: {round(price,2)}
Stop: {round(stop,2)}
Target: {round(target,2)}
RR: 1:2
Time: {datetime.now(pytz.timezone("Asia/Kolkata"))}
"""

            print("BUY SIGNAL")

            send_telegram(message)

            last_signal_candle = candle_time

        # ==========================
        # SELL SIGNAL
        # ==========================

        elif bearish_trend and rsi < 48 and pullback and rsi_down:

            stop = price + atr
            target = price - (2 * atr)

            message = f"""
🔴 GOLD SELL SIGNAL

Entry: {round(price,2)}
Stop: {round(stop,2)}
Target: {round(target,2)}
RR: 1:2
Time: {datetime.now(pytz.timezone("Asia/Kolkata"))}
"""

            print("SELL SIGNAL")

            send_telegram(message)

            last_signal_candle = candle_time

        else:

            print("No setup")

    except Exception as e:

        print("Error:", e)


# ==========================
# BOT LOOP
# ==========================

print("Gold Live Bot Started")

while True:

    check_signal()

    time.sleep(300)