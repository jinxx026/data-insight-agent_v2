from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO
from xml.etree import ElementTree
from zipfile import ZipFile

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
EXCEL_EXTENSIONS = {".xlsx", ".xls"}


def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def is_excel_file(filename: str) -> bool:
    return get_file_extension(filename) in EXCEL_EXTENSIONS


def list_excel_sheets(file: BinaryIO) -> list[str]:
    """Return sheet names from an uploaded Excel file object."""
    file.seek(0)
    try:
        workbook = pd.ExcelFile(file)
    except ImportError as exc:
        if get_file_extension(getattr(file, "name", "") or "") == ".xls":
            raise ImportError(
                "Legacy .xls files require an Excel engine. Please save the file as .xlsx or install dependencies."
            ) from exc
        return _list_xlsx_sheets_without_openpyxl(file)
    file.seek(0)
    return workbook.sheet_names


def load_dataset(file: BinaryIO, filename: str, sheet_name: str | None = None) -> pd.DataFrame:
    """Load a CSV or Excel dataset from an uploaded file object."""
    extension = get_file_extension(filename)

    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{extension}'. Supported types: {supported}.")

    file.seek(0)
    if extension == ".csv":
        return _validate_dataset(pd.read_csv(file), filename, sheet_name)

    selected_sheet: str | int = sheet_name if sheet_name is not None else 0
    try:
        dataframe = pd.read_excel(file, sheet_name=selected_sheet)
    except ImportError as exc:
        if extension == ".xlsx":
            dataframe = _read_xlsx_without_openpyxl(file, sheet_name=sheet_name)
        else:
            raise ImportError(
                "Legacy .xls files require the xlrd package. Please save the file as .xlsx or install xlrd."
            ) from exc

    return _validate_dataset(dataframe, filename, sheet_name)


def _validate_dataset(
    dataframe: pd.DataFrame,
    filename: str,
    sheet_name: str | None,
) -> pd.DataFrame:
    """Reject files that cannot produce a meaningful analysis before the workflow runs."""
    location = f" sheet '{sheet_name}'" if sheet_name else ""
    if dataframe.shape[1] == 0:
        raise ValueError(f"'{filename}'{location} does not contain any columns.")
    if dataframe.shape[0] == 0:
        raise ValueError(f"'{filename}'{location} contains column headers but no data rows.")
    return dataframe


def _list_xlsx_sheets_without_openpyxl(file: BinaryIO) -> list[str]:
    workbook_bytes = _read_file_bytes(file)
    with ZipFile(BytesIO(workbook_bytes)) as archive:
        return [sheet["name"] for sheet in _read_xlsx_sheet_metadata(archive)]


def _read_xlsx_without_openpyxl(file: BinaryIO, sheet_name: str | None = None) -> pd.DataFrame:
    """Read a simple .xlsx workbook using only the Python standard library.

    This fallback keeps Streamlit Cloud uploads usable even when openpyxl was not
    installed by the hosting environment. It supports normal cell values and
    shared strings, which covers typical exported spreadsheet datasets.
    """
    workbook_bytes = _read_file_bytes(file)
    with ZipFile(BytesIO(workbook_bytes)) as archive:
        sheets = _read_xlsx_sheet_metadata(archive)
        if not sheets:
            return pd.DataFrame()

        selected_sheet = _select_xlsx_sheet(sheets, sheet_name)
        shared_strings = _read_xlsx_shared_strings(archive)
        rows = _read_xlsx_sheet_rows(archive, selected_sheet["path"], shared_strings)

    if not rows:
        return pd.DataFrame()

    width = max(len(row) for row in rows)
    normalized_rows = [row + [None] * (width - len(row)) for row in rows]
    raw_headers = normalized_rows[0]
    headers = _normalize_xlsx_headers(raw_headers, width)
    data_rows = normalized_rows[1:]
    return pd.DataFrame(data_rows, columns=headers)


def _read_file_bytes(file: BinaryIO) -> bytes:
    file.seek(0)
    workbook_bytes = file.read()
    file.seek(0)
    return workbook_bytes


