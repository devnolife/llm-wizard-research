"""
Test suite for LLM interface
"""

import pytest
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
