from __future__ import annotations

import sys
from pathlib import Path
import re

import altair as alt
import pandas as pd
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.agents.workflow_agent import (
    WorkflowConfig,
    run_analysis_workflow,
    workflow_steps_to_dataframe,
)
from app.agents.qa_agent import answer_user_question
from app.agents.sft_dataset_agent import build_sft_dataset
from app.agents.table_query_agent import generate_sql_from_question, run_table_query
from app.data.loader import (
    is_excel_file,
    list_excel_sheets,
    load_dataset,
)
from app.data.eda import (
    build_category_counts,
    build_correlation_pairs,
    build_target_by_category,
    build_time_trend,
)
from app.data.profiler import summarize_feature_types
from app.data.quality import (
    build_quality_summary,
    summarize_issue_types,
)
from app.llm.model import build_llm_config
from app.llm.presets import CUSTOM_PROVIDER, LLM_PROVIDER_PRESETS
from app.ui.i18n import LANGUAGE_OPTIONS, localize_dataframe, t


st.set_page_config(
    page_title="DataInsight Agent",
    page_icon="DA",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.html((ROOT_DIR / "frontend" / "styles.css").read_text(encoding="utf-8"))


def load_llm_secret_defaults() -> dict[str, str]:
    try:
        llm_secrets = st.secrets.get("llm", {})
    except Exception:
        llm_secrets = {}

    return {
        "provider": str(llm_secrets.get("provider", "DeepSeek")),
        "api_key": str(llm_secrets.get("api_key", "")),
        "base_url": str(llm_secrets.get("base_url", "https://api.deepseek.com/v1")),
        "model": str(llm_secrets.get("model", "deepseek-chat")),
    }


llm_secret_defaults = load_llm_secret_defaults()

language = st.sidebar.selectbox(
    "Language / 语言",
    options=list(LANGUAGE_OPTIONS.keys()),
    format_func=lambda option: LANGUAGE_OPTIONS[option],
)
insight_mode = st.sidebar.selectbox(
    t(language, "insight_mode"),
    options=["local", "llm"],
    format_func=lambda option: (
        t(language, "insight_mode_local")
        if option == "local"
        else t(language, "insight_mode_llm")
    ),
)
runtime_llm_config = None
if insight_mode == "llm":
    st.sidebar.caption(t(language, "llm_config_help"))
    llm_api_key = st.sidebar.text_input(
        t(language, "llm_api_key"),
        type="password",
        placeholder="sk-...",
        value=llm_secret_defaults["api_key"],
    )
    provider_options = [*LLM_PROVIDER_PRESETS.keys(), CUSTOM_PROVIDER]
    default_provider = (
        llm_secret_defaults["provider"]
        if llm_secret_defaults["provider"] in provider_options
        else CUSTOM_PROVIDER
    )
    llm_provider = st.sidebar.selectbox(
        t(language, "llm_provider"),
        options=provider_options,
        index=provider_options.index(default_provider),
    )
    if llm_provider == CUSTOM_PROVIDER:
        llm_base_url = st.sidebar.text_input(
            t(language, "llm_custom_base_url"),
            value=llm_secret_defaults["base_url"],
        )
        llm_model = st.sidebar.text_input(
            t(language, "llm_custom_model"),
            value=llm_secret_defaults["model"],
        )
    else:
        provider_preset = LLM_PROVIDER_PRESETS[llm_provider]
        default_base_url = (
            llm_secret_defaults["base_url"]
            if llm_secret_defaults["base_url"] in provider_preset["base_urls"]
            else provider_preset["base_urls"][0]
        )
        default_model = (
            llm_secret_defaults["model"]
            if llm_secret_defaults["model"] in provider_preset["models"]
            else provider_preset["models"][0]
        )
        llm_base_url = st.sidebar.selectbox(
            t(language, "llm_base_url"),
            options=provider_preset["base_urls"],
            index=provider_preset["base_urls"].index(default_base_url),
        )
        llm_model = st.sidebar.selectbox(
            t(language, "llm_model"),
            options=provider_preset["models"],
            index=provider_preset["models"].index(default_model),
        )
    runtime_llm_config = build_llm_config(
        api_key=llm_api_key,
        base_url=llm_base_url,
        model=llm_model,
    )

page_labels = {
    "home": ("首页", "Home"),
    "quality": ("概览与质量", "Overview & Quality"),
    "eda": ("EDA 与图表", "EDA & Charts"),
    "insights": ("洞察与下载", "Insights & Downloads"),
    "qa": ("知识问答", "Knowledge Q&A"),
    "sql": ("SQL 表格查询", "SQL Query"),
    "sft": ("SFT 数据集", "SFT Dataset"),
}
with st.container(key="masthead"):
    brand, navigation = st.columns([1, 4], vertical_alignment="center")
    with brand:
        st.html('<div class="brand"><span class="brand-mark">D/</span>'
                '<span>DataInsight<small>AGENT WORKSPACE</small></span></div>')
    with navigation:
        page = st.radio(
            "功能导航" if language == "zh" else "Navigation",
            list(page_labels),
            format_func=lambda value: page_labels[value][0 if language == "zh" else 1],
            horizontal=True,
            key="active_page",
            label_visibility="collapsed",
        )

st.html('<div class="workspace-label">DATA WORKSPACE <span>/</span> '
        + page_labels[page][0 if language == "zh" else 1] + '</div>')
st.title(("数据工作台" if language == "zh" else "Data workspace")
         if page == "home" else page_labels[page][0 if language == "zh" else 1])


def render_summary(summary: dict[str, object]) -> None:
    metric_columns = st.columns(5)
    metric_columns[0].metric(t(language, "rows"), f"{summary['rows']:,}")
    metric_columns[1].metric(t(language, "columns"), f"{summary['columns']:,}")
    metric_columns[2].metric(t(language, "missing_cells"), f"{summary['missing_cells']:,}")
    metric_columns[3].metric(t(language, "duplicate_rows"), f"{summary['duplicate_rows']:,}")
    metric_columns[4].metric(t(language, "memory"), f"{summary['memory_usage_mb']} MB")


def render_profiler(profile_df: pd.DataFrame) -> None:
    st.subheader(t(language, "smart_field_detection"))

    type_summary = summarize_feature_types(profile_df)
    if not type_summary.empty:
        st.dataframe(localize_dataframe(type_summary, language), use_container_width=True, hide_index=True)

    target_columns = profile_df.loc[
        profile_df["smart_type"] == "target_variable", "column"
    ].tolist()
    if target_columns:
        st.success(t(language, "detected_target", columns=", ".join(target_columns)))
    else:
        st.warning(t(language, "no_target"))

    visible_columns = [
        "column",
        "pandas_dtype",
        "smart_type",
        "analysis_role",
        "reason",
        "missing_rate",
        "unique_count",
        "unique_rate",
        "example_values",
    ]
    st.dataframe(
        localize_dataframe(profile_df[visible_columns], language),
        use_container_width=True,
        hide_index=True,
    )


def render_quality_report(df: pd.DataFrame, quality_df: pd.DataFrame) -> None:
    st.subheader(t(language, "quality_report"))

    quality_summary = build_quality_summary(df, quality_df)
    metric_columns = st.columns(4)
    metric_columns[0].metric(t(language, "quality_issues"), f"{quality_summary['quality_issues']:,}")
    metric_columns[1].metric(t(language, "high_severity"), f"{quality_summary['high_severity']:,}")
    metric_columns[2].metric(t(language, "columns_with_missing"), f"{quality_summary['columns_with_missing']:,}")
    metric_columns[3].metric(t(language, "duplicate_rows"), f"{quality_summary['duplicate_rows']:,}")

    if quality_df.empty:
        st.success(t(language, "no_quality_issues"))
        return

    issue_summary = summarize_issue_types(quality_df)
    st.dataframe(localize_dataframe(issue_summary, language), use_container_width=True, hide_index=True)

    st.caption(t(language, "severity_caption"))
    st.dataframe(localize_dataframe(quality_df, language), use_container_width=True, hide_index=True)


def render_eda_report(df: pd.DataFrame, eda_df: pd.DataFrame) -> None:
    st.subheader(t(language, "eda_report"))

    if eda_df.empty:
        st.warning(t(language, "no_eda_recommendations"))
        return

    display_eda_df = eda_df.copy()
    if language == "zh":
        localized_titles = []
        localized_rationales = []
        for recommendation in eda_df.to_dict("records"):
            localized_titles.append(_localized_recommendation_title(recommendation))
            localized_rationales.append(_localized_recommendation_rationale(recommendation))
        display_eda_df["title"] = localized_titles
        display_eda_df["rationale"] = localized_rationales

    st.dataframe(localize_dataframe(display_eda_df, language), use_container_width=True, hide_index=True)

    for recommendation in eda_df.to_dict("records"):
        with st.container(border=True):
            st.markdown(f"**{_localized_recommendation_title(recommendation)}**")
            st.caption(_localized_recommendation_rationale(recommendation))
            _render_recommended_chart(df, recommendation)


def _render_recommended_chart(df: pd.DataFrame, recommendation: dict[str, object]) -> None:
    analysis_type = str(recommendation["analysis_type"])
    columns = recommendation["columns"]

    if analysis_type == "numeric_distribution":
        column = columns[0]
        chart_df = pd.DataFrame({"value": pd.to_numeric(df[column], errors="coerce")}).dropna()
        if chart_df.empty:
            st.info(t(language, "not_enough_data_for_chart"))
            return

        chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(
                x=alt.X("value:Q", bin=alt.Bin(maxbins=30), title=column),
                y=alt.Y("count():Q", title=t(language, "count")),
                tooltip=[alt.Tooltip("value:Q", bin=True, title=column), alt.Tooltip("count():Q")],
            )
            .properties(height=260)
        )
        _safe_altair_chart(chart)
        return

    if analysis_type in {"category_distribution", "target_distribution"}:
        column = columns[0]
        chart_df = build_category_counts(df, column).rename(columns={column: "category"})
        if chart_df.empty:
            st.info(t(language, "not_enough_data_for_chart"))
            return

        chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(
                x=alt.X("count:Q", title=t(language, "count")),
                y=alt.Y("category:N", sort="-x", title=column),
                tooltip=[alt.Tooltip("category:N", title=column), alt.Tooltip("count:Q")],
            )
            .properties(height=max(260, min(520, len(chart_df) * 28)))
        )
        _safe_altair_chart(chart)
        return

    if analysis_type == "time_trend":
        column = columns[0]
        chart_df = build_time_trend(df, column).rename(columns={column: "date"})
        if chart_df.empty:
            st.info(t(language, "no_valid_datetime_values"))
            return

        chart = (
            alt.Chart(chart_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("date:T", title=column),
                y=alt.Y("count:Q", title=t(language, "count")),
                tooltip=[alt.Tooltip("date:T", title=column), alt.Tooltip("count:Q")],
            )
            .properties(height=260)
        )
        _safe_altair_chart(chart)
        return

    if analysis_type == "target_by_category":
        category_column, target_column = columns
        chart_df = build_target_by_category(df, category_column, target_column)
        if chart_df.empty:
            st.info(t(language, "not_enough_data_for_chart"))
            return

        if "target_rate" in chart_df.columns:
            chart_df = chart_df.rename(columns={category_column: "category"})
            chart = (
                alt.Chart(chart_df)
                .mark_bar()
                .encode(
                    x=alt.X("category:N", sort="-y", title=category_column),
                    y=alt.Y("target_rate:Q", title=t(language, "target_rate"), axis=alt.Axis(format="%")),
                    tooltip=[
                        alt.Tooltip("category:N", title=category_column),
                        alt.Tooltip("count:Q"),
                        alt.Tooltip("target_rate:Q", format=".1%"),
                    ],
                )
                .properties(height=300)
            )
        else:
            chart_df = chart_df.rename(columns={category_column: "category", target_column: "target"})
            chart = (
                alt.Chart(chart_df)
                .mark_bar()
                .encode(
                    x=alt.X("category:N", title=category_column),
                    y=alt.Y("count:Q", title=t(language, "count")),
                    color=alt.Color("target:N", title=target_column),
                    tooltip=[
                        alt.Tooltip("category:N", title=category_column),
                        alt.Tooltip("target:N", title=target_column),
                        alt.Tooltip("count:Q"),
                    ],
                )
                .properties(height=300)
            )
        _safe_altair_chart(chart)
        return

    if analysis_type == "correlation_heatmap":
        chart_df = build_correlation_pairs(df, columns)
        if chart_df.empty:
            st.info(t(language, "not_enough_data_for_chart"))
            return

        chart = (
            alt.Chart(chart_df)
            .mark_rect()
            .encode(
                x=alt.X("feature_x:N", title=""),
                y=alt.Y("feature_y:N", title=""),
                color=alt.Color("correlation:Q", scale=alt.Scale(scheme="redblue", domain=[-1, 1])),
                tooltip=["feature_x", "feature_y", "correlation"],
            )
            .properties(height=340)
        )
        _safe_altair_chart(chart)
        return

    st.info(t(language, "unsupported_chart"))


