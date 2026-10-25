# Trading Bot — Read-only System Audit

- Audit time: 2026-10-21T04:19:54+01:00
- Project root: `C:\Users\PC\trading_bot`
- Execution policy: **No project modules imported; no tests/backtests run; no existing files modified.**
- Scope: static source inspection and analysis of already-saved JSON/CSV outputs.

## 1. Inventory

- Total files scanned (excluding virtual environments, caches, and common binary files): **195**
- Python files: **124**
- Data/config-like files: **30**

| Extension | Count |
|---|---:|
| `.bak` | 23 |
| `.connection` | 1 |
| `.csv` | 24 |
| `.db` | 2 |
| `.json` | 6 |
| `.mean()` | 1 |
| `.minimum_average_pf` | 1 |
| `.minimum_validation_trades` | 1 |
| `.minimum_validation_windows` | 1 |
| `.py` | 124 |
| `.robust_pf` | 1 |
| `.sum()` | 1 |
| `.txt` | 1 |
| `[no extension]` | 8 |

### Key project files

- `diagnose_breakout_results.py` — 1401 bytes; SHA-256 `4d926c294cc0d0647daba3c41e79dcb2ec758776d69dcdd17ac2053f19d4e6fb`
- `requirements.txt` — 91 bytes; SHA-256 `fde7485965ee75c454cff63d6a7cbe1d51f500f4de4bb0ba658a5a8a8d1f1899`
- `run_breakout_backtest.py` — 2094 bytes; SHA-256 `0be235251cc84c4ab2c8540a48a7cfc9b698ed1e2c2254914d60205bc4d0fe83`
- `run_cooldown_2loss.py` — 2109 bytes; SHA-256 `4eb5ce3bf3ca7988c46d330b3c786c7ad166cdba5c4fe2f30478f716abdce60e`
- `run_cooldown_2loss_verify.py` — 2115 bytes; SHA-256 `d67fdc84f065d72256f5a50cf8b417559c45e23ab4fdaa6331ce271b69eaaa4b`
- `run_cooldown_comparison.py` — 2122 bytes; SHA-256 `1d75e97052da03ea3dc5012ac92ccb774b54b2dfa0c0675f2a40525571df8fb1`

## 2. Python syntax and static source checks

These checks parse source without importing or executing it. Pattern matches are leads for review, not automatic proof of defects.

### Python syntax errors

- **ERROR** `diagnose_breakout_results.py:1` — invalid non-printable character U+FEFF
- **ERROR** `engines\market_structure.py:1` — invalid non-printable character U+FEFF
- **ERROR** `run_breakout_backtest.py:1` — invalid non-printable character U+FEFF
- **ERROR** `run_cooldown_2loss.py:1` — invalid non-printable character U+FEFF
- **ERROR** `run_cooldown_comparison.py:1` — invalid non-printable character U+FEFF
- **ERROR** `tests\diagnose_paper_losing_streak.py:1` — invalid non-printable character U+FEFF
- **ERROR** `tests\test_breakout_backtest.py:1` — invalid non-printable character U+FEFF
- **ERROR** `tests\test_losing_streak_pause.py:1` — invalid non-printable character U+FEFF
- **ERROR** `tests\test_market_data.py:1` — invalid non-printable character U+FEFF
- **ERROR** `tests\test_market_structure.py:1` — invalid non-printable character U+FEFF
- **ERROR** `tests\test_v7_independent_observations.py:1` — invalid non-printable character U+FEFF

### Review leads

