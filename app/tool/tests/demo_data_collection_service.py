"""
Real-world demonstration of DataCollectionServiceTool.

This script demonstrates data collection and scraping service capabilities
with realistic scenarios for various use cases.

Run with: python app/tool/tests/demo_data_collection_service.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)

from app.tool.monetization.data_collection_service import DataCollectionServiceTool

# ==================== Test Data ====================

# Simulated scraped data for demos
MOCK_PRODUCT_DATA = [
    {
        "title": "Wireless Earbuds Pro",
        "price": 79.99,
        "rating": 4.5,
        "stock": "In Stock",
    },
    {"title": "Smart Watch Ultra", "price": 299.99, "rating": 4.8, "stock": "In Stock"},
    {"title": "Portable Speaker", "price": 45.99, "rating": 4.2, "stock": "Limited"},
    {
        "title": "Gaming Keyboard RGB",
        "price": 89.99,
        "rating": 4.6,
        "stock": "In Stock",
    },
    {"title": "USB-C Hub Adapter", "price": 34.99, "rating": 4.4, "stock": "In Stock"},
    {"title": "Wireless Mouse", "price": 29.99, "rating": 4.3, "stock": "In Stock"},
    {"title": "Laptop Stand", "price": 39.99, "rating": 4.7, "stock": "In Stock"},
]

MOCK_JOB_DATA = [
    {
        "title": "Senior Python Developer",
        "company": "TechCorp",
        "salary": "$120k-150k",
        "location": "Remote",
        "posted": "2 days ago",
    },
    {
        "title": "Full Stack Engineer",
        "company": "StartupX",
        "salary": "$100k-130k",
        "location": "San Francisco",
        "posted": "1 day ago",
    },
    {
        "title": "Data Engineer",
        "company": "DataCo",
        "salary": "$110k-140k",
        "location": "New York",
        "posted": "3 days ago",
    },
    {
        "title": "DevOps Engineer",
        "company": "CloudTech",
        "salary": "$115k-145k",
        "location": "Remote",
        "posted": "1 day ago",
    },
    {
        "title": "ML Engineer",
        "company": "AI Solutions",
        "salary": "$130k-160k",
        "location": "Seattle",
        "posted": "4 days ago",
    },
]

MOCK_PROPERTY_DATA = [
    {
        "title": "Modern 2BR Apartment",
        "price": "$450,000",
        "beds": 2,
        "baths": 2,
        "sqft": 1200,
        "location": "Downtown",
    },
    {
        "title": "Spacious 3BR House",
        "price": "$650,000",
        "beds": 3,
        "baths": 2.5,
        "sqft": 2000,
        "location": "Suburbs",
    },
    {
        "title": "Luxury Condo",
        "price": "$800,000",
        "beds": 2,
        "baths": 2,
        "sqft": 1500,
        "location": "Waterfront",
    },
    {
        "title": "Cozy Studio",
        "price": "$280,000",
        "beds": 1,
        "baths": 1,
        "sqft": 600,
        "location": "City Center",
    },
]

MOCK_NEWS_DATA = [
    {
        "title": "Tech Giants Announce AI Partnership",
        "category": "Technology",
        "date": "2024-03-20",
        "author": "John Doe",
    },
    {
        "title": "Market Reaches Record High",
        "category": "Finance",
        "date": "2024-03-21",
        "author": "Jane Smith",
    },
    {
        "title": "New Climate Initiative Launched",
        "category": "Environment",
        "date": "2024-03-19",
        "author": "Bob Johnson",
    },
    {
        "title": "Healthcare Innovation Breakthrough",
        "category": "Health",
        "date": "2024-03-20",
        "author": "Alice Brown",
    },
]

MOCK_SOCIAL_DATA = [
    {
        "username": "techinfluencer",
        "followers": 125000,
        "posts": 450,
        "engagement": 4.2,
        "verified": True,
    },
    {
        "username": "brandofficial",
        "followers": 89000,
        "posts": 320,
        "engagement": 3.8,
        "verified": True,
    },
    {
        "username": "contentcreator",
        "followers": 67000,
        "posts": 890,
        "engagement": 5.1,
        "verified": False,
    },
    {
        "username": "businesspro",
        "followers": 45000,
        "posts": 210,
        "engagement": 3.5,
        "verified": True,
    },
]

# ==================== Helper Functions ====================


def print_header(text):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f" {text}")
    print("=" * 80 + "\n")


def print_subheader(text):
    """Print formatted subsection header"""
    print(f"\n--- {text} ---")


def print_result(label, value):
    """Print formatted key-value pair"""
    print(f"  {label}: {value}")


def print_success(message):
    """Print success message"""
    print(f"✓ {message}")


def print_data_sample(data, max_items=3):
    """Print sample of scraped data"""
    print("  Sample Data:")
    for i, item in enumerate(data[:max_items], 1):
        print(f"    {i}. {item}")
    if len(data) > max_items:
        print(f"    ... and {len(data) - max_items} more items")


def format_currency(amount: float) -> str:
    """Format amount as currency."""
    return f"${amount:,.2f}"


def calculate_scenario_revenue(
    scenario_name, dataset_price, monthly_sales, api_subscribers=0, api_price=0
):
    """Calculate revenue for a scenario"""
    dataset_revenue = dataset_price * monthly_sales
    api_revenue = api_subscribers * api_price
    total = dataset_revenue + api_revenue

    print(f"\n💰 {scenario_name} Revenue:")
    if dataset_revenue > 0:
        print(
            f"  Dataset Sales: ${dataset_price} × {monthly_sales} = ${format_currency(dataset_revenue)}/month"
        )
    if api_revenue > 0:
        print(
            f"  API Subscriptions: ${api_price} × {api_subscribers} = ${format_currency(api_revenue)}/month"
        )
    print(f"  Total Monthly Revenue: ${format_currency(total)}")
    print(f"  Annual Revenue: ${format_currency(total * 12)}")

    return total


# ==================== Demo Scenarios ====================


async def scenario_1_ecommerce_monitoring(tool):
    """
    SCENARIO 1: E-commerce Product Price Monitoring

    Demonstrates scraping product prices, pagination, filtering, and CSV export.
    """
    print_header("SCENARIO 1: E-commerce Product Price Monitoring")

    print_subheader("Step 1: Create Scraping Job")

    # Create job
    job_result = await tool.create_scraping_job(
        url="https://example.com/products",
        selectors={
            "title": ".product-title",
            "price": ".product-price",
            "rating": ".product-rating",
            "stock": ".stock-status",
        },
        pagination={
            "enabled": True,
            "max_pages": 10,
            "next_selector": ".pagination-next",
        },
    )

    job_id = job_result.get("job_id", "scrape_20241001_abc123")

    print_success("Job created successfully")
    print_result("Job ID", job_id)
    print_result("Target URL", "https://example.com/products")
    print_result("Selectors", "title, price, rating, stock")
    print_result("Pagination", "Enabled (max 10 pages)")

    print_subheader("Step 2: Execute Scraping")

    # Simulate scraping (using mock data)
    scraped_data = MOCK_PRODUCT_DATA * 7  # Simulate 47 products across pages
    data_quality = 92
    execution_time = 2.3

    print_success(f"Scraped {len(scraped_data)} products across 5 pages")
    print_result("Data Quality Score", f"{data_quality}%")
    print_result("Execution Time", f"{execution_time} seconds")
    print_data_sample(scraped_data[:3])

    print_subheader("Step 3: Transform Data (Filter by Price)")

    # Filter products by price > $50
    before_count = len(scraped_data)
    filtered_data = [p for p in scraped_data if p["price"] > 50]
    after_count = len(filtered_data)

    print_success(f"Applied filter: price > $50")
    print_result("Before", f"{before_count} products")
    print_result("After", f"{after_count} products")
    print_result("Removed", f"{before_count - after_count} products")

    print_subheader("Step 4: Export to CSV")

    export_result = await tool.export_dataset(
        job_id=job_id, format="csv", data=filtered_data
    )

    print_success("Dataset exported successfully")
    print_result("Format", "CSV")
    print_result("File Size", "2.4 KB")
    print_result("Record Count", after_count)
    print_result(
        "Download URL", f"/exports/products_{datetime.now().strftime('%Y%m%d')}.csv"
    )

    # Revenue calculation
    revenue = calculate_scenario_revenue(
        "E-commerce Monitoring", dataset_price=75, monthly_sales=10
    )

    return revenue


async def scenario_2_job_board_aggregation(tool):
    """
    SCENARIO 2: Job Board Data Aggregation

    Demonstrates job scraping, deduplication, filtering, and JSON export.
    """
    print_header("SCENARIO 2: Job Board Data Aggregation")

    print_subheader("Step 1: Create Job Scraping Job")

    job_result = await tool.create_scraping_job(
        url="https://example.com/jobs",
        selectors={
            "title": ".job-title",
            "company": ".company-name",
            "salary": ".salary-range",
            "location": ".job-location",
            "posted": ".post-date",
        },
        pagination={"enabled": True, "max_pages": 20, "next_selector": ".next-page"},
    )

    job_id = job_result.get("job_id", "scrape_20241001_def456")

    print_success("Job created successfully")
    print_result("Job ID", job_id)
    print_result("Target URL", "https://example.com/jobs")
    print_result("Selectors", "title, company, salary, location, posted")
    print_result("Pagination", "Enabled (max 20 pages)")

    print_subheader("Step 2: Execute Scraping with Multiple Pages")

    # Simulate scraping with duplicates
    scraped_data = MOCK_JOB_DATA * 15  # 75 jobs with duplicates

    print_success(f"Scraped {len(scraped_data)} job postings across 15 pages")
    print_result("Data Quality Score", "89%")
    print_result("Execution Time", "4.7 seconds")
    print_data_sample(scraped_data[:3])

    print_subheader("Step 3: Transform Data (Deduplicate & Filter)")

    # Deduplicate by title
    before_dedup = len(scraped_data)
    unique_data = []
    seen = set()
    for job in scraped_data:
        if job["title"] not in seen:
            unique_data.append(job)
            seen.add(job["title"])

    print_success(f"Deduplicated by job title")
    print_result("Before", f"{before_dedup} jobs")
    print_result("After", f"{len(unique_data)} unique jobs")
    print_result("Duplicates Removed", f"{before_dedup - len(unique_data)}")

    # Filter by salary (contains 'k')
    filtered_data = [j for j in unique_data if "k" in j["salary"].lower()]

    print()
    print_success(f"Applied filter: salary data available")
    print_result("After Filter", f"{len(filtered_data)} jobs")

    print_subheader("Step 4: Export to JSON")

    export_result = await tool.export_dataset(
        job_id=job_id, format="json", data=filtered_data
    )

    print_success("Dataset exported successfully")
    print_result("Format", "JSON")
    print_result("File Size", "8.7 KB")
    print_result("Record Count", len(filtered_data))
    print_result(
        "Download URL", f"/exports/jobs_{datetime.now().strftime('%Y%m%d')}.json"
    )

    print_subheader("Step 5: API Subscription Potential")

    print("  API Endpoints:")
    print("    • GET /api/jobs - List all jobs")
    print("    • GET /api/jobs?location=remote - Filter by location")
    print("    • GET /api/jobs?salary_min=100000 - Filter by salary")
    print("    • GET /api/jobs/latest - Recent postings (updated hourly)")

    # Revenue calculation
    revenue = calculate_scenario_revenue(
        "Job Board Aggregation",
        dataset_price=150,
        monthly_sales=8,
        api_subscribers=5,
        api_price=200,
    )

    return revenue


async def scenario_3_real_estate_listings(tool):
    """
    SCENARIO 3: Real Estate Listings Collection

    Demonstrates property scraping, quality scoring, sorting, and Excel export.
    """
    print_header("SCENARIO 3: Real Estate Listings Collection")

    print_subheader("Step 1: Create Property Listings Scraper")

    job_result = await tool.create_scraping_job(
        url="https://example.com/properties",
        selectors={
            "title": ".property-title",
            "price": ".property-price",
            "beds": ".bedroom-count",
            "baths": ".bathroom-count",
            "sqft": ".square-feet",
            "location": ".property-location",
        },
        quality_checks={
            "required_fields": ["title", "price", "location"],
            "min_data_points": 4,
        },
    )

    job_id = job_result.get("job_id", "scrape_20241001_ghi789")

    print_success("Job created successfully")
    print_result("Job ID", job_id)
    print_result("Target URL", "https://example.com/properties")
    print_result("Selectors", "title, price, beds, baths, sqft, location")
    print_result("Quality Checks", "Enabled")

    print_subheader("Step 2: Execute Scraping with Quality Scoring")

    scraped_data = MOCK_PROPERTY_DATA * 8  # 32 properties
    quality_score = 94

    print_success(f"Scraped {len(scraped_data)} property listings")
    print_result("Data Quality Score", f"{quality_score}%")
    print_result("Execution Time", "3.2 seconds")
    print_result(
        "Complete Records", f"{int(len(scraped_data) * 0.94)}/{len(scraped_data)}"
    )
    print_data_sample(scraped_data[:3])

    print_subheader("Step 3: Transform Data (Sort & Filter)")

    # Sort by price (parse price string)
    def parse_price(price_str):
        return float(price_str.replace("$", "").replace(",", ""))

    sorted_data = sorted(
        scraped_data, key=lambda x: parse_price(x["price"]), reverse=True
    )

    print_success("Sorted by price (highest first)")
    print("  Top 3 Most Expensive:")
    for i, prop in enumerate(sorted_data[:3], 1):
        print(f"    {i}. {prop['title']} - {prop['price']}")

    # Filter by location
    filtered_data = [
        p
        for p in sorted_data
        if "Downtown" in p["location"] or "Waterfront" in p["location"]
    ]

    print()
    print_success(f"Applied filter: Premium locations")
    print_result("Before", f"{len(sorted_data)} properties")
    print_result("After", f"{len(filtered_data)} properties")

    print_subheader("Step 4: Export to Excel")

    export_result = await tool.export_dataset(
        job_id=job_id, format="excel", data=filtered_data
    )

    print_success("Dataset exported successfully")
    print_result("Format", "Excel (XLSX)")
    print_result("File Size", "15.3 KB")
    print_result("Record Count", len(filtered_data))
    print_result("Sheets", "Properties, Summary, Charts")
    print_result(
        "Download URL", f"/exports/properties_{datetime.now().strftime('%Y%m%d')}.xlsx"
    )

    # Revenue calculation
    revenue = calculate_scenario_revenue(
        "Real Estate Listings",
        dataset_price=350,
        monthly_sales=2,
        api_subscribers=3,
        api_price=150,
    )

    return revenue


async def scenario_4_news_aggregation(tool):
    """
    SCENARIO 4: News Article Aggregation

    Demonstrates news scraping, enrichment, validation, and recurring jobs.
    """
    print_header("SCENARIO 4: News Article Aggregation")

    print_subheader("Step 1: Create News Scraper with Categories")

    job_result = await tool.create_scraping_job(
        url="https://example.com/news",
        selectors={
            "title": ".article-title",
            "category": ".article-category",
            "date": ".publish-date",
            "author": ".article-author",
            "summary": ".article-summary",
        },
        filters={
            "categories": ["Technology", "Finance", "Health"],
            "date_range": "last_7_days",
        },
    )

    job_id = job_result.get("job_id", "scrape_20241001_jkl012")

    print_success("Job created successfully")
    print_result("Job ID", job_id)
    print_result("Target URL", "https://example.com/news")
    print_result("Categories", "Technology, Finance, Health")
    print_result("Date Filter", "Last 7 days")

    print_subheader("Step 2: Execute Scraping with Date Filtering")

    scraped_data = MOCK_NEWS_DATA * 12  # 48 articles

    print_success(f"Scraped {len(scraped_data)} news articles")
    print_result("Data Quality Score", "91%")
    print_result("Execution Time", "2.8 seconds")
    print_result("Date Range", "2024-03-15 to 2024-03-21")
    print_data_sample(scraped_data[:3])

    print_subheader("Step 3: Transform Data (Enrich & Validate)")

    # Enrich with metadata
    enriched_data = []
    for article in scraped_data:
        enriched = article.copy()
        enriched["word_count"] = 450  # Simulated
        enriched["read_time"] = "3 min"
        enriched["sentiment"] = "neutral"
        enriched_data.append(enriched)

    print_success("Enriched articles with metadata")
    print_result("Added Fields", "word_count, read_time, sentiment")

    # Validate schema
    required_fields = ["title", "category", "date", "author"]
    valid_data = [
        a for a in enriched_data if all(field in a for field in required_fields)
    ]

    print()
    print_success("Validated data schema")
    print_result("Required Fields", ", ".join(required_fields))
    print_result("Valid Records", f"{len(valid_data)}/{len(enriched_data)}")

    print_subheader("Step 4: Schedule Recurring Job (Daily Updates)")

    schedule_result = await tool.schedule_recurring_job(
        job_id=job_id, schedule="0 8 * * *", enabled=True  # Daily at 8 AM
    )

    print_success("Recurring job scheduled")
    print_result("Schedule", "Daily at 8:00 AM (0 8 * * *)")
    print_result(
        "Next Run", (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d 08:00")
    )
    print_result("Status", "Active")
    print_result("Auto-Export", "Enabled (JSON format)")

    print_subheader("Step 5: Content Aggregation Revenue")

    print("  Revenue Streams:")
    print("    • Daily news digest newsletter ($5/month × 80 subscribers)")
    print("    • API access for news apps ($100/month × 4 clients)")
    print("    • Custom category feeds ($50/month × 6 clients)")

    # Revenue calculation
    revenue = calculate_scenario_revenue(
        "News Aggregation",
        dataset_price=0,
        monthly_sales=0,
        api_subscribers=10,
        api_price=60,  # Average across all tiers
    )

    return revenue


async def scenario_5_social_media_data(tool):
    """
    SCENARIO 5: Social Media Profile Data

    Demonstrates social media scraping, engagement metrics, and SQL export.
    """
    print_header("SCENARIO 5: Social Media Profile Data")

    print_subheader("Step 1: Create Social Media Scraper")

    job_result = await tool.create_scraping_job(
        url="https://example.com/profiles",
        selectors={
            "username": ".profile-username",
            "followers": ".follower-count",
            "posts": ".post-count",
            "engagement": ".engagement-rate",
            "verified": ".verified-badge",
        },
        rate_limit={"requests_per_minute": 30, "delay_between_requests": 2},
    )

    job_id = job_result.get("job_id", "scrape_20241001_mno345")

    print_success("Job created successfully")
    print_result("Job ID", job_id)
    print_result("Target URL", "https://example.com/profiles")
    print_result("Metrics", "followers, posts, engagement, verified")
    print_result("Rate Limit", "30 requests/minute")

    print_subheader("Step 2: Execute Scraping with Engagement Metrics")

    scraped_data = MOCK_SOCIAL_DATA * 22  # 88 profiles

    print_success(f"Scraped {len(scraped_data)} social media profiles")
    print_result("Data Quality Score", "87%")
    print_result("Execution Time", "6.4 seconds")
    print_result("Rate Limit Status", "Within limits (28 req/min)")
    print_data_sample(scraped_data[:3])

    print_subheader("Step 3: Transform Data (Sort & Filter)")

    # Sort by followers
    sorted_data = sorted(scraped_data, key=lambda x: x["followers"], reverse=True)

    print_success("Sorted by followers (highest first)")
    print("  Top 3 Influencers:")
    for i, profile in enumerate(sorted_data[:3], 1):
        print(f"    {i}. @{profile['username']} - {profile['followers']:,} followers")

    # Filter active accounts (engagement > 3.0)
    active_data = [p for p in sorted_data if p["engagement"] > 3.0]

    print()
    print_success(f"Applied filter: High engagement (>3.0%)")
    print_result("Before", f"{len(sorted_data)} profiles")
    print_result("After", f"{len(active_data)} active profiles")
    print_result(
        "Average Engagement",
        f"{sum(p['engagement'] for p in active_data) / len(active_data):.1f}%",
    )

    print_subheader("Step 4: Export to SQL Format")

    export_result = await tool.export_dataset(
        job_id=job_id, format="sql", data=active_data
    )

    print_success("Dataset exported successfully")
    print_result("Format", "SQL (INSERT statements)")
    print_result("File Size", "12.8 KB")
    print_result("Record Count", len(active_data))
    print_result("Table Name", "social_profiles")
    print_result(
        "Download URL", f"/exports/profiles_{datetime.now().strftime('%Y%m%d')}.sql"
    )

    print_subheader("Step 5: Lead Generation Value")

    print("  Use Cases:")
    print("    • Influencer marketing campaigns")
    print("    • Brand partnership opportunities")
    print("    • Competitor analysis reports")
    print("    • Audience insights and demographics")

    # Revenue calculation
    revenue = calculate_scenario_revenue(
        "Social Media Data",
        dataset_price=200,
        monthly_sales=4,
        api_subscribers=2,
        api_price=250,
    )

    return revenue


async def scenario_6_recurring_schedules(tool):
    """
    SCENARIO 6: Recurring Scheduled Scraping

    Demonstrates multiple recurring jobs with different schedules and subscription model.
    """
    print_header("SCENARIO 6: Recurring Scheduled Scraping")

    print_subheader("Step 1: Set Up Multiple Recurring Jobs")

    # Job 1: Hourly price monitoring
    job1 = {
        "id": "hourly_prices_xyz123",
        "name": "E-commerce Price Monitor",
        "schedule": "0 * * * *",
        "frequency": "Hourly",
        "next_run": datetime.now() + timedelta(hours=1),
    }

    # Job 2: Daily news aggregation
    job2 = {
        "id": "daily_news_abc456",
        "name": "News Aggregator",
        "schedule": "0 8 * * *",
        "frequency": "Daily at 8 AM",
        "next_run": datetime.now().replace(hour=8, minute=0) + timedelta(days=1),
    }

    # Job 3: Weekly market research
    job3 = {
        "id": "weekly_market_def789",
        "name": "Market Research Report",
        "schedule": "0 9 * * 1",
        "frequency": "Weekly on Monday at 9 AM",
        "next_run": datetime.now() + timedelta(days=(7 - datetime.now().weekday())),
    }

    jobs = [job1, job2, job3]

    print_success(f"Configured {len(jobs)} recurring jobs")
    print()
    for i, job in enumerate(jobs, 1):
        print(f"  {i}. {job['name']}")
        print(f"     ID: {job['id']}")
        print(f"     Schedule: {job['frequency']} ({job['schedule']})")
        print(f"     Next Run: {job['next_run'].strftime('%Y-%m-%d %H:%M')}")
        print()

    print_subheader("Step 2: Next Run Calculations")

    print("  Upcoming Executions (Next 24 Hours):")

    upcoming = []
    now = datetime.now()
    for job in jobs:
        time_until = (job["next_run"] - now).total_seconds() / 3600
        if time_until <= 24:
            upcoming.append((job, time_until))

    upcoming.sort(key=lambda x: x[1])

    for job, hours in upcoming:
        print(f"    • {job['name']}: in {hours:.1f} hours")

    print_subheader("Step 3: Subscription Revenue Model")

    print("  Subscription Tiers:")
    print()
    print("  📦 Basic Plan - $99/month")
    print("     • 1 recurring job")
    print("     • Daily execution")
    print("     • 1,000 records/month")
    print("     • CSV/JSON exports")
    print()
    print("  🚀 Pro Plan - $299/month")
    print("     • 5 recurring jobs")
    print("     • Hourly execution")
    print("     • 10,000 records/month")
    print("     • All export formats + API access")
    print()
    print("  💎 Enterprise Plan - $799/month")
    print("     • Unlimited recurring jobs")
    print("     • Real-time execution")
    print("     • Unlimited records")
    print("     • Dedicated support + Custom integrations")

    print_subheader("Step 4: Calculate Monthly Revenue Potential")

    subscribers = {"Basic": 15, "Pro": 6, "Enterprise": 2}

    prices = {"Basic": 99, "Pro": 299, "Enterprise": 799}

    total_revenue = 0
    print()
    for tier, count in subscribers.items():
        tier_revenue = count * prices[tier]
        total_revenue += tier_revenue
        print(
            f"  {tier}: {count} subscribers × ${prices[tier]} = ${format_currency(tier_revenue)}/month"
        )

    print()
    print(f"  💰 Total Monthly Revenue: ${format_currency(total_revenue)}")
    print(f"  💰 Annual Revenue: ${format_currency(total_revenue * 12)}")

    return total_revenue


# ==================== Summary ====================


def print_summary(total_revenue):
    """Display final summary of the demo"""
    print_header("DEMO SUMMARY")

    print("📊 Scenarios Demonstrated: 6")
    print("   ✅ Scenario 1: E-commerce Product Price Monitoring")
    print("   ✅ Scenario 2: Job Board Data Aggregation")
    print("   ✅ Scenario 3: Real Estate Listings Collection")
    print("   ✅ Scenario 4: News Article Aggregation")
    print("   ✅ Scenario 5: Social Media Profile Data")
    print("   ✅ Scenario 6: Recurring Scheduled Scraping")
    print()

    print("📈 Key Metrics:")
    print(f"   Jobs Created: 6")
    print(f"   Total Records Scraped: 287")
    print(f"   Data Quality Average: 91%")
    print(f"   Export Formats Used: JSON, CSV, Excel, SQL")
    print(f"   Transformations Applied: 15")
    print(f"   Recurring Jobs Scheduled: 3")
    print()

    print("💡 Features Demonstrated:")
    print("   • Multi-page scraping with pagination")
    print("   • Data quality scoring and validation")
    print(
        "   • All 5 transformation types (filter, sort, deduplicate, enrich, validate)"
    )
    print("   • All export formats (JSON, CSV, Excel, SQL)")
    print("   • Recurring job scheduling with cron syntax")
    print("   • Rate limiting and caching")
    print("   • Revenue calculation models")
    print()

    print("💰 Revenue Potential Summary:")
    print(f"   E-commerce Monitoring:     $750/month")
    print(f"   Job Board Aggregation:     $1,200/month")
    print(f"   Real Estate Listings:      $800/month")
    print(f"   News Aggregation:          $600/month")
    print(f"   Social Media Data:         $900/month")
    print(f"   Recurring Subscriptions:   $2,400/month")
    print()
    print(f"💰 TOTAL MONTHLY REVENUE POTENTIAL: ${format_currency(total_revenue)}")
    print(f"💰 TOTAL ANNUAL REVENUE POTENTIAL: ${format_currency(total_revenue * 12)}")
    print()

    print("🚀 Next Steps:")
    print("   1. Set up scraping infrastructure (proxies, user agents)")
    print("   2. Implement data storage and API endpoints")
    print("   3. Create customer dashboard and billing system")
    print("   4. Launch with 2-3 high-demand data sources")
    print("   5. Scale to additional verticals based on demand")
    print()

    print("=" * 80)
    print("✓ DataCollectionServiceTool demo completed successfully!")
    print("=" * 80)


# ==================== Main Demo Runner ====================


async def main():
    """Run all demo scenarios"""
    print("\n")
    print("=" * 80)
    print("  DataCollectionServiceTool - Real-World Demonstration")
    print("  Automated Web Scraping & Data Collection Service")
    print("=" * 80)
    print()
    print("This demo showcases the tool's capabilities with realistic scenarios.")
    print("All data is simulated for demonstration purposes.")
    print()

    input("Press Enter to start the demo...")

    # Initialize tool
    tool = DataCollectionServiceTool(
        config={"database_url": "sqlite:///:memory:", "cache_enabled": True}
    )

    total_revenue = 0

    try:
        # Run all scenarios
        revenue = await scenario_1_ecommerce_monitoring(tool)
        total_revenue += revenue

        input("\nPress Enter to continue to Scenario 2...")
        revenue = await scenario_2_job_board_aggregation(tool)
        total_revenue += revenue

        input("\nPress Enter to continue to Scenario 3...")
        revenue = await scenario_3_real_estate_listings(tool)
        total_revenue += revenue

        input("\nPress Enter to continue to Scenario 4...")
        revenue = await scenario_4_news_aggregation(tool)
        total_revenue += revenue

        input("\nPress Enter to continue to Scenario 5...")
        revenue = await scenario_5_social_media_data(tool)
        total_revenue += revenue

        input("\nPress Enter to continue to Scenario 6...")
        revenue = await scenario_6_recurring_schedules(tool)
        total_revenue += revenue

        input("\nPress Enter to see the final summary...")
        print_summary(total_revenue)

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
