"""Prometheus-compatible metrics collectors for NIEL Industrial AI."""

from collections import defaultdict
import threading
import time
from typing import Dict, List, Tuple


class MetricsCollector:
    """Thread-safe in-memory metrics registry formatted for Prometheus scraping."""

    def __init__(self):
        self._lock = threading.Lock()

        # Counters: key -> int/float
        self._http_requests_total: Dict[Tuple[str, str, int], int] = defaultdict(int)
        self._security_blocks_total: Dict[str, int] = defaultdict(int)
        self._token_usage_total: Dict[str, int] = defaultdict(int)
        self._human_escalations_total: int = 0
        self._rag_abstentions_total: int = 0
        self._estimated_cost_usd_total: float = 0.0

        # Histograms / Summaries: key -> List[float]
        self._http_request_durations: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        self._rag_retrieval_durations: List[float] = []
        self._llm_response_durations: List[float] = []
        self._agent_tool_durations: Dict[str, List[float]] = defaultdict(list)

    def record_http_request(self, method: str, path: str, status_code: int, duration_sec: float):
        with self._lock:
            # Group paths to avoid cardinality explosion (e.g. /customers/{id} -> /customers/id)
            norm_path = path.split("?")[0]
            self._http_requests_total[(method, norm_path, status_code)] += 1
            dur_list = self._http_request_durations[(method, norm_path)]
            dur_list.append(duration_sec)
            if len(dur_list) > 1000:
                self._http_request_durations[(method, norm_path)] = dur_list[-1000:]

    def record_rag_retrieval(self, duration_sec: float):
        with self._lock:
            self._rag_retrieval_durations.append(duration_sec)
            if len(self._rag_retrieval_durations) > 1000:
                self._rag_retrieval_durations = self._rag_retrieval_durations[-1000:]

    def record_llm_response(self, duration_sec: float):
        with self._lock:
            self._llm_response_durations.append(duration_sec)
            if len(self._llm_response_durations) > 1000:
                self._llm_response_durations = self._llm_response_durations[-1000:]

    def record_tool_execution(self, tool_name: str, duration_sec: float):
        with self._lock:
            dur_list = self._agent_tool_durations[tool_name]
            dur_list.append(duration_sec)
            if len(dur_list) > 1000:
                self._agent_tool_durations[tool_name] = dur_list[-1000:]

    def record_tokens(self, prompt_tokens: int, completion_tokens: int, cost_usd: float = 0.0):
        with self._lock:
            self._token_usage_total["prompt"] += prompt_tokens
            self._token_usage_total["completion"] += completion_tokens
            self._estimated_cost_usd_total += cost_usd

    def increment_human_escalation(self):
        with self._lock:
            self._human_escalations_total += 1

    def increment_rag_abstention(self):
        with self._lock:
            self._rag_abstentions_total += 1

    def record_security_block(self, reason: str):
        with self._lock:
            self._security_blocks_total[reason] += 1

    def render_prometheus_text(self) -> str:
        """Render all recorded metrics into official Prometheus exposition format."""
        with self._lock:
            lines: List[str] = [
                "# HELP niel_http_requests_total Total number of HTTP requests received.",
                "# TYPE niel_http_requests_total counter",
            ]
            for (method, path, status), count in sorted(self._http_requests_total.items()):
                lines.append(f'niel_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}')

            lines.extend([
                "\n# HELP niel_human_escalations_total Total count of customer handoffs to human engineering/sales.",
                "# TYPE niel_human_escalations_total counter",
                f"niel_human_escalations_total {self._human_escalations_total}",
                "\n# HELP niel_rag_abstentions_total Total count of queries where RAG refrained from unverified claims.",
                "# TYPE niel_rag_abstentions_total counter",
                f"niel_rag_abstentions_total {self._rag_abstentions_total}",
                "\n# HELP niel_security_blocked_attempts_total Total prompt injection or unauthorized attempts blocked.",
                "# TYPE niel_security_blocked_attempts_total counter",
            ])
            for reason, count in sorted(self._security_blocks_total.items()):
                lines.append(f'niel_security_blocked_attempts_total{{reason="{reason}"}} {count}')

            lines.extend([
                "\n# HELP niel_token_usage_total Total tokens consumed.",
                "# TYPE niel_token_usage_total counter",
            ])
            for token_type, count in sorted(self._token_usage_total.items()):
                lines.append(f'niel_token_usage_total{{type="{token_type}"}} {count}')

            lines.extend([
                "\n# HELP niel_estimated_api_cost_usd_total Estimated API usage cost in USD.",
                "# TYPE niel_estimated_api_cost_usd_total counter",
                f"niel_estimated_api_cost_usd_total {round(self._estimated_cost_usd_total, 6)}",
            ])

            # RAG retrieval summary
            if self._rag_retrieval_durations:
                cnt = len(self._rag_retrieval_durations)
                tot = sum(self._rag_retrieval_durations)
                lines.extend([
                    "\n# HELP niel_rag_retrieval_duration_seconds RAG vector retrieval latency summary.",
                    "# TYPE niel_rag_retrieval_duration_seconds summary",
                    f"niel_rag_retrieval_duration_seconds_count {cnt}",
                    f"niel_rag_retrieval_duration_seconds_sum {round(tot, 4)}",
                ])

            # LLM response summary
            if self._llm_response_durations:
                cnt = len(self._llm_response_durations)
                tot = sum(self._llm_response_durations)
                lines.extend([
                    "\n# HELP niel_llm_response_duration_seconds LLM inference latency summary.",
                    "# TYPE niel_llm_response_duration_seconds summary",
                    f"niel_llm_response_duration_seconds_count {cnt}",
                    f"niel_llm_response_duration_seconds_sum {round(tot, 4)}",
                ])

            # Agent tools summary
            if self._agent_tool_durations:
                lines.extend([
                    "\n# HELP niel_agent_tool_duration_seconds Tool execution duration by tool name.",
                    "# TYPE niel_agent_tool_duration_seconds summary",
                ])
                for t_name, durs in sorted(self._agent_tool_durations.items()):
                    lines.append(f'niel_agent_tool_duration_seconds_count{{tool="{t_name}"}} {len(durs)}')
                    lines.append(f'niel_agent_tool_duration_seconds_sum{{tool="{t_name}"}} {round(sum(durs), 4)}')

            lines.append("")
            return "\n".join(lines)


# Global singleton instance
metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    return metrics_collector