def _safe_altair_chart(chart: alt.Chart) -> None:
    try:
        st.altair_chart(chart, use_container_width=True)
    except ValueError as exc:
        st.warning(_ui_text("chart_render_error"))
        st.caption(str(exc))


def _localized_recommendation_title(recommendation: dict[str, object]) -> str:
    if language == "en":
        return str(recommendation["title"])

    analysis_type = str(recommendation["analysis_type"])
    columns = recommendation["columns"]
    if analysis_type == "numeric_distribution":
        return f"{columns[0]} 的数值分布"
    if analysis_type == "category_distribution":
        return f"{columns[0]} 的主要类别"
    if analysis_type == "time_trend":
        return f"按 {columns[0]} 的记录趋势"
    if analysis_type == "target_distribution":
        return f"{columns[0]} 的目标变量分布"
    if analysis_type == "target_by_category":
        return f"{columns[1]} 按 {columns[0]} 分组对比"
    if analysis_type == "correlation_heatmap":
        return "数值特征相关性"
    return str(recommendation["title"])


def _localized_recommendation_rationale(recommendation: dict[str, object]) -> str:
    if language == "en":
        return str(recommendation["rationale"])

    rationales = {
        "numeric_distribution": "数值特征需要检查分布范围、偏态以及是否存在不寻常取值。",
        "category_distribution": "类别特征需要检查是否存在占比很高的主导类别或长尾类别。",
        "time_trend": "时间字段可以用于趋势分析和季节性检查。",
        "target_distribution": "目标变量在建模前需要检查类别是否平衡。",
        "target_by_category": "按类别对比目标变量，可以发现不同用户分组或业务分组的差异。",
        "correlation_heatmap": "相关性分析可以发现数值特征之间的关系和潜在冗余。",
    }
    return rationales.get(str(recommendation["analysis_type"]), str(recommendation["rationale"]))


