from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.data.quality import build_quality_summary
from app.llm.model import LLMConfig, generate_chat_completion, load_llm_config


@dataclass(frozen=True)
class InsightResult:
    mode: str
    summary: str
    insights: pd.DataFrame
    llm_output: str | None = None
    llm_error: str | None = None


INSIGHT_COLUMNS = ["priority", "topic", "insight", "evidence", "recommendation"]


def generate_insights(
    df: pd.DataFrame,
    profile_df: pd.DataFrame,
    quality_df: pd.DataFrame,
    eda_df: pd.DataFrame,
    language: str,
    use_llm: bool = False,
    llm_config: LLMConfig | None = None,
) -> InsightResult:
    """Generate data insights from structured profiling, quality, and EDA outputs."""
    local_summary = _build_local_summary(df, profile_df, quality_df, eda_df, language)
    local_insights = _build_local_insights(df, profile_df, quality_df, eda_df, language)

    if not use_llm:
        return InsightResult(mode="local", summary=local_summary, insights=local_insights)

    config = llm_config or load_llm_config()
    if config is None:
        return InsightResult(
            mode="local_fallback",
            summary=local_summary,
            insights=local_insights,
            llm_error=_text(
                language,
                zh="未检测到 LLM_API_KEY，已使用本地规则生成洞察。",
                en="LLM_API_KEY was not found, so local rule-based insights were used.",
            ),
        )

    context = _build_llm_context(df, profile_df, quality_df, eda_df, local_insights)
    system_prompt = _system_prompt(language)
    user_prompt = _user_prompt(language, context)

    try:
        llm_output = generate_chat_completion(config, system_prompt, user_prompt)
    except Exception as exc:
        return InsightResult(
            mode="local_fallback",
            summary=local_summary,
            insights=local_insights,
            llm_error=_text(
                language,
                zh=f"LLM 调用失败，已使用本地规则生成洞察。错误：{exc}",
                en=f"LLM call failed, so local rule-based insights were used. Error: {exc}",
            ),
        )

    return InsightResult(
        mode="llm",
        summary=_text(
            language,
            zh="已基于结构化数据摘要生成 LLM 洞察报告。",
            en="LLM insight report generated from structured data summaries.",
        ),
        insights=local_insights,
        llm_output=llm_output,
    )


def _build_local_summary(
    df: pd.DataFrame,
    profile_df: pd.DataFrame,
    quality_df: pd.DataFrame,
    eda_df: pd.DataFrame,
    language: str,
) -> str:
    row_count, column_count = df.shape
    target_columns = profile_df.loc[
        profile_df["smart_type"] == "target_variable", "column"
    ].tolist()
    quality_summary = build_quality_summary(df, quality_df)

    if language == "zh":
        target_text = "、".join(target_columns) if target_columns else "暂未检测到"
        return (
            f"数据集包含 {row_count:,} 行、{column_count:,} 列；"
            f"检测到目标变量：{target_text}；"
            f"当前发现 {quality_summary['quality_issues']} 个数据质量问题，"
            f"其中高严重程度问题 {quality_summary['high_severity']} 个；"
            f"系统推荐 {len(eda_df)} 个 EDA 分析动作。"
        )

    target_text = ", ".join(target_columns) if target_columns else "not detected"
    return (
        f"The dataset contains {row_count:,} rows and {column_count:,} columns. "
        f"Detected target variable: {target_text}. "
        f"The current rule set found {quality_summary['quality_issues']} data quality issues, "
        f"including {quality_summary['high_severity']} high-severity issues. "
        f"The system recommended {len(eda_df)} EDA actions."
    )


