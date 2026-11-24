# loans_monthly

| | |
|---|---|
| **Asset type** | Table (parquet) |
| **Path** | `data/processed/loans_monthly.parquet` |
| **Certificate** | 🟡 Draft. Fit for exploration; loss columns need review before modeling |
| **Owner** | dui-mondo |
| **Source** | Freddie Mac CRT loan-level disclosure (STACR), via Clarity |
| **Built by** | `load_lld.py` |
| **Size** | 5,909,435 rows · 43 columns · 168,850 loans · 35 months |
| **Coverage** | Feb 2020 to Dec 2022 |
| **Tags** | `mortgage` `credit-risk` `high-ltv` `covid` `monthly-panel` |

## Description

Month-by-month performance of every loan in the Freddie Mac STACR deals **2019-HQA1** and **2019-HQA2**. These are high-LTV loans (81-97%) made around 2018-2019, which all carry private mortgage insurance. The table answers: *how was each loan doing each month through COVID, and if it ended badly, how much was lost?*

## Grain

**One row = one loan in one reporting month.** The primary key is (`loan_id`, `period`).

Every loan appears in **all 35 months**, including after it has paid off or been sold. Once a loan exits, its later rows repeat the exit information. Filter with `zero_bal_code.isna()` to keep only active loans.

## Lineage

```
Clarity download (zip, open with 7-Zip)
  -> data/raw/<deal>_<YYYYMMDD>_lld.txt   70 files, pipe-delimited, no header, latin-1
  -> load_lld.py                           names columns by position, keeps 41 of 88-93,
                                           sentinel codes -> null, parses dates, adds calc_loss
  -> data/processed/loans_monthly.parquet
```

## Column groups

| Group | What it holds | Changes month to month? |
|---|---|---|
| Identity | Which loan, which month, which deal | Key |
| Origination | The loan as it was made | No (static) |
| Performance | Payments, balance, refreshed risk | Yes |
| Relief | Forbearance, deferrals, modifications | Yes |
| Exit & loss | How the loan ended and what it cost | Filled once the loan exits |

## Columns

### Identity

| Column | Type | Description | Values | % null |
|---|---|---|---|---|
| `period` | date | Reporting month (1st of month) | 2020-02-01 .. 2022-12-01 | 0 |
| `pool` | category | CRT deal the loan belongs to | `19HQA1`, `19HQA2` | 0 |
| `loan_id` | string | Unique loan identifier. Prefix is the deal | e.g. `19HQA1000002` | 0 |
| `source_file` | category | Raw file this row was read from (lineage) | 70 files | 0 |

### Origination (static)

| Column | Type | Description | Values | % null |
|---|---|---|---|---|
| `state` | category | Property state | 53 (incl. DC, PR, territories) | 0 |
| `orig_rate` | float | Interest rate at origination, % | 3.25 .. 6.75 | 0 |
| `orig_upb` | float | Original loan balance, $ ("UPB" = unpaid principal balance) | 19,000 .. 864,000 | 0 |
| `orig_term` | float | Loan length in months | 252 .. 480 (mostly 360) | 0 |
| `first_pay_dt` | date | First payment due date | 2015-04 .. 2018-11 | 0 |
| `loan_purpose` | category | Why the loan was taken | `P` purchase, `N` no-cash-out refi, `C` cash-out refi | 0 |
| `channel` | category | Who sold the loan to the borrower | `R` retail, `C` correspondent, `B` broker | 0 |
| `prop_type` | category | Property type | `SF` single family, `PU` planned development, `CO` condo, `MH` manufactured, `CP` co-op | 0 |
| `units` | float | Number of units in the property | 1 .. 4 | 0 |
| `occupancy` | category | How the owner uses the home | `P` primary, `S` second home, `I` investment | 0 |
| `num_borrowers` | float | Number of borrowers on the loan | 1 .. 5 | 0 |
| `first_time_buyer` | category | First-time homebuyer | `Y`, `N` | 0 |
| `fico` | float | Credit score at origination (higher = safer) | 605 .. 832 | 0 |
| `oltv` | float | Original loan-to-value: loan as % of home value | 81 .. 97 | 0 |
| `ocltv` | float | Combined LTV, including any second loans | 81 .. 103 | 0 |
| `dti` | float | Debt-to-income: monthly debt payments as % of income | 2 .. 50 | 0 |
| `mi_pct` | float | Mortgage insurance coverage, % of the loan the insurer pays on a claim | 0 .. 38 | 0 |

### Performance (monthly)

