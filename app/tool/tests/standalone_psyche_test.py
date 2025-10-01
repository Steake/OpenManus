"""
Standalone test for PsycheDebugger without package imports.
Copies the class definition and tests core functionality.
"""

import ast
import json
import tokenize
from io import BytesIO
from typing import Any, Dict, List

import numpy as np
from pydantic import BaseModel
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class ToolResult(BaseModel):
    """Simple ToolResult for standalone testing."""

    output: Any = None
    error: str = None


class BaseTool(BaseModel):
    """Minimal BaseTool for standalone."""

    name: str = "base"
    description: str = "base"
    parameters: Any = None

    def success_response(self, data):
        if isinstance(data, dict):
            text = json.dumps(data, indent=2)
        else:
            text = str(data)
        return ToolResult(output=text)

    def fail_response(self, msg: str):
        return ToolResult(error=msg)


class PsycheDebugger(BaseTool):
    name: str = "psyche_debugger"
    description: str = (
        "Profile code 'mood' via sentiment on comments/identifiers and structure analysis. "
        "Suggests refactors for 'stressed' sections. Provide code_paths or code_content."
    )
    parameters: Dict = {
        "type": "object",
        "properties": {
            "code_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of file paths to analyze (optional if code_content given).",
            },
            "code_content": {
                "type": "string",
                "description": "Direct code string to analyze (alternative to paths).",
            },
            "analyze_elements": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Elements: 'comments', 'identifiers', 'nesting' (default all).",
                "default": ["comments", "identifiers", "nesting"],
            },
            "model": {
                "type": "string",
                "description": "Sentiment model: 'vader' (default).",
                "default": "vader",
            },
            "threshold": {
                "type": "number",
                "description": "Alert threshold for negative moods (-1 to 1, default -0.1).",
                "default": -0.1,
            },
        },
        "required": [],
    }

    def __init__(self):
        super().__init__()
        self.analyzer = SentimentIntensityAnalyzer()
        self.negative_words = {"bug", "error", "fail", "crash"}

    def extract_comments(self, code: str) -> List[str]:
        """Extract comments from code string."""
        comments = []
        try:
            io_obj = BytesIO(code.encode("utf-8"))
            for token in tokenize.tokenize(io_obj.readline):
                if token.type == tokenize.COMMENT:
                    comments.append(token.string.strip("#").strip())
        except tokenize.TokenError:
            pass
        return comments

    def extract_identifiers(self, code: str) -> List[str]:
        """Extract var/class/func names via ast."""
        try:
            tree = ast.parse(code)
            identifiers = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Name, ast.FunctionDef, ast.ClassDef)):
                    identifiers.append(
                        node.id
                        if hasattr(node, "id")
                        else getattr(node, "name", str(node))
                    )
            return identifiers
        except SyntaxError:
            return []

    def get_nesting_moods(self, tree: ast.AST) -> Dict:
        """Calculate mood from structure: high nesting = anxious."""
        max_nest = 0
        moods = {"nesting_score": 0.0}
        for node in ast.walk(tree):
            depth = self._calc_nesting(node)
            if depth > max_nest:
                max_nest = depth
        moods["nesting_score"] = -0.05 * max_nest  # Negative for deep
        return moods

    def _calc_nesting(self, node: ast.AST, depth: int = 0) -> int:
        return depth + max(
            (
                self._calc_nesting(child, depth + 1)
                for child in ast.iter_child_nodes(node)
            ),
            default=depth,
        )

    def generate_suggestions(self, profile: Dict) -> List[Dict]:
        """Rule-based suggestions from moods."""
        suggestions = []
        if (
            profile.get("overall_sentiment") == "anxious"
            and profile.get("neg_comments", 0) > 2
        ):
            suggestions.append(
                {
                    "issue_type": "negative_comments",
                    "description": "Excess negative comments may indicate stressed code; add positive docs.",
                    "proposed_change": "# Improved: This function is robust and efficient.",
                    "diff_preview": "- # This is buggy\n+ # This function handles inputs gracefully.",
                }
            )
        if profile.get("nesting_score", 0) < -0.2:
            suggestions.append(
                {
                    "issue_type": "deep_nesting",
                    "description": "High nesting causes anxiety; extract methods.",
                    "proposed_change": "def extract_inner():\n    pass\n# Replace nested block with extract_inner()",
                    "diff_preview": "  # Deep if/for\n+  extract_inner()",
                }
            )
        return suggestions

    async def execute(self, **kwargs) -> ToolResult:
        try:
            code_paths = kwargs.get("code_paths", [])
            code_content = kwargs.get("code_content", "")
            elements = kwargs.get(
                "analyze_elements", ["comments", "identifiers", "nesting"]
            )
            model = kwargs.get("model", "vader")
            threshold = kwargs.get("threshold", -0.1)

            all_code = code_content
            # Skip file reading for standalone, assume code_content
            if not all_code.strip():
                return self.fail_response("No code provided.")

            # Analyze
            tree = ast.parse(all_code)
            comments = self.extract_comments(all_code) if "comments" in elements else []
            ids = (
                self.extract_identifiers(all_code) if "identifiers" in elements else []
            )
            struct_moods = (
                self.get_nesting_moods(tree)
                if "nesting" in elements
                else {"nesting_score": 0.0}
            )

            # Sentiment scores
            comment_scores = [
                self.analyzer.polarity_scores(c)["compound"] for c in comments
            ]
            id_scores = [
                self.analyzer.polarity_scores(id.lower())["compound"]
                for id in ids
                if id.lower() not in self.negative_words
            ]

            avg_comment = np.mean(comment_scores) if comment_scores else 0
            avg_id = np.mean(id_scores) if id_scores else 0
            overall = (
                avg_comment * 0.4 + avg_id * 0.3 + struct_moods["nesting_score"] * 0.3
            )

            sectional = {
                "comments": {
                    "pos": len([s for s in comment_scores if s > 0.1])
                    / max(len(comment_scores), 1),
                    "neg": len([s for s in comment_scores if s < -0.1]),
                    "compound_avg": avg_comment,
                },
                "identifiers": {
                    "pos": len([s for s in id_scores if s > 0.1])
                    / max(len(id_scores), 1),
                    "neg": len(
                        [
                            id
                            for id in ids
                            if set(self.negative_words) & set(id.lower().split())
                        ]
                    ),
                    "compound_avg": avg_id,
                },
                "nesting": struct_moods,
            }

            mood = (
                "anxious"
                if overall < threshold
                else "balanced" if overall < 0.3 else "optimistic"
            )

            reports = []
            if avg_comment < threshold:
                reports.append(
                    {
                        "location": {"section": "comments"},
                        "mood": "depressed",
                        "score": avg_comment,
                        "evidence": "\n".join(comments[:3]),
                    }
                )

            suggestions = self.generate_suggestions(
                {
                    "overall_sentiment": mood,
                    "neg_comments": len([s for s in comment_scores if s < threshold]),
                    "nesting_score": struct_moods["nesting_score"],
                }
            )

            result = {
                "mood_profile": {
                    "overall_sentiment": mood,
                    "overall_score": overall,
                    "sectional_scores": sectional,
                },
                "empathy_report": reports,
                "refactor_suggestions": suggestions,
            }

            return self.success_response(result)

        except Exception as e:
            return self.fail_response(f"Debug failed: {str(e)}")


