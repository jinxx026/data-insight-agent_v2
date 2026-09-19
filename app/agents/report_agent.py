from __future__ import annotations

from datetime import datetime
from html import escape
import re

import pandas as pd

from app.agents.insight_agent import InsightResult
from app.data.quality import build_quality_summary
from app.ui.i18n import localize_dataframe


def generate_markdown_report(
    df: pd.DataFrame,
    dataset_name: str,
    dataset_summary: dict[str, object],
    profile_df: pd.DataFrame,
    quality_df: pd.DataFrame,
    eda_df: pd.DataFrame,
    insight_result: InsightResult,
    language: str,
) -> str:
    """Generate a Markdown analysis report from structured analysis outputs."""
    if language == "zh":
        return _generate_zh_report(
            df=df,
            dataset_name=dataset_name,
            dataset_summary=dataset_summary,
            profile_df=profile_df,
            quality_df=quality_df,
            eda_df=eda_df,
            insight_result=insight_result,
        )

    return _generate_en_report(
        df=df,
        dataset_name=dataset_name,
        dataset_summary=dataset_summary,
        profile_df=profile_df,
        quality_df=quality_df,
        eda_df=eda_df,
        insight_result=insight_result,
    )


def generate_html_report(markdown_report: str, title: str = "DataInsight Agent Report") -> str:
    """Convert the generated Markdown report into a standalone HTML report."""
    body = _markdown_to_html(markdown_report)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{
      margin: 0;
      background: #f6f7f9;
      color: #1f2937;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      line-height: 1.6;
    }}
    main {{
      max-width: 1080px;
      margin: 32px auto;
      padding: 40px;
      background: white;
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
    }}
    h1, h2, h3 {{
      color: #111827;
      line-height: 1.25;
    }}
    h1 {{
      margin-top: 0;
      border-bottom: 2px solid #e5e7eb;
      padding-bottom: 16px;
    }}
    h2 {{
      margin-top: 32px;
      border-bottom: 1px solid #e5e7eb;
      padding-bottom: 8px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 16px 0 24px;
      font-size: 14px;
    }}
    th, td {{
      border: 1px solid #e5e7eb;
      padding: 8px 10px;
      vertical-align: top;
    }}
    th {{
      background: #f3f4f6;
      font-weight: 650;
      text-align: left;
    }}
    code {{
      background: #f3f4f6;
      padding: 2px 5px;
      border-radius: 4px;
    }}
    ul {{
      padding-left: 24px;
    }}
  </style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""


