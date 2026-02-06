"""Tests for NBA API retry wrapper."""

from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError, ReadTimeout

from src.nba_config import nba_api_call


class FakeEndpoint:
    """Mock NBA API endpoint class."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get_data_frames(self):
        return [MagicMock()]


class FakeEndpointTimeout(FakeEndpoint):
    """Endpoint that raises ReadTimeout on first N calls, then succeeds."""

    call_count = 0
    fail_count = 1

    def __init__(self, **kwargs):
        FakeEndpointTimeout.call_count += 1
        if FakeEndpointTimeout.call_count <= FakeEndpointTimeout.fail_count:
            raise ReadTimeout("Connection timed out")
        super().__init__(**kwargs)


class FakeEndpointAlwaysFails:
    """Endpoint that always raises ReadTimeout."""

    def __init__(self, **kwargs):
        raise ReadTimeout("Connection timed out")


class FakeEndpointConnectionError:
    """Endpoint that always raises ConnectionError."""

    def __init__(self, **kwargs):
        raise ConnectionError("Connection refused")


@patch("src.nba_config.NBA_RATE_LIMIT_SLEEP", 0)
@patch("src.nba_config.rate_limit")
class TestNbaApiCall:
    """Tests for nba_api_call wrapper."""

    def test_successful_call(self, mock_rate_limit):
        result = nba_api_call(FakeEndpoint, critical=True, game_date="01/01/2025")

        assert result is not None
        assert isinstance(result, FakeEndpoint)
        assert result.kwargs["game_date"] == "01/01/2025"
        mock_rate_limit.assert_called_once()

    def test_timeout_injected(self, mock_rate_limit):
        result = nba_api_call(FakeEndpoint, critical=True, season="2024-25")

        assert result.kwargs["timeout"] == 60

    @patch("src.nba_config.NBA_TIMEOUT", 120)
    def test_custom_timeout(self, mock_rate_limit):
        result = nba_api_call(FakeEndpoint, critical=True)

        assert result.kwargs["timeout"] == 120

    def test_timeout_not_overridden(self, mock_rate_limit):
        result = nba_api_call(FakeEndpoint, critical=True, timeout=30)

        assert result.kwargs["timeout"] == 30

    @patch("src.nba_config.NBA_PROXY", "http://proxy:8080")
    def test_proxy_injected(self, mock_rate_limit):
        result = nba_api_call(FakeEndpoint, critical=True)

        assert result.kwargs["proxy"] == "http://proxy:8080"

    @patch("src.nba_config.NBA_PROXY", None)
    def test_no_proxy_when_not_set(self, mock_rate_limit):
        result = nba_api_call(FakeEndpoint, critical=True)

        assert "proxy" not in result.kwargs

    @patch("src.nba_config.NBA_MAX_RETRIES", 3)
    def test_retry_on_timeout_then_succeed(self, mock_rate_limit):
        FakeEndpointTimeout.call_count = 0
        FakeEndpointTimeout.fail_count = 1

        result = nba_api_call(FakeEndpointTimeout, critical=True)

        assert result is not None
        assert FakeEndpointTimeout.call_count == 2

    @patch("src.nba_config.NBA_MAX_RETRIES", 3)
    def test_critical_raises_after_retries_exhausted(self, mock_rate_limit):
        with pytest.raises(ReadTimeout):
            nba_api_call(FakeEndpointAlwaysFails, critical=True)

    @patch("src.nba_config.NBA_MAX_RETRIES", 3)
    def test_non_critical_returns_none_after_retries_exhausted(self, mock_rate_limit):
        result = nba_api_call(FakeEndpointAlwaysFails, critical=False)

        assert result is None

    @patch("src.nba_config.NBA_MAX_RETRIES", 3)
    def test_non_critical_connection_error_returns_none(self, mock_rate_limit):
        result = nba_api_call(FakeEndpointConnectionError, critical=False)

        assert result is None

    @patch("src.nba_config.NBA_MAX_RETRIES", 2)
    def test_retry_on_timeout_then_succeed_with_two_retries(self, mock_rate_limit):
        FakeEndpointTimeout.call_count = 0
        FakeEndpointTimeout.fail_count = 1

        result = nba_api_call(FakeEndpointTimeout, critical=True)

        assert result is not None

    def test_non_retryable_exception_propagates(self, mock_rate_limit):
        class BadEndpoint:
            def __init__(self, **kwargs):
                raise ValueError("bad argument")

        with pytest.raises(ValueError, match="bad argument"):
            nba_api_call(BadEndpoint, critical=True)

    def test_non_retryable_exception_propagates_non_critical(self, mock_rate_limit):
        class BadEndpoint:
            def __init__(self, **kwargs):
                raise ValueError("bad argument")

        with pytest.raises(ValueError, match="bad argument"):
            nba_api_call(BadEndpoint, critical=False)
