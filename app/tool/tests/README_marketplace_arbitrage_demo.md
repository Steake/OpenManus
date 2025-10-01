# MarketplaceArbitrageTool Demo Guide

## Overview

This directory contains comprehensive real-world demonstrations of the MarketplaceArbitrageTool capabilities. The demos showcase realistic arbitrage scenarios using simulated data.

## Demo Files

### 1. `demo_marketplace_arbitrage.py` (Interactive)
**Interactive demo with step-by-step progression**

Run with:
```bash
python app/tool/tests/demo_marketplace_arbitrage.py
```

Features:
- User prompts between scenarios
- Detailed explanations at each step
- Educational walkthrough format
- Best for learning and presentations

### 2. `demo_marketplace_arbitrage_auto.py` (Automated)
**Automated demo that runs all scenarios without interaction**

Run with:
```bash
python app/tool/tests/demo_marketplace_arbitrage_auto.py
```

Features:
- No user interaction required
- Runs all scenarios sequentially
- Suitable for CI/CD testing
- Best for quick verification

## Demo Scenarios

### Scenario 1: Profit Calculation
**Demonstrates detailed profit analysis with fee breakdown**

Shows:
- ✅ Source and target platform pricing
- ✅ Gross vs net profit calculation
- ✅ Detailed fee breakdown (platform, payment processing, shipping)
- ✅ Profit margin and ROI calculations
- ✅ Profitability assessment

Example Output:
```
Profit Analysis
────────────────────────────────────────────────────────────────────────────────
Source Cost:              $8.99
Target Price:             $24.99
Gross Profit:             $16.00

Fees Breakdown:
  Platform Fee (15.0%):   $3.75
  Payment Processing:     $1.02
  Shipping Cost:          $5.00
  Total Fees:             $9.77

Net Profit:               $6.23
Profit Margin:            24.9%
ROI:                      42.7%

✅ PROFITABLE - This is a good arbitrage opportunity!
```

### Scenario 2: Finding Opportunities
**Demonstrates opportunity discovery and filtering**

Shows:
- ✅ Multi-product analysis
- ✅ Filtering by minimum profit margin (25%)
- ✅ Top opportunities ranked by margin
- ✅ Summary statistics
- ✅ Revenue projections

Analyzes 5 test products across platforms:
- Wireless Bluetooth Earbuds (AliExpress → Amazon)
- LED Strip Lights (AliExpress → eBay)
- Smart Watch Fitness Tracker (Amazon → Walmart)
- Yoga Mat (AliExpress → Amazon)
- Portable Phone Charger (Amazon → eBay)

### Scenario 3: Competition Monitoring
**Demonstrates price tracking and competitive analysis**

Shows:
- ✅ 7-day price history tracking
- ✅ Competitor count monitoring
- ✅ Price volatility analysis
- ✅ Pricing recommendations
- ✅ Profit recalculation at recommended price

### Scenario 4: Listing Creation
**Demonstrates AI-optimized listing generation**

Shows:
- ✅ SEO-optimized product titles
- ✅ Compelling product descriptions
- ✅ Feature bullet points
- ✅ Keyword optimization
- ✅ Pricing strategy with launch discounts

### Scenario 5: Rate Limiting & Caching
**Demonstrates performance optimizations**

Shows:
- ✅ Rate limiting across multiple platforms
- ✅ Request throttling
- ✅ Cache performance improvements
- ✅ Speed comparisons (cached vs uncached)

### Scenario 6: Error Handling
**Demonstrates robust error handling**

Tests:
- ✅ Invalid price values (negative, zero)
- ✅ Missing required parameters
- ✅ Invalid actions
- ✅ Edge cases
- ✅ Graceful error recovery

## Test Data

The demos use realistic but simulated product data:

