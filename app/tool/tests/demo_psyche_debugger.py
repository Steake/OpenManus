import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
print("Added project root to sys.path")

import traceback

from app.tool.base import ToolResult
from app.tool.psyche_debugger import PsycheDebugger
from app.tool.python_execute import PythonExecute
from app.tool.tool_collection import create_full_collection


async def main():
    try:
        collection = create_full_collection()
        debugger = collection.get_tool("psyche_debugger")
        python_exec = collection.get_tool("python_execute")
        print(
            "Instantiated PsycheDebugger and PythonExecute from tool collection successfully"
        )

        # Positive mood sample
        positive_code = """
# Well-structured function with good docs.
def happy_sum(n):
    \"\"\"Calculate sum happily.\"\"\"
    total = 0.0  # Positive identifier
    for i in range(n):
        total += i  # Efficient loop
    return total  # Success indicator
        """

        print("Positive sample code prepared")

        # Execute with PythonExecute
        exec_result = await collection.execute(
            name="python_execute", tool_input={"code": positive_code}
        )
        print(
            "Python execution result:",
            (
                exec_result.get("output")
                if exec_result.get("output")
                else exec_result.get("error")
            ),
        )

        # Analyze with PsycheDebugger
        print("Executing PsycheDebugger on positive code...")
        positive_result = await debugger.execute(
            code_content=positive_code,
            analyze_elements=["comments", "identifiers", "nesting"],
        )
        print("Positive analysis completed")
        if (
            positive_result
            and hasattr(positive_result, "output")
            and positive_result.output
        ):
            print(
                "Positive output preview (first 500 chars):",
                str(positive_result.output)[:500],
            )
        elif positive_result and hasattr(positive_result, "error"):
            print("Positive error:", positive_result.error)
        else:
            print("Positive unexpected result:", positive_result)

        # Negative mood sample for error handling demo
        negative_code = """
def frustrating_task(data):
    # No docstring
    if not data:
        raise ValueError("Data missing - failure!")  # Negative exception
    total = 0
    for i in range(10000):  # Inefficient large loop
        total += i * data  # Overcomplicated
        if i % 1000 == 0:
            print("Still grinding...")  # Frustrating output
    return total  # No success note
        """

        print("Negative sample code prepared")

        # Execute with PythonExecute (will timeout or error for demo)
        exec_neg_code = (
            negative_code
            + "\nprint('Running negative function...')\nfrustrating_task([])"
        )  # Will raise error to demo handling
        exec_result_neg = await collection.execute(
            name="python_execute", tool_input={"code": exec_neg_code}
        )
        print(
            "Python execution result (negative):",
            (
                exec_result_neg.get("output")
                if exec_result_neg.get("output")
                else exec_result_neg.get("error")
            ),
        )

        # Analyze with PsycheDebugger
        print("Executing PsycheDebugger on negative code...")
        negative_result = await debugger.execute(
            code_content=negative_code,
            analyze_elements=["comments", "identifiers", "nesting"],
        )
        print("Negative analysis completed")
        if (
            negative_result
            and hasattr(negative_result, "output")
            and negative_result.output
        ):
            print(
                "Negative output preview (first 500 chars):",
                str(negative_result.output)[:500],
            )
        elif negative_result and hasattr(negative_result, "error"):
            print("Negative error:", negative_result.error)
        else:
            print("Negative unexpected result:", negative_result)
    except Exception as e:
        print("Error during execution:", str(e))
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
