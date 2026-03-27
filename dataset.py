import json
from config import (
    JSON_FILE,
    ANALYSIS_DIR,
    CSV_FILENAME,
    COLUMNS_TO_EXTRACT,
    OUTPUT_DIR_AGG,
    COLUMNS_PRESENCE,
    CSV_BASE_DIR,
    OUTPUT_DIR_AGG_GT0
)
import pandas as pd
import os
import csv
import shutil
from pathlib import Path
from packaging.version import parse as parse_version
from packaging.version import InvalidVersion
import ast

#########################################
#   UTILS FUNCTIONS                     #
#########################################

def delete_dir():
    dirs_to_delete = [CSV_BASE_DIR]
    for dir_name in dirs_to_delete:
        dir_path = Path(dir_name)
        if dir_path.exists() and dir_path.is_dir():
            shutil.rmtree(dir_path)

def load_package_list():
    """Load package list from JSON file"""
    with open(JSON_FILE, 'r') as f:
        return json.load(f)

def load_csv_data(pkg_name: str) -> pd.DataFrame:
    """Upload CSV for a single package"""
    pkg_name = pkg_name.replace("/", "_")   # sanitize some inputs
    csv_path = os.path.join(ANALYSIS_DIR, pkg_name, CSV_FILENAME)
    r_csv_path = os.path.join(ANALYSIS_DIR, pkg_name, "R-" + CSV_FILENAME)  # removed pkg from analysis
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, sep=',', keep_default_na=False)
            return "ok", df
        except:
            return "load_error", None
    if os.path.exists(r_csv_path):
        #print (f"Skip pkg {pkg_name}: R-prefix file exists")
        return "r_prefix_error", None
    
    return "not_found", None
    
def get_class_from_metric(col_name):
    if col_name.startswith("generic."):
        return "generic"
    if col_name.startswith("evasion."):
        return "evasion"
    if col_name.startswith("payload."):
        return "payload"
    if col_name.startswith("exfiltration."):
        return "exfiltration"
    if col_name.startswith("crypto."):
        return "crypto"
    return "other"

def metric_to_filename(col_name):
    # Renaming
    if "obfuscation_patterns_count" in col_name:
        col_name = col_name.replace("obfuscation_patterns_count", "hexadecimal_count")
    if "list_obfuscation_patterns" in col_name:
        col_name = col_name.replace("list_obfuscation_patterns", "list_hexadecimal_count")
    if "len_list_obfuscation_patterns_unique" in col_name:
        col_name = col_name.replace("len_list_obfuscation_patterns_unique", "len_list_hexadecimal_count_unique")
    # toglie "generic.", "evasion.", ecc.
    short = col_name.split(".", 1)[1]
    return short.replace(".", "_") + ".csv"

def append_package_to_column_files(pkg_name, df: pd.DataFrame, stats_agg):
    try:
        df = df.sort_values(by="version", key=lambda s: s.map(parse_version))
    except InvalidVersion:
        #print(f"Skip pkg {pkg_name}: colonne non valide come versioni")
        return "sort_error"  # skip the whole package
    except KeyError:
        #print(f"Skip pkg {pkg_name}: manca la colonna version")
        return "sort_error"
    except Exception as e:
        #print(f"Error sorting versions for {pkg_name}: {e}")
        return "sort_error"
    for col in COLUMNS_TO_EXTRACT:
        if col in df.columns and len(df[col]) == 20:
            values = (df[col].fillna(0).replace('', 0).tolist())
            row = [pkg_name] + values
            metric_file = metric_to_filename(col)
            class_dir = get_class_from_metric(col)
            filepath = os.path.join(OUTPUT_DIR_AGG, class_dir, metric_file)
            with open(filepath, 'a', newline='') as f:
                csv.writer(f).writerow(row)

            stats_agg.setdefault(class_dir, {})
            stats_agg[class_dir].setdefault(col, 0)
            stats_agg[class_dir][col] += 1

    return "ok"

#########################################
#   PRE-PULIZIA FUNCTIONS               #
#########################################

def apply_inheritance_logic(output_dir_agg):
    """Metriche che ereditano il valore dai file 'original'"""
    inherit_mapping = {
        "weighted_avg_shannon_entropy_no_comments.csv": "weighted_avg_shannon_entropy_original.csv",
        "weighted_avg_blank_space_and_character_ratio_no_comments.csv": "weighted_avg_blank_space_and_character_ratio_original.csv",
    }
    path_agg_generic = os.path.join(output_dir_agg, "generic")
    
    for target_file, source_file in inherit_mapping.items():
        t_path = os.path.join(path_agg_generic, target_file)
        s_path = os.path.join(path_agg_generic, source_file)
        
        if os.path.exists(t_path) and os.path.exists(s_path):
            df_t = pd.read_csv(t_path, keep_default_na=False)
            df_s = pd.read_csv(s_path, keep_default_na=False).set_index("package").reindex(df_t["package"]).reset_index()
            
            v_cols = [c for c in df_t.columns if c.startswith("version_")]
            for col in v_cols:
                mask = (pd.to_numeric(df_t[col], errors='coerce').fillna(0) == 0)
                df_t[col] = df_t[col].where(~mask, df_s[col])
            
            df_t.to_csv(t_path, index=False)
            #print(f"Fixed (Inherit): {target_file}")

