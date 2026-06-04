from app.api.models import _descriptor_payload, _writes_enabled
from app.models.registry_types import ModelDescriptor, ModelRequirements, ModelLicense


def test_payload_includes_new_metadata():
    d = ModelDescriptor(
        id="m", name="M", description="d", provider="p",
        requirements=ModelRequirements(min_vram_gb=8, gpu_required=True),
        license=ModelLicense(code="apache-2.0", commercial_use=True),
        provider_metadata={"author": "k2-fsa"},
    )
    payload = _descriptor_payload(d)
    assert payload["requirements"]["min_vram_gb"] == 8
    assert payload["license"]["code"] == "apache-2.0"
    assert payload["provider_metadata"]["author"] == "k2-fsa"


def test_lifecycle_writes_disabled_in_community():
    # CE: settings.features.auth is False → writes disabled.
    assert _writes_enabled() is False
