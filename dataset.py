"""
dataset.py - run AFTER main.py has finished analyzing all packages.

For each metric in COLUMNS_TO_EXTRACT it produces two CSV files:
  - OUTPUT_DIR_AGG/<class>/<metric>.csv      → all packages (zeros included)
  - OUTPUT_DIR_AGG_GT0/<class>/<metric>.csv  → only packages with at least one version > 0

Output format:
  package, version_-19, version_-18, ..., version_0
"""
import json
from config import (
    JSON_FILE,
    ANALYSIS_DIR,
    CSV_FILENAME,
    COLUMNS_TO_EXTRACT,
    OUTPUT_DIR_AGG,
    COLUMNS_PRESENCE,
    CSV_BASE_DIR,
    OUTPUT_DIR_AGG_GT0,
)
import pandas as pd
import os
import csv
import shutil
from pathlib import Path
from packaging.version import parse as parse_version
from packaging.version import InvalidVersion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def delete_dir():
    """Remove output directories so we start fresh."""
    for dir_name in [CSV_BASE_DIR]:
        dir_path = Path(dir_name)
        if dir_path.exists() and dir_path.is_dir():
            shutil.rmtree(dir_path)


def load_package_list():
    with open(JSON_FILE, "r") as f:
        return json.load(f)


def load_csv_data(pkg_name: str):
    """Load aggregate_metrics_by_single_version.csv for one package."""
    pkg_name_safe = pkg_name.replace("/", "_")
    csv_path  = os.path.join(ANALYSIS_DIR, pkg_name_safe, CSV_FILENAME)
    r_csv_path = os.path.join(ANALYSIS_DIR, pkg_name_safe, "R-" + CSV_FILENAME)

    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, sep=",", keep_default_na=False)
            return "ok", df
        except Exception:
            return "load_error", None
    if os.path.exists(r_csv_path):
        return "r_prefix_error", None
    return "not_found", None


def get_class_from_metric(col_name: str) -> str:
    """Return the subdirectory name based on the metric prefix."""
    for prefix in ("generic", "evasion", "payload", "exfiltration", "crypto"):
        if col_name.startswith(prefix + "."):
            return prefix
    return "other"


def metric_to_filename(col_name: str) -> str:
    """Convert a dotted column name to a short filename.

    Special rename: obfuscation_patterns → hexadecimal_values
    (matches the naming used in the thesis / GitHub datasets).
    """
    # Rename evasion columns to match thesis terminology
    col_name = col_name.replace("obfuscation_patterns_count",      "hexadecimal_count")
    col_name = col_name.replace("list_obfuscation_patterns",       "list_hexadecimal_values")
    col_name = col_name.replace("len_list_obfuscation_patterns_unique",
                                "len_list_hexadecimal_values_unique")
    # Strip class prefix and convert dots → underscores
    short = col_name.split(".", 1)[1]
    return short.replace(".", "_") + ".csv"


def append_package_to_column_files(pkg_name: str, df: pd.DataFrame, stats_agg: dict) -> str:
    """Sort versions and append one row per metric CSV."""
    try:
        df = df.sort_values(by="version", key=lambda s: s.map(parse_version))
    except (InvalidVersion, KeyError, Exception):
        return "sort_error"

    for col in COLUMNS_TO_EXTRACT:
        if col in df.columns and len(df[col]) == 20:
            values = df[col].fillna(0).replace("", 0).tolist()
            row = [pkg_name] + values
            metric_file = metric_to_filename(col)
            class_dir   = get_class_from_metric(col)
            filepath = os.path.join(OUTPUT_DIR_AGG, class_dir, metric_file)
            with open(filepath, "a", newline="") as f:
                csv.writer(f).writerow(row)

            stats_agg.setdefault(class_dir, {}).setdefault(col, 0)
            stats_agg[class_dir][col] += 1

    return "ok"


# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------

def is_present(x) -> bool:
    """Return True if the cell contains a meaningful (non-zero, non-empty) value."""
    if pd.isna(x):
        return False
    if isinstance(x, (int, float)):
        return x > 0
    s = str(x).strip()
    return s not in ("", "0", "[]")


def save_packages_with_presence(metric_csv_path: str, output_dir: str, class_dir: str) -> int:
    """Write a filtered CSV that keeps only rows with at least one version > 0."""
    metric_name = os.path.basename(metric_csv_path).replace(".csv", "")
    df = pd.read_csv(metric_csv_path, keep_default_na=False)

    version_cols = [c for c in df.columns if c.startswith("version_")]
    mask = df[version_cols].apply(lambda col: col.map(is_present)).any(axis=1)
    df_filtered = df[mask]

    output_path = os.path.join(output_dir, class_dir, metric_name + ".csv")
    df_filtered.to_csv(output_path, index=False)
    print(
        f"Metric: {metric_name:55s} | class: {class_dir:12s} | "
        f"total: {len(df):4d} | saved (>0): {len(df_filtered):4d}"
    )
    return len(df_filtered)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    delete_dir()

    print("Loading package list …")
    pkg_list = load_package_list()
    print(f"Found {len(pkg_list)} packages in {JSON_FILE}")

    # Create output directories
    classes = list({get_class_from_metric(c) for c in COLUMNS_TO_EXTRACT})
    for base in [OUTPUT_DIR_AGG, OUTPUT_DIR_AGG_GT0]:
        for c in classes:
            os.makedirs(os.path.join(base, c), exist_ok=True)

    # Initialize empty CSV files with header row
    version_cols = ["package"] + [f"version_{i - 20}" for i in range(1, 21)]
    for col in COLUMNS_TO_EXTRACT:
        metric_file = metric_to_filename(col)
        class_dir   = get_class_from_metric(col)
        filepath = os.path.join(OUTPUT_DIR_AGG, class_dir, metric_file)
        pd.DataFrame(columns=version_cols).to_csv(filepath, index=False)

    # Process packages
    stats_agg = {}
    counts = dict(processed=0, not_found=0, load_error=0, sort_error=0, r_prefix=0)

    for pkg in pkg_list:
        status, df = load_csv_data(pkg)
        if status == "not_found":
            counts["not_found"] += 1
            continue
        if status == "load_error":
            counts["load_error"] += 1
            continue
        if status == "r_prefix_error":
            counts["r_prefix"] += 1
            continue

        res = append_package_to_column_files(pkg, df, stats_agg)
        if res == "sort_error":
            counts["sort_error"] += 1
            continue
        counts["processed"] += 1

    # Summary
    print("\n--- Aggregation complete ---")
    for class_dir, metrics in stats_agg.items():
        print(f"\nClass: {class_dir}")
        for metric, count in metrics.items():
            print(f"  {metric}: {count} packages")
    print(f"\nProcessed:   {counts['processed']}")
    print(f"Not found:   {counts['not_found']}")
    print(f"R-prefix:    {counts['r_prefix']}")
    print(f"Load error:  {counts['load_error']}")
    print(f"Sort error:  {counts['sort_error']}")

    # Produce filtered (>0) CSVs
    print("\n--- Filtering packages with at least one version > 0 ---")
    for col in COLUMNS_PRESENCE:
        metric_file = metric_to_filename(col)
        class_dir   = get_class_from_metric(col)
        filepath = os.path.join(OUTPUT_DIR_AGG, class_dir, metric_file)
        if os.path.exists(filepath):
            save_packages_with_presence(filepath, OUTPUT_DIR_AGG_GT0, class_dir)


if __name__ == "__main__":
    main()