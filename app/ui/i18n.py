from __future__ import annotations

import pandas as pd


LANGUAGE_OPTIONS = {
    "zh": "中文",
    "en": "English",
}


TEXT = {
    "zh": {
        "language": "语言",
        "caption": "上传 CSV 或 Excel 数据集，自动预览数据、识别字段类型并检查数据质量。",
        "upload_dataset": "上传数据集",
        "sample_dataset": "或使用示例数据",
        "none": "不使用示例",
        "select_excel_sheet": "选择 Excel 工作表",
        "start_upload": "请先上传 CSV / Excel 数据集，或选择一个示例数据。",
        "sample_preview": "示例数据预览",
        "dataset_overview": "数据集概览",
        "smart_field_detection": "智能字段类型识别",
        "detected_target": "检测到目标变量：{columns}",
        "no_target": "暂未检测到目标变量。仍然可以继续做描述性分析。",
        "quality_report": "数据质量报告",
        "no_quality_issues": "当前规则没有检测到明显的数据质量问题。",
        "severity_caption": "严重程度是基于规则判断的：高表示会明显影响分析或建模；中表示需要人工复核；低表示主要是使用提醒。",
        "data_preview": "数据预览",
        "column_overview": "字段概览",
        "load_error": "数据读取失败：{error}",
        "running_analysis": "正在运行数据分析工作流…",
        "analysis_error": "数据分析失败：{error}",
        "rows": "行数",
        "columns": "列数",
        "missing_cells": "缺失单元格",
        "duplicate_rows": "重复行",
        "memory": "内存占用",
        "quality_issues": "质量问题数",
        "high_severity": "高严重问题",
        "columns_with_missing": "有缺失的字段",
        "eda_report": "自动 EDA 与图表推荐",
        "no_eda_recommendations": "当前字段类型不足以生成自动 EDA 推荐。",
        "count": "数量",
        "target_rate": "目标变量占比",
        "no_valid_datetime_values": "没有足够的有效时间值用于绘制趋势图。",
        "not_enough_data_for_chart": "没有足够数据用于绘制该图表。",
        "unsupported_chart": "暂不支持该图表类型。",
        "insight_mode": "洞察生成模式",
        "insight_mode_local": "本地规则",
        "insight_mode_llm": "LLM（如果已配置）",
        "llm_api_key": "LLM API Key",
        "llm_provider": "LLM 提供商",
        "llm_base_url": "LLM Base URL",
        "llm_model": "LLM 模型",
        "llm_custom_base_url": "自定义 Base URL",
        "llm_custom_model": "自定义模型名",
        "llm_config_help": "API Key 只在当前会话中使用，不会写入项目文件。",
        "insight_report": "智能洞察总结",
        "llm_report": "LLM 生成报告",
        "llm_fallback": "LLM 未使用，已回退到本地规则。",
        "report_section": "Markdown 分析报告",
        "report_preview": "报告预览",
        "download_report": "下载 Markdown 报告",
        "download_html_report": "下载 HTML 报告",
        "workflow_steps": "多 Agent 工作流",
        "rag_qa": "数据集与知识库自然语言问答",
        "rag_question": "输入你的数据分析问题",
        "rag_question_placeholder": "例如：这个数据集有什么主要风险？为什么 customer_id 不适合建模？",
        "rag_answer": "问答结果",
        "rag_sources": "检索到的知识片段",
    },
    "en": {
        "language": "Language",
        "caption": "Upload a CSV or Excel dataset to preview, profile fields, and check data quality.",
        "upload_dataset": "Upload dataset",
        "sample_dataset": "Or use a sample dataset",
        "none": "None",
        "select_excel_sheet": "Select Excel sheet",
        "start_upload": "Start by uploading a CSV or Excel dataset, or choose a sample dataset.",
        "sample_preview": "Sample data preview",
        "dataset_overview": "Dataset overview",
        "smart_field_detection": "Smart field type detection",
        "detected_target": "Detected target variable: {columns}",
        "no_target": "No target variable detected yet. You can still run descriptive analysis.",
        "quality_report": "Data quality report",
        "no_quality_issues": "No obvious data quality issues were detected by the current rule set.",
        "severity_caption": "Severity is rule-based: high means it can strongly affect analysis or modeling; medium means it needs review; low means it is mostly a usage warning.",
        "data_preview": "Data preview",
        "column_overview": "Column overview",
        "load_error": "Failed to load dataset: {error}",
        "running_analysis": "Running the data analysis workflow...",
        "analysis_error": "Data analysis failed: {error}",
        "rows": "Rows",
        "columns": "Columns",
        "missing_cells": "Missing cells",
        "duplicate_rows": "Duplicate rows",
        "memory": "Memory",
        "quality_issues": "Quality issues",
        "high_severity": "High severity",
        "columns_with_missing": "Columns with missing",
        "eda_report": "Automatic EDA and chart recommendations",
        "no_eda_recommendations": "There are not enough recognized field types to generate EDA recommendations.",
        "count": "Count",
        "target_rate": "Target rate",
        "no_valid_datetime_values": "There are not enough valid datetime values for a trend chart.",
        "not_enough_data_for_chart": "There is not enough data to render this chart.",
        "unsupported_chart": "This chart type is not supported yet.",
        "insight_mode": "Insight mode",
        "insight_mode_local": "Local rules",
        "insight_mode_llm": "LLM if configured",
        "llm_api_key": "LLM API Key",
        "llm_provider": "LLM provider",
        "llm_base_url": "LLM Base URL",
        "llm_model": "LLM model",
        "llm_custom_base_url": "Custom Base URL",
        "llm_custom_model": "Custom model name",
        "llm_config_help": "The API key is only used in the current session and is not written to project files.",
        "insight_report": "Insight summary",
        "llm_report": "LLM-generated report",
        "llm_fallback": "LLM was not used; local rule-based insights are shown.",
        "report_section": "Markdown analysis report",
        "report_preview": "Report preview",
        "download_report": "Download Markdown report",
        "download_html_report": "Download HTML report",
        "workflow_steps": "Multi-agent workflow",
        "rag_qa": "Dataset and knowledge base Q&A",
        "rag_question": "Ask a data analysis question",
        "rag_question_placeholder": "Example: What are the main risks in this dataset? Why is customer_id not suitable for modeling?",
        "rag_answer": "Q&A answer",
        "rag_sources": "Retrieved knowledge snippets",
    },
}


