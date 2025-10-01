"""Unit tests for NeuroPatternMatcher tool."""

import ast
from unittest.mock import Mock, patch

import numpy as np
import pytest
from networkx import DiGraph

from app.tool.base import ToolResult
from app.tool.neuro_pattern_matcher import NeuroPatternMatcher


@pytest.fixture
def sample_graph():
    """Sample networkx graph for testing."""
    G = DiGraph()
    G.add_node("observer_func", type="FunctionDef", lineno=1)
    G.add_node("Subject", type="ClassDef", lineno=5)
    G.add_edge("Subject", "observer_func", relation="calls")
    return G


@pytest.fixture
def matcher():
    return NeuroPatternMatcher()


@pytest.mark.asyncio
async def test_neuro_pattern_matcher_basic(matcher, sample_graph):
    """Test basic execution with mocked embeddings."""
    code_paths = ["dummy.py"]

    with patch.object(
        matcher, "get_embeddings", return_value=np.array([[0.8, 0.2], [0.3, 0.7]])
    ), patch("networkx.DiGraph", return_value=sample_graph):

        result = await matcher.execute(
            code_paths=code_paths, target_patterns=["observer"], suggest_novel=False
        )

    assert isinstance(result, ToolResult)
    assert result.error is None
    import json

    data = json.loads(result.output)
    assert "matched_patterns" in data
    assert len(data["matched_patterns"]) > 0  # At least one mock match
    assert "code_graph_summary" in data
    assert data["code_graph_summary"]["edges"] == 1  # From sample


@pytest.mark.asyncio
async def test_neuro_pattern_matcher_novel_suggestions(matcher):
    """Test novel suggestion generation with clustering."""
    code_paths = ["test.py"]
    node_embeds_mock = np.array([[1, 0], [1, 0], [0, 1]])  # Two clusters

    with patch.object(matcher, "get_embeddings") as mock_embed:
        mock_embed.return_value = node_embeds_mock
        # Mock build_graph to return empty but nodes collected
        with patch("app.tool.neuro_pattern_matcher.nx.DiGraph"):
            result = await matcher.execute(code_paths=code_paths, suggest_novel=True)

    data = json.loads(result.output)
    assert "novel_suggestions" in data
    assert len(data["novel_suggestions"]) >= 1  # Clustering produces


@pytest.mark.asyncio
async def test_neuro_pattern_matcher_empty_paths(matcher):
    """Test with empty code paths."""
    result = await matcher.execute(code_paths=[])
    assert isinstance(result, ToolResult)
    assert result.error is None
    data = json.loads(result.output)
    assert data["matched_patterns"] == []
    assert data["novel_suggestions"] == []


@pytest.mark.asyncio
async def test_neuro_pattern_matcher_build_graph(matcher):
    """Test graph building from sample code."""
    code = """
def factory(): return "object"
class Singleton: pass
    """
    G = matcher.build_code_graph(code)
    assert isinstance(G, DiGraph)
    assert G.has_node("factory")
    assert G.nodes["factory"]["type"] == "FunctionDef"


if __name__ == "__main__":
    pytest.main([__file__])
