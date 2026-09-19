from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.auth_routes import router as auth_router
from app.api.dataset_routes import router as dataset_router
from app.api.routes import router
from app.db.database import init_db


app = FastAPI(
    title="DataInsight Agent API",
    description="FastAPI backend for dataset profiling, data quality analysis, EDA planning, reports, and RAG Q&A.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "http://127.0.0.1:8501,http://localhost:8501").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(dataset_router, prefix="/api")


@app.on_event("startup")
def initialize_database_on_startup() -> None:
    if os.getenv("INIT_DB_ON_STARTUP", "false").lower() == "true":
        init_db()


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    frontend_url = os.getenv("FRONTEND_URL", "http://127.0.0.1:8501")
    return f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>DataInsight Agent</title>
        <style>
          body {{
            margin: 0;
            font-family: Arial, sans-serif;
            color: #1f2937;
            background: #f8fafc;
          }}
          main {{
            max-width: 760px;
            margin: 64px auto;
            padding: 0 24px;
          }}
          h1 {{
            font-size: 40px;
            margin: 0 0 12px;
          }}
          p {{
            color: #64748b;
            line-height: 1.6;
          }}
          .links {{
            display: grid;
            gap: 12px;
            margin-top: 28px;
          }}
          a {{
            display: block;
            padding: 16px 18px;
            border: 1px solid #dbe3ef;
            border-radius: 8px;
            color: #0f172a;
            background: white;
            text-decoration: none;
            font-weight: 700;
          }}
          a span {{
            display: block;
            margin-top: 4px;
            color: #64748b;
            font-weight: 400;
            font-size: 14px;
          }}
        </style>
      </head>
      <body>
        <main>
          <h1>DataInsight Agent</h1>
          <p>Choose an entry point for the data analysis app or backend API.</p>
          <div class="links">
            <a href="{frontend_url}">Open Streamlit Frontend<span>Upload datasets, run analysis, query tables, and generate reports.</span></a>
            <a href="/docs">Open FastAPI Docs<span>Test backend endpoints including analysis, Q&A, and table query APIs.</span></a>
            <a href="/api/health">Check API Health<span>Verify that the backend service is running.</span></a>
          </div>
        </main>
      </body>
    </html>
    """
