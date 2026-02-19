"""
Broker adapter: abstract interface for OANDA / MetaTrader 5 / IBKR.
Human-in-the-Loop: live orders are allowed only if strategy/signal is in AI_Employee_Vault/Approved/.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class OrderRequest:
    """Generic order request (symbol, side, size, order_type, sl, tp, etc.)."""
    symbol: str
    side: str  # "buy" | "sell"
    size: float
    order_type: str = "market"  # "market" | "limit" | "stop"
    limit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_id: Optional[str] = None  # required for live: must be in Approved/


@dataclass
class OrderResult:
    """Result of order submission."""
    success: bool
    order_id: Optional[str] = None
    message: Optional[str] = None
    filled_price: Optional[float] = None


class HumanInTheLoopEnforcer:
    """
    Code must strictly check AI_Employee_Vault/Approved/ before sending any live order.
    Approved/ can contain:
    - strategy_<id>.approved marker files, or
    - an Approved_Strategies.md listing allowed strategy IDs.
    """

    def __init__(self, vault_path: str):
        self.approved_dir = Path(vault_path) / "Approved"

    def is_approved(self, strategy_id: str) -> bool:
        """
        Returns True only if strategy_id is explicitly approved for live trading.
        Checks: Approved/<strategy_id>.approved, Approved/<strategy_id>.md, or Approved/Approved_Strategies.md.
        """
        if not strategy_id or not self.approved_dir.exists():
            return False
        # Marker file
        if (self.approved_dir / f"{strategy_id}.approved").exists():
            return True
        if (self.approved_dir / f"{strategy_id}.md").exists():
            return True
        # List file
        list_file = self.approved_dir / "Approved_Strategies.md"
        if list_file.exists():
            try:
                text = list_file.read_text(encoding="utf-8")
                return strategy_id in text and f"{strategy_id}" in text
            except Exception:
                return False
        return False

    def assert_approved(self, strategy_id: str) -> None:
        """Raises PermissionError if strategy_id is not approved. Call before sending live order."""
        if not self.is_approved(strategy_id):
            raise PermissionError(
                f"Live order rejected: strategy '{strategy_id}' is not in {self.approved_dir}. "
                "Add strategy to Approved/ before sending live orders."
            )


class BaseBrokerAdapter(ABC):
    """
    Abstract broker connector. Implementations: OANDA, MetaTrader 5, IBKR.
    All live orders must go through HumanInTheLoopEnforcer.
    """

    def __init__(self, vault_path: str, live: bool = False):
        self.vault_path = vault_path
        self.live = live
        self.enforcer = HumanInTheLoopEnforcer(vault_path)

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to broker. Returns True on success."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection."""
        pass

    @abstractmethod
    def place_order(self, request: OrderRequest) -> OrderResult:
        """
        Submit order. If live=True, enforcer.assert_approved(request.strategy_id) must be called first.
        """
        pass

    def place_order_live(self, request: OrderRequest) -> OrderResult:
        """Place order only if live and strategy is approved. Otherwise returns failure."""
        if not self.live:
            return OrderResult(success=False, message="Adapter not in live mode.")
        if not request.strategy_id:
            return OrderResult(success=False, message="strategy_id required for live orders.")
        self.enforcer.assert_approved(request.strategy_id)
        return self.place_order(request)


# --- Stub implementations (Phase 4: real API connectors) ---

class OANDAAdapter(BaseBrokerAdapter):
    """OANDA connector. Stub: implement with oandapy-v20 or similar."""

    def connect(self) -> bool:
        # TODO: OANDA API connection
        return True

    def disconnect(self) -> None:
        pass

    def place_order(self, request: OrderRequest) -> OrderResult:
        if self.live:
            self.enforcer.assert_approved(request.strategy_id or "")
        # Stub: no real order
        return OrderResult(success=True, order_id="OANDA-stub", message="Stub: no real order sent.")


class MT5Adapter(BaseBrokerAdapter):
    """MetaTrader 5 connector. Stub: implement with MetaTrader5 package."""

    def connect(self) -> bool:
        # TODO: MT5 connection
        return True

    def disconnect(self) -> None:
        pass

    def place_order(self, request: OrderRequest) -> OrderResult:
        if self.live:
            self.enforcer.assert_approved(request.strategy_id or "")
        return OrderResult(success=True, order_id="MT5-stub", message="Stub: no real order sent.")


class IBKRAdapter(BaseBrokerAdapter):
    """Interactive Brokers connector. Stub: implement with ib_insync or official API."""

    def connect(self) -> bool:
        # TODO: IBKR connection
        return True

    def disconnect(self) -> None:
        pass

    def place_order(self, request: OrderRequest) -> OrderResult:
        if self.live:
            self.enforcer.assert_approved(request.strategy_id or "")
        return OrderResult(success=True, order_id="IBKR-stub", message="Stub: no real order sent.")
