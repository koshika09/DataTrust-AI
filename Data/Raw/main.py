import pandas as pd
import sys
from pathlib import Path


# Allow Python to import metadata.py from the project folder.
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from metadata import (
    initialize_database,
    save_pipeline_run_with_lineage
)
from validation import validate_data, format_quality_summary
from scorecard import build_scorecard_rows, write_scorecard

input_relative_path = Path("Data") / "Raw" / "Online_Retail.xlsx"
file_path = project_root / input_relative_path

df = pd.read_excel(file_path)

print("Dataset loaded successfully!")
print("Number of rows and columns:", df.shape)

print("\nFirst 5 rows:")
print(df.head())

print("\nColumn names:")
print(df.columns.tolist())


print("\n--- DATA QUALITY CHECK ---")

print("\nMissing values in each column:")
missing_values = df.isnull().sum().astype(int).to_dict()
print(pd.Series(missing_values))

print("\nTotal duplicate rows:")
duplicate_rows = int(df.duplicated().sum())
print(duplicate_rows)

print("\nDataset information:")
df.info()


print("\n--- DATA QUALITY SUMMARY ---")

total_rows = len(df)

print("Total rows:", total_rows)

print(
    "Missing CustomerID (%):",
    round(df["CustomerID"].isnull().mean() * 100, 2)
)

print(
    "Missing Description (%):",
    round(df["Description"].isnull().mean() * 100, 2)
)

print(
    "Duplicate rows (%):",
    round(df.duplicated().mean() * 100, 2)
)



print("\n--- VALIDATION RULES ---")
valid_df, quarantine_df, metrics = validate_data(df)
for rule_name, count in metrics["rule_counts"].items():
    print(f"{rule_name}: {count}")

print("\n--- QUARANTINE REPORT ---")

print("Unique rows needing review:", len(quarantine_df))

print("\nSample records needing review:")
print(
    quarantine_df[
        ["InvoiceNo", "Description", "Quantity",
         "UnitPrice", "ReviewReason"]
    ].head(10).to_string(index=False)
)

# Save the quarantine report.
quarantine_relative_path = Path("Data") / "quarantine_report.csv"
output_path = project_root / quarantine_relative_path

quarantine_df.to_csv(output_path, index=False)

print("\nQuarantine report saved to:", output_path)
print("Total quarantined rows:", len(quarantine_df))


# Save the records that passed validation.
valid_relative_path = Path("Data") / "valid_records.csv"
valid_output_path = project_root / valid_relative_path

valid_df.to_csv(valid_output_path, index=False)

print("\n--- VALIDATION OUTPUT SUMMARY ---")
print("Rows needing review:", metrics["review_rows"])
print("Rows passing current checks:", metrics["valid_rows"])
print("Total rows processed:", metrics["total_rows"])
print("Valid records saved to:", valid_output_path)



print("\n--- SAVING PIPELINE METADATA ---")

initialize_database()

run_id = save_pipeline_run_with_lineage(
    total_rows=len(df),
    valid_rows=len(valid_df),
    quarantined_rows=len(quarantine_df),
    lineage_entries=[
        (
            input_relative_path.as_posix(),
            "Data quality validation",
            valid_relative_path.as_posix()
        ),
        (
            input_relative_path.as_posix(),
            "Data quality validation",
            quarantine_relative_path.as_posix()
        ),
        (
            input_relative_path.as_posix(),
            "Data quality scorecard",
            "Data/quality_scorecard.csv"
        )
    ]
)

summary_path = project_root / "Data" / "quality_summary.txt"
scorecard_path = project_root / "Data" / "quality_scorecard.csv"
summary_path.write_text(
    format_quality_summary(
        metrics=metrics,
        run_id=run_id,
        source_name=file_path.name,
        missing_values=missing_values,
        duplicate_rows=duplicate_rows,
        output_paths=[
            ("Valid records", valid_output_path.resolve()),
            ("Quarantine report", output_path.resolve()),
            ("Quality summary", summary_path.resolve()),
            ("Quality scorecard", scorecard_path.resolve()),
        ],
    ),
    encoding="utf-8"
)

scorecard_rows = build_scorecard_rows(
    source_name=file_path.name,
    total_rows=metrics["total_rows"],
    column_count=df.shape[1],
    missing_values=missing_values,
    duplicate_rows=duplicate_rows,
    metrics=metrics,
    run_id=run_id,
    output_paths=[
        ("Valid records", valid_output_path.resolve()),
        ("Quarantine report", output_path.resolve()),
        ("Quality summary", summary_path.resolve()),
        ("Quality scorecard", scorecard_path.resolve()),
    ],
)
write_scorecard(scorecard_path, scorecard_rows)

print("Pipeline metadata and lineage saved successfully!")

