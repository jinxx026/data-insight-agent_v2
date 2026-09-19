from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.agents.qa_agent import answer_user_question
from app.agents.table_query_agent import generate_sql_from_question, run_table_query
from app.agents.workflow_agent import AnalysisWorkflowResult, WorkflowConfig, run_analysis_workflow
from app.data.loader import is_excel_file, list_excel_sheets, load_dataset
from app.llm.model import build_llm_config
from app.llm.presets import CUSTOM_PROVIDER, LLM_PROVIDER_PRESETS


router = APIRouter()
KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge_base"


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "data-insight-agent"}


@router.get("/llm/presets")
def get_llm_presets() -> dict[str, Any]:
    return {"providers": LLM_PROVIDER_PRESETS, "custom_provider": CUSTOM_PROVIDER}


@router.post("/datasets/sheets")
def get_excel_sheets(file: UploadFile = File(...)) -> dict[str, Any]:
    if not is_excel_file(file.filename or ""):
        raise HTTPException(status_code=400, detail="Sheet selection is only available for Excel files.")

    try:
        sheets = list_excel_sheets(file.file)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel sheets: {exc}") from exc

    return {"filename": file.filename, "sheets": sheets}


@router.post("/analysis")
def analyze_dataset(
    file: UploadFile = File(...),
    sheet_name: str | None = Form(default=None),
    language: str = Form(default="zh"),
    use_llm: bool = Form(default=False),
    api_key: str = Form(default=""),
    base_url: str = Form(default="https://api.deepseek.com/v1"),
    model: str = Form(default="deepseek-chat"),
) -> dict[str, Any]:
    df = _load_uploaded_dataset(file, sheet_name)
    workflow_result = run_analysis_workflow(
        df=df,
        config=WorkflowConfig(
            dataset_name=file.filename or "uploaded_dataset",
            language=_normalize_language(language),
            use_llm=use_llm,
            llm_config=build_llm_config(api_key=api_key, base_url=base_url, model=model),
        ),
    )
    return _workflow_result_payload(workflow_result)


@router.post("/qa")
def answer_question(
    file: UploadFile = File(...),
    question: str = Form(...),
    sheet_name: str | None = Form(default=None),
    language: str = Form(default="zh"),
    use_llm: bool = Form(default=False),
    api_key: str = Form(default=""),
    base_url: str = Form(default="https://api.deepseek.com/v1"),
    model: str = Form(default="deepseek-chat"),
) -> dict[str, Any]:
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    df = _load_uploaded_dataset(file, sheet_name)
    normalized_language = _normalize_language(language)
    llm_config = build_llm_config(api_key=api_key, base_url=base_url, model=model)
    workflow_result = run_analysis_workflow(
        df=df,
        config=WorkflowConfig(
            dataset_name=file.filename or "uploaded_dataset",
            language=normalized_language,
            use_llm=use_llm,
            llm_config=llm_config,
        ),
    )
    qa_result = answer_user_question(
        question=question,
        workflow_result=workflow_result,
        knowledge_dir=KNOWLEDGE_DIR,
        language=normalized_language,
        use_llm=use_llm,
        llm_config=llm_config,
    )

    return {
        "dataset_name": workflow_result.dataset_name,
        "question": question,
        "answer": qa_result.answer,
        "mode": qa_result.mode,
        "error": qa_result.error,
        "retrieved_knowledge": _dataframe_records(qa_result.retrieved_df),
    }


@router.post("/table-query")
def query_table(
    file: UploadFile = File(...),
    sql: str = Form(default=""),
    question: str = Form(default=""),
    sheet_name: str | None = Form(default=None),
    language: str = Form(default="zh"),
    use_llm: bool = Form(default=False),
    api_key: str = Form(default=""),
    base_url: str = Form(default="https://api.deepseek.com/v1"),
    model: str = Form(default="deepseek-chat"),
) -> dict[str, Any]:
    df = _load_uploaded_dataset(file, sheet_name)
    normalized_language = _normalize_language(language)
    llm_config = build_llm_config(api_key=api_key, base_url=base_url, model=model)

    workflow_result = run_analysis_workflow(
        df=df,
        config=WorkflowConfig(
            dataset_name=file.filename or "uploaded_dataset",
            language=normalized_language,
            use_llm=False,
            llm_config=None,
        ),
    )

    query_sql = sql.strip()
    if not query_sql:
        if not question.strip():
            raise HTTPException(status_code=400, detail="Either sql or question is required.")
        if not use_llm or llm_config is None:
            raise HTTPException(status_code=400, detail="Natural-language table query requires LLM configuration.")
        try:
            query_sql = generate_sql_from_question(
                question=question,
                df=df,
                profile_df=workflow_result.profile_df,
                llm_config=llm_config,
                language=normalized_language,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to generate SQL: {exc}") from exc

    result = run_table_query(df, query_sql)
    if result.error:
        raise HTTPException(status_code=400, detail=result.error)

    return {
        "dataset_name": workflow_result.dataset_name,
        "sql": result.sql,
        "rows": len(result.result_df),
        "truncated": result.truncated,
        "result": _dataframe_records(result.result_df),
    }


def _load_uploaded_dataset(file: UploadFile, sheet_name: str | None) -> pd.DataFrame:
    try:
        return load_dataset(file.file, file.filename or "", sheet_name=sheet_name or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to load dataset: {exc}") from exc


def _normalize_language(language: str) -> str:
    return "en" if language.lower().startswith("en") else "zh"


def _workflow_result_payload(result: AnalysisWorkflowResult) -> dict[str, Any]:
    return {
        "dataset_name": result.dataset_name,
        "dataset_summary": _clean_for_json(result.dataset_summary),
        "column_overview": _dataframe_records(result.column_overview),
        "field_profile": _dataframe_records(result.profile_df),
        "quality_issues": _dataframe_records(result.quality_df),
        "eda_recommendations": _dataframe_records(result.eda_df),
        "insights": {
            "mode": result.insight_result.mode,
            "summary": result.insight_result.summary,
            "items": _dataframe_records(result.insight_result.insights),
            "llm_output": result.insight_result.llm_output,
            "error": result.insight_result.llm_error,
        },
        "reports": {
            "markdown": result.markdown_report,
            "html": result.html_report,
        },
        "workflow_steps": [_clean_for_json(step.__dict__) for step in result.steps],
    }


def _dataframe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    clean_df = df.astype(object).where(pd.notna(df), None)
    return _clean_for_json(clean_df.to_dict("records"))


def _clean_for_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_for_json(item) for item in value]
    if isinstance(value, tuple):
        return [_clean_for_json(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if value is pd.NA:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    return value
