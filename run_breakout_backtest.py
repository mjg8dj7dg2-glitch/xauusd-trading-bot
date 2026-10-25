import json
from pathlib import Path

import pandas as pd

from engines.breakout_backtest import BreakoutConfig, backtest_breakouts

data_path = Path("data/xauusd/raw/XAUUSD_5m.csv")
output_dir = Path("data/xauusd/backtest")
output_dir.mkdir(parents=True, exist_ok=True)

if not data_path.exists():
    raise FileNotFoundError(f"Historical CSV not found: {data_path}")

data = pd.read_csv(data_path)
data["datetime"] = pd.to_datetime(data["datetime"], utc=True, errors="raise")

config = BreakoutConfig(
    initial_balance=10_000.0,
    risk_fraction=0.005,
    daily_loss_fraction=0.01,
    stop_atr_multiplier=1.5,
    reward_risk_ratio=2.0,
    atr_period=14,
    left_bars=2,
    right_bars=2,
    max_consecutive_losses=3,
    value_per_price_unit=1.0,
    spread_price=0.30,
    slippage_price_per_side=0.05,
    commission_per_unit_per_side=0.0,
)

result = backtest_breakouts(data, config)

print("\n=== XAU/USD 5-MINUTE HISTORICAL BACKTEST ===")
print(f"Data file: {data_path}")
print(f"First candle: {data['datetime'].min()}")
print(f"Last candle:  {data['datetime'].max()}")
print(f"Candles:      {len(data):,}")
print("\n--- Metrics ---")

for key, value in result["metrics"].items():
    if isinstance(value, float):
        print(f"{key}: {value:,.4f}")
    else:
        print(f"{key}: {value}")

trades_path = output_dir / "trades.csv"
equity_path = output_dir / "equity_curve.csv"
signals_path = output_dir / "signals.csv"
metrics_path = output_dir / "metrics.json"

result["trades"].to_csv(trades_path, index=False)
result["equity_curve"].to_csv(equity_path, index=False)
result["signals"].to_csv(signals_path, index=False)
metrics_path.write_text(
    json.dumps(result["metrics"], indent=2, allow_nan=False),
    encoding="utf-8",
)

print("\n--- Saved outputs ---")
print(trades_path)
print(equity_path)
print(signals_path)
print(metrics_path)

if not result["trades"].empty:
    print("\n--- Most recent 10 trades ---")
    print(result["trades"].tail(10).to_string(index=False))
else:
    print("\nNo trades were generated. Check signals and strategy assumptions.")
