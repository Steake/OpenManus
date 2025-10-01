"""
Real-world demonstration of MarketplaceArbitrageTool (Automated Version).

This script runs all demos automatically without user interaction.
Run with: python app/tool/tests/demo_marketplace_arbitrage_auto.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)

# Import all the test data and functions from the main demo
from demo_marketplace_arbitrage import (
    TEST_PRODUCTS,
    format_currency,
    format_percentage,
    print_header,
    print_section,
    scenario_1_profit_calculation,
    scenario_2_find_opportunities,
    scenario_3_monitor_competition,
    scenario_4_create_listing,
    scenario_5_rate_limiting,
    scenario_6_error_handling,
)

from app.tool.monetization.marketplace_arbitrage import MarketplaceArbitrageTool


async def run_demo_summary(opportunities: List[Dict], profit_example: Dict):
    """Display final summary of the demo."""
    print_header("DEMO SUMMARY", "=")

    print("📊 Scenarios Executed:")
    print("   ✅ Scenario 1: Profit Calculation")
    print("   ✅ Scenario 2: Finding Opportunities")
    print("   ✅ Scenario 3: Competition Monitoring")
    print("   ✅ Scenario 4: Listing Creation")
    print("   ✅ Scenario 5: Rate Limiting & Caching")
    print("   ✅ Scenario 6: Error Handling")
    print()

    print("📈 Key Metrics:")
    print(f"   Products Analyzed:           {len(TEST_PRODUCTS)}")
    print(f"   Profitable Opportunities:    {len(opportunities)}")

    if opportunities:
        avg_margin = sum(o["profit"]["profit_margin"] for o in opportunities) / len(
            opportunities
        )
        print(f"   Average Profit Margin:       {format_percentage(avg_margin)}")

        total_potential_profit = sum(o["profit"]["net_profit"] for o in opportunities)
        print(
            f"   Total Potential Profit:      {format_currency(total_potential_profit)}"
        )

        # Monthly revenue estimate (assuming 1 sale per product per week)
        monthly_revenue = total_potential_profit * 4
        print(
            f"   Est. Monthly Revenue:        {format_currency(monthly_revenue)} (@ 1 sale/product/week)"
        )
    print()

    print("💡 Key Insights:")
    print("   • Higher profit margins on electronics (avg 35%)")
    print("   • AliExpress → Amazon arbitrage shows best ROI")
    print("   • Products with 4.5+ ratings sell faster")
    print("   • Monitor competition weekly for price adjustments")
    print()

    print("🚀 Next Steps:")
    print("   1. Set up accounts on source and target platforms")
    print("   2. Start with 2-3 high-margin products")
    print("   3. Monitor competition and adjust pricing")
    print("   4. Scale up profitable products")
    print("   5. Automate inventory sync and repricing")
    print()

    print("=" * 80)
    print(f"{'Demo completed successfully!':^80}")
    print("=" * 80)


async def main():
    """Run all demo scenarios automatically."""
    print("\n")
    print("=" * 80)
    print(f"{'MARKETPLACE ARBITRAGE TOOL - AUTOMATED DEMO':^80}")
    print(f"{'Automated E-commerce Arbitrage Discovery & Management':^80}")
    print("=" * 80)
    print()
    print("Running all scenarios automatically...")
    print("All data is simulated for demonstration purposes.")
    print()

    try:
        # Run all scenarios
        profit_example = await scenario_1_profit_calculation()
        await asyncio.sleep(1)

        opportunities = await scenario_2_find_opportunities()
        await asyncio.sleep(1)

        await scenario_3_monitor_competition()
        await asyncio.sleep(1)

        await scenario_4_create_listing()
        await asyncio.sleep(1)

        await scenario_5_rate_limiting()
        await asyncio.sleep(1)

        await scenario_6_error_handling()
        await asyncio.sleep(1)

        await run_demo_summary(opportunities, profit_example)

        return 0  # Success

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Error during demo: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
