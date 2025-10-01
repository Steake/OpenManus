"""Unit tests for EvolCodeOptimizer tool."""

import ast
from unittest.mock import Mock, patch

import astor
import numpy as np
import pytest

from app.tool.base import ToolResult
from app.tool.evol_optimizer import EvolCodeOptimizer


@pytest.fixture
def sample_code():
    """Simple sum function as sample code."""
    return """
def simple_sum(n):
    total = 0
    for i in range(n):
        total += i
    return total
    """


@pytest.fixture
def optimizer():
    return EvolCodeOptimizer()


@pytest.mark.asyncio
async def test_evol_optimizer_basic_execution(optimizer, sample_code):
    """Test basic execution with mocked fitness to ensure flow works."""
    test_inputs = [5]

    with patch("app.tool.evol_optimizer.timeit") as mock_timeit, patch(
        "app.tool.evol_optimizer.np", mocks=np
    ), patch("app.tool.evol_optimizer.difflib") as mock_diff:

        # Mock exec and fitness to return low values for success
        mock_timeit.timeit.return_value = 0.001
        mock_diff.unified_diff.return_value = ["--- original", "+++ evolved"]

        # Mock deap to simplify - return a dummy best
        with patch.object(optimizer, "evaluate_fitness", return_value=0.001):
            with patch("app.tool.evol_optimizer.creator", Mock()), patch(
                "app.tool.evol_optimizer.tools",
                Mock(select_best=lambda pop, k: [ast.parse(sample_code)]),
            ):

                result = await optimizer.execute(
                    code_content=sample_code,
                    function_name="simple_sum",
                    test_inputs=test_inputs,
                    generations=2,
                    pop_size=2,
                )

        assert isinstance(result, ToolResult)
        assert result.error is None
        output = result.output  # Assuming it's str JSON
        import json

        data = json.loads(output)
        assert "best_evolution" in data
        assert data["best_evolution"]["fitness_score"] == 0.001  # Mocked
        assert "diff_from_original" in data["best_evolution"]


@pytest.mark.asyncio
async def test_evol_optimizer_invalid_function(optimizer, sample_code):
    """Test when function not found."""
    result = await optimizer.execute(
        code_content=sample_code, function_name="nonexistent", generations=1
    )
    assert result.error is not None
    assert "not found" in result.error


@pytest.mark.asyncio
async def test_evol_optimizer_complexity_fitness(optimizer, sample_code):
    """Test complexity fitness with mocked nesting."""
    with patch.object(optimizer, "_get_nesting_depth", return_value=2):
        with patch(
            "app.tool.evol_optimizer.ast.parse", return_value=ast.parse(sample_code)
        ):
            result = await optimizer.execute(
                code_content=sample_code,
                function_name="simple_sum",
                fitness_type="complexity",
                generations=1,
            )

    assert result.error is None
    data = json.loads(result.output)
    assert data["best_evolution"]["fitness_score"] == 2  # Mocked depth


@pytest.mark.asyncio
async def test_evol_optimizer_mutation_validity(optimizer):
    """Test mutation produces valid AST, mocked."""
    dummy_ast = ast.parse("def dummy(): pass")
    mutated = optimizer.mutate_individual(dummy_ast, 0.5)
    assert isinstance(mutated, ast.AST)  # Basic validity


if __name__ == "__main__":
    pytest.main([__file__])
