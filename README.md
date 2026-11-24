# Mortgage Default Under COVID Stress (ongoing project)

> 🚧 **Work in progress.** The default analysis is done. Loss modeling and out-of-time validation are next (see [Roadmap](#roadmap)).

Which pre-COVID mortgages went bad once COVID hit, and how much was lost? This project uses Freddie Mac's loan-level Credit Risk Transfer data to model **probability of default under economic stress**, the first building block of the expected-loss estimate mortgage insurers price on:

```
Expected loss = Probability of default × Loss given default × Exposure
```

## Data

Freddie Mac **STACR** reference pools, downloaded from [Clarity](https://capitalmarkets.freddiemac.com/crt/resources/clarity-glossary) (account required).

| Filter | Choice | Why |
|---|---|---|
| Period | Feb 2020 to Dec 2022 | Feb 2020 is the pre-COVID baseline; most losses land in 2022 after moratoriums ended |
| Deals | 2019-HQA1, 2019-HQA2 | Loans originated 2018-19, active when COVID hit |
| Segment | High LTV (81-97%) | The loans that require private mortgage insurance |
| Offering | STACR only | ACIS covers overlapping pools and would duplicate loans |

Result: **5.9M loan-month rows, 168,850 loans, 35 months.**

Also used: the [FHFA House Price Index](https://www.fhfa.gov/data/hpi) by 3-digit ZIP, plus a ZIP3-to-state map (both in `data/`).

## Method

**1. Pipeline.** [`load_lld.py`](load_lld.py) reads the raw monthly files (pipe-delimited, no header, 88-93 columns), names columns by position, turns 999/9999 codes into missing values, removes duplicates, estimates the loss on loans that ended badly, and writes one parquet table. Column reference: [`docs/loans_monthly.md`](docs/loans_monthly.md).

**2. Cohort.** Loans that were active and current in Feb 2020, watched for 12 months (Mar 2020 to Feb 2021). Paid-off loans are dropped so they don't count as false "never defaulted".

**3. COVID-adjusted default.** During 2020-21, borrowers in approved forbearance show up as delinquent. Default here = **90+ days late while not in forbearance**. Plain "90+ days late" flags 7,810 loans; the adjusted definition flags 902.

| Outcome | Loans | Share |
|---|---:|---:|
| Paid normally | 124,660 | 91.4% |
| COVID relief (forbearance) | 10,864 | 8.0% |
| Defaulted | 902 | 0.66% |

**4. Three lenses.**
- **Significance tests:** Mann-Whitney (numeric) and chi-square (categorical), Bonferroni-corrected, with effect sizes.
- **Permutation importance:** gradient-boosted trees, scored on PR-AUC because defaults are rare.
- **Logistic regression:** one model with all features, odds ratios per 1 standard deviation.

## Findings so far

- **Refreshed credit score is the strongest signal.** The Feb 2020 score (not the one at origination) has odds ratio **1.88 per ~61 points**. Median 681 for defaulters vs 756 for steady payers.
- **Income buffers matter.** Two borrowers vs one: **OR 1.81**. Higher debt-to-income (**0.82**) and larger loans (**0.78**) lower the odds of paying.
- **Equity didn't matter in this period.** LTV, current LTV, loan age, channel, property type, occupancy and purpose were not significant.
- **House prices don't explain state differences.** State price change vs relief and default rates: Spearman rho -0.15 to 0.23, none significant (44 states). Prices rose +19% to +60% from 2019 Q4 to 2022 Q4, so nearly everyone kept equity.

## Limitations

- **Modest predictive power.** The tree model's held-out PR-AUC is 0.022 vs 0.007 for random guessing (about 3×). The regression's AUC of 0.77 is measured on its own training data.
- **Sparse losses.** Freddie Mac's actual-loss field is empty for 2020-22, so loss is estimated from cost fields.
- **One stress event.** COVID was an income shock with heavy government relief; a price crash may behave differently.
- **State-level house prices are unweighted** by loan count.

## Roadmap

- [ ] Add state unemployment (BLS) to test the job-loss explanation
- [ ] Out-of-time validation: train on HQA1, test on HQA2
- [ ] Loss-given-default model, then expected loss per loan

## Run it

```bash
# 1. Put the unzipped *_lld.txt files in data/raw/ (use 7-Zip: Windows' extractor shows them as empty)
pip install -r requirements.txt
python load_lld.py data/raw data/processed/loans_monthly.parquet

# 2. Open notebooks/01_explore_data.ipynb and run all cells
```

Raw and processed loan data are not included in this repo. Download them from Freddie Mac Clarity.

## Repo layout

```
load_lld.py                       raw monthly files -> one parquet table
notebooks/01_explore_data.ipynb   exploration, tests and models
docs/loans_monthly.md             column reference for the processed table
data/                             house price index and ZIP3 -> state map
```
