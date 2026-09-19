FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt requirements-api.txt .
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN python -m pip install \
    --no-cache-dir \
    --default-timeout=120 \
    --retries=10 \
    -i ${PIP_INDEX_URL} \
    -r requirements-api.txt

COPY . .

EXPOSE 8501 8000

CMD ["streamlit", "run", "frontend/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
