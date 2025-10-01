"""
Comprehensive unit tests for DataCollectionServiceTool.

Tests cover:
- Job creation and validation
- Scraping execution with mock data
- Data transformations (filter, sort, deduplicate, enrich, validate)
- Multi-format exports (JSON, CSV, Excel, SQL, XML)
- Recurring job scheduling
- Error handling and edge cases
- Rate limiting and caching
"""

import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)

import json
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text

from app.tool.base import ToolResult
from app.tool.monetization.base import MonetizationError, ValidationError
from app.tool.monetization.data_collection_service import DataCollectionServiceTool
from app.tool.sql_manager import create_connection, get_connection

# ==================== Test Data Factory ====================


def create_test_job_config(**overrides) -> Dict[str, Any]:
    """Create test job configuration with optional overrides."""
    config = {
        "name": "Test Product Scraper",
        "url": "https://example.com/products",
        "selectors": {
            "title": ".product-title",
            "price": ".product-price",
            "rating": ".product-rating",
        },
        "pagination": {
            "enabled": True,
            "next_selector": ".next-page",
            "max_pages": 5,
        },
        "output_format": "json",
    }
    config.update(overrides)
    return config


def create_test_scraped_data() -> List[Dict[str, Any]]:
    """Create mock scraped data for testing."""
    return [
        {
            "title": "Product A",
            "price": 29.99,
            "rating": 4.5,
            "quality_score": 0.95,
        },
        {
            "title": "Product B",
            "price": 59.99,
            "rating": 4.8,
            "quality_score": 0.90,
        },
        {
            "title": "Product C",
            "price": 15.99,
            "rating": 4.2,
            "quality_score": 0.85,
        },
    ]


# ==================== Fixtures ====================


@pytest.fixture
def tool():
    """Create DataCollectionServiceTool instance for testing."""
    tool = DataCollectionServiceTool()
    tool.connection_id = "test_db"
    return tool


@pytest.fixture
def tool_with_db():
    """Create tool with in-memory SQLite database."""
    conn_id = create_connection("sqlite", "", 0, ":memory:", "", "")
    engine = get_connection(conn_id)

    # Create required tables
    with engine.connect() as c:
        # Data collection jobs table
        c.execute(
            text(
                """
            CREATE TABLE data_collection_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT NOT NULL,
                job_name TEXT NOT NULL,
                job_type TEXT NOT NULL,
                target_sources TEXT,
                data_schema TEXT,
                collection_frequency TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                next_run TIMESTAMP
            )
        """
            )
        )

        # Collected data table
        c.execute(
            text(
                """
            CREATE TABLE collected_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                raw_data TEXT,
                cleaned_data TEXT,
                quality_score REAL,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_url TEXT,
                exported BOOLEAN DEFAULT FALSE,
                export_format TEXT,
                exported_at TIMESTAMP
            )
        """
            )
        )
        c.commit()

    tool = DataCollectionServiceTool()
    tool.connection_id = conn_id
    return tool


@pytest.fixture
def sample_job_config():
    """Sample job configuration for testing."""
    return create_test_job_config()


@pytest.fixture
def mock_db_execute(tool):
    """Mock database execute method."""
    with patch.object(tool, "db_execute", new_callable=AsyncMock) as mock:
        mock.return_value = {"success": True, "job_id": "test-job-123"}
        yield mock


@pytest.fixture
def mock_cache(tool):
    """Mock cache methods."""
    with patch.object(tool, "cache_set", new_callable=AsyncMock) as cache_set_mock:
        with patch.object(tool, "cache_get", new_callable=AsyncMock) as cache_get_mock:
            yield {"set": cache_set_mock, "get": cache_get_mock}


@pytest.fixture
def mock_rate_limit(tool):
    """Mock rate limiting."""
    with patch.object(tool, "wait_for_rate_limit", new_callable=AsyncMock) as mock_wait:
        with patch.object(tool, "record_request") as mock_record:
            mock_wait.return_value = True
            yield {"wait": mock_wait, "record": mock_record}