- `audit_trading_bot.py:199` — **broad exception handling** — `except Exception as e:`
- `audit_trading_bot.py:229` — **broad exception handling** — `except Exception:`
- `audit_trading_bot.py:234` — **broad exception handling** — `except Exception as e:`
- `audit_trading_bot.py:267` — **broad exception handling** — `except Exception:`
- `audit_trading_bot.py:269` — **broad exception handling** — `except Exception as e:`
- `audit_trading_bot.py:105` — **debug / unfinished markers** — `("debug / unfinished markers", re.compile(r"\b(TODO\|FIXME\|XXX\|NotImplementedError)\b")),`
- `audit_trading_bot.py:106` — **randomness** — `("randomness", re.compile(r"\b(random\|np\.random\|numpy\.random)\b")),`
- `audit_trading_bot.py:73` — **possible time-zone-naive datetime usage** — `sections.append(f"- Audit time: {datetime.now().astimezone().isoformat(timespec='seconds')}")`
- `audit_trading_bot.py:308` — **file writes / overwrite operations** — `REPORT.write_text("\n".join(sections) + "\n", encoding="utf-8")`
- `engines\backtest.py:328` — **broad exception handling** — `except Exception as error:`
- `engines\backtest.py:280` — **possible time-zone-naive datetime usage** — `<= pd.to_datetime(current_timestamp)`
- `engines\data_source.py:23` — **possible time-zone-naive datetime usage** — `df["timestamp"] = pd.to_datetime(df["timestamp"])`
- `engines\historical_data.py:29` — **broad exception handling** — `except Exception as exc:`
- `engines\market_data.py:255` — **broad exception handling** — `except Exception as exc:`
- `engines\news.py:30` — **possible time-zone-naive datetime usage** — `"event_time": pd.to_datetime(event_time),`
- `engines\news.py:73` — **possible time-zone-naive datetime usage** — `current = pd.to_datetime(current_time)`
- `engines\news.py:74` — **possible time-zone-naive datetime usage** — `event = pd.to_datetime(event_time)`
- `engines\news.py:97` — **possible time-zone-naive datetime usage** — `current_time = pd.to_datetime(current_time)`
- `engines\paper_persistence.py:58` — **broad exception handling** — `except Exception:`
- `engines\paper_persistence.py:64` — **broad exception handling** — `except Exception:`
- `engines\paper_persistence.py:115` — **broad exception handling** — `except Exception:`
- `engines\paper_persistence.py:169` — **broad exception handling** — `except Exception:`
- `engines\paper_persistence.py:1094` — **broad exception handling** — `except Exception:`
- `engines\paper_persistence.py:409` — **possible time-zone-naive datetime usage** — `started_at = datetime.now().astimezone()`
- `engines\paper_persistence.py:882` — **possible time-zone-naive datetime usage** — `datetime.now()`
- `engines\paper_persistence.py:961` — **possible time-zone-naive datetime usage** — `datetime.now()`
- `engines\strategy_experiment.py:404` — **broad exception handling** — `except Exception:`
- `fix_paper_persistence_close.py:29` — **file writes / overwrite operations** — `path.write_text(updated, encoding="utf-8")`
- `patch_risk_persistence.py:43` — **file writes / overwrite operations** — `backup.write_text(source, encoding="utf-8")`
- `patch_risk_persistence.py:45` — **file writes / overwrite operations** — `path.write_text(source[:start] + new_block + source[end:], encoding="utf-8")`
- `run_breakout_backtest.py:54` — **file writes / overwrite operations** — `result["trades"].to_csv(trades_path, index=False)`
- `run_breakout_backtest.py:55` — **file writes / overwrite operations** — `result["equity_curve"].to_csv(equity_path, index=False)`
- `run_breakout_backtest.py:56` — **file writes / overwrite operations** — `result["signals"].to_csv(signals_path, index=False)`
- `run_breakout_backtest.py:57` — **file writes / overwrite operations** — `metrics_path.write_text(`
- `run_cooldown_2loss.py:54` — **file writes / overwrite operations** — `result["trades"].to_csv(trades_path, index=False)`
- `run_cooldown_2loss.py:55` — **file writes / overwrite operations** — `result["equity_curve"].to_csv(equity_path, index=False)`
- `run_cooldown_2loss.py:56` — **file writes / overwrite operations** — `result["signals"].to_csv(signals_path, index=False)`
- `run_cooldown_2loss.py:57` — **file writes / overwrite operations** — `metrics_path.write_text(`
- `run_cooldown_2loss_verify.py:54` — **file writes / overwrite operations** — `result["trades"].to_csv(trades_path, index=False)`
- `run_cooldown_2loss_verify.py:55` — **file writes / overwrite operations** — `result["equity_curve"].to_csv(equity_path, index=False)`
- `run_cooldown_2loss_verify.py:56` — **file writes / overwrite operations** — `result["signals"].to_csv(signals_path, index=False)`
- `run_cooldown_2loss_verify.py:57` — **file writes / overwrite operations** — `metrics_path.write_text(`
- `run_cooldown_comparison.py:54` — **file writes / overwrite operations** — `result["trades"].to_csv(trades_path, index=False)`
- `run_cooldown_comparison.py:55` — **file writes / overwrite operations** — `result["equity_curve"].to_csv(equity_path, index=False)`
- `run_cooldown_comparison.py:56` — **file writes / overwrite operations** — `result["signals"].to_csv(signals_path, index=False)`
- `run_cooldown_comparison.py:57` — **file writes / overwrite operations** — `metrics_path.write_text(`
- `run_xauusd_paper_session.py:244` — **broad exception handling** — `except Exception as exc:`
- `tests\test_breakout_backtest.py:225` — **possible time-zone-naive datetime usage** — `assert pd.to_datetime(trades["entry_time"]).tolist() == expected_entry_times`
- `tests\test_full_historical_backtest.py:53` — **file writes / overwrite operations** — `pd.DataFrame(rows).to_csv(`
- `tests\test_historical_data.py:48` — **file writes / overwrite operations** — `).to_csv(`
- `tests\test_historical_pipeline.py:33` — **file writes / overwrite operations** — `pd.DataFrame(rows).to_csv(`
- `tests\test_real_xauusd_import.py:43` — **broad exception handling** — `except Exception as exc:`
- `tests\test_v7_independent_observations.py:233` — **file writes / overwrite operations** — `window["data"].to_csv(`
- `v7_dashboard.py:85` — **broad exception handling** — `except Exception:`
- `v7_dashboard.py:147` — **broad exception handling** — `except Exception:`

