"""
Repository unit tests for Sprint 2.

Tests CRUD operations for all 12 repositories using the test database.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from models import (
    User,
    ExchangeAccount,
    TradingInstance,
    Position,
    Order,
    GridProfile,
    Strategy,
    Transaction,
    Subscription,
    Affiliate,
    Notification,
    Balance,
)
from models.exchange_account import ExchangeName
from models.notification import NotificationType
from models.user import SubscriptionTier, UserRole
from core.types import (
    TradingInstanceStatus,
    StrategyType,
    OrderSide,
    OrderType,
    OrderStatus,
    PositionSide,
    TransactionType,
)
from repositories import (
    UserRepository,
    ExchangeAccountRepository,
    TradingInstanceRepository,
    PositionRepository,
    OrderRepository,
    GridProfileRepository,
    StrategyRepository,
    TransactionRepository,
    SubscriptionRepository,
    AffiliateRepository,
    NotificationRepository,
    BalanceRepository,
)


@pytest.mark.unit
class TestUserRepository:
    async def test_create_and_get_by_id(self, db_session):
        repo = UserRepository(db_session)
        user = await repo.create(
            email="test@example.com",
            password_hash="hashedpass",
            full_name="Test User",
        )
        assert user.id is not None
        assert user.email == "test@example.com"

        fetched = await repo.get_by_id(user.id)
        assert fetched is not None
        assert fetched.email == "test@example.com"

    async def test_get_by_email(self, db_session):
        repo = UserRepository(db_session)
        await repo.create(
            email="alice@example.com",
            password_hash="hashedpass",
        )
        found = await repo.get_by_email("alice@example.com")
        assert found is not None
        assert found.email == "alice@example.com"

    async def test_exists_by_email(self, db_session):
        repo = UserRepository(db_session)
        await repo.create(
            email="bob@example.com",
            password_hash="hashedpass",
        )
        assert await repo.exists_by_email("bob@example.com") is True
        assert await repo.exists_by_email("nobody@example.com") is False

    async def test_update_user(self, db_session):
        repo = UserRepository(db_session)
        user = await repo.create(
            email="update@example.com",
            password_hash="hashedpass",
        )
        updated = await repo.update(user, full_name="Updated Name")
        assert updated.full_name == "Updated Name"

    async def test_delete_user(self, db_session):
        repo = UserRepository(db_session)
        user = await repo.create(
            email="delete@example.com",
            password_hash="hashedpass",
        )
        await repo.delete(user)
        fetched = await repo.get_by_id(user.id)
        assert fetched is None

    async def test_count(self, db_session):
        repo = UserRepository(db_session)
        initial = await repo.count()
        await repo.create(email="count1@example.com", password_hash="x")
        await repo.create(email="count2@example.com", password_hash="x")
        assert await repo.count() == initial + 2


@pytest.mark.unit
class TestStrategyRepository:
    async def test_create_and_get_by_name(self, db_session):
        repo = StrategyRepository(db_session)
        strategy = await repo.create(
            name="Smart Grid",
            type=StrategyType.SMART_GRID,
            min_investment=Decimal("100"),
            is_active=True,
        )
        found = await repo.get_by_name("Smart Grid")
        assert found is not None
        assert found.id == strategy.id

    async def test_get_active(self, db_session):
        repo = StrategyRepository(db_session)
        await repo.create(
            name="Active Strategy",
            type=StrategyType.DCA,
            min_investment=Decimal("50"),
            is_active=True,
        )
        await repo.create(
            name="Inactive Strategy",
            type=StrategyType.INFINITY_GRID,
            min_investment=Decimal("200"),
            is_active=False,
        )
        active = await repo.get_active()
        assert len(active) == 1
        assert active[0].name == "Active Strategy"


@pytest.mark.unit
class TestGridProfileRepository:
    async def test_create_and_get_by_user(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create(email="grid@example.com", password_hash="x")

        repo = GridProfileRepository(db_session)
        await repo.create(
            user_id=user.id,
            name="My Grid",
            strategy_type=StrategyType.SMART_GRID,
            upper_price=Decimal("50000"),
            lower_price=Decimal("40000"),
            grid_count=10,
            investment_per_grid=Decimal("100"),
        )
        profiles = await repo.get_by_user_id(user.id)
        assert len(profiles) == 1
        assert profiles[0].name == "My Grid"


@pytest.mark.unit
class TestExchangeAccountRepository:
    async def test_create_and_get_by_user(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create(email="ex@example.com", password_hash="x")

        repo = ExchangeAccountRepository(db_session)
        await repo.create(
            user_id=user.id,
            exchange_name=ExchangeName.BINANCE,
            account_name="Binance Main",
            api_key_encrypted="encrypted_key",
            api_secret_encrypted="encrypted_secret",
        )
        accounts = await repo.get_by_user_id(user.id)
        assert len(accounts) == 1
        assert accounts[0].account_name == "Binance Main"


@pytest.mark.unit
class TestTradingInstanceRepository:
    async def _create_full_setup(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create(email="ti@example.com", password_hash="x")

        ea_repo = ExchangeAccountRepository(db_session)
        ea = await ea_repo.create(
            user_id=user.id,
            exchange_name=ExchangeName.BINANCE,
            account_name="Binance",
            api_key_encrypted="k",
            api_secret_encrypted="s",
        )

        strat_repo = StrategyRepository(db_session)
        strategy = await strat_repo.create(
            name="TI Strategy",
            type=StrategyType.SMART_GRID,
            min_investment=Decimal("100"),
        )

        gp_repo = GridProfileRepository(db_session)
        gp = await gp_repo.create(
            user_id=user.id,
            name="TI Grid",
            strategy_type=StrategyType.SMART_GRID,
            upper_price=Decimal("50000"),
            lower_price=Decimal("40000"),
            grid_count=10,
            investment_per_grid=Decimal("100"),
        )
        return user, ea, strategy, gp

    async def test_create_and_get_by_user(self, db_session):
        user, ea, strategy, gp = await self._create_full_setup(db_session)
        repo = TradingInstanceRepository(db_session)
        instance = await repo.create(
            user_id=user.id,
            exchange_account_id=ea.id,
            strategy_id=strategy.id,
            grid_profile_id=gp.id,
            symbol="BTCUSDT",
            status=TradingInstanceStatus.CREATED,
            start_price=Decimal("45000"),
            total_investment=Decimal("1000"),
            base_currency="BTC",
            quote_currency="USDT",
        )
        assert instance.id is not None
        instances = await repo.get_by_user_id(user.id)
        assert len(instances) == 1

    async def test_get_by_status(self, db_session):
        user, ea, strategy, gp = await self._create_full_setup(db_session)
        repo = TradingInstanceRepository(db_session)
        await repo.create(
            user_id=user.id,
            exchange_account_id=ea.id,
            strategy_id=strategy.id,
            grid_profile_id=gp.id,
            symbol="BTCUSDT",
            status=TradingInstanceStatus.RUNNING,
            start_price=Decimal("45000"),
            total_investment=Decimal("1000"),
            base_currency="BTC",
            quote_currency="USDT",
        )
        running = await repo.get_by_status(TradingInstanceStatus.RUNNING)
        assert len(running) == 1


@pytest.mark.unit
class TestPositionRepository:
    async def test_get_by_trading_instance(self, db_session, create_trading_instance):
        instance = await create_trading_instance(db_session)
        repo = PositionRepository(db_session)
        await repo.create(
            trading_instance_id=instance.id,
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            entry_price=Decimal("45000"),
            quantity=Decimal("0.1"),
            value=Decimal("4500"),
        )
        positions = await repo.get_by_trading_instance(instance.id)
        assert len(positions) == 1


@pytest.mark.unit
class TestOrderRepository:
    async def test_create_and_get_by_user(self, db_session, create_trading_instance):
        instance = await create_trading_instance(db_session)
        repo = OrderRepository(db_session)
        await repo.create(
            user_id=instance.user_id,
            exchange_account_id=instance.exchange_account_id,
            trading_instance_id=instance.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
            status=OrderStatus.PENDING,
        )
        orders = await repo.get_by_user_id(instance.user_id)
        assert len(orders) == 1


@pytest.mark.unit
class TestTransactionRepository:
    async def test_create_and_get_by_user(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create(email="tx@example.com", password_hash="x")

        repo = TransactionRepository(db_session)
        await repo.create(
            user_id=user.id,
            type=TransactionType.DEPOSIT,
            amount=Decimal("1000"),
            currency="USDT",
            status="pending",
        )
        txns = await repo.get_by_user_id(user.id)
        assert len(txns) == 1


@pytest.mark.unit
class TestSubscriptionRepository:
    async def test_create_and_get_by_user(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create(email="sub@example.com", password_hash="x")

        repo = SubscriptionRepository(db_session)
        await repo.create(
            user_id=user.id,
            tier=SubscriptionTier.PRO,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 8, 1),
        )
        sub = await repo.get_by_user_id(user.id)
        assert sub is not None
        assert sub.tier == SubscriptionTier.PRO


@pytest.mark.unit
class TestAffiliateRepository:
    async def test_create_and_get_by_user(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create(email="aff@example.com", password_hash="x")

        repo = AffiliateRepository(db_session)
        await repo.create(
            user_id=user.id,
            commission_rate=Decimal("10.00"),
        )
        aff = await repo.get_by_user_id(user.id)
        assert aff is not None
        assert aff.commission_rate == Decimal("10.00")


@pytest.mark.unit
class TestNotificationRepository:
    async def test_create_and_get_unread(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create(email="notif@example.com", password_hash="x")

        repo = NotificationRepository(db_session)
        await repo.create(
            user_id=user.id,
            type=NotificationType.SYSTEM,
            title="Welcome",
            message="Welcome to UTOS",
        )
        unread = await repo.get_unread(user.id)
        assert len(unread) == 1
        assert unread[0].is_read is False


@pytest.mark.unit
class TestBalanceRepository:
    async def test_create_and_get_by_account(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create(email="bal@example.com", password_hash="x")

        ea_repo = ExchangeAccountRepository(db_session)
        ea = await ea_repo.create(
            user_id=user.id,
            exchange_name=ExchangeName.BINANCE,
            account_name="Binance",
            api_key_encrypted="k",
            api_secret_encrypted="s",
        )

        repo = BalanceRepository(db_session)
        await repo.create(
            exchange_account_id=ea.id,
            currency="USDT",
            available=Decimal("1000"),
            locked=Decimal("0"),
            total=Decimal("1000"),
        )
        balances = await repo.get_by_exchange_account(ea.id)
        assert len(balances) == 1
        assert balances[0].currency == "USDT"

    async def test_get_by_account_and_currency(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create(email="bal2@example.com", password_hash="x")

        ea_repo = ExchangeAccountRepository(db_session)
        ea = await ea_repo.create(
            user_id=user.id,
            exchange_name=ExchangeName.BINANCE,
            account_name="Binance",
            api_key_encrypted="k",
            api_secret_encrypted="s",
        )

        repo = BalanceRepository(db_session)
        await repo.create(
            exchange_account_id=ea.id,
            currency="BTC",
            available=Decimal("0.5"),
            locked=Decimal("0"),
            total=Decimal("0.5"),
        )
        bal = await repo.get_by_account_and_currency(ea.id, "BTC")
        assert bal is not None
        assert bal.currency == "BTC"