def render_insight_report(result: object) -> None:
    st.subheader(t(language, "insight_report"))

    st.info(result.summary)
    if result.llm_error:
        st.warning(result.llm_error)

    st.dataframe(localize_dataframe(result.insights, language), use_container_width=True, hide_index=True)

    if result.llm_output:
        st.markdown(f"### {t(language, 'llm_report')}")
        st.markdown(result.llm_output)


def render_markdown_report(
    dataset_name: str,
    markdown_report: str,
    html_report: str,
) -> None:
    st.subheader(t(language, "report_section"))

    download_columns = st.columns(2)
    download_columns[0].download_button(
        label=t(language, "download_report"),
        data=markdown_report.encode("utf-8"),
        file_name=f"{_slugify_filename(dataset_name)}_analysis_report.md",
        mime="text/markdown",
        use_container_width=True,
    )
    download_columns[1].download_button(
        label=t(language, "download_html_report"),
        data=html_report.encode("utf-8"),
        file_name=f"{_slugify_filename(dataset_name)}_analysis_report.html",
        mime="text/html",
        use_container_width=True,
    )

    with st.expander(t(language, "report_preview"), expanded=False):
        st.markdown(markdown_report)


def render_workflow_steps(workflow_result: object) -> None:
    st.subheader(t(language, "workflow_steps"))
    st.dataframe(
        localize_dataframe(workflow_steps_to_dataframe(workflow_result.steps), language),
        use_container_width=True,
        hide_index=True,
    )