def _build_local_insights(
    df: pd.DataFrame,
    profile_df: pd.DataFrame,
    quality_df: pd.DataFrame,
    eda_df: pd.DataFrame,
    language: str,
) -> pd.DataFrame:
    insights: list[dict[str, str]] = []

    insights.extend(_quality_insights(quality_df, language))
    insights.extend(_target_insights(df, profile_df, language))
    insights.extend(_feature_mix_insights(profile_df, language))
    insights.extend(_eda_insights(eda_df, language))

    if not insights:
        insights.append(
            _insight(
                priority="medium",
                topic=_text(language, zh="总体结论", en="Overall summary"),
                insight=_text(
                    language,
                    zh="当前规则没有发现明显风险，数据可以进入基础 EDA 阶段。",
                    en="No major rule-based risks were found, so the dataset is ready for basic EDA.",
                ),
                evidence=_text(language, zh="质量问题表为空。", en="The quality issue table is empty."),
                recommendation=_text(
                    language,
                    zh="继续查看自动图表，并结合业务问题选择重点字段。",
                    en="Continue reviewing automatic charts and prioritize fields based on the business question.",
                ),
            )
        )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    return pd.DataFrame(insights, columns=INSIGHT_COLUMNS).sort_values(
        by="priority", key=lambda values: values.map(priority_order)
    )


def _quality_insights(quality_df: pd.DataFrame, language: str) -> list[dict[str, str]]:
    if quality_df.empty:
        return []

    insights = []
    high_issues = quality_df.loc[quality_df["severity"] == "high"]
    if not high_issues.empty:
        issue_text = ", ".join(
            f"{row['issue_type']}({row['column'] or row['scope']})"
            for row in high_issues.to_dict("records")[:3]
        )
        insights.append(
            _insight(
                priority="high",
                topic=_text(language, zh="优先处理高风险质量问题", en="Prioritize high-risk data quality issues"),
                insight=_text(
                    language,
                    zh="数据中存在会明显影响分析或建模的高严重程度问题。",
                    en="The dataset contains high-severity issues that can materially affect analysis or modeling.",
                ),
                evidence=issue_text,
                recommendation=_text(
                    language,
                    zh="先处理这些问题，再进行建模或业务结论汇报。",
                    en="Resolve these issues before modeling or presenting business conclusions.",
                ),
            )
        )

    missing_issues = quality_df.loc[quality_df["issue_type"] == "missing_values"]
    if not missing_issues.empty:
        columns = ", ".join(missing_issues["column"].astype(str).tolist()[:5])
        insights.append(
            _insight(
                priority="medium",
                topic=_text(language, zh="缺失值处理", en="Missing value handling"),
                insight=_text(
                    language,
                    zh="部分字段存在缺失值，可能影响统计图表和模型特征。",
                    en="Some fields contain missing values, which can affect charts and model features.",
                ),
                evidence=columns,
                recommendation=_text(
                    language,
                    zh="按字段类型选择填充、单独标记 Unknown，或过滤缺失样本。",
                    en="Choose imputation, Unknown categories, or row filtering based on field type and business meaning.",
                ),
            )
        )

    return insights


def _target_insights(df: pd.DataFrame, profile_df: pd.DataFrame, language: str) -> list[dict[str, str]]:
    insights = []
    target_columns = profile_df.loc[
        profile_df["smart_type"] == "target_variable", "column"
    ].tolist()
    if not target_columns:
        insights.append(
            _insight(
                priority="medium",
                topic=_text(language, zh="目标变量", en="Target variable"),
                insight=_text(
                    language,
                    zh="当前没有检测到目标变量，系统更适合先做描述性分析。",
                    en="No target variable was detected, so the current workflow is better suited for descriptive analysis.",
                ),
                evidence=_text(language, zh="字段画像中没有 target_variable。", en="No target_variable exists in the field profile."),
                recommendation=_text(
                    language,
                    zh="如果要做预测建模，请确认标签字段名称或手动指定目标变量。",
                    en="If predictive modeling is needed, verify the label column name or manually specify the target.",
                ),
            )
        )
        return insights

    for target in target_columns[:1]:
        distribution = df[target].dropna().value_counts(normalize=True)
        if distribution.empty:
            continue
        top_share = float(distribution.max())
        evidence = ", ".join(f"{index}: {value:.1%}" for index, value in distribution.items())
        priority = "high" if top_share >= 0.8 else "medium" if top_share >= 0.65 else "low"
        insights.append(
            _insight(
                priority=priority,
                topic=_text(language, zh="目标变量分布", en="Target distribution"),
                insight=_text(
                    language,
                    zh=f"{target} 的类别分布需要重点关注。",
                    en=f"The class distribution of {target} should be reviewed.",
                ),
                evidence=evidence,
                recommendation=_text(
                    language,
                    zh="如果类别不平衡，后续建模应使用分层抽样，并重点看 recall、F1 或 PR-AUC。",
                    en="If classes are imbalanced, use stratified splits and prioritize recall, F1, or PR-AUC.",
                ),
            )
        )

    return insights


