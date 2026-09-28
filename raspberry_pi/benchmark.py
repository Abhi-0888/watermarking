"""
raspberry_pi/benchmark.py — Verification performance benchmark for the Pi.

Runs verify_document() N times and records:
  • wall-clock time per run (ms)
  • peak RSS memory per run (psutil, MB)
  • CPU% per run (psutil, measured over the run interval)

Outputs:
  • printed summary table (mean / median / min / max for each metric)
  • results/pi_benchmark.csv  (one row per run + a header comment with Pi model)

Usage (from project root, venv active):
    python3 raspberry_pi/benchmark.py \
        --file    samples/watermarked.png \
        --manifest samples/manifest.json \
        --provenance samples/provenance.json \
        -n 30

Optional flags:
    --registry   path/to/registry.json   (enables online mode if given)
    --mode       offline|online          (default: offline)
    -n / --runs  integer                 (default: 30)
    --csv        path/to/output.csv      (default: results/pi_benchmark.csv)
    --no-csv     skip CSV output

Dependencies (besides project requirements):
    pip install psutil
"""

import argparse
import csv
import os
import statistics
import sys
import time
from pathlib import Path

# Allow running as `python3 raspberry_pi/benchmark.py` from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import psutil  # type: ignore
    _PSUTIL = True
except ImportError:
    _PSUTIL = False
    print(
        "[benchmark] WARNING: psutil not installed — memory and CPU metrics will be 0.\n"
        "  Install with: pip install psutil",
        file=sys.stderr,
    )

from verification.verify import verify_document


def _pi_model() -> str:
    model_file = Path("/proc/device-tree/model")
    if model_file.exists():
        try:
            return model_file.read_text(encoding="utf-8", errors="replace").strip("\x00").strip()
        except OSError:
            pass
    return "Non-Pi / Unknown"


