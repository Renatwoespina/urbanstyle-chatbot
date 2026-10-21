"""Fixtures compartidas: aíslan disco y evitan llamadas reales al LLM."""

from __future__ import annotations

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from src import config


@pytest.fixture
def entorno_temporal(tmp_path, monkeypatch):
    """Redirige los archivos generados a un directorio temporal."""
    monkeypatch.setattr(config, "SOLICITUDES_FILE", tmp_path / "solicitudes.json")
    monkeypatch.setattr(config, "MEMORIA_FILE", tmp_path / "memoria.json")
    monkeypatch.setattr(config, "PLAN_FILE", tmp_path / "plan_actual.json")
    return tmp_path


class FakeLLM(BaseChatModel):
    """Chat model de prueba: responde un texto fijo, registra prompts y acepta tools."""

    respuesta: str = "respuesta simulada"
    prompts: list[str] = []

    @property
    def _llm_type(self) -> str:
        return "fake-urbanstyle"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.prompts.append(str(messages))
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.respuesta))])

    def bind_tools(self, tools, **kwargs):
        return self


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture(scope="session")
def retriever():
    from src.rag_pipeline import crear_retriever

    return crear_retriever()