def _generate_zh_report(
    df: pd.DataFrame,
    dataset_name: str,
    dataset_summary: dict[str, object],
    profile_df: pd.DataFrame,
    quality_df: pd.DataFrame,
    eda_df: pd.DataFrame,
    insight_result: InsightResult,
) -> str:
    quality_summary = build_quality_summary(df, quality_df)
    target_columns = profile_df.loc[
        profile_df["smart_type"] == "target_variable", "column"
    ].tolist()
    target_text = "、".join(target_columns) if target_columns else "暂未检测到"

    sections = [
        "# DataInsight Agent 数据分析报告",
        "",
        f"- 数据集：{dataset_name}",
        f"- 生成时间：{_now_text()}",
        f"- 报告模式：{_mode_label(insight_result.mode, 'zh')}",
        "",
        "## 1. 数据集概览",
        "",
        f"- 行数：{dataset_summary['rows']:,}",
        f"- 列数：{dataset_summary['columns']:,}",
        f"- 缺失单元格：{dataset_summary['missing_cells']:,}",
        f"- 重复行：{dataset_summary['duplicate_rows']:,}",
        f"- 内存占用：{dataset_summary['memory_usage_mb']} MB",
        f"- 目标变量：{target_text}",
        "",
        "## 2. 智能字段类型识别",
        "",
        _df_to_markdown(
            localize_dataframe(
                profile_df[
                    [
                        "column",
                        "pandas_dtype",
                        "smart_type",
                        "analysis_role",
                        "missing_rate",
                        "unique_count",
                        "unique_rate",
                    ]
                ],
                "zh",
            )
        ),
        "",
        "## 3. 数据质量问题",
        "",
        f"- 质量问题总数：{quality_summary['quality_issues']}",
        f"- 高严重程度问题：{quality_summary['high_severity']}",
        f"- 有缺失值的字段数：{quality_summary['columns_with_missing']}",
        f"- 重复行数：{quality_summary['duplicate_rows']}",
        "",
    ]

    if quality_df.empty:
        sections.extend(["当前规则没有检测到明显的数据质量问题。", ""])
    else:
        sections.extend(
            [
                _df_to_markdown(
                    localize_dataframe(
                        quality_df[
                            [
                                "severity",
                                "issue_type",
                                "column",
                                "metric",
                                "details",
                                "recommendation",
                            ]
                        ],
                        "zh",
                    )
                ),
                "",
            ]
        )

    sections.extend(
        [
            "## 4. 自动 EDA 路线",
            "",
            _df_to_markdown(
                localize_dataframe(
                    eda_df[["analysis_type", "chart_type", "title", "columns", "rationale"]],
                    "zh",
                )
                if not eda_df.empty
                else pd.DataFrame(columns=["分析类型", "图表类型", "标题", "使用字段", "推荐原因"])
            ),
            "",
            "## 5. 关键洞察",
            "",
            insight_result.summary,
            "",
            _df_to_markdown(localize_dataframe(insight_result.insights, "zh")),
            "",
        ]
    )

    if insight_result.llm_output:
        sections.extend(["## 6. LLM 生成报告", "", insight_result.llm_output, ""])

    sections.extend(
        [
            "## 7. 建议的下一步",
            "",
            "- 优先处理高严重程度的数据质量问题。",
            "- 结合目标变量查看分组差异，尤其关注流失率、欺诈率或转化率等业务标签。",
            "- 对异常值和高基数字段进行人工复核，再决定是否清洗、分箱或排除。",
            "- 在进入建模前，确认目标变量定义、样本时间范围和数据泄漏风险。",
        ]
    )

    return "\n".join(sections)


def _generate_en_report(
    df: pd.DataFrame,
    dataset_name: str,
    dataset_summary: dict[str, object],
    profile_df: pd.DataFrame,
    quality_df: pd.DataFrame,
    eda_df: pd.DataFrame,
    insight_result: InsightResult,
) -> str:
    quality_summary = build_quality_summary(df, quality_df)
    target_columns = profile_df.loc[
        profile_df["smart_type"] == "target_variable", "column"
    ].tolist()
    target_text = ", ".join(target_columns) if target_columns else "not detected"

    sections = [
        "# DataInsight Agent Analysis Report",
        "",
        f"- Dataset: {dataset_name}",
        f"- Generated at: {_now_text()}",
        f"- Insight mode: {_mode_label(insight_result.mode, 'en')}",
        "",
        "## 1. Dataset Overview",
        "",
        f"- Rows: {dataset_summary['rows']:,}",
        f"- Columns: {dataset_summary['columns']:,}",
        f"- Missing cells: {dataset_summary['missing_cells']:,}",
        f"- Duplicate rows: {dataset_summary['duplicate_rows']:,}",
        f"- Memory usage: {dataset_summary['memory_usage_mb']} MB",
        f"- Target variable: {target_text}",
        "",
        "## 2. Smart Field Type Detection",
        "",
        _df_to_markdown(
            profile_df[
                [
                    "column",
                    "pandas_dtype",
                    "smart_type",
                    "analysis_role",
                    "missing_rate",
                    "unique_count",
                    "unique_rate",
                ]
            ]
        ),
        "",
        "## 3. Data Quality Issues",
        "",
        f"- Quality issues: {quality_summary['quality_issues']}",
        f"- High severity: {quality_summary['high_severity']}",
        f"- Columns with missing values: {quality_summary['columns_with_missing']}",
        f"- Duplicate rows: {quality_summary['duplicate_rows']}",
        "",
    ]

    if quality_df.empty:
        sections.extend(["No obvious data quality issues were detected by the current rule set.", ""])
    else:
        sections.extend(
            [
                _df_to_markdown(
                    quality_df[
                        [
                            "severity",
                            "issue_type",
                            "column",
                            "metric",
                            "details",
                            "recommendation",
                        ]
                    ]
                ),
                "",
            ]
        )

    sections.extend(
        [
            "## 4. Automatic EDA Plan",
            "",
            _df_to_markdown(
                eda_df[["analysis_type", "chart_type", "title", "columns", "rationale"]]
                if not eda_df.empty
                else pd.DataFrame(columns=["analysis_type", "chart_type", "title", "columns", "rationale"])
            ),
            "",
            "## 5. Key Insights",
            "",
            insight_result.summary,
            "",
            _df_to_markdown(insight_result.insights),
            "",
        ]
    )

    if insight_result.llm_output:
        sections.extend(["## 6. LLM-Generated Report", "", insight_result.llm_output, ""])

    sections.extend(
        [
            "## 7. Recommended Next Steps",
            "",
            "- Resolve high-severity data quality issues first.",
            "- Review target-related segment differences such as churn, fraud, or conversion rates.",
            "- Manually inspect outliers and high-cardinality fields before cleaning, binning, or excluding them.",
            "- Before modeling, confirm target definition, sample time window, and potential leakage risks.",
        ]
    )

    return "\n".join(sections)


