from app.services.model_adapters.omnivoice_adapter import (
    OmniVoiceAdapter,
    OmniVoiceSingingAdapter,
)


def test_wire_runtime_registers_family_adapters():
    from app.services.runtime import runtime
    from app.services.model_wiring import wire_runtime

    wire_runtime()

    assert isinstance(runtime.get_adapter("omnivoice-base"), OmniVoiceAdapter)
    assert isinstance(runtime.get_adapter("omnivoice-singing"), OmniVoiceSingingAdapter)
    # The base adapter is NOT the singing subclass — distinct adapter classes, one contract.
    assert not isinstance(runtime.get_adapter("omnivoice-base"), OmniVoiceSingingAdapter)


def test_wire_registry_registers_singing_provider():
    from app.services.model_registry import model_registry
    from app.services.model_wiring import wire_registry

    wire_registry()
    # Both provider factories are registered (not instantiated — that would require torch).
    assert callable(model_registry._provider_factories.get("omnivoice"))
    assert callable(model_registry._provider_factories.get("omnivoice-singing"))