def is_list_boring(val_str):
    """Ritorna True se la lista contiene SOLO 'eth' (case-insensitive). 
    Ritorna False se contiene almeno una crypto "interessante" (es. 'ethereum', 'bitcoin')."""
    if pd.isna(val_str) or val_str in ["", "[]", 0, "0"]:
        return None 
    try:
        if isinstance(val_str, str):
            try:
                val = ast.literal_eval(val_str)
            except:
                val = [val_str]
        else:
            val = val_str
            
        if not isinstance(val, list): val = [val]
        if len(val) == 0: return None
        unique_items = set(str(x).lower().strip() for x in val)
        if unique_items.issubset({'eth'}): #, 'btc'}):
            return True
        else:
            return False
    except:
        return None

def should_skip_package_crypto(row, v_cols):
    results = [is_list_boring(row[col]) for col in v_cols]
    if False in results:
        return False
    if True in results:
        return True
    return False

def is_present(x):
    if pd.isna(x):
        return False
    if isinstance(x, (int, float)):
        return x > 0
    s = str(x).strip()
    if s == "" or s == "0" or s == "[]":
        return False
    return True

# A volte weighted_avg_blank_space_and_character_ratio contiene inf
def get_packages_always_numeric(metric_paths):
    """Ritorna l'insieme dei package che: NON contengono inf, per tutte le versioni e in tutte le metriche passate"""
    valid_pkgs = None
    for path in metric_paths:
        df = pd.read_csv(path, keep_default_na=False)
        version_cols = [c for c in df.columns if c.startswith("version_")]
        mask_numeric = df[version_cols].apply(
            lambda row: pd.to_numeric(row, errors="coerce").replace([float("inf")], pd.NA).notna().all(),
            axis=1
        )
        pkgs_ok = set(df.loc[mask_numeric, "package"])
        valid_pkgs = pkgs_ok if valid_pkgs is None else valid_pkgs & pkgs_ok
    return valid_pkgs

#---------
def save_packages_with_presence(metric_csv_path, output_dir, class_dir, boring_packages=None, allowed_packages=None):
    metric_name = os.path.basename(metric_csv_path).replace(".csv", "")
    df = pd.read_csv(metric_csv_path, keep_default_na=False) # c'è un pkg che si chiama nan, e me lo legge come NaN pandas
    
    if allowed_packages is not None:
        df = df[df["package"].isin(allowed_packages)]

    version_cols = [c for c in df.columns if c.startswith("version_")]
    
    target_crypto_metrics = [
        "cryptocurrency_name", 
        "list_cryptocurrency_names", 
        "len_list_cryptocurrency_names_unique"
    ]

    mask = df[version_cols].apply(lambda col: col.map(is_present)).any(axis=1)
    if boring_packages and metric_name in target_crypto_metrics:
        # Esclude i pacchetti identificati come boring (solo eth)
        mask = mask & (~df['package'].isin(boring_packages))

    df_filtered = df[mask]

    output_path = os.path.join(output_dir, class_dir, metric_name + ".csv")
    df_filtered.to_csv(output_path, index=False)
    print(f"Metric: {metric_name} | Classe: {class_dir} | Tot pacchetti: {len(df)} | Salvati (>0): {len(df_filtered)}")
    return len(df_filtered), metric_name, class_dir
# ------

