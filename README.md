# DataInsight Agent

DataInsight Agent 是一个基于 LLM + RAG + 多 Agent 工作流 + SFT 数据集构造的智能数据分析系统。用户上传 CSV 或 Excel 数据集后，系统可以自动完成字段类型识别、数据质量检测、探索性数据分析、图表推荐、自然语言洞察生成、RAG 问答、SQL 表格查询、SFT JSONL 样本导出和 Markdown/HTML 报告导出。

这个项目的目标不是做一个普通 dashboard，而是把数据分析流程拆成多个可复用 Agent，让系统能够自动理解数据、选择分析方法，并用自然语言解释结果。

## Demo Flow

1. 上传 CSV 或 Excel 文件。
2. 如果是 Excel，选择需要分析的 Sheet。
3. 系统自动运行多 Agent 分析流程。
4. 查看字段画像、数据质量问题、EDA 图表和洞察总结。
5. 使用 RAG Q&A 询问数据分析方法或当前数据集问题。
6. 使用 Table Query Agent 对上传表格执行 SQL 查询。
7. 使用 SFT Dataset Builder 导出 instruction-input-output 训练样本。
8. 下载 Markdown 或 HTML 分析报告。

## Key Features

- CSV / Excel 上传，支持 Excel Sheet 选择
- 智能字段类型识别：ID、数值、类别、时间、文本、目标变量
- 数据质量分析：缺失值、重复行、空字段、常量字段、高基数字段、异常值、目标类别不平衡
- 自动 EDA：数值分布、类别分布、时间趋势、目标变量分布、目标变量分组对比、相关性分析
- Insight Agent：基于本地规则或 LLM 生成自然语言数据洞察
- RAG Q&A：基于内置数据分析知识库回答问题
- Table Query Agent：用 DuckDB 或 SQLite 回退引擎对上传数据执行只读 SQL 查询
- Natural Language to SQL：配置 LLM 后，可用自然语言生成 SQL
- SFT Dataset Builder：把字段识别、质量分析、EDA、洞察和报告生成结果转换成可用于监督微调的 JSONL 样本
- Report Agent：生成 Markdown 和 HTML 分析报告
- FastAPI 后端：封装分析、问答、Sheet 读取和表格查询接口
- Docker Compose：同时启动 Streamlit 前端和 FastAPI 后端
- 中英文界面切换

## Tech Stack

| Layer | Tech |
| --- | --- |
| Frontend | Streamlit |
| Backend | FastAPI |
| Data Processing | pandas, numpy |
| SQL Engine | DuckDB with SQLite fallback |
| Visualization | Altair |
| LLM API | OpenAI-compatible API, DeepSeek, GPT, Gemini, Kimi |
| RAG | Local TF-IDF retriever, Markdown knowledge base |
| SFT Data | Instruction-input-output JSONL export |
| Deployment | Docker, Docker Compose, Streamlit Community Cloud |

## Architecture

```text
User
  |
  v
Streamlit Frontend
  |
  +-- Upload CSV / Excel
  +-- Display analysis results
  +-- Run RAG Q&A
  +-- Run SQL table queries
  +-- Export SFT JSONL samples
  |
  v
Multi-Agent Workflow
  |
  +-- Data Loader
  +-- Data Profiler Agent
  +-- Data Quality Agent
  +-- EDA Agent
  +-- Insight Agent
  +-- Report Agent
  +-- RAG QA Agent
  +-- Table Query Agent
  +-- SFT Dataset Builder
  |
  v
Data Layer
  |
  +-- pandas
  +-- DuckDB / SQLite fallback
  +-- Altair
  |
  v
RAG Knowledge Base + Optional LLM API
```

## Multi-Agent Workflow

| Agent | Responsibility |
| --- | --- |
| Data Loader | 读取 CSV / Excel，生成数据集概览 |
| Data Profiler Agent | 识别字段的语义类型和分析角色 |
| Data Quality Agent | 检测缺失值、重复值、异常值、高基数字段等质量问题 |
| EDA Agent | 根据字段类型自动推荐分析方法和图表 |
| Insight Agent | 基于统计结果生成自然语言洞察 |
| Report Agent | 生成 Markdown / HTML 分析报告 |
| RAG QA Agent | 结合当前数据集和知识库回答自然语言问题 |
| Table Query Agent | 将数据表注册为内存表并执行只读 SQL，DuckDB 不可用时自动回退 SQLite |
| SFT Dataset Builder | 将一次完整分析流程转换成 instruction-input-output 格式的监督微调样本 |

## Project Structure

```text
data-insight-agent/
├── app/
│   ├── agents/
│   │   ├── insight_agent.py
│   │   ├── qa_agent.py
│   │   ├── report_agent.py
│   │   ├── sft_dataset_agent.py
│   │   ├── table_query_agent.py
│   │   └── workflow_agent.py
│   ├── api/
│   │   └── routes.py
│   ├── data/
│   │   ├── eda.py
│   │   ├── loader.py
│   │   ├── profiler.py
│   │   └── quality.py
│   ├── llm/
│   │   ├── model.py
│   │   └── presets.py
│   ├── rag/
│   │   └── retriever.py
│   ├── ui/
│   │   └── i18n.py
│   └── main.py
├── frontend/
│   └── streamlit_app.py
├── knowledge_base/
├── sample_data/
├── outputs/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── run_app.bat
├── run_api.bat
└── run_docker.bat
```