def render_rag_qa(workflow_result: object) -> None:
    st.subheader(t(language, "rag_qa"))
    question = st.text_input(
        t(language, "rag_question"),
        placeholder=t(language, "rag_question_placeholder"),
    )
    if not question.strip():
        return

    qa_result = answer_user_question(
        question=question,
        workflow_result=workflow_result,
        knowledge_dir=ROOT_DIR / "knowledge_base",
        language=language,
        use_llm=insight_mode == "llm",
        llm_config=runtime_llm_config,
    )
    if qa_result.error:
        st.warning(qa_result.error)
    st.markdown(f"### {t(language, 'rag_answer')}")
    st.markdown(qa_result.answer)

    with st.expander(t(language, "rag_sources"), expanded=False):
        st.dataframe(localize_dataframe(qa_result.retrieved_df, language), use_container_width=True, hide_index=True)


def render_table_query_agent(df: pd.DataFrame, workflow_result: object) -> None:
    st.subheader(_ui_text("table_query_title"))
    st.caption(_ui_text("table_query_caption"))

    mode = st.radio(
        _ui_text("table_query_mode"),
        options=["manual_sql", "natural_language"],
        format_func=lambda option: _ui_text(option),
        horizontal=True,
    )

    sql = ""
    if mode == "manual_sql":
        sql = st.text_area(
            _ui_text("manual_sql_label"),
            value="SELECT * FROM dataset LIMIT 20",
            height=140,
            help=_ui_text("sql_help"),
        )
    else:
        question = st.text_input(
            _ui_text("nl_query_label"),
            placeholder=_ui_text("nl_query_placeholder"),
        )
        if st.button(_ui_text("generate_sql_button"), use_container_width=True):
            if not question.strip():
                st.warning(_ui_text("empty_question_warning"))
            elif runtime_llm_config is None:
                st.warning(_ui_text("llm_required_warning"))
            else:
                try:
                    st.session_state["generated_table_sql"] = generate_sql_from_question(
                        question=question,
                        df=df,
                        profile_df=workflow_result.profile_df,
                        llm_config=runtime_llm_config,
                        language=language,
                    )
                except Exception as exc:
                    st.error(_ui_text("generate_sql_error", error=exc))

        sql = st.text_area(
            _ui_text("generated_sql_label"),
            value=st.session_state.get("generated_table_sql", ""),
            height=140,
            help=_ui_text("sql_help"),
        )

    if st.button(_ui_text("run_sql_button"), use_container_width=True):
        query_result = run_table_query(df, sql)
        if query_result.error:
            st.error(_ui_text("sql_error", error=query_result.error))
            return

        st.code(query_result.sql, language="sql")
        if query_result.truncated:
            st.warning(_ui_text("result_truncated"))
        st.dataframe(query_result.result_df, use_container_width=True, hide_index=True)
        st.download_button(
            label=_ui_text("download_query_result"),
            data=query_result.result_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{_slugify_filename(dataset_name)}_query_result.csv",
            mime="text/csv",
            use_container_width=True,
        )


