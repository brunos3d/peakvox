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
        license=ModelLicense(name="Apache License 2.0", code="apache-2.0", commercial_use=True),
        provider_metadata={
            "author": "k2-fsa",
            "homepage_url": "https://example",
            "repository_url": "https://github.com/example/model",
        },
    )
    assert d.requirements.min_vram_gb == 8
    assert d.license.commercial_use is True
    assert d.provider_metadata["author"] == "k2-fsa"
    assert d.homepage_url == "https://example"
    assert d.repository_url == "https://github.com/example/model"
    assert d.install_status == "installed"
    assert d.activation_status == "active"


def test_descriptor_maps_disabled_to_not_installed_inactive():
    d = ModelDescriptor(id="m", name="M", description="d", provider="p", status="disabled")
    assert d.install_status == "not_installed"
    assert d.activation_status == "inactive"
