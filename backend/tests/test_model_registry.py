from pathlib import Path

import pytest

from app.models.registry_types import ModelDescriptor
from app.services.model_providers.base import ModelProvider
from app.services.model_registry import ModelRegistry


class FakeProvider(ModelProvider):
    """A torch-free provider that records calls, for registry behavior tests."""

    def __init__(self, name: str):
        self.name = name
        self._loaded_id = None
        self.load_calls: list[str] = []
        self.offload_calls = 0
        self.generate_calls: list[str] = []

    async def load(self, descriptor):
        self.load_calls.append(descriptor.id)
        self._loaded_id = descriptor.id

    def offload(self):
        self.offload_calls += 1
        self._loaded_id = None

    @property
    def is_loaded(self):
        return self._loaded_id is not None

    @property
    def loaded_model_id(self):
        return self._loaded_id

    async def generate(self, *, descriptor, text, output_path, params=None, **kw):
        self.generate_calls.append(descriptor.id)
        return (1.23, [f"generated {descriptor.id}"])


def _descriptor(model_id: str, provider: str, default: bool = False) -> ModelDescriptor:
    return ModelDescriptor(
        id=model_id, name=model_id, description="x", provider=provider,
        status="available", is_default=default,
    )


@pytest.fixture
def registry():
    reg = ModelRegistry()
    reg.set_descriptors([
        _descriptor("base", "omnivoice", default=True),
        _descriptor("distilled", "omnivoice"),
        _descriptor("singing", "omnivoice-singing"),
    ])
    return reg


def test_list_and_get_and_default(registry):
    assert {m.id for m in registry.list_models()} == {"base", "distilled", "singing"}
    assert registry.get("base").id == "base"
    assert registry.get("nope") is None
    assert registry.resolve_default().id == "base"


def test_get_or_default_falls_back(registry):
    assert registry.get_or_default(None).id == "base"
    assert registry.get_or_default("singing").id == "singing"
    with pytest.raises(KeyError):
        registry.get_or_default("ghost")


async def test_ensure_loaded_loads_provider(registry):
    prov = FakeProvider("omnivoice")
    registry.register_provider("omnivoice", lambda: prov)
    await registry.ensure_loaded("base")
    assert prov.loaded_model_id == "base"
    assert registry.resident_model_id == "base"


async def test_switching_model_offloads_previous_provider(registry):
    ov = FakeProvider("omnivoice")
    sing = FakeProvider("omnivoice-singing")
    registry.register_provider("omnivoice", lambda: ov)
    registry.register_provider("omnivoice-singing", lambda: sing)

    await registry.ensure_loaded("base")
    await registry.ensure_loaded("singing")

    assert ov.offload_calls == 1          # previous provider offloaded on switch
    assert sing.loaded_model_id == "singing"
    assert registry.resident_model_id == "singing"


async def test_generate_delegates_and_loads(registry):
    prov = FakeProvider("omnivoice")
    registry.register_provider("omnivoice", lambda: prov)
    duration, logs = await registry.generate(
        "base", text="hi", output_path=Path("/tmp/x.wav"), params={},
    )
    assert duration == 1.23
    assert prov.generate_calls == ["base"]
    assert registry.resident_model_id == "base"


async def test_generate_unknown_model_raises(registry):
    with pytest.raises(KeyError):
        await registry.generate("ghost", text="hi", output_path=Path("/tmp/x.wav"))


async def test_is_generating_flag(registry):
    prov = FakeProvider("omnivoice")
    registry.register_provider("omnivoice", lambda: prov)
    assert registry.is_generating is False
    await registry.generate("base", text="hi", output_path=Path("/tmp/x.wav"), params={})
    assert registry.is_generating is False  # released after completion
