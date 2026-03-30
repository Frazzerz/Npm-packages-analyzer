JSON_FILE = "list_pkg.json"
ANALYSIS_DIR = "analysis_results"
CSV_FILENAME = "aggregate_metrics_by_single_version.csv"
CSV_BASE_DIR = "datasets_csv_raw"
OUTPUT_DIR_AGG = "datasets_csv_raw"
OUTPUT_DIR_AGG_GT0 = "datasets_csv_gt0"

COLUMNS_TO_EXTRACT = [
    "generic.list_file_types",
    "generic.len_list_file_types_unique",
    "generic.total_dim_bytes_pkg",
    "generic.longest_line_length_no_comments",
    "evasion.len_list_obfuscation_patterns_unique",
    "crypto.len_list_crypto_addresses_unique",
]

COLUMNS_PRESENCE = COLUMNS_TO_EXTRACT