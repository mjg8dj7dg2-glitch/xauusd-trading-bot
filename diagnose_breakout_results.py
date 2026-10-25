import pandas as pd

signals = pd.read_csv("data/xauusd/backtest/signals.csv")
trades = pd.read_csv("data/xauusd/backtest/trades.csv")

print("=== SIGNAL DIAGNOSTICS ===")
print("Candles:", len(signals))
print("\nSignal counts (-1 = short, 0 = none, 1 = long):")
print(signals["breakout_signal"].value_counts().sort_index())

print("\nFirst 20 non-zero signals:")
cols = ["datetime", "close", "breakout_signal", "atr"]
available = [c for c in cols if c in signals.columns]
print(
    signals.loc[signals["breakout_signal"] != 0, available]
    .head(20)
    .to_string(index=False)
)

print("\n=== TRADE EXIT REASONS ===")
if trades.empty:
    print("No trades")
else:
    print(trades["exit_reason"].value_counts().to_string())
    print("\nTrade direction counts:")
    print(trades["direction"].value_counts().to_string())
    trades["entry_time"] = pd.to_datetime(trades["entry_time"], utc=True)
    print("\nTrades by entry date:")
    print(trades.groupby(trades["entry_time"].dt.date).size().to_string())

print("\n=== SIGNALS BY MONTH ===")
signals["datetime"] = pd.to_datetime(signals["datetime"], utc=True)
signals["month"] = signals["datetime"].dt.strftime("%Y-%m")
print(
    signals.groupby("month")["breakout_signal"]
    .agg(
        candles="size",
        long_signals=lambda s: int((s == 1).sum()),
        short_signals=lambda s: int((s == -1).sum()),
    )
    .to_string()
)
