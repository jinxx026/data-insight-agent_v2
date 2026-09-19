from __future__ import annotations

import pandas as pd
from pandas.api.types import is_numeric_dtype


QUALITY_COLUMNS = [
    "severity",
    "issue_type",
    "scope",
    "column",
    "metric",
    "details",
    "recommendation",
]


def analyze_data_quality(df: pd.DataFrame, profile_df: pd.DataFrame) -> pd.DataFrame:
    """Detect common data quality issues using dataframe statistics and smart field types."""
    issues: list[dict[str, str]] = []

    issues.extend(_detect_duplicate_rows(df))
    issues.extend(_detect_missing_values(profile_df))
    issues.extend(_detect_empty_or_constant_fields(profile_df))
    issues.extend(_detect_identifier_fields(profile_df))
    issues.extend(_detect_high_cardinality_fields(profile_df))
    issues.extend(_detect_numeric_outliers(df, profile_df))
    issues.extend(_detect_target_imbalance(df, profile_df))

    if not issues:
        return pd.DataFrame(columns=QUALITY_COLUMNS)

    return pd.DataFrame(issues, columns=QUALITY_COLUMNS).sort_values(
        by=["severity", "issue_type", "column"],
        key=lambda column: column.map(_severity_sort_key) if column.name == "severity" else column,
    )


