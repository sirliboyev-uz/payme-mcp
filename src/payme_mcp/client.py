"""HTTP client for Payme Subscribe API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

PAYME_SUBSCRIBE_URL = "https://checkout.paycom.uz/api"
PAYME_SANDBOX_URL = "https://checkout.test.paycom.uz/api"
PAYME_CHECKOUT_URL = "https://checkout.paycom.uz"
PAYME_SANDBOX_CHECKOUT_URL = "https://checkout.test.paycom.uz"


class PaymeError(Exception):
    """Error returned by Payme API."""

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"Payme error {code}: {message}")


class PaymeClient:
    """Client for Payme Subscribe API (cards + receipts)."""

    def __init__(self, payme_id: str, payme_key: str, test_mode: bool = False):
        self.payme_id = payme_id
        self.payme_key = payme_key
        self.test_mode = test_mode
        self.base_url = PAYME_SANDBOX_URL if test_mode else PAYME_SUBSCRIBE_URL
        self.checkout_url = PAYME_SANDBOX_CHECKOUT_URL if test_mode else PAYME_CHECKOUT_URL
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _call(self, method: str, params: dict) -> Any:
        """Make a JSON-RPC call to Payme Subscribe API."""
        headers = {
            "X-Auth": f"{self.payme_id}:{self.payme_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params,
        }

        logger.debug("Payme API call: %s %s", method, params)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.base_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        if "error" in data:
            err = data["error"]
            raise PaymeError(
                code=err.get("code", -1),
                message=err.get("message", {}).get("en", str(err.get("message", "Unknown error"))),
                data=err.get("data"),
            )

        return data.get("result")

    # ── Cards API ──

    async def cards_create(self, number: str, expire: str, save: bool = True) -> dict:
        """Create (tokenize) a card.

        Returns: {"card": {"number": "860012******9012", "expire": "03/99", "token": "...", ...}}
        """
        return await self._call("cards.create", {
            "card": {"number": number, "expire": expire},
            "save": save,
        })

    async def cards_get_verify_code(self, token: str) -> dict:
        """Request SMS verification code for a card.

        Returns: {"sent": true, "phone": "99890***4567", "wait": 60}
        """
        return await self._call("cards.get_verify_code", {
            "token": token,
        })

    async def cards_verify(self, token: str, code: str) -> dict:
        """Verify a card with SMS code.

        Returns: {"card": {"number": "860012******9012", "expire": "03/99", "token": "...", "recurrent": true, "verify": true}}
        """
        return await self._call("cards.verify", {
            "token": token,
            "code": code,
        })

    async def cards_check(self, token: str) -> dict:
        """Check if a card token is valid.

        Returns: {"card": {"number": "860012******9012", "expire": "03/99", "token": "...", "recurrent": true, "verify": true}}
        """
        return await self._call("cards.check", {"token": token})

    async def cards_remove(self, token: str) -> dict:
        """Remove a saved card.

        Returns: {"success": true}
        """
        return await self._call("cards.remove", {"token": token})

    # ── Receipts API ──

    async def receipts_create(
        self,
        order_id: str,
        amount: int,
        description: str = "",
        detail: dict | None = None,
    ) -> dict:
        """Create a payment receipt.

        Args:
            order_id: Your unique order/payment identifier.
            amount: Amount in tiyin (1 UZS = 100 tiyin).
            description: Optional payment description.
            detail: Optional fiscal receipt detail for tax compliance.

        Returns: {"receipt": {"_id": "...", "create_time": ..., "state": 0, ...}}
        """
        params: dict = {
            "amount": amount,
            "account": {"order_id": order_id},
        }
        if description:
            params["description"] = description
        if detail:
            params["detail"] = detail
        return await self._call("receipts.create", params)

    async def receipts_pay(self, receipt_id: str, token: str) -> dict:
        """Pay a receipt using a card token.

        Returns: {"receipt": {"_id": "...", "state": 4, ...}}
        """
        return await self._call("receipts.pay", {
            "id": receipt_id,
            "token": token,
        })

    async def receipts_send(self, receipt_id: str, phone: str) -> dict:
        """Send receipt notification via SMS.

        Returns: {"success": true}
        """
        return await self._call("receipts.send", {
            "id": receipt_id,
            "phone": phone,
        })

    async def receipts_cancel(self, receipt_id: str) -> dict:
        """Cancel a receipt.

        Returns: {"receipt": {"_id": "...", "state": 50, ...}}
        """
        return await self._call("receipts.cancel", {"id": receipt_id})

    async def receipts_check(self, receipt_id: str) -> dict:
        """Check receipt status.

        Returns: {"state": 4} where states: 0=created, 4=paid, 21=held, 50=cancelled
        """
        return await self._call("receipts.check", {"id": receipt_id})

    # ── Checkout URL ──

    def generate_checkout_url(
        self,
        merchant_id: str,
        order_id: str,
        amount: int,
        callback_url: str = "",
    ) -> str:
        """Generate a Payme checkout payment URL.

        Args:
            merchant_id: Your Payme merchant ID.
            order_id: Your unique order identifier.
            amount: Amount in tiyin.
            callback_url: Optional redirect URL after payment.

        Returns: Checkout URL string.
        """
        import base64

        params = f"m={merchant_id};ac.order_id={order_id};a={amount}"
        if callback_url:
            params += f";c={callback_url}"

        encoded = base64.b64encode(params.encode()).decode()
        return f"{self.checkout_url}/{encoded}"
