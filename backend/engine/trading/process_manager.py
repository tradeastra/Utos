"""Trading process manager — lifecycle, registry, locking, Redis state."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from core.config import settings
from core.context import ProcessMemory
from core.domain_types import (
    ExchangeAdapterConfig,
    ExchangeCredentials,
    TradingInstanceStatus,
)
from core.exceptions import (
    AuthenticationError,
    ConfigurationError,
    ExchangeAccountNotFound,
    InvalidStateTransition,
    ServiceUnavailable,
    StrategyError,
    SymbolNotSupported,
    TradingInstanceNotFound,
    ValidationError,
)
from core.logging import get_logger
from database.base import get_db
from database.redis_client import get_redis, init_redis
from exchanges.adapter import IExchangeAdapter
from exchanges.credential_manager import CredentialManager
from exchanges.factory import ExchangeFactory
from fastapi import Depends
from models.exchange_account import ExchangeAccount
from models.trading_instance import TradingInstance
from repositories.exchange_account_repository import ExchangeAccountRepository
from repositories.grid_profile_repository import GridProfileRepository
from repositories.strategy_repository import StrategyRepository
from repositories.trading_instance_repository import TradingInstanceRepository
from sqlalchemy.ext.asyncio import AsyncSession

from .process import TradingProcess
from .state_machine import ProcessStateMachine

logger = get_logger(__name__)

WORKER_ID = uuid.uuid4().hex

# In-process registry shared by all manager instances.  Protected by _registry_lock.
_process_registry: dict[uuid.UUID, TradingProcess] = {}
_process_registry_lock: asyncio.Lock = asyncio.Lock()


def _state_key(instance_id: uuid.UUID) -> str:
    return f"process:{instance_id}:state"


def _lock_key(instance_id: uuid.UUID) -> str:
    return f"process:{instance_id}:lock"


class _ProcessStateStore:
    """Abstract-ish Redis-backed state store with an in-memory fallback for tests."""

    def __init__(self, redis: Any | None = None):
        self.redis = redis

    async def _ensure_redis(self) -> Any:
        if self.redis is None:
            client = get_redis()
            if client is None:
                if settings.TESTING:
                    return None
                try:
                    client = await init_redis()
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"Redis init failed, using in-memory fallback: {exc}")
                    return None
            self.redis = client
        return self.redis

    async def get_state(self, instance_id: uuid.UUID) -> dict[str, Any] | None:
        client = await self._ensure_redis()
        if client is None:
            return None
        try:
            raw = await client.get(_state_key(instance_id))
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Redis get_state failed, ignoring: {exc}")
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set_state(self, instance_id: uuid.UUID, state: dict[str, Any]) -> bool:
        client = await self._ensure_redis()
        if client is None:
            return False
        try:
            await client.set(_state_key(instance_id), json.dumps(state, default=str))
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Redis set_state failed, ignoring: {exc}")
            return False

    async def acquire_lock(
        self, instance_id: uuid.UUID, worker_id: str, ttl: int = 60
    ) -> bool:
        client = await self._ensure_redis()
        if client is None:
            return True
        try:
            lock_value = f"{worker_id}:{datetime.now(tz=UTC).isoformat()}"
            acquired = await client.set(_lock_key(instance_id), lock_value, nx=True, ex=ttl)
            return bool(acquired)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Redis acquire_lock failed, allowing: {exc}")
            return True

    async def release_lock(self, instance_id: uuid.UUID) -> bool:
        client = await self._ensure_redis()
        if client is None:
            return True
        try:
            await client.delete(_lock_key(instance_id))
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Redis release_lock failed, ignoring: {exc}")
            return True

    async def refresh_lock(
        self, instance_id: uuid.UUID, worker_id: str, ttl: int = 60
    ) -> bool:
        client = await self._ensure_redis()
        if client is None:
            return True
        try:
            value = await client.get(_lock_key(instance_id))
            if value is None:
                return await self.acquire_lock(instance_id, worker_id, ttl)
            if value.startswith(f"{worker_id}:"):
                await client.set(_lock_key(instance_id), value, ex=ttl, xx=True)
                return True
            return False
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Redis refresh_lock failed, ignoring: {exc}")
            return True


class TradingProcessManager:
    """Manages the full lifecycle of TradingProcess instances."""

    def __init__(
        self,
        session: AsyncSession,
        store: _ProcessStateStore | None = None,
        worker_id: str | None = None,
        credential_manager: CredentialManager | None = None,
    ):
        self.session = session
        self.store = store or _ProcessStateStore()
        self.worker_id = worker_id or WORKER_ID
        self.credential_manager = credential_manager or CredentialManager()
        self.instance_repo = TradingInstanceRepository(session)
        self.account_repo = ExchangeAccountRepository(session)
        self.strategy_repo = StrategyRepository(session)
        self.grid_profile_repo = GridProfileRepository(session)

    # ────────────────────────────────────────────────────────────────
    # Registry helpers
    # ────────────────────────────────────────────────────────────────
    async def _get_process(self, instance_id: uuid.UUID) -> TradingProcess | None:
        async with _process_registry_lock:
            return _process_registry.get(instance_id)

    async def _register(self, process: TradingProcess) -> None:
        async with _process_registry_lock:
            _process_registry[process.instance_id] = process

    async def _unregister(self, instance_id: uuid.UUID) -> None:
        async with _process_registry_lock:
            _process_registry.pop(instance_id, None)

    async def list_active(self) -> list[TradingProcess]:
        async with _process_registry_lock:
            return list(_process_registry.values())

    # ────────────────────────────────────────────────────────────────
    # Persistence helpers
    # ────────────────────────────────────────────────────────────────
    async def _persist_instance(
        self,
        instance: TradingInstance,
        status: TradingInstanceStatus | None = None,
        error_message: str | None = None,
        started_at: datetime | None = None,
        stopped_at: datetime | None = None,
        memory_snapshot: dict[str, Any] | None = None,
        memory_version: int | None = None,
        worker_id: str | None = None,
    ) -> TradingInstance:
        if status is not None:
            instance.status = status
        if error_message is not None:
            instance.error_message = error_message
        if started_at is not None:
            instance.started_at = started_at
        if stopped_at is not None:
            instance.stopped_at = stopped_at
        if memory_snapshot is not None:
            instance.memory_snapshot = memory_snapshot
        if memory_version is not None:
            instance.memory_version = memory_version
        if worker_id is not None:
            instance.worker_id = worker_id
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def _persist_state(self, process: TradingProcess) -> None:
        await self.store.set_state(process.instance_id, process.snapshot())

    # ────────────────────────────────────────────────────────────────
    # Validation helpers
    # ────────────────────────────────────────────────────────────────
    async def _get_instance(self, instance_id: uuid.UUID) -> TradingInstance:
        instance = await self.instance_repo.get_by_id(instance_id)
        if instance is None:
            raise TradingInstanceNotFound(str(instance_id))
        return instance

    async def _validate_ownership(
        self, instance: TradingInstance, user_id: uuid.UUID
    ) -> None:
        if instance.user_id != user_id:
            raise AuthenticationError("Trading instance does not belong to user")

    async def _validate_account(self, account: ExchangeAccount) -> IExchangeAdapter:
        if not account.is_active:
            raise ValidationError("Exchange account is inactive")
        if not ExchangeFactory.is_registered(account.exchange_name.value):
            raise ConfigurationError(f"No adapter for {account.exchange_name.value}")
        adapter = ExchangeFactory.create(account.exchange_name.value)
        return adapter

    async def _validate_symbol(self, adapter: IExchangeAdapter, symbol: str) -> None:
        info = await adapter.get_exchange_info()
        if symbol.upper() not in {s.upper() for s in info.supported_symbols}:
            raise SymbolNotSupported(symbol, adapter.name)

    async def _authenticate_adapter(
        self, adapter: IExchangeAdapter, account: ExchangeAccount
    ) -> None:
        try:
            api_key = self.credential_manager.decrypt(account.api_key_encrypted)
            api_secret = self.credential_manager.decrypt(account.api_secret_encrypted)
        except AuthenticationError as exc:
            raise AuthenticationError("Failed to decrypt exchange credentials") from exc

        credentials = ExchangeCredentials(
            exchange_name=account.exchange_name.value,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=None,
        )
        adapter.name = account.exchange_name.value
        await adapter.initialize(
            ExchangeAdapterConfig(
                exchange_name=account.exchange_name.value,
                is_testnet=account.is_testnet,
            )
        )
        if not await adapter.authenticate(credentials):
            raise AuthenticationError("Exchange authentication failed")

    async def _check_duplicate_running(self, instance: TradingInstance) -> None:
        running = await self.instance_repo.get_by_status(TradingInstanceStatus.RUNNING)
        for other in running:
            if other.id == instance.id:
                continue
            if (
                other.symbol.upper() == instance.symbol.upper()
                and other.exchange_account_id == instance.exchange_account_id
                and other.strategy_id == instance.strategy_id
            ):
                raise ValidationError(
                    "A running process already exists for this symbol, strategy and exchange account"
                )

    async def _build_process_from_instance(
        self, instance: TradingInstance
    ) -> TradingProcess:
        account = await self.account_repo.get_by_id(instance.exchange_account_id)
        if account is None:
            raise ExchangeAccountNotFound(str(instance.exchange_account_id))

        adapter = await self._validate_account(account)
        await self._authenticate_adapter(adapter, account)

        memory_snapshot = instance.memory_snapshot or {}
        if memory_snapshot:
            memory = ProcessMemory.from_dict(memory_snapshot)
        else:
            memory = ProcessMemory(
                instance_id=str(instance.id),
                status=instance.status.value,
            )

        lock_value = f"{self.worker_id}:{datetime.now(tz=UTC).isoformat()}"
        return TradingProcess(
            instance_id=instance.id,
            user_id=instance.user_id,
            exchange_account_id=instance.exchange_account_id,
            strategy_id=instance.strategy_id,
            symbol=instance.symbol,
            exchange_name=account.exchange_name.value,
            status=instance.status,
            adapter=adapter,
            memory=memory,
            worker_id=self.worker_id,
            lock_value=lock_value,
            redis=self.store.redis,
        )

    # ────────────────────────────────────────────────────────────────
    # Lifecycle API
    # ────────────────────────────────────────────────────────────────
    async def create_process(
        self,
        user_id: uuid.UUID,
        exchange_account_id: uuid.UUID,
        strategy_id: uuid.UUID,
        grid_profile_id: uuid.UUID,
        symbol: str,
        start_price: float | None = None,
        total_investment: float = 0.0,
        base_currency: str = "",
        quote_currency: str = "",
        strategy_mode: str | None = None,
        selected_coins: list[str] | None = None,
        continuation_rate: float | None = None,
        breaker_enabled: bool = True,
    ) -> TradingInstance:
        account = await self.account_repo.get_by_id(exchange_account_id)
        if account is None or account.user_id != user_id:
            raise ExchangeAccountNotFound(str(exchange_account_id))
        strategy = await self.strategy_repo.get_by_id(strategy_id)
        if strategy is None:
            raise StrategyError("Strategy not found")
        grid_profile = await self.grid_profile_repo.get_by_id(grid_profile_id)
        if grid_profile is None or grid_profile.user_id != user_id:
            raise ValidationError("Grid profile not found")
        if not ExchangeFactory.is_registered(account.exchange_name.value):
            raise ConfigurationError(f"No adapter for {account.exchange_name.value}")

        instance = await self.instance_repo.create(
            user_id=user_id,
            exchange_account_id=exchange_account_id,
            strategy_id=strategy_id,
            grid_profile_id=grid_profile_id,
            symbol=symbol.upper(),
            status=TradingInstanceStatus.CREATED,
            start_price=start_price or 0.0,
            total_investment=total_investment,
            base_currency=(base_currency or "").upper(),
            quote_currency=(quote_currency or "").upper(),
            strategy_mode=strategy_mode,
            selected_coins=selected_coins,
            continuation_rate=continuation_rate,
            breaker_enabled=breaker_enabled,
        )
        return instance

    async def prepare(
        self, instance_id: uuid.UUID, user_id: uuid.UUID
    ) -> TradingInstance:
        instance = await self._get_instance(instance_id)
        await self._validate_ownership(instance, user_id)
        ProcessStateMachine.validate_transition(
            instance.status, TradingInstanceStatus.READY
        )

        account = await self.account_repo.get_by_id(instance.exchange_account_id)
        if account is None:
            raise ExchangeAccountNotFound(str(instance.exchange_account_id))
        strategy = await self.strategy_repo.get_by_id(instance.strategy_id)
        if strategy is None or not strategy.is_active:
            raise StrategyError("Strategy not found or inactive")

        adapter = await self._validate_account(account)
        await self._authenticate_adapter(adapter, account)
        await self._validate_symbol(adapter, instance.symbol)

        await self._persist_instance(instance, status=TradingInstanceStatus.READY)
        return instance

    async def start(
        self, instance_id: uuid.UUID, user_id: uuid.UUID
    ) -> TradingInstance:
        instance = await self._get_instance(instance_id)
        await self._validate_ownership(instance, user_id)
        ProcessStateMachine.validate_transition(
            instance.status, TradingInstanceStatus.RUNNING
        )

        await self._check_duplicate_running(instance)

        if not await self.store.acquire_lock(instance.id, self.worker_id, ttl=60):
            raise InvalidStateTransition(
                message="Process is already running or locked by another worker",
                current_state=instance.status.value,
                target_state=TradingInstanceStatus.RUNNING.value,
            )

        process = await self._build_process_from_instance(instance)
        process.set_status(TradingInstanceStatus.RUNNING)

        await self._register(process)

        # ── Wire grid engine + market hub + circuit breaker ──────────
        # These are global singletons initialized in main.py lifespan.
        # We import lazily to avoid circular imports and to keep tests
        # working without a running MarketHub/GridEngine.
        await self._wire_grid_and_market(instance, process)

        await self._persist_instance(
            instance,
            status=TradingInstanceStatus.RUNNING,
            started_at=datetime.now(tz=UTC),
            worker_id=self.worker_id,
            memory_snapshot=process.memory.to_dict(),
            memory_version=1,
        )
        await self._persist_state(process)
        return instance

    async def _wire_grid_and_market(
        self, instance: TradingInstance, process: TradingProcess
    ) -> None:
        """Initialize grid, activate it, install circuit breaker, and
        subscribe to MarketHub price updates.

        Failures here are logged but do NOT prevent the bot from starting
        — the grid engine may be unavailable in test environments. The
        subscription id is stored on the process so stop()/pause() can
        unsubscribe cleanly.
        """
        try:
            from main import grid_engine, market_hub
        except ImportError:
            return  # tests / no main module

        if grid_engine is None or market_hub is None:
            return  # not initialized yet

        from decimal import Decimal
        from sqlalchemy import select
        from models.averaging_config import AveragingConfig
        from services.averaging_template import get_default_averaging_template

        # 1. Load grid profile (for investment_per_grid) and averaging config.
        # Auto-trading mode: if the instance has averaging configs (or we fall
        # back to the default template), grid levels are generated from the
        # current market price + per-step drop rates — NOT from a fixed
        # upper/lower price range. This is the correct mode for auto-trading
        # because the bot enters at the current market price and averages down.
        grid_profile = await self.grid_profile_repo.get_by_id(instance.grid_profile_id)
        if grid_profile is None:
            logger.warning(
                "Grid profile not found, skipping grid init",
                extra={"instance_id": str(instance.id), "grid_profile_id": str(instance.grid_profile_id)},
            )
            return

        investment_per_grid = Decimal(str(grid_profile.investment_per_grid))

        # Load per-instance averaging config from DB; fall back to default
        # 35-step template if none configured. This is the auto-trading mode:
        # grid levels are derived from start_price (= market price) + drop
        # rates, so the bot enters at the current price and averages down.
        avg_result = await self.session.execute(
            select(AveragingConfig)
            .where(AveragingConfig.trading_instance_id == instance.id)
            .order_by(AveragingConfig.step_number)
        )
        avg_rows = list(avg_result.scalars().all())
        if avg_rows:
            averaging_steps = [
                {
                    "step_number": r.step_number,
                    "drop_rate": Decimal(str(r.drop_rate)),
                    "multiple_buy_amount": Decimal(str(r.multiple_buy_amount)),
                    "take_profit": Decimal(str(r.take_profit)),
                }
                for r in avg_rows
            ]
        else:
            # No per-instance config → use default 35-step template.
            averaging_steps = get_default_averaging_template()

        try:
            # Fetch current price FIRST — in averaging mode this becomes
            # the start_price (upper_price param) for grid initialization.
            current_price = await market_hub.get_price(
                process.exchange_name, instance.symbol
            )

            await grid_engine.initialize_grid(
                instance_id=str(instance.id),
                exchange_account_id=instance.exchange_account_id,
                symbol=instance.symbol,
                upper_price=current_price,  # start_price = market price
                lower_price=Decimal("0"),   # derived from averaging steps
                grid_count=len(averaging_steps),
                investment_per_grid=investment_per_grid,
                averaging_steps=averaging_steps,
            )

            # 2. Activate grid: place initial buy orders for levels below
            # current price. In averaging mode, step 0 buys at start_price
            # (= current price), so the first entry is at market price.
            await grid_engine.activate_grid(str(instance.id), current_price)

            # 3. Install circuit breaker if enabled.
            if instance.breaker_enabled and instance.continuation_rate is not None:
                from services.breaker_screening_store import BreakerScreeningStore
                breaker_store = BreakerScreeningStore()
                await breaker_store.setup_breaker_for_instance(
                    db=self.session,
                    grid_engine=grid_engine,
                    instance_id=str(instance.id),
                    symbol=instance.symbol,
                    min_continuation_rate=Decimal(str(instance.continuation_rate)),
                    exchange=process.exchange_name,
                    day_open_price=current_price,
                )

            # 4. Subscribe to MarketHub ticker stream → forward to grid engine.
            async def _price_callback(exchange: str, symbol: str, channel: str, data: Any) -> None:
                from core.domain_types import TickerData
                if isinstance(data, TickerData):
                    await grid_engine.on_price_update(
                        str(instance.id), Decimal(str(data.last_price))
                    )

            sub_id = await market_hub.subscribe(
                process.exchange_name, instance.symbol, "ticker", _price_callback
            )
            process.subscription_id = sub_id  # type: ignore[attr-defined]

            logger.info(
                "Grid wired and subscribed to market data",
                extra={
                    "instance_id": str(instance.id),
                    "symbol": instance.symbol,
                    "current_price": str(current_price),
                    "subscription_id": sub_id,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to wire grid/market for instance: %s",
                exc,
                extra={"instance_id": str(instance.id)},
            )

    async def _unwire_grid_and_market(
        self, instance: TradingInstance, process: TradingProcess
    ) -> None:
        """Unsubscribe from MarketHub and pause the grid.

        Called by stop() and pause() so price updates stop flowing to the
        grid engine and open orders are cancelled.
        """
        # Unsubscribe from MarketHub
        sub_id = getattr(process, "subscription_id", None)
        if sub_id is not None:
            try:
                from main import market_hub
                if market_hub is not None:
                    await market_hub.unsubscribe(sub_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to unsubscribe from market hub: %s", exc,
                    extra={"instance_id": str(instance.id), "subscription_id": sub_id},
                )
            process.subscription_id = None  # type: ignore[attr-defined]

        # Pause grid (cancel open orders)
        try:
            from main import grid_engine
            if grid_engine is not None:
                await grid_engine.pause_grid(str(instance.id))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to pause grid: %s", exc,
                extra={"instance_id": str(instance.id)},
            )

    async def pause(
        self, instance_id: uuid.UUID, user_id: uuid.UUID
    ) -> TradingInstance:
        instance = await self._get_instance(instance_id)
        await self._validate_ownership(instance, user_id)
        ProcessStateMachine.validate_transition(
            instance.status, TradingInstanceStatus.PAUSED
        )

        process = await self._get_process(instance.id)
        if process is None:
            process = await self._build_process_from_instance(instance)
            await self._register(process)

        await self._unwire_grid_and_market(instance, process)
        process.set_status(TradingInstanceStatus.PAUSED)
        await self._persist_instance(
            instance,
            status=TradingInstanceStatus.PAUSED,
            memory_snapshot=process.memory.to_dict(),
        )
        await self._persist_state(process)
        await self.store.release_lock(instance.id)
        return instance

    async def resume(
        self, instance_id: uuid.UUID, user_id: uuid.UUID
    ) -> TradingInstance:
        instance = await self._get_instance(instance_id)
        await self._validate_ownership(instance, user_id)
        ProcessStateMachine.validate_transition(
            instance.status, TradingInstanceStatus.RUNNING
        )

        await self.store.release_lock(instance.id)
        if not await self.store.acquire_lock(instance.id, self.worker_id, ttl=60):
            raise InvalidStateTransition(
                message="Cannot resume process; lock is held by another worker",
                current_state=instance.status.value,
                target_state=TradingInstanceStatus.RUNNING.value,
            )

        process = await self._get_process(instance.id)
        if process is None:
            process = await self._build_process_from_instance(instance)
            await self._register(process)

        process.set_status(TradingInstanceStatus.RUNNING)
        await self._persist_instance(
            instance,
            status=TradingInstanceStatus.RUNNING,
            memory_snapshot=process.memory.to_dict(),
        )
        await self._persist_state(process)
        return instance

    async def stop(self, instance_id: uuid.UUID, user_id: uuid.UUID) -> TradingInstance:
        instance = await self._get_instance(instance_id)
        await self._validate_ownership(instance, user_id)
        ProcessStateMachine.validate_transition(
            instance.status, TradingInstanceStatus.STOPPING
        )

        instance.status = TradingInstanceStatus.STOPPING
        await self.session.flush()

        process = await self._get_process(instance.id)
        if process is not None:
            process.set_status(TradingInstanceStatus.STOPPING)
            await self._unwire_grid_and_market(instance, process)
            try:
                await process.adapter.disconnect()
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Adapter disconnect failed during stop: {exc}")

        await self.store.release_lock(instance.id)
        await self._unregister(instance.id)

        await self._persist_instance(
            instance,
            status=TradingInstanceStatus.STOPPED,
            stopped_at=datetime.now(tz=UTC),
            memory_snapshot=(
                process.memory.to_dict() if process else instance.memory_snapshot
            ),
        )
        await self.store.set_state(
            instance.id,
            {
                "instance_id": str(instance.id),
                "status": TradingInstanceStatus.STOPPED.value,
                "worker_id": self.worker_id,
                "updated_at": datetime.now(tz=UTC).isoformat(),
            },
        )
        return instance

    async def recover(self) -> list[TradingInstance]:
        """Recover RUNNING/PAUSED processes after application restart."""
        recovered: list[TradingInstance] = []
        for status in (
            TradingInstanceStatus.RUNNING,
            TradingInstanceStatus.PAUSED,
            TradingInstanceStatus.RECOVERING,
        ):
            instances = await self.instance_repo.get_by_status(status)
            for instance in instances:
                try:
                    await self._recover_instance(instance)
                    recovered.append(instance)
                except Exception as exc:  # noqa: BLE001
                    logger.error(f"Failed to recover instance {instance.id}: {exc}")
                    await self._persist_instance(
                        instance,
                        status=TradingInstanceStatus.ERROR,
                        error_message=str(exc),
                    )
        return recovered

    async def _recover_instance(self, instance: TradingInstance) -> None:
        ProcessStateMachine.validate_transition(
            instance.status, TradingInstanceStatus.RECOVERING
        )

        previous_status = instance.status
        if not await self.store.acquire_lock(instance.id, self.worker_id, ttl=60):
            current_lock = (
                await self.store.redis.get(_lock_key(instance.id))
                if self.store.redis
                else None
            )
            if current_lock and not current_lock.startswith(
                f"{self.worker_id}:".encode()
            ):
                await self._persist_instance(
                    instance,
                    status=TradingInstanceStatus.ERROR,
                    error_message="Split-brain: process locked by another worker",
                )
                return

        process = await self._build_process_from_instance(instance)

        if not await process.adapter.health_check():
            await self._persist_instance(
                instance,
                status=TradingInstanceStatus.ERROR,
                error_message="Exchange health check failed during recovery",
            )
            return

        try:
            await self._validate_symbol(process.adapter, instance.symbol)
        except SymbolNotSupported:
            await self._persist_instance(
                instance,
                status=TradingInstanceStatus.ERROR,
                error_message=f"Symbol {instance.symbol} no longer supported on {process.exchange_name}",
            )
            return

        process.set_status(TradingInstanceStatus.RECOVERING)
        await self._persist_instance(
            instance,
            status=TradingInstanceStatus.RECOVERING,
            worker_id=self.worker_id,
            memory_snapshot=process.memory.to_dict(),
        )

        if previous_status in (
            TradingInstanceStatus.RUNNING,
            TradingInstanceStatus.RECOVERING,
        ):
            process.set_status(TradingInstanceStatus.RUNNING)
            final_status = TradingInstanceStatus.RUNNING
        else:
            process.set_status(TradingInstanceStatus.PAUSED)
            final_status = TradingInstanceStatus.PAUSED

        await self._persist_instance(
            instance,
            status=final_status,
            memory_snapshot=process.memory.to_dict(),
        )
        await self._persist_state(process)
        await self._register(process)

    async def get_status(
        self, instance_id: uuid.UUID, user_id: uuid.UUID
    ) -> TradingInstance:
        instance = await self._get_instance(instance_id)
        await self._validate_ownership(instance, user_id)
        return instance

    async def list_by_user(self, user_id: uuid.UUID) -> list[TradingInstance]:
        return await self.instance_repo.get_by_user_id(user_id)


async def get_process_manager(
    session: AsyncSession = Depends(get_db),
) -> TradingProcessManager:
    """FastAPI dependency for a TradingProcessManager."""
    redis = get_redis()
    if redis is None and not settings.TESTING:
        redis = await init_redis()
    if redis is None and not settings.TESTING:
        raise ServiceUnavailable("redis")
    store = _ProcessStateStore(redis)
    return TradingProcessManager(session, store=store)
