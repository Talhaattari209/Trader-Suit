"""
Gateway: lightweight approval and control-plane helpers (OpenClaw-style, simplified).
"""
from .approval import can_approve_strategy, can_execute_order

__all__ = ["can_approve_strategy", "can_execute_order"]
