from app.core.database import Base
import app.models.db  # noqa: F401  (registers tables on Base.metadata)

EXPECTED_TABLES = {
    "roles",
    "creators",
    "marketplace_listings",
    "credit_ledgers",
    "transactions",
    "royalties",
    "payouts",
}


def test_commercial_tables_registered():
    assert EXPECTED_TABLES <= set(Base.metadata.tables.keys())


def test_transactions_has_append_only_shape():
    cols = {c.name for c in Base.metadata.tables["transactions"].columns}
    assert {"id", "owner_id", "type", "amount", "balance_after", "ref", "created_at"} <= cols


def test_royalty_split_columns_present():
    cols = {c.name for c in Base.metadata.tables["royalties"].columns}
    assert {"gross_amount", "creator_amount", "platform_amount", "infra_amount"} <= cols
