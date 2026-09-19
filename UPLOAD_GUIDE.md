# GitHub 上传说明

本包包含 2026-09-19 的前端调整：顶部导航、七个功能板块、浅色工作台、青绿色选中标识、页面淡入过渡，以及会话内的数据与分析结果复用。

## 上传

1. 打开目标 GitHub 仓库，选择 Add file → Upload files。
2. 上传本文件夹内的内容，让 `app/`、`frontend/` 和 `requirements.txt` 直接位于仓库根目录。不要上传 ZIP 代替源码，也不要额外套一层本文件夹名称。
3. 确保包含隐藏目录 `.streamlit/`，以及 `frontend/styles.css`。
4. 提交修改。上传前请检查仓库里是否有旧的嵌套项目目录或旧依赖文件；上传不会自动删除旧文件。

## Streamlit Cloud

- Main file path：`frontend/streamlit_app.py`
- Python：3.12
- 使用根目录 `requirements.txt`。
- LLM 密钥在 Cloud 的 Secrets 中配置，模板为 `.streamlit/secrets.example.toml`。不要把真实密钥上传 GitHub。

本包保留 MySQL 用户与数据集后端源码。Streamlit Cloud 前端部署不会自动启动 MySQL 或 FastAPI；后端需单独配置部署。数据库连接使用 `.env.example` 中的模板配置。

本包不含虚拟环境、缓存、运行日志、真实密钥或个人分析输出。完整使用说明见 `README.md`，部署说明见 `DEPLOYMENT_STEPS.md`。
