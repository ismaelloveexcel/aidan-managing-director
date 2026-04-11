"""LemonSqueezy API v1 client for payment checkout URL generation.

Handles global VAT automatically. Free to start.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.lemonsqueezy.com/v1"
_STUB_CHECKOUT_URL = "https://lemonsqueezy.com"


class LemonSqueezyClient:
    """Async client for the LemonSqueezy API v1.

    Gracefully degrades to stub responses when ``lemonsqueezy_api_key`` is not
    configured, so callers never need to guard against missing credentials.
    """

    def is_configured(self) -> bool:
        """Return ``True`` if a LemonSqueezy API key is present in settings."""
        return bool(get_settings().lemonsqueezy_api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {get_settings().lemonsqueezy_api_key}",
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json",
        }

    async def create_checkout(
        self,
        variant_id: str,
        product_name: str,
        email: str,
        custom_price_cents: int | None = None,
    ) -> dict[str, Any]:
        """Generate a hosted checkout URL for a product variant.

        Args:
            variant_id: LemonSqueezy variant ID to check out.
            product_name: Display name pre-filled in checkout metadata.
            email: Buyer e-mail pre-filled in the checkout form.
            custom_price_cents: Override price in cents (e.g. 999 → $9.99).
                Pass ``None`` to use the variant's default price.

        Returns:
            ``{"checkout_url": str, "stub": bool}`` — ``stub`` is ``True``
            when the client is not configured and a fallback URL is returned.
        """
        if not self.is_configured():
            return {"checkout_url": _STUB_CHECKOUT_URL, "stub": True}

        settings = get_settings()
        attributes: dict[str, Any] = {
            "checkout_data": {"email": email, "name": product_name},
            "product_options": {"redirect_url": ""},
        }
        if custom_price_cents is not None:
            attributes["custom_price"] = custom_price_cents

        payload = {
            "data": {
                "type": "checkouts",
                "attributes": attributes,
                "relationships": {
                    "store": {
                        "data": {"type": "stores", "id": settings.lemonsqueezy_store_id}
                    },
                    "variant": {
                        "data": {"type": "variants", "id": variant_id}
                    },
                },
            }
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{_BASE_URL}/checkouts",
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
                data = response.json()
                checkout_url: str = (
                    data["data"]["attributes"]["url"]
                )
                return {"checkout_url": checkout_url, "stub": False}
        except httpx.HTTPError as exc:
            logger.warning("LemonSqueezy create_checkout failed: %s", exc)
            return {"checkout_url": _STUB_CHECKOUT_URL, "stub": True}

    async def list_products(self) -> list[dict[str, Any]]:
        """Return all products in the configured store.

        Returns:
            List of ``{"id": str, "name": str, "status": str,
            "buy_now_url": str}`` dicts, or ``[]`` when not configured.
        """
        if not self.is_configured():
            return []

        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{_BASE_URL}/products",
                    params={"filter[store_id]": settings.lemonsqueezy_store_id},
                    headers=self._headers(),
                )
                response.raise_for_status()
                items = response.json().get("data", [])
                return [
                    {
                        "id": item["id"],
                        "name": item["attributes"].get("name", ""),
                        "status": item["attributes"].get("status", ""),
                        "buy_now_url": item["attributes"].get("buy_now_url", ""),
                    }
                    for item in items
                ]
        except httpx.HTTPError as exc:
            logger.warning("LemonSqueezy list_products failed: %s", exc)
            return []

    async def list_variants(self, product_id: str) -> list[dict[str, Any]]:
        """Return all variants for a given product.

        Args:
            product_id: LemonSqueezy product ID to query variants for.

        Returns:
            List of ``{"id": str, "name": str, "price": int, "status": str}``
            dicts, or ``[]`` when not configured or on HTTP error.
        """
        if not self.is_configured():
            return []

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{_BASE_URL}/variants",
                    params={"filter[product_id]": product_id},
                    headers=self._headers(),
                )
                response.raise_for_status()
                items = response.json().get("data", [])
                return [
                    {
                        "id": item["id"],
                        "name": item["attributes"].get("name", ""),
                        "price": item["attributes"].get("price", 0),
                        "status": item["attributes"].get("status", ""),
                    }
                    for item in items
                ]
        except httpx.HTTPError as exc:
            logger.warning("LemonSqueezy list_variants failed: %s", exc)
            return []
