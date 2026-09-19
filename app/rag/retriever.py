from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


@dataclass(frozen=True)
class KnowledgeChunk:
    source: str
    title: str
    text: str


def load_knowledge_chunks(knowledge_dir: Path) -> list[KnowledgeChunk]:
    """Load markdown knowledge files and split them into retrievable chunks."""
    chunks: list[KnowledgeChunk] = []
    for path in sorted(knowledge_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = _extract_title(text, path.stem)
        for chunk_text in _split_markdown(text):
            chunks.append(KnowledgeChunk(source=path.name, title=title, text=chunk_text))
    return chunks


def retrieve_knowledge(
    query: str,
    knowledge_dir: Path,
    top_k: int = 4,
) -> pd.DataFrame:
    """Retrieve relevant knowledge chunks using local TF-IDF cosine similarity."""
    chunks = load_knowledge_chunks(knowledge_dir)
    if not query.strip() or not chunks:
        return pd.DataFrame(columns=["score", "source", "title", "text"])

    query_tokens = _tokenize(query)
    if not query_tokens:
        return pd.DataFrame(columns=["score", "source", "title", "text"])

    documents = [_tokenize(chunk.text) for chunk in chunks]
    idf = _build_idf(documents)
    query_vector = _tfidf_vector(query_tokens, idf)

    results = []
    for chunk, tokens in zip(chunks, documents):
        score = _cosine_similarity(query_vector, _tfidf_vector(tokens, idf))
        if score <= 0:
            continue
        results.append(
            {
                "score": round(score, 4),
                "source": chunk.source,
                "title": chunk.title,
                "text": chunk.text,
            }
        )

    return (
        pd.DataFrame(results)
        .sort_values(["score", "source"], ascending=[False, True])
        .head(top_k)
        .reset_index(drop=True)
        if results
        else pd.DataFrame(columns=["score", "source", "title", "text"])
    )


def build_retrieval_answer(query: str, retrieved_df: pd.DataFrame, language: str) -> str:
    """Build a deterministic answer from retrieved knowledge snippets."""
    if retrieved_df.empty:
        return (
            "暂未在知识库中找到相关内容。你可以换一种问法，或补充更多关键词。"
            if language == "zh"
            else "No relevant knowledge base content was found. Try rephrasing the question or adding more keywords."
        )

    if language == "zh":
        lines = [f"基于知识库，关于“{query}”可以这样理解：", ""]
        for index, row in enumerate(retrieved_df.to_dict("records"), start=1):
            lines.append(f"{index}. 来源：{row['source']}，相关度：{row['score']}")
            lines.append(_trim_text(row["text"], max_chars=420))
            lines.append("")
        lines.append("这些内容来自内置数据分析知识库，不依赖外部 API。")
        return "\n".join(lines)

    lines = [f"Based on the knowledge base, here is the relevant context for: {query}", ""]
    for index, row in enumerate(retrieved_df.to_dict("records"), start=1):
        lines.append(f"{index}. Source: {row['source']}, score: {row['score']}")
        lines.append(_trim_text(row["text"], max_chars=420))
        lines.append("")
    lines.append("This answer is generated from the built-in data analysis knowledge base without external APIs.")
    return "\n".join(lines)


def _extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback.replace("_", " ").title()


def _split_markdown(text: str) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    chunks = []
    current: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_length = len(paragraph)
        if current and current_length + paragraph_length > 900:
            chunks.append("\n\n".join(current))
            current = []
            current_length = 0
        current.append(paragraph)
        current_length += paragraph_length

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def _build_idf(documents: list[list[str]]) -> dict[str, float]:
    doc_count = max(len(documents), 1)
    document_frequency: dict[str, int] = {}

    for tokens in documents:
        for token in set(tokens):
            document_frequency[token] = document_frequency.get(token, 0) + 1

    return {
        token: math.log((doc_count + 1) / (frequency + 1)) + 1
        for token, frequency in document_frequency.items()
    }


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    if not tokens:
        return {}

    term_frequency: dict[str, int] = {}
    for token in tokens:
        term_frequency[token] = term_frequency.get(token, 0) + 1

    token_count = len(tokens)
    return {
        token: (count / token_count) * idf.get(token, 1.0)
        for token, count in term_frequency.items()
    }


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0

    common_tokens = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in common_tokens)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _trim_text(text: str, max_chars: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."