def _run_once(file_path: str, manifest_path: str, mode: str, registry_path, provenance_path):
    """Run one verification and return (elapsed_ms, peak_rss_mb, cpu_pct)."""
    proc = psutil.Process(os.getpid()) if _PSUTIL else None

    if proc:
        mem_before = proc.memory_info().rss
        proc.cpu_percent(interval=None)  # prime the counter

    t0 = time.perf_counter()
    verify_document(
        file_path,
        manifest_path,
        mode=mode,
        registry_path=registry_path,
        provenance_path=provenance_path,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    if proc:
        mem_after = proc.memory_info().rss
        cpu_pct = proc.cpu_percent(interval=None)
        peak_rss_mb = max(mem_before, mem_after) / (1024 * 1024)
    else:
        peak_rss_mb = 0.0
        cpu_pct = 0.0

    return elapsed_ms, peak_rss_mb, cpu_pct


def run_benchmark(
    file_path: str,
    manifest_path: str,
    mode: str,
    registry_path,
    provenance_path,
    n_runs: int,
    quiet_fn=None,
) -> list[dict]:
    """Run N timed verifications.  quiet_fn, if provided, wraps _run_once and
    suppresses verify_document's own stdout output so only the progress lines
    produced here are visible."""
    run_fn = quiet_fn if quiet_fn is not None else _run_once
    results = []
    print(f"[benchmark] Running {n_runs} verification passes (mode={mode}) ...")
    print(f"  {'Run':>4}   {'Time (ms)':>10}   {'RSS (MB)':>8}   {'CPU%':>6}")
    print(f"  {'-'*4}   {'-'*10}   {'-'*8}   {'-'*6}")

    # Warm-up run (not counted in results)
    try:
        run_fn(file_path, manifest_path, mode, registry_path, provenance_path)
    except Exception as exc:
        print(f"[benchmark] Warm-up failed: {exc}", file=sys.stderr)
        sys.exit(1)

    for i in range(1, n_runs + 1):
        try:
            elapsed_ms, rss_mb, cpu_pct = run_fn(
                file_path, manifest_path, mode, registry_path, provenance_path
            )
        except Exception as exc:
            print(f"[benchmark] Run {i} failed: {exc}", file=sys.stderr)
            continue
        results.append({"run": i, "elapsed_ms": elapsed_ms, "rss_mb": rss_mb, "cpu_pct": cpu_pct})
        print(f"  {i:>4}   {elapsed_ms:>10.1f}   {rss_mb:>8.1f}   {cpu_pct:>6.1f}")

    return results


def _stats(values: list[float]) -> dict:
    if not values:
        return {"mean": 0, "median": 0, "min": 0, "max": 0}
    return {
        "mean":   round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "min":    round(min(values), 2),
        "max":    round(max(values), 2),
    }


def print_summary(results: list[dict], model: str) -> None:
    times  = [r["elapsed_ms"] for r in results]
    mems   = [r["rss_mb"]     for r in results]
    cpus   = [r["cpu_pct"]    for r in results]

    t = _stats(times)
    m = _stats(mems)
    c = _stats(cpus)

    import sys as _sys
    _enc       = getattr(_sys.stdout, "encoding", "utf-8") or "utf-8"
    _unicode   = _enc.lower().replace("-", "") in ("utf8", "utf16", "utf32")
    _H         = "=" if not _unicode else "\u2550"   # ═  or =
    _S         = "-" if not _unicode else "\u2500"   # ─  or -

    col = 10
    sep = _S * 56
    print(f"\n{_H*56}")
    print(f"  BENCHMARK RESULTS -- {model}")
    print(f"{_H*56}")
    print(f"  Runs completed : {len(results)}")
    print(sep)
    print(f"  {'Metric':<20}{'Mean':>{col}}{'Median':>{col}}{'Min':>{col}}{'Max':>{col}}")
    print(sep)
    print(f"  {'Verify time (ms)':<20}{t['mean']:>{col}.1f}{t['median']:>{col}.1f}{t['min']:>{col}.1f}{t['max']:>{col}.1f}")
    print(f"  {'Peak RSS (MB)':<20}{m['mean']:>{col}.1f}{m['median']:>{col}.1f}{m['min']:>{col}.1f}{m['max']:>{col}.1f}")
    print(f"  {'CPU usage (%)':<20}{c['mean']:>{col}.1f}{c['median']:>{col}.1f}{c['min']:>{col}.1f}{c['max']:>{col}.1f}")
    print(f"{_H*56}\n")


def save_csv(results: list[dict], csv_path: str, model: str, mode: str) -> None:
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        fh.write(f"# SecureDocSystem Pi Benchmark\n")
        fh.write(f"# Pi model : {model}\n")
        fh.write(f"# Mode     : {mode}\n")
        fh.write(f"# Runs     : {len(results)}\n")
        writer = csv.DictWriter(fh, fieldnames=["run", "elapsed_ms", "rss_mb", "cpu_pct"])
        writer.writeheader()
        writer.writerows(results)
    print(f"[benchmark] Results saved → {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark verify_document() on the Raspberry Pi")
    parser.add_argument("--file",       required=True,  help="Protected image path")
    parser.add_argument("--manifest",   required=True,  help="Manifest JSON path")
    parser.add_argument("--registry",   default=None,   help="Registry JSON (for online mode)")
    parser.add_argument("--provenance", default=None,   help="Provenance JSON")
    parser.add_argument("--mode",       default="offline", choices=["offline", "online"])
    parser.add_argument("-n", "--runs", type=int, default=30, metavar="N",
                        help="Number of benchmark runs (default: 30)")
    parser.add_argument("--csv",        default="results/pi_benchmark.csv",
                        help="Output CSV path (default: results/pi_benchmark.csv)")
    parser.add_argument("--no-csv",     action="store_true", help="Skip CSV output")
    args = parser.parse_args()

    model = _pi_model()
    print(f"[benchmark] Pi model : {model}")
    print(f"[benchmark] File     : {args.file}")
    print(f"[benchmark] Manifest : {args.manifest}")
    print(f"[benchmark] Mode     : {args.mode}")

    # verify_document() prints a full report on every call.  We suppress that
    # during benchmarking so only the progress lines (which we print ourselves
    # directly to the real stdout) are visible.
    import contextlib

    _devnull_path = os.devnull  # "/dev/null" on Linux, "nul" on Windows

    # Monkey-patch _run_once to redirect verify_document's internal prints.
    _orig_run_once = _run_once

    def _run_once_quiet(file_path, manifest_path, mode, registry_path, provenance_path):
        with open(_devnull_path, "w") as _null:
            with contextlib.redirect_stdout(_null):
                return _orig_run_once(file_path, manifest_path, mode, registry_path, provenance_path)

    results = run_benchmark(
        args.file,
        args.manifest,
        args.mode,
        args.registry,
        args.provenance,
        args.runs,
        quiet_fn=_run_once_quiet,
    )

    print_summary(results, model)

    if not args.no_csv:
        save_csv(results, args.csv, model, args.mode)


if __name__ == "__main__":
    main()
