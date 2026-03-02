import yfinance as yf
import pandas as pd
import ta


def check_signal():
    print("Checking market...\n")

    # Download 5m Gold Futures data
    data = yf.download(
        "GC=F",
        interval="5m",
        period="3d",
        auto_adjust=True
    )

    if data.empty or len(data) < 60:
        print("Not enough data.")
        return

    # Fix MultiIndex columns if present
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Ensure Close column is 1D Series
    close_series = data["Close"].squeeze()

    # Calculate EMA 50
    data["EMA50"] = close_series.ewm(span=50).mean()

    # Calculate RSI 14
    rsi_indicator = ta.momentum.RSIIndicator(close_series, window=14)
    data["RSI"] = rsi_indicator.rsi()

    # Get latest candles
    last = data.iloc[-1]
    prev = data.iloc[-2]

    price = last["Close"]
    ema = last["EMA50"]
    rsi = last["RSI"]

    # EMA slope check (last 5 candles)
    ema_slope = data["EMA50"].iloc[-1] - data["EMA50"].iloc[-5]

    # Pullback detection (price near EMA within 0.3%)
    pullback = abs(price - ema) / ema < 0.003

    # Candle strength calculation
    range_size = last["High"] - last["Low"]
    body_size = abs(last["Close"] - last["Open"])

    if range_size == 0:
        print("Zero range candle. Skipping.")
        return

    strong_bull = (
        body_size > range_size * 0.6
        and last["Close"] > last["Open"]
    )

    strong_bear = (
        body_size > range_size * 0.6
        and last["Close"] < last["Open"]
    )

    # 🟢 Bullish Setup
    if (
        price > ema
        and rsi > 50
        and ema_slope > 0
        and pullback
        and strong_bull
    ):
        stop = last["Low"] - 2
        target = price + (price - stop) * 2

        print("🟢 BUY SIGNAL")
        print(f"Entry: {price:.2f}")
        print(f"Stop Loss: {stop:.2f}")
        print(f"Target (1:2 RR): {target:.2f}")

    # 🔴 Bearish Setup
    elif (
        price < ema
        and rsi < 50
        and ema_slope < 0
        and pullback
        and strong_bear
    ):
        stop = last["High"] + 2
        target = price - (stop - price) * 2

        print("🔴 SELL SIGNAL")
        print(f"Entry: {price:.2f}")
        print(f"Stop Loss: {stop:.2f}")
        print(f"Target (1:2 RR): {target:.2f}")

    else:
        print("No valid setup.\n")


if __name__ == "__main__":
    check_signal()