### Import map (static)

- `audit_trading_bot.py`: __future__, ast, collections, csv, datetime, hashlib, json, os, pathlib, re, sys
- `check_risk_events.py`: json, pathlib, sqlite3
- `compare_baseline_v5.py`: engines.backtest, engines.pipeline, math, pandas, pathlib
- `database.py`: pathlib, sqlite3
- `engines\backtest.py`: engines.correlation, engines.memory_report, engines.news, engines.risk, pandas
- `engines\breakout_backtest.py`: dataclasses, engines.breakout_detection, engines.market_structure, math, numpy, pandas
- `engines\breakout_detection.py`: pandas
- `engines\correlation.py`: pandas
- `engines\data_source.py`: abc, pandas
- `engines\health_report.py`: engines.regime_health, engines.strategy_health
- `engines\historical_data.py`: pandas
- `engines\historical_pipeline.py`: engines.historical_data, engines.regime, engines.strategy, engines.technical, pandas
- `engines\losing_patterns.py`: pandas
- `engines\market_data.py`: os, pandas, sqlite3
- `engines\memory_report.py`: engines.losing_patterns, engines.trade_memory
- `engines\news.py`: datetime, pandas
- `engines\paper_evaluation.py`: __future__, collections, math
- `engines\paper_history.py`: __future__, contextlib, datetime, hashlib, json, pathlib, sqlite3
- `engines\paper_monitor.py`: __future__, typing
- `engines\paper_persistence.py`: __future__, contextlib, datetime, json, pathlib, sqlite3, typing
- `engines\paper_runner.py`: __future__, engines.paper_evaluation, engines.paper_monitor, engines.paper_session, engines.paper_trading, engines.pipeline, engines.strategy_evaluation, pathlib, typing
- `engines\paper_session.py`: __future__, datetime, engines.paper_persistence, uuid
- `engines\paper_trading.py`: __future__, engines.backtest, pandas, typing
- `engines\pattern_analysis.py`: itertools, pandas
- `engines\pattern_validation.py`: itertools, pandas
- `engines\pipeline.py`: engines.backtest, engines.health_report, engines.market_data, engines.regime, engines.strategy, engines.technical, pandas
- `engines\regime.py`: pandas
- `engines\regime_health.py`: pandas
- `engines\regime_robustness.py`: pandas
- `engines\risk.py`: math, pandas
- `engines\strategy.py`: pandas
- `engines\strategy_evaluation.py`: engines.strategy_lifecycle, typing
- `engines\strategy_experiment.py`: __future__, engines.backtest, pandas, typing
- `engines\strategy_health.py`: pandas
- `engines\strategy_lifecycle.py`: __future__, typing
- `engines\strategy_robustness.py`: __future__, typing
- `engines\technical.py`: pandas
- `engines\trade_analysis.py`: collections, math, pandas
- `engines\trade_memory.py`: math, pandas
- `engines\walk_forward.py`: __future__, dataclasses, engines.strategy_experiment, pandas, typing
- `fix_paper_persistence_close.py`: pathlib
- `paper_runner.py`: __future__, argparse, engines.paper_monitor, engines.paper_session, engines.paper_trading, engines.pipeline, pathlib, typing
- `patch_risk_persistence.py`: pathlib
- `run_cooldown_2loss_verify.py`: engines.breakout_backtest, json, pandas, pathlib
- `run_xauusd_paper.py`: datetime, engines.market_data, os, pandas, pathlib, requests
- `run_xauusd_paper_session.py`: datetime, engines.market_data, engines.regime, engines.strategy, engines.technical, json, os, pandas, pathlib, sqlite3, urllib.parse, urllib.request
- `tests\test_backtest.py`: engines.backtest, engines.regime, engines.strategy, engines.technical, tests.test_strategy_controlled
- `tests\test_backtest_correlation.py`: engines.backtest, engines.regime, engines.strategy, engines.technical, tests.test_strategy_controlled
- `tests\test_backtest_data.py`: pandas
- `tests\test_backtest_news.py`: engines.backtest, engines.news, engines.regime, engines.strategy, engines.technical, tests.test_strategy_controlled
- `tests\test_backtest_risk.py`: engines.backtest, engines.regime, engines.risk, engines.strategy, engines.technical, tests.test_strategy_controlled
- `tests\test_correlation.py`: engines.correlation, pandas
- `tests\test_data_source.py`: engines.data_source
- `tests\test_database.py`: pathlib, sqlite3, tempfile
- `tests\test_full_historical_backtest.py`: engines.pipeline, os, pandas, tempfile
- `tests\test_health_report.py`: engines.health_report
- `tests\test_historical_data.py`: engines.historical_data, os, pandas, tempfile
- `tests\test_historical_pipeline.py`: engines.historical_pipeline, os, pandas, tempfile
- `tests\test_losing_patterns.py`: engines.losing_patterns
- `tests\test_market_structure_breakouts.py`: engines.breakout_detection, pandas, pytest
- `tests\test_memory_report.py`: engines.memory_report
- `tests\test_news.py`: engines.news
- `tests\test_paper_evaluation.py`: __future__, engines.paper_evaluation
- `tests\test_paper_history.py`: __future__, engines.paper_history, pathlib, sqlite3, tempfile
- `tests\test_paper_monitor.py`: __future__, engines.paper_monitor
- `tests\test_paper_persistence.py`: engines.paper_persistence, json, pathlib, tempfile
- `tests\test_paper_runner.py`: __future__, engines.paper_runner, pathlib
- `tests\test_paper_runner_isolated.py`: engines.paper_persistence, engines.paper_runner, pathlib, tempfile
- `tests\test_paper_runner_v5.py`: __future__, engines.paper_runner, engines.pipeline, engines.strategy_experiment, pandas, pathlib
- `tests\test_paper_runner_v7.py`: engines.paper_runner, engines.pipeline, engines.strategy_experiment, pathlib
- `tests\test_paper_session.py`: engines.paper_persistence, engines.paper_session, gc, pathlib, shutil, tempfile, time
- `tests\test_paper_trading.py`: engines.paper_trading, engines.strategy_experiment, pandas
- `tests\test_paper_workflow.py`: __future__, datetime, engines.paper_persistence, engines.paper_session, engines.paper_trading, pandas, pathlib, tempfile
- `tests\test_pattern_analysis.py`: engines.pattern_analysis, engines.pipeline
- `tests\test_pattern_validation.py`: engines.pattern_validation, engines.pipeline
- `tests\test_pipeline.py`: engines.pipeline, numpy, pandas
- `tests\test_real_xauusd_backtest.py`: engines.pipeline, os
- `tests\test_real_xauusd_import.py`: engines.historical_data, os
- `tests\test_real_xauusd_pipeline.py`: engines.pipeline, os
- `tests\test_real_xauusd_regime.py`: engines.pipeline, os, pandas
- `tests\test_real_xauusd_regime_robustness.py`: engines.pipeline, engines.regime_robustness, pathlib
- `tests\test_real_xauusd_walk_forward_regime.py`: engines.regime, engines.regime_robustness, engines.strategy, engines.technical, engines.walk_forward, pandas, pathlib
- `tests\test_regime.py`: engines.data_source, engines.regime
- `tests\test_regime_health.py`: engines.regime_health
- `tests\test_regime_robustness.py`: engines.regime_robustness, pandas
- `tests\test_risk.py`: engines.data_source, engines.regime, engines.risk, engines.strategy, engines.technical
- `tests\test_strategy.py`: engines.data_source, engines.regime, engines.strategy, engines.technical
- `tests\test_strategy_controlled.py`: engines.regime, engines.strategy, engines.technical, pandas
- `tests\test_strategy_evaluation.py`: engines.strategy_evaluation
- `tests\test_strategy_experiment.py`: engines.market_data, engines.regime, engines.strategy, engines.strategy_experiment, engines.technical
- `tests\test_strategy_health.py`: engines.strategy_health
- `tests\test_strategy_lifecycle.py`: engines.strategy_lifecycle
- `tests\test_strategy_robustness.py`: engines.regime, engines.strategy, engines.strategy_experiment, engines.strategy_robustness, engines.technical, engines.walk_forward, pandas
- `tests\test_strategy_variants.py`: engines.market_data, engines.regime, engines.strategy, engines.strategy_experiment, engines.technical
- `tests\test_technical.py`: engines.data_source, engines.technical
- `tests\test_trade_analysis.py`: engines.pipeline, engines.trade_analysis
- `tests\test_trade_analysis_deep.py`: engines.pipeline, engines.trade_analysis
- `tests\test_trade_memory.py`: engines.trade_memory
- `tests\test_unified_strategy_health.py`: engines.strategy_evaluation
- `tests\test_v5_losing_streak.py`: __future__, engines.backtest, engines.pipeline, pandas, pathlib
- `tests\test_v5_patterns.py`: __future__, collections, engines.backtest, engines.pipeline, engines.strategy_experiment, pandas, pathlib
- `tests\test_v7_cross_session_stability.py`: __future__, contextlib, dataclasses, engines.paper_runner, io, pandas, pathlib, re, typing
- `tests\test_v7_paper_observation.py`: __future__, engines.paper_evaluation, engines.paper_history, engines.paper_persistence, math
- `tests\test_v7_robustness.py`: engines.paper_runner, pandas, pathlib
- `tests\test_v7_tue_wed.py`: engines.backtest, engines.pipeline, engines.strategy_experiment, pandas, pathlib
- `tests\test_v7_walk_forward.py`: engines.data_source, engines.pipeline, engines.strategy_experiment, engines.walk_forward, pathlib
- `tests\test_walk_forward.py`: __future__, engines.market_data, engines.regime, engines.strategy, engines.technical, engines.walk_forward, pandas
- `tests\test_walk_forward_regime.py`: engines.regime, engines.strategy, engines.technical, engines.walk_forward, pandas, pathlib
- `v7_dashboard.py`: __future__, json, math, pandas, pathlib, plotly.express, sqlite3, streamlit, typing