VALUE_TRANSLATIONS = {
    "zh": {
        "smart_type": {
            "empty_field": "空字段",
            "id_field": "ID 字段",
            "target_variable": "目标变量",
            "datetime_feature": "时间字段",
            "categorical_feature": "类别特征",
            "numerical_feature": "数值特征",
            "text_feature": "文本特征",
            "unknown_feature": "待确认字段",
        },
        "analysis_role": {
            "exclude": "排除",
            "identifier": "标识符",
            "target": "目标",
            "time": "时间",
            "feature": "特征",
            "review": "需复核",
        },
        "severity": {
            "high": "高",
            "medium": "中",
            "low": "低",
        },
        "scope": {
            "dataset": "数据集",
            "column": "字段",
        },
        "issue_type": {
            "duplicate_rows": "重复行",
            "missing_values": "缺失值",
            "empty_field": "空字段",
            "constant_field": "常量字段",
            "identifier_field": "ID 字段",
            "high_cardinality": "高基数字段",
            "numeric_outliers": "数值异常值",
            "target_imbalance": "目标变量类别不平衡",
        },
        "analysis_type": {
            "numeric_distribution": "数值分布分析",
            "category_distribution": "类别分布分析",
            "time_trend": "时间趋势分析",
            "target_distribution": "目标变量分布",
            "target_by_category": "目标变量分组对比",
            "correlation_heatmap": "相关性热力图",
        },
        "chart_type": {
            "histogram": "直方图",
            "bar_chart": "柱状图",
            "line_chart": "折线图",
            "grouped_bar_chart": "分组柱状图",
            "heatmap": "热力图",
        },
        "priority": {
            "high": "高",
            "medium": "中",
            "low": "低",
        },
    },
    "en": {},
}


