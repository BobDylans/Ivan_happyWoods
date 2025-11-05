from pathlib import Path
import sys

import pytest

project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

from src.config.models import LLMConfig, LLMModels, LLMProvider, RAGConfig, VoiceAgentConfig
from src.rag.ingestion import IngestionResult, ingest_files


class DummyEmbeddingClient:
    def __init__(self, *args, **kwargs):
        self.calls = []

    async def embed_texts(self, texts):
        self.calls.append(list(texts))
        return [[1.0] * 3 for _ in texts]

    async def aclose(self):  # pragma: no cover - no resources to close
        pass


class DummyVectorStore:
    def __init__(self, *args, **kwargs):
        self.upserts = []

    async def ensure_collection(self, *args, **kwargs):
        return None

    async def upsert_chunks(self, batch):
        self.upserts.append(batch)

    async def close(self):  # pragma: no cover - no resources to close
        pass


def build_test_config(tmp_path: Path) -> VoiceAgentConfig:
    return VoiceAgentConfig(
        llm=LLMConfig(
            provider=LLMProvider.OPENAI,
            api_key="test_api_key_12345",
            base_url="https://api.example.com",
            models=LLMModels(default="gpt-5-mini", fast="gpt-5-mini", creative="gpt-5-mini"),
        ),
        rag=RAGConfig(
            enabled=True,
            upload_temp_dir=str(tmp_path),
            ingest_batch_size=2,
        ),
    )


@pytest.mark.asyncio
async def test_ingest_files_with_dummy_clients(monkeypatch, tmp_path):
    config = build_test_config(tmp_path)
    source_file = tmp_path / "sample.md"
    source_file.write_text("# Hello\nThis is a test document.")

    monkeypatch.setattr("src.rag.ingestion.EmbeddingClient", DummyEmbeddingClient)
    monkeypatch.setattr("src.rag.ingestion.QdrantVectorStore", DummyVectorStore)

    result = await ingest_files(config, [source_file])

    assert isinstance(result, IngestionResult)
    assert result.processed_files == 1
    assert result.stored_chunks > 0

