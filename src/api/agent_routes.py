"""
Agent Routes — FastAPI router for the Autonomous AI Agent endpoints.

POST /agent/chat          — process a chat message (both modes)
GET  /agent/context       — return current system context snapshot
"""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["Autonomous Agent"])


# ── Pydantic models ────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    mode: str = "chat"   # "chat" | "agent"


class ChatResponse(BaseModel):
    response: str
    mode: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/agent/chat", response_model=ChatResponse)
async def agent_chat(req: ChatRequest) -> ChatResponse:
    """
    Process a user message via the Autonomous Agent.

    - mode="chat"  : read-only, safe for all users
    - mode="agent" : can execute real system actions (HITL safeguards apply)
    """
    from src.agents.autonomous_agent import process_message

    if req.mode not in ("chat", "agent"):
        raise HTTPException(status_code=400, detail="mode must be 'chat' or 'agent'")

    api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")

    history = [{"role": m.role, "content": m.content} for m in req.history]

    response = await process_message(
        message=req.message,
        history=history,
        mode=req.mode,
        api_base_url=api_base_url,
    )

    return ChatResponse(response=response, mode=req.mode)


@router.get("/agent/context")
async def get_agent_context() -> dict:
    """Return the current system context snapshot used by the agent."""
    from src.agents.autonomous_agent import _build_system_context, _context_to_text

    ctx = _build_system_context()
    return {
        "context_text": _context_to_text(ctx),
        "raw": {
            "timestamp": ctx["timestamp"],
            "strategy_count": len(ctx.get("strategies", [])),
            "alpha_count": len(ctx.get("alphas", [])),
            "workflow_state": ctx.get("workflow_state", {}),
            "vault_summary": {k: len(v) for k, v in ctx.get("vault_summary", {}).items()},
            "has_price_levels": bool(ctx.get("price_levels")),
        },
    }
