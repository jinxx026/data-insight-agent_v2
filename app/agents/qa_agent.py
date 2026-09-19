from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.agents.workflow_agent import AnalysisWorkflowResult
from app.llm.model import LLMConfig, generate_chat_completion
from app.rag.retriever import retrieve_knowledge
from app.ui.i18n import localize_dataframe


@dataclass(frozen=True)
class QAResult:
    mode: str
    answer: str
    retrieved_df: pd.DataFrame
    error: str | None = None


def answer_user_question(
    question: str,
    workflow_result: AnalysisWorkflowResult,
    knowledge_dir: Path,
    language: str,
    use_llm: bool = False,
    llm_config: LLMConfig | None = None,
) -> QAResult:
    """Answer a natural-language user question using dataset context and RAG snippets."""
    retrieved_df = retrieve_knowledge(question, knowledge_dir, top_k=4)
    local_answer = _build_local_answer(question, workflow_result, retrieved_df, language)

    if not use_llm:
        return QAResult(mode="local", answer=local_answer, retrieved_df=retrieved_df)

    if llm_config is None:
        return QAResult(
            mode="local_fallback",
            answer=local_answer,
            retrieved_df=retrieved_df,
            error=_text(
                language,
                zh="未检测到可用的 LLM 配置，已使用本地 RAG 规则回答。",
                en="No usable LLM configuration was found, so local RAG rules were used.",
            ),
        )

    try:
        llm_answer = generate_chat_completion(
            config=llm_config,
            system_prompt=_qa_system_prompt(language),
            user_prompt=_qa_user_prompt(question, workflow_result, retrieved_df, language),
        )
    except Exception as exc:
        return QAResult(
            mode="local_fallback",
            answer=local_answer,
            retrieved_df=retrieved_df,
            error=_text(
                language,
                zh=f"LLM 问答调用失败，已使用本地 RAG 规则回答。错误：{exc}",
                en=f"LLM Q&A call failed, so local RAG rules were used. Error: {exc}",
            ),
        )

    return QAResult(mode="llm", answer=llm_answer, retrieved_df=retrieved_df)


def _build_local_answer(
    question: str,
    workflow_result: AnalysisWorkflowResult,
    retrieved_df: pd.DataFrame,
    language: str,
) -> str:
    matched_columns = _find_referenced_columns(question, workflow_result.profile_df)
    matched_quality = _find_relevant_quality_issues(question, workflow_result.quality_df, matched_columns)

    if language == "zh":
        lines = [
            f"针对你的问题：{question}",
            "",
            "### 基于当前数据集的回答",
            _dataset_context_text(workflow_result, matched_columns, matched_quality, language),
            "",
            "### 基于知识库的解释",
            _knowledge_context_text(retrieved_df, language),
            "",
            "### 建议",
            _recommendation_text(matched_columns, matched_quality, retrieved_df, language),
        ]
        return "\n".join(lines)

    lines = [
        f"Question: {question}",
        "",
        "### Answer From The Current Dataset",
        _dataset_context_text(workflow_result, matched_columns, matched_quality, language),
        "",
        "### Explanation From The Knowledge Base",
        _knowledge_context_text(retrieved_df, language),
        "",
        "### Recommendation",
        _recommendation_text(matched_columns, matched_quality, retrieved_df, language),
    ]
    return "\n".join(lines)


def _find_referenced_columns(question: str, profile_df: pd.DataFrame) -> pd.DataFrame:
    if profile_df.empty:
        return profile_df

    lowered_question = question.lower()
    matched_columns = [
        column
        for column in profile_df["column"].astype(str).tolist()
        if column.lower() in lowered_question
    ]

    if matched_columns:
        return profile_df.loc[profile_df["column"].isin(matched_columns)]

    return pd.DataFrame(columns=profile_df.columns)


def _find_relevant_quality_issues(
    question: str,
    quality_df: pd.DataFrame,
    matched_columns: pd.DataFrame,
) -> pd.DataFrame:
    if quality_df.empty:
        return quality_df

    lowered_question = question.lower()
    matched_column_names = (
        set(matched_columns["column"].astype(str).tolist()) if not matched_columns.empty else set()
    )
    mask = quality_df["column"].astype(str).isin(matched_column_names)

    for issue_type in quality_df["issue_type"].astype(str).unique().tolist():
        if issue_type.replace("_", " ") in lowered_question or issue_type in lowered_question:
            mask = mask | (quality_df["issue_type"] == issue_type)

    risk_keywords = ["风险", "问题", "主要风险", "质量", "risk", "issue", "problem", "quality"]
    if any(keyword in lowered_question for keyword in risk_keywords):
        risk_mask = quality_df["severity"].isin(["high", "medium"])
        if risk_mask.any():
            mask = mask | risk_mask

    return quality_df.loc[mask]


