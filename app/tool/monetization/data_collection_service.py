"""
Data Collection Service Tool

Automated web scraping service that collects structured data from websites
and sells it as datasets or API access to businesses and researchers.

Revenue Model:
- Monthly Revenue: $800-$3,000
- Pricing: $50-500/dataset or $100-1,000/month for API access
- Clients: Market researchers, businesses, academics, data analysts
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Any, ClassVar, Dict, List, Optional
from urllib.parse import urlparse

from app.logger import logger
from app.tool.base import ToolResult
from app.tool.monetization.base import (
    CacheConfig,
    MonetizationBase,
    MonetizationError,
    ValidationError,
)


class DataCollectionServiceTool(MonetizationBase):
    """
    Automated web scraping service for collecting and selling structured data.

    Features:
    - Configurable scraping jobs with CSS/XPath selectors
    - Multi-format data export (JSON, CSV, Excel, SQL, XML)
    - Data transformation pipeline (filter, sort, deduplicate, enrich)
    - Recurring job scheduling (cron-like syntax)
    - Quality validation and scoring
    - Mock scraping for testing (no real web requests)

    Revenue potential: $800-$3,000/month
    Use cases: Market research, price monitoring, lead generation, content aggregation
    """

    name: str = "data_collection_service"
    description: str = (
        "Automated web scraping and data collection service with "
        "multi-format export and transformation pipeline"
    )

    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "create_scraping_job",
                    "execute_scrape",
                    "transform_data",
                    "export_dataset",
                    "schedule_recurring_job",
                ],
                "description": "Action to perform",
            },
            "job_config": {
                "type": "object",
                "description": "Job configuration for create_scraping_job",
                "properties": {
                    "name": {"type": "string"},
                    "url": {"type": "string"},
                    "selectors": {"type": "object"},
                    "pagination": {"type": "object"},
                    "output_format": {"type": "string"},
                    "schedule": {"type": "string"},
                },
            },
            "job_id": {
                "type": "string",
                "description": "Job ID for execute_scrape, transform_data, export_dataset",
            },
            "transformations": {
                "type": "array",
                "description": "List of transformations to apply",
                "items": {"type": "object"},
            },
            "format": {
                "type": "string",
                "description": "Export format (json, csv, excel, sql, xml)",
            },
            "export_options": {
                "type": "object",
                "description": "Export options (filters, pagination, etc.)",
            },
            "schedule": {
                "type": "string",
                "description": "Cron-like schedule string (e.g., '0 */6 * * *')",
            },
        },
        "required": ["action"],
    }

    # Supported export formats
    SUPPORTED_FORMATS: ClassVar[List[str]] = ["json", "csv", "excel", "sql", "xml"]

    # Supported transformation types
    TRANSFORMATION_TYPES: ClassVar[List[str]] = [
        "filter",
        "sort",
        "deduplicate",
        "enrich",
        "validate",
    ]

    # Mock data templates for different scraping scenarios
    MOCK_DATA_TEMPLATES: ClassVar[Dict[str, List[Dict]]] = {
        "ecommerce": [
            {
                "title": "Premium Wireless Headphones",
                "price": 79.99,
                "rating": 4.5,
                "reviews": 1234,
                "in_stock": True,
                "url": "https://example.com/product/1",
            },
            {
                "title": "Smart Watch Pro",
                "price": 199.99,
                "rating": 4.7,
                "reviews": 892,
                "in_stock": True,
                "url": "https://example.com/product/2",
            },
            {
                "title": "Bluetooth Speaker",
                "price": 49.99,
                "rating": 4.3,
                "reviews": 567,
                "in_stock": False,
                "url": "https://example.com/product/3",
            },
        ],
        "jobs": [
            {
                "title": "Senior Software Engineer",
                "company": "TechCorp Inc.",
                "location": "San Francisco, CA",
                "salary": "$120k-$180k",
                "posted_date": "2024-01-15",
                "url": "https://jobs.example.com/123",
            },
            {
                "title": "Data Scientist",
                "company": "DataWorks",
                "location": "Remote",
                "salary": "$100k-$150k",
                "posted_date": "2024-01-14",
                "url": "https://jobs.example.com/124",
            },
        ],
        "real_estate": [
            {
                "address": "123 Main St, Apt 4B",
                "price": 450000,
                "bedrooms": 2,
                "bathrooms": 2,
                "sqft": 1200,
                "listing_date": "2024-01-10",
                "url": "https://realestate.example.com/listing/1",
            },
            {
                "address": "456 Oak Ave",
                "price": 750000,
                "bedrooms": 3,
                "bathrooms": 2.5,
                "sqft": 2000,
                "listing_date": "2024-01-12",
                "url": "https://realestate.example.com/listing/2",
            },
        ],
        "news": [
            {
                "headline": "Tech Industry Sees Major Growth",
                "author": "John Smith",
                "published": "2024-01-15T10:30:00",
                "category": "Technology",
                "summary": "The tech sector experienced significant growth...",
                "url": "https://news.example.com/article/1",
            },
            {
                "headline": "Market Analysis: Q1 2024",
                "author": "Jane Doe",
                "published": "2024-01-14T14:20:00",
                "category": "Finance",
                "summary": "Financial markets showed mixed results...",
                "url": "https://news.example.com/article/2",
            },
        ],
        "social": [
            {
                "username": "techinfluencer",
                "followers": 45000,
                "posts": 1234,
                "engagement_rate": 3.2,
                "verified": True,
                "profile_url": "https://social.example.com/techinfluencer",
            },
            {
                "username": "businessguru",
                "followers": 78000,
                "posts": 890,
                "engagement_rate": 4.5,
                "verified": True,
                "profile_url": "https://social.example.com/businessguru",
            },
        ],
    }

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the data collection service tool.

        Args:
            **kwargs: Action-specific parameters

        Returns:
            ToolResult with action results
        """
        action = kwargs.get("action")

        if not action:
            raise ValidationError("Action is required")

        self.log_action("execute", action=action, params=kwargs)

        try:
            if action == "create_scraping_job":
                return await self.create_scraping_job(
                    job_config=kwargs.get("job_config", {})
                )
            elif action == "execute_scrape":
                return await self.execute_scrape(job_id=kwargs.get("job_id"))
            elif action == "transform_data":
                return await self.transform_data(
                    job_id=kwargs.get("job_id"),
                    transformations=kwargs.get("transformations", []),
                )
            elif action == "export_dataset":
                return await self.export_dataset(
                    job_id=kwargs.get("job_id"),
                    format=kwargs.get("format", "json"),
                    options=kwargs.get("export_options", {}),
                )
            elif action == "schedule_recurring_job":
                return await self.schedule_recurring_job(
                    job_id=kwargs.get("job_id"), schedule=kwargs.get("schedule")
                )
            else:
                raise ValidationError(f"Unknown action: {action}")

        except ValidationError as e:
            self.log_error("validation_error", error=str(e))
            return ToolResult(error=str(e))
        except Exception as e:
            self.log_error("execution_error", error=str(e))
            return ToolResult(error=f"Execution failed: {str(e)}")

    async def create_scraping_job(self, job_config: Dict) -> ToolResult:
        """
        Create and configure new scraping job.

        Flow:
        1. Validate job configuration
        2. Parse and validate URL
        3. Validate CSS selectors
        4. Generate job ID
        5. Store job configuration in database
        6. Return job details

        Args:
            job_config: Job configuration dictionary with:
                - name: Job name
                - url: Target URL
                - selectors: Dict of CSS/XPath selectors
                - pagination: Optional pagination config
                - output_format: Desired output format
                - schedule: Optional cron schedule

        Returns:
            ToolResult with job_id and configuration

        Example:
            >>> config = {
            ...     'name': 'Product Price Monitor',
            ...     'url': 'https://example.com/products',
            ...     'selectors': {
            ...         'title': '.product-title',
            ...         'price': '.product-price',
            ...         'rating': '.product-rating'
            ...     },
            ...     'pagination': {
            ...         'enabled': True,
            ...         'next_selector': '.pagination-next',
            ...         'max_pages': 10
            ...     },
            ...     'output_format': 'json',
            ...     'schedule': '0 0 * * *'
            ... }
            >>> result = await tool.create_scraping_job(config)
        """
        # Validate required fields
        self.validate_required_params(job_config, ["name", "url", "selectors"])

        name = job_config["name"]
        url = job_config["url"]
        selectors = job_config["selectors"]
        pagination = job_config.get("pagination", {})
        output_format = job_config.get("output_format", "json")
        schedule = job_config.get("schedule")

        # Validate URL
        if not self.validate_url(url):
            raise ValidationError(f"Invalid URL: {url}")

        # Validate selectors
        if not selectors or not isinstance(selectors, dict):
            raise ValidationError("Selectors must be a non-empty dictionary")

        for field, selector in selectors.items():
            if not self._validate_css_selector(selector):
                raise ValidationError(
                    f"Invalid CSS selector for field '{field}': {selector}"
                )

        # Validate output format
        if output_format not in self.SUPPORTED_FORMATS:
            raise ValidationError(
                f"Unsupported format '{output_format}'. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # Validate schedule if provided
        if schedule and not self._validate_cron_schedule(schedule):
            raise ValidationError(f"Invalid cron schedule: {schedule}")

        # Determine job type from URL
        job_type = self._detect_job_type(url)

        # Generate job ID
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(url) % 10000}"

        self.log_action(
            "create_scraping_job",
            job_id=job_id,
            name=name,
            url=url,
            job_type=job_type,
        )

        # Store in database (mock implementation)
        if self.connection_id:
            try:
                await self.db_execute(
                    """
                    INSERT INTO data_collection_jobs
                    (client_id, job_name, job_type, target_sources, data_schema,
                     collection_frequency, status, created_at)
                    VALUES
                    (:client_id, :job_name, :job_type, :target_sources, :data_schema,
                     :frequency, :status, :created_at)
                    """,
                    {
                        "client_id": "demo_client",
                        "job_name": name,
                        "job_type": job_type,
                        "target_sources": [url],
                        "data_schema": json.dumps(selectors),
                        "frequency": (
                            self._parse_cron_to_frequency(schedule)
                            if schedule
                            else "once"
                        ),
                        "status": "active",
                        "created_at": datetime.now(),
                    },
                )
            except Exception as e:
                self.log_error("database_store_failed", error=str(e))

        result = {
            "job_id": job_id,
            "name": name,
            "url": url,
            "job_type": job_type,
            "selectors": selectors,
            "pagination": pagination,
            "output_format": output_format,
            "schedule": schedule,
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "next_run": self._calculate_next_run(schedule) if schedule else None,
        }

        # Cache the job config
        cache_key = self._cache_key("job_config", job_id=job_id)
        await self.cache_set(cache_key, result, ttl=CacheConfig.TTL["default"])

        self.log_metric("job_created", job_id)

        return ToolResult(output=json.dumps(result, indent=2))

    async def execute_scrape(self, job_id: str) -> ToolResult:
        """
        Execute scraping job and store results.

        Flow:
        1. Load job configuration
        2. Execute web scraping (mock implementation)
        3. Handle pagination if enabled
        4. Apply rate limiting
        5. Extract data using selectors
        6. Calculate quality score
        7. Store results in database
        8. Return scraping summary

        Args:
            job_id: Job identifier

        Returns:
            ToolResult with scraped data count and status

        Example:
            >>> result = await tool.execute_scrape("job_20240115_123456_7890")
        """
        if not job_id:
            raise ValidationError("job_id is required")

        self.log_action("execute_scrape", job_id=job_id)

        # Load job config from cache or database
        cache_key = self._cache_key("job_config", job_id=job_id)
        job_config = await self.cache_get(cache_key)

        if not job_config:
            raise ValidationError(f"Job not found: {job_id}")

        url = job_config["url"]
        selectors = job_config["selectors"]
        pagination = job_config.get("pagination", {})
        job_type = job_config["job_type"]

        # Check rate limit for the domain
        domain = urlparse(url).netloc
        await self.wait_for_rate_limit(domain, max_wait=30)
        self.record_request(domain)

        # Mock scraping implementation
        # In production, would use BeautifulSoup/Selenium
        scraped_data = self._mock_scrape_data(job_type, selectors)

        # Handle pagination
        if pagination.get("enabled", False):
            max_pages = pagination.get("max_pages", 1)
            for page in range(2, max_pages + 1):
                # Mock pagination
                page_data = self._mock_scrape_data(job_type, selectors)
                scraped_data.extend(page_data)

                # Rate limiting between pages
                await asyncio.sleep(0.1)

        # Calculate quality scores
        for item in scraped_data:
            item["quality_score"] = self._calculate_quality_score(item, selectors)

        # Store results in database
        records_stored = 0
        if self.connection_id:
            try:
                for item in scraped_data:
                    await self.db_execute(
                        """
                        INSERT INTO collected_data
                        (job_id, raw_data, quality_score, collected_at, source_url)
                        VALUES (:job_id, :raw_data, :quality_score, :collected_at, :source_url)
                        """,
                        {
                            "job_id": job_id,
                            "raw_data": json.dumps(item),
                            "quality_score": item["quality_score"],
                            "collected_at": datetime.now(),
                            "source_url": url,
                        },
                    )
                    records_stored += 1
            except Exception as e:
                self.log_error("database_store_failed", error=str(e))

        # Calculate statistics
        avg_quality = (
            sum(item["quality_score"] for item in scraped_data) / len(scraped_data)
            if scraped_data
            else 0
        )

        result = {
            "job_id": job_id,
            "status": "completed",
            "records_scraped": len(scraped_data),
            "records_stored": (
                records_stored if self.connection_id else len(scraped_data)
            ),
            "avg_quality_score": round(avg_quality, 2),
            "execution_time": "2.3s",  # Mock timing
            "pages_scraped": 1
            + (pagination.get("max_pages", 1) - 1 if pagination.get("enabled") else 0),
            "scraped_at": datetime.now().isoformat(),
            "sample_data": scraped_data[:3] if scraped_data else [],
        }

        # Cache the results
        cache_key = self._cache_key("scrape_results", job_id=job_id)
        await self.cache_set(
            cache_key, scraped_data, ttl=CacheConfig.TTL["api_response"]
        )

        self.log_metric("records_scraped", len(scraped_data))

        return ToolResult(output=json.dumps(result, indent=2))

    async def transform_data(
        self, job_id: str, transformations: List[Dict]
    ) -> ToolResult:
        """
        Clean and transform scraped data.

        Flow:
        1. Load scraped data
        2. Apply transformations in sequence:
           - filter: Remove records not matching criteria
           - sort: Sort by field
           - deduplicate: Remove duplicates based on fields
           - enrich: Add calculated fields
           - validate: Check against schema
        3. Update quality scores
        4. Store transformed data
        5. Return transformation summary

        Args:
            job_id: Job identifier
            transformations: List of transformation operations

        Returns:
            ToolResult with transformation summary

        Example:
            >>> transformations = [
            ...     {'type': 'filter', 'field': 'price', 'operator': '>', 'value': 10},
            ...     {'type': 'sort', 'field': 'rating', 'order': 'desc'},
            ...     {'type': 'deduplicate', 'fields': ['title', 'url']},
            ...     {'type': 'enrich', 'field': 'price', 'function': 'convert_currency'},
            ...     {'type': 'validate', 'schema': {'title': 'required', 'price': 'number'}}
            ... ]
            >>> result = await tool.transform_data("job_123", transformations)
        """
        if not job_id:
            raise ValidationError("job_id is required")

        if not transformations:
            raise ValidationError("transformations list cannot be empty")

        self.log_action(
            "transform_data", job_id=job_id, transformation_count=len(transformations)
        )

        # Load scraped data from cache
        cache_key = self._cache_key("scrape_results", job_id=job_id)
        data = await self.cache_get(cache_key)

        if not data:
            raise ValidationError(f"No scraped data found for job: {job_id}")

        original_count = len(data)
        transformation_log = []

        # Apply transformations in sequence
        for idx, transform in enumerate(transformations):
            transform_type = transform.get("type")

            if transform_type not in self.TRANSFORMATION_TYPES:
                raise ValidationError(
                    f"Unsupported transformation type: {transform_type}. "
                    f"Supported: {', '.join(self.TRANSFORMATION_TYPES)}"
                )

            before_count = len(data)

            if transform_type == "filter":
                data = self._apply_filter(data, transform)
            elif transform_type == "sort":
                data = self._apply_sort(data, transform)
            elif transform_type == "deduplicate":
                data = self._apply_deduplicate(data, transform)
            elif transform_type == "enrich":
                data = self._apply_enrich(data, transform)
            elif transform_type == "validate":
                data = self._apply_validate(data, transform)

            after_count = len(data)

            transformation_log.append(
                {
                    "step": idx + 1,
                    "type": transform_type,
                    "before_count": before_count,
                    "after_count": after_count,
                    "removed": before_count - after_count,
                }
            )

        # Update data in cache
        await self.cache_set(cache_key, data, ttl=CacheConfig.TTL["api_response"])

        # Store transformed data in database
        if self.connection_id:
            try:
                for item in data:
                    await self.db_execute(
                        """
                        UPDATE collected_data
                        SET cleaned_data = :cleaned_data,
                            quality_score = :quality_score
                        WHERE job_id = :job_id AND raw_data = :raw_data
                        """,
                        {
                            "job_id": job_id,
                            "cleaned_data": json.dumps(item),
                            "quality_score": item.get("quality_score", 0.8),
                            "raw_data": json.dumps(item),
                        },
                    )
            except Exception as e:
                self.log_error("database_update_failed", error=str(e))

        result = {
            "job_id": job_id,
            "status": "transformed",
            "original_records": original_count,
            "final_records": len(data),
            "records_removed": original_count - len(data),
            "transformations_applied": len(transformations),
            "transformation_log": transformation_log,
            "sample_data": data[:3] if data else [],
        }

        self.log_metric("records_transformed", len(data))

        return ToolResult(output=json.dumps(result, indent=2))

    async def export_dataset(
        self, job_id: str, format: str, options: Dict
    ) -> ToolResult:
        """
        Export data in specified format.

        Flow:
        1. Load transformed data
        2. Apply filters from options
        3. Apply pagination from options
        4. Convert to requested format
        5. Generate download URL/file
        6. Track download for billing
        7. Return export details

        Args:
            job_id: Job identifier
            format: Export format (json, csv, excel, sql, xml)
            options: Export options:
                - filters: Additional filters
                - limit: Max records
                - offset: Skip records
                - fields: Specific fields to export

        Returns:
            ToolResult with export details and download info

        Example:
            >>> options = {
            ...     'filters': {'price': {'$gt': 50}},
            ...     'limit': 100,
            ...     'fields': ['title', 'price', 'rating']
            ... }
            >>> result = await tool.export_dataset("job_123", "csv", options)
        """
        if not job_id:
            raise ValidationError("job_id is required")

        if format not in self.SUPPORTED_FORMATS:
            raise ValidationError(
                f"Unsupported format '{format}'. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        self.log_action("export_dataset", job_id=job_id, format=format)

        # Load data from cache
        cache_key = self._cache_key("scrape_results", job_id=job_id)
        data = await self.cache_get(cache_key)

        if not data:
            raise ValidationError(f"No data found for job: {job_id}")

        # Apply additional filters
        filters = options.get("filters", {})
        if filters:
            data = [item for item in data if self._matches_filters(item, filters)]

        # Apply field selection
        fields = options.get("fields")
        if fields:
            data = [{k: v for k, v in item.items() if k in fields} for item in data]

        # Apply pagination
        offset = options.get("offset", 0)
        limit = options.get("limit", len(data))
        paginated_data = data[offset : offset + limit]

        # Convert to requested format
        export_content = self._convert_to_format(paginated_data, format)

        # Generate mock download URL
        file_ext = format if format != "excel" else "xlsx"
        filename = (
            f"{job_id}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_ext}"
        )
        download_url = f"https://datacollection.example.com/downloads/{filename}"

        # Store export metadata in database
        if self.connection_id:
            try:
                await self.db_execute(
                    """
                    UPDATE collected_data
                    SET exported = TRUE,
                        export_format = :format,
                        exported_at = :exported_at
                    WHERE job_id = :job_id
                    """,
                    {
                        "job_id": job_id,
                        "format": format,
                        "exported_at": datetime.now(),
                    },
                )
            except Exception as e:
                self.log_error("database_update_failed", error=str(e))

        result = {
            "job_id": job_id,
            "format": format,
            "records_exported": len(paginated_data),
            "total_records": len(data),
            "file_size": f"{len(export_content) / 1024:.2f} KB",
            "filename": filename,
            "download_url": download_url,
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
            "exported_at": datetime.now().isoformat(),
        }

        self.log_metric("dataset_exported", format)

        return ToolResult(output=json.dumps(result, indent=2))

    async def schedule_recurring_job(self, job_id: str, schedule: str) -> ToolResult:
        """
        Set up recurring scraping schedule.

        Flow:
        1. Validate job exists
        2. Parse and validate cron schedule
        3. Calculate next run time
        4. Store schedule in database
        5. Enable job for automatic execution
        6. Return schedule configuration

        Args:
            job_id: Job identifier
            schedule: Cron-like schedule string
                Examples:
                - "0 * * * *" - Every hour
                - "0 */6 * * *" - Every 6 hours
                - "0 0 * * *" - Daily at midnight
                - "0 0 * * 0" - Weekly on Sunday
                - "0 0 1 * *" - Monthly on 1st

        Returns:
            ToolResult with schedule configuration

        Example:
            >>> result = await tool.schedule_recurring_job(
            ...     "job_123",
            ...     "0 */6 * * *"  # Every 6 hours
            ... )
        """
        if not job_id:
            raise ValidationError("job_id is required")

        if not schedule:
            raise ValidationError("schedule is required")

        # Validate cron schedule
        if not self._validate_cron_schedule(schedule):
            raise ValidationError(
                f"Invalid cron schedule: {schedule}. "
                f"Expected format: 'minute hour day month weekday'"
            )

        self.log_action("schedule_recurring_job", job_id=job_id, schedule=schedule)

        # Load job config
        cache_key = self._cache_key("job_config", job_id=job_id)
        job_config = await self.cache_get(cache_key)

        if not job_config:
            raise ValidationError(f"Job not found: {job_id}")

        # Parse schedule
        frequency = self._parse_cron_to_frequency(schedule)
        next_run = self._calculate_next_run(schedule)

        # Update job config with schedule
        job_config["schedule"] = schedule
        job_config["frequency"] = frequency
        job_config["next_run"] = next_run
        job_config["scheduled_at"] = datetime.now().isoformat()

        # Update cache
        await self.cache_set(cache_key, job_config, ttl=CacheConfig.TTL["default"])

        # Update database
        if self.connection_id:
            try:
                await self.db_execute(
                    """
                    UPDATE data_collection_jobs
                    SET collection_frequency = :frequency,
                        next_run = :next_run,
                        updated_at = :updated_at
                    WHERE job_name = :job_id
                    """,
                    {
                        "job_id": job_id,
                        "frequency": frequency,
                        "next_run": datetime.fromisoformat(next_run),
                        "updated_at": datetime.now(),
                    },
                )
            except Exception as e:
                self.log_error("database_update_failed", error=str(e))

        result = {
            "job_id": job_id,
            "schedule": schedule,
            "frequency": frequency,
            "next_run": next_run,
            "status": "scheduled",
            "scheduled_at": job_config["scheduled_at"],
            "description": self._describe_schedule(schedule),
        }

        self.log_metric("job_scheduled", job_id)

        return ToolResult(output=json.dumps(result, indent=2))

    # ==================== Helper Methods ====================

    def _validate_css_selector(self, selector: str) -> bool:
        """
        Validate CSS selector syntax.

        Basic validation - checks for common patterns.
        In production, would use cssselect or similar library.
        """
        if not selector or not isinstance(selector, str):
            return False

        # Basic CSS selector patterns
        valid_patterns = [
            r"^[.#][\w-]+$",  # .class or #id
            r"^[\w-]+$",  # tag name
            r"^[\w-]+\[[\w-]+[=~|^$*]?.*\]$",  # attribute selector
            r"^[.#]?[\w-]+\s*[>+~]\s*[.#]?[\w-]+$",  # combinator
            r"^[.#]?[\w-]+[\s>+~][.#]?[\w-]+",  # descendant
        ]

        return any(re.match(pattern, selector.strip()) for pattern in valid_patterns)

    def _validate_cron_schedule(self, schedule: str) -> bool:
        """
        Validate cron schedule syntax.

        Expected format: "minute hour day month weekday"
        Example: "0 */6 * * *" (every 6 hours)
        """
        if not schedule or not isinstance(schedule, str):
            return False

        parts = schedule.split()
        if len(parts) != 5:
            return False

        # Basic validation of each part
        patterns = [
            r"^(\*|[0-5]?[0-9]|\*/[0-9]+|[0-9]+-[0-9]+)$",  # minute (0-59)
            r"^(\*|[01]?[0-9]|2[0-3]|\*/[0-9]+|[0-9]+-[0-9]+)$",  # hour (0-23)
            r"^(\*|[1-2]?[0-9]|3[01]|\*/[0-9]+|[0-9]+-[0-9]+)$",  # day (1-31)
            r"^(\*|[1-9]|1[0-2]|\*/[0-9]+|[0-9]+-[0-9]+)$",  # month (1-12)
            r"^(\*|[0-6]|\*/[0-9]+|[0-9]+-[0-9]+)$",  # weekday (0-6)
        ]

        return all(re.match(pattern, part) for part, pattern in zip(parts, patterns))

    def _detect_job_type(self, url: str) -> str:
        """Detect job type from URL patterns."""
        url_lower = url.lower()

        if any(
            x in url_lower for x in ["shop", "product", "store", "ecommerce", "buy"]
        ):
            return "price_monitoring"
        elif any(x in url_lower for x in ["job", "career", "hiring"]):
            return "lead_generation"
        elif any(x in url_lower for x in ["news", "article", "blog"]):
            return "content_scraping"
        elif any(x in url_lower for x in ["real", "estate", "property", "listing"]):
            return "market_research"
        elif any(x in url_lower for x in ["social", "twitter", "facebook", "linkedin"]):
            return "contact_scraping"
        else:
            return "general_scraping"

    def _parse_cron_to_frequency(self, schedule: str) -> str:
        """Convert cron schedule to human-readable frequency."""
        parts = schedule.split()

        if schedule == "0 * * * *":
            return "hourly"
        elif schedule.startswith("0 0 * * *"):
            return "daily"
        elif schedule.startswith("0 0 * * 0"):
            return "weekly"
        elif schedule.startswith("0 0 1 * *"):
            return "monthly"
        elif "*/6" in parts[1]:
            return "every_6_hours"
        elif "*/12" in parts[1]:
            return "every_12_hours"
        else:
            return "custom"

    def _calculate_next_run(self, schedule: str) -> str:
        """Calculate next run time from cron schedule."""
        # Simplified calculation - in production would use croniter
        now = datetime.now()

        if schedule == "0 * * * *":  # Hourly
            next_run = now.replace(minute=0, second=0, microsecond=0) + timedelta(
                hours=1
            )
        elif schedule == "0 0 * * *":  # Daily
            next_run = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif schedule == "0 */6 * * *":  # Every 6 hours
            next_hour = ((now.hour // 6) + 1) * 6
            if next_hour >= 24:
                next_run = (now + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            else:
                next_run = now.replace(
                    hour=next_hour, minute=0, second=0, microsecond=0
                )
        else:
            # Default to 1 hour from now
            next_run = now + timedelta(hours=1)

        return next_run.isoformat()

    def _describe_schedule(self, schedule: str) -> str:
        """Generate human-readable schedule description."""
        descriptions = {
            "0 * * * *": "Every hour",
            "0 */6 * * *": "Every 6 hours",
            "0 */12 * * *": "Every 12 hours",
            "0 0 * * *": "Daily at midnight",
            "0 0 * * 0": "Weekly on Sunday at midnight",
            "0 0 1 * *": "Monthly on the 1st at midnight",
        }

        return descriptions.get(schedule, f"Custom schedule: {schedule}")

    def _mock_scrape_data(self, job_type: str, selectors: Dict) -> List[Dict]:
        """
        Generate mock scraped data based on job type.

        In production, this would use BeautifulSoup/Selenium to actually scrape.
        """
        # Map job types to mock templates
        type_mapping = {
            "price_monitoring": "ecommerce",
            "lead_generation": "jobs",
            "market_research": "real_estate",
            "content_scraping": "news",
            "contact_scraping": "social",
            "general_scraping": "ecommerce",
        }

        template_type = type_mapping.get(job_type, "ecommerce")
        template_data = self.MOCK_DATA_TEMPLATES.get(template_type, [])

        # Return a copy with some variations
        return [item.copy() for item in template_data]

    def _calculate_quality_score(self, item: Dict, selectors: Dict) -> float:
        """
        Calculate data quality score (0-1).

        Factors:
        - Completeness: All expected fields present
        - Non-empty values
        - Valid data types
        """
        score = 0.0
        total_fields = len(selectors)

        for field in selectors:
            if field in item:
                score += 0.5  # Field exists
                if item[field] not in [None, "", []]:
                    score += 0.5  # Field has value

        return min(round(score / total_fields, 2), 1.0) if total_fields > 0 else 0.8

    def _apply_filter(self, data: List[Dict], transform: Dict) -> List[Dict]:
        """Apply filter transformation."""
        field = transform.get("field")
        operator = transform.get("operator", "==")
        value = transform.get("value")

        if not field:
            return data

        filtered = []
        for item in data:
            if field not in item:
                continue

            item_value = item[field]

            try:
                if operator == "==":
                    if item_value == value:
                        filtered.append(item)
                elif operator == "!=":
                    if item_value != value:
                        filtered.append(item)
                elif operator == ">":
                    if float(item_value) > float(value):
                        filtered.append(item)
                elif operator == "<":
                    if float(item_value) < float(value):
                        filtered.append(item)
                elif operator == ">=":
                    if float(item_value) >= float(value):
                        filtered.append(item)
                elif operator == "<=":
                    if float(item_value) <= float(value):
                        filtered.append(item)
                elif operator == "contains":
                    if str(value).lower() in str(item_value).lower():
                        filtered.append(item)
            except (ValueError, TypeError):
                continue

        return filtered

    def _apply_sort(self, data: List[Dict], transform: Dict) -> List[Dict]:
        """Apply sort transformation."""
        field = transform.get("field")
        order = transform.get("order", "asc")

        if not field:
            return data

        reverse = order.lower() == "desc"

        try:
            return sorted(
                data,
                key=lambda x: x.get(field, 0),
                reverse=reverse,
            )
        except TypeError:
            # Fallback if values aren't comparable
            return data

    def _apply_deduplicate(self, data: List[Dict], transform: Dict) -> List[Dict]:
        """Apply deduplication transformation."""
        fields = transform.get("fields", [])

        if not fields:
            return data

        seen = set()
        deduplicated = []

        for item in data:
            # Create hash of specified fields
            key_values = tuple(item.get(f) for f in fields)

            if key_values not in seen:
                seen.add(key_values)
                deduplicated.append(item)

        return deduplicated

    def _apply_enrich(self, data: List[Dict], transform: Dict) -> List[Dict]:
        """Apply enrichment transformation."""
        field = transform.get("field")
        function = transform.get("function")

        if not field or not function:
            return data

        for item in data:
            if field in item:
                # Mock enrichment functions
                if function == "convert_currency":
                    # Mock currency conversion
                    if isinstance(item[field], (int, float)):
                        item[f"{field}_usd"] = item[field]
                        item[f"{field}_eur"] = round(item[field] * 0.92, 2)
                elif function == "extract_domain":
                    # Extract domain from URL
                    if "url" in item:
                        parsed = urlparse(item["url"])
                        item["domain"] = parsed.netloc
                elif function == "calculate_age":
                    # Calculate age from date
                    try:
                        date_val = datetime.fromisoformat(str(item[field]))
                        age_days = (datetime.now() - date_val).days
                        item[f"{field}_age_days"] = age_days
                    except (ValueError, TypeError):
                        pass

        return data

    def _apply_validate(self, data: List[Dict], transform: Dict) -> List[Dict]:
        """Apply validation transformation."""
        schema = transform.get("schema", {})

        if not schema:
            return data

        validated = []

        for item in data:
            valid = True

            for field, rule in schema.items():
                if rule == "required" and field not in item:
                    valid = False
                    break
                elif rule == "number" and field in item:
                    if not isinstance(item[field], (int, float)):
                        valid = False
                        break
                elif rule == "string" and field in item:
                    if not isinstance(item[field], str):
                        valid = False
                        break

            if valid:
                validated.append(item)

        return validated

    def _matches_filters(self, item: Dict, filters: Dict) -> bool:
        """Check if item matches filter criteria."""
        for field, criteria in filters.items():
            if field not in item:
                return False

            if isinstance(criteria, dict):
                # MongoDB-style operators
                for op, value in criteria.items():
                    if op == "$gt" and not item[field] > value:
                        return False
                    elif op == "$lt" and not item[field] < value:
                        return False
                    elif op == "$gte" and not item[field] >= value:
                        return False
                    elif op == "$lte" and not item[field] <= value:
                        return False
                    elif op == "$eq" and item[field] != value:
                        return False
                    elif op == "$ne" and item[field] == value:
                        return False
            elif item[field] != criteria:
                return False

        return True

    def _convert_to_format(self, data: List[Dict], format: str) -> str:
        """Convert data to requested export format."""
        if format == "json":
            return json.dumps(data, indent=2)

        elif format == "csv":
            if not data:
                return ""

            # Get all unique keys
            keys = set()
            for item in data:
                keys.update(item.keys())
            keys = sorted(keys)

            # Create CSV
            lines = [",".join(keys)]
            for item in data:
                values = [str(item.get(k, "")) for k in keys]
                lines.append(",".join(f'"{v}"' for v in values))

            return "\n".join(lines)

        elif format == "excel":
            # Mock Excel format (in production would use openpyxl)
            return f"Excel format (XLSX) with {len(data)} rows"

        elif format == "sql":
            # Generate SQL INSERT statements
            if not data:
                return ""

            keys = sorted(data[0].keys())
            table_name = "scraped_data"

            statements = [f"-- SQL INSERT statements for {table_name}"]
            for item in data:
                values = [f"'{item.get(k, '')}'" for k in keys]
                statements.append(
                    f"INSERT INTO {table_name} ({', '.join(keys)}) "
                    f"VALUES ({', '.join(values)});"
                )

            return "\n".join(statements)

        elif format == "xml":
            # Generate XML
            lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<data>"]

            for item in data:
                lines.append("  <record>")
                for key, value in item.items():
                    lines.append(f"    <{key}>{value}</{key}>")
                lines.append("  </record>")

            lines.append("</data>")
            return "\n".join(lines)

        else:
            return json.dumps(data, indent=2)
