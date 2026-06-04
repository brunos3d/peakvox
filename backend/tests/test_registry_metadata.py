from app.models.registry_types import ModelDescriptor, ModelRequirements, ModelLicense


def test_descriptor_defaults_are_backward_compatible():
    d = ModelDescriptor(id="m", name="M", description="d", provider="p")
    assert d.requirements == ModelRequirements()
    assert d.license is None
    assert d.provider_metadata == {}


def test_descriptor_accepts_requirements_and_license():
    d = ModelDescriptor(
        id="m", name="M", description="d", provider="p",
        requirements=ModelRequirements(min_vram_gb=8, gpu_required=True),
        license=ModelLicense(code="apache-2.0", commercial_use=True),
        provider_metadata={"author": "k2-fsa", "homepage": "https://example"},
    )
    assert d.requirements.min_vram_gb == 8
    assert d.license.commercial_use is True
    assert d.provider_metadata["author"] == "k2-fsa"
