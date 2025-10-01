"""
Monetization Tools Base Class

Provides shared functionality for all monetization tools including:
- Rate limiting
- Caching
- Database operations
- Error handling
- Logging
- Common utilities
"""

import asyncio
import hashlib
import json
import re
from abc import abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import Field, PrivateAttr

from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.crawl4ai import Crawl4aiTool
from app.tool.create_chat_completion import CreateChatCompletion
from app.tool.sql_manager import get_connection
from app.tool.web_search import WebSearch


class RateLimitConfig:
    """Rate limit configuration for external APIs."""

    LIMITS = {
        # Marketplace platforms
        "amazon": {"requests_per_minute": 60, "requests_per_hour": 3000},
        "ebay": {"requests_per_minute": 100, "requests_per_hour": 5000},
        "aliexpress": {"requests_per_minute": 30, "requests_per_hour": 1000},
        "walmart": {"requests_per_minute": 50, "requests_per_hour": 2000},
        # Freelance platforms
        "upwork": {"requests_per_minute": 20, "requests_per_hour": 500},
        "fiverr": {"requests_per_minute": 30, "requests_per_hour": 800},
        # Lead/data sources
        "linkedin": {"requests_per_minute": 10, "requests_per_hour": 200},
        "hunter_io": {"requests_per_minute": 30, "requests_per_hour": 1000},
        "clearbit": {"requests_per_minute": 50, "requests_per_hour": 2000},
        # Domain services
        "whois": {"requests_per_minute": 60, "requests_per_hour": 3000},
        "moz": {"requests_per_minute": 10, "requests_per_hour": 200},
        # Default for unknown services
        "default": {"requests_per_minute": 30, "requests_per_hour": 1000},
    }


class CacheConfig:
    """Cache TTL configuration in seconds."""

    TTL = {
        "product_price": 3600,  # 1 hour
        "lead_data": 86400,  # 24 hours
        "domain_metrics": 43200,  # 12 hours
        "company_info": 86400,  # 24 hours
        "project_listing": 1800,  # 30 minutes
        "api_response": 300,  # 5 minutes
        "default": 3600,  # 1 hour
    }


class MonetizationError(Exception):
    """Base exception for monetization tools."""

    pass


class RateLimitError(MonetizationError):
    """Rate limit exceeded."""

    pass


class ValidationError(MonetizationError):
    """Input validation failed."""

    pass


class ExternalAPIError(MonetizationError):
    """External API call failed."""

    pass