def main():
    delete_dir()
    print("Loading package list...")
    pkg_list = load_package_list()
    print(f"Found {len(pkg_list)} packages in JSON")

    skipped_not_found = skipped_load_error = skipped_sort_error = processed = skipped_r_prefix = 0
    os.makedirs(OUTPUT_DIR_AGG, exist_ok=True)
    classes = ["generic", "evasion", "payload", "exfiltration", "crypto"]
    for base in [OUTPUT_DIR_AGG, OUTPUT_DIR_AGG_GT0]:
        for c in classes:
            os.makedirs(os.path.join(base, c), exist_ok=True)
    
    # Inizializza CSV vuoti
    for col in COLUMNS_TO_EXTRACT:
        metric_file = metric_to_filename(col)
        class_dir = get_class_from_metric(col)
        filepath = os.path.join(OUTPUT_DIR_AGG, class_dir, metric_file)
        columns = ["package"] + [f"version_{i-20}" for i in range(1, 21)]  # version_-19 a version_0
        pd.DataFrame(columns=columns).to_csv(filepath, index=False)
    
    # Dizionario per statistiche
    stats_agg = {}

    for pkg in pkg_list:
        status, df = load_csv_data(pkg)
        if status == "not_found":
            skipped_not_found += 1
            continue
        if status == "load_error":
            skipped_load_error += 1
            continue
        if status == "r_prefix_error":
            skipped_r_prefix += 1
            continue

        res = append_package_to_column_files(pkg, df, stats_agg)
        if res == "sort_error":
            skipped_sort_error += 1
            continue
        processed += 1

    print("\n--- Aggregazione completata ---")
    for class_dir, metrics in stats_agg.items():
        print(f"\nClasse: {class_dir} (tot metriche: {len(metrics)})")
        for metric, count in metrics.items():
            print(f"  Metrica: {metric} | Pacchetti salvati: {count}")
    
    # Somma totale metriche
    tot_metriche = sum(len(metrics) for metrics in stats_agg.values())
    print(f"\nTotale metriche: {tot_metriche}")
    print(f"Processed correctly: {processed}")
    print(f"Skipped (file not found): {skipped_not_found}")
    print(f"Skipped (R-prefix error): {skipped_r_prefix}")
    print(f"Skipped (CSV load error): {skipped_load_error}")
    print(f"Skipped (version sort error): {skipped_sort_error}")
    print(f"Total packages before remove: {processed + skipped_r_prefix}")
    print(f"Total packages: {len(pkg_list)}")
            
    apply_inheritance_logic(OUTPUT_DIR_AGG)

    # Per aggregazione con filtri >0
    # Identificazione pacchetti da skippare (solo 'eth')
    boring_packages = set()
    list_names_path = os.path.join(OUTPUT_DIR_AGG, "crypto", "list_cryptocurrency_names.csv")
    
    if os.path.exists(list_names_path):
        df_names = pd.read_csv(list_names_path)
        v_cols = [c for c in df_names.columns if c.startswith("version_")]
        
        for _, row in df_names.iterrows():
            if should_skip_package_crypto(row, v_cols):
                boring_packages.add(row['package']) 

    tot_metriche_presenza = 0
    metriche_zero = []
    
    target_metrics = [
        "generic.weighted_avg_blank_space_and_character_ratio_original",
        "generic.weighted_avg_blank_space_and_character_ratio_no_comments",
    ]
    metric_paths = []
    for m in target_metrics:
        metric_file = metric_to_filename(m)
        class_dir = get_class_from_metric(m)
        metric_paths.append(os.path.join(OUTPUT_DIR_AGG, class_dir, metric_file))
    df_tmp = pd.read_csv(metric_paths[0])
    tot_pkgs = len(df_tmp["package"])
    always_numeric_pkgs = get_packages_always_numeric(metric_paths)

    # Salvataggio pacchetti con almeno un valore > 0 per ogni metrica di presenza (anche con liste (se presenta almeno un elemento))
    os.makedirs(OUTPUT_DIR_AGG_GT0, exist_ok=True)
    print("\nFiltraggio pacchetti >0 o presenti per metrica di presenza")

    print(f"Rimossi pacchetti per weighted_avg_blank_space_and_character_ratio (contenevano inf): {tot_pkgs - len(always_numeric_pkgs)}")
    print(f"Identificati {len(boring_packages)} pacchetti da escludere (solo 'eth') per cryptocurrency_name.")

    inf_sensitive_metrics = {
        "weighted_avg_blank_space_and_character_ratio_original",
        "weighted_avg_blank_space_and_character_ratio_no_comments",
    }

    for col in COLUMNS_PRESENCE:
        metric_file = metric_to_filename(col)
        metric_name = metric_file.replace(".csv", "")
        class_dir = get_class_from_metric(col)
        filepath = os.path.join(OUTPUT_DIR_AGG, class_dir, metric_file)
        if os.path.exists(filepath):
            allowed_pkgs = (always_numeric_pkgs if metric_name in inf_sensitive_metrics else None)
            saved, _, classe = save_packages_with_presence(filepath, OUTPUT_DIR_AGG_GT0, class_dir, boring_packages, allowed_pkgs)

            tot_metriche_presenza += 1
            if saved == 0:
                metriche_zero.append(f"{classe}.{metric_name}")
    
    print(f"Totale metriche di presenza: {tot_metriche_presenza}")
    print(f"Metriche con 0 pacchetti salvati: {len(metriche_zero)}")
    if metriche_zero:
        print("Lista:")
        for metrica in metriche_zero:
            print(f"  - {metrica}")
    
if __name__ == "__main__":
    main()