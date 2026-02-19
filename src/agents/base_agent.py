import logging
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"Agent.{name}")
        self.logger.setLevel(logging.INFO)

    @abstractmethod
    async def perceive(self, input_data: Any) -> Any:
        """Observe data from the environment (e.g., read a file or API)."""
        pass

    @abstractmethod
    async def reason(self, state: Any) -> Dict[str, Any]:
        """Process observations and determine the next action."""
        pass

    @abstractmethod
    async def act(self, plan: Dict[str, Any]) -> bool:
        """Execute the chosen action (e.g., write a file or trade)."""
        pass

    def log_action(self, action_name: str, status: str):
        self.logger.info(f"Action: {action_name} | Status: {status}")
