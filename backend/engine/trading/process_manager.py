"""Trading process manager — lifecycle, registry, locking, Redis state."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.context import ProcessMemory
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
from core.types import ExchangeAdapterConfig, ExchangeCredentials, TradingInstanceStatus
from database.base import get_db
from database.redis_client import get_redis, init_redis
from exchanges.adapter import IExchangeAdapter
from exchanges.credential_manager import CredentialManager
from exchanges.factory import ExchangeFactory
from models.exchange_account import ExchangeAccount
from models.grid_profile import GridProfile
from models.strategy import Strategy
from models.trading_instance import TradingInstance
from repositories.exchange_account_repository import ExchangeAccountRepository
from repositories.grid_profile_repository import GridProfileRepository
from repositories.strategy_repository import StrategyRepository
from repositories.trading_instance_repository import TradingInstanceRepository

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
                client = await init_redis()
            self.redis = client
        return self.redis

    async def get_state(self, instance_id: uuid.UUID) -> dict[str, Any] | None:
        client = await self._ensure_redis()
        if client is None:
            return None
        raw = await client.get(_state_key(instance_id))
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
        await client.set(_state_key(instance_id), json.dumps(state, default=str))
        return True

    async def acquire_lock(
        self, instance_id: uuid.UUID, worker_id: str, ttl: int = 60
    ) -> bool:
        client = await self._ensure_redis()
        if client is None:
            return True
        lock_value = f"{worker_id}:{datetime.now(tz=timezone.utc).isoformat()}"
        acquired = await client.set(_lock_key(instance_id), lock_value, nx=True, ex=ttl)
        return bool(acquired)

    async def release_lock(self, instance_id: uuid.UUID) -> bool:
        client = await self._ensure_redis()
        if client is None:
            return True
        await client.delete(_lock_key(instance_id))
        return True

    async def refresh_lock(
        self, instance_id: uuid.UUID, worker_id: str, ttl: int = 60
    ) -> bool:
        client = await self._ensure_redis()
        if client is None:
            return True
        value = await client.get(_lock_key(instance_id))
        if value is None:
            return await self.acquire_lock(instance_id, worker_id, ttl)
        if value.startswith(f"{worker_id}:"):
            await client.set(_lock_key(instance_id), value, ex=ttl, xx=True)
            return True
        return False


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

        lock_value = f"{self.worker_id}:{datetime.now(tz=timezone.utc).isoformat()}"
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
        )
        return instance

    async def prepare(self, instance_id: uuid.UUID, user_id: uuid.UUID) -> TradingInstance:
        instance = await self._get_instance(instance_id)
        await self._validate_ownership(instance, user_id)
        ProcessStateMachine.validate_transition(instance.status, TradingInstanceStatus.READY)

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

    async def start(self, instance_id: uuid.UUID, user_id: uuid.UUID) -> TradingInstance:
        instance = await self._get_instance(instance_id)
        await self._validate_ownership(instance, user_id)
        ProcessStateMachine.validate_transition(instance.status, TradingInstanceStatus.RUNNING)

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
        await self._persist_instance(
            instance,
            status=TradingInstanceStatus.RUNNING,
            started_at=datetime.now(tz=timezone.utc),
            worker_id=self.worker_id,
            memory_snapshot=process.memory.to_dict(),
            memory_version=1,
        )
        await self._persist_state(process)
        return instance

    async def pause(self, instance_id: uuid.UUID, user_id: uuid.UUID) -> TradingInstance:
        instance = await self._get_instance(instance_id)
        await self._validate_ownership(instance, user_id)
        ProcessStateMachine.validate_transition(instance.status, TradingInstanceStatus.PAUSED)

        process = await self._get_process(instance.id)
        if process is None:
            process = await self._build_process_from_instance(instance)
            await self._register(process)

        process.set_status(TradingInstanceStatus.PAUSED)
        await self._persist_instance(
            instance,
            status=TradingInstanceStatus.PAUSED,
            memory_snapshot=process.memory.to_dict(),
        )
        await self._persist_state(process)
        return instance

    async def resume(self, instance_id: uuid.UUID, user_id: uuid.UUID) -> TradingInstance:
        instance = await self._get_instance(instance_id)
        await self._validate_ownership(instance, user_id)
        ProcessStateMachine.validate_transition(instance.status, TradingInstanceStatus.RUNNING)

        if not await self.store.refresh_lock(instance.id, self.worker_id, ttl=60):
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
        ProcessStateMachine.validate_transition(instance.status, TradingInstanceStatus.STOPPING)

        instance.status = TradingInstanceStatus.STOPPING
        await self.session.flush()

        process = await self._get_process(instance.id)
        if process is not None:
            process.set_status(TradingInstanceStatus.STOPPING)
            try:
                await process.adapter.disconnect()
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Adapter disconnect failed during stop: {exc}")

        await self.store.release_lock(instance.id)
        await self._unregister(instance.id)

        await self._persist_instance(
            instance,
            status=TradingInstanceStatus.STOPPED,
            stopped_at=datetime.now(tz=timezone.utc),
            memory_snapshot=process.memory.to_dict() if process else instance.memory_snapshot,
        )
        await self.store.set_state(
            instance.id,
            {
                "instance_id": str(instance.id),
                "status": TradingInstanceStatus.STOPPED.value,
                "worker_id": self.worker_id,
                "updated_at": datetime.now(tz=timezone.utc).isoformat(),
            },
        )
        return instance

    async def recover(self) -> list[TradingInstance]:
        """Recover RUNNING/PAUSED processes after application restart."""
        recovered: list[TradingInstance] = []
        for status in (TradingInstanceStatus.RUNNING, TradingInstanceStatus.PAUSED, TradingInstanceStatus.RECOVERING):
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
        ProcessStateMachine.validate_transition(instance.status, TradingInstanceStatus.RECOVERING)

        previous_status = instance.status
        if not await self.store.acquire_lock(instance.id, self.worker_id, ttl=60):
            current_lock = await self.store.redis.get(_lock_key(instance.id)) if self.store.redis else None
            if current_lock and not current_lock.startswith(f"{self.worker_id}:".encode()):
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

        if previous_status in (TradingInstanceStatus.RUNNING, TradingInstanceStatus.RECOVERING):
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

    async def get_status(self, instance_id: uuid.UUID, user_id: uuid.UUID) -> TradingInstance:
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
