"""Unit tests for PsycheDebugger tool."""

import ast
from unittest.mock import Mock, patch

import numpy as np
import pytest
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.tool.base import ToolResult
from app.tool.psyche_debugger import PsycheDebugger


@pytest.fixture
def sample_positive_code():
    """Code with positive/neutral elements."""
    return """
# Well-structured function with good docs.
def happy_sum(n):
    total = 0.0  # Positive identifier
    for i in range(n):
        total += i  # Efficient loop
    return total  # Success indicator
    """


@pytest.fixture
def sample_negative_code():
    """Code with negative elements."""
    return """
# Buggy and error-prone code beware!
def fail_hard(n):
    buggy_total = 0  # Problematic
    if n < 0:
        raise ErrorException  # Crash waiting
    for i in range(n if n > 0 else 0):  # Complex conditional
        buggy_total += i * -1  # Negative logic
    return buggy_total  # Failure possible
    """


@pytest.fixture
def debugger():
    return PsycheDebugger()


@pytest.mark.asyncio
async def test_psyche_debugger_positive_mood(debugger, sample_positive_code):
    """Test analysis on positive code yields balanced/optimistic mood."""
    with patch.object(
        debugger.analyzer, "polarity_scores", return_value={"compound": 0.3}
    ):
        result = await debugger.execute(
            code_content=sample_positive_code,
            analyze_elements=["comments", "identifiers"],
        )

    assert isinstance(result, ToolResult)
    assert result.error is None
    import json

    data = json.loads(result.output)
    assert data["mood_profile"]["overall_sentiment"] in ["balanced", "optimistic"]
    assert data["mood_profile"]["overall_score"] > -0.1  # Above threshold


@pytest.mark.asyncio
async def test_psyche_debugger_negative_mood_suggestions(
    debugger, sample_negative_code
):
    """Test negative code generates anxious mood and suggestions."""
    mock_negative_scores = [{"compound": -0.6}]
    mock_id_scores = [{"compound": -0.4}]

    with patch.object(debugger.analyzer, "polarity_scores") as mock_analyzer:
        mock_analyzer.side_effect = lambda x: (
            mock_negative_scores[0] if "Buggy" in x else mock_id_scores[0]
        )
        with patch.object(debugger, "_calc_nesting", return_value=3):  # Deep nesting
            result = await debugger.execute(
                code_content=sample_negative_code,
                analyze_elements=["comments", "identifiers", "nesting"],
                threshold=-0.5,
            )

    data = json.loads(result.output)
    assert data["mood_profile"]["overall_sentiment"] == "anxious"
    assert data["mood_profile"]["overall_score"] < -0.1
    assert len(data["refactor_suggestions"]) >= 1  # Suggestions generated


@pytest.mark.asyncio
async def test_psyche_debugger_empty_code(debugger):
    """Test with empty code."""
    result = await debugger.execute(code_content="")
    assert result.error is not None
    assert "No code provided." in result.error


@pytest.mark.asyncio
async def test_psyche_debugger_extract_elements(debugger, sample_positive_code):
    """Test extraction functions work."""
    comments = debugger.extract_comments(sample_positive_code)
    assert len(comments) > 0  # At least doc-like comment

    ids = debugger.extract_identifiers(sample_positive_code)
    assert "happy_sum" in ids
    assert "total" in ids


@pytest.mark.asyncio
async def test_psyche_debugger_structure_mood(debugger, sample_positive_code):
    """Test nesting mood calculation."""
    tree = ast.parse(sample_positive_code)
    result = await debugger.execute(
        code_content=sample_positive_code, analyze_elements=["nesting"]
    )
    data = json.loads(result.output)
    assert data["mood_profile"]["sectional_scores"]["nesting"]["nesting_score"] <= 0


if __name__ == "__main__":
    pytest.main([__file__])
