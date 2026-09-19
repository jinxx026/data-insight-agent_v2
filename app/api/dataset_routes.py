from __future__ import annotations

import os
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.agents.workflow_agent import WorkflowConfig, run_analysis_workflow
from app.auth.security import ensure_database_ready, get_current_user
from app.data.loader import load_dataset
from app.db.database import get_db
from app.db.models import AnalysisReport, Dataset, DatasetRow, User


router = APIRouter(prefix="/datasets", tags=["datasets"])
MAX_STORED_ROWS = int(os.getenv("MAX_STORED_ROWS", "50000"))


class DatasetSummaryResponse(BaseModel):
    id: str
    filename: str
    sheet_name: str | None
    file_type: str
    row_count: int
    column_count: int
    stored_row_count: int
    created_at: datetime


class DatasetDetailResponse(DatasetSummaryResponse):
    columns: list[str]
    preview: list[dict[str, Any]]
    latest_report_id: str | None
    latest_report_created_at: datetime | None


class DatasetRowsResponse(BaseModel):
    dataset_id: str
    offset: int
    limit: int
    rows: list[dict[str, Any]]


class UploadDatasetResponse(BaseModel):
    dataset: DatasetDetailResponse
    report_id: str
    stored_row_count: int
    storage_warning: str | None = None


@router.post("/upload", response_model=UploadDatasetResponse)
def upload_dataset_to_mysql(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    sheet_name: str | None = Form(default=None),
    language: str = Form(default="zh"),
) -> UploadDatasetResponse:
    ensure_database_ready()
    df = _load_uploaded_dataset(file, sheet_name)
    dataset_id = str(uuid.uuid4())

    dataset = Dataset(
        id=dataset_id,
        owner_id=current_user.id,
        filename=file.filename or "uploaded_dataset",
        sheet_name=sheet_name,
        file_type=Path(file.filename or "").suffix.lower().lstrip(".") or "unknown",
        row_count=int(len(df)),
        column_count=int(len(df.columns)),
        columns_json=[str(column) for column in df.columns],
        preview_json=_dataframe_records(df.head(20)),
    )
    db.add(dataset)

    stored_rows = min(len(df), MAX_STORED_ROWS)
    for row_index, row_data in enumerate(_dataframe_records(df.head(stored_rows))):
        db.add(DatasetRow(dataset_id=dataset_id, row_index=row_index, row_data=row_data))

    workflow_result = run_analysis_workflow(
        df=df,
        config=WorkflowConfig(
            dataset_name=file.filename or "uploaded_dataset",
            language=_normalize_language(language),
            use_llm=False,
            llm_config=None,
        ),
    )
    report = AnalysisReport(
        id=str(uuid.uuid4()),
        dataset_id=dataset_id,
        owner_id=current_user.id,
        dataset_summary=_clean_for_json(workflow_result.dataset_summary),
        field_profile=_dataframe_records(workflow_result.profile_df),
        quality_issues=_dataframe_records(workflow_result.quality_df),
        eda_recommendations=_dataframe_records(workflow_result.eda_df),
        insights={
            "mode": workflow_result.insight_result.mode,
            "summary": workflow_result.insight_result.summary,
            "items": _dataframe_records(workflow_result.insight_result.insights),
        },
        markdown_report=workflow_result.markdown_report,
        html_report=workflow_result.html_report,
    )
    db.add(report)
    db.commit()
    db.refresh(dataset)
    db.refresh(report)

    warning = None
    if len(df) > MAX_STORED_ROWS:
        warning = f"Only the first {MAX_STORED_ROWS} rows were stored in dataset_rows."

    return UploadDatasetResponse(
        dataset=_dataset_detail(dataset, stored_rows, report),
        report_id=report.id,
        stored_row_count=stored_rows,
        storage_warning=warning,
    )


@router.get("/history", response_model=list[DatasetSummaryResponse])
def list_my_datasets(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
) -> list[DatasetSummaryResponse]:
    datasets = db.scalars(
        select(Dataset)
        .where(Dataset.owner_id == current_user.id)
        .order_by(desc(Dataset.created_at))
        .limit(limit)
    ).all()
    return [_dataset_summary(dataset, _count_rows(db, dataset.id)) for dataset in datasets]


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset_detail(
    dataset_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DatasetDetailResponse:
    dataset = _get_owned_dataset(db, dataset_id, current_user)
    latest_report = _latest_report(db, dataset.id)
    return _dataset_detail(dataset, _count_rows(db, dataset.id), latest_report)


@router.get("/{dataset_id}/rows", response_model=DatasetRowsResponse)
def get_dataset_rows(
    dataset_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> DatasetRowsResponse:
    dataset = _get_owned_dataset(db, dataset_id, current_user)
    rows = db.scalars(
        select(DatasetRow)
        .where(DatasetRow.dataset_id == dataset.id)
        .order_by(DatasetRow.row_index)
        .offset(offset)
        .limit(limit)
    ).all()
    return DatasetRowsResponse(
        dataset_id=dataset.id,
        offset=offset,
        limit=limit,
        rows=[{"row_index": row.row_index, **row.row_data} for row in rows],
    )


def _load_uploaded_dataset(file: UploadFile, sheet_name: str | None) -> pd.DataFrame:
    try:
        return load_dataset(file.file, file.filename or "", sheet_name=sheet_name or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to load dataset: {exc}") from exc


def _get_owned_dataset(db: Session, dataset_id: str, current_user: User) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return dataset


def _latest_report(db: Session, dataset_id: str) -> AnalysisReport | None:
    return db.scalar(
        select(AnalysisReport)
        .where(AnalysisReport.dataset_id == dataset_id)
        .order_by(desc(AnalysisReport.created_at))
        .limit(1)
    )


def _count_rows(db: Session, dataset_id: str) -> int:
    return len(db.scalars(select(DatasetRow.id).where(DatasetRow.dataset_id == dataset_id)).all())


def _dataset_summary(dataset: Dataset, stored_row_count: int) -> DatasetSummaryResponse:
    return DatasetSummaryResponse(
        id=dataset.id,
        filename=dataset.filename,
        sheet_name=dataset.sheet_name,
        file_type=dataset.file_type,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        stored_row_count=stored_row_count,
        created_at=dataset.created_at,
    )


def _dataset_detail(dataset: Dataset, stored_row_count: int, latest_report: AnalysisReport | None) -> DatasetDetailResponse:
    summary = _dataset_summary(dataset, stored_row_count)
    return DatasetDetailResponse(
        **summary.model_dump(),
        columns=list(dataset.columns_json),
        preview=list(dataset.preview_json),
        latest_report_id=latest_report.id if latest_report is not None else None,
        latest_report_created_at=latest_report.created_at if latest_report is not None else None,
    )


def _normalize_language(language: str) -> str:
    return "en" if language.lower().startswith("en") else "zh"


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
