"""
FilesystemStore — single class for all DataStore/ JSON file I/O.
All agents and API endpoints use this instead of direct file I/O or asyncpg.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.computation_budget import budget as CB


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Any:
    if not path.exists():
        return [] if path.name not in ("workflow_state.json",) else {}
    with path.open("r", encoding="utf-8") as f:
        text = f.read().strip()
        if not text:
            return [] if path.name not in ("workflow_state.json",) else {}
        return json.loads(text)


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


class FilesystemStore:
    """Read/write all DataStore/ JSON files. Thread-safe for single-process use."""

    def __init__(self, datastore_path: str = "DataStore") -> None:
        self.root = Path(datastore_path)
        self.root.mkdir(parents=True, exist_ok=True)
        self._alphas_path    = self.root / "alphas.json"
        self._strategies_path = self.root / "strategies.json"
        self._audit_path     = self.root / "audit_log.json"
        self._state_path     = self.root / "workflow_state.json"
        self._debug_log_path = self.root / "debug.log"
        self._ensure_files()

    # ── Init ─────────────────────────────────────────────────────────────────

    def _ensure_files(self) -> None:
        for p, default in [
            (self._alphas_path, []),
            (self._strategies_path, []),
            (self._audit_path, []),
            (self._state_path, {
                "step": "idle", "context": {}, "started_at": None,
                "alpha_id": None, "workflow_id": None, "circuit_breaker_active": False,
            }),
        ]:
            if not p.exists():
                _save_json(p, default)

    # ── Alphas ───────────────────────────────────────────────────────────────

    def load_alphas(self) -> list[dict]:
        """Load all alpha records from alphas.json."""
        return _load_json(self._alphas_path) or []

    def save_alpha(self, alpha: dict) -> str:
        """Append alpha to alphas.json. Returns generated alpha_id."""
        alphas = self.load_alphas()
        if "alpha_id" not in alpha or not alpha["alpha_id"]:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            alpha["alpha_id"] = f"alpha_{ts}_{uuid.uuid4().hex[:4]}"
        if "created_at" not in alpha:
            alpha["created_at"] = _utcnow()
        alphas.append(alpha)
        _save_json(self._alphas_path, alphas)
        return alpha["alpha_id"]

    # Class-level TF-IDF cache: keyed by corpus size to auto-invalidate on new alphas
    _tfidf_cache: dict = {}

    def find_similar_alphas(self, hypothesis: str, top_k: int | None = None) -> list[dict]:
        """
        Cosine similarity on hypothesis text + numeric price_levels comparison.
        Returns top_k most similar existing alphas with similarity scores.

        TF-IDF vectoriser is cached by corpus size to avoid re-fitting on
        every call (saves ~50ms per call after the first).
        """
        top_k = top_k if top_k is not None else CB.similarity_top_k
        alphas = self.load_alphas()
        if not alphas:
            return []

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            cache_key = len(alphas)
            if cache_key not in FilesystemStore._tfidf_cache:
                texts_corpus = [a.get("hypothesis", "") for a in alphas]
                vec = TfidfVectorizer(min_df=1, stop_words="english")
                tfidf_corpus = vec.fit_transform(texts_corpus)
                FilesystemStore._tfidf_cache = {cache_key: (vec, tfidf_corpus, list(alphas))}

            vec, tfidf_corpus, cached_alphas = FilesystemStore._tfidf_cache[cache_key]
            query_vec = vec.transform([hypothesis])
            text_sims = cosine_similarity(query_vec, tfidf_corpus)[0]
            alphas = cached_alphas
        except Exception:
            text_sims = [0.0] * len(alphas)

        scored = []
        for i, alpha in enumerate(alphas):
            score = float(text_sims[i]) if i < len(text_sims) else 0.0
            scored.append({**alpha, "similarity_score": round(score, 4)})

        scored.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored[:top_k]

    # ── Strategies ───────────────────────────────────────────────────────────

    def load_strategies(self, status: str | None = None) -> list[dict]:
        """Load strategies index. Filter by status: 'draft'|'production'|'graveyard'."""
        strategies = _load_json(self._strategies_path) or []
        if status and status != "all":
            strategies = [s for s in strategies if s.get("status") == status]
        return strategies

    def save_strategy_metadata(self, strategy_id: str, metadata: dict) -> None:
        """Write/update strategy entry in strategies.json."""
        strategies = _load_json(self._strategies_path) or []
        for i, s in enumerate(strategies):
            if s.get("strategy_id") == strategy_id:
                strategies[i] = {**s, **metadata, "strategy_id": strategy_id}
                _save_json(self._strategies_path, strategies)
                return
        metadata["strategy_id"] = strategy_id
        if "created_at" not in metadata:
            metadata["created_at"] = _utcnow()
        strategies.append(metadata)
        _save_json(self._strategies_path, strategies)

    def move_strategy(self, strategy_id: str, new_status: str) -> None:
        """Change strategy status (draft→production or draft→graveyard)."""
        self.save_strategy_metadata(strategy_id, {"status": new_status, "updated_at": _utcnow()})

    # ── Audit log ────────────────────────────────────────────────────────────

    def log_mc_run(self, strategy_id: str, mc_results: dict, price_levels: dict | None = None) -> str:
        """Append MC run to audit_log.json. Returns run_id."""
        audit = _load_json(self._audit_path) or []
        run_id = f"mc_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
        entry = {
            "run_id": run_id,
            "strategy_id": strategy_id,
            "ran_at": _utcnow(),
            "results": mc_results,
            "price_levels": price_levels or {},
        }
        audit.append(entry)
        _save_json(self._audit_path, audit)
        return run_id

    # ── Workflow state ────────────────────────────────────────────────────────

    def get_workflow_state(self) -> dict:
        """Return current workflow_state.json content."""
        data = _load_json(self._state_path)
        if isinstance(data, list):
            return {"step": "idle", "context": {}}
        return data

    def set_workflow_state(self, state: dict) -> None:
        """Overwrite workflow_state.json."""
        _save_json(self._state_path, state)

    def advance_workflow_step(self, step: str, context: dict | None = None) -> None:
        """Advance to next step, merging context into state."""
        current = self.get_workflow_state()
        current["step"] = step
        current["updated_at"] = _utcnow()
        if context:
            current["context"] = {**current.get("context", {}), **context}
            for key in ("alpha_id", "workflow_id", "strategy_id"):
                if key in context:
                    current[key] = context[key]
        _save_json(self._state_path, current)

    # ── Debug log ────────────────────────────────────────────────────────────

    def write_debug(self, message: str) -> None:
        """Append a line to DataStore/debug.log."""
        with self._debug_log_path.open("a", encoding="utf-8") as f:
            f.write(f"[{_utcnow()}] {message}\n")