# ==================== Test create_scraping_job ====================


@pytest.mark.asyncio
async def test_create_scraping_job_success(tool, sample_job_config, mock_db_execute):
    """Test successful job creation with valid configuration."""
    result = await tool.create_scraping_job(sample_job_config)

    assert isinstance(result, ToolResult)
    assert result.error is None

    output = json.loads(result.output)
    assert "job_id" in output
    assert output["name"] == "Test Product Scraper"
    assert output["url"] == "https://example.com/products"
    assert output["status"] == "created"
    assert output["selectors"]["title"] == ".product-title"
    assert "created_at" in output


@pytest.mark.asyncio
async def test_create_scraping_job_invalid_url(tool):
    """Test job creation with invalid URL."""
    config = create_test_job_config(url="not-a-valid-url")

    with pytest.raises(ValidationError, match="Invalid URL"):
        await tool.create_scraping_job(config)


@pytest.mark.asyncio
async def test_create_scraping_job_invalid_selectors(tool):
    """Test job creation with invalid CSS selectors."""
    config = create_test_job_config(selectors={"title": ""})

    with pytest.raises(ValidationError, match="Invalid CSS selector"):
        await tool.create_scraping_job(config)


@pytest.mark.asyncio
async def test_create_scraping_job_invalid_format(tool):
    """Test job creation with unsupported export format."""
    config = create_test_job_config(output_format="invalid_format")

    with pytest.raises(ValidationError, match="Unsupported format"):
        await tool.create_scraping_job(config)


@pytest.mark.asyncio
async def test_create_scraping_job_missing_required_fields(tool):
    """Test job creation with missing required fields."""
    # Missing name
    with pytest.raises(ValidationError, match="Missing required parameters"):
        await tool.create_scraping_job({"url": "https://example.com"})

    # Missing url
    with pytest.raises(ValidationError, match="Missing required parameters"):
        await tool.create_scraping_job({"name": "Test"})

    # Missing selectors
    with pytest.raises(ValidationError, match="Missing required parameters"):
        await tool.create_scraping_job({"name": "Test", "url": "https://example.com"})


# ==================== Test execute_scrape ====================


@pytest.mark.asyncio
async def test_execute_scrape_success(tool_with_db, sample_job_config):
    """Test successful scraping execution."""
    # First create a job
    job_result = await tool_with_db.create_scraping_job(sample_job_config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]

    # Execute scraping
    result = await tool_with_db.execute_scrape(job_id)

    assert isinstance(result, ToolResult)
    assert result.error is None

    output = json.loads(result.output)
    assert output["job_id"] == job_id
    assert output["status"] == "completed"
    assert output["records_scraped"] > 0
    assert "avg_quality_score" in output
    assert "sample_data" in output
    assert "execution_time" in output


@pytest.mark.asyncio
async def test_execute_scrape_with_pagination(tool_with_db):
    """Test scraping with pagination handling."""
    config = create_test_job_config(
        pagination={"enabled": True, "next_selector": ".next", "max_pages": 3}
    )

    job_result = await tool_with_db.create_scraping_job(config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]

    result = await tool_with_db.execute_scrape(job_id)

    output = json.loads(result.output)
    assert output["pages_scraped"] == 3
    # Should have scraped more records due to pagination
    assert output["records_scraped"] > 0


@pytest.mark.asyncio
async def test_execute_scrape_job_not_found(tool):
    """Test scraping with non-existent job ID."""
    with pytest.raises(ValidationError, match="Job not found"):
        await tool.execute_scrape("nonexistent-job-id")


@pytest.mark.asyncio
async def test_execute_scrape_rate_limiting(tool_with_db, sample_job_config):
    """Test rate limit enforcement during scraping."""
    job_result = await tool_with_db.create_scraping_job(sample_job_config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]

    with patch.object(
        tool_with_db, "wait_for_rate_limit", new_callable=AsyncMock
    ) as mock_wait:
        mock_wait.return_value = True

        result = await tool_with_db.execute_scrape(job_id)

        # Verify rate limiting was called
        assert mock_wait.called
        assert result.error is None


