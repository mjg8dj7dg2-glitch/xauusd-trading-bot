#!/usr/bin/env python3
"""
Read-only static audit for the trading_bot project.
- Does not import or execute project modules.
- Does not run tests or backtests.
- Does not modify existing project files.
- Writes one report: system_audit_report.md in the project root.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "system_audit_report.md"

EXCLUDED_DIRS = {
    ".venv", "venv", "env", "__pycache__", ".git", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules", "site-packages",
}
SKIP_SUFFIXES = {".pyc", ".pyo", ".exe", ".dll", ".so", ".bin", ".parquet"}
MAX_TEXT_BYTES = 2_000_000

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)

def files_under(root: Path):
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for name in names:
            p = Path(base) / name
            if p.suffix.lower() in SKIP_SUFFIXES:
                continue
            yield p

def read_text(path: Path):
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

def md_escape(value):
    return str(value).replace("|", r"\|").replace("\n", " ")

def main():
    all_files = list(files_under(ROOT))
    python_files = [p for p in all_files if p.suffix.lower() == ".py"]
    data_files = [p for p in all_files if p.suffix.lower() in {".csv", ".json", ".yaml", ".yml", ".toml", ".ini"}]
    findings = []
    sections = []

    sections.append("# Trading Bot — Read-only System Audit\n")
    sections.append(f"- Audit time: {datetime.now().astimezone().isoformat(timespec='seconds')}")
    sections.append(f"- Project root: `{ROOT}`")
    sections.append("- Execution policy: **No project modules imported; no tests/backtests run; no existing files modified.**")
    sections.append("- Scope: static source inspection and analysis of already-saved JSON/CSV outputs.")
    sections.append("\n## 1. Inventory\n")
    counts = Counter(p.suffix.lower() or "[no extension]" for p in all_files)
    sections.append(f"- Total files scanned (excluding virtual environments, caches, and common binary files): **{len(all_files)}**")
    sections.append(f"- Python files: **{len(python_files)}**")
    sections.append(f"- Data/config-like files: **{len(data_files)}**")
    sections.append("\n| Extension | Count |\n|---|---:|")
    for ext, count in sorted(counts.items()):
        sections.append(f"| `{md_escape(ext)}` | {count} |")
    sections.append("\n### Key project files\n")
    key_names = {
        "run_breakout_backtest.py", "run_cooldown_comparison.py",
        "run_cooldown_2loss.py", "run_cooldown_2loss_verify.py",
        "diagnose_breakout_results.py", "requirements.txt", "pyproject.toml",
        "pytest.ini", "setup.cfg", "tox.ini",
    }
    key_files = [p for p in all_files if p.name in key_names]
    for p in sorted(key_files):
        sections.append(f"- `{rel(p)}` — {p.stat().st_size} bytes; SHA-256 `{sha256(p)}`")
    if not key_files:
        sections.append("- No known runner/config filenames found.")

    sections.append("\n## 2. Python syntax and static source checks\n")
    sections.append("These checks parse source without importing or executing it. Pattern matches are leads for review, not automatic proof of defects.\n")
    parse_errors = []
    pattern_hits = []
    patterns = [
        ("possible look-ahead / future data", re.compile(r"\bshift\s*\(\s*-\s*\d+|\.iloc\s*\[\s*i\s*\+\s*\d+|center\s*=\s*True", re.I)),
        ("broad exception handling", re.compile(r"except\s*:\s*(?:#.*)?$|except\s+Exception\b", re.M)),
        ("debug / unfinished markers", re.compile(r"\b(TODO|FIXME|XXX|NotImplementedError)\b")),
        ("randomness", re.compile(r"\b(random|np\.random|numpy\.random)\b")),
        ("possible time-zone-naive datetime usage", re.compile(r"datetime\.now\(\)|datetime\.utcnow\(\)|pd\.to_datetime\([^,\n]+\)")),
        ("file writes / overwrite operations", re.compile(r"\.to_csv\s*\(|write_text\s*\(|open\s*\([^,\n]+,\s*['\"]w")),
        ("credential-like literals (value redacted)", re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{6,}['\"]")),
    ]
    for p in sorted(python_files):
        text = read_text(p)
        if text is None:
            findings.append(("MEDIUM", f"Skipped large Python file during text inspection: {rel(p)}"))
            continue
        try:
            ast.parse(text, filename=str(p))
        except SyntaxError as e:
            parse_errors.append((rel(p), e.lineno, e.msg))
        lines = text.splitlines()
        for label, regex in patterns:
            for i, line in enumerate(lines, 1):
                if regex.search(line):
                    snippet = line.strip()
                    if label == "credential-like literals (value redacted)":
                        snippet = "[matching line redacted; inspect locally]"
                    pattern_hits.append((label, rel(p), i, snippet[:180]))
    if parse_errors:
        sections.append("### Python syntax errors\n")
        for path, line, msg in parse_errors:
            sections.append(f"- **ERROR** `{path}:{line}` — {md_escape(msg)}")
            findings.append(("HIGH", f"Python syntax error in {path}:{line}: {msg}"))
    else:
        sections.append("- No Python syntax errors found in files that could be read and parsed.")
    sections.append("\n### Review leads\n")
    if pattern_hits:
        for label, path, line, snippet in pattern_hits[:250]:
            sections.append(f"- `{path}:{line}` — **{label}** — `{md_escape(snippet)}`")
        if len(pattern_hits) > 250:
            sections.append(f"- Truncated: {len(pattern_hits) - 250} additional pattern hits omitted.")
    else:
        sections.append("- No matches for the selected review patterns.")
    sections.append("\n### Import map (static)\n")
    for p in sorted(python_files):
        text = read_text(p)
        if text is None:
            continue
        try:
            tree = ast.parse(text, filename=str(p))
        except SyntaxError:
            continue
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append("." * node.level + (node.module or ""))
        if imports:
            sections.append(f"- `{rel(p)}`: " + ", ".join(sorted(set(imports))))

    sections.append("\n## 3. Dependency/configuration files\n")
    config_names = {"requirements.txt", "pyproject.toml", "Pipfile", "environment.yml", "conda.yml", "setup.cfg", "pytest.ini", "tox.ini"}
    configs = [p for p in all_files if p.name in config_names]
    if configs:
        for p in sorted(configs):
            sections.append(f"\n### `{rel(p)}`\n")
            text = read_text(p)
            if text is None:
                sections.append("- File too large or unreadable.")
            else:
                # Avoid printing likely credentials if any appear in config.
                safe_lines = []
                for line in text.splitlines()[:160]:
                    if re.search(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]", line):
                        safe_lines.append("[credential-like config line redacted]")
                    else:
                        safe_lines.append(line)
                sections.append("```text\n" + "\n".join(safe_lines) + "\n```")
    else:
        sections.append("- No common dependency/configuration file found.")

    sections.append("\n## 4. Existing saved backtest outputs\n")
    metric_files = [p for p in all_files if p.name == "metrics.json" and "backtest" in str(p).lower()]
    if not metric_files:
        sections.append("- No `metrics.json` files under paths containing `backtest` were found.")
    for mp in sorted(metric_files):
        sections.append(f"\n### `{rel(mp)}`\n")
        try:
            metrics = json.loads(mp.read_text(encoding="utf-8"))
            for key in ("initial_balance", "final_balance", "net_profit", "trades", "win_rate_pct",
                        "expectancy_per_trade", "profit_factor", "max_drawdown_pct", "gross_profit", "gross_loss"):
                if key in metrics:
                    sections.append(f"- `{key}`: `{metrics[key]}`")
            if all(k in metrics for k in ("initial_balance", "final_balance", "net_profit")):
                diff = float(metrics["initial_balance"]) + float(metrics["net_profit"]) - float(metrics["final_balance"])
                sections.append(f"- Balance identity error (`initial_balance + net_profit - final_balance`): `{diff:.12g}`")
                if abs(diff) > 1e-6:
                    findings.append(("HIGH", f"Balance identity mismatch in {rel(mp)}: {diff}"))
        except Exception as e:
            sections.append(f"- Could not parse metrics JSON: {type(e).__name__}: {e}")
            findings.append(("MEDIUM", f"Could not parse metrics file {rel(mp)}"))

        trades_path = mp.parent / "trades.csv"
        if trades_path.exists():
            try:
                with trades_path.open("r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    headers = reader.fieldnames or []
                sections.append(f"- Trade rows in CSV: `{len(rows)}`")
                sections.append(f"- Trade CSV SHA-256: `{sha256(trades_path)}`")
                pnl_col = next((h for h in headers if h and h.lower() in {"pnl", "net_pnl", "profit_loss"}), None)
                if pnl_col:
                    vals = []
                    bad = 0
                    for row in rows:
                        try:
                            vals.append(float(row[pnl_col]))
                        except (TypeError, ValueError):
                            bad += 1
                    total = sum(vals)
                    sections.append(f"- P&L column: `{pnl_col}`; numeric rows: `{len(vals)}`; invalid/missing: `{bad}`; sum: `{total:.12g}`")
                    try:
                        reported = float(metrics.get("net_profit"))
                        diff = total - reported
                        sections.append(f"- Trade-P&L sum minus reported net profit: `{diff:.12g}`")
                        if abs(diff) > max(0.01, abs(reported) * 1e-8):
                            findings.append(("HIGH", f"Trade P&L sum mismatch in {rel(trades_path)}: {diff}"))
                    except Exception:
                        pass
                else:
                    sections.append(f"- No recognized P&L column found. CSV headers: {headers}")
                sections.append(f"- Trade CSV columns: {', '.join(headers) if headers else '(none)'}")
            except Exception as e:
                sections.append(f"- Could not read trade CSV: {type(e).__name__}: {e}")
        else:
            sections.append("- Matching `trades.csv` not found.")

        equity_path = mp.parent / "equity_curve.csv"
        if equity_path.exists():
            sections.append(f"- Equity CSV SHA-256: `{sha256(equity_path)}`")
            try:
                with equity_path.open("r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    erows = list(reader)
                    eheaders = reader.fieldnames or []
                sections.append(f"- Equity rows: `{len(erows)}`; columns: {', '.join(eheaders) if eheaders else '(none)'}")
                equity_col = next((h for h in eheaders if h and h.lower() in {"equity", "balance", "account_equity"}), None)
                if equity_col:
                    ev = []
                    for row in erows:
                        try:
                            ev.append(float(row[equity_col]))
                        except (TypeError, ValueError):
                            continue
                    if ev:
                        peak = ev[0]
                        max_dd = 0.0
                        for v in ev:
                            peak = max(peak, v)
                            if peak:
                                max_dd = max(max_dd, (peak - v) / peak * 100)
                        sections.append(f"- Recomputed max drawdown from `{equity_col}`: `{max_dd:.6f}%`")
                        try:
                            reported_dd = float(metrics.get("max_drawdown_pct"))
                            sections.append(f"- Recomputed minus reported max drawdown: `{max_dd - reported_dd:.6f}` percentage points")
                        except Exception:
                            pass
            except Exception as e:
                sections.append(f"- Could not read equity CSV: {type(e).__name__}: {e}")

    sections.append("\n## 5. Data and duplicate-output inventory\n")
    data_candidates = [p for p in all_files if p.suffix.lower() in {".csv", ".parquet", ".feather"}]
    for p in sorted(data_candidates)[:200]:
        try:
            sections.append(f"- `{rel(p)}` — {p.stat().st_size} bytes — SHA-256 `{sha256(p)}`")
        except OSError:
            pass
    if len(data_candidates) > 200:
        sections.append(f"- Truncated: {len(data_candidates)-200} additional data files omitted.")
    # Compare hashes for same-named files, especially saved result files.
    by_name = {}
    for p in all_files:
        if p.name in {"trades.csv", "signals.csv", "equity_curve.csv", "metrics.json"}:
            try:
                by_name.setdefault((p.name, sha256(p)), []).append(rel(p))
            except OSError:
                pass
    duplicate_groups = [paths for (name, digest), paths in by_name.items() if len(paths) > 1]
    if duplicate_groups:
        sections.append("\n### Byte-identical saved output files\n")
        for paths in duplicate_groups:
            sections.append("- " + " = ".join(f"`{p}`" for p in paths))
    else:
        sections.append("- No byte-identical groups found among recognized saved-output filenames.")

    sections.append("\n## 6. Findings summary\n")
    if findings:
        for severity, message in findings:
            sections.append(f"- **{severity}** — {message}")
    else:
        sections.append("- No automatic accounting or syntax findings were raised by this script. This does not mean the strategy or implementation is correct.")
    sections.append("\n## 7. Limitations and next review\n")
    sections.append("- This is a static, first-pass audit, not proof of profitability or broker-execution correctness.")
    sections.append("- The script does not execute project code, run tests, contact a broker, access the network, or inspect the `.venv`.")
    sections.append("- Static pattern matches can be false positives. Absence of matches does not prove absence of bugs.")
    sections.append("- Review the report before any code changes. The most useful follow-up is to share this report back for a focused interpretation.")
    REPORT.write_text("\n".join(sections) + "\n", encoding="utf-8")
    print(f"Audit complete. Report written to: {REPORT}")
    print(f"Scanned {len(all_files)} files; parsed {len(python_files)} Python files; found {len(metric_files)} saved metrics.json files.")
    print("No project modules, tests, or backtests were executed.")
    print("Please review the report for accidental sensitive information before sharing it.")

if __name__ == "__main__":
    main()