# Standalone tests
def test_extract_comments():
    debugger = PsycheDebugger()
    code = """
# This is a comment
print("code")
# Another comment
"""
    comments = debugger.extract_comments(code)
    assert len(comments) >= 2
    assert "This is a comment" in comments
    print("test_extract_comments passed")


def test_extract_identifiers():
    debugger = PsycheDebugger()
    code = "def test_func(): x = 1"
    ids = debugger.extract_identifiers(code)
    assert "test_func" in ids
    assert "x" in ids
    print("test_extract_identifiers passed")


def test_nesting_calc():
    debugger = PsycheDebugger()
    code = """
def outer():
    if True:
        while True:
            pass
"""
    tree = ast.parse(code)
    moods = debugger.get_nesting_moods(tree)
    assert moods["nesting_score"] < 0
    print("test_nesting_calc passed")


def test_execute_positive():
    debugger = PsycheDebugger()
    sample_code = """
# Well-structured function with good docs.
def happy_sum(n):
    total = 0.0  # Positive identifier
    for i in range(n):
        total += i  # Efficient loop
    return total  # Success indicator
    """
    result = asyncio.run(debugger.execute(code_content=sample_code))
    assert result.error is None
    data = json.loads(result.output)
    assert data["mood_profile"]["overall_sentiment"] in ["balanced", "optimistic"]
    print("test_execute_positive passed")


def test_execute_negative():
    debugger = PsycheDebugger()
    sample_code = """
# Buggy code!
def fail_hard():
    error_var = 0
    if bad_condition:
        raise CrashError
"""
    result = asyncio.run(debugger.execute(code_content=sample_code, threshold=-0.05))
    assert result.error is None
    data = json.loads(result.output)
    assert data["mood_profile"]["overall_sentiment"] == "anxious"
    print("test_execute_negative passed")


def test_empty_code():
    debugger = PsycheDebugger()
    result = asyncio.run(debugger.execute(code_content=""))
    assert result.error is not None
    assert "No code provided" in result.error
    print("test_empty_code passed")


if __name__ == "__main__":
    import asyncio

    print("Running standalone PsycheDebugger tests...")
    test_extract_comments()
    test_extract_identifiers()
    test_nesting_calc()
    asyncio.run(test_execute_positive())  # Note: execute is async, so run with asyncio
    asyncio.run(test_execute_negative())
    asyncio.run(test_empty_code())
    print("All tests completed successfully!")
