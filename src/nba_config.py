"""Centralized NBA API configuration and retry wrapper."""

import logging
import os
import time

from requests.exceptions import ConnectionError, ReadTimeout
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Configuration from environment
NBA_TIMEOUT = int(os.environ.get("NBA_TIMEOUT", "60"))
NBA_PROXY = os.environ.get("NBA_PROXY") or None
NBA_MAX_RETRIES = int(os.environ.get("NBA_MAX_RETRIES", "3"))
NBA_RATE_LIMIT_SLEEP = float(os.environ.get("NBA_RATE_LIMIT_SLEEP", "1.0"))

# Exceptions worth retrying
RETRYABLE_EXCEPTIONS = (ReadTimeout, ConnectionError, TimeoutError)


def rate_limit():
    """Sleep between NBA API calls to avoid rate limiting."""
    time.sleep(NBA_RATE_LIMIT_SLEEP)


def nba_api_call(endpoint_class, critical=True, **kwargs):
    """
    Call an NBA API endpoint with retry logic, timeout, and optional proxy.

    Args:
        endpoint_class: The nba_api endpoint class (e.g., ScoreboardV2)
        critical: If True, raise after all retries exhausted.
                  If False, return None after all retries exhausted.
        **kwargs: Arguments passed to the endpoint constructor.

    Returns:
        The endpoint instance on success, or None if non-critical and all retries failed.

    Raises:
        Exception: If critical=True and all retries are exhausted.
    """
    rate_limit()

    kwargs.setdefault("timeout", NBA_TIMEOUT)
    if NBA_PROXY:
        kwargs.setdefault("proxy", NBA_PROXY)

    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        stop=stop_after_attempt(NBA_MAX_RETRIES),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _call():
        return endpoint_class(**kwargs)

    try:
        return _call()
    except RETRYABLE_EXCEPTIONS as e:
        if critical:
            raise
        logger.warning(
            "All %d retries exhausted for %s: %s",
            NBA_MAX_RETRIES,
            endpoint_class.__name__,
            e,
        )
        return None