TEXT_TRANSLATIONS = {
    "zh": {
        "All values are missing, so this field cannot be used for analysis yet.": "所有值均缺失，因此该字段目前无法用于分析。",
        "The column name suggests a label/target and it has a small number of classes.": "字段名显示它可能是标签/目标变量，并且类别数量较少。",
        "The column name or near-unique values indicate an identifier, not a modeling feature.": "字段名或接近唯一的取值显示它更像标识符，而不是建模特征。",
        "Most non-missing values can be parsed as dates or timestamps.": "大多数非缺失值可以被解析为日期或时间戳。",
        "Boolean values are best treated as a two-class categorical feature.": "布尔值更适合作为二分类类别特征处理。",
        "Numeric values have low cardinality, so they are likely categories or flags.": "数值取值种类较少，因此更可能是类别或标记字段。",
        "Numeric dtype with enough distinct values for distribution and correlation analysis.": "该字段是数值类型且有足够多不同取值，适合做分布和相关性分析。",
        "String values are relatively long or high-cardinality, which fits text analysis.": "字符串较长或唯一值较多，更适合按文本特征分析。",
        "String/object values have repeated groups suitable for category comparison.": "字符串/object 字段存在重复分组，适合做类别对比分析。",
        "The field does not match common numeric, categorical, datetime, text, target, or ID rules.": "该字段暂不符合常见数值、类别、时间、文本、目标变量或 ID 规则。",
        "Duplicate rows can bias aggregate statistics and model training.": "重复行会影响汇总统计，也可能让模型训练产生偏差。",
        "Review whether duplicated records are valid repeat events or accidental duplicates.": "需要确认重复记录是真实重复事件，还是数据采集中的意外重复。",
        "Missing values can distort summaries, charts, and model features.": "缺失值可能影响统计摘要、图表展示和模型特征。",
        "The field contains no usable values.": "该字段没有可用取值。",
        "Exclude this field or fix the upstream data collection process.": "建议排除该字段，或修复上游数据采集流程。",
        "A constant field has no variation and contributes little to analysis or modeling.": "常量字段没有变化，对分析或建模贡献很小。",
        "Exclude this field unless the constant value has operational meaning.": "除非该常量有明确业务含义，否则建议排除。",
        "Identifier fields are useful for joining records but should not be treated as analytical features.": "ID 字段适合用于记录关联，但不应作为分析或建模特征。",
        "Keep this column for lookup or traceability, but exclude it from feature statistics and modeling.": "可保留该字段用于查询或追踪，但应从特征统计和建模中排除。",
        "High-cardinality fields can create noisy group comparisons and sparse model features.": "高基数字段会造成分组对比噪声较大，也可能产生稀疏特征。",
        "Consider grouping rare values, extracting text features, or excluding the raw column.": "可以考虑合并低频类别、抽取文本特征，或排除原始字段。",
        "Inspect whether these are valid extreme values, data entry errors, or require capping/transformation.": "需要检查这些值是真实极端值、录入错误，还是需要截尾/转换处理。",
        "An imbalanced target can make model accuracy misleading and reduce minority-class performance.": "目标变量不平衡会让准确率指标产生误导，并削弱少数类识别能力。",
        "Use stratified splits and evaluate precision, recall, F1, ROC-AUC, or PR-AUC instead of accuracy alone.": "建议使用分层切分，并评估 precision、recall、F1、ROC-AUC 或 PR-AUC，而不是只看 accuracy。",
        "Consider median imputation, missing indicators, or removing the field if missingness is too high.": "可考虑中位数填充、增加缺失指示变量；如果缺失率过高则考虑删除字段。",
        "Consider a dedicated 'Unknown' category, mode imputation, or row filtering depending on business meaning.": "可根据业务含义使用 Unknown 类别、众数填充或过滤对应行。",
        "Check whether missing timestamps mean incomplete events before imputing or filtering.": "填充或过滤前，需要确认缺失时间是否代表事件未完成。",
        "Keep blanks as empty text only if absence of text is meaningful; otherwise investigate collection gaps.": "只有当文本为空本身有业务含义时才保留为空；否则应检查数据采集缺口。",
        "Investigate why values are missing before choosing deletion or imputation.": "在删除或填充之前，应先确认缺失原因。",
    },
    "en": {},
}


COLUMN_LABELS = {
    "zh": {
        "smart_type": "智能类型",
        "count": "数量",
        "column": "字段名",
        "pandas_dtype": "原始类型",
        "analysis_role": "分析角色",
        "reason": "判断原因",
        "missing_rate": "缺失率",
        "missing_count": "缺失数量",
        "unique_count": "唯一值数量",
        "unique_rate": "唯一值比例",
        "example_values": "示例值",
        "severity": "严重程度",
        "issue_type": "问题类型",
        "scope": "范围",
        "metric": "指标",
        "details": "影响说明",
        "recommendation": "处理建议",
        "analysis_type": "分析类型",
        "chart_type": "图表类型",
        "title": "标题",
        "columns": "使用字段",
        "rationale": "推荐原因",
        "priority": "优先级",
        "topic": "主题",
        "insight": "洞察",
        "evidence": "证据",
        "agent": "智能体",
        "status": "状态",
        "output": "输出",
        "score": "相关度",
        "source": "来源",
        "title": "标题",
        "text": "内容",
    },
    "en": {},
}


def t(language: str, key: str, **kwargs: object) -> str:
    text = TEXT.get(language, TEXT["en"]).get(key, TEXT["en"].get(key, key))
    return text.format(**kwargs)


def localize_dataframe(df: pd.DataFrame, language: str) -> pd.DataFrame:
    if language == "en" or df.empty:
        return df

    localized = df.copy()
    value_maps = VALUE_TRANSLATIONS["zh"]
    for column, value_map in value_maps.items():
        if column in localized.columns:
            localized[column] = localized[column].map(lambda value: value_map.get(value, value))

    for column in ["reason", "details", "recommendation"]:
        if column in localized.columns:
            localized[column] = localized[column].map(
                lambda value: _translate_text_value(value)
            )

    if "metric" in localized.columns:
        localized["metric"] = localized["metric"].map(_translate_metric_value)

    return localized.rename(columns=COLUMN_LABELS["zh"])


def _translate_text_value(value: object) -> object:
    if not isinstance(value, str):
        return value

    exact_translation = TEXT_TRANSLATIONS["zh"].get(value)
    if exact_translation:
        return exact_translation

    if value.startswith("IQR rule detected values outside"):
        bounds = value.replace("IQR rule detected values outside ", "").rstrip(".")
        return f"IQR 规则检测到取值超出 {bounds}。"

    return value


def _translate_metric_value(value: object) -> object:
    if not isinstance(value, str):
        return value

    translated = value
    translated = translated.replace(" rows", " 行")
    translated = translated.replace(" missing", " 个缺失")
    translated = translated.replace(" outliers", " 个异常值")
    translated = translated.replace(" unique value", " 个唯一值")
    translated = translated.replace(" unique", " 个唯一值")
    translated = translated.replace("minority ", "少数类 ")
    translated = translated.replace(", majority ", "，多数类 ")
    return translated
