"""
Tool for psychological profiling of code using sentiment analysis.
Analyzes comments, identifiers, structures for 'moods', suggests empathetic refactors.
Uses vaderSentiment for text, ast/tokenize for extraction, rule-based for structure moods.
"""

import ast
import tokenize
from io import BytesIO
from typing import Any, Dict, List

import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.logger import logger
from app.tool.base import BaseTool, ToolResult


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
        "required": [],  # At least one of code_paths or code_content
    }

    def __init__(self):
        super().__init__()
        # Use object.__setattr__ to bypass Pydantic validation for runtime attributes
        object.__setattr__(self, "analyzer", SentimentIntensityAnalyzer())
        object.__setattr__(
            self, "negative_words", {"bug", "error", "fail", "crash"}
        )  # For identifiers

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
                        node.id if hasattr(node, "id") else str(node.name)
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
        if profile["overall_sentiment"] == "anxious" and profile["neg_comments"] > 2:
            suggestions.append(
                {
                    "issue_type": "negative_comments",
                    "description": "Excess negative comments may indicate stressed code; add positive docs.",
                    "proposed_change": "# Improved: This function is robust and efficient.",
                    "diff_preview": "- # This is buggy\n+ # This function handles inputs gracefully.",
                }
            )
        if profile["nesting_score"] < -0.2:
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
            if code_paths and not code_content:
                # Inline read for simplicity; in full, use read_file tool
                for path in code_paths[:2]:  # Limit
                    with open(path, "r") as f:  # Assume local for tool, but warn
                        all_code += f.read() + "\n"
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
            # Similar for others

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

            logger.info(f"Psyche debug complete: mood {mood}, score {overall:.2f}")
            return self.success_response(result)

        except Exception as e:
            logger.error(f"PsycheDebugger failed: {str(e)}")
            return self.fail_response(f"Debug failed: {str(e)}")
