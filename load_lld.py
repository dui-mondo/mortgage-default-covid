"""
Load Freddie Mac STACR monthly loan-level files (*_lld.txt) into one Parquet file.

Usage:
    python load_lld.py                      # reads data/raw, writes data/processed
    python load_lld.py path/to/raw out.parquet

Files have no header, are pipe-delimited, and one file = one deal x one month
(e.g. 19HQA1_20200201_lld.txt). Older files have 88 columns, newer ones up to 93;
names are assigned by position, so missing trailing columns just become NaN.
"""
import sys
from pathlib import Path

import pandas as pd

# All 93 positions from Freddie Mac's "CRT Reference Pool Disclosure File Layouts"
ALL_COLS = [
    "period", "pool", "loan_id", "amort_type", "seller", "state", "zip3", "msa",
    "first_pay_dt", "maturity_dt", "orig_term", "orig_rate", "orig_upb", "upb_issuance",
    "loan_purpose", "channel", "prop_type", "units", "occupancy", "num_borrowers",
    "first_time_buyer", "prepay_penalty", "fico", "oltv", "ocltv", "dti", "mi_pct",
    "upd_fico_issuance", "special_elig", "mi_type", "filler1", "disaster_grace",
    "servicer", "loan_age", "rem_months_legal", "adj_rmm", "dlq_status", "pay_history",
    "curr_rate", "curr_upb", "curr_ib_upb", "upb_removal", "zero_bal_code", "zero_bal_dt",
    "defect_settle_dt", "mod_flag", "dlq_disaster", "ddlpi", "bankruptcy_flag",
    "fcl_referral_dt", "net_sales_proceeds", "mi_credit", "taxes_ins", "legal_costs",
    "maint_costs", "cramdown_costs", "misc_exp", "misc_credits", "mi_cancel", "eltv",
    "filler2", "upd_fico1", "upd_fico2", "num_mods", "mod_program", "mod_type",
    "mod_first_pay_dt", "mod_dti", "cap_amount", "step_ind",
    "step1_dt", "step1_rate", "step2_dt", "step2_rate", "step3_dt", "step3_rate",
    "step4_dt", "step4_rate", "step5_dt", "step5_rate", "dlq_accrued_int",
    "curr_mod_cost", "upd_fico3", "valuation_method", "group_num", "relief_refi_ind",
    "borrower_assist", "pay_deferral", "distressed_flag", "buydown_type",
    "vantage4", "actual_loss", "cum_mod_cost",
]

# Columns kept for modeling (edit freely)
KEEP = [
    # keys
    "period", "pool", "loan_id",
    # origination features (fixed per loan)
    "state", "orig_rate", "orig_upb", "orig_term", "loan_purpose", "channel",
    "prop_type", "units", "occupancy", "num_borrowers", "first_time_buyer",
    "fico", "oltv", "ocltv", "dti", "mi_pct", "first_pay_dt",
    # monthly performance
    "loan_age", "dlq_status", "curr_upb", "eltv", "upd_fico1",
    "borrower_assist", "pay_deferral", "mod_flag", "dlq_disaster",
    # exit / loss
    "zero_bal_code", "zero_bal_dt", "upb_removal", "net_sales_proceeds",
    "mi_credit", "taxes_ins", "legal_costs", "maint_costs", "misc_exp",
    "misc_credits", "dlq_accrued_int", "actual_loss",
]

NUMERIC = [
    "orig_rate", "orig_upb", "orig_term", "units", "num_borrowers", "fico", "oltv",
    "ocltv", "dti", "mi_pct", "loan_age", "curr_upb", "eltv", "upd_fico1",
    "upb_removal", "net_sales_proceeds", "mi_credit", "taxes_ins", "legal_costs",
    "maint_costs", "misc_exp", "misc_credits", "dlq_accrued_int", "actual_loss",
]
DATES = ["period", "first_pay_dt", "zero_bal_dt"]
CATEGORICAL = [
    "pool", "state", "loan_purpose", "channel", "prop_type", "occupancy",
    "first_time_buyer", "borrower_assist", "pay_deferral", "mod_flag",
    "dlq_disaster", "zero_bal_code",
]

# Sentinel codes meaning "not available"
MISSING_CODES = {
    "fico": [9999], "upd_fico1": [9999], "dti": [999], "oltv": [999],
    "ocltv": [999], "mi_pct": [999], "eltv": [999],
}


def read_one(path: Path) -> pd.DataFrame:
    with open(path, encoding="latin-1") as fh:
        n_cols = fh.readline().rstrip("\r\n").count("|") + 1
    names = ALL_COLS[:n_cols]
    df = pd.read_csv(
        path, sep="|", header=None, names=names,
        usecols=[c for c in KEEP if c in names],
        dtype=str, keep_default_na=False, na_values=[""], encoding="latin-1",
    )
    for c in KEEP:  # columns this file version doesn't have yet
        if c not in df:
            df[c] = pd.NA
    df = df[KEEP]
    for c in NUMERIC:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c, codes in MISSING_CODES.items():
        df[c] = df[c].mask(df[c].isin(codes))
    for c in DATES:
        df[c] = pd.to_datetime(df[c], format="%Y%m", errors="coerce")
    df["source_file"] = path.name
    return df


def load_all(raw_dir: Path) -> pd.DataFrame:
    files = sorted(raw_dir.rglob("*_lld.txt"))
    if not files:
        raise FileNotFoundError(f"No *_lld.txt files under {raw_dir}")
    frames = []
    for i, f in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {f.name}")
        frames.append(read_one(f))
    df = pd.concat(frames, ignore_index=True)
    for c in CATEGORICAL + ["source_file"]:
        df[c] = df[c].astype("category")

    # Loss for loans that left the pool via a credit event (02, 03, 09, 15).
    # Freddie only publishes "actual_loss" from July 2026 reports, so older
    # files need it rebuilt from the components (approximate).
    credit_exit = df["zero_bal_code"].isin(["02", "03", "09", "15"])
    costs = df[["dlq_accrued_int", "taxes_ins", "legal_costs", "maint_costs", "misc_exp"]].fillna(0).sum(axis=1)
    recoveries = df[["net_sales_proceeds", "mi_credit", "misc_credits"]].fillna(0).sum(axis=1)
    df["calc_loss"] = (df["upb_removal"].fillna(0) + costs - recoveries).where(credit_exit)

    # Same loan + month should appear once; drop accidental duplicate downloads
    df = df.drop_duplicates(["loan_id", "period"])
    return df.sort_values(["loan_id", "period"]).reset_index(drop=True)


if __name__ == "__main__":
    raw = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/processed/loans_monthly.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)

    df = load_all(raw)
    df.to_parquet(out, index=False)
    print(f"Saved {len(df):,} rows, {df['loan_id'].nunique():,} loans, "
          f"{df['period'].nunique()} months -> {out}")
