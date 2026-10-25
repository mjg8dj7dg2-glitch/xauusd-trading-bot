from __future__ import annotations

from typing import Callable, Dict, List, Tuple

import pandas as pd

from engines.backtest import BacktestEngine


VariantTransform = Callable[[pd.DataFrame], pd.DataFrame]


# ============================================================
# Strategy transforms
# ============================================================

def baseline(df: pd.DataFrame) -> pd.DataFrame:
    return df.copy()


def block_short_atr_8_12(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    mask = (
        (result["signal"] == "SHORT")
        & (result["atr"] >= 8.0)
        & (result["atr"] < 12.0)
    )

    result.loc[mask, "signal"] = "NO_SIGNAL"
    result.loc[mask, "signal_strength"] = 0.0
    result.loc[mask, "signal_reason"] = (
        "Blocked by variant: SHORT + ATR 8-12"
    )

    return result


def block_low_vol_thursday(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    timestamp = pd.to_datetime(
        result["timestamp"],
        utc=True,
    )

    mask = (
        result["signal"].isin(["LONG", "SHORT"])
        & (result["volatility_regime"] == "LOW_VOLATILITY")
        & (timestamp.dt.dayofweek == 3)
    )

    result.loc[mask, "signal"] = "NO_SIGNAL"
    result.loc[mask, "signal_strength"] = 0.0
    result.loc[mask, "signal_reason"] = (
        "Blocked by variant: LOW_VOLATILITY + Thursday"
    )

    return result


def block_short_low_vol(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    mask = (
        (result["signal"] == "SHORT")
        & (result["volatility_regime"] == "LOW_VOLATILITY")
    )

    result.loc[mask, "signal"] = "NO_SIGNAL"
    result.loc[mask, "signal_strength"] = 0.0
    result.loc[mask, "signal_reason"] = (
        "Blocked by variant: SHORT + LOW_VOLATILITY"
    )

    return result


def compose_transforms(
    first: VariantTransform,
    second: VariantTransform,
) -> VariantTransform:

    def combined(df: pd.DataFrame) -> pd.DataFrame:
        result = first(df)
        result = second(result)
        return result

    return combined


# ============================================================
# Public variant factory
# ============================================================

def get_standard_variants() -> List[Tuple[str, VariantTransform]]:
    return [
        (
            "V1_BASELINE",
            baseline,
        ),
        (
            "V2_BLOCK_SHORT_ATR_8_12",
            block_short_atr_8_12,
        ),
        (
            "V3_BLOCK_LOW_VOL_THURSDAY",
            block_low_vol_thursday,
        ),
        (
            "V4_BLOCK_SHORT_LOW_VOL",
            block_short_low_vol,
        ),
        (
            "V5_V2_PLUS_V3",
            compose_transforms(
                block_short_atr_8_12,
                block_low_vol_thursday,
            ),
        ),
        (
            "V6_V2_PLUS_V4",
            compose_transforms(
                block_short_atr_8_12,
                block_short_low_vol,
            ),
        ),
    ]


# ============================================================
# Experiment engine
# ============================================================

class StrategyExperiment:

    def __init__(
        self,
        initial_balance: float = 10_000.0,
        risk_per_trade: float = 0.01,

        stop_atr_multiplier: float = 2.0,
        take_profit_atr_multiplier: float = 4.0,
        take_profit_ratio: float = 2.0,

        slippage_per_trade: float = 0.0,
        commission_per_trade: float = 0.0,

        stop_loss_distance: float | None = None,
        take_profit_distance: float | None = None,
    ):
        self.initial_balance = initial_balance
        self.risk_per_trade = risk_per_trade

        self.stop_atr_multiplier = stop_atr_multiplier
        self.take_profit_atr_multiplier = (
            take_profit_atr_multiplier
        )

        self.take_profit_ratio = take_profit_ratio

        self.slippage_per_trade = (
            slippage_per_trade
        )

        self.commission_per_trade = (
            commission_per_trade
        )

        self.stop_loss_distance = (
            stop_loss_distance
        )

        self.take_profit_distance = (
            take_profit_distance
        )

    # --------------------------------------------------------
    # Variant access
    # --------------------------------------------------------

    @staticmethod
    def get_standard_variants():
        return get_standard_variants()

    # --------------------------------------------------------
    # Backtester
    # --------------------------------------------------------

    def _create_backtester(self) -> BacktestEngine:

        kwargs = {
            "initial_balance": self.initial_balance,
            "risk_per_trade": self.risk_per_trade,
        }

        if self.stop_loss_distance is not None:
            kwargs["stop_loss_distance"] = (
                self.stop_loss_distance
            )

        if self.take_profit_distance is not None:
            kwargs["take_profit_distance"] = (
                self.take_profit_distance
            )

        # Try full constructor compatibility first.
        try:
            return BacktestEngine(
                **kwargs,
                slippage_per_trade=(
                    self.slippage_per_trade
                ),
                commission_per_trade=(
                    self.commission_per_trade
                ),
            )

        except TypeError:
            pass

        # Try slippage without commission.
        try:
            return BacktestEngine(
                **kwargs,
                slippage_per_trade=(
                    self.slippage_per_trade
                ),
            )

        except TypeError:
            pass

        # Fall back to the older constructor.
        return BacktestEngine(**kwargs)

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    @staticmethod
    def _normalize_variants(variants):

        if isinstance(variants, dict):
            return list(variants.items())

        return list(variants)

    @staticmethod
    def _count_blocked_signals(
        original_data: pd.DataFrame,
        transformed_data: pd.DataFrame,
    ) -> int:

        original_signals = (
            original_data["signal"].isin(
                ["LONG", "SHORT"]
            )
        )

        transformed_signals = (
            transformed_data["signal"].isin(
                ["LONG", "SHORT"]
            )
        )

        return int(
            (
                original_signals
                & ~transformed_signals
            ).sum()
        )

    # --------------------------------------------------------
    # Run one variant
    # --------------------------------------------------------

    def run_variant(
        self,
        variant_name: str,
        transform: VariantTransform,
        data: pd.DataFrame | None = None,
        analyzed_data: pd.DataFrame | None = None,
    ) -> Dict:

        source_data = (
            analyzed_data
            if analyzed_data is not None
            else data
        )

        if source_data is None:
            raise ValueError(
                "run_variant requires data= "
                "or analyzed_data="
            )

        if transform is None:
            transformed = source_data.copy()
        else:
            transformed = transform(
                source_data.copy()
            )

        backtester = self._create_backtester()

        result = backtester.run(
            transformed
        )

        summary = self.summarize_result(
            result
        )

        blocked = (
            self._count_blocked_signals(
                source_data,
                transformed,
            )
        )

        # Return a hybrid result object: keep every authoritative
        # BacktestEngine field (including the completed trade list)
        # and add the experiment summary fields on top.  The test
        # suite intentionally treats the run_variant return value as
        # both a backtest result and an experiment summary.
        result["variant_name"] = variant_name
        result["data"] = transformed
        result["summary"] = summary
        result["trades_summary"] = summary["trades"]
        result["wins"] = summary["wins"]
        result["losses"] = summary["losses"]
        result["total_pnl"] = summary["total_pnl"]
        result["blocked_signals"] = blocked
        result["candidate_blocked_signals"] = blocked

        return result

    # --------------------------------------------------------
    # Run all variants
    # --------------------------------------------------------

    def run_all(
        self,
        analyzed_data: pd.DataFrame,
        variants=None,
    ) -> Dict[str, Dict]:

        if variants is None:
            variants = get_standard_variants()

        variant_items = (
            self._normalize_variants(
                variants
            )
        )

        results = {}

        for variant_name, transform in (
            variant_items
        ):

            print(
                f"Running {variant_name}..."
            )

            results[variant_name] = (
                self.run_variant(
                    variant_name=variant_name,
                    transform=transform,
                    analyzed_data=analyzed_data,
                )
            )

        return results

    # --------------------------------------------------------
    # Result summary
    # --------------------------------------------------------

    @staticmethod
    @staticmethod
    def _trade_entry_time(trade):
        """Return the entry timestamp from a backtest trade record."""
        if not isinstance(trade, dict):
            return None

        candidate_keys = (
            "entry_time",
            "entry_timestamp",
            "entry_datetime",
            "open_time",
            "open_timestamp",
            "timestamp",
        )

        for key in candidate_keys:
            value = trade.get(key)
            if value is None or value == "":
                continue
            try:
                parsed = pd.to_datetime(value, errors="coerce")
            except Exception:
                continue
            if pd.isna(parsed):
                continue
            return parsed

        return None

    @staticmethod
    def summarize_result(
        result: Dict
    ) -> Dict:
        """
        Convert a BacktestEngine result into the compact summary
        used by the strategy-variant tests.

        BacktestEngine already calculates the authoritative trade
        statistics.  We therefore use those aggregate values first
        instead of assuming that result["trades"] always has a
        particular pandas-compatible structure.

        A trade list/DataFrame is used only as a compatibility
        fallback when aggregate values are missing.
        """

        if not isinstance(result, dict):
            raise TypeError(
                "summarize_result expects a backtest result dictionary."
            )

        # --------------------------------------------------------
        # Prefer the statistics calculated by BacktestEngine.
        # --------------------------------------------------------

        total_trades = int(
            result.get(
                "total_trades",
                0,
            )
            or 0
        )

        wins = int(
            result.get(
                "winning_trades",
                0,
            )
            or 0
        )

        losses = int(
            result.get(
                "losing_trades",
                0,
            )
            or 0
        )

        win_rate = float(
            result.get(
                "win_rate",
                0.0,
            )
            or 0.0
        )

        profit_factor = float(
            result.get(
                "profit_factor",
                0.0,
            )
            or 0.0
        )

        max_drawdown = float(
            result.get(
                "max_drawdown",
                result.get(
                    "maximum_drawdown",
                    0.0,
                ),
            )
            or 0.0
        )

        # BacktestEngine does not currently return total_pnl
        # explicitly, so calculate it from final - initial balance.
        initial_balance = result.get(
            "initial_balance"
        )

        final_balance = result.get(
            "final_balance"
        )

        if (
            initial_balance is not None
            and final_balance is not None
        ):
            total_pnl = float(
                final_balance
                - initial_balance
            )
        else:
            total_pnl = 0.0

        # --------------------------------------------------------
        # Compatibility fallback for older result structures.
        # --------------------------------------------------------

        trades = result.get(
            "trades",
            []
        )

        if (
            total_trades == 0
            and isinstance(trades, pd.DataFrame)
        ):
            trade_df = trades.copy()

            total_trades = len(
                trade_df
            )

        elif (
            total_trades == 0
            and isinstance(trades, list)
        ):
            # Only build a DataFrame when the value really is a
            # list.  This avoids the pandas constructor failure
            # caused by scalar/dict-style result structures.
            trade_df = pd.DataFrame.from_records(
                trades
            )

            total_trades = len(
                trade_df
            )

        else:
            trade_df = None

        if (
            trade_df is not None
            and not trade_df.empty
        ):
            if "pnl" in trade_df.columns:
                pnl = pd.to_numeric(
                    trade_df["pnl"],
                    errors="coerce",
                ).fillna(0.0)

            elif "profit" in trade_df.columns:
                pnl = pd.to_numeric(
                    trade_df["profit"],
                    errors="coerce",
                ).fillna(0.0)

            else:
                pnl = pd.Series(
                    0.0,
                    index=trade_df.index,
                )

            wins = int(
                (pnl > 0).sum()
            )

            losses = int(
                (pnl < 0).sum()
            )

            gross_profit = float(
                pnl[pnl > 0].sum()
            )

            gross_loss = float(
                -pnl[pnl < 0].sum()
            )

            if gross_loss > 0:
                profit_factor = (
                    gross_profit
                    / gross_loss
                )
            elif gross_profit > 0:
                profit_factor = float("inf")
            else:
                profit_factor = 0.0

            total_pnl = float(
                pnl.sum()
            )

            if total_trades > 0:
                win_rate = (
                    wins
                    / total_trades
                )

        # --------------------------------------------------------
        # Return the stable summary structure expected by the
        # multi-variant experiment and validation code.
        # --------------------------------------------------------

        summary = {
            "trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_pnl": total_pnl,
            "final_balance": (
                float(final_balance)
                if final_balance is not None
                else (
                    float(initial_balance) + total_pnl
                    if initial_balance is not None
                    else total_pnl
                )
            ),
            "average_pnl": (
                total_pnl / total_trades
                if total_trades > 0
                else 0.0
            ),
            "max_drawdown": max_drawdown,
            "blocked_signals": int(
                result.get(
                    "blocked_signals",
                    0,
                )
                or 0
            ),
            "candidate_blocked_signals": int(
                result.get(
                    "candidate_blocked_signals",
                    0,
                )
                or 0
            ),
        }

        # Preserve the variant identifier when a raw experiment
        # result carries it.  The test/reporting layer expects
        # summarize_result(run_variant(...)) to remain printable.
        if "variant_name" in result:
            summary["variant_name"] = result["variant_name"]

        return summary


    # --------------------------------------------------------
    # Chronological split
    # --------------------------------------------------------

    @staticmethod
    def _split_by_time(
        data: pd.DataFrame,
        split_time,
    ):

        timestamp = pd.to_datetime(
            data["timestamp"],
            utc=True,
        )

        split_timestamp = pd.Timestamp(
            split_time
        )

        if split_timestamp.tzinfo is None:
            split_timestamp = (
                split_timestamp.tz_localize(
                    "UTC"
                )
            )
        else:
            split_timestamp = (
                split_timestamp.tz_convert(
                    "UTC"
                )
            )

        discovery = data.loc[
            timestamp < split_timestamp
        ].copy()

        validation = data.loc[
            timestamp >= split_timestamp
        ].copy()

        return (
            discovery,
            validation,
        )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    def evaluate_validation(
        self,
        analyzed_data: pd.DataFrame | None = None,
        variants=None,
        split_time=None,
        baseline_result: Dict | None = None,
        candidate_result: Dict | None = None,
    ) -> Dict:
        """Run chronological discovery/validation comparisons.

        The preferred interface accepts the already-run baseline and
        candidate results used by the multi-variant test.  The older
        analyzed_data/variants interface remains supported.
        """

        # New test-facing interface: use the exact already-transformed
        # datasets from the two completed experiment results.
        if baseline_result is not None and candidate_result is not None:
            baseline_data = baseline_result.get("data")
            candidate_data = candidate_result.get("data")

            if baseline_data is None or candidate_data is None:
                raise ValueError(
                    "baseline_result and candidate_result must contain data."
                )

            if split_time is None:
                timestamp = pd.to_datetime(
                    baseline_data["timestamp"],
                    utc=True,
                )
                split_time = timestamp.min() + (
                    timestamp.max() - timestamp.min()
                ) * 0.70

            split_time = pd.Timestamp(split_time)
            if split_time.tzinfo is None:
                split_time = split_time.tz_localize("UTC")
            else:
                split_time = split_time.tz_convert("UTC")

            baseline_discovery_data, baseline_validation_data = self._split_by_time(
                baseline_data, split_time
            )
            candidate_discovery_data, candidate_validation_data = self._split_by_time(
                candidate_data, split_time
            )

            baseline_discovery = self.run_variant(
                variant_name=baseline_result.get("variant_name", "V1_BASELINE"),
                transform=baseline,
                analyzed_data=baseline_discovery_data,
            )
            baseline_validation = self.run_variant(
                variant_name=baseline_result.get("variant_name", "V1_BASELINE"),
                transform=baseline,
                analyzed_data=baseline_validation_data,
            )

            candidate_name = candidate_result.get(
                "variant_name", "CANDIDATE"
            )
            candidate_discovery = self.run_variant(
                variant_name=candidate_name,
                transform=baseline,
                analyzed_data=candidate_discovery_data,
            )
            candidate_validation = self.run_variant(
                variant_name=candidate_name,
                transform=baseline,
                analyzed_data=candidate_validation_data,
            )

            baseline_discovery_summary = self.summarize_result(
                baseline_discovery
            )
            baseline_validation_summary = self.summarize_result(
                baseline_validation
            )
            candidate_discovery_summary = self.summarize_result(
                candidate_discovery
            )
            candidate_validation_summary = self.summarize_result(
                candidate_validation
            )

            comparison = {
                "trade_change": candidate_validation_summary["trades"] - baseline_validation_summary["trades"],
                "win_rate_change": candidate_validation_summary["win_rate"] - baseline_validation_summary["win_rate"],
                "profit_factor_change": candidate_validation_summary["profit_factor"] - baseline_validation_summary["profit_factor"],
                "pnl_change": candidate_validation_summary["total_pnl"] - baseline_validation_summary["total_pnl"],
                "drawdown_change": candidate_validation_summary["max_drawdown"] - baseline_validation_summary["max_drawdown"],
                "blocked_signal_change": candidate_validation_summary["blocked_signals"] - baseline_validation_summary["blocked_signals"],
            }

            return {
                "split_time": split_time,
                "baseline": {
                    "name": baseline_result.get("variant_name", "V1_BASELINE"),
                    "discovery": baseline_discovery_summary,
                    "validation": baseline_validation_summary,
                    "validation_max_drawdown": baseline_validation_summary["max_drawdown"],
                    "blocked_signals": baseline_discovery_summary["blocked_signals"] + baseline_validation_summary["blocked_signals"],
                },
                "candidate": {
                    "name": candidate_name,
                    "discovery": candidate_discovery_summary,
                    "validation": candidate_validation_summary,
                    "validation_max_drawdown": candidate_validation_summary["max_drawdown"],
                    "blocked_signals": candidate_discovery_summary["blocked_signals"] + candidate_validation_summary["blocked_signals"],
                },
                "baseline_discovery": baseline_discovery_summary,
                "baseline_validation": baseline_validation_summary,
                "candidate_discovery": candidate_discovery_summary,
                "candidate_validation": candidate_validation_summary,
                "comparison": comparison,
                "validation_changes": comparison,
            }

        # Backward-compatible interface.
        if analyzed_data is None:
            raise ValueError(
                "evaluate_validation requires analyzed_data or baseline_result/candidate_result."
            )

        if variants is None:
            variants = get_standard_variants()

        variant_items = self._normalize_variants(variants)

        if split_time is None:
            timestamp = pd.to_datetime(analyzed_data["timestamp"], utc=True)
            split_time = timestamp.min() + (
                timestamp.max() - timestamp.min()
            ) * 0.70

        split_time = pd.Timestamp(split_time)
        if split_time.tzinfo is None:
            split_time = split_time.tz_localize("UTC")
        else:
            split_time = split_time.tz_convert("UTC")

        discovery_data, validation_data = self._split_by_time(
            analyzed_data, split_time
        )

        baseline_discovery = self.run_variant(
            "V1_BASELINE", baseline, analyzed_data=discovery_data
        )
        baseline_validation = self.run_variant(
            "V1_BASELINE", baseline, analyzed_data=validation_data
        )

        candidate_items = [x for x in variant_items if x[0] != "V1_BASELINE"]
        if candidate_items:
            candidate_name, candidate_transform = candidate_items[0]
        else:
            candidate_name, candidate_transform = "V1_BASELINE", baseline

        candidate_discovery = self.run_variant(
            candidate_name, candidate_transform, analyzed_data=discovery_data
        )
        candidate_validation = self.run_variant(
            candidate_name, candidate_transform, analyzed_data=validation_data
        )

        bd = self.summarize_result(baseline_discovery)
        bv = self.summarize_result(baseline_validation)
        cd = self.summarize_result(candidate_discovery)
        cv = self.summarize_result(candidate_validation)

        return {
            "split_time": split_time,
            "baseline": {"name": "V1_BASELINE", "discovery": bd, "validation": bv, "validation_max_drawdown": bv["max_drawdown"]},
            "candidate": {"name": candidate_name, "discovery": cd, "validation": cv, "validation_max_drawdown": cv["max_drawdown"]},
            "baseline_discovery": bd,
            "baseline_validation": bv,
            "candidate_discovery": cd,
            "candidate_validation": cv,
            "comparison": {
                "trade_change": cv["trades"] - bv["trades"],
                "win_rate_change": cv["win_rate"] - bv["win_rate"],
                "profit_factor_change": cv["profit_factor"] - bv["profit_factor"],
                "pnl_change": cv["total_pnl"] - bv["total_pnl"],
                "drawdown_change": cv["max_drawdown"] - bv["max_drawdown"],
                "blocked_signal_change": cv["blocked_signals"] - bv["blocked_signals"],
            },
            "validation_changes": {
                "trade_change": cv["trades"] - bv["trades"],
                "win_rate_change": cv["win_rate"] - bv["win_rate"],
                "profit_factor_change": cv["profit_factor"] - bv["profit_factor"],
                "pnl_change": cv["total_pnl"] - bv["total_pnl"],
                "drawdown_change": cv["max_drawdown"] - bv["max_drawdown"],
                "blocked_signal_change": cv["blocked_signals"] - bv["blocked_signals"],
            },
        }

    def compare_results(
        self,
        baseline_result: Dict,
        candidate_result: Dict,
    ) -> Dict:
        """Compare two completed variant results."""

        baseline = self.summarize_result(baseline_result)
        candidate = self.summarize_result(candidate_result)

        changes = {
            "trades": candidate["trades"] - baseline["trades"],
            "win_rate": candidate["win_rate"] - baseline["win_rate"],
            "profit_factor": candidate["profit_factor"] - baseline["profit_factor"],
            "total_pnl": candidate["total_pnl"] - baseline["total_pnl"],
            "average_pnl": candidate["average_pnl"] - baseline["average_pnl"],
            "max_drawdown": candidate["max_drawdown"] - baseline["max_drawdown"],
            "final_balance": candidate["final_balance"] - baseline["final_balance"],
            "blocked_signals": candidate["blocked_signals"] - baseline["blocked_signals"],
        }

        return {
            "baseline": baseline,
            "candidate": candidate,
            "changes": changes,
        }


# ============================================================
# Compatibility alias
# ============================================================

ExperimentEngine = StrategyExperiment