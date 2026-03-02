import yfinance as yf
import pandas as pd
import ta

print("Running 60-Day Backtest with Smart Trailing Stop...\n")

data = yf.download(
    "GC=F",
    interval="5m",
    period="60d",
    auto_adjust=True,
    progress=False
)

if data is None or data.empty:
    print("Data download failed.")
    exit()

if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)

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

equity = 0
peak_equity = 0
max_drawdown = 0
losing_streak = 0
max_losing_streak = 0

wins = 0
losses = 0
total_trades = 0

for i in range(60, len(data) - 20):

    current_time = data.index[i].time()

    if not (7 <= current_time.hour < 13):
        continue

    price = data["Close"].iloc[i]
    ema = data["EMA50"].iloc[i]
    rsi = data["RSI"].iloc[i]
    atr = data["ATR"].iloc[i]

    ema_slope = data["EMA50"].iloc[i] - data["EMA50"].iloc[i - 5]
    pullback = abs(price - ema) / ema < 0.002

    candle = data.iloc[i]
    range_size = candle["High"] - candle["Low"]
    body_size = abs(candle["Close"] - candle["Open"])

    if range_size == 0 or atr == 0:
        continue

    strong_bull = body_size > range_size * 0.65 and candle["Close"] > candle["Open"]
    strong_bear = body_size > range_size * 0.65 and candle["Close"] < candle["Open"]

    rsi_up = data["RSI"].iloc[i] > data["RSI"].iloc[i - 1]
    rsi_down = data["RSI"].iloc[i] < data["RSI"].iloc[i - 1]

    trade_result = None

    # ================= BULLISH =================
    if (
        price > ema
        and rsi > 55
        and ema_slope > 0
        and pullback
        and strong_bull
        and rsi_up
    ):
        entry = price
        stop = entry - atr
        trailing_stop = stop
        activated_trailing = False

        future = data.iloc[i + 1 : i + 20]

        for _, row in future.iterrows():

            # Activate trailing after 1R move
            if not activated_trailing and row["High"] >= entry + atr:
                activated_trailing = True

            if activated_trailing:
                trailing_stop = max(trailing_stop, row["Close"] - atr)

            if row["Low"] <= trailing_stop:
                trade_result = (trailing_stop - entry) / atr
                break

        if trade_result is None:
            trade_result = (future["Close"].iloc[-1] - entry) / atr

    # ================= BEARISH =================
    elif (
        price < ema
        and rsi < 45
        and ema_slope < 0
        and pullback
        and strong_bear
        and rsi_down
    ):
        entry = price
        stop = entry + atr
        trailing_stop = stop
        activated_trailing = False

        future = data.iloc[i + 1 : i + 20]

        for _, row in future.iterrows():

            if not activated_trailing and row["Low"] <= entry - atr:
                activated_trailing = True

            if activated_trailing:
                trailing_stop = min(trailing_stop, row["Close"] + atr)

            if row["High"] >= trailing_stop:
                trade_result = (entry - trailing_stop) / atr
                break

        if trade_result is None:
            trade_result = (entry - future["Close"].iloc[-1]) / atr

    if trade_result is not None:
        total_trades += 1
        equity += trade_result

        if trade_result > 0:
            wins += 1
            losing_streak = 0
        else:
            losses += 1
            losing_streak += 1
            max_losing_streak = max(max_losing_streak, losing_streak)

        peak_equity = max(peak_equity, equity)
        drawdown = peak_equity - equity
        max_drawdown = max(max_drawdown, drawdown)

# ===== RESULTS =====

print("Total Trades:", total_trades)
print("Wins:", wins)
print("Losses:", losses)

if total_trades > 0:
    winrate = round((wins / total_trades) * 100, 2)
    avg_r = round(equity / total_trades, 3)
    print("Win Rate:", winrate, "%")
    print("Average R per Trade:", avg_r)
    print("Max Drawdown (R):", round(max_drawdown, 2))
    print("Max Losing Streak:", max_losing_streak)
else:
    print("No trades found.")