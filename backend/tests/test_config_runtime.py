from app.utils import config_loader
from app.utils.config_loader import ConfigLoader


def test_effective_config_maps_runtime_llm_queue_and_ocr_values(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
llm:
  model_name: test-model
  context_window: 1234
  timeout: 45
  top_p: 0.8
  keep_alive: 5m
  num_parallel: 3
retrieval:
  min_relevance_score: 0.2
analysis_queue:
  max_workers: 2
  max_attempts: 3
ocr:
  enabled: true
  dpi: 150
  concurrency: 2
  timeout: 90
  min_chars_per_page: 20
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(config_loader, "load_project_env", lambda: None)
    for name in (
      "OLLAMA_KEEP_ALIVE", "OLLAMA_NUM_PARALLEL", "OCR_ENABLED",
      "MIN_RELEVANCE_SCORE", "OCR_SERVICE_URL", "OCR_IMAGE_MODE", "OCR_DPI",
      "OCR_CONCURRENCY", "OCR_TIMEOUT", "OCR_MIN_CHARS_PER_PAGE",
      "OCR_NGRAM_SIZE", "OCR_NGRAM_WINDOW", "OCR_VALIDATE_ON_STARTUP",
    ):
      monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OLLAMA_MODEL", "env-model")

    config = ConfigLoader(str(config_path)).get_config()

    assert config.llm.model_name == "env-model"
    assert config.llm.context_window == 1234
    assert config.llm.timeout == 45
    assert config.llm.top_p == 0.8
    assert config.llm.keep_alive == "5m"
    assert config.llm.num_parallel == 3
    assert config.retrieval.min_relevance_score == 0.2
    assert config.queue.max_workers == 2
    assert config.queue.max_attempts == 3
    assert config.ocr.enabled is True
    assert config.ocr.dpi == 150


def test_config_rejects_more_than_two_local_analysis_workers(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("analysis_queue:\n  max_workers: 3\n", encoding="utf-8")
    monkeypatch.setattr(config_loader, "load_project_env", lambda: None)

    try:
        ConfigLoader(str(config_path))
    except ValueError as exc:
        assert "max_workers" in str(exc)
    else:
        raise AssertionError("ConfigLoader must reject unsafe local queue worker counts")



def test_dependency_factory_passes_effective_llm_fields(monkeypatch):
    from app.api import dependencies

    captured = {}

    class FakeLLM:
        def __init__(self, model_config):
            captured["config"] = model_config

    config = ConfigLoader().get_config()
    config.llm.top_p = 0.77
    config.llm.timeout = 33
    config.llm.context_window = 4097
    config.llm.keep_alive = "9m"
    config.llm.num_parallel = 2
    monkeypatch.setattr(dependencies, "config", config)
    monkeypatch.setattr(dependencies, "GLMInterface", FakeLLM)
    dependencies.get_glm_interface.cache_clear()
    dependencies._components.pop("glm", None)
    try:
        dependencies.get_glm_interface()
        model_config = captured["config"]
        assert model_config.top_p == 0.77
        assert model_config.timeout == 33
        assert model_config.num_ctx == 4097
        assert model_config.keep_alive == "9m"
        assert model_config.max_parallel == 2
    finally:
        dependencies.get_glm_interface.cache_clear()
        dependencies._components.pop("glm", None)
