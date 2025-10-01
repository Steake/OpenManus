"""Unit tests for ai_ml_tools using in-memory SQLite and mock embeddings."""

import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)

import json
import pickle

import numpy as np
import pytest
from sentence_transformers import SentenceTransformer
from sqlalchemy import text

from app.tool.ai_ml_tools import EmbeddingsSearchTool
from app.tool.base import ToolResult
from app.tool.sql_manager import create_connection, get_connection


@pytest.mark.asyncio
async def test_embeddings_search_create_table():
    """Test that the tool can create the documents table if missing."""
    conn_id = create_connection("sqlite", "", 0, ":memory:", "", "")
    tool = EmbeddingsSearchTool()
    result = await tool.execute(
        connection_id=conn_id,
        query="test query",
        create_if_missing=True,
    )
    assert isinstance(result, ToolResult)
    output = json.loads(result.output)
    assert "results" in output
    assert "message" in output or len(output["results"]) == 0  # No docs yet


@pytest.mark.asyncio
async def test_embeddings_search_with_data():
    """Test search with sample documents and embeddings."""
    # Create connection
    conn_id = create_connection("sqlite", "", 0, ":memory:", "", "")
    engine = get_connection(conn_id)

    # Create table
    with engine.connect() as c:
        c.execute(
            text(
                """
            CREATE TABLE documents (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT,
                content TEXT NOT NULL,
                embedding BYTEA
            )
        """
            )
        )
        c.commit()

    # Load model for embedding
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Sample documents
    docs = [
        {"title": "Doc1", "url": "url1", "content": "This is about machine learning."},
        {"title": "Doc2", "url": "url2", "content": "Python programming basics."},
    ]

    # Embed and insert
    contents = [doc["content"] for doc in docs]
    embeddings = model.encode(contents)
    values = []
    for i, (doc, emb) in enumerate(zip(docs, embeddings)):
        value = doc.copy()
        value["embedding"] = pickle.dumps(emb)
        values.append(value)

    # Insert via raw SQL for test setup
    with engine.connect() as c:
        for value in values:
            columns = ", ".join(value.keys())
            placeholders = ", ".join([f":{k}" for k in value.keys()])
            insert_sql = f"INSERT INTO documents ({columns}) VALUES ({placeholders})"
            c.execute(text(insert_sql), value)
        c.commit()

    # Now test the tool
    tool = EmbeddingsSearchTool()
    result = await tool.execute(
        connection_id=conn_id,
        query="machine learning",
        top_k=1,
    )
    assert isinstance(result, ToolResult)
    output = json.loads(result.output)
    assert "results" in output
    results = output["results"]
    assert len(results) == 1
    assert results[0]["title"] == "Doc1"
    assert results[0]["similarity_score"] > 0.5  # Reasonable similarity for cosine


@pytest.mark.asyncio
async def test_embeddings_search_no_docs():
    """Test search with empty DB."""
    conn_id = create_connection("sqlite", "", 0, ":memory:", "", "")
    tool = EmbeddingsSearchTool()
    result = await tool.execute(
        connection_id=conn_id,
        query="test query",
    )
    assert isinstance(result, ToolResult)
    assert result.error
    assert "Table 'documents' not found" in result.error


if __name__ == "__main__":
    pytest.main([__file__])