@pytest.mark.asyncio
async def test_execute_scrape_quality_scoring(tool_with_db, sample_job_config):
    """Test data quality score calculation."""
    job_result = await tool_with_db.create_scraping_job(sample_job_config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]

    result = await tool_with_db.execute_scrape(job_id)

    output = json.loads(result.output)
    assert "avg_quality_score" in output
    assert 0 <= output["avg_quality_score"] <= 1.0
    # Check sample data has quality scores
    if output["sample_data"]:
        assert "quality_score" in output["sample_data"][0]


# ==================== Test transform_data ====================


@pytest.mark.asyncio
async def test_transform_data_filter(tool_with_db, sample_job_config):
    """Test filter transformation on scraped data."""
    # Create and execute job
    job_result = await tool_with_db.create_scraping_job(sample_job_config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]
    await tool_with_db.execute_scrape(job_id)

    # Apply filter transformation
    transformations = [
        {"type": "filter", "field": "price", "operator": ">", "value": 50.0}
    ]

    result = await tool_with_db.transform_data(job_id, transformations)

    assert isinstance(result, ToolResult)
    assert result.error is None

    output = json.loads(result.output)
    assert output["transformations_applied"] == 1
    assert "before_count" in output
    assert "after_count" in output
    assert output["after_count"] <= output["before_count"]


@pytest.mark.asyncio
async def test_transform_data_sort(tool_with_db, sample_job_config):
    """Test sort transformation on scraped data."""
    job_result = await tool_with_db.create_scraping_job(sample_job_config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]
    await tool_with_db.execute_scrape(job_id)

    # Apply sort transformation
    transformations = [{"type": "sort", "field": "rating", "order": "desc"}]

    result = await tool_with_db.transform_data(job_id, transformations)

    output = json.loads(result.output)
    assert output["transformations_applied"] == 1
    assert output["status"] == "transformed"
    # Verify sample data is sorted
    if len(output["sample_data"]) >= 2:
        sample = output["sample_data"]
        assert sample[0]["rating"] >= sample[1]["rating"]


@pytest.mark.asyncio
async def test_transform_data_deduplicate(tool_with_db, sample_job_config):
    """Test deduplication transformation."""
    job_result = await tool_with_db.create_scraping_job(sample_job_config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]
    await tool_with_db.execute_scrape(job_id)

    # Apply deduplicate transformation
    transformations = [{"type": "deduplicate", "fields": ["title"]}]

    result = await tool_with_db.transform_data(job_id, transformations)

    output = json.loads(result.output)
    assert output["transformations_applied"] == 1
    assert output["final_records"] <= output["original_records"]


@pytest.mark.asyncio
async def test_transform_data_enrich(tool_with_db, sample_job_config):
    """Test data enrichment transformation."""
    job_result = await tool_with_db.create_scraping_job(sample_job_config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]
    await tool_with_db.execute_scrape(job_id)

    # Apply enrich transformation
    transformations = [
        {"type": "enrich", "field": "price", "function": "convert_currency"}
    ]

    result = await tool_with_db.transform_data(job_id, transformations)

    output = json.loads(result.output)
    assert output["transformations_applied"] == 1
    # Check if enrichment added fields
    if output["sample_data"]:
        sample = output["sample_data"][0]
        # Should have added currency conversion fields
        assert "price_usd" in sample or "price_eur" in sample


@pytest.mark.asyncio
async def test_transform_data_validate(tool_with_db, sample_job_config):
    """Test schema validation transformation."""
    job_result = await tool_with_db.create_scraping_job(sample_job_config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]
    await tool_with_db.execute_scrape(job_id)

    # Apply validate transformation
    transformations = [
        {"type": "validate", "schema": {"title": "required", "price": "number"}}
    ]

    result = await tool_with_db.transform_data(job_id, transformations)

    output = json.loads(result.output)
    assert output["transformations_applied"] == 1
    # Valid records should remain
    assert output["final_records"] >= 0


