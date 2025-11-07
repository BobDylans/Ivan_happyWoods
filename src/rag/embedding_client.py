"""Embedding client built on top of the existing LLM API endpoint."""

from __future__ import annotations

import logging
from typing import List

import httpx


logger = logging.getLogger(__name__)


class EmbeddingClient:
    """Async client for fetching embeddings from an OpenAI-compatible endpoint."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: int = 15,
    ) -> None:
        self.model = model
        self._endpoint = self._build_embeddings_url(base_url)
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.AsyncClient(timeout=timeout, headers=headers)

    @staticmethod
    def _build_embeddings_url(base_url: str) -> str:
        base = base_url.rstrip("/")
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        return f"{base}/embeddings"

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        payload = {
            "model": self.model,
            "input": texts,
        }

        response = await self._client.post(self._endpoint, json=payload)
        response.raise_for_status()
        data = response.json()
        embeddings = [item["embedding"] for item in data.get("data", [])]

        if len(embeddings) != len(texts):
            logger.warning(
                "Embedding count mismatch: expected %s, got %s",
                len(texts),
                len(embeddings),
            )

        return embeddings

    async def aclose(self) -> None:
        await self._client.aclose()


