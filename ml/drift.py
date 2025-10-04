import argparse
import os
import sys
import numpy as np
import pandas as pd


def psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    # Population Stability Index (simple implementation)
    eps = 1e-6
    expected_perc, edges = np.histogram(expected, bins=bins)
    actual_perc, _ = np.histogram(actual, bins=edges)
    expected_perc = expected_perc / (expected_perc.sum() + eps)
    actual_perc = actual_perc / (actual_perc.sum() + eps)
    psi_vals = (actual_perc - expected_perc) * np.log((actual_perc + eps) / (expected_perc + eps))
    return float(np.sum(psi_vals))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default=os.getenv("ML_BASELINE_DATA", "./ml/data/baseline.csv"))
    parser.add_argument("--input", default=os.getenv("ML_INPUT_DATA", "./ml/data/new_batch.csv"))
    parser.add_argument("--threshold", type=float, default=0.2)
    args = parser.parse_args()

    if not os.path.exists(args.baseline) or not os.path.exists(args.input):
        print("No data files found; skipping drift check.")
        sys.exit(0)

    base = pd.read_csv(args.baseline)
    new = pd.read_csv(args.input)

    common_cols = [c for c in base.columns if c in new.columns and base[c].dtype != "object"]
    if not common_cols:
        print("No common numeric columns; skipping drift check.")
        sys.exit(0)

    psi_vals = [psi(base[c].values, new[c].values) for c in common_cols]
    max_psi = max(psi_vals)
    print(f"PSI per column: {dict(zip(common_cols, [round(v,4) for v in psi_vals]))}")
    print(f"Max PSI: {max_psi:.4f}")

    if max_psi > args.threshold:
        print("retrain recommended: true")
        sys.exit(1)
    else:
        print("retrain recommended: false")
        sys.exit(0)


if __name__ == "__main__":
    main()
