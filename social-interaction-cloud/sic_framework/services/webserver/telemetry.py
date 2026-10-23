"""
telemetry.py - MLOps & LLMOps Telemetry Tracker for Conversational Agents.

Provides structured logging and operational metrics for Google Cloud Monitoring:
- Per-stage latency tracking (STT, NLU, DialogManager, Speech Synthesis)
- NLU engine tracking (BERT ONNX, INT8, Claude Haiku, keyword fallback)
- Real-time Fallback Rate calculation (drift & coverage monitoring)
- Cache hit / miss rates for YouTube API and prompts
"""

import json
import logging
import threading
from typing import Dict, Any, Optional
from collections import Counter

logger = logging.getLogger("Telemetry")

# Engine labels emitted by webserver_pca.py as f"bert_{FastBERTNLU.backend}".
# FastBERTNLU.backend is one of: "onnx_int8", "onnx", "pytorch".
LOCAL_BERT_ENGINES = frozenset({"bert_onnx_int8", "bert_int8", "bert_onnx", "bert_pytorch"})


def is_local_bert_engine(engine: str) -> bool:
    """True when the NLU engine is the Tier-1 local BERT model (not an LLM / rule fallback)."""
    return engine in LOCAL_BERT_ENGINES or engine.startswith("bert_")


class PipelineTelemetry:
    """Singleton operational metrics tracker and Cloud Logging emitter."""

    def __init__(self):
        self.total_requests = 0
        self.nlu_engine_counts = Counter()
        self.youtube_cache_hits = 0
        self.youtube_cache_misses = 0
        self.llm_errors = 0
        self.recent_latencies = []
        self._max_recent = 100
        self._lock = threading.Lock()

    def record_youtube_cache(self, hit: bool):
        with self._lock:
            if hit:
                self.youtube_cache_hits += 1
            else:
                self.youtube_cache_misses += 1

    def record_llm_error(self):
        with self._lock:
            self.llm_errors += 1

    def _fallback_rate_unlocked(self) -> float:
        if self.total_requests == 0:
            return 0.0
        local_hits = sum(
            count for engine, count in self.nlu_engine_counts.items() if is_local_bert_engine(engine)
        )
        fallback_turns = self.total_requests - local_hits
        return round((fallback_turns / self.total_requests) * 100.0, 2)

    def get_fallback_rate(self) -> float:
        """Percentage of queries where BERT failed to classify and fell back to LLM or rules."""
        with self._lock:
            return self._fallback_rate_unlocked()

    def log_turn(
        self,
        transcript: str,
        intent: str,
        engine: str,
        stt_ms: float = 0.0,
        nlu_ms: float = 0.0,
        dialog_ms: float = 0.0,
        total_ms: float = 0.0,
        slots: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
    ):
        with self._lock:
            self.total_requests += 1
            self.nlu_engine_counts[engine] += 1
            self.recent_latencies.append(total_ms)
            if len(self.recent_latencies) > self._max_recent:
                self.recent_latencies.pop(0)
            fallback_rate = self._fallback_rate_unlocked()
            total_turns = self.total_requests
            engine_distribution = dict(self.nlu_engine_counts)

        payload = {
            "component": "conversational_pipeline",
            "event": "turn_completed",
            "transcript_snippet": transcript[:40] if transcript else "",
            "intent": intent,
            "engine": engine,
            "confidence": round(confidence, 3),
            "slots_count": len(slots or {}),
            "latencies_ms": {
                "stt": round(stt_ms, 1),
                "nlu": round(nlu_ms, 1),
                "dialog": round(dialog_ms, 1),
                "total": round(total_ms, 1),
            },
            "metrics_snapshot": {
                "total_turns": total_turns,
                "fallback_rate_pct": fallback_rate,
                "engine_distribution": engine_distribution,
            },
        }

        # Emits single-line JSON log for Cloud Run -> Google Cloud Logging metrics parsing
        logger.info(f"TELEMETRY_LOG {json.dumps(payload)}")

    def get_health_metrics(self) -> Dict[str, Any]:
        """Summary dictionary exposed via /api/metrics for Cloud Monitoring and health checks."""
        with self._lock:
            avg_latency = (
                round(sum(self.recent_latencies) / len(self.recent_latencies), 1)
                if self.recent_latencies
                else 0.0
            )
            return {
                "status": "healthy",
                "total_turns": self.total_requests,
                "fallback_rate_pct": self._fallback_rate_unlocked(),
                "avg_latency_ms": avg_latency,
                "nlu_engine_counts": dict(self.nlu_engine_counts),
                "youtube_cache": {
                    "hits": self.youtube_cache_hits,
                    "misses": self.youtube_cache_misses,
                    "hit_ratio_pct": round(
                        (self.youtube_cache_hits / max(1, self.youtube_cache_hits + self.youtube_cache_misses)) * 100, 1
                    ),
                },
                "llm_errors": self.llm_errors,
            }


# Global singleton instance
telemetry = PipelineTelemetry()
