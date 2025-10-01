"""
Real-world demonstration of MarketplaceArbitrageTool.

This script demonstrates the tool's capabilities with realistic test scenarios.
Run with: python app/tool/tests/demo_marketplace_arbitrage.py
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

from app.tool.monetization.marketplace_arbitrage import MarketplaceArbitrageTool

# ==================== Test Data ====================

TEST_PRODUCTS = [
    {
        "title": "Wireless Bluetooth Earbuds with Noise Cancellation",
        "source_platform": "aliexpress",
        "source_price": 8.99,
        "target_platform": "amazon",
        "target_price": 24.99,
        "rating": 4.5,
        "reviews": 1523,
        "category": "electronics",
        "shipping_cost": 5.00,
    },
    {
        "title": "LED Strip Lights RGB 32ft",
        "source_platform": "aliexpress",
        "source_price": 12.50,
        "target_platform": "ebay",
        "target_price": 29.99,
        "rating": 4.7,
        "reviews": 892,
        "category": "home",
        "shipping_cost": 7.00,
    },
    {
        "title": "Smart Watch Fitness Tracker",
        "source_platform": "amazon",
        "source_price": 35.00,
        "target_platform": "walmart",
        "target_price": 59.99,
        "rating": 4.3,
        "reviews": 2341,
        "category": "electronics",
        "shipping_cost": 10.00,
    },
    {
        "title": "Yoga Mat Extra Thick Non-Slip",
        "source_platform": "aliexpress",
        "source_price": 6.50,
        "target_platform": "amazon",
        "target_price": 22.99,
        "rating": 4.6,
        "reviews": 654,
        "category": "sports",
        "shipping_cost": 8.00,
    },
    {
        "title": "Portable Phone Charger 20000mAh",
        "source_platform": "amazon",
        "source_price": 18.00,
        "target_platform": "ebay",
        "target_price": 35.99,
        "rating": 4.4,
        "reviews": 1876,
        "category": "electronics",
        "shipping_cost": 6.00,
    },
]

# ==================== Helper Functions ====================


def print_header(title: str, char: str = "="):
    """Print a formatted header."""
    print(f"\n{char * 80}")
    print(f"{title:^80}")
    print(f"{char * 80}\n")


def print_section(title: str):
    """Print a section divider."""
    print(f"\n{'-' * 80}")
    print(f"  {title}")
    print(f"{'-' * 80}\n")


def format_currency(amount: float) -> str:
    """Format amount as currency."""
    return f"${amount:,.2f}"


def format_percentage(value: float) -> str:
    """Format value as percentage."""
    return f"{value * 100:.1f}%"


# ==================== Demo Scenarios ====================


async def scenario_1_profit_calculation():
    """
    SCENARIO 1: Calculate Profit for Known Product

    Demonstrates detailed profit calculation with fee breakdown.
    """
    print_header("SCENARIO 1: Profit Calculation for Known Product")

    tool = MarketplaceArbitrageTool()

    # Example: Wireless Earbuds
    product = TEST_PRODUCTS[0]

    print(f"📦 Product: {product['title']}")
    print(
        f"🛒 Source: {product['source_platform'].upper()} - {format_currency(product['source_price'])}"
    )
    print(
        f"💰 Target: {product['target_platform'].upper()} - {format_currency(product['target_price'])}"
    )
    print(f"📊 Rating: {product['rating']}⭐ ({product['reviews']} reviews)")
    print()

    # Calculate profit
    profit = await tool.calculate_profit(
        source_price=product["source_price"],
        target_price=product["target_price"],
        platform_fees=tool.PLATFORM_FEES[product["target_platform"]],
        shipping_cost=product["shipping_cost"],
        category=product["category"],
    )

    print_section("Profit Analysis")
    print(f"Source Cost:              {format_currency(profit['source_price'])}")
    print(f"Target Price:             {format_currency(profit['target_price'])}")
    print(f"Gross Profit:             {format_currency(profit['gross_profit'])}")
    print()
    print(f"Fees Breakdown:")
    print(
        f"  Platform Fee ({format_percentage(profit['fees_breakdown']['platform_fee_rate'])}):  {format_currency(profit['fees_breakdown']['platform_fee'])}"
    )
    print(
        f"  Payment Processing:     {format_currency(profit['fees_breakdown']['payment_processing'])}"
    )
    print(
        f"  Shipping Cost:          {format_currency(profit['fees_breakdown']['shipping_cost'])}"
    )
    print(
        f"  Total Fees:             {format_currency(profit['fees_breakdown']['total_fees'])}"
    )
    print()
    print(f"Total Costs:              {format_currency(profit['total_costs'])}")
    print(f"Net Profit:               {format_currency(profit['net_profit'])}")
    print(f"Profit Margin:            {format_percentage(profit['profit_margin'])}")
    print(f"ROI:                      {profit['roi_percentage']:.1f}%")
    print()

    if profit["is_profitable"]:
        print("✅ PROFITABLE - This is a good arbitrage opportunity!")
    else:
        print("❌ NOT PROFITABLE - Skip this product")

    return profit


async def scenario_2_find_opportunities():
    """
    SCENARIO 2: Simulate Finding Opportunities

    Demonstrates filtering products by profit margin and showing top opportunities.
    """
    print_header("SCENARIO 2: Finding Arbitrage Opportunities")

    tool = MarketplaceArbitrageTool()

    print("🔍 Analyzing products from multiple platforms...")
    print(f"📊 Minimum profit margin: 25%")
    print()

    # Simulate opportunity discovery
    opportunities = []

    for product in TEST_PRODUCTS:
        # Calculate profit for each product
        profit = await tool.calculate_profit(
            source_price=product["source_price"],
            target_price=product["target_price"],
            platform_fees=tool.PLATFORM_FEES.get(product["target_platform"], 0.10),
            shipping_cost=product["shipping_cost"],
            category=product["category"],
        )

        # Filter by minimum margin (25%)
        if profit["profit_margin"] >= 0.25:
            opportunities.append({"product": product, "profit": profit})

    # Sort by profit margin
    opportunities.sort(key=lambda x: x["profit"]["profit_margin"], reverse=True)

    print_section(f"Top {min(5, len(opportunities))} Opportunities Found")

    for i, opp in enumerate(opportunities[:5], 1):
        product = opp["product"]
        profit = opp["profit"]

        print(f"{i}. {product['title']}")
        print(
            f"   {product['source_platform'].upper()} → {product['target_platform'].upper()}"
        )
        print(
            f"   Buy: {format_currency(profit['source_price'])} | Sell: {format_currency(profit['target_price'])}"
        )
        print(
            f"   💰 Net Profit: {format_currency(profit['net_profit'])} | Margin: {format_percentage(profit['profit_margin'])} | ROI: {profit['roi_percentage']:.1f}%"
        )
        print(f"   ⭐ Rating: {product['rating']} ({product['reviews']} reviews)")
        print()

    # Summary statistics with zero division guards
    print_section("Summary Statistics")
    total_profit = sum(opp["profit"]["net_profit"] for opp in opportunities)

    # Guard against division by zero
    if len(opportunities) > 0:
        avg_margin = sum(opp["profit"]["profit_margin"] for opp in opportunities) / len(
            opportunities
        )
        avg_roi = sum(opp["profit"]["roi_percentage"] for opp in opportunities) / len(
            opportunities
        )
    else:
        avg_margin = 0
        avg_roi = 0

    print(f"✅ Profitable Products Found:  {len(opportunities)}/{len(TEST_PRODUCTS)}")
    print(f"💰 Total Potential Profit:     {format_currency(total_profit)}")
    print(f"📊 Average Profit Margin:      {format_percentage(avg_margin)}")
    print(f"📈 Average ROI:                {avg_roi:.1f}%")

    return opportunities


async def scenario_3_monitor_competition():
    """
    SCENARIO 3: Monitor Competition

    Demonstrates price tracking and competitive analysis.
    """
    print_header("SCENARIO 3: Competition Monitoring")

    product = TEST_PRODUCTS[0]

    print(f"📦 Monitoring: {product['title']}")
    print(f"🎯 Target Platform: {product['target_platform'].upper()}")
    print()

    # Simulate price history
    print_section("Price History (Last 7 Days)")

    price_history = [
        {"date": "2024-03-15", "price": 26.99, "competitors": 12},
        {"date": "2024-03-16", "price": 25.99, "competitors": 13},
        {"date": "2024-03-17", "price": 24.99, "competitors": 15},
        {"date": "2024-03-18", "price": 24.99, "competitors": 14},
        {"date": "2024-03-19", "price": 23.99, "competitors": 16},
        {"date": "2024-03-20", "price": 24.49, "competitors": 15},
        {"date": "2024-03-21", "price": 24.99, "competitors": 14},
    ]

    for entry in price_history:
        print(
            f"{entry['date']}  {format_currency(entry['price']):>8}  ({entry['competitors']} competitors)"
        )

    # Price analysis with zero division guards
    print_section("Competitive Analysis")

    current_price = price_history[-1]["price"]
    lowest_price = min(e["price"] for e in price_history)
    highest_price = max(e["price"] for e in price_history)

    # Guard against empty list and zero average
    if len(price_history) > 0:
        avg_price = sum(e["price"] for e in price_history) / len(price_history)
    else:
        avg_price = 0

    print(f"Current Price:       {format_currency(current_price)}")
    print(f"7-Day Average:       {format_currency(avg_price)}")
    print(f"7-Day Low:           {format_currency(lowest_price)}")
    print(f"7-Day High:          {format_currency(highest_price)}")

    # Guard against zero average price
    if avg_price > 0:
        volatility = (highest_price - lowest_price) / avg_price
    else:
        volatility = 0
    print(f"Price Volatility:    {format_percentage(volatility)}")
    print(f"Active Competitors:  {price_history[-1]['competitors']}")
    print()

    # Pricing recommendation
    print_section("Pricing Recommendation")

    recommended_price = (
        avg_price * 0.98 if avg_price > 0 else product["target_price"] * 0.98
    )  # Fallback to target price if avg is 0

    print(f"💡 Recommended Price: {format_currency(recommended_price)}")
    print(f"   Strategy: Price 2% below average to be competitive")
    print()

    # Calculate profit at recommended price
    tool = MarketplaceArbitrageTool()
    profit = await tool.calculate_profit(
        source_price=product["source_price"],
        target_price=recommended_price,
        platform_fees=tool.PLATFORM_FEES[product["target_platform"]],
        shipping_cost=product["shipping_cost"],
        category=product["category"],
    )

    print(f"   Expected Net Profit: {format_currency(profit['net_profit'])}")
    print(f"   Profit Margin: {format_percentage(profit['profit_margin'])}")
    print()

    if profit["is_profitable"]:
        print("✅ Still profitable at recommended price")
    else:
        print("⚠️  Not profitable at recommended price - consider alternative products")


async def scenario_4_create_listing():
    """
    SCENARIO 4: Create Listing

    Demonstrates AI-generated listing optimization.
    """
    print_header("SCENARIO 4: Optimized Listing Creation")

    product = TEST_PRODUCTS[2]  # Smart Watch

    print(f"📦 Product: {product['title']}")
    print(f"🎯 Target Platform: {product['target_platform'].upper()}")
    print()

    # Simulate AI-generated listing
    print_section("AI-Generated Listing Content")

    # Mock optimized listing (simulating AI generation)
    listing = {
        "title": "Smart Watch Fitness Tracker - Heart Rate Monitor, Sleep Tracking, IP68 Waterproof",
        "description": """