## 3. Dependency/configuration files


### `requirements.txt`

```text
pandas==3.0.5
numpy==2.5.3
requests==2.34.2
streamlit==1.64.0
plotly==7.1.0
pytest==9.1.1
```

## 4. Existing saved backtest outputs


### `data\xauusd\backtest\backup_before_rerun\metrics.json`

- `initial_balance`: `10000.0`
- `final_balance`: `9994.636895919642`
- `net_profit`: `-5.363104080357516`
- `trades`: `9`
- `win_rate_pct`: `33.33333333333333`
- `expectancy_per_trade`: `-0.595900453373205`
- `profit_factor`: `0.9822216553260145`
- `max_drawdown_pct`: `2.052264130198176`
- `gross_profit`: `296.3018809734233`
- `gross_loss`: `301.6649850537821`
- Balance identity error (`initial_balance + net_profit - final_balance`): `0`
- Trade rows in CSV: `9`
- Trade CSV SHA-256: `f916032dc09204d7af2db6657f14162958a5c74828ba1e4509a0c2aa79629093`
- P&L column: `pnl`; numeric rows: `9`; invalid/missing: `0`; sum: `-5.36310408036`
- Trade-P&L sum minus reported net profit: `-1.35003119794e-12`
- Trade CSV columns: entry_time, exit_time, direction, entry_price, exit_price, stop_price, target_price, quantity, pnl, r_multiple, exit_reason, balance_after
- Equity CSV SHA-256: `6e45031658fd472f588f8d121f73d78fa81c1aa40ad15d517df67c3e81d2efbd`
- Equity rows: `36006`; columns: datetime, balance, equity
- Recomputed max drawdown from `balance`: `1.492513%`
- Recomputed minus reported max drawdown: `-0.559752` percentage points

### `data\xauusd\backtest\baseline_backup_20261021_0214\metrics.json`

- `initial_balance`: `10000.0`
- `final_balance`: `9331.191009535916`
- `net_profit`: `-668.8089904640838`
- `trades`: `342`
- `win_rate_pct`: `33.04093567251462`
- `expectancy_per_trade`: `-1.9555818434622885`
- `profit_factor`: `0.9372640760266769`
- `max_drawdown_pct`: `14.23414311353865`
- `gross_profit`: `9991.893014156045`
- `gross_loss`: `10660.702004620147`
- Balance identity error (`initial_balance + net_profit - final_balance`): `0`
- Trade rows in CSV: `342`
- Trade CSV SHA-256: `c799fb5f9d258a36f41ce2d40796f9d7b7dbebbd6930a0982a1d699d60979841`
- P&L column: `pnl`; numeric rows: `342`; invalid/missing: `0`; sum: `-668.808990464`
- Trade-P&L sum minus reported net profit: `-1.87583282241e-11`
- Trade CSV columns: entry_time, exit_time, direction, entry_price, exit_price, stop_price, target_price, quantity, pnl, r_multiple, exit_reason, balance_after
- Equity CSV SHA-256: `eab1e61c55b00d28ae9be1c76068f93e2b9541745f1ed93e1d97fb0bc8b61ee1`
- Equity rows: `36006`; columns: datetime, balance, equity
- Recomputed max drawdown from `balance`: `13.759898%`
- Recomputed minus reported max drawdown: `-0.474245` percentage points

### `data\xauusd\backtest\cooldown_2loss\metrics.json`

