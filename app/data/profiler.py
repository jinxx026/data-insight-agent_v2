from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_string_dtype,
)


TARGET_NAME_KEYWORDS = {
    "target",
    "label",
    "class",
    "churn",
    "fraud",
    "default",
    "survived",
    "clicked",
    "converted",
    "purchased",
    "is_fraud",
    "is_churn",
}

ID_NAME_KEYWORDS = {"id", "uuid", "guid", "key", "code", "number", "no"}


@dataclass(frozen=True)
class ColumnProfile:
    column: str
    pandas_dtype: str
    smart_type: str
    analysis_role: str
    reason: str
    missing_count: int
    missing_rate: float
    unique_count: int
    unique_rate: float
    example_values: str


def profile_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Infer analysis-oriented feature types for all columns in a dataframe."""
    profiles = [_profile_column(df, column) for column in df.columns]
    return pd.DataFrame([profile.__dict__ for profile in profiles])


def summarize_feature_types(profile_df: pd.DataFrame) -> pd.DataFrame:
    """Return counts by inferred smart type for the UI summary."""
    if profile_df.empty:
        return pd.DataFrame(columns=["smart_type", "count"])

    return (
        profile_df.groupby("smart_type", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["count", "smart_type"], ascending=[False, True])
    )


def _profile_column(df: pd.DataFrame, column: str) -> ColumnProfile:
    series = df[column]
    row_count = max(len(series), 1)
    non_null = series.dropna()
    unique_count = int(non_null.nunique(dropna=True))
    missing_count = int(series.isna().sum())
    missing_rate = round(missing_count / row_count, 4)
    unique_rate = round(unique_count / row_count, 4)
    dtype = str(series.dtype)
    normalized_name = _normalize_name(column)
    example_values = _format_examples(non_null)

    smart_type, role, reason = _infer_smart_type(
        series=series,
        non_null=non_null,
        column_name=normalized_name,
        unique_count=unique_count,
        unique_rate=unique_rate,
        row_count=row_count,
    )

    return ColumnProfile(
        column=column,
        pandas_dtype=dtype,
        smart_type=smart_type,
        analysis_role=role,
        reason=reason,
        missing_count=missing_count,
        missing_rate=missing_rate,
        unique_count=unique_count,
        unique_rate=unique_rate,
        example_values=example_values,
    )


def _infer_smart_type(
    series: pd.Series,
    non_null: pd.Series,
    column_name: str,
    unique_count: int,
    unique_rate: float,
    row_count: int,
) -> tuple[str, str, str]:
    if non_null.empty:
        return (
            "empty_field",
            "exclude",
            "All values are missing, so this field cannot be used for analysis yet.",
        )

    if _looks_like_target(column_name, unique_count):
        return (
            "target_variable",
            "target",
            "The column name suggests a label/target and it has a small number of classes.",
        )

    if _looks_like_id(column_name, unique_count, unique_rate, row_count):
        return (
            "id_field",
            "identifier",
            "The column name or near-unique values indicate an identifier, not a modeling feature.",
        )

    if is_datetime64_any_dtype(series) or _looks_like_datetime(column_name, non_null):
        return (
            "datetime_feature",
            "time",
            "Most non-missing values can be parsed as dates or timestamps.",
        )

    if is_bool_dtype(series):
        return (
            "categorical_feature",
            "feature",
            "Boolean values are best treated as a two-class categorical feature.",
        )

    if is_numeric_dtype(series):
        if _looks_binary(non_null) or _looks_low_cardinality_numeric(unique_count, row_count):
            return (
                "categorical_feature",
                "feature",
                "Numeric values have low cardinality, so they are likely categories or flags.",
            )

        return (
            "numerical_feature",
            "feature",
            "Numeric dtype with enough distinct values for distribution and correlation analysis.",
        )

    if _looks_like_text(non_null, unique_count, unique_rate, row_count):
        return (
            "text_feature",
            "feature",
            "String values are relatively long or high-cardinality, which fits text analysis.",
        )

    if is_string_dtype(series) or series.dtype == "object":
        return (
            "categorical_feature",
            "feature",
            "String/object values have repeated groups suitable for category comparison.",
        )

    return (
        "unknown_feature",
        "review",
        "The field does not match common numeric, categorical, datetime, text, target, or ID rules.",
    )


def _normalize_name(column: str) -> str:
    return column.strip().lower().replace("-", "_").replace(" ", "_")


def _looks_like_target(column_name: str, unique_count: int) -> bool:
    has_target_name = any(keyword in column_name for keyword in TARGET_NAME_KEYWORDS)
    return has_target_name and 2 <= unique_count <= 20


def _looks_like_id(column_name: str, unique_count: int, unique_rate: float, row_count: int) -> bool:
    name_parts = {part for part in column_name.replace(".", "_").split("_") if part}
    has_id_name = bool(name_parts & ID_NAME_KEYWORDS) or column_name.endswith("_id")
    near_unique_large_column = row_count >= 30 and unique_rate >= 0.9 and unique_count >= 20
    return has_id_name or near_unique_large_column


def _looks_like_datetime(column_name: str, non_null: pd.Series) -> bool:
    sample = non_null.astype(str).head(100)
    if sample.empty:
        return False

    date_name_hint = any(token in column_name for token in ["date", "time", "created", "updated"])
    date_value_hint = sample.str.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}").mean() >= 0.6
    if not date_name_hint and not date_value_hint:
        return False

    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    return float(parsed.notna().mean()) >= 0.8


def _looks_binary(non_null: pd.Series) -> bool:
    values = set(non_null.drop_duplicates().head(3).astype(str).str.lower())
    binary_sets = [
        {"0", "1"},
        {"true", "false"},
        {"yes", "no"},
        {"y", "n"},
    ]
    return any(values <= allowed and len(values) == 2 for allowed in binary_sets)


def _looks_low_cardinality_numeric(unique_count: int, row_count: int) -> bool:
    if row_count < 30:
        return 2 <= unique_count <= 5

    return unique_count <= 10 and unique_count / row_count <= 0.2


def _looks_like_text(
    non_null: pd.Series,
    unique_count: int,
    unique_rate: float,
    row_count: int,
) -> bool:
    sample = non_null.astype(str).head(100)
    average_length = float(sample.str.len().mean()) if not sample.empty else 0.0

    return average_length >= 40 or (row_count >= 30 and unique_rate >= 0.5 and unique_count >= 20)


def _format_examples(non_null: pd.Series) -> str:
    examples = non_null.drop_duplicates().head(3).astype(str).tolist()
    return ", ".join(examples)