# ==================== Test export_dataset ====================


@pytest.mark.asyncio
async def test_export_dataset_json(tool_with_db, sample_job_config):
    """Test JSON export with default options."""
    job_result = await tool_with_db.create_scraping_job(sample_job_config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]
    await tool_with_db.execute_scrape(job_id)

    result = await tool_with_db.export_dataset(
        job_id, "json", {"include_metadata": True}
    )

    assert isinstance(result, ToolResult)
    assert result.error is None

    output = json.loads(result.output)
    assert output["format"] == "json"
    assert "download_url" in output
    assert "records_exported" in output
    assert "file_size" in output
    assert "filename" in output


@pytest.mark.asyncio
async def test_export_dataset_csv(tool_with_db, sample_job_config):
    """Test CSV export."""
    job_result = await tool_with_db.create_scraping_job(sample_job_config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]
    await tool_with_db.execute_scrape(job_id)

    result = await tool_with_db.export_dataset(job_id, "csv", {})

    output = json.loads(result.output)
    assert output["format"] == "csv"
    assert output["records_exported"] > 0
    assert output["filename"].endswith(".csv")


@pytest.mark.asyncio
async def test_export_dataset_with_filters(tool_with_db, sample_job_config):
    """Test filtered export."""
    job_result = await tool_with_db.create_scraping_job(sample_job_config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]
    await tool_with_db.execute_scrape(job_id)

    # Export with filters
    options = {"filters": {"price": {"$gt": 30}}, "limit": 10}

    result = await tool_with_db.export_dataset(job_id, "json", options)

    output = json.loads(result.output)
    assert output["records_exported"] <= output["total_records"]
    assert output["records_exported"] <= 10  # Limit applied


@pytest.mark.asyncio
async def test_export_dataset_invalid_format(tool_with_db, sample_job_config):
    """Test export with unsupported format."""
    job_result = await tool_with_db.create_scraping_job(sample_job_config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]
    await tool_with_db.execute_scrape(job_id)

    with pytest.raises(ValidationError, match="Unsupported format"):
        await tool_with_db.export_dataset(job_id, "invalid", {})


# ==================== Test schedule_recurring_job ====================


@pytest.mark.asyncio
async def test_schedule_recurring_job_success(tool_with_db, sample_job_config):
    """Test valid cron schedule creation."""
    job_result = await tool_with_db.create_scraping_job(sample_job_config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]

    result = await tool_with_db.schedule_recurring_job(job_id, "0 */6 * * *")

    assert isinstance(result, ToolResult)
    assert result.error is None

    output = json.loads(result.output)
    assert output["job_id"] == job_id
    assert output["schedule"] == "0 */6 * * *"
    assert output["status"] == "scheduled"
    assert "frequency" in output
    assert "next_run" in output
    assert "description" in output


@pytest.mark.asyncio
async def test_schedule_recurring_job_invalid_cron(tool_with_db, sample_job_config):
    """Test invalid cron syntax."""
    job_result = await tool_with_db.create_scraping_job(sample_job_config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]

    # Invalid cron - wrong number of fields
    with pytest.raises(ValidationError, match="Invalid cron schedule"):
        await tool_with_db.schedule_recurring_job(job_id, "0 */6")

    # Invalid cron - bad values
    with pytest.raises(ValidationError, match="Invalid cron schedule"):
        await tool_with_db.schedule_recurring_job(job_id, "99 99 99 99 99")


@pytest.mark.asyncio
async def test_schedule_recurring_job_next_run_calculation(
    tool_with_db, sample_job_config
):
    """Test next run time calculation."""
    job_result = await tool_with_db.create_scraping_job(sample_job_config)
    job_output = json.loads(job_result.output)
    job_id = job_output["job_id"]

    # Test daily schedule
    result = await tool_with_db.schedule_recurring_job(job_id, "0 0 * * *")

    output = json.loads(result.output)
    assert output["frequency"] == "daily"
    assert "next_run" in output
    # Verify next_run is a valid ISO timestamp
    datetime.fromisoformat(output["next_run"])