- `initial_balance`: `10000.0`
- `final_balance`: `9331.191009535916`
- `net_profit`: `-668.8089904640838`
- `trades`: `342`
- `win_rate_pct`: `33.04093567251462`
- `expectancy_per_trade`: `-1.9555818434622885`
- `profit_factor`: `0.9372640760266769`
- `max_drawdown_pct`: `14.23414311353865`
- `gross_profit`: `9991.893014156045`
- `gross_loss`: `10660.702004620147`
- Balance identity error (`initial_balance + net_profit - final_balance`): `0`
- Trade rows in CSV: `342`
- Trade CSV SHA-256: `c799fb5f9d258a36f41ce2d40796f9d7b7dbebbd6930a0982a1d699d60979841`
- P&L column: `pnl`; numeric rows: `342`; invalid/missing: `0`; sum: `-668.808990464`
- Trade-P&L sum minus reported net profit: `-1.87583282241e-11`
- Trade CSV columns: entry_time, exit_time, direction, entry_price, exit_price, stop_price, target_price, quantity, pnl, r_multiple, exit_reason, balance_after
- Equity CSV SHA-256: `eab1e61c55b00d28ae9be1c76068f93e2b9541745f1ed93e1d97fb0bc8b61ee1`
- Equity rows: `36006`; columns: datetime, balance, equity
- Recomputed max drawdown from `balance`: `13.759898%`
- Recomputed minus reported max drawdown: `-0.474245` percentage points

### `data\xauusd\backtest\cooldown_2loss_verify\metrics.json`

- `initial_balance`: `10000.0`
- `final_balance`: `9331.191009535916`
- `net_profit`: `-668.8089904640838`
- `trades`: `342`
- `win_rate_pct`: `33.04093567251462`
- `expectancy_per_trade`: `-1.9555818434622885`
- `profit_factor`: `0.9372640760266769`
- `max_drawdown_pct`: `14.23414311353865`
- `gross_profit`: `9991.893014156045`
- `gross_loss`: `10660.702004620147`
- Balance identity error (`initial_balance + net_profit - final_balance`): `0`
- Trade rows in CSV: `342`
- Trade CSV SHA-256: `c799fb5f9d258a36f41ce2d40796f9d7b7dbebbd6930a0982a1d699d60979841`
- P&L column: `pnl`; numeric rows: `342`; invalid/missing: `0`; sum: `-668.808990464`
- Trade-P&L sum minus reported net profit: `-1.87583282241e-11`
- Trade CSV columns: entry_time, exit_time, direction, entry_price, exit_price, stop_price, target_price, quantity, pnl, r_multiple, exit_reason, balance_after
- Equity CSV SHA-256: `eab1e61c55b00d28ae9be1c76068f93e2b9541745f1ed93e1d97fb0bc8b61ee1`
- Equity rows: `36006`; columns: datetime, balance, equity
- Recomputed max drawdown from `balance`: `13.759898%`
- Recomputed minus reported max drawdown: `-0.474245` percentage points

### `data\xauusd\backtest\cooldown_comparison\metrics.json`

- `initial_balance`: `10000.0`
- `final_balance`: `6507.623088101276`
- `net_profit`: `-3492.376911898724`
- `trades`: `994`
- `win_rate_pct`: `31.287726358148895`
- `expectancy_per_trade`: `-3.5134576578457875`
- `profit_factor`: `0.8701237856599965`
- `max_drawdown_pct`: `37.789979295424544`
- `gross_profit`: `23397.665499993607`
- `gross_loss`: `26890.04241189232`
- Balance identity error (`initial_balance + net_profit - final_balance`): `0`
- Trade rows in CSV: `994`
- Trade CSV SHA-256: `94bdba3a23e28f4ed39085e81f20c5096bd0563545babab72c11ef4883821470`
- P&L column: `pnl`; numeric rows: `994`; invalid/missing: `0`; sum: `-3492.3769119`
- Trade-P&L sum minus reported net profit: `1.13686837722e-11`
- Trade CSV columns: entry_time, exit_time, direction, entry_price, exit_price, stop_price, target_price, quantity, pnl, r_multiple, exit_reason, balance_after
- Equity CSV SHA-256: `3026a8a78f6f8487e903cbf2ae6a19f402ea784c3f6264e292f99c2dbce22a12`
- Equity rows: `36006`; columns: datetime, balance, equity
- Recomputed max drawdown from `balance`: `37.353372%`
- Recomputed minus reported max drawdown: `-0.436607` percentage points

### `data\xauusd\backtest\metrics.json`