def _df_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No records._"

    display_df = df.copy()
    for column in display_df.columns:
        display_df[column] = display_df[column].map(_format_cell)

    headers = [str(column) for column in display_df.columns]
    rows = [
        [_escape_markdown_table_cell(value) for value in row]
        for row in display_df.astype(str).values.tolist()
    ]
    header_row = "| " + " | ".join(headers) + " |"
    separator_row = "| " + " | ".join("---" for _ in headers) + " |"
    body_rows = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_row, separator_row, *body_rows])


def _format_cell(value: object) -> object:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if pd.isna(value):
        return ""
    return value


def _escape_markdown_table_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _mode_label(mode: str, language: str) -> str:
    labels = {
        "zh": {
            "local": "本地规则",
            "local_fallback": "本地规则（LLM 回退）",
            "llm": "LLM",
        },
        "en": {
            "local": "Local rules",
            "local_fallback": "Local rules with LLM fallback",
            "llm": "LLM",
        },
    }
    return labels[language].get(mode, mode)


def _markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    html_lines: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        if stripped.startswith("|") and _looks_like_markdown_table(lines, index):
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            html_lines.append(_table_to_html(table_lines))
            continue

        if stripped.startswith("# "):
            html_lines.append(f"<h1>{_inline_markdown(stripped[2:].strip())}</h1>")
        elif stripped.startswith("## "):
            html_lines.append(f"<h2>{_inline_markdown(stripped[3:].strip())}</h2>")
        elif stripped.startswith("### "):
            html_lines.append(f"<h3>{_inline_markdown(stripped[4:].strip())}</h3>")
        elif stripped.startswith("- "):
            items = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                items.append(lines[index].strip()[2:].strip())
                index += 1
            html_lines.append("<ul>")
            html_lines.extend(f"<li>{_inline_markdown(item)}</li>" for item in items)
            html_lines.append("</ul>")
            continue
        else:
            html_lines.append(f"<p>{_inline_markdown(stripped)}</p>")

        index += 1

    return "\n".join(html_lines)


def _looks_like_markdown_table(lines: list[str], index: int) -> bool:
    return (
        index + 1 < len(lines)
        and lines[index].strip().startswith("|")
        and re.fullmatch(r"\|\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?", lines[index + 1].strip())
        is not None
    )


def _table_to_html(table_lines: list[str]) -> str:
    headers = _split_table_row(table_lines[0])
    body_rows = [_split_table_row(row) for row in table_lines[2:]]

    html = ["<table>", "<thead><tr>"]
    html.extend(f"<th>{_inline_markdown(header)}</th>" for header in headers)
    html.append("</tr></thead>")
    html.append("<tbody>")
    for row in body_rows:
        html.append("<tr>")
        padded_row = row + [""] * (len(headers) - len(row))
        html.extend(f"<td>{_inline_markdown(cell)}</td>" for cell in padded_row[: len(headers)])
        html.append("</tr>")
    html.append("</tbody></table>")
    return "\n".join(html)


def _split_table_row(row: str) -> list[str]:
    row = row.strip().strip("|")
    return [cell.strip().replace("\\|", "|") for cell in row.split("|")]


def _inline_markdown(text: str) -> str:
    escaped = escape(str(text))
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped
