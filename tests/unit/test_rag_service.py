import sys
from pathlib import Path

import pytest
pytest.importorskip("qdrant_client", reason="Qdrant client is required for RAG tests")

project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

from src.config.models import LLMConfig, LLMModels, LLMProvider, RAGConfig, VoiceAgentConfig
from src.rag.service import RAGResult, RAGService


def build_base_config(rag_enabled: bool = False) -> VoiceAgentConfig:
    return VoiceAgentConfig(
        llm=LLMConfig(
            provider=LLMProvider.OPENAI,
            api_key="test_api_key_12345",
            base_url="https://api.example.com",
            models=LLMModels(default="gpt-5-mini", fast="gpt-5-mini", creative="gpt-5-mini"),
        ),
        rag=RAGConfig(enabled=rag_enabled),
    )


@pytest.mark.asyncio
async def test_rag_service_disabled_returns_empty():
    service = RAGService(build_base_config(False))
    results = await service.retrieve("hello world", user_id=None)
    assert results == []


def test_rag_prompt_formatting():
    config = build_base_config(True)
    service = RAGService(config)
    results = [
        RAGResult(
            text="Python 是一种高级编程语言。",
            score=0.42,
            source="docs/intro.md",
            metadata={"chunk_index": 1},
        ),
    ]

    prompt = service.build_prompt(results)
    assert "Python" in prompt
    assert "docs/intro.md" in prompt


def test_collection_name_resolution():
    config = build_base_config(True)
    config.rag.per_user_collections = True
    config.rag.collection_name_template = "{collection}-{user_id}-{corpus_id}"
    service = RAGService(config)

    name = service.resolve_collection_name(user_id="User 01", corpus_id="Primary")

    assert name.startswith(config.rag.collection + "-")
    assert "user-01" in name
    assert name.endswith("-primary")

