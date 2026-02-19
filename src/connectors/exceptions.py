"""
Custom exceptions for connector layer.
Used for BrokerConnectionError, InsufficientLiquidityError, AuthenticationError.
"""


class ConnectorError(Exception):
    """Base exception for all connector-related errors."""

    pass


class BrokerConnectionError(ConnectorError):
    """Raised when connection to the broker (MT5 terminal or Alpaca) fails."""

    pass


class InsufficientLiquidityError(ConnectorError):
    """Raised when order is rejected due to risk/position size limits or insufficient buying power."""

    pass


class AuthenticationError(ConnectorError):
    """Raised when API credentials are invalid or expired."""

    pass