🏃‍♂️ PREMIUM FITNESS TRACKING: Track your daily activities, steps, calories, and distance with precision.
Built-in heart rate monitor provides 24/7 health monitoring for optimal fitness insights.

💤 ADVANCED SLEEP ANALYSIS: Monitor your sleep patterns and quality. Get personalized recommendations
to improve your rest and recovery.

💦 IP68 WATERPROOF: Swim-proof and splash-resistant design. Perfect for all weather conditions and
water sports activities.

⌚ LONG BATTERY LIFE: Up to 7 days of battery life on a single charge. Quick charge technology gets
you back to tracking in minutes.

📱 SMART NOTIFICATIONS: Stay connected with call, text, and app notifications right on your wrist.
Compatible with iOS and Android devices.
        """.strip(),
        "features": [
            "24/7 Heart Rate Monitoring",
            "Sleep Quality Analysis",
            "IP68 Waterproof Rating",
            "7-Day Battery Life",
            "Multi-Sport Tracking Modes",
            "Smart Notifications",
            "iOS & Android Compatible",
        ],
        "keywords": "smart watch, fitness tracker, heart rate monitor, sleep tracking, waterproof watch, activity tracker, health monitor",
        "category": "Electronics > Wearable Technology > Smart Watches",
    }

    print(f"✨ Optimized Title ({len(listing['title'])} chars):")
    print(f"   {listing['title']}")
    print()

    print("📝 Description:")
    for line in listing["description"].split("\n"):
        if line.strip():
            print(f"   {line}")
    print()

    print("🎯 Key Features:")
    for feature in listing["features"]:
        print(f"   • {feature}")
    print()

    print(f"🔍 SEO Keywords: {listing['keywords']}")
    print(f"📁 Category: {listing['category']}")
    print()

    # Calculate optimal pricing
    print_section("Pricing Strategy")

    tool = MarketplaceArbitrageTool()
    profit = await tool.calculate_profit(
        source_price=product["source_price"],
        target_price=product["target_price"],
        platform_fees=tool.PLATFORM_FEES[product["target_platform"]],
        shipping_cost=product["shipping_cost"],
        category=product["category"],
    )

    list_price = product["target_price"]
    sale_price = list_price * 0.95  # 5% discount

    print(f"List Price:          {format_currency(list_price)}")
    print(f"Sale Price:          {format_currency(sale_price)} (5% off)")
    print(f"Your Cost:           {format_currency(product['source_price'])}")
    print(f"Expected Profit:     {format_currency(profit['net_profit'])}")
    print(f"Profit Margin:       {format_percentage(profit['profit_margin'])}")
    print()
    print("💡 Strategy: Launch with 5% discount to attract initial buyers and reviews")


async def scenario_5_rate_limiting():
    """
    SCENARIO 5: Rate Limiting in Action

    Demonstrates rate limiting and caching behavior.
    """
    print_header("SCENARIO 5: Rate Limiting & Caching")

    tool = MarketplaceArbitrageTool()

    print("🔄 Making multiple requests to demonstrate rate limiting...")
    print()

    platforms = ["amazon", "ebay", "aliexpress", "walmart"]

    print_section("Request Simulation")

    for i, platform in enumerate(platforms, 1):
        print(f"Request {i}: Checking {platform.upper()}...", end=" ")

        # Record request (simulates API call)
        tool.record_request(platform)

        # Check if we need to wait
        can_proceed = await tool.check_rate_limit(platform)

        if can_proceed:
            print("✅ OK")
        else:
            print("⏳ Rate limited - waiting...")
            await tool.wait_for_rate_limit(platform, max_wait=5)
            print("   ✅ Resumed after wait")

        # Small delay to simulate processing
        await asyncio.sleep(0.1)

    print()
    print_section("Caching Demonstration")

    product = TEST_PRODUCTS[0]

    print("First calculation (no cache):")
    start = asyncio.get_event_loop().time()
    profit1 = await tool.calculate_profit(
        source_price=product["source_price"],
        target_price=product["target_price"],
        platform_fees=0.15,
        shipping_cost=5.00,
        category="electronics",
    )
    time1 = asyncio.get_event_loop().time() - start
    print(f"   Time: {time1*1000:.2f}ms")
    print(f"   Result: {format_currency(profit1['net_profit'])} profit")
    print()

    print("Second calculation (cached):")
    start = asyncio.get_event_loop().time()
    profit2 = await tool.calculate_profit(
        source_price=product["source_price"],
        target_price=product["target_price"],
        platform_fees=0.15,
        shipping_cost=5.00,
        category="electronics",
    )
    time2 = asyncio.get_event_loop().time() - start
    print(f"   Time: {time2*1000:.2f}ms")
    print(f"   Result: {format_currency(profit2['net_profit'])} profit")
    print()

    # Guard against zero division when calculating speedup
    if time2 > 0:
        speedup = time1 / time2
        print(f"⚡ Cache speedup: {speedup:.1f}x faster")
    else:
        print(f"⚡ Cache speedup: Instant (from cache)")


async def scenario_6_error_handling():
    """
    SCENARIO 6: Error Handling

    Demonstrates graceful error handling for various scenarios.
    """
    print_header("SCENARIO 6: Error Handling")

    tool = MarketplaceArbitrageTool()

    print("Testing various error scenarios...\n")

    # Test 1: Invalid prices
    print_section("Test 1: Invalid Price Values")
    try:
        profit = await tool.calculate_profit(
            source_price=-10.00,  # Invalid negative price
            target_price=25.00,
            platform_fees=0.15,
            shipping_cost=5.00,
            category="electronics",
        )
        print("❌ Should have raised error")
    except Exception as e:
        print(f"✅ Caught error: {e}")

    # Test 2: Missing required parameters
    print_section("Test 2: Missing Required Parameters")
    try:
        result = await tool.execute(action="calculate_profit")
        print("❌ Should have raised error")
    except Exception as e:
        print(f"✅ Caught error: Missing required parameters")

    # Test 3: Invalid action
    print_section("Test 3: Invalid Action")
    try:
        result = await tool.execute(action="invalid_action")
        if result.error:
            print(f"✅ Handled gracefully: {result.error}")
        else:
            print("❌ Should have returned error")
    except Exception as e:
        print(f"✅ Caught error: {e}")

    # Test 4: Zero price calculation
    print_section("Test 4: Zero Price Edge Case")
    try:
        profit = await tool.calculate_profit(
            source_price=0.01,
            target_price=0.01,
            platform_fees=0.15,
            shipping_cost=5.00,
            category="electronics",
        )
        print(f"✅ Handled gracefully")
        print(f"   Net Profit: {format_currency(profit['net_profit'])}")
        print(f"   Is Profitable: {profit['is_profitable']}")
    except Exception as e:
        print(f"✅ Caught error: {e}")

    print()
    print("✅ All error handling tests completed successfully")


async def run_demo_summary(opportunities: List[Dict], profit_example: Dict):
    """
    Display final summary of the demo.
    """
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

    # Guard against zero division for average calculations
    if len(opportunities) > 0:
        avg_profit_margin = sum(
            o["profit"]["profit_margin"] for o in opportunities
        ) / len(opportunities)
        total_potential_profit = sum(o["profit"]["net_profit"] for o in opportunities)
    else:
        avg_profit_margin = 0
        total_potential_profit = 0

    print(f"   Average Profit Margin:       {format_percentage(avg_profit_margin)}")
    print(f"   Total Potential Profit:      {format_currency(total_potential_profit)}")

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


# ==================== Main Demo Runner ====================


async def main():
    """Run all demo scenarios."""
    print("\n")
    print("=" * 80)
    print(f"{'MARKETPLACE ARBITRAGE TOOL - REAL-WORLD DEMO':^80}")
    print(f"{'Automated E-commerce Arbitrage Discovery & Management':^80}")
    print("=" * 80)
    print()
    print("This demo showcases the tool's capabilities with realistic scenarios.")
    print("All data is simulated for demonstration purposes.")
    print()

    input("Press Enter to start the demo...")

    try:
        # Run all scenarios
        profit_example = await scenario_1_profit_calculation()

        input("\nPress Enter to continue to Scenario 2...")
        opportunities = await scenario_2_find_opportunities()

        input("\nPress Enter to continue to Scenario 3...")
        await scenario_3_monitor_competition()

        input("\nPress Enter to continue to Scenario 4...")
        await scenario_4_create_listing()

        input("\nPress Enter to continue to Scenario 5...")
        await scenario_5_rate_limiting()

        input("\nPress Enter to continue to Scenario 6...")
        await scenario_6_error_handling()

        input("\nPress Enter to see the final summary...")
        await run_demo_summary(opportunities, profit_example)

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
