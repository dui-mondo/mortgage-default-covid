# Mortgage Default Under COVID Stress (ongoing project)

> 🚧 **Work in progress.** The default analysis is done. Loss modeling and out-of-time validation are next (see [Roadmap](#roadmap)).

Which pre-COVID mortgages went bad once COVID hit, and how much was lost? This project uses Freddie Mac's loan-level Credit Risk Transfer data to model **probability of default under economic stress**, the first building block of the expected-loss estimate mortgage insurers price on:

```
Expected loss = Probability of default × Loss given default × Exposure
```

**Slides:** [methodology deck](https://claude.ai/artifact/4Sx9CWwsvKyNrYrQciZuTn) (13 slides, plain-language walkthrough with speaker notes).

## In plain English

- **The loans:** about 169,000 mortgages where the buyer put down less than 20%, the kind that needs mortgage insurance.
- **The question:** when COVID hit, who stopped paying, and could a lender have seen it coming on the day the loan was made?
- **The twist:** in 2020 many borrowers got an approved payment pause (forbearance), but the data still marks them as late. Counting them as defaults would be wrong, so a default here means 3+ months behind *without* an approved pause. That cuts 7,810 "defaults" down to 902.
- **The answer so far:** a household's income cushion (a second borrower, less debt compared to income, a smaller loan) predicted COVID defaults about as well as credit score did. House prices didn't matter much, because they rose almost everywhere.

## Data

Freddie Mac **STACR** reference pools, downloaded from [Clarity](https://claritydownload.fmapps.freddiemac.com/CRT) (account required; monthly loan-level files ending in `_lld.txt`).

| Filter | Choice | Why |
|---|---|---|
| Period | Feb 2020 to Dec 2022 | Feb 2020 is the pre-COVID baseline; most losses land in 2022 after moratoriums ended |
| Deals | 2019-HQA1, 2019-HQA2 | Loans originated 2018-19, active when COVID hit |
| Segment | High LTV (81-97%) | The loans that require private mortgage insurance |
| Offering | STACR only | ACIS covers overlapping pools and would duplicate loans |

Result: **5,909,750 loan-month rows, 168,850 loans, 35 months.** Completeness check: every monthly file lists every loan in its deal (86,883 for HQA1, 81,967 for HQA2). This caught one truncated download (315 loans missing), which was replaced.

Also used: the [FHFA House Price Index](https://www.fhfa.gov/data/hpi) by 3-digit ZIP, plus a ZIP3-to-state map (both in `data/`).

## Method

**1. Data preparation (manual, one-time).** This is not an automated pipeline. The monthly files are downloaded by hand from Freddie Mac Clarity (one zip per deal per period) and unzipped with 7-Zip into `data/raw/`. The Python script [`load_lld.py`](load_lld.py) is then run once to combine all 70 monthly files into a single table: it names the columns (the files have no header), turns 999/9999 placeholder codes into missing values, removes duplicate rows, and estimates the loss on loans that ended badly. The notebook reads that combined table. Column reference: [`docs/loans_monthly.md`](docs/loans_monthly.md).

**2. Cohort.** Loans that were active and current in Feb 2020, watched for 12 months (Mar 2020 to Feb 2021). Paid-off loans are dropped so they don't count as false "never defaulted".

**3. COVID-adjusted default.** During 2020-21, borrowers in approved forbearance show up as delinquent. Default here = **90+ days late while not in forbearance**. Plain "90+ days late" flags 7,810 loans; the adjusted definition flags 902.

| Outcome | Loans | Share |
|---|---:|---:|
| Paid normally | 124,660 | 91.4% |
| COVID relief (forbearance) | 10,864 | 8.0% |
| Defaulted | 902 | 0.66% |

**4. Origination-only features.** Models use only what is known when the loan is priced. The refreshed credit score and current LTV are left out: they're measured after origination, and an insurer prices at origination.

**5. Three lenses.**
- **Significance tests:** Mann-Whitney (numeric) and chi-square (categorical), Bonferroni-corrected, with effect sizes.
- **Permutation importance:** gradient-boosted trees trained on HQA1, tested on HQA2, scored on PR-AUC because defaults are rare.
- **Logistic regression:** one model with all features, odds ratios per 1 standard deviation.

## Findings so far

- **Income resilience is the strongest signal.** Two borrowers vs one: **OR 1.89**. Higher debt-to-income (**OR 0.77** per ~8 points) and larger loans (**OR 0.77** per ~$108k) lower the odds of paying.
- **Origination credit score is close behind:** **OR 1.77 per ~41 points**, and the top feature in the tree model.
- **Rate carries extra risk.** At the same credit score, a higher original rate leans toward default (**OR 0.86** per 0.3 points).
- **Equity didn't matter in this period.** LTV, loan age, channel, property type, occupancy and purpose were not significant.
- **House prices don't explain state differences.** State price change vs relief and default rates: Spearman rho -0.15 to 0.23, none significant (44 states). Prices rose +19% to +60% from 2019 Q4 to 2022 Q4, so nearly everyone kept equity.

## Limitations

- **Modest predictive power.** The tree model's held-out PR-AUC is 0.016 vs 0.007 for random guessing (about 2.3×), ROC-AUC 0.66. The regression's AUC of 0.72 is measured on its own training data.
- **Sparse losses.** Freddie Mac's actual-loss field is empty for 2020-22, so loss is estimated from cost fields.
- **One stress event.** COVID was an income shock with heavy government relief; a price crash may behave differently.
- **State-level house prices are unweighted** by loan count.

## Roadmap

- [ ] Add state unemployment (BLS) to test the job-loss explanation
- [ ] Out-of-time validation: test on a later period the model never saw (train-on-HQA1 / test-on-HQA2 is already done in the tree model)
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
load_lld.py                       one-time script: combines the downloaded monthly files into one table
notebooks/01_explore_data.ipynb   exploration, tests and models
docs/loans_monthly.md             column reference for the processed table
data/                             house price index and ZIP3 -> state map
```
