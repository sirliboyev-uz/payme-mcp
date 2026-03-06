"""Payme MCP Server — AI-powered payment tools for Uzbekistan.

Exposes Payme Subscribe API (cards, receipts, checkout) as MCP tools
that any AI agent (Claude, GPT, etc.) can use.

Environment variables:
    PAYME_ID       — Your Payme merchant ID (required)
    PAYME_KEY      — Your Payme merchant key (required)
    PAYME_TEST     — Set to "true" for sandbox mode (optional, default: false)
"""

from __future__ import annotations

import json
import logging
import os

from fastmcp import FastMCP

from payme_mcp.client import PaymeClient, PaymeError
from payme_mcp.types import (
    CardCreateInput,
    CardTokenInput,
    CardVerifyInput,
    CheckoutInput,
    ReceiptCreateInput,
    ReceiptIdInput,
    ReceiptPayInput,
    ReceiptSendInput,
)

logger = logging.getLogger(__name__)

mcp = FastMCP("Payme MCP")


def _get_client() -> PaymeClient:
    """Get a configured PaymeClient from environment variables."""
    payme_id = os.environ.get("PAYME_ID", "")
    payme_key = os.environ.get("PAYME_KEY", "")
    test_mode = os.environ.get("PAYME_TEST", "false").lower() in ("true", "1", "yes")

    if not payme_id or not payme_key:
        raise ValueError(
            "PAYME_ID and PAYME_KEY environment variables are required. "
            "Get your credentials at https://merchant.paycom.uz"
        )

    return PaymeClient(payme_id=payme_id, payme_key=payme_key, test_mode=test_mode)


def _format_result(data: dict) -> str:
    """Format API response as readable JSON."""
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _format_error(e: PaymeError) -> str:
    """Format Payme error as readable message."""
    msg = f"Payme API Error (code {e.code}): {e.message}"
    if e.data:
        msg += f"\nDetails: {e.data}"
    return msg


# ═══════════════════════════════════════════════════════════
#  CARDS — Tokenize and manage payment cards
# ═══════════════════════════════════════════════════════════


@mcp.tool
async def cards_create(params: CardCreateInput) -> str:
    """Create (tokenize) a payment card.

    Sends the card number and expiry to Payme and returns a reusable token.
    After creation, you must verify the card with an SMS code using cards_verify.

    Example: cards_create(card_number="8600123456789012", expire="0399")
    """
    client = _get_client()
    try:
        result = await client.cards_create(
            number=params.card_number,
            expire=params.expire,
            save=params.save,
        )
        # Auto-request verification code
        token = result.get("card", {}).get("token", "")
        if token:
            try:
                verify_info = await client.cards_get_verify_code(token)
                result["verification"] = verify_info
            except PaymeError:
                result["verification"] = {"note": "Call cards_verify with the SMS code sent to cardholder"}

        return _format_result(result)
    except PaymeError as e:
        return _format_error(e)


@mcp.tool
async def cards_verify(params: CardVerifyInput) -> str:
    """Verify a card using the SMS code sent to the cardholder.

    Must be called after cards_create. The code is sent via SMS to the
    phone number linked to the card.

    Example: cards_verify(token="630e5e...", code="666666")
    """
    client = _get_client()
    try:
        result = await client.cards_verify(token=params.token, code=params.code)
        return _format_result(result)
    except PaymeError as e:
        return _format_error(e)


@mcp.tool
async def cards_check(params: CardTokenInput) -> str:
    """Check if a card token is still valid and get card details.

    Returns masked card number, expiry, and verification status.

    Example: cards_check(token="630e5e...")
    """
    client = _get_client()
    try:
        result = await client.cards_check(token=params.token)
        return _format_result(result)
    except PaymeError as e:
        return _format_error(e)


