"""
Tests for API Connectors (Pluggable Senses).
- Base interface and factory (no live credentials needed for factory fallback).
- Alpaca/MT5 imports and WSL handling (MT5 must fail gracefully on non-Windows).
"""
import os
import sys

import pytest


def test_base_connector_interface():
    """BaseConnector defines the required abstract methods."""
    from src.connectors.base_connector import BaseConnector

    assert hasattr(BaseConnector, "connect")
    assert hasattr(BaseConnector, "get_ohlcv")
    assert hasattr(BaseConnector, "execute_order")
    assert hasattr(BaseConnector, "get_account_state")


def test_exceptions_exist():
    """Custom connector exceptions are importable."""
    from src.connectors.exceptions import (
        BrokerConnectionError,
        InsufficientLiquidityError,
        AuthenticationError,
        ConnectorError,
    )

    assert issubclass(BrokerConnectionError, ConnectorError)
    assert issubclass(InsufficientLiquidityError, ConnectorError)
    assert issubclass(AuthenticationError, ConnectorError)


def test_factory_unknown_broker_raises():
    """Factory raises BrokerConnectionError for unknown BROKER_TYPE."""
    from src.connectors.connector_factory import get_connector
    from src.connectors.exceptions import BrokerConnectionError

    prev = os.environ.pop("BROKER_TYPE", None)
    try:
        os.environ["BROKER_TYPE"] = "unknown_broker"
        with pytest.raises(BrokerConnectionError, match="Unknown BROKER_TYPE"):
            get_connector()
    finally:
        if prev is not None:
            os.environ["BROKER_TYPE"] = prev
        else:
            os.environ.pop("BROKER_TYPE", None)


def test_factory_mt5_on_linux_raises():
    """On Linux/WSL, requesting MT5 raises BrokerConnectionError with bridge message."""
    from src.connectors.connector_factory import get_connector, _is_wsl_or_linux
    from src.connectors.exceptions import BrokerConnectionError

    if not _is_wsl_or_linux():
        pytest.skip("Only runs on Linux/WSL to verify graceful MT5 failure")

    prev = os.environ.pop("BROKER_TYPE", None)
    try:
        os.environ["BROKER_TYPE"] = "mt5"
        with pytest.raises(BrokerConnectionError, match="WSL|bridge|Windows"):
            get_connector()
    finally:
        if prev is not None:
            os.environ["BROKER_TYPE"] = prev
        else:
            os.environ.pop("BROKER_TYPE", None)


def test_us30_loader_load_from_connector_interface():
    """US30Loader.load_from_connector exists and accepts connector, symbol, timeframe, count."""
    from src.data.us30_loader import US30Loader

    loader = US30Loader()
    assert hasattr(loader, "load_from_connector")
    # Call signature check (would need a mock connector to run fully)
    import inspect
    sig = inspect.signature(loader.load_from_connector)
    params = list(sig.parameters)
    assert "connector" in params
    assert "symbol" in params
    assert "timeframe" in params
    assert "count" in params


def test_us30_loader_load_clean_data_requires_path():
    """US30Loader.load_clean_data() raises when file_path is None."""
    from src.data.us30_loader import US30Loader

    loader = US30Loader(file_path=None)
    with pytest.raises(ValueError, match="file_path is required"):
        loader.load_clean_data()
