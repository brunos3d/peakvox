from app.services.model_catalog import BUILTIN_MODELS, builtin_by_id, default_model
from app.services.tag_catalog import TAG_CATALOG


def test_exactly_one_default():
    defaults = [m for m in BUILTIN_MODELS if m.is_default]
    assert len(defaults) == 1
    assert defaults[0].id == "omnivoice-base"


def test_default_model_helper():
    assert default_model().id == "omnivoice-base"


def test_expected_models_present():
    ids = {m.id for m in BUILTIN_MODELS}
    assert {"omnivoice-base", "omnivoice-distilled", "omnivoice-singing"} <= ids


def test_all_supported_tags_exist_in_catalog():
    for model in BUILTIN_MODELS:
        for tag in model.supported_tags:
            assert tag in TAG_CATALOG, f"{model.id} references unknown tag {tag}"


def test_singing_capabilities_and_tags():
    singing = builtin_by_id("omnivoice-singing")
    assert singing is not None
    assert singing.capabilities.supports_singing is True
    assert singing.capabilities.supports_emotions is True
    assert "singing" in singing.supported_tags
    assert "happy" in singing.supported_tags


def test_base_does_not_support_singing_tag():
    base = builtin_by_id("omnivoice-base")
    assert base is not None
    assert base.capabilities.supports_singing is False
    assert "singing" not in base.supported_tags
    assert "laughter" in base.supported_tags


def test_builtin_by_id_unknown_returns_none():
    assert builtin_by_id("nope") is None
