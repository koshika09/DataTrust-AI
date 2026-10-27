"""Data quality checks for the Online Retail pipeline."""

import pandas as pd


def validate_data(dataframe):
    """Return valid rows, rows needing review, and rule counts.

    The source DataFrame is not modified. Negative quantities are review items
    because they may represent legitimate retail returns.
    """
    required_columns = {"Description", "Quantity", "UnitPrice", "InvoiceDate"}
    missing_columns = required_columns.difference(dataframe.columns)
    if missing_columns:
        raise ValueError(
            "Missing required columns: " + ", ".join(sorted(missing_columns))
        )

    quality_df = dataframe.copy()
    numeric_quantity = pd.to_numeric(quality_df["Quantity"], errors="coerce")
    numeric_price = pd.to_numeric(quality_df["UnitPrice"], errors="coerce")

    quality_df["MissingDescription"] = quality_df["Description"].isna()
    quality_df["MissingQuantity"] = quality_df["Quantity"].isna()
    quality_df["MissingUnitPrice"] = quality_df["UnitPrice"].isna()
    quality_df["InvalidQuantityType"] = (
        quality_df["Quantity"].notna() & numeric_quantity.isna()
    )
    quality_df["InvalidPriceType"] = (
        quality_df["UnitPrice"].notna() & numeric_price.isna()
    )
    quality_df["NegativeQuantityNeedsReview"] = numeric_quantity.lt(0).fillna(False)
    quality_df["ZeroQuantityNeedsReview"] = numeric_quantity.eq(0).fillna(False)
    quality_df["QuantityNeedsReview"] = (
        quality_df["NegativeQuantityNeedsReview"]
        | quality_df["ZeroQuantityNeedsReview"]
    )
    quality_df["UnitPriceNeedsReview"] = numeric_price.le(0).fillna(False)
    quality_df["InvalidInvoiceDate"] = pd.to_datetime(
        quality_df["InvoiceDate"], errors="coerce"
    ).isna()

    reasons = pd.Series("", index=quality_df.index, dtype="object")

    def add_reason(mask, reason):
        reasons.loc[mask] += reason

    add_reason(quality_df["MissingDescription"], "Missing description; ")
    add_reason(quality_df["MissingQuantity"], "Missing quantity; ")
    add_reason(quality_df["MissingUnitPrice"], "Missing unit price; ")
    add_reason(
        quality_df["NegativeQuantityNeedsReview"],
        "Negative quantity (possible retail return; review); ",
    )
    add_reason(quality_df["ZeroQuantityNeedsReview"], "Zero quantity; ")
    add_reason(quality_df["UnitPriceNeedsReview"], "Zero or negative unit price; ")
    add_reason(quality_df["InvalidInvoiceDate"], "Invalid invoice date; ")
    add_reason(quality_df["InvalidQuantityType"], "Invalid quantity type; ")
    add_reason(quality_df["InvalidPriceType"], "Invalid price type; ")
    quality_df["ReviewReason"] = reasons

    review_mask = quality_df["ReviewReason"].ne("")
    valid_mask = ~review_mask
    total_rows = len(dataframe)
    valid_rows = int(valid_mask.sum())
    review_rows = int(review_mask.sum())

    if (valid_mask & review_mask).any():
        raise AssertionError("Valid and review output rows overlap")
    if total_rows != valid_rows + review_rows:
        raise AssertionError(
            "Row accounting failed: total_rows must equal valid_rows + review_rows"
        )

    valid_df = quality_df.loc[valid_mask].copy()
    review_df = quality_df.loc[review_mask].copy()
    metrics = {
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "review_rows": review_rows,
        "rule_counts": {
            column: int(quality_df[column].sum())
            for column in (
                "MissingDescription",
                "MissingQuantity",
                "MissingUnitPrice",
                "NegativeQuantityNeedsReview",
                "ZeroQuantityNeedsReview",
                "UnitPriceNeedsReview",
                "InvalidInvoiceDate",
                "InvalidQuantityType",
                "InvalidPriceType",
            )
        },
    }
    return valid_df, review_df, metrics


def format_quality_summary(
    metrics, run_id, source_name, missing_values, duplicate_rows, output_paths
):
    """Format a concise report from the existing pipeline results."""
    total_rows = metrics["total_rows"]
    lines = [
        "DataTrust AI - Data Quality Summary",
        f"Source dataset: {source_name}",
        f"Total rows: {total_rows}",
        f"Total missing values: {sum(missing_values.values())}",
        f"Duplicate rows: {duplicate_rows}",
        "Missing values by column:",
    ]
    lines.extend(
        f"  {column}: {count}"
        for column, count in missing_values.items()
    )
    lines.extend([
        "",
        "Validation rule counts (% of source rows; rules may overlap):",
    ])
    lines.extend(
        f"{name}: {count} ({count / total_rows * 100:.2f}%)"
        if total_rows
        else f"{name}: {count} (0.00%)"
        for name, count in metrics["rule_counts"].items()
    )
    lines.extend([
        "",
        f"Valid rows: {metrics['valid_rows']}",
        f"Rows needing review: {metrics['review_rows']}",
        "",
        f"Latest pipeline run ID: {run_id if run_id is not None else 'unavailable'}",
        "Output files:",
    ])
    lines.extend(f"  {label}: {path}" for label, path in output_paths)
    return "\n".join(lines) + "\n"
