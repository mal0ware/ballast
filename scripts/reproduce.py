"""Rebuild every table and figure.

Usage:
    uv run python scripts/reproduce.py            # real data from data/, writes results/
    uv run python scripts/reproduce.py --fast     # seeded synthetic data, writes a temp dir

``--fast`` needs no download and is what CI runs. It also cuts the bootstrap to
199 draws and the size study to 20 samples per design. Its numbers are not
findings, so it never writes into ``results/`` unless ``--out`` says so.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

from ballast.data import load_factors
from ballast.report import build_results
from ballast.synthetic import synthetic_factors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fast", action="store_true", help="use synthetic data, no download")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=None, help="output directory")
    args = parser.parse_args()

    started = time.perf_counter()
    if args.fast:
        data = synthetic_factors()
        out_dir = args.out or Path(tempfile.mkdtemp(prefix="ballast-smoke-"))
    else:
        data = load_factors(args.data_dir)
        out_dir = args.out or Path("results")
    if args.fast:
        written = build_results(data, out_dir, draws=199, size_sims=20)
    else:
        written = build_results(data, out_dir)
    for name, path in written.items():
        print(f"{name:28s} {path}")
    print(f"done in {time.perf_counter() - started:.1f}s; data through {data.monthly.index[-1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