## Quick Start

### Windows

启动 Streamlit 前端：

```text
run_app.bat
```

打开浏览器：

```text
http://127.0.0.1:8501
```

启动 FastAPI 后端：

```text
run_api.bat
```

后端入口页：

```text
http://127.0.0.1:8000/
```

API 文档：

```text
http://127.0.0.1:8000/docs
```

### macOS / Linux

```bash
pip install -r requirements.txt
streamlit run frontend/streamlit_app.py
```

另开一个终端启动 API：

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Docker

启动 Streamlit 前端和 FastAPI 后端：

```bash
docker compose up --build
```

访问地址：

```text
Streamlit Frontend: http://127.0.0.1:8501
Backend Entry:      http://127.0.0.1:8000/
FastAPI Docs:       http://127.0.0.1:8000/docs
```

Windows 也可以直接双击：

```text
run_docker.bat
```

## LLM Configuration

系统默认可以不配置 LLM，使用本地规则生成分析结果。配置 LLM 后，可以启用：

- LLM 洞察生成
- RAG 问答增强回答
- 自然语言生成 SQL

支持的预设提供商：

- DeepSeek
- OpenAI GPT
- Google Gemini
- Kimi
- Custom OpenAI-compatible API

### Sidebar Runtime Config

在 Streamlit 侧边栏选择：

```text
Insight mode -> LLM if configured
Provider -> DeepSeek / OpenAI GPT / Google Gemini / Kimi / Custom
API Key -> your_api_key
Base URL -> provider base url
Model -> model name
```

API Key 只会保存在当前 Streamlit session 中，不会写入项目文件。

### Local Secrets

复制示例文件：

```text
.streamlit/secrets.example.toml -> .streamlit/secrets.toml
```

填写：

```toml
[llm]
provider = "DeepSeek"
api_key = "your_api_key_here"
base_url = "https://api.deepseek.com/v1"
model = "deepseek-chat"
```

`.streamlit/secrets.toml` 已被 `.gitignore` 忽略，不应该提交到 GitHub。

## Table Query Agent

Table Query Agent 会把当前上传的数据注册成内存表：

```text
dataset
```

你可以直接写 SQL：

```sql
SELECT contract_type, COUNT(*) AS customers
FROM dataset
GROUP BY contract_type
ORDER BY customers DESC;
```

也可以在配置 LLM 后输入自然语言：

```text
按合同类型统计客户数量，并按客户数量降序排列
```

系统会生成 SQL，再由 SQL 引擎执行并输出表格。部署环境支持 DuckDB 时优先使用 DuckDB；如果 DuckDB 不可用，会自动回退到 Python 标准库 SQLite。

### SQL Safety

为了避免执行危险操作，系统只允许：

```text
SELECT
WITH
```

禁止：

```text
INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, COPY, INSTALL, LOAD, PRAGMA
```

LLM 只负责生成 SQL，真正执行和安全校验由系统完成。

## SFT Dataset Builder

SFT Dataset Builder 会把一次完整的数据分析流程转换成监督微调常用的 JSONL 格式：

```json
{"instruction": "...", "input": {...}, "output": {...}, "metadata": {...}}
```

当前会导出 5 类样本：

- field_profiling：字段语义类型识别
- data_quality_analysis：数据质量问题检测
- eda_planning：EDA 分析方法推荐
- insight_generation：自然语言洞察生成
- report_generation：Markdown 报告生成

这个模块的定位是 SFT 数据构造，而不是在 Streamlit 应用内直接训练模型。后续可以把导出的 JSONL 接入 LoRA / QLoRA / SFTTrainer 等训练流程。

## RAG Knowledge Base

内置知识库位于：

```text
knowledge_base/
```

包含：

- feature_types.md
- missing_values.md
- outlier_detection.md
- correlation_analysis.md
- visualization_guide.md
- class_imbalance.md
- eda_methods.md

用户可以询问：

```text
为什么 customer_id 不适合建模？
为什么要看缺失值？
类别不平衡有什么影响？
什么时候用柱状图，什么时候用折线图？
```

系统会结合当前数据集分析结果和知识库片段回答。