def render_sft_dataset_builder(workflow_result: object) -> None:
    st.subheader(_ui_text("sft_title"))
    st.caption(_ui_text("sft_caption"))

    sft_result = build_sft_dataset(workflow_result=workflow_result, language=language)
    st.metric(_ui_text("sft_sample_count"), len(sft_result.samples))

    with st.expander(_ui_text("sft_preview"), expanded=False):
        preview_rows = [
            {
                "task_type": sample["metadata"]["task_type"],
                "instruction": sample["instruction"],
            }
            for sample in sft_result.samples
        ]
        st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)
        if sft_result.samples:
            st.json(sft_result.samples[0])

    st.download_button(
        label=_ui_text("download_sft_jsonl"),
        data=sft_result.jsonl.encode("utf-8"),
        file_name=f"{_slugify_filename(workflow_result.dataset_name)}_sft_dataset.jsonl",
        mime="application/jsonl",
        use_container_width=True,
    )


def _ui_text(key: str, **kwargs: object) -> str:
    labels = {
        "zh": {
            "table_query_title": "表格查询 Agent",
            "table_query_caption": "用只读 SQL 查询当前上传的数据表。表名固定为 dataset。",
            "table_query_mode": "查询模式",
            "manual_sql": "手写 SQL",
            "natural_language": "自然语言生成 SQL",
            "manual_sql_label": "输入 SQL",
            "generated_sql_label": "生成/编辑 SQL",
            "nl_query_label": "输入你想对表格做的操作",
            "nl_query_placeholder": "例如：按地区统计销售额，并按销售额降序排列",
            "generate_sql_button": "生成 SQL",
            "run_sql_button": "运行 SQL",
            "download_query_result": "下载查询结果 CSV",
            "empty_question_warning": "请先输入一个自然语言问题。",
            "llm_required_warning": "自然语言生成 SQL 需要先在侧边栏配置 LLM。你也可以切换到手写 SQL 模式。",
            "generate_sql_error": "SQL 生成失败：{error}",
            "sql_error": "SQL 执行失败：{error}",
            "result_truncated": "结果超过 500 行，当前只展示前 500 行。",
            "sql_help": "只允许 SELECT 或 WITH 查询。当前数据表名是 dataset。",
            "sft_title": "SFT 数据集构造",
            "sft_caption": "把本次分析流程转换成 instruction-input-output 格式的监督微调样本。当前功能只负责导出训练数据，不在应用内直接训练模型。",
            "sft_sample_count": "SFT 样本数",
            "sft_preview": "预览 SFT JSONL 样本",
            "download_sft_jsonl": "下载 SFT JSONL",
            "chart_render_error": "这个图表暂时无法渲染，其他分析结果不受影响。",
        },
        "en": {
            "table_query_title": "Table Query Agent",
            "table_query_caption": "Query the current uploaded dataset with read-only SQL. The table name is dataset.",
            "table_query_mode": "Query mode",
            "manual_sql": "Manual SQL",
            "natural_language": "Natural language to SQL",
            "manual_sql_label": "Enter SQL",
            "generated_sql_label": "Generated / editable SQL",
            "nl_query_label": "Describe the table operation you want",
            "nl_query_placeholder": "Example: summarize revenue by region and sort by revenue descending",
            "generate_sql_button": "Generate SQL",
            "run_sql_button": "Run SQL",
            "download_query_result": "Download query result CSV",
            "empty_question_warning": "Enter a natural-language question first.",
            "llm_required_warning": "Natural-language SQL generation requires an LLM config in the sidebar. You can use Manual SQL mode instead.",
            "generate_sql_error": "SQL generation failed: {error}",
            "sql_error": "SQL execution failed: {error}",
            "result_truncated": "The result exceeded 500 rows, so only the first 500 rows are shown.",
            "sql_help": "Only SELECT or WITH queries are allowed. The current table name is dataset.",
            "sft_title": "SFT Dataset Builder",
            "sft_caption": "Convert this analysis workflow into instruction-input-output supervised fine-tuning samples. This app exports training data only; it does not fine-tune a model directly.",
            "sft_sample_count": "SFT samples",
            "sft_preview": "Preview SFT JSONL samples",
            "download_sft_jsonl": "Download SFT JSONL",
            "chart_render_error": "This chart could not be rendered. Other analysis results are still available.",
        },
    }
    text = labels.get(language, labels["en"]).get(key, key)
    return text.format(**kwargs)


