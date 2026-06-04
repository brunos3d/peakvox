from pathlib import Path

import pytest

from app.models.registry_types import ModelDescriptor
from app.services.runtime import PeakVoxRuntime, ModelNotAvailableInEdition


class _FakeAdapter:
    """Minimal adapter stub (availability is descriptor-driven, not behavior)."""

    def __init__(self, descriptor):
        self.descriptor = descriptor

    @property
    def model_id(self):
        return self.descriptor.id

    def get_supported_tags(self):
        return list(self.descriptor.supported_tags)

    def get_capabilities(self):
        return self.descriptor.capabilities

    async def generate(self, **kwargs):
        return (1.0, ["ok"])


def _runtime():
    rt = PeakVoxRuntime()
    rt.register_adapter(_FakeAdapter(ModelDescriptor(
        id="ce-only", name="CE", description="d", provider="p", editions=["community"])))
    rt.register_adapter(_FakeAdapter(ModelDescriptor(
        id="everywhere", name="EW", description="d", provider="p",
        editions=["community", "cloud"], is_default=True)))
    return rt


def test_is_available_is_edition_scoped():
    rt = _runtime()
    assert rt.is_available("ce-only", edition="community") is True
    assert rt.is_available("ce-only", edition="cloud") is False
    assert rt.is_available("everywhere", edition="cloud") is True


def test_ensure_available_raises_for_unavailable_edition():
    rt = _runtime()
    rt.ensure_available("ce-only", edition="community")  # no raise
    with pytest.raises(ModelNotAvailableInEdition):
        rt.ensure_available("ce-only", edition="cloud")


async def test_generate_rejects_model_unavailable_in_edition(monkeypatch):
    from app.core import config as config_module
    monkeypatch.setattr(config_module.settings, "EDITION", "cloud")
    rt = _runtime()
    with pytest.raises(ModelNotAvailableInEdition):
        await rt.generate(None, text="hi", model_id="ce-only", output_path=Path("/tmp/x.wav"))
