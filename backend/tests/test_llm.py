"""
Test suite for LLM interface
"""

from unittest.mock import Mock

import httpx
import ollama
import pytest
from app.services import llm_service
from app.services.llm_service import GLMInterface, ModelConfig, PromptTemplate


@pytest.fixture
def glm_interface():
    """Create LLM interface for testing"""
    config = ModelConfig(
        model_name="llama3.2:latest",
        base_url="http://localhost:11434",
        temperature=0.7
    )
    return GLMInterface(config)


def test_model_config():
    """Test model configuration"""
    config = ModelConfig(model_name="llama3.2:latest")
    assert config.model_name == "llama3.2:latest"
    assert config.temperature == 0.7
    assert config.max_tokens == 2048


def test_client_receives_configured_timeout(monkeypatch):
    """Test configured timeout is passed to the Ollama client."""
    client_factory = Mock(return_value=Mock())
    monkeypatch.setattr(llm_service.ollama, "Client", client_factory)

    config = ModelConfig(base_url="http://ollama.example", timeout=42)
    GLMInterface(config)

    client_factory.assert_called_once_with(host="http://ollama.example", timeout=42)


def test_generate_retries_transient_connect_error_then_succeeds(monkeypatch):
    """Test transient connection errors are retried before succeeding."""
    sleep_calls = []
    monkeypatch.setattr(llm_service.time, "sleep", lambda delay: sleep_calls.append(delay))

    interface = GLMInterface(ModelConfig(model_name="llama3.2:latest", engine="ollama"))
    interface.client = Mock()
    interface.client.chat.side_effect = [
        httpx.ConnectError("connection refused"),
        {"message": {"content": "ok"}, "eval_count": 1},
    ]

    response = interface.generate("hello")

    assert response == "ok"
    assert interface.client.chat.call_count == 2
    assert sleep_calls == [1]


def test_generate_does_not_retry_non_transient_response_error(monkeypatch):
    """Test non-transient Ollama errors are not retried."""
    sleep_mock = Mock()
    monkeypatch.setattr(llm_service.time, "sleep", sleep_mock)

    interface = GLMInterface(ModelConfig(model_name="llama3.2:latest", engine="ollama"))
    interface.client = Mock()
    interface.client.chat.side_effect = ollama.ResponseError("model not found", status_code=404)

    with pytest.raises(ollama.ResponseError):
        interface.generate("hello")

    assert interface.client.chat.call_count == 1
    sleep_mock.assert_not_called()


def test_generate_uses_copilot_engine(monkeypatch):
    """With engine=copilot, generation goes through copilotd, not Ollama."""
    monkeypatch.setattr(
        llm_service.copilot_client, "is_configured", lambda: True
    )
    monkeypatch.setattr(
        llm_service.copilot_client,
        "generate",
        Mock(return_value=("copilot says hi", "copilot:claude-opus-4.8-fast")),
    )

    interface = GLMInterface(ModelConfig(model_name="llama3.2:latest", engine="copilot"))
    interface.client = Mock()

    response = interface.generate("hello", system_prompt="be brief")

    assert response == "copilot says hi"
    interface.client.chat.assert_not_called()
    assert interface.active_model_name.startswith("copilot:")


def test_copilot_strict_raises_when_unavailable(monkeypatch):
    """Strict mode refuses the silent Ollama fallback when copilotd is down."""
    monkeypatch.setattr(llm_service.time, "sleep", lambda _: None)
    monkeypatch.setattr(llm_service.copilot_client, "is_configured", lambda: True)
    monkeypatch.setattr(llm_service.copilot_client, "generate", Mock(return_value=None))
    monkeypatch.setenv("COPILOT_STRICT", "1")

    interface = GLMInterface(ModelConfig(model_name="llama3.2:latest", engine="copilot"))
    interface.client = Mock()

    with pytest.raises(RuntimeError):
        interface.generate("hello")

    interface.client.chat.assert_not_called()


def test_copilot_non_strict_falls_back_to_ollama(monkeypatch):
    """With strict mode off, copilotd downtime falls back to local Ollama."""
    monkeypatch.setattr(llm_service.time, "sleep", lambda _: None)
    monkeypatch.setattr(llm_service.copilot_client, "is_configured", lambda: True)
    monkeypatch.setattr(llm_service.copilot_client, "generate", Mock(return_value=None))
    monkeypatch.setenv("COPILOT_STRICT", "0")

    interface = GLMInterface(ModelConfig(model_name="llama3.2:latest", engine="copilot"))
    interface.client = Mock()
    interface.client.chat.return_value = {"message": {"content": "ollama fallback"}}

    assert interface.generate("hello") == "ollama fallback"


def test_prompt_template():
    """Test prompt template formatting"""
    prompt = PromptTemplate.format(
        "research_analysis",
        content="Sample research content"
    )
    assert "Sample research content" in prompt
    assert "analysis" in prompt.lower()


@pytest.mark.skipif(
    True,
    reason="Requires running Ollama server"
)
def test_health_check(glm_interface):
    """Test GLM health check"""
    is_healthy = glm_interface.health_check()
    assert isinstance(is_healthy, bool)


@pytest.mark.skipif(
    True,
    reason="Requires running Ollama server"
)
def test_generate(glm_interface):
    """Test text generation"""
    response = glm_interface.generate(
        prompt="What is machine learning?",
        max_tokens=100
    )
    assert isinstance(response, str)
    assert len(response) > 0


def test_prompt_templates_exist():
    """Test that all prompt templates exist"""
    templates = [
        "RESEARCH_ANALYSIS",
        "GAP_DETECTION",
        "RECOMMENDATION",
        "SUMMARIZATION"
    ]
    for template in templates:
        assert hasattr(PromptTemplate, template)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
