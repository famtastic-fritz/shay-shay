from agent.models_dev import get_model_capabilities
from shay_cli.auth import ZAI_ENDPOINTS
from shay_cli.models import _PROVIDER_MODELS


def test_glm_5_2_capabilities_are_text_only():
    caps = get_model_capabilities("zai", "glm-5.2")
    assert caps is not None
    assert caps.supports_tools is False
    assert caps.supports_vision is False
    assert caps.model_family == "glm"


def test_glm_5_2_is_in_zai_provider_catalog():
    assert "glm-5.2" in _PROVIDER_MODELS["zai"]


def test_zai_coding_endpoint_probe_prefers_glm_5_2():
    coding = [entry for entry in ZAI_ENDPOINTS if entry[0].startswith("coding-")]
    assert coding
    for _, _, probe_models, _ in coding:
        assert probe_models[0] == "glm-5.2"
