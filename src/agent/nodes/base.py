"""
Base Node Class

This module contains the base class for agent nodes, providing:
- Configuration management
- HTTP client lifecycle (lazy initialization)
- RAG service integration
- Resource cleanup and context manager support

All specialized node modules (input_processor, llm_caller, etc.) will
inherit from this base class.
"""

import json
import logging
import asyncio
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx

from ..state import AgentState

# Import configuration
try:
    from config.models import VoiceAgentConfig
except ImportError:
    # Fallback for when running as script
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from config.models import VoiceAgentConfig

# Import RAG service (optional dependency)
try:
    from rag.service import RAGService
except ImportError:  # pragma: no cover - optional dependency
    RAGService = None  # type: ignore


logger = logging.getLogger(__name__)


# ============================================================================
# Utility Classes
# ============================================================================

class DateTimeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects.

    Converts datetime objects to ISO format strings when serializing to JSON.
    This is used throughout the agent for consistent datetime handling.

    Example:
        >>> import json
        >>> data = {"timestamp": datetime.now()}
        >>> json.dumps(data, cls=DateTimeJSONEncoder)
        '{"timestamp": "2025-01-15T10:30:45.123456"}'
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# ============================================================================
# Base Node Class
# ============================================================================

class AgentNodesBase:
    """Base class for agent nodes providing core functionality.

    This class provides:
    - Configuration management (LLM, RAG, etc.)
    - HTTP client lifecycle management (lazy initialization with thread safety)
    - RAG service integration (optional, enabled via config)
    - Resource cleanup and async context manager support

    All specialized node classes (InputProcessor, LLMCaller, ToolHandler, etc.)
    should inherit from this base to share common functionality.

    Attributes:
        config: Voice agent configuration object
        logger: Logger instance for this class
        trace: Optional TraceEmitter for visualization
        _http_client: Lazy-initialized httpx.AsyncClient for LLM API calls
        _rag_service: Optional RAG service for document retrieval

    Example:
        >>> from config.models import VoiceAgentConfig
        >>> config = VoiceAgentConfig()
        >>>
        >>> # Using async context manager (recommended)
        >>> async with AgentNodesBase(config) as nodes:
        ...     # nodes.cleanup() will be called automatically
        ...     result = await nodes.some_method(state)
        >>>
        >>> # Manual cleanup
        >>> nodes = AgentNodesBase(config)
        >>> try:
        ...     result = await nodes.some_method(state)
        >>> finally:
        ...     await nodes.cleanup()
    """

    def __init__(self, config: VoiceAgentConfig, trace=None, *, observability=None):
        """Initialize base node configuration.

        Args:
            config: Voice agent configuration object containing:
                - llm: LLM provider settings (API key, base URL, timeout)
                - rag: RAG settings (enabled, collection name, etc.)
            trace: Optional TraceEmitter instance for visualization events
            observability: Optional Observability tracker for metrics
        """
        self.config = config
        self.logger = logger

        # HTTP client for LLM API calls (lazy-initialized)
        self._http_client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()  # Thread-safe initialization

        # Optional trace emitter for visualization
        self.trace = trace
        self.observability = observability

        # Initialize RAG service if enabled
        self._rag_service: Optional[RAGService] = None
        if RAGService and self.config.rag.enabled:
            try:
                self._rag_service = RAGService(config)
                self.logger.info("📚 RAG service initialized")
            except Exception as exc:  # pragma: no cover - safeguard
                self.logger.warning(f"RAG service initialization failed: {exc}")
                self._rag_service = None

    # ========================================================================
    # HTTP Client Management
    # ========================================================================

    async def _ensure_http_client(self):
        """Ensure HTTP client is initialized (lazy loading).

        Uses double-checked locking pattern for thread-safe singleton initialization.
        The HTTP client is shared across all LLM calls to reuse connections.

        The client is configured with:
        - Timeout from config.llm.timeout (default 120s)
        - Authorization header with API key
        - Content-Type: application/json

        Thread-safe: Multiple concurrent calls will only create one client.
        """
        if self._http_client is None:
            async with self._client_lock:
                if self._http_client is None:  # Double-check
                    timeout = httpx.Timeout(self.config.llm.timeout, connect=10)
                    self._http_client = httpx.AsyncClient(
                        timeout=timeout,
                        headers={
                            "Authorization": f"Bearer {self.config.llm.api_key}",
                            "Content-Type": "application/json"
                        }
                    )
                    self.logger.debug("HTTP 客户端初始化成功")

    def _build_llm_url(self, endpoint: str = "chat/completions") -> str:
        """Build complete LLM API URL.

        Automatically handles whether base_url includes /v1 or not,
        ensuring the correct URL format for OpenAI-compatible APIs.

        Args:
            endpoint: API endpoint path, defaults to "chat/completions"

        Returns:
            Complete API URL string

        Examples:
            >>> # base_url = "https://api.openai-proxy.org/v1"
            >>> self._build_llm_url()
            "https://api.openai-proxy.org/v1/chat/completions"

            >>> # base_url = "https://api.openai-proxy.org"
            >>> self._build_llm_url()
            "https://api.openai-proxy.org/v1/chat/completions"

            >>> # Custom endpoint
            >>> self._build_llm_url("embeddings")
            "https://api.openai-proxy.org/v1/embeddings"
        """
        # Debug logging for URL construction
        self.logger.info(f"🔧 配置检查 - base_url: {self.config.llm.base_url}")
        self.logger.info(f"🔧 配置检查 - provider: {self.config.llm.provider}")
        self.logger.info(f"🔧 配置检查 - model: {self.config.llm.models.default}")

        base = self.config.llm.base_url.rstrip('/')

        # Only add /v1 if base_url doesn't already have it
        if not base.endswith('/v1'):
            base = base + '/v1'

        url = f"{base}/{endpoint}"
        self.logger.info(f"🔧 最终 URL: {url}")
        return url

    # ========================================================================
    # RAG Integration
    # ========================================================================

    async def _retrieve_rag_snippets(self, state: AgentState) -> List[Any]:
        """Retrieve relevant document snippets using RAG.

        This method queries the RAG service (if enabled) to find relevant
        document snippets based on the user's input. Results are stored
        in state["rag_snippets"] for use in prompt building.

        Args:
            state: Current conversation state containing:
                - user_input: Query text for RAG retrieval
                - user_id: Optional user identifier for per-user collections
                - active_corpus_id: Corpus to search (defaults to config default)
                - rag_collection: Collection name override (optional)

        Returns:
            List of RAG result objects with text, score, source, metadata

        Side Effects:
            Updates state with:
            - rag_snippets: List of retrieved snippets (empty list if RAG disabled/failed)
            - active_corpus_id: Set to default corpus if not provided
            - rag_collection: Resolved collection name

        Example:
            >>> state = {
            ...     "user_input": "What is the capital of France?",
            ...     "user_id": "user123"
            ... }
            >>> results = await self._retrieve_rag_snippets(state)
            >>> state["rag_snippets"]
            [
                {
                    "text": "Paris is the capital of France...",
                    "score": 0.92,
                    "source": "geography.pdf",
                    "metadata": {"page": 42}
                }
            ]
        """
        start_time = time.perf_counter()
        metrics_status = "skipped"
        resolved_collection: Optional[str] = None
        try:
            # Early return if RAG not enabled or initialized
            if not self._rag_service or not self._rag_service.enabled:
                state["rag_snippets"] = []
                metrics_status = "disabled"
                return []

            # Get query from user input
            query = state.get("user_input", "")
            if not query.strip():
                state["rag_snippets"] = []
                metrics_status = "empty-query"
                return []

            # Get user_id and corpus_id for collection resolution
            user_id = state.get("user_id")
            corpus_id = state.get("active_corpus_id")
            if corpus_id is None:
                corpus_id = self.config.rag.default_corpus_name
                state["active_corpus_id"] = corpus_id

            # Resolve collection name (handles per-user collections if enabled)
            try:
                resolved_collection = self._rag_service.resolve_collection_name(
                    user_id=user_id,
                    corpus_id=corpus_id,
                    collection_name=state.get("rag_collection"),
                )
                state["rag_collection"] = resolved_collection
            except ValueError as exc:
                self.logger.warning(f"RAG collection resolution failed: {exc}")
                state["rag_snippets"] = []
                metrics_status = "invalid-collection"
                return []

            # Perform RAG retrieval
            try:
                results = await self._rag_service.retrieve(
                    query,
                    user_id=user_id,
                    corpus_id=corpus_id,
                    collection_name=resolved_collection,
                )
            except Exception as exc:  # pragma: no cover - tolerate runtime errors
                self.logger.warning(f"RAG 检索失败: {exc}")
                state["rag_snippets"] = []
                metrics_status = "error"
                return []

            # Format results for state storage
            state["rag_snippets"] = [
                {
                    "text": item.text,
                    "score": round(item.score, 4),
                    "source": item.source,
                    "metadata": item.metadata,
                }
                for item in results
            ]

            metrics_status = "success" if results else "no-results"
            return results
        finally:
            if self.observability:
                duration_ms = (time.perf_counter() - start_time) * 1000
                payload = {
                    "status": metrics_status,
                }
                if resolved_collection:
                    payload["collection"] = resolved_collection
                self.observability.observe("rag.retrieve_ms", duration_ms, **payload)
                self.observability.increment("rag.query_count", status=metrics_status)

    # ========================================================================
    # Resource Cleanup
    # ========================================================================

    async def cleanup(self):
        """Clean up resources.

        Closes HTTP client connection and RAG service, releasing resources.
        Should be called when shutting down the service or exiting the program.

        This method is idempotent - it's safe to call multiple times.

        Example:
            >>> nodes = AgentNodesBase(config)
            >>> try:
            ...     await nodes.some_method()
            >>> finally:
            ...     await nodes.cleanup()  # Ensure cleanup happens
        """
        # Close HTTP client
        if self._http_client:
            try:
                await self._http_client.aclose()
                self.logger.debug("HTTP 客户端已关闭")
            except Exception as e:
                self.logger.warning(f"关闭 HTTP 客户端时出错: {e}")
            finally:
                self._http_client = None

        # Close RAG service
        if self._rag_service:
            try:
                await self._rag_service.close()
                self.logger.debug("RAG 服务已关闭")
            except Exception as e:  # pragma: no cover - cleanup safeguard
                self.logger.warning(f"关闭 RAG 服务时出错: {e}")

    # ========================================================================
    # Async Context Manager Support
    # ========================================================================

    async def __aenter__(self):
        """Async context manager entry.

        Allows using the class with async with statement:
            async with AgentNodesBase(config) as nodes:
                await nodes.some_method()
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit, automatically cleans up resources.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        Returns:
            None (exceptions are not suppressed)
        """
        await self.cleanup()


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "AgentNodesBase",
    "DateTimeJSONEncoder",
]
