from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.agents.insight_agent import InsightResult, generate_insights
from app.agents.report_agent import generate_html_report, generate_markdown_report
from app.data.eda import build_eda_recommendations
from app.data.loader import build_column_overview, build_dataset_summary
from app.data.profiler import profile_dataframe
from app.data.quality import analyze_data_quality
from app.llm.model import LLMConfig


@dataclass(frozen=True)
class WorkflowConfig:
    dataset_name: str
    language: str
    use_llm: bool = False
    llm_config: LLMConfig | None = None


@dataclass(frozen=True)
class WorkflowStep:
    agent: str
    status: str
    output: str


@dataclass(frozen=True)
class AnalysisWorkflowResult:
    dataset_name: str
    dataset_summary: dict[str, object]
    column_overview: pd.DataFrame
    profile_df: pd.DataFrame
    quality_df: pd.DataFrame
    eda_df: pd.DataFrame
    insight_result: InsightResult
    markdown_report: str
    html_report: str
    steps: list[WorkflowStep]


def run_analysis_workflow(df: pd.DataFrame, config: WorkflowConfig) -> AnalysisWorkflowResult:
    """Run the multi-agent analysis workflow from raw dataframe to report."""
    steps: list[WorkflowStep] = []

    dataset_summary = build_dataset_summary(df)
    column_overview = build_column_overview(df)
    steps.append(
        WorkflowStep(
            agent="Data Loader",
            status="completed",
            output=f"Loaded {dataset_summary['rows']} rows and {dataset_summary['columns']} columns.",
        )
    )

    profile_df = profile_dataframe(df)
    steps.append(
        WorkflowStep(
            agent="Data Profiler Agent",
            status="completed",
            output=f"Classified {len(profile_df)} fields into semantic feature types.",
        )
    )

    quality_df = analyze_data_quality(df, profile_df)
    steps.append(
        WorkflowStep(
            agent="Data Quality Agent",
            status="completed",
            output=f"Detected {len(quality_df)} data quality issues.",
        )
    )

    eda_df = build_eda_recommendations(profile_df)
    steps.append(
        WorkflowStep(
            agent="EDA Agent",
            status="completed",
            output=f"Recommended {len(eda_df)} exploratory analysis actions.",
        )
    )

    insight_result = generate_insights(
        df=df,
        profile_df=profile_df,
        quality_df=quality_df,
        eda_df=eda_df,
        language=config.language,
        use_llm=config.use_llm,
        llm_config=config.llm_config,
    )
    steps.append(
        WorkflowStep(
            agent="Insight Agent",
            status="completed",
            output=f"Generated insights using {insight_result.mode} mode.",
        )
    )

    markdown_report = generate_markdown_report(
        df=df,
        dataset_name=config.dataset_name,
        dataset_summary=dataset_summary,
        profile_df=profile_df,
        quality_df=quality_df,
        eda_df=eda_df,
        insight_result=insight_result,
        language=config.language,
    )
    html_report = generate_html_report(markdown_report, title=f"{config.dataset_name} Analysis Report")
    steps.append(
        WorkflowStep(
            agent="Report Agent",
            status="completed",
            output="Generated Markdown and HTML analysis reports.",
        )
    )

    return AnalysisWorkflowResult(
        dataset_name=config.dataset_name,
        dataset_summary=dataset_summary,
        column_overview=column_overview,
        profile_df=profile_df,
        quality_df=quality_df,
        eda_df=eda_df,
        insight_result=insight_result,
        markdown_report=markdown_report,
        html_report=html_report,
        steps=steps,
    )


def workflow_steps_to_dataframe(steps: list[WorkflowStep]) -> pd.DataFrame:
    return pd.DataFrame([step.__dict__ for step in steps])