# ==================== Test execute routing ====================


@pytest.mark.asyncio
async def test_execute_create_scraping_job(tool, sample_job_config):
    """Test action routing for create_scraping_job."""
    result = await tool.execute(
        action="create_scraping_job", job_config=sample_job_config
    )

    assert isinstance(result, ToolResult)
    assert result.error is None
    output = json.loads(result.output)
    assert "job_id" in output


@pytest.mark.asyncio
async def test_execute_invalid_action(tool):
    """Test error handling for invalid action."""
    result = await tool.execute(action="invalid_action")

    assert isinstance(result, ToolResult)
    assert result.error is not None
    assert "Unknown action" in result.error


@pytest.mark.asyncio
async def test_execute_missing_action(tool):
    """Test validation when action is missing."""
    result = await tool.execute()

    assert isinstance(result, ToolResult)
    assert result.error is not None
    assert "Action is required" in result.error


# ==================== Test Helper Methods ====================


def test_validate_css_selector(tool):
    """Test CSS selector validation."""
    # Valid selectors
    assert tool._validate_css_selector(".class-name") is True
    assert tool._validate_css_selector("#id-name") is True
    assert tool._validate_css_selector("div") is True
    assert tool._validate_css_selector("div > span") is True

    # Invalid selectors
    assert tool._validate_css_selector("") is False
    assert tool._validate_css_selector(None) is False


def test_validate_cron_schedule(tool):
    """Test cron schedule validation."""
    # Valid cron schedules
    assert tool._validate_cron_schedule("0 * * * *") is True
    assert tool._validate_cron_schedule("0 */6 * * *") is True
    assert tool._validate_cron_schedule("0 0 * * *") is True
    assert tool._validate_cron_schedule("0 0 1 * *") is True

    # Invalid cron schedules
    assert tool._validate_cron_schedule("") is False
    assert tool._validate_cron_schedule("0 */6") is False
    assert tool._validate_cron_schedule("invalid") is False
    assert tool._validate_cron_schedule("99 99 99 99 99") is False


def test_detect_job_type(tool):
    """Test job type detection from URL."""
    assert (
        tool._detect_job_type("https://shop.example.com/products") == "price_monitoring"
    )
    assert (
        tool._detect_job_type("https://jobs.example.com/listings") == "lead_generation"
    )
    assert (
        tool._detect_job_type("https://news.example.com/articles") == "content_scraping"
    )
    assert (
        tool._detect_job_type("https://realestate.example.com/homes")
        == "market_research"
    )
    assert (
        tool._detect_job_type("https://social.example.com/profiles")
        == "contact_scraping"
    )
    assert tool._detect_job_type("https://example.com") == "general_scraping"


def test_parse_cron_to_frequency(tool):
    """Test cron to frequency conversion."""
    assert tool._parse_cron_to_frequency("0 * * * *") == "hourly"
    assert tool._parse_cron_to_frequency("0 0 * * *") == "daily"
    assert tool._parse_cron_to_frequency("0 0 * * 0") == "weekly"
    assert tool._parse_cron_to_frequency("0 0 1 * *") == "monthly"
    assert tool._parse_cron_to_frequency("0 */6 * * *") == "every_6_hours"


def test_calculate_quality_score(tool):
    """Test data quality score calculation."""
    selectors = {"title": ".title", "price": ".price", "rating": ".rating"}

    # Complete data
    item = {"title": "Product", "price": 10.0, "rating": 4.5}
    score = tool._calculate_quality_score(item, selectors)
    assert score == 1.0

    # Partial data
    item = {"title": "Product", "price": 10.0}
    score = tool._calculate_quality_score(item, selectors)
    assert 0 < score < 1.0

    # Empty values
    item = {"title": "", "price": None, "rating": 4.5}
    score = tool._calculate_quality_score(item, selectors)
    assert 0 < score < 1.0


