from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class EDARecommendation:
    analysis_type: str
    chart_type: str
    title: str
    columns: list[str]
    rationale: str


def build_eda_recommendations(profile_df: pd.DataFrame) -> pd.DataFrame:
    """Create rule-based EDA recommendations from smart field types."""
    recommendations: list[EDARecommendation] = []

    numeric_columns = _columns_by_type(profile_df, "numerical_feature")
    categorical_columns = _columns_by_type(profile_df, "categorical_feature")
    datetime_columns = _columns_by_type(profile_df, "datetime_feature")
    target_columns = _columns_by_type(profile_df, "target_variable")

    for column in numeric_columns[:4]:
        recommendations.append(
            EDARecommendation(
                analysis_type="numeric_distribution",
                chart_type="histogram",
                title=f"Distribution of {column}",
                columns=[column],
                rationale="Numerical features should be checked for spread, skewness, and unusual values.",
            )
        )

    for column in categorical_columns[:4]:
        recommendations.append(
            EDARecommendation(
                analysis_type="category_distribution",
                chart_type="bar_chart",
                title=f"Top categories in {column}",
                columns=[column],
                rationale="Categorical features should be checked for dominant groups and long-tail categories.",
            )
        )

    for column in datetime_columns[:2]:
        recommendations.append(
            EDARecommendation(
                analysis_type="time_trend",
                chart_type="line_chart",
                title=f"Record trend by {column}",
                columns=[column],
                rationale="Datetime fields enable trend analysis and seasonality checks.",
            )
        )

    for target in target_columns[:1]:
        recommendations.append(
            EDARecommendation(
                analysis_type="target_distribution",
                chart_type="bar_chart",
                title=f"Target distribution of {target}",
                columns=[target],
                rationale="Target variables should be checked for class balance before modeling.",
            )
        )

        for category in categorical_columns[:3]:
            recommendations.append(
                EDARecommendation(
                    analysis_type="target_by_category",
                    chart_type="grouped_bar_chart",
                    title=f"{target} by {category}",
                    columns=[category, target],
                    rationale="Comparing the target across categories can reveal segments associated with different outcomes.",
                )
            )

    if len(numeric_columns) >= 2:
        recommendations.append(
            EDARecommendation(
                analysis_type="correlation_heatmap",
                chart_type="heatmap",
                title="Numerical feature correlation",
                columns=numeric_columns,
                rationale="Correlation analysis helps identify related numerical features and potential redundancy.",
            )
        )

    return pd.DataFrame([recommendation.__dict__ for recommendation in recommendations])


def build_category_counts(df: pd.DataFrame, column: str, top_n: int = 15) -> pd.DataFrame:
    counts = (
        df[column]
        .fillna("Missing")
        .astype(str)
        .value_counts()
        .head(top_n)
        .reset_index()
    )
    counts.columns = [column, "count"]
    return counts


def build_time_trend(df: pd.DataFrame, column: str) -> pd.DataFrame:
    trend_df = pd.DataFrame({column: pd.to_datetime(df[column], errors="coerce", format="mixed")})
    trend_df = trend_df.dropna()
    if trend_df.empty:
        return pd.DataFrame(columns=[column, "count"])

    trend_df[column] = trend_df[column].dt.to_period("M").dt.to_timestamp()
    return trend_df.groupby(column).size().reset_index(name="count").sort_values(column)


def build_target_by_category(df: pd.DataFrame, category_column: str, target_column: str) -> pd.DataFrame:
    clean_df = df[[category_column, target_column]].dropna().copy()
    if clean_df.empty:
        return pd.DataFrame(columns=[category_column, target_column, "count", "target_rate"])

    clean_df[category_column] = clean_df[category_column].astype(str)
    numeric_target = pd.to_numeric(clean_df[target_column], errors="coerce")
    unique_numeric_targets = set(numeric_target.dropna().unique().tolist())

    if unique_numeric_targets <= {0, 1} and len(unique_numeric_targets) == 2:
        grouped = (
            clean_df.assign(_target=numeric_target)
            .groupby(category_column)
            .agg(count=("_target", "size"), target_rate=("_target", "mean"))
            .reset_index()
            .sort_values("target_rate", ascending=False)
        )
        return grouped

    grouped = (
        clean_df.groupby([category_column, target_column])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    grouped[target_column] = grouped[target_column].astype(str)
    return grouped


def build_correlation_pairs(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    numeric_df = df[columns].apply(pd.to_numeric, errors="coerce")
    corr = numeric_df.corr().round(3)
    if corr.empty:
        return pd.DataFrame(columns=["feature_x", "feature_y", "correlation"])

    return corr.stack().reset_index(name="correlation").rename(
        columns={"level_0": "feature_x", "level_1": "feature_y"}
    )


def _columns_by_type(profile_df: pd.DataFrame, smart_type: str) -> list[str]:
    if profile_df.empty:
        return []

    return profile_df.loc[profile_df["smart_type"] == smart_type, "column"].tolist()
