"""
BillingService — payment provider abstraction.

Supports Manual, Stripe, Midtrans, Xendit providers.
Does NOT process payments directly — delegates to registered providers.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from core.exceptions import ValidationError
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Invoice:
    id: str
    user_id: str
    amount: Decimal
    currency: str
    plan: str
    status: str = "pending"  # pending | paid | failed | cancelled
    provider: str | None = None
    transaction_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    paid_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentResult:
    invoice_id: str
    status: str  # success | failed
    transaction_id: str | None = None
    error: str | None = None


class BillingProvider(ABC):
    """Abstract billing provider."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def charge(
        self,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any],
    ) -> PaymentResult: ...


class ManualProvider(BillingProvider):
    """Manual payment provider — marks invoices as paid immediately."""

    @property
    def provider_name(self) -> str:
        return "manual"

    async def charge(
        self,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any],
    ) -> PaymentResult:
        invoice_id = metadata.get("invoice_id", str(uuid.uuid4()))
        logger.info("Manual payment processed", extra={"invoice_id": invoice_id, "amount": str(amount)})
        return PaymentResult(
            invoice_id=invoice_id,
            status="success",
            transaction_id=f"manual-{uuid.uuid4()}",
        )


class StripeProvider(BillingProvider):
    """Stripe payment provider (stub — real implementation uses stripe SDK)."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return "stripe"

    async def charge(
        self,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any],
    ) -> PaymentResult:
        invoice_id = metadata.get("invoice_id", str(uuid.uuid4()))
        if self._api_key is None:
            return PaymentResult(
                invoice_id=invoice_id,
                status="failed",
                error="Stripe API key not configured",
            )
        logger.info("Stripe payment processed", extra={"invoice_id": invoice_id})
        return PaymentResult(
            invoice_id=invoice_id,
            status="success",
            transaction_id=f"stripe-{uuid.uuid4()}",
        )


class MidtransProvider(BillingProvider):
    """Midtrans payment provider (stub)."""

    def __init__(self, server_key: str | None = None) -> None:
        self._server_key = server_key

    @property
    def provider_name(self) -> str:
        return "midtrans"

    async def charge(
        self,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any],
    ) -> PaymentResult:
        invoice_id = metadata.get("invoice_id", str(uuid.uuid4()))
        if self._server_key is None:
            return PaymentResult(
                invoice_id=invoice_id,
                status="failed",
                error="Midtrans server key not configured",
            )
        logger.info("Midtrans payment processed", extra={"invoice_id": invoice_id})
        return PaymentResult(
            invoice_id=invoice_id,
            status="success",
            transaction_id=f"midtrans-{uuid.uuid4()}",
        )


class XenditProvider(BillingProvider):
    """Xendit payment provider (stub)."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return "xendit"

    async def charge(
        self,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any],
    ) -> PaymentResult:
        invoice_id = metadata.get("invoice_id", str(uuid.uuid4()))
        if self._api_key is None:
            return PaymentResult(
                invoice_id=invoice_id,
                status="failed",
                error="Xendit API key not configured",
            )
        logger.info("Xendit payment processed", extra={"invoice_id": invoice_id})
        return PaymentResult(
            invoice_id=invoice_id,
            status="success",
            transaction_id=f"xendit-{uuid.uuid4()}",
        )


class BillingService:
    """Billing service — manages invoices and payment providers."""

    def __init__(self) -> None:
        self._providers: dict[str, BillingProvider] = {}
        self._invoices: dict[str, Invoice] = {}
        self._metrics: dict[str, int] = {
            "invoices_created": 0,
            "payments_succeeded": 0,
            "payments_failed": 0,
        }
        self._register_default_providers()

    def register_provider(self, provider: BillingProvider) -> None:
        self._providers[provider.provider_name] = provider
        logger.info("Billing provider registered", extra={"provider": provider.provider_name})

    async def create_invoice(
        self,
        user_id: str,
        amount: Decimal,
        currency: str,
        plan: str,
        metadata: dict[str, Any] | None = None,
    ) -> Invoice:
        if amount <= 0:
            raise ValidationError("Amount must be positive")

        invoice = Invoice(
            id=str(uuid.uuid4()),
            user_id=user_id,
            amount=Decimal(str(amount)),
            currency=currency.upper(),
            plan=plan,
            metadata=metadata or {},
        )
        self._invoices[invoice.id] = invoice
        self._metrics["invoices_created"] += 1
        logger.info("Invoice created", extra={"invoice_id": invoice.id, "user_id": user_id, "amount": str(amount)})
        return invoice

    async def process_payment(self, invoice_id: str, provider_name: str) -> PaymentResult:
        invoice = self._invoices.get(invoice_id)
        if invoice is None:
            raise ValidationError(f"Invoice not found: {invoice_id}")

        provider = self._providers.get(provider_name)
        if provider is None:
            raise ValidationError(f"Provider not registered: {provider_name}")

        result = await provider.charge(
            amount=invoice.amount,
            currency=invoice.currency,
            metadata={**invoice.metadata, "invoice_id": invoice_id},
        )

        if result.status == "success":
            invoice.status = "paid"
            invoice.provider = provider_name
            invoice.transaction_id = result.transaction_id
            invoice.paid_at = datetime.now(timezone.utc)
            self._metrics["payments_succeeded"] += 1
        else:
            invoice.status = "failed"
            invoice.provider = provider_name
            self._metrics["payments_failed"] += 1

        return result

    async def get_invoice(self, invoice_id: str) -> Invoice | None:
        return self._invoices.get(invoice_id)

    async def list_invoices(self, user_id: str) -> list[Invoice]:
        return [inv for inv in self._invoices.values() if inv.user_id == user_id]

    async def cancel_invoice(self, invoice_id: str) -> bool:
        invoice = self._invoices.get(invoice_id)
        if invoice is None or invoice.status != "pending":
            return False
        invoice.status = "cancelled"
        return True

    def get_providers(self) -> list[str]:
        return list(self._providers.keys())

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)

    def _register_default_providers(self) -> None:
        self._providers["manual"] = ManualProvider()
        self._providers["stripe"] = StripeProvider()
        self._providers["midtrans"] = MidtransProvider()
        self._providers["xendit"] = XenditProvider()
