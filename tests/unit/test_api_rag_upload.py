from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

from src.api.main import app
from src.config.models import LLMConfig, LLMModels, LLMProvider, RAGConfig, VoiceAgentConfig
from src.rag.ingestion import IngestionResult


client = TestClient(app)


def build_config(temp_dir: Path) -> VoiceAgentConfig:
    return VoiceAgentConfig(
        llm=LLMConfig(
            provider=LLMProvider.OPENAI,
            api_key="test_api_key_12345",
            base_url="https://api.example.com",
            models=LLMModels(default="gpt-5-mini", fast="gpt-5-mini", creative="gpt-5-mini"),
        ),
        rag=RAGConfig(
            enabled=True,
            upload_temp_dir=str(temp_dir),
            ingest_batch_size=2,
        ),
    )


def test_upload_documents_success(monkeypatch, tmp_path):
    config = build_config(tmp_path)
    captured_paths = []

    async def fake_ingest(config_arg, files, recreate=False, batch_size=None):
        captured_paths.extend(files)
        assert batch_size == config.rag.ingest_batch_size
        return IngestionResult(processed_files=len(files), stored_chunks=5)

    monkeypatch.setattr("src.api.routes.get_config", lambda: config)
    monkeypatch.setattr("src.api.routes.configure_proxy_bypass", lambda *_: None)
    monkeypatch.setattr("src.api.routes.ingest_files", fake_ingest)

    response = client.post(
        "/api/v1/rag/upload",
        files=[("files", ("doc.md", b"# heading\ncontent", "text/markdown"))],
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["stored_chunks"] == 5
    assert any(item["status"] == "accepted" for item in data["results"])
    assert captured_paths, "ingest_files should be called with saved paths"
    for path in captured_paths:
        assert not Path(path).exists()


def test_upload_documents_unsupported_type(monkeypatch, tmp_path):
    config = build_config(tmp_path)

    async def fail_if_called(*args, **kwargs):  # pragma: no cover - should not run
        raise AssertionError("ingest_files should not be called for unsupported files")

    monkeypatch.setattr("src.api.routes.get_config", lambda: config)
    monkeypatch.setattr("src.api.routes.configure_proxy_bypass", lambda *_: None)
    monkeypatch.setattr("src.api.routes.ingest_files", fail_if_called)

    response = client.post(
        "/api/v1/rag/upload",
        files=[("files", ("image.png", b"fake", "image/png"))],
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["processed_files"] == 0
    assert data["results"][0]["status"] == "skipped"