def _dataset_context_text(
    workflow_result: AnalysisWorkflowResult,
    matched_columns: pd.DataFrame,
    matched_quality: pd.DataFrame,
    language: str,
) -> str:
    summary = workflow_result.dataset_summary
    if language == "zh":
        lines = [
            f"当前数据集包含 {summary['rows']:,} 行、{summary['columns']:,} 列，"
            f"发现 {len(workflow_result.quality_df)} 个数据质量问题，"
            f"系统推荐 {len(workflow_result.eda_df)} 个 EDA 分析动作。"
        ]
        if not matched_columns.empty:
            lines.append("问题中提到的字段画像：")
            display_columns = localize_dataframe(matched_columns, "zh")
            for row in display_columns.to_dict("records"):
                lines.append(
                    f"- {row['字段名']}：{row['智能类型']}，缺失率 {float(row['缺失率']):.1%}，"
                    f"唯一值数量 {int(row['唯一值数量'])}。判断原因：{row['判断原因']}"
                )
        if not matched_quality.empty:
            lines.append("相关数据质量问题：")
            display_quality = localize_dataframe(matched_quality, "zh")
            for row in display_quality.to_dict("records"):
                lines.append(f"- {row['严重程度']} / {row['问题类型']}：{row['指标']}。{row['处理建议']}")
        return "\n".join(lines)

    lines = [
        f"The current dataset has {summary['rows']:,} rows and {summary['columns']:,} columns, "
        f"with {len(workflow_result.quality_df)} detected quality issues and "
        f"{len(workflow_result.eda_df)} recommended EDA actions."
    ]
    if not matched_columns.empty:
        lines.append("Referenced field profile:")
        for row in matched_columns.to_dict("records"):
            lines.append(
                f"- {row['column']}: {row['smart_type']}, missing rate {float(row['missing_rate']):.1%}, "
                f"{int(row['unique_count'])} unique values. Reason: {row['reason']}"
            )
    if not matched_quality.empty:
        lines.append("Related data quality issues:")
        for row in matched_quality.to_dict("records"):
            lines.append(f"- {row['severity']} / {row['issue_type']}: {row['metric']}. {row['recommendation']}")
    return "\n".join(lines)


def _knowledge_context_text(retrieved_df: pd.DataFrame, language: str) -> str:
    if retrieved_df.empty:
        return (
            "知识库中暂未检索到直接相关内容。"
            if language == "zh"
            else "No directly relevant knowledge snippets were retrieved."
        )

    lines = []
    for index, row in enumerate(retrieved_df.to_dict("records"), start=1):
        if language == "zh":
            lines.append(f"{index}. 来源 {row['source']}，相关度 {row['score']}：{_trim(row['text'])}")
        else:
            lines.append(f"{index}. Source {row['source']}, score {row['score']}: {_trim(row['text'])}")
    return "\n".join(lines)


def _recommendation_text(
    matched_columns: pd.DataFrame,
    matched_quality: pd.DataFrame,
    retrieved_df: pd.DataFrame,
    language: str,
) -> str:
    if language == "zh":
        if not matched_quality.empty:
            return "优先处理上面列出的质量问题，再基于字段类型选择图表或建模方法。"
        if not matched_columns.empty:
            return "先确认字段的业务含义，再根据字段类型决定是否用于 EDA、建模或仅用于追踪。"
        if not retrieved_df.empty:
            return "可以结合知识库解释继续追问更具体的字段或分析方法。"
        return "建议换一种问法，加入字段名或分析主题，例如缺失值、异常值、相关性或类别不平衡。"

    if not matched_quality.empty:
        return "Address the listed quality issues first, then choose charts or modeling methods based on field type."
    if not matched_columns.empty:
        return "Confirm the field's business meaning, then decide whether it should be used for EDA, modeling, or traceability only."
    if not retrieved_df.empty:
        return "Use the retrieved explanation as a basis and ask a more specific follow-up about a field or method."
    return "Try rephrasing the question with a field name or analysis topic such as missing values, outliers, correlation, or class imbalance."


def _qa_system_prompt(language: str) -> str:
    if language == "zh":
        return (
            "你是一个严谨的数据分析问答助手。只能基于当前数据集摘要和检索到的知识库片段回答。"
            "不要编造不存在的字段、数值或结论。回答要简洁、可操作。"
        )

    return (
        "You are a rigorous data analysis Q&A assistant. Answer only from the current dataset summary "
        "and retrieved knowledge snippets. Do not invent fields, values, or conclusions. Keep the answer concise and actionable."
    )


def _qa_user_prompt(
    question: str,
    workflow_result: AnalysisWorkflowResult,
    retrieved_df: pd.DataFrame,
    language: str,
) -> str:
    context = {
        "question": question,
        "dataset_summary": workflow_result.dataset_summary,
        "field_profile": workflow_result.profile_df[
            ["column", "smart_type", "missing_rate", "unique_count", "unique_rate", "reason"]
        ].to_dict("records"),
        "quality_issues": workflow_result.quality_df.to_dict("records"),
        "eda_recommendations": workflow_result.eda_df.to_dict("records"),
        "retrieved_knowledge": retrieved_df.to_dict("records"),
    }
    context_text = pd.Series(context).to_json(force_ascii=False, indent=2)
    if language == "zh":
        return f"请回答用户问题，并说明依据来自数据集还是知识库。\n\n{context_text}"
    return f"Answer the user question and state whether the evidence comes from the dataset or the knowledge base.\n\n{context_text}"


def _trim(text: str, max_chars: int = 380) -> str:
    compact = " ".join(str(text).split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."


def _text(language: str, zh: str, en: str) -> str:
    return zh if language == "zh" else en
