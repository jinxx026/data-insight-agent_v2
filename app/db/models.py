from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="analyst", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    datasets: Mapped[list["Dataset"]] = relationship(back_populates="owner")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sheet_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str] = mapped_column(String(30), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False)
    columns_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    preview_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    owner: Mapped[User] = relationship(back_populates="datasets")
    rows: Mapped[list["DatasetRow"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")
    reports: Mapped[list["AnalysisReport"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class DatasetRow(Base):
    __tablename__ = "dataset_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id"), index=True, nullable=False)
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    row_data: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)

    dataset: Mapped[Dataset] = relationship(back_populates="rows")


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id"), index=True, nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    dataset_summary: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    field_profile: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    quality_issues: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    eda_recommendations: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    insights: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    markdown_report: Mapped[str] = mapped_column(Text, nullable=False)
    html_report: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    dataset: Mapped[Dataset] = relationship(back_populates="reports")