| Column | Type | Description | Values | % null |
|---|---|---|---|---|
| `loan_age` | float | Months since first payment | 0 .. 91 | 0 |
| `dlq_status` | string | Months behind on payments | `00` current, `01` 30-59 days, `02` 60-89, `03`+ = 90+ days (number = months late), `RA` foreclosed home (REO), `XX` not applicable | 0 |
| `curr_upb` | float | Current unpaid balance, $ | 0 .. 803,422 | 0 |
| `eltv` | float | Estimated current LTV, from Freddie's home-value model | 0 .. 583 | 5.8 |
| `upd_fico1` | float | Refreshed credit score (updated quarterly) | 394 .. 844 | 0.4 |

### Relief (COVID-era)

| Column | Type | Description | Values | % null |
|---|---|---|---|---|
| `borrower_assist` | category | Active help plan this month. Null = none | `F` forbearance, `R` repayment plan, `T` trial modification | 97.4 |
| `pay_deferral` | category | Missed payments moved to the end of the loan | `C` this month, `P` in a prior month | 97.7 |
| `mod_flag` | category | Loan terms have been permanently changed | `Y` this month, `P` previously | 99.6 |
| `dlq_disaster` | category | Lateness is due to a declared disaster (incl. COVID) | `Y` | 98.3 |

### Exit & loss

Most of these are null unless the loan ended with a loss (about 100% null overall).

| Column | Type | Description | Values | % null |
|---|---|---|---|---|
| `zero_bal_code` | category | How the loan left the pool. Null = still active | `01` paid off, `03` short sale, `09` foreclosed home sold, `96` repurchased for defect, `98` other | 42.1 |
| `zero_bal_dt` | date | Month the loan exited | 2019-01 .. 2022-12 | 42.1 |
| `upb_removal` | float | Balance outstanding when the loan exited, $ | 0 .. 856,713 | 0 |
| `net_sales_proceeds` | float | Money from selling the home, after selling costs | 0 .. 451,000 | ~100 |
| `mi_credit` | float | Mortgage insurance payout | 0 .. 131,649 | ~100 |
| `misc_credits` | float | Other money recovered | 0 .. 68,900 | ~100 |
| `dlq_accrued_int` | float | Interest owed but unpaid while delinquent | 1,300 .. 66,954 | ~100 |
| `taxes_ins` | float | Property taxes and insurance advanced | -139 .. 38,719 | ~100 |
| `legal_costs` | float | Foreclosure legal costs | -113 .. 20,819 | ~100 |
| `maint_costs` | float | Upkeep of the foreclosed home | 0 .. 41,928 | ~100 |
| `misc_exp` | float | Other expenses | -3,687 .. 21,846 | ~100 |
| `actual_loss` | float | Freddie's published loss. **Empty for all 2020-2022 rows** | none | 100 |
| `calc_loss` | float | **Derived.** Approximate loss for credit exits (`02/03/09/15`): balance + interest + costs - sale proceeds - MI payout - other credits | -68,634 .. 241,097 | ~100 |

## Usage

```python
df = pd.read_parquet("data/processed/loans_monthly.parquet")

active = df[df.zero_bal_code.isna()]                       # loans still alive that month
late90 = ~df.dlq_status.isin(["00", "01", "02", "XX"])     # 90+ days late (incl. RA)
losses = (df[df.calc_loss.notna()]
          .sort_values("period").drop_duplicates("loan_id")) # one row per loss
```

Explore it in `notebooks/01_explore_data.ipynb`.

## Known issues

| Issue | Impact | Workaround |
|---|---|---|
| Exited loans repeat in every later month | Loss totals inflate about 20x (106 loans -> 2,112 rows) | Keep the first exit row per loan |
| 30,624 loans already paid off in Feb 2020 | Count as false "never defaulted" | Drop rows with non-null `zero_bal_code` at baseline |
| 1,656 loans already late in Feb 2020 | Not COVID defaults | Exclude or flag |
| Forbearance shows up as 90+ days late | Raw default rate 5.7% vs 0.66% adjusted (first 12 months) | Use the COVID-adjusted definition in `CLAUDE.md` |
| 7 of 106 credit exits happened before Feb 2020 | Pre-COVID losses mixed in | Filter on `zero_bal_dt >= 2020-02-01` |
| 15 credit exits have negative `calc_loss` | Recoveries exceeded what was owed, or formula gap | Review before loss-size modeling |
| `calc_loss` is approximate | May not match Freddie's official loss | State this openly; `actual_loss` publishes from July 2026 |
| `eltv` max 583 | Outlier home values | Cap or check before using as a feature |
| Only 106 loans with a credit loss | Too few for a strong loss-size model | Use a simple severity estimate; say so |
