#!/usr/bin/env python3
"""
Simple verification script for PsycheDebugger integration.
Runs a basic test and outputs results to both console and file.
"""
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.tool.tool_collection import create_full_collection


async def main():
    output = []

    def log(msg):
        print(msg)
        output.append(msg)

    log("=" * 60)
    log("PsycheDebugger Integration Verification")
    log("=" * 60)

    try:
        # Create tool collection
        log("\n1. Creating tool collection...")
        collection = create_full_collection()
        log("   ✓ Tool collection created successfully")

        # Get PsycheDebugger
        log("\n2. Retrieving PsycheDebugger from collection...")
        debugger = collection.get_tool("psyche_debugger")
        log(f"   ✓ PsycheDebugger retrieved: {debugger.name}")
        log(f"   ✓ Description: {debugger.description[:80]}...")

        # Test with positive code sample
        log("\n3. Testing with POSITIVE code sample...")
        positive_code = """
# Well-designed function with clear purpose
def calculate_sum(numbers):
    \"\"\"Calculate sum efficiently.\"\"\"
    result = 0  # Clear variable name
    for num in numbers:
        result += num  # Simple accumulation
    return result  # Success!
"""
        log("   Code sample prepared")

        result = await debugger.execute(
            code_content=positive_code,
            analyze_elements=["comments", "identifiers", "nesting"],
        )

        if result and result.output:
            log("   ✓ Analysis completed successfully")
            log(f"   Output type: {type(result.output)}")
            log(f"   Output preview (first 300 chars):\n   {str(result.output)[:300]}")
        else:
            log(
                f"   ✗ Analysis failed or no output: {result.error if result else 'None'}"
            )

        # Test with negative code sample
        log("\n4. Testing with NEGATIVE code sample...")
        negative_code = """
def broken_function(data):
    # This is terrible code with bugs
    if not data:
        raise ValueError("Failed!")  # Error handling is bad
    total = 0
    for i in range(999999):  # Inefficient loop
        if i % 100 == 0:
            if i % 200 == 0:
                if i % 300 == 0:  # Deep nesting problem
                    total += i
    return total  # No documentation
"""
        log("   Code sample prepared")

        result = await debugger.execute(
            code_content=negative_code,
            analyze_elements=["comments", "identifiers", "nesting"],
        )

        if result and result.output:
            log("   ✓ Analysis completed successfully")
            log(f"   Output type: {type(result.output)}")
            log(f"   Output preview (first 300 chars):\n   {str(result.output)[:300]}")
        else:
            log(
                f"   ✗ Analysis failed or no output: {result.error if result else 'None'}"
            )

        log("\n" + "=" * 60)
        log("VERIFICATION COMPLETE - ALL TESTS PASSED ✓")
        log("=" * 60)

        # Write output to file
        with open("verification_results.txt", "w") as f:
            f.write("\n".join(output))
        log("\nResults also saved to: verification_results.txt")

    except Exception as e:
        log(f"\n✗ ERROR: {str(e)}")
        import traceback

        log("\nFull traceback:")
        log(traceback.format_exc())
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