def _feature_mix_insights(profile_df: pd.DataFrame, language: str) -> list[dict[str, str]]:
    type_counts = profile_df["smart_type"].value_counts().to_dict()
    numeric_count = int(type_counts.get("numerical_feature", 0))
    categorical_count = int(type_counts.get("categorical_feature", 0))
    datetime_count = int(type_counts.get("datetime_feature", 0))
    text_count = int(type_counts.get("text_feature", 0))

    return [
        _insight(
            priority="low",
            topic=_text(language, zh="字段结构", en="Feature mix"),
            insight=_text(
                language,
                zh="数据包含多种字段类型，适合做组合型 EDA。",
                en="The dataset contains multiple field types and supports mixed EDA.",
            ),
            evidence=_text(
                language,
                zh=f"数值特征 {numeric_count} 个，类别特征 {categorical_count} 个，时间字段 {datetime_count} 个，文本字段 {text_count} 个。",
                en=f"{numeric_count} numerical, {categorical_count} categorical, {datetime_count} datetime, and {text_count} text fields.",
            ),
            recommendation=_text(
                language,
                zh="优先结合目标变量查看类别分组差异，再查看数值分布和相关性。",
                en="Start with target-by-category comparisons, then review numerical distributions and correlations.",
            ),
        )
    ]


def _eda_insights(eda_df: pd.DataFrame, language: str) -> list[dict[str, str]]:
    if eda_df.empty:
        return []

    analysis_types = eda_df["analysis_type"].value_counts().to_dict()
    recommended = ", ".join(f"{key}: {value}" for key, value in analysis_types.items())

    return [
        _insight(
            priority="low",
            topic=_text(language, zh="后续分析路径", en="Next analysis path"),
            insight=_text(
                language,
                zh="系统已经根据字段类型生成自动 EDA 路线。",
                en="The system generated an automatic EDA path based on smart field types.",
            ),
            evidence=recommended,
            recommendation=_text(
                language,
                zh="优先查看目标变量相关图表，再查看异常值和相关性图表。",
                en="Review target-related charts first, then inspect outlier and correlation charts.",
            ),
        )
    ]


def _build_llm_context(
    df: pd.DataFrame,
    profile_df: pd.DataFrame,
    quality_df: pd.DataFrame,
    eda_df: pd.DataFrame,
    local_insights: pd.DataFrame,
) -> str:
    summary = {
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "field_profile": profile_df[
            ["column", "smart_type", "missing_rate", "unique_count", "unique_rate"]
        ].to_dict("records"),
        "quality_issues": quality_df.to_dict("records"),
        "eda_recommendations": eda_df.to_dict("records"),
        "local_rule_insights": local_insights.to_dict("records"),
    }
    return pd.Series(summary).to_json(force_ascii=False, indent=2)


def _system_prompt(language: str) -> str:
    if language == "zh":
        return (
            "你是一个严谨的数据分析助手。只能基于用户提供的结构化摘要进行分析，"
            "不要编造未提供的数据。输出中文，结构包括：总体结论、关键发现、风险提醒、下一步建议。"
        )

    return (
        "You are a rigorous data analysis assistant. Use only the structured summary provided by the user. "
        "Do not invent data. Respond in English with sections: Overall Summary, Key Findings, Risks, Next Steps."
    )


def _user_prompt(language: str, context: str) -> str:
    if language == "zh":
        return f"请基于以下数据摘要生成一份简洁的数据洞察报告：\n\n{context}"

    return f"Generate a concise data insight report from the following dataset summary:\n\n{context}"


def _insight(
    priority: str,
    topic: str,
    insight: str,
    evidence: str,
    recommendation: str,
) -> dict[str, str]:
    return {
        "priority": priority,
        "topic": topic,
        "insight": insight,
        "evidence": evidence,
        "recommendation": recommendation,
    }


def _text(language: str, zh: str, en: str) -> str:
    return zh if language == "zh" else en