## FastAPI Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| POST | `/api/auth/init-db` | 初始化 MySQL 数据表 |
| POST | `/api/auth/register` | 注册用户并返回 JWT |
| POST | `/api/auth/login` | 登录并返回 JWT |
| GET | `/api/auth/me` | 查看当前登录用户 |
| POST | `/api/datasets/upload` | 登录后上传数据集，保存到 MySQL 并生成分析报告 |
| GET | `/api/datasets/history` | 查看当前用户历史数据集 |
| GET | `/api/datasets/{dataset_id}` | 查看数据集详情 |
| GET | `/api/datasets/{dataset_id}/rows` | 查看保存到 MySQL 的数据行 |
| GET | `/api/llm/presets` | 获取 LLM provider 和 model 预设 |
| POST | `/api/datasets/sheets` | 读取 Excel Sheet 名称 |
| POST | `/api/analysis` | 上传数据集并返回完整分析结果 |
| POST | `/api/qa` | 基于当前数据集和知识库问答 |
| POST | `/api/table-query` | 对上传数据执行 SQL 查询 |

## Enterprise Backend: MySQL + User System

当前版本新增了企业化后端雏形：

- 用户注册 / 登录
- JWT Bearer Token 鉴权
- 上传数据集保存到 MySQL
- 每一行表格数据保存到 `dataset_rows`
- 分析报告保存到 `analysis_reports`
- 用户可以查看自己的历史数据集

MySQL 会自动创建这些表：

```text
users
datasets
dataset_rows
analysis_reports
```

### Docker Compose 启动

```bash
docker compose up --build
```

服务地址：

```text
FastAPI Docs: http://127.0.0.1:8000/docs
MySQL:        127.0.0.1:3306
Database:     datainsight
User:         datainsight
Password:     datainsight
```

### 本地 MySQL 配置

如果不用 Docker，需要先在 MySQL 里创建数据库和账号：

```sql
CREATE DATABASE datainsight CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'datainsight'@'%' IDENTIFIED BY 'datainsight';
GRANT ALL PRIVILEGES ON datainsight.* TO 'datainsight'@'%';
FLUSH PRIVILEGES;
```

然后设置环境变量：

```text
DATABASE_URL=mysql+pymysql://datainsight:datainsight@127.0.0.1:3306/datainsight
JWT_SECRET_KEY=replace_with_a_long_random_secret
```

### API 使用流程

1. 初始化数据库：

```text
POST /api/auth/init-db
```

2. 注册用户：

```json
POST /api/auth/register
{
  "email": "analyst@example.com",
  "password": "password123",
  "full_name": "Data Analyst"
}
```

3. 登录后复制返回的 `access_token`。

4. 在 FastAPI Docs 右上角点击 `Authorize`，填入：

```text
Bearer your_access_token
```

5. 上传数据集：

```text
POST /api/datasets/upload
```

6. 在 MySQL 里查看数据：

```sql
SELECT * FROM users;
SELECT * FROM datasets;
SELECT * FROM dataset_rows LIMIT 20;
SELECT * FROM analysis_reports;
```

说明：`dataset_rows.row_data` 是 JSON 字段，保存上传表格的每一行。为了避免超大文件把数据库写爆，默认最多保存前 `50000` 行，可通过 `MAX_STORED_ROWS` 调整。

## Streamlit Community Cloud Deployment

请将本目录内容直接作为 GitHub 仓库根目录，结构如下：

```text
datainsight/
├── .streamlit/
│   └── config.toml
├── app/
├── frontend/
│   └── streamlit_app.py
├── knowledge_base/
├── sample_data/
└── requirements.txt
```

Streamlit Community Cloud 的 Main file path 填写：

```text
frontend/streamlit_app.py
```

Python 版本选择 `3.12`。仓库仅使用根目录的 `requirements.txt`，不要在 `frontend/` 下再放第二份依赖文件，以免云端优先读取后者并造成版本漂移。

应用默认不需要 LLM Key；配置 Streamlit Secrets 后才启用 LLM 洞察和自然语言转 SQL。完整推送前检查、Secrets 示例和重部署步骤见 [`DEPLOYMENT_STEPS.md`](DEPLOYMENT_STEPS.md)。

Table Query Agent 在 Community Cloud 使用 Python 标准库 SQLite，无需安装 DuckDB。

## Example Questions

数据分析问答：

```text
这个数据集有哪些主要质量风险？
为什么某个字段被识别成 ID？
缺失值应该删除还是填充？
目标变量是否存在类别不平衡？
```

SQL 查询：

```text
筛选出 monthly_charges 大于 80 的客户
按 contract_type 统计客户数量
计算不同 payment_method 的平均 monthly_charges
找出 total_charges 最高的前 10 个客户
```

## Resume Highlights

- Built an LLM-powered data analysis system with Streamlit and FastAPI for CSV/Excel profiling, data quality checks, EDA automation, insight generation, and report export.
- Designed a multi-agent workflow including Profiler, Quality, EDA, Insight, Report, RAG QA, and Table Query agents.
- Implemented RAG-based data analysis Q&A with a local knowledge base and TF-IDF retrieval.
- Built a read-only Table Query Agent supporting SQL and natural-language-to-SQL over uploaded datasets, with DuckDB execution and SQLite fallback for cloud deployment.
- Containerized the Streamlit frontend and FastAPI backend with Docker Compose.

## License

This project is intended for learning, portfolio, and internship application use.
