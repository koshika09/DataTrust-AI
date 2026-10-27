# DataTrust AI

DataTrust AI is a local pandas pipeline for profiling and reviewing the Online Retail dataset. It writes valid and review CSV files, a text quality summary, and SQLite run and lineage metadata. It does not use a cloud service or paid API.

## Setup

Use Python 3 and the project virtual environment. The pipeline uses `pandas` and an Excel reader supported by pandas (the current environment uses `openpyxl`); SQLite and the remaining utilities are part of Python's standard library. If the environment needs these packages, install them into the virtual environment:

```powershell
& .\.venv\Scripts\python.exe -m pip install pandas openpyxl
```

No dependency manifest is currently included.

## Run

From the project directory in PowerShell:

```powershell
& .\.venv\Scripts\python.exe Data\Raw\main.py
```

The script resolves project paths from its own location, so it can also be started from another working directory using the full path to the script. Each run overwrites the CSV outputs and summary with the latest results, then adds a new run and lineage records to the existing database.

## Architecture and flow

- `Data/Raw/main.py` reads `Data/Raw/Online_Retail.xlsx`, prints profiling information, writes output CSVs, saves the run and lineage through `metadata.py`, and writes `Data/quality_summary.txt`.
- `Data/Raw/validation.py` contains the shared validation rules, partitions records into valid and review groups, reconciles row counts, and formats the summary from those results.
- `metadata.py` stores pipeline run counts in `pipeline_runs` and source-to-output records in `pipeline_lineage` in `Data/datatrust.db`. The pipeline inserts the run and its lineage in one transaction.

## Validation rules

Rows are sent to review when they have a missing description, missing or nonnumeric quantity or unit price, a nonnumeric or invalid invoice date, a zero quantity, a negative quantity, or a zero/negative unit price. Negative quantities are described as possible retail returns requiring review; they are not automatically considered invalid. Rule counts can overlap because a row may violate more than one rule.

Missing values by column and exact duplicate rows are profiled in the summary. Missing `CustomerID` values and duplicate rows are not currently validation rules and do not, by themselves, send a row to review.

## Outputs and metadata

- `Data/valid_records.csv` — records passing the current rules.
- `Data/quarantine_report.csv` — records requiring review, with rule flags and reasons.
- `Data/quality_summary.txt` — source row count, missing values, duplicates, rule counts and percentages, output counts, latest run ID, and output locations.
- `Data/quality_scorecard.csv` — local scorecard with column completeness, duplicate rate, validation-rule counts, and the overall score components.
- `Data/datatrust.db` — run history and lineage linking each pipeline run to the valid CSV, review CSV, and scorecard.

The overall score is the equal-weight arithmetic mean of three percentages: cell completeness (`100 * (1 - missing cells / total cells)`), duplicate-free rate (`100 * (1 - exact duplicate rows / total rows)`), and current-rule pass rate (`100 * valid rows / total rows`). It is a project-specific summary, not an industry-standard score. Its limits are recorded in the CSV: missing `CustomerID` values may be acceptable for some use cases, negative quantities may be valid returns but are currently sent for review, and the components may overlap.

## Tests

Run the synthetic-data unit tests from the project directory:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests do not load the full Excel workbook.

## Latest verified results

The most recent full-data run recorded **Run ID 21** and processed **541,909 rows**: **530,104 valid** and **11,805 requiring review**. Its overall score was **97.9/100** under the project-specific formula above. The source workbook has 8 columns. All ten validation and scorecard tests passed during the last verification. The summary and scorecard reports contain the profile and rule results for the latest run.

## Limitations

This is a local command-line project. It has no dashboard, cloud integration, PySpark, or GenAI feature. The current rules are basic and should be reviewed for each use case. Each run replaces the CSV and text report outputs, although SQLite run history is retained.