- `initial_balance`: `10000.0`
- `final_balance`: `8332.132083412456`
- `net_profit`: `-1667.8679165875437`
- `trades`: `450`
- `win_rate_pct`: `31.555555555555554`
- `expectancy_per_trade`: `-3.7063731479723274`
- `profit_factor`: `0.8771771189189409`
- `max_drawdown_pct`: `23.321934611954223`
- `gross_profit`: `11911.588141659524`
- `gross_loss`: `13579.456058247071`
- Balance identity error (`initial_balance + net_profit - final_balance`): `0`
- Trade rows in CSV: `450`
- Trade CSV SHA-256: `92dcb0a02dba1543c3ce932f28feea8ae3682c94a0992869814689dc979ac5a6`
- P&L column: `pnl`; numeric rows: `450`; invalid/missing: `0`; sum: `-1667.86791659`
- Trade-P&L sum minus reported net profit: `-3.41060513165e-12`
- Trade CSV columns: entry_time, exit_time, direction, entry_price, exit_price, stop_price, target_price, quantity, pnl, r_multiple, exit_reason, balance_after
- Equity CSV SHA-256: `57e34a36c34081844497b7ba852dc24b8289ede9e25f1f47724e6ff53719a7b1`
- Equity rows: `36006`; columns: datetime, balance, equity
- Recomputed max drawdown from `balance`: `22.883735%`
- Recomputed minus reported max drawdown: `-0.438200` percentage points

## 5. Data and duplicate-output inventory

- `data\test_gold.csv` — 466 bytes — SHA-256 `35b47a3dace0c8e1998d705910aa0823017f87612f92d3c5dd9413b7622d8073`
- `data\xauusd\backtest\backup_before_rerun\equity_curve.csv` — 2268050 bytes — SHA-256 `6e45031658fd472f588f8d121f73d78fa81c1aa40ad15d517df67c3e81d2efbd`
- `data\xauusd\backtest\backup_before_rerun\signals.csv` — 4959359 bytes — SHA-256 `1e724f948a0f92a626d9cedd19abd793101f2957e7d3384e43b6b672655f5150`
- `data\xauusd\backtest\backup_before_rerun\trades.csv` — 1986 bytes — SHA-256 `f916032dc09204d7af2db6657f14162958a5c74828ba1e4509a0c2aa79629093`
- `data\xauusd\backtest\baseline_backup_20261021_0214\equity_curve.csv` — 2252109 bytes — SHA-256 `eab1e61c55b00d28ae9be1c76068f93e2b9541745f1ed93e1d97fb0bc8b61ee1`
- `data\xauusd\backtest\baseline_backup_20261021_0214\signals.csv` — 4959359 bytes — SHA-256 `1e724f948a0f92a626d9cedd19abd793101f2957e7d3384e43b6b672655f5150`
- `data\xauusd\backtest\baseline_backup_20261021_0214\trades.csv` — 70639 bytes — SHA-256 `c799fb5f9d258a36f41ce2d40796f9d7b7dbebbd6930a0982a1d699d60979841`
- `data\xauusd\backtest\cooldown_2loss\equity_curve.csv` — 2252109 bytes — SHA-256 `eab1e61c55b00d28ae9be1c76068f93e2b9541745f1ed93e1d97fb0bc8b61ee1`
- `data\xauusd\backtest\cooldown_2loss\signals.csv` — 4959359 bytes — SHA-256 `1e724f948a0f92a626d9cedd19abd793101f2957e7d3384e43b6b672655f5150`
- `data\xauusd\backtest\cooldown_2loss\trades.csv` — 70639 bytes — SHA-256 `c799fb5f9d258a36f41ce2d40796f9d7b7dbebbd6930a0982a1d699d60979841`
- `data\xauusd\backtest\cooldown_2loss_verify\equity_curve.csv` — 2252109 bytes — SHA-256 `eab1e61c55b00d28ae9be1c76068f93e2b9541745f1ed93e1d97fb0bc8b61ee1`
- `data\xauusd\backtest\cooldown_2loss_verify\signals.csv` — 4959359 bytes — SHA-256 `1e724f948a0f92a626d9cedd19abd793101f2957e7d3384e43b6b672655f5150`
- `data\xauusd\backtest\cooldown_2loss_verify\trades.csv` — 70639 bytes — SHA-256 `c799fb5f9d258a36f41ce2d40796f9d7b7dbebbd6930a0982a1d699d60979841`
- `data\xauusd\backtest\cooldown_comparison\equity_curve.csv` — 2262339 bytes — SHA-256 `3026a8a78f6f8487e903cbf2ae6a19f402ea784c3f6264e292f99c2dbce22a12`
- `data\xauusd\backtest\cooldown_comparison\signals.csv` — 4959359 bytes — SHA-256 `1e724f948a0f92a626d9cedd19abd793101f2957e7d3384e43b6b672655f5150`
- `data\xauusd\backtest\cooldown_comparison\trades.csv` — 205706 bytes — SHA-256 `94bdba3a23e28f4ed39085e81f20c5096bd0563545babab72c11ef4883821470`
- `data\xauusd\backtest\equity_curve.csv` — 2258723 bytes — SHA-256 `57e34a36c34081844497b7ba852dc24b8289ede9e25f1f47724e6ff53719a7b1`
- `data\xauusd\backtest\signals.csv` — 4959359 bytes — SHA-256 `1e724f948a0f92a626d9cedd19abd793101f2957e7d3384e43b6b672655f5150`
- `data\xauusd\backtest\trades.csv` — 92969 bytes — SHA-256 `92dcb0a02dba1543c3ce932f28feea8ae3682c94a0992869814689dc979ac5a6`
- `data\xauusd\paper_observations\V7_observation_1.csv` — 752414 bytes — SHA-256 `be94fc9c767834657c32fd504023b7f6a55035b8743e6dd2980ac7f9bf2d4c78`
- `data\xauusd\paper_observations\V7_observation_2.csv` — 942203 bytes — SHA-256 `1cde43d350cc331f42cac28ca3aaa70cf23145036a8255fa556443f4a315af33`
- `data\xauusd\paper_observations\V7_observation_3.csv` — 977306 bytes — SHA-256 `dc5e61092f8bcb9e67c7eabae802db2fc54d1e467717f45b11a2939e1d841576`
- `data\xauusd\paper_observations\V7_observation_4.csv` — 847898 bytes — SHA-256 `db1ab62ffbbc98dd845dc5b2cb0a22252f2f8cdafd6d8f9b1d398b16cf0dc6be`
- `data\xauusd\raw\XAUUSD_5m.csv` — 3100655 bytes — SHA-256 `34ae01957a7024fe357bbafee2c704f47d8477e657deffae937bd17785aaec7b`

