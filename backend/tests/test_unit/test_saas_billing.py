"""Unit tests for BillingService."""

from decimal import Decimal

import pytest
from core.exceptions import ValidationError
from services.saas.billing import (
    BillingService,
    ManualProvider,
    MidtransProvider,
    StripeProvider,
    XenditProvider,
)


class TestProviders:

    def test_default_providers_registered(self) -> None:
        svc = BillingService()
        providers = svc.get_providers()
        assert "manual" in providers
        assert "stripe" in providers
        assert "midtrans" in providers
        assert "xendit" in providers

    @pytest.mark.asyncio
    async def test_manual_provider_charges(self) -> None:
        provider = ManualProvider()
        result = await provider.charge(Decimal("99.00"), "USD", {"invoice_id": "inv-1"})
        assert result.status == "success"
        assert result.transaction_id is not None

    @pytest.mark.asyncio
    async def test_stripe_no_api_key(self) -> None:
        provider = StripeProvider()
        result = await provider.charge(Decimal("99.00"), "USD", {})
        assert result.status == "failed"
        assert "API key" in result.error

    @pytest.mark.asyncio
    async def test_stripe_with_api_key(self) -> None:
        provider = StripeProvider(api_key="sk_test_123")
        result = await provider.charge(Decimal("99.00"), "USD", {})
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_midtrans_no_key(self) -> None:
        provider = MidtransProvider()
        result = await provider.charge(Decimal("99.00"), "IDR", {})
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_xendit_no_key(self) -> None:
        provider = XenditProvider()
        result = await provider.charge(Decimal("99.00"), "IDR", {})
        assert result.status == "failed"


class TestInvoice:

    @pytest.mark.asyncio
    async def test_create_invoice(self) -> None:
        svc = BillingService()
        invoice = await svc.create_invoice("user-1", Decimal("99.00"), "USD", "pro")
        assert invoice.user_id == "user-1"
        assert invoice.amount == Decimal("99.00")
        assert invoice.status == "pending"
        assert svc.get_metrics()["invoices_created"] == 1

    @pytest.mark.asyncio
    async def test_create_invoice_zero_amount(self) -> None:
        svc = BillingService()
        with pytest.raises(ValidationError):
            await svc.create_invoice("user-1", Decimal("0"), "USD", "free")

    @pytest.mark.asyncio
    async def test_get_invoice(self) -> None:
        svc = BillingService()
        invoice = await svc.create_invoice("user-1", Decimal("99.00"), "USD", "pro")
        found = await svc.get_invoice(invoice.id)
        assert found is not None
        assert found.id == invoice.id

    @pytest.mark.asyncio
    async def test_list_invoices(self) -> None:
        svc = BillingService()
        await svc.create_invoice("user-1", Decimal("99.00"), "USD", "pro")
        await svc.create_invoice("user-1", Decimal("29.00"), "USD", "starter")
        await svc.create_invoice("user-2", Decimal("99.00"), "USD", "pro")
        invoices = await svc.list_invoices("user-1")
        assert len(invoices) == 2


class TestProcessPayment:

    @pytest.mark.asyncio
    async def test_process_manual_payment(self) -> None:
        svc = BillingService()
        invoice = await svc.create_invoice("user-1", Decimal("99.00"), "USD", "pro")
        result = await svc.process_payment(invoice.id, "manual")
        assert result.status == "success"
        updated = await svc.get_invoice(invoice.id)
        assert updated.status == "paid"
        assert updated.provider == "manual"
        assert updated.paid_at is not None
        assert svc.get_metrics()["payments_succeeded"] == 1

    @pytest.mark.asyncio
    async def test_process_stripe_no_key(self) -> None:
        svc = BillingService()
        invoice = await svc.create_invoice("user-1", Decimal("99.00"), "USD", "pro")
        result = await svc.process_payment(invoice.id, "stripe")
        assert result.status == "failed"
        updated = await svc.get_invoice(invoice.id)
        assert updated.status == "failed"
        assert svc.get_metrics()["payments_failed"] == 1

    @pytest.mark.asyncio
    async def test_process_unknown_provider(self) -> None:
        svc = BillingService()
        invoice = await svc.create_invoice("user-1", Decimal("99.00"), "USD", "pro")
        with pytest.raises(ValidationError):
            await svc.process_payment(invoice.id, "unknown")

    @pytest.mark.asyncio
    async def test_process_unknown_invoice(self) -> None:
        svc = BillingService()
        with pytest.raises(ValidationError):
            await svc.process_payment("fake-id", "manual")


class TestCancelInvoice:

    @pytest.mark.asyncio
    async def test_cancel_pending(self) -> None:
        svc = BillingService()
        invoice = await svc.create_invoice("user-1", Decimal("99.00"), "USD", "pro")
        assert await svc.cancel_invoice(invoice.id) is True
        assert (await svc.get_invoice(invoice.id)).status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_paid(self) -> None:
        svc = BillingService()
        invoice = await svc.create_invoice("user-1", Decimal("99.00"), "USD", "pro")
        await svc.process_payment(invoice.id, "manual")
        assert await svc.cancel_invoice(invoice.id) is False
