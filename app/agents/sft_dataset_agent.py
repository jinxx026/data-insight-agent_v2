from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.agents.workflow_agent import AnalysisWorkflowResult


@dataclass(frozen=True)
class SFTDatasetResult:
    samples: list[dict[str, Any]]
    jsonl: str


def build_sft_dataset(
    workflow_result: AnalysisWorkflowResult,
    language: str,
) -> SFTDatasetResult:
    """Build instruction-tuning samples from one completed analysis workflow.

    The app does not fine-tune a model directly. It exports supervised
    fine-tuning examples that can later be used by a LoRA/SFT training pipeline.
    """
    samples = [
        _sample(
            task_type="field_profiling",
            instruction=_text(
                language,
                zh="根据数据集概览和字段统计，识别每个字段的语义类型，并说明判断理由。",
                en="Identify each field's semantic type from dataset metadata and explain the reasoning.",
            ),
            input_data={
                "dataset_summary": workflow_result.dataset_summary,
                "column_overview": _records(workflow_result.column_overview),
            },
            output_data=_records(workflow_result.profile_df),
            dataset_name=workflow_result.dataset_name,
            language=language,
        ),
        _sample(
            task_type="data_quality_analysis",
            instruction=_text(
                language,
                zh="根据字段画像和数据统计，找出主要数据质量问题并给出处理建议。",
                en="Detect major data quality issues from the field profile and dataset statistics, then provide recommendations.",
            ),
            input_data={
                "dataset_summary": workflow_result.dataset_summary,
                "field_profile": _records(workflow_result.profile_df),
            },
            output_data=_records(workflow_result.quality_df),
            dataset_name=workflow_result.dataset_name,
            language=language,
        ),
        _sample(
            task_type="eda_planning",
            instruction=_text(
                language,
                zh="根据字段类型和数据质量情况，推荐适合的探索性数据分析方法。",
                en="Recommend suitable exploratory data analysis actions from field types and data quality context.",
            ),
            input_data={
                "field_profile": _records(workflow_result.profile_df),
                "quality_issues": _records(workflow_result.quality_df),
            },
            output_data=_records(workflow_result.eda_df),
            dataset_name=workflow_result.dataset_name,
            language=language,
        ),
        _sample(
            task_type="insight_generation",
            instruction=_text(
                language,
                zh="根据字段画像、质量问题和 EDA 推荐，生成清晰、可执行的数据洞察。",
                en="Generate concise and actionable data insights from field profiles, quality issues, and EDA recommendations.",
            ),
            input_data={
                "dataset_summary": workflow_result.dataset_summary,
                "field_profile": _records(workflow_result.profile_df),
                "quality_issues": _records(workflow_result.quality_df),
                "eda_recommendations": _records(workflow_result.eda_df),
            },
            output_data={
                "summary": workflow_result.insight_result.summary,
                "insights": _records(workflow_result.insight_result.insights),
                "llm_output": workflow_result.insight_result.llm_output,
            },
            dataset_name=workflow_result.dataset_name,
            language=language,
        ),
        _sample(
            task_type="report_generation",
            instruction=_text(
                language,
                zh="根据完整分析结果生成一份结构化 Markdown 数据分析报告。",
                en="Generate a structured Markdown data analysis report from the completed analysis results.",
            ),
            input_data={
                "dataset_summary": workflow_result.dataset_summary,
                "field_profile": _records(workflow_result.profile_df),
                "quality_issues": _records(workflow_result.quality_df),
                "eda_recommendations": _records(workflow_result.eda_df),
                "insights": _records(workflow_result.insight_result.insights),
            },
            output_data=workflow_result.markdown_report,
            dataset_name=workflow_result.dataset_name,
            language=language,
        ),
    ]

    jsonl = "\n".join(json.dumps(sample, ensure_ascii=False) for sample in samples)
    return SFTDatasetResult(samples=samples, jsonl=jsonl)


def _sample(
    task_type: str,
    instruction: str,
    input_data: Any,
    output_data: Any,
    dataset_name: str,
    language: str,
) -> dict[str, Any]:
    return {
        "instruction": instruction,
        "input": input_data,
        "output": output_data,
        "metadata": {
            "dataset_name": dataset_name,
            "task_type": task_type,
            "language": language,
            "format": "data-insight-agent-sft-v1",
        },
    }


def _records(df: pd.DataFrame, limit: int = 100) -> list[dict[str, Any]]:
    if df.empty:
        return []
    clean_df = df.head(limit).astype(object).where(pd.notna(df.head(limit)), None)
    return clean_df.to_dict("records")


def _text(language: str, zh: str, en: str) -> str:
    return zh if language == "zh" else en
