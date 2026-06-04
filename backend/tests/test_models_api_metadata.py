from app.api.models import _descriptor_payload, _writes_enabled
from app.models.registry_types import ModelDescriptor, ModelRequirements, ModelLicense


def test_payload_includes_new_metadata():
    d = ModelDescriptor(
        id="m", name="M", description="d", provider="p",
        requirements=ModelRequirements(min_vram_gb=8, gpu_required=True),
        license=ModelLicense(name="Apache License 2.0", code="apache-2.0", commercial_use=True),
        provider_metadata={
            "author": "k2-fsa",
            "homepage_url": "https://example.test/model",
            "repository_url": "https://github.com/example/model",
        },
    )
    payload = _descriptor_payload(d)
    assert payload["requirements"]["min_vram_gb"] == 8
    assert payload["license"]["code"] == "apache-2.0"
    assert payload["provider_metadata"]["author"] == "k2-fsa"
    assert payload["homepage_url"] == "https://example.test/model"
    assert payload["repository_url"] == "https://github.com/example/model"
    assert payload["license_name"] == "Apache License 2.0"
    assert payload["install_status"] == "installed"
    assert payload["activation_status"] == "active"


def test_lifecycle_writes_enabled_in_community():
    # CE is self-hosted: the local owner manages their own models ("Ollama for Voice").
    assert _writes_enabled() is True
