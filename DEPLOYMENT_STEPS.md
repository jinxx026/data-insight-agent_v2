# Streamlit Cloud 部署步骤

这是 DataInsight Agent 的干净部署版。请把这个文件夹里的内容作为 GitHub 仓库根目录上传，不要再套一层 `data-insight-agent/` 文件夹。

## 1. GitHub 仓库结构应该是这样

```text
your-repo/
├── app/
├── frontend/
├── knowledge_base/
├── sample_data/
├── requirements.txt
├── README.md
└── ...
```

不要变成：

```text
your-repo/
└── data-insight-agent/
    ├── app/
    ├── frontend/
    └── requirements.txt
```

## 2. Streamlit Cloud 设置

Repository:

```text
jinxx026/data-insight-agent
```

Branch:

```text
main
```

Main file path:

```text
frontend/streamlit_app.py
```

Python version:

```text
3.12
```

在 `Advanced settings` 中可以选填 Secrets。应用默认使用本地规则，不配置 LLM 也能完成分析；如需 LLM 洞察、增强问答和自然语言转 SQL，可粘贴：

```toml
[llm]
provider = "DeepSeek"
api_key = "你的 API Key"
base_url = "https://api.deepseek.com/v1"
model = "deepseek-chat"
```

## 3. 推送前本地验证

请从仓库根目录运行，保持与 Streamlit Cloud 的工作目录一致：

```bash
python -m venv .venv
# Windows
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m unittest tests.smoke_test -v
.venv\Scripts\streamlit run frontend/streamlit_app.py
```

浏览器确认样例数据可运行后，可用健康检查验证服务：

```text
http://127.0.0.1:8501/_stcore/health
```

正常响应应为 `ok`。

## 4. 重新部署

如果之前部署失败过，建议直接删除 Streamlit Cloud 里的旧 app，然后 New app 重新部署。

如果不删除，也至少执行：

```text
Manage app -> Clear cache
Manage app -> Reboot app
```

## 5. 依赖说明

仓库只保留根目录的 `requirements.txt` 作为 Streamlit Cloud 依赖入口，避免入口目录与根目录的依赖文件互相覆盖。依赖已包含 `.xlsx` 和 `.xls` 读取引擎，并移除了非必需的 DuckDB 二进制依赖。

Table Query Agent 仍然可以使用 SQL 查询。云端会自动使用 Python 标准库 SQLite 作为 fallback。

本地如果需要运行 FastAPI 后端，可以安装：

```bash
pip install -r requirements-api.txt
```
