"""AI/ML Tools for Embeddings Search and Web Integration.

Implements EmbeddingsSearchTool as the first prototype tool.
Requires SQL connection for metadata storage/retrieval.
Uses sentence-transformers for embedding, FAISS for vector search.
Assumes 'documents' table exists (created dynamically if not).
Embedding stored as BLOB (pickled numpy array).
"""

import json
import os
import pickle
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.sql_manager import get_connection


class EmbeddingsSearchTool(BaseTool):
    """Embed a query and search stored documents using vector similarity in a local FAISS index.
    Stores/retrieves from SQL DB (title, url, content, embedding as BLOB).
    """

    name: str = "embeddings_search"
    description: str = (
        "Search embedded documents for a query using vector similarity. "
        "Requires prior storage of embeddings in the 'documents' table via other tools."
    )
    parameters: Dict = {
        "type": "object",
        "properties": {
            "connection_id": {
                "type": "string",
                "description": "The connection_id from sql_connect (SQL DB for metadata/embeddings).",
            },
            "query": {
                "type": "string",
                "description": "The search query to embed and search for.",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of top similar results to return (default 5).",
                "default": 5,
            },
            "embedding_model": {
                "type": "string",
                "description": "Sentence-transformers model name (default 'all-MiniLM-L6-v2').",
                "default": "all-MiniLM-L6-v2",
            },
            "create_if_missing": {
                "type": "boolean",
                "description": "If true, create 'documents' table if it doesn't exist (default false).",
                "default": False,
            },
        },
        "required": ["connection_id", "query"],
    }

    model: Optional[SentenceTransformer] = None
    dim: int = 384  # For all-MiniLM-L6-v2

    def __init__(self):
        super().__init__()

    async def execute(self, **kwargs) -> ToolResult:
        try:
            conn_id = kwargs["connection_id"]
            query = kwargs["query"]
            top_k = kwargs.get("top_k", 5)
            model_name = kwargs.get("embedding_model", "all-MiniLM-L6-v2")
            create_table = kwargs.get("create_if_missing", False)

            conn = get_connection(conn_id)
            inspector = inspect(conn)

            # Ensure 'documents' table exists
            if "documents" not in inspector.get_table_names():
                if not create_table:
                    return self.fail_response(
                        "Table 'documents' not found. Set create_if_missing=true or create manually."
                    )
                else:
                    create_sql = """
                    CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        url TEXT,
                        content TEXT NOT NULL,
                        embedding BLOB
                    )
                    """
                    with conn.connect() as c:
                        c.execute(text(create_sql))
                        c.commit()
                    logger.info("Created 'documents' table.")

            # Load or init model
            if not hasattr(self, "model") or self.model is None:
                self.model = SentenceTransformer(model_name)
                logger.info(f"Loaded embedding model: {model_name}")

            # Embed query
            query_embedding = self.model.encode([query])[0]  # Shape (384,)
            query_embedding = query_embedding.astype("float32")

            # Retrieve all embeddings from DB and build temp FAISS index
            with conn.connect() as c:
                result = c.execute(
                    text("SELECT id, title, url, content, embedding FROM documents")
                )
                rows = result.fetchall()
                if not rows:
                    return self.success_response(
                        {"results": [], "message": "No documents in DB yet."}
                    )

                # Load embeddings as numpy
                embeddings_list = []
                doc_metadata = []  # List of (id, title, url, content)
                for row in rows:
                    doc_id, title, url, content, emb_blob = row
                    if emb_blob:
                        emb = pickle.loads(emb_blob)
                        embeddings_list.append(emb.astype("float32"))
                        doc_metadata.append(
                            {
                                "id": doc_id,
                                "title": title,
                                "url": url,
                                "content": content,
                            }
                        )
                    else:
                        logger.warning(
                            f"Document {doc_id} missing embedding, skipping."
                        )

                if not embeddings_list:
                    return self.fail_response("No documents with embeddings found.")

                embeddings_np = np.array(embeddings_list, dtype="float32")
                n_docs, dim = embeddings_np.shape

                # Build FAISS index (Inner Product for cosine similarity)
                index = faiss.IndexFlatIP(self.dim)
                faiss.normalize_L2(embeddings_np)  # Normalize for cosine
                index.add(embeddings_np)

                # Search
                query_np = np.array([query_embedding], dtype="float32")
                faiss.normalize_L2(query_np)
                distances, indices = index.search(query_np, min(top_k, n_docs))

                # Gather results
                results = []
                for i, idx in enumerate(indices[0]):
                    if idx != -1:
                        doc = doc_metadata[idx]
                        score = distances[0][i]
                        results.append(
                            {
                                "id": doc["id"],
                                "title": doc["title"],
                                "url": doc["url"],
                                "content": (
                                    doc["content"][:200] + "..."
                                    if len(doc["content"]) > 200
                                    else doc["content"]
                                ),
                                "similarity_score": float(score),
                            }
                        )

            logger.info(f"EmbeddingsSearch successful: returned {len(results)} results")
            return self.success_response({"results": results[:top_k]})

        except SQLAlchemyError as e:
            logger.error(f"DB error in EmbeddingsSearch: {str(e)}")
            return self.fail_response(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"EmbeddingsSearch failed: {str(e)}")
            return self.fail_response(f"Search failed: {str(e)}")
