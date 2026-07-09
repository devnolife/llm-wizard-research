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

    interface = GLMInterface(ModelConfig(model_name="llama3.2:latest"))
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

    interface = GLMInterface(ModelConfig(model_name="llama3.2:latest"))
    interface.client = Mock()
    interface.client.chat.side_effect = ollama.ResponseError("model not found", status_code=404)

    with pytest.raises(ollama.ResponseError):
        interface.generate("hello")

    assert interface.client.chat.call_count == 1
    sleep_mock.assert_not_called()


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
