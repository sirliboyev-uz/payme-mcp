"""Pydantic models for Payme API requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Cards API ──


class CardCreateInput(BaseModel):
    """Input for creating a card token."""
    card_number: str = Field(description="16-digit card number (e.g. '8600123456789012')")
    expire: str = Field(description="Card expiry in MMYY format (e.g. '0399')")
    save: bool = Field(default=True, description="Whether to save the card for future use")


class CardVerifyInput(BaseModel):
    """Input for verifying a card with SMS code."""
    token: str = Field(description="Card token from cards.create response")
    code: str = Field(description="SMS verification code sent to cardholder")


class CardTokenInput(BaseModel):
    """Input for operations requiring a card token."""
    token: str = Field(description="Card token")


# ── Receipts API ──


class ReceiptItem(BaseModel):
    """Line item for a receipt (fiscal compliance)."""
    title: str = Field(description="Item/service name")
    price: int = Field(description="Price in tiyin (1 UZS = 100 tiyin)")
    count: int = Field(default=1, description="Quantity")
    code: str = Field(default="10305001001000000", description="MXIK tax code")
    package_code: str = Field(default="1516282", description="Unit measurement code")
    vat_percent: int = Field(default=0, description="VAT percentage (0 or 12 or 15)")


class ReceiptCreateInput(BaseModel):
    """Input for creating a payment receipt."""
    order_id: str = Field(description="Your unique order/payment ID")
    amount: int = Field(description="Amount in tiyin (e.g. 990000 = 9,900 UZS)")
    description: str = Field(default="", description="Payment description (optional)")
    detail: list[ReceiptItem] | None = Field(
        default=None,
        description="Fiscal receipt line items (optional, for tax compliance)",
    )


class ReceiptPayInput(BaseModel):
    """Input for paying a receipt with a card token."""
    receipt_id: str = Field(description="Receipt ID from receipts.create response")
    token: str = Field(description="Card token from cards.create")


class ReceiptIdInput(BaseModel):
    """Input for operations requiring a receipt ID."""
    receipt_id: str = Field(description="Receipt ID")


class ReceiptSendInput(BaseModel):
    """Input for sending a receipt notification."""
    receipt_id: str = Field(description="Receipt ID")
    phone: str = Field(description="Phone number in format '998901234567'")


# ── Checkout API ──


class CheckoutInput(BaseModel):
    """Input for generating a Payme checkout URL."""
    merchant_id: str = Field(description="Your Payme merchant ID")
    order_id: str = Field(description="Your unique order/payment ID")
    amount: int = Field(description="Amount in tiyin")
    callback_url: str = Field(default="", description="URL to redirect after payment (optional)")