def build_quality_summary(df: pd.DataFrame, quality_df: pd.DataFrame) -> dict[str, int]:
    """Return top-level quality metrics for Streamlit metric cards."""
    return {
        "quality_issues": int(len(quality_df)),
        "high_severity": int((quality_df["severity"] == "high").sum()) if not quality_df.empty else 0,
        "columns_with_missing": int(df.isna().any().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
    }


def summarize_issue_types(quality_df: pd.DataFrame) -> pd.DataFrame:
    if quality_df.empty:
        return pd.DataFrame(columns=["issue_type", "count"])

    return (
        quality_df.groupby("issue_type", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["count", "issue_type"], ascending=[False, True])
    )


def _detect_duplicate_rows(df: pd.DataFrame) -> list[dict[str, str]]:
    duplicate_count = int(df.duplicated().sum())
    if duplicate_count == 0:
        return []

    duplicate_rate = duplicate_count / max(len(df), 1)
    severity = "high" if duplicate_rate >= 0.1 else "medium"

    return [
        _issue(
            severity=severity,
            issue_type="duplicate_rows",
            scope="dataset",
            column="",
            metric=f"{duplicate_count} rows ({duplicate_rate:.1%})",
            details="Duplicate rows can bias aggregate statistics and model training.",
            recommendation="Review whether duplicated records are valid repeat events or accidental duplicates.",
        )
    ]


def _detect_missing_values(profile_df: pd.DataFrame) -> list[dict[str, str]]:
    issues = []
    missing_profiles = profile_df.loc[profile_df["missing_count"] > 0]

    for row in missing_profiles.to_dict("records"):
        missing_rate = float(row["missing_rate"])
        severity = "high" if missing_rate >= 0.3 else "medium" if missing_rate >= 0.1 else "low"
        issues.append(
            _issue(
                severity=severity,
                issue_type="missing_values",
                scope="column",
                column=row["column"],
                metric=f"{int(row['missing_count'])} missing ({missing_rate:.1%})",
                details="Missing values can distort summaries, charts, and model features.",
                recommendation=_missing_value_recommendation(row["smart_type"]),
            )
        )

    return issues


def _detect_empty_or_constant_fields(profile_df: pd.DataFrame) -> list[dict[str, str]]:
    issues = []

    for row in profile_df.to_dict("records"):
        if row["smart_type"] == "empty_field":
            issues.append(
                _issue(
                    severity="high",
                    issue_type="empty_field",
                    scope="column",
                    column=row["column"],
                    metric="100.0% missing",
                    details="The field contains no usable values.",
                    recommendation="Exclude this field or fix the upstream data collection process.",
                )
            )
        elif int(row["unique_count"]) <= 1:
            issues.append(
                _issue(
                    severity="medium",
                    issue_type="constant_field",
                    scope="column",
                    column=row["column"],
                    metric=f"{int(row['unique_count'])} unique value",
                    details="A constant field has no variation and contributes little to analysis or modeling.",
                    recommendation="Exclude this field unless the constant value has operational meaning.",
                )
            )

    return issues


def _detect_identifier_fields(profile_df: pd.DataFrame) -> list[dict[str, str]]:
    issues = []
    id_profiles = profile_df.loc[profile_df["smart_type"] == "id_field"]

    for row in id_profiles.to_dict("records"):
        issues.append(
            _issue(
                severity="low",
                issue_type="identifier_field",
                scope="column",
                column=row["column"],
                metric=f"{int(row['unique_count'])} unique ({float(row['unique_rate']):.1%})",
                details="Identifier fields are useful for joining records but should not be treated as analytical features.",
                recommendation="Keep this column for lookup or traceability, but exclude it from feature statistics and modeling.",
            )
        )

    return issues


def _detect_high_cardinality_fields(profile_df: pd.DataFrame) -> list[dict[str, str]]:
    issues = []
    candidate_profiles = profile_df.loc[
        profile_df["smart_type"].isin(["categorical_feature", "text_feature"])
        & (profile_df["unique_count"] >= 20)
        & (profile_df["unique_rate"] >= 0.5)
    ]

    for row in candidate_profiles.to_dict("records"):
        issues.append(
            _issue(
                severity="medium",
                issue_type="high_cardinality",
                scope="column",
                column=row["column"],
                metric=f"{int(row['unique_count'])} unique ({float(row['unique_rate']):.1%})",
                details="High-cardinality fields can create noisy group comparisons and sparse model features.",
                recommendation="Consider grouping rare values, extracting text features, or excluding the raw column.",
            )
        )

    return issues


def _detect_numeric_outliers(df: pd.DataFrame, profile_df: pd.DataFrame) -> list[dict[str, str]]:
    issues = []
    numeric_columns = profile_df.loc[
        profile_df["smart_type"] == "numerical_feature", "column"
    ].tolist()

    for column in numeric_columns:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(series) < 8 or not is_numeric_dtype(series):
            continue

        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        if iqr == 0:
            continue

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outlier_mask = (series < lower_bound) | (series > upper_bound)
        outlier_count = int(outlier_mask.sum())
        if outlier_count == 0:
            continue

        outlier_rate = outlier_count / len(series)
        severity = "high" if outlier_rate >= 0.05 else "medium"
        issues.append(
            _issue(
                severity=severity,
                issue_type="numeric_outliers",
                scope="column",
                column=column,
                metric=f"{outlier_count} outliers ({outlier_rate:.1%})",
                details=f"IQR rule detected values outside [{lower_bound:.2f}, {upper_bound:.2f}].",
                recommendation="Inspect whether these are valid extreme values, data entry errors, or require capping/transformation.",
            )
        )

    return issues


def _detect_target_imbalance(df: pd.DataFrame, profile_df: pd.DataFrame) -> list[dict[str, str]]:
    issues = []
    target_columns = profile_df.loc[
        profile_df["smart_type"] == "target_variable", "column"
    ].tolist()

    for column in target_columns:
        distribution = df[column].dropna().value_counts(normalize=True)
        if len(distribution) < 2:
            continue

        minority_share = float(distribution.min())
        majority_share = float(distribution.max())
        if minority_share >= 0.35:
            continue

        severity = "high" if minority_share < 0.2 else "medium"
        issues.append(
            _issue(
                severity=severity,
                issue_type="target_imbalance",
                scope="column",
                column=column,
                metric=f"minority {minority_share:.1%}, majority {majority_share:.1%}",
                details="An imbalanced target can make model accuracy misleading and reduce minority-class performance.",
                recommendation="Use stratified splits and evaluate precision, recall, F1, ROC-AUC, or PR-AUC instead of accuracy alone.",
            )
        )

    return issues


def _missing_value_recommendation(smart_type: str) -> str:
    if smart_type == "numerical_feature":
        return "Consider median imputation, missing indicators, or removing the field if missingness is too high."
    if smart_type in {"categorical_feature", "target_variable"}:
        return "Consider a dedicated 'Unknown' category, mode imputation, or row filtering depending on business meaning."
    if smart_type == "datetime_feature":
        return "Check whether missing timestamps mean incomplete events before imputing or filtering."
    if smart_type == "text_feature":
        return "Keep blanks as empty text only if absence of text is meaningful; otherwise investigate collection gaps."
    return "Investigate why values are missing before choosing deletion or imputation."


def _issue(
    severity: str,
    issue_type: str,
    scope: str,
    column: str,
    metric: str,
    details: str,
    recommendation: str,
) -> dict[str, str]:
    return {
        "severity": severity,
        "issue_type": issue_type,
        "scope": scope,
        "column": column,
        "metric": metric,
        "details": details,
        "recommendation": recommendation,
    }


def _severity_sort_key(value: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(value, 3)