### Byte-identical saved output files

- `data\xauusd\backtest\signals.csv` = `data\xauusd\backtest\backup_before_rerun\signals.csv` = `data\xauusd\backtest\baseline_backup_20261021_0214\signals.csv` = `data\xauusd\backtest\cooldown_2loss\signals.csv` = `data\xauusd\backtest\cooldown_2loss_verify\signals.csv` = `data\xauusd\backtest\cooldown_comparison\signals.csv`
- `data\xauusd\backtest\baseline_backup_20261021_0214\equity_curve.csv` = `data\xauusd\backtest\cooldown_2loss\equity_curve.csv` = `data\xauusd\backtest\cooldown_2loss_verify\equity_curve.csv`
- `data\xauusd\backtest\baseline_backup_20261021_0214\metrics.json` = `data\xauusd\backtest\cooldown_2loss\metrics.json` = `data\xauusd\backtest\cooldown_2loss_verify\metrics.json`
- `data\xauusd\backtest\baseline_backup_20261021_0214\trades.csv` = `data\xauusd\backtest\cooldown_2loss\trades.csv` = `data\xauusd\backtest\cooldown_2loss_verify\trades.csv`

## 6. Findings summary

- **HIGH** — Python syntax error in diagnose_breakout_results.py:1: invalid non-printable character U+FEFF
- **HIGH** — Python syntax error in engines\market_structure.py:1: invalid non-printable character U+FEFF
- **HIGH** — Python syntax error in run_breakout_backtest.py:1: invalid non-printable character U+FEFF
- **HIGH** — Python syntax error in run_cooldown_2loss.py:1: invalid non-printable character U+FEFF
- **HIGH** — Python syntax error in run_cooldown_comparison.py:1: invalid non-printable character U+FEFF
- **HIGH** — Python syntax error in tests\diagnose_paper_losing_streak.py:1: invalid non-printable character U+FEFF
- **HIGH** — Python syntax error in tests\test_breakout_backtest.py:1: invalid non-printable character U+FEFF
- **HIGH** — Python syntax error in tests\test_losing_streak_pause.py:1: invalid non-printable character U+FEFF
- **HIGH** — Python syntax error in tests\test_market_data.py:1: invalid non-printable character U+FEFF
- **HIGH** — Python syntax error in tests\test_market_structure.py:1: invalid non-printable character U+FEFF
- **HIGH** — Python syntax error in tests\test_v7_independent_observations.py:1: invalid non-printable character U+FEFF

## 7. Limitations and next review

- This is a static, first-pass audit, not proof of profitability or broker-execution correctness.
- The script does not execute project code, run tests, contact a broker, access the network, or inspect the `.venv`.
- Static pattern matches can be false positives. Absence of matches does not prove absence of bugs.
- Review the report before any code changes. The most useful follow-up is to share this report back for a focused interpretation.
