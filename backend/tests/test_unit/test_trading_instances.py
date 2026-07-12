"""Integration tests for trading instance endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_trading_instance(trading_client: AsyncClient, create_trading_instance, db_session, test_user) -> None:
    instance = await create_trading_instance(db_session, user=test_user)
    payload = {
        "exchange_account_id": str(instance.exchange_account_id),
        "strategy_id": str(instance.strategy_id),
        "grid_profile_id": str(instance.grid_profile_id),
        "symbol": "ETHUSDT",
        "total_investment": 500.0,
        "base_currency": "ETH",
        "quote_currency": "USDT",
    }
    response = await trading_client.post("/api/v1/trading-instances", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["symbol"] == "ETHUSDT"
    assert data["status"] == "created"


@pytest.mark.asyncio
async def test_list_trading_instances(trading_client: AsyncClient, create_trading_instance, db_session, test_user) -> None:
    instance = await create_trading_instance(db_session, user=test_user)
    response = await trading_client.get("/api/v1/trading-instances")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(instance.id)


@pytest.mark.asyncio
async def test_get_trading_instance(trading_client: AsyncClient, create_trading_instance, db_session, test_user) -> None:
    instance = await create_trading_instance(db_session, user=test_user)
    response = await trading_client.get(f"/api/v1/trading-instances/{instance.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(instance.id)


@pytest.mark.asyncio
async def test_prepare_and_start_trading_instance(trading_client: AsyncClient, create_trading_instance, db_session, test_user) -> None:
    instance = await create_trading_instance(db_session, user=test_user)
    response = await trading_client.post(f"/api/v1/trading-instances/{instance.id}/prepare")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"

    response = await trading_client.post(f"/api/v1/trading-instances/{instance.id}/start")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_start_requires_prepare(trading_client: AsyncClient, create_trading_instance, db_session, test_user) -> None:
    instance = await create_trading_instance(db_session, user=test_user)
    response = await trading_client.post(f"/api/v1/trading-instances/{instance.id}/start")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_pause_resume_stop_trading_instance(trading_client: AsyncClient, create_trading_instance, db_session, test_user) -> None:
    instance = await create_trading_instance(db_session, user=test_user)
    await trading_client.post(f"/api/v1/trading-instances/{instance.id}/prepare")
    await trading_client.post(f"/api/v1/trading-instances/{instance.id}/start")

    response = await trading_client.post(f"/api/v1/trading-instances/{instance.id}/pause")
    assert response.status_code == 200
    assert response.json()["status"] == "paused"

    response = await trading_client.post(f"/api/v1/trading-instances/{instance.id}/resume")
    assert response.status_code == 200
    assert response.json()["status"] == "running"

    response = await trading_client.post(f"/api/v1/trading-instances/{instance.id}/stop")
    assert response.status_code == 200
    assert response.json()["status"] == "stopped"


@pytest.mark.asyncio
async def test_delete_stopped_instance(trading_client: AsyncClient, create_trading_instance, db_session, test_user) -> None:
    instance = await create_trading_instance(db_session, user=test_user)
    await trading_client.post(f"/api/v1/trading-instances/{instance.id}/prepare")
    await trading_client.post(f"/api/v1/trading-instances/{instance.id}/start")
    await trading_client.post(f"/api/v1/trading-instances/{instance.id}/stop")
    response = await trading_client.delete(f"/api/v1/trading-instances/{instance.id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_cannot_delete_running_instance(trading_client: AsyncClient, create_trading_instance, db_session, test_user) -> None:
    instance = await create_trading_instance(db_session, user=test_user)
    await trading_client.post(f"/api/v1/trading-instances/{instance.id}/prepare")
    await trading_client.post(f"/api/v1/trading-instances/{instance.id}/start")
    response = await trading_client.delete(f"/api/v1/trading-instances/{instance.id}")
    assert response.status_code == 400
