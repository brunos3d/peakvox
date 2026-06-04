"""Edition-gated router mounting.

Cloud routers mount only when their feature flag is on. In Community Edition this is a no-op,
keeping the commercial surface entirely unmounted (not merely 404) — the open-core deployment
boundary from docs/architecture/01-PRODUCT_ARCHITECTURE.md §4.2.
"""

import logging

from fastapi import FastAPI

from app.core.features import Features

logger = logging.getLogger(__name__)


def mount_cloud_routers(app: FastAPI, *, features: Features) -> None:
    """Mount Cloud-only routers gated by feature flags. No-op in Community Edition.

    Later phases add blocks like:

        if features.billing:
            from app.cloud.billing import router as billing_router
            app.include_router(billing_router, prefix="/billing", tags=["Billing"])
    """
    if not any(
        [features.auth, features.billing, features.marketplace, features.creators, features.payouts]
    ):
        return  # Community Edition: mount nothing.
    logger.info("Cloud edition detected — mounting enabled cloud routers")
    # Phase 4+ register concrete routers here, each guarded by its flag.