@mcp.tool
async def cards_remove(params: CardTokenInput) -> str:
    """Remove a saved card token.

    The token will no longer be usable for payments after removal.

    Example: cards_remove(token="630e5e...")
    """
    client = _get_client()
    try:
        result = await client.cards_remove(token=params.token)
        return _format_result(result)
    except PaymeError as e:
        return _format_error(e)


# ═══════════════════════════════════════════════════════════
#  RECEIPTS — Create and process payments
# ═══════════════════════════════════════════════════════════


@mcp.tool
async def receipts_create(params: ReceiptCreateInput) -> str:
    """Create a payment receipt.

    Creates a new receipt (invoice) in Payme. The receipt must be paid
    using receipts_pay with a card token, or cancelled with receipts_cancel.

    Amount is in tiyin (1 UZS = 100 tiyin).
    Example: 99,000 UZS = 9,900,000 tiyin

    Example: receipts_create(order_id="order-123", amount=9900000, description="Pro subscription")
    """
    client = _get_client()
    try:
        detail = None
        if params.detail:
            detail = {
                "receipt_type": 0,
                "items": [item.model_dump() for item in params.detail],
            }

        result = await client.receipts_create(
            order_id=params.order_id,
            amount=params.amount,
            description=params.description,
            detail=detail,
        )
        return _format_result(result)
    except PaymeError as e:
        return _format_error(e)


@mcp.tool
async def receipts_pay(params: ReceiptPayInput) -> str:
    """Pay a receipt using a verified card token.

    Charges the card and completes the payment. The card must be
    previously verified using cards_verify.

    Example: receipts_pay(receipt_id="63...", token="630e5e...")
    """
    client = _get_client()
    try:
        result = await client.receipts_pay(
            receipt_id=params.receipt_id,
            token=params.token,
        )
        return _format_result(result)
    except PaymeError as e:
        return _format_error(e)


@mcp.tool
async def receipts_send(params: ReceiptSendInput) -> str:
    """Send a receipt notification to the customer via SMS.

    Sends a payment confirmation or receipt link to the specified phone number.

    Example: receipts_send(receipt_id="63...", phone="998901234567")
    """
    client = _get_client()
    try:
        result = await client.receipts_send(
            receipt_id=params.receipt_id,
            phone=params.phone,
        )
        return _format_result(result)
    except PaymeError as e:
        return _format_error(e)


@mcp.tool
async def receipts_cancel(params: ReceiptIdInput) -> str:
    """Cancel a receipt.

    Cancels an unpaid or held receipt. Paid receipts may also be
    cancelled (refunded) depending on your merchant settings.

    Example: receipts_cancel(receipt_id="63...")
    """
    client = _get_client()
    try:
        result = await client.receipts_cancel(receipt_id=params.receipt_id)
        return _format_result(result)
    except PaymeError as e:
        return _format_error(e)


@mcp.tool
async def receipts_check(params: ReceiptIdInput) -> str:
    """Check the status of a receipt.

    Receipt states: 0=created, 4=paid, 21=held, 50=cancelled.

    Example: receipts_check(receipt_id="63...")
    """
    client = _get_client()
    try:
        result = await client.receipts_check(receipt_id=params.receipt_id)
        return _format_result(result)
    except PaymeError as e:
        return _format_error(e)


# ═══════════════════════════════════════════════════════════
#  CHECKOUT — Generate payment URLs
# ═══════════════════════════════════════════════════════════


@mcp.tool
def checkout_url(params: CheckoutInput) -> str:
    """Generate a Payme checkout payment URL.

    Creates a URL that redirects the customer to Payme's hosted
    payment page. Useful for sending payment links via chat/email.

    Amount is in tiyin (1 UZS = 100 tiyin).

    Example: checkout_url(merchant_id="5e7...", order_id="order-123", amount=9900000)
    """
    client = _get_client()
    url = client.generate_checkout_url(
        merchant_id=params.merchant_id,
        order_id=params.order_id,
        amount=params.amount,
        callback_url=params.callback_url,
    )
    return f"Payme checkout URL:\n{url}"


def main():
    """Entry point for the Payme MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
