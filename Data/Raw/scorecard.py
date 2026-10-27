"""Transparent scoring and CSV formatting for existing pipeline metrics."""

import csv


def calculate_quality_score(
    total_rows, column_count, missing_value_count, duplicate_rows, valid_rows
):
    """Calculate an equal-weight completeness, uniqueness, and pass-rate score.

    An empty dataset scores zero because its rates are undefined. Values are
    percentages from 0 to 100; invalid count inputs raise ValueError.
    """
    counts = {
        "total_rows": total_rows,
        "column_count": column_count,
        "missing_value_count": missing_value_count,
        "duplicate_rows": duplicate_rows,
        "valid_rows": valid_rows,
    }
    if any(value < 0 for value in counts.values()):
        raise ValueError("Scorecard counts cannot be negative")
    if duplicate_rows > total_rows or valid_rows > total_rows:
        raise ValueError("Row counts cannot exceed total_rows")
    if missing_value_count > total_rows * column_count:
        raise ValueError("Missing-value count cannot exceed total cells")

    total_cells = total_rows * column_count
    if total_rows == 0:
        completeness = duplicate_free = validation_pass = 0.0
    else:
        completeness = (
            100.0 * (total_cells - missing_value_count) / total_cells
            if total_cells
            else 0.0
        )
        duplicate_free = 100.0 * (total_rows - duplicate_rows) / total_rows
        validation_pass = 100.0 * valid_rows / total_rows

    overall = (completeness + duplicate_free + validation_pass) / 3.0
    return {
        "completeness": completeness,
        "duplicate_free": duplicate_free,
        "validation_pass": validation_pass,
        "overall": overall,
    }


def build_scorecard_rows(
    source_name,
    total_rows,
    column_count,
    missing_values,
    duplicate_rows,
    metrics,
    run_id,
    output_paths,
):
    """Build scorecard records using existing profile and validation results."""
    missing_value_count = sum(missing_values.values())
    scores = calculate_quality_score(
        total_rows=total_rows,
        column_count=column_count,
        missing_value_count=missing_value_count,
        duplicate_rows=duplicate_rows,
        valid_rows=metrics["valid_rows"],
    )
    duplicate_rate = 100.0 * duplicate_rows / total_rows if total_rows else 0.0
    rows = []

    def add(category, metric, count="", percentage="", score="", notes=""):
        rows.append({
            "category": category,
            "metric": metric,
            "count": count,
            "percentage": round(percentage, 4) if percentage != "" else "",
            "score": round(score, 4) if score != "" else "",
            "notes": notes,
        })

    add("dataset", "Source dataset", notes=source_name)
    add("dataset", "Total rows", total_rows)
    add("dataset", "Total columns", column_count)
    add("dataset", "Total missing values", missing_value_count)
    add("dataset", "Exact duplicate rows", duplicate_rows, duplicate_rate,
        notes="Percentage is duplicate rows divided by total rows")

    for column, missing_count in missing_values.items():
        completeness = (
            100.0 * (total_rows - missing_count) / total_rows
            if total_rows
            else 0.0
        )
        add(
            "column_completeness",
            column,
            missing_count,
            completeness,
            notes="Count is missing values; percentage is non-missing rows",
        )

    for rule_name, count in metrics["rule_counts"].items():
        add(
            "validation_rule",
            rule_name,
            count,
            100.0 * count / total_rows if total_rows else 0.0,
            notes="Percentage of source rows; rule counts can overlap",
        )

    add(
        "score_component",
        "Completeness",
        missing_value_count,
        scores["completeness"],
        scores["completeness"],
        "100 * (1 - missing cells / total cells)",
    )
    add(
        "score_component",
        "Duplicate-free rate",
        duplicate_rows,
        scores["duplicate_free"],
        scores["duplicate_free"],
        "100 * (1 - exact duplicate rows / total rows)",
    )
    add(
        "score_component",
        "Current-rule pass rate",
        metrics["valid_rows"],
        scores["validation_pass"],
        scores["validation_pass"],
        "100 * rows passing current validation rules / total rows",
    )
    add(
        "overall_score",
        "Overall data quality score",
        percentage=scores["overall"],
        score=scores["overall"],
        notes="Arithmetic mean of the three equally weighted components; not an industry-standard score",
    )
    add(
        "score_limitation",
        "CustomerID missingness",
        notes="Missing CustomerID values reduce completeness even when acceptable for a particular use case.",
    )
    add(
        "score_limitation",
        "Negative quantities",
        notes="Negative quantities may represent legitimate returns; this pipeline marks them for review, which lowers the current-rule pass-rate component.",
    )
    add(
        "score_limitation",
        "Metric interpretation",
        notes="The score is a simple project-specific summary. Components may overlap, and equal weights are a transparent choice rather than a universal standard.",
    )
    add("pipeline", "Latest pipeline run ID", run_id if run_id is not None else "unavailable")
    for label, path in output_paths:
        add("output", label, notes=str(path))
    return rows


def write_scorecard(path, rows):
    """Write scorecard rows as a local UTF-8 CSV."""
    fieldnames = ["category", "metric", "count", "percentage", "score", "notes"]
    with path.open("w", encoding="utf-8", newline="") as scorecard_file:
        writer = csv.DictWriter(scorecard_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