def _slugify_filename(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_").lower()
    return slug or "dataset"


with st.container(key=f"page_{page}"):
    if page == "home":
        st.subheader(t(language, "upload_dataset"))
        uploaded_file = st.file_uploader(
            t(language, "upload_dataset"),
            type=["csv", "xlsx", "xls"],
            accept_multiple_files=False,
        )
        sample_options = {
            "Customer churn sample": ROOT_DIR / "sample_data" / "customer_churn_sample.csv",
            "Customer churn quality demo": ROOT_DIR / "sample_data" / "customer_churn_quality_demo.csv",
        }
        selected_sample = None
        selected_sheet = None
        if uploaded_file is None:
            selected_sample = st.selectbox(
                t(language, "sample_dataset"),
                [None] + [name for name, path in sample_options.items() if path.exists()],
                format_func=lambda value: t(language, "none") if value is None else value,
            )
        elif is_excel_file(uploaded_file.name):
            try:
                selected_sheet = st.selectbox(
                    t(language, "select_excel_sheet"), list_excel_sheets(uploaded_file)
                )
            except Exception as exc:
                st.error(t(language, "load_error", error=exc))
                st.stop()

        if st.button(
            "载入数据集" if language == "zh" else "Load dataset",
            type="primary",
            disabled=uploaded_file is None and selected_sample is None,
        ):
            try:
                if uploaded_file is not None:
                    loaded_df = load_dataset(uploaded_file, uploaded_file.name, sheet_name=selected_sheet)
                    loaded_name = uploaded_file.name
                else:
                    loaded_df = pd.read_csv(sample_options[selected_sample])
                    loaded_name = f"{selected_sample}.csv"
                # Commit the new dataset only after parsing succeeds.
                st.session_state["active_dataset"] = (loaded_name, selected_sheet, loaded_df)
                for key in ("analysis_result", "analysis_settings", "generated_table_sql"):
                    st.session_state.pop(key, None)
            except Exception as exc:
                st.error(t(language, "load_error", error=exc))

    if "active_dataset" not in st.session_state:
        st.info(t(language, "start_upload"))
        st.stop()

    dataset_name, dataset_sheet, df = st.session_state["active_dataset"]
    st.caption(f"{dataset_name}" + (f" · {dataset_sheet}" if dataset_sheet else ""))

    if page == "home":
        st.subheader(t(language, "data_preview"))
        st.dataframe(df.head(20), use_container_width=True)
        st.stop()

    settings = (language, insight_mode, runtime_llm_config)
    if st.session_state.get("analysis_settings") != settings:
        try:
            with st.spinner(t(language, "running_analysis")):
                result = run_analysis_workflow(
                    df=df,
                    config=WorkflowConfig(
                        dataset_name=dataset_name,
                        language=language,
                        use_llm=insight_mode == "llm",
                        llm_config=runtime_llm_config,
                    ),
                )
            st.session_state["analysis_result"] = result
            st.session_state["analysis_settings"] = settings
        except Exception as exc:
            st.error(t(language, "analysis_error", error=exc))
            st.stop()

    workflow_result = st.session_state["analysis_result"]
    if page == "quality":
        st.subheader(t(language, "dataset_overview"))
        render_summary(workflow_result.dataset_summary)
        render_profiler(workflow_result.profile_df)
        render_quality_report(df, workflow_result.quality_df)
        with st.expander(t(language, "column_overview")):
            st.dataframe(localize_dataframe(workflow_result.column_overview, language), use_container_width=True)
        with st.expander(t(language, "workflow_steps")):
            render_workflow_steps(workflow_result)
    elif page == "eda":
        render_eda_report(df, workflow_result.eda_df)
    elif page == "insights":
        render_insight_report(workflow_result.insight_result)
        render_markdown_report(dataset_name, workflow_result.markdown_report, workflow_result.html_report)
    elif page == "qa":
        render_rag_qa(workflow_result)
    elif page == "sql":
        render_table_query_agent(df, workflow_result)
    elif page == "sft":
        render_sft_dataset_builder(workflow_result)