def _read_xlsx_sheet_metadata(archive: ZipFile) -> list[dict[str, str]]:
    workbook_xml = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    rels_xml = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels_xml
        if "Id" in rel.attrib and "Target" in rel.attrib
    }

    sheets = []
    for sheet in workbook_xml.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet"):
        relation_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = rel_targets.get(relation_id or "")
        if not target:
            continue
        path = target.lstrip("/")
        if not path.startswith("xl/"):
            path = f"xl/{path}"
        sheets.append({"name": sheet.attrib.get("name", "Sheet"), "path": path})
    return sheets


def _select_xlsx_sheet(sheets: list[dict[str, str]], sheet_name: str | None) -> dict[str, str]:
    if not sheet_name:
        return sheets[0]
    for sheet in sheets:
        if sheet["name"] == sheet_name:
            return sheet
    available = ", ".join(sheet["name"] for sheet in sheets)
    raise ValueError(f"Sheet '{sheet_name}' was not found. Available sheets: {available}.")


def _read_xlsx_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    shared_xml = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    strings = []
    for item in shared_xml.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
        parts = [
            text.text or ""
            for text in item.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
        ]
        strings.append("".join(parts))
    return strings


def _read_xlsx_sheet_rows(archive: ZipFile, sheet_path: str, shared_strings: list[str]) -> list[list[object]]:
    sheet_xml = ElementTree.fromstring(archive.read(sheet_path))
    rows = []
    for row in sheet_xml.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
        values: list[object] = []
        for cell in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
            cell_index = _xlsx_column_index(cell.attrib.get("r", ""))
            while len(values) < cell_index:
                values.append(None)
            values.append(_xlsx_cell_value(cell, shared_strings))
        rows.append(values)
    return rows


def _xlsx_column_index(cell_reference: str) -> int:
    letters = "".join(character for character in cell_reference if character.isalpha())
    index = 0
    for character in letters:
        index = index * 26 + ord(character.upper()) - ord("A") + 1
    return max(index - 1, 0)


def _xlsx_cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> object:
    cell_type = cell.attrib.get("t")
    value_element = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
    if cell_type == "inlineStr":
        return "".join(
            text.text or ""
            for text in cell.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
        )
    if value_element is None or value_element.text is None:
        return None
    raw_value = value_element.text
    if cell_type == "s":
        shared_index = int(raw_value)
        return shared_strings[shared_index] if shared_index < len(shared_strings) else raw_value
    if cell_type == "b":
        return raw_value == "1"
    return _coerce_xlsx_scalar(raw_value)


def _coerce_xlsx_scalar(value: str) -> object:
    try:
        number = float(value)
    except ValueError:
        return value
    if number.is_integer():
        return int(number)
    return number


def _normalize_xlsx_headers(raw_headers: list[object], width: int) -> list[str]:
    headers = []
    seen: dict[str, int] = {}
    for index in range(width):
        header = raw_headers[index] if index < len(raw_headers) else None
        name = str(header).strip() if header is not None and str(header).strip() else f"column_{index + 1}"
        count = seen.get(name, 0)
        seen[name] = count + 1
        headers.append(name if count == 0 else f"{name}_{count + 1}")
    return headers


def build_dataset_summary(df: pd.DataFrame) -> dict[str, object]:
    """Return lightweight metadata for the first Streamlit MVP screen."""
    missing_cells = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "missing_cells": missing_cells,
        "duplicate_rows": duplicate_rows,
        "memory_usage_mb": round(float(df.memory_usage(deep=True).sum()) / 1024 / 1024, 3),
    }


def build_column_overview(df: pd.DataFrame) -> pd.DataFrame:
    """Create a compact per-column overview for the upload preview."""
    row_count = max(len(df), 1)

    overview = pd.DataFrame(
        {
            "column": df.columns,
            "pandas_dtype": [str(dtype) for dtype in df.dtypes],
            "missing_count": df.isna().sum().astype(int).values,
            "missing_rate": (df.isna().sum() / row_count).round(4).values,
            "unique_count": df.nunique(dropna=True).astype(int).values,
            "unique_rate": (df.nunique(dropna=True) / row_count).round(4).values,
        }
    )

    return overview
