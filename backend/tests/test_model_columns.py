from app.core.database import Base
import app.models.db  # noqa: F401


def test_model_has_new_metadata_columns():
    cols = {c.name for c in Base.metadata.tables["models"].columns}
    assert {"requirements", "license", "provider_metadata", "deprecated_at"} <= cols