def test_apply_filter(tool):
    """Test filter transformation logic."""
    data = create_test_scraped_data()

    # Greater than filter
    transform = {"field": "price", "operator": ">", "value": 30}
    filtered = tool._apply_filter(data, transform)
    assert all(item["price"] > 30 for item in filtered)

    # Equals filter
    transform = {"field": "rating", "operator": "==", "value": 4.5}
    filtered = tool._apply_filter(data, transform)
    assert all(item["rating"] == 4.5 for item in filtered)


def test_apply_sort(tool):
    """Test sort transformation logic."""
    data = create_test_scraped_data()

    # Ascending sort
    transform = {"field": "price", "order": "asc"}
    sorted_data = tool._apply_sort(data, transform)
    prices = [item["price"] for item in sorted_data]
    assert prices == sorted(prices)

    # Descending sort
    transform = {"field": "rating", "order": "desc"}
    sorted_data = tool._apply_sort(data, transform)
    ratings = [item["rating"] for item in sorted_data]
    assert ratings == sorted(ratings, reverse=True)


def test_apply_deduplicate(tool):
    """Test deduplication logic."""
    data = [
        {"title": "Product A", "price": 10.0},
        {"title": "Product A", "price": 15.0},  # Duplicate title
        {"title": "Product B", "price": 20.0},
    ]

    transform = {"fields": ["title"]}
    deduped = tool._apply_deduplicate(data, transform)
    assert len(deduped) == 2  # Should remove one duplicate


def test_convert_to_format(tool):
    """Test data format conversion."""
    data = create_test_scraped_data()

    # JSON format
    json_output = tool._convert_to_format(data, "json")
    assert isinstance(json_output, str)
    assert "Product A" in json_output

    # CSV format
    csv_output = tool._convert_to_format(data, "csv")
    assert isinstance(csv_output, str)
    assert "title" in csv_output  # Header
    assert "Product A" in csv_output

    # XML format
    xml_output = tool._convert_to_format(data, "xml")
    assert "<?xml" in xml_output
    assert "<data>" in xml_output
    assert "</data>" in xml_output


@pytest.mark.asyncio
async def test_cache_functionality(tool):
    """Test caching behavior."""
    cache_key = "test_cache_key"
    test_data = {"test": "value", "number": 123}

    # Set cache
    await tool.cache_set(cache_key, test_data, ttl=3600)

    # Get cache
    cached_value = await tool.cache_get(cache_key)

    assert cached_value == test_data


@pytest.mark.asyncio
async def test_rate_limit_tracking(tool):
    """Test rate limit request tracking."""
    domain = "example.com"

    # Record multiple requests
    for i in range(5):
        tool.record_request(domain)

    # Verify tracking
    assert domain in tool._rate_limit_state
    assert len(tool._rate_limit_state[domain]) == 5


def test_mock_scrape_data(tool):
    """Test mock data generation."""
    selectors = {"title": ".title", "price": ".price"}

    # Test different job types
    ecommerce_data = tool._mock_scrape_data("price_monitoring", selectors)
    assert len(ecommerce_data) > 0
    assert "title" in ecommerce_data[0]

    jobs_data = tool._mock_scrape_data("lead_generation", selectors)
    assert len(jobs_data) > 0

    news_data = tool._mock_scrape_data("content_scraping", selectors)
    assert len(news_data) > 0


def test_matches_filters(tool):
    """Test filter matching logic."""
    item = {"price": 50.0, "rating": 4.5, "in_stock": True}

    # MongoDB-style filters
    assert tool._matches_filters(item, {"price": {"$gt": 40}}) is True
    assert tool._matches_filters(item, {"price": {"$gt": 60}}) is False
    assert tool._matches_filters(item, {"rating": {"$gte": 4.5}}) is True
    assert tool._matches_filters(item, {"rating": {"$lt": 4.0}}) is False

    # Direct equality
    assert tool._matches_filters(item, {"in_stock": True}) is True
    assert tool._matches_filters(item, {"in_stock": False}) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