class MonetizationBase(BaseTool):
    """
    Base class for all monetization tools.

    Provides:
    - Rate limiting across external APIs
    - Multi-layer caching
    - Database operations
    - Error handling with retries
    - Logging and metrics
    - Input validation
    - ROI calculations

    Attributes:
        browser_tool: Browser automation tool instance
        search_tool: Web search tool instance
        crawl_tool: Web crawling tool instance
        chat_tool: AI chat completion tool instance
        sql_manager: SQL database manager
        connection_id: Database connection identifier
    """

    # Shared tool instances (lazy-loaded)
    browser_tool: Optional[BrowserUseTool] = Field(default=None)
    search_tool: Optional[WebSearch] = Field(default=None)
    crawl_tool: Optional[Crawl4aiTool] = Field(default=None)
    chat_tool: Optional[CreateChatCompletion] = Field(default=None)

    # SQL connection
    connection_id: Optional[str] = Field(default=None)

    # Rate limiting state (in-memory, per instance)
    _rate_limit_state: Dict[str, List[float]] = PrivateAttr(default_factory=dict)

    # Cache state (in-memory, per instance)
    _cache: Dict[str, tuple] = PrivateAttr(
        default_factory=dict
    )  # key -> (value, expiry)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        """Initialize with lazy-loaded tools."""
        super().__init__(**data)
        # Tools will be initialized on first use

    # ==================== Tool Initialization ====================

    def _get_browser_tool(self) -> BrowserUseTool:
        """Lazy-load browser tool."""
        if self.browser_tool is None:
            self.browser_tool = BrowserUseTool()
        return self.browser_tool

    def _get_search_tool(self) -> WebSearch:
        """Lazy-load search tool."""
        if self.search_tool is None:
            self.search_tool = WebSearch()
        return self.search_tool

    def _get_crawl_tool(self) -> Crawl4aiTool:
        """Lazy-load crawl tool."""
        if self.crawl_tool is None:
            self.crawl_tool = Crawl4aiTool()
        return self.crawl_tool

    def _get_chat_tool(self) -> CreateChatCompletion:
        """Lazy-load chat completion tool."""
        if self.chat_tool is None:
            self.chat_tool = CreateChatCompletion()
        return self.chat_tool

    # ==================== Rate Limiting ====================

    async def check_rate_limit(self, resource: str) -> bool:
        """
        Check if request is within rate limits.

        Args:
            resource: Resource name (e.g., 'amazon', 'linkedin')

        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.now().timestamp()
        limits = RateLimitConfig.LIMITS.get(resource, RateLimitConfig.LIMITS["default"])

        # Initialize state if needed
        if resource not in self._rate_limit_state:
            self._rate_limit_state[resource] = []

        # Clean old timestamps
        minute_ago = now - 60
        hour_ago = now - 3600
        self._rate_limit_state[resource] = [
            ts for ts in self._rate_limit_state[resource] if ts > hour_ago
        ]

        # Check limits
        recent_minute = [
            ts for ts in self._rate_limit_state[resource] if ts > minute_ago
        ]
        recent_hour = self._rate_limit_state[resource]

        if len(recent_minute) >= limits["requests_per_minute"]:
            logger.warning(
                f"[{self.name}] Rate limit reached for {resource}: "
                f"{len(recent_minute)}/min"
            )
            return False

        if len(recent_hour) >= limits["requests_per_hour"]:
            logger.warning(
                f"[{self.name}] Rate limit reached for {resource}: "
                f"{len(recent_hour)}/hour"
            )
            return False

        return True

    async def wait_for_rate_limit(self, resource: str, max_wait: int = 60):
        """
        Wait until rate limit allows the request.

        Args:
            resource: Resource name
            max_wait: Maximum seconds to wait

        Raises:
            RateLimitError: If max_wait exceeded
        """
        start_time = datetime.now()
        while not await self.check_rate_limit(resource):
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > max_wait:
                raise RateLimitError(
                    f"Rate limit for {resource} exceeded, max wait time {max_wait}s reached"
                )
            await asyncio.sleep(1)

    def record_request(self, resource: str):
        """Record a request for rate limiting."""
        now = datetime.now().timestamp()
        if resource not in self._rate_limit_state:
            self._rate_limit_state[resource] = []
        self._rate_limit_state[resource].append(now)

    # ==================== Caching ====================

    def _cache_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from parameters."""
        key_data = json.dumps(kwargs, sort_keys=True)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    async def cache_get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/missing
        """
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now().timestamp() < expiry:
                logger.debug(f"[{self.name}] Cache hit: {key}")
                return value
            else:
                # Clean expired entry
                del self._cache[key]
                logger.debug(f"[{self.name}] Cache expired: {key}")
        return None

    async def cache_set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None for default)
        """
        if ttl is None:
            ttl = CacheConfig.TTL["default"]

        expiry = datetime.now().timestamp() + ttl
        self._cache[key] = (value, expiry)
        logger.debug(f"[{self.name}] Cached: {key} (TTL: {ttl}s)")

    async def cache_invalidate(self, key: str):
        """Invalidate cache entry."""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"[{self.name}] Cache invalidated: {key}")

    # ==================== Database Operations ====================

    async def db_execute(self, query: str, params: Optional[dict] = None) -> Any:
        """
        Execute database query.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Query result
        """
        if not self.connection_id:
            raise MonetizationError("Database connection not initialized")

        try:
            engine = get_connection(self.connection_id)
            with engine.connect() as conn:
                from sqlalchemy import text

                result = conn.execute(text(query), params or {})
                conn.commit()
                return result
        except Exception as e:
            logger.error(f"[{self.name}] Database error: {e}", exc_info=True)
            raise MonetizationError(f"Database operation failed: {e}")

    async def db_fetch_one(
        self, query: str, params: Optional[dict] = None
    ) -> Optional[dict]:
        """Fetch single row from database."""
        result = await self.db_execute(query, params)
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def db_fetch_all(
        self, query: str, params: Optional[dict] = None
    ) -> List[dict]:
        """Fetch all rows from database."""
        result = await self.db_execute(query, params)
        return [dict(row._mapping) for row in result.fetchall()]

    # ==================== Validation ====================

    def validate_required_params(self, params: dict, required: List[str]):
        """
        Validate required parameters are present.

        Args:
            params: Parameter dictionary
            required: List of required parameter names

        Raises:
            ValidationError: If required parameter missing
        """
        missing = [r for r in required if r not in params or params[r] is None]
        if missing:
            raise ValidationError(f"Missing required parameters: {', '.join(missing)}")

    def validate_url(self, url: str) -> bool:
        """Validate URL format."""
        pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
            r"localhost|"  # localhost
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )
        return bool(pattern.match(url))

    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        return bool(pattern.match(email))

    # ==================== ROI Calculation ====================

    def calculate_roi(
        self, revenue: float, costs: float, initial_investment: float = 0
    ) -> Dict[str, Any]:
        """
        Calculate return on investment metrics.

        Args:
            revenue: Total revenue
            costs: Operating costs
            initial_investment: Initial investment

        Returns:
            Dictionary with ROI metrics
        """
        total_investment = initial_investment + costs
        profit = revenue - costs
        net_profit = revenue - total_investment

        roi = (net_profit / total_investment * 100) if total_investment > 0 else 0
        profit_margin = (profit / revenue * 100) if revenue > 0 else 0

        return {
            "revenue": round(revenue, 2),
            "costs": round(costs, 2),
            "profit": round(profit, 2),
            "net_profit": round(net_profit, 2),
            "roi_percentage": round(roi, 2),
            "profit_margin": round(profit_margin, 2),
            "breakeven": total_investment > 0 and net_profit >= 0,
        }

    # ==================== Logging Helpers ====================

    def log_action(self, action: str, **kwargs):
        """Log tool action with structured data."""
        logger.info(f"[{self.name}] {action}", extra={"data": kwargs})

    def log_error(self, error: str, **kwargs):
        """Log error with context."""
        logger.error(f"[{self.name}] {error}", extra={"data": kwargs}, exc_info=True)

    def log_metric(self, metric_name: str, value: Any):
        """Log performance metric."""
        logger.info(f"[{self.name}] Metric: {metric_name}={value}")

    # ==================== Abstract Methods ====================

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters. Must be implemented by subclasses."""
        pass