| Product | Source | Source Price | Target | Target Price | Margin |
|---------|--------|--------------|--------|--------------|--------|
| Bluetooth Earbuds | AliExpress | $8.99 | Amazon | $24.99 | ~25% |
| LED Strip Lights | AliExpress | $12.50 | eBay | $29.99 | ~30% |
| Smart Watch | Amazon | $35.00 | Walmart | $59.99 | ~20% |
| Yoga Mat | AliExpress | $6.50 | Amazon | $22.99 | ~32% |
| Phone Charger | Amazon | $18.00 | eBay | $35.99 | ~28% |

## Key Metrics Demonstrated

### Profitability Analysis
- **Gross Profit**: Revenue minus cost of goods
- **Net Profit**: After all fees and costs
- **Profit Margin**: Net profit as % of revenue
- **ROI**: Return on investment percentage

### Fee Structure
- **Platform Fees**: 5-15% depending on platform
  - Amazon: 15%
  - eBay: 10%
  - Walmart: 12%
  - AliExpress: 5%
- **Payment Processing**: ~2.9% + $0.30
- **Shipping**: $5-10 depending on weight

### Performance Metrics
- **Request Rate Limiting**: Prevents API throttling
- **Cache Performance**: 10-100x speedup on repeated queries
- **Batch Processing**: Multiple products analyzed efficiently

## Sample Output Summary

```
DEMO SUMMARY
================================================================================

📊 Scenarios Executed:
   ✅ Scenario 1: Profit Calculation
   ✅ Scenario 2: Finding Opportunities
   ✅ Scenario 3: Competition Monitoring
   ✅ Scenario 4: Listing Creation
   ✅ Scenario 5: Rate Limiting & Caching
   ✅ Scenario 6: Error Handling

📈 Key Metrics:
   Products Analyzed:           5
   Profitable Opportunities:    4
   Average Profit Margin:       28.5%
   Total Potential Profit:      $45.20
   Est. Monthly Revenue:        $180.80 (@ 1 sale/product/week)

💡 Key Insights:
   • Higher profit margins on electronics (avg 35%)
   • AliExpress → Amazon arbitrage shows best ROI
   • Products with 4.5+ ratings sell faster
   • Monitor competition weekly for price adjustments

🚀 Next Steps:
   1. Set up accounts on source and target platforms
   2. Start with 2-3 high-margin products
   3. Monitor competition and adjust pricing
   4. Scale up profitable products
   5. Automate inventory sync and repricing
```

## Requirements

- Python 3.8+
- Dependencies from `requirements.txt`
- No real API credentials needed (uses mocked data)
- No database setup required for demo

## Integration with Unit Tests

The demos complement the comprehensive unit test suite in `test_marketplace_arbitrage.py`:
- **22 unit tests** covering all functionality
- **Mocked external dependencies** for isolated testing
- **Edge cases and error scenarios** thoroughly tested

## Educational Value

These demos are designed to:
1. **Showcase capabilities** to potential users
2. **Provide learning examples** for developers
3. **Demonstrate best practices** in arbitrage automation
4. **Validate tool functionality** in realistic scenarios

## Customization

To customize the demos:

1. **Modify test data** in `TEST_PRODUCTS` list
2. **Adjust profit margins** in scenario parameters
3. **Change platform fees** in tool configuration
4. **Add new scenarios** following the existing pattern

## Troubleshooting

### Import Errors
```bash
# Ensure you're in the project root
cd /Users/oli/code/OpenManus
python app/tool/tests/demo_marketplace_arbitrage_auto.py
```

### Path Issues
The demos automatically add the project root to `sys.path`:
```python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
```

## Related Files

- `app/tool/monetization/marketplace_arbitrage.py` - Main implementation
- `app/tool/tests/test_marketplace_arbitrage.py` - Unit tests (22 tests)
- `app/tool/monetization/base.py` - Base monetization class
- `docs/monetization_implementation_spec.md` - Detailed specification

## License

Part of the OpenManus project. See LICENSE file for details.
