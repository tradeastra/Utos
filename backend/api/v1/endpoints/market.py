"""
Market data API endpoints.

These endpoints expose the MarketHub's cached data to external consumers.
All data is served from in-memory cache; fallback to adapter REST fetch
happens transparently inside the hub.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from core.exceptions import SymbolNotSupported
from market.hub.market_hub import MarketHub

router = APIRouter()


def _get_hub() -> MarketHub:
    """Return the singleton MarketHub instance."""
    from main import market_hub

    if market_hub is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market Hub is not initialized",
        )
    return market_hub


class TickerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    bid: str
    ask: str
    last: str
    volume: str
    timestamp: str


class OrderBookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    bids: list[list[str]]
    asks: list[list[str]]
    timestamp: str


class CandleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    interval: str
    open: str
    high: str
    low: str
    close: str
    volume: str
    timestamp: str


class PriceResponse(BaseModel):
    exchange: str
    symbol: str
    price: str


class StatusResponse(BaseModel):
    exchange: str
    symbol: str
    status: str
    is_alive: bool


class MetricsResponse(BaseModel):
    exchange: str
    symbol: str
    last_update: str | None
    latency_ms: float
    reconnect_count: int
    dropped_messages: int
    message_rate: float
    status: str


class SymbolsResponse(BaseModel):
    exchange: str
    symbols: list[str]


class HubSnapshotResponse(BaseModel):
    running: bool
    active_logical_subscriptions: int
    active_websocket_subscriptions: int
    consumer_subscriptions: int
    cache_entries: int
    exchanges: list[str]
    avg_latency_ms: float


def _ticker_to_response(t: Any) -> TickerResponse:
    return TickerResponse(
        symbol=t.symbol,
        bid=str(t.bid),
        ask=str(t.ask),
        last=str(t.last),
        volume=str(t.volume),
        timestamp=t.timestamp.isoformat() if hasattr(t.timestamp, "isoformat") else str(t.timestamp),
    )


def _orderbook_to_response(ob: Any) -> OrderBookResponse:
    return OrderBookResponse(
        symbol=ob.symbol,
        bids=[[str(p), str(q)] for p, q in ob.bids],
        asks=[[str(p), str(q)] for p, q in ob.asks],
        timestamp=ob.timestamp.isoformat() if hasattr(ob.timestamp, "isoformat") else str(ob.timestamp),
    )


def _candle_to_response(c: Any) -> CandleResponse:
    return CandleResponse(
        symbol=c.symbol,
        interval=c.interval,
        open=str(c.open),
        high=str(c.high),
        low=str(c.low),
        close=str(c.close),
        volume=str(c.volume),
        timestamp=c.timestamp.isoformat() if hasattr(c.timestamp, "isoformat") else str(c.timestamp),
    )


@router.get("/price/{exchange}/{symbol}", response_model=PriceResponse)
async def get_price(exchange: str, symbol: str) -> PriceResponse:
    hub = _get_hub()
    try:
        price = await hub.get_price(exchange, symbol)
        return PriceResponse(exchange=exchange.lower(), symbol=symbol.upper(), price=str(price))
    except SymbolNotSupported:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Symbol {symbol} not found on {exchange}")


@router.get("/ticker/{exchange}/{symbol}", response_model=TickerResponse)
async def get_ticker(exchange: str, symbol: str) -> TickerResponse:
    hub = _get_hub()
    try:
        ticker = await hub.get_ticker(exchange, symbol)
        return _ticker_to_response(ticker)
    except SymbolNotSupported:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Symbol {symbol} not found on {exchange}")


@router.get("/orderbook/{exchange}/{symbol}", response_model=OrderBookResponse)
async def get_orderbook(exchange: str, symbol: str) -> OrderBookResponse:
    hub = _get_hub()
    try:
        ob = await hub.get_orderbook(exchange, symbol)
        return _orderbook_to_response(ob)
    except SymbolNotSupported:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Symbol {symbol} not found on {exchange}")


@router.get("/candles/{exchange}/{symbol}", response_model=list[CandleResponse])
async def get_candles(
    exchange: str,
    symbol: str,
    interval: str = Query("1m", description="Candle interval (1m, 5m, 15m, 1h, 4h, 1d)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum candles to return"),
) -> list[CandleResponse]:
    hub = _get_hub()
    try:
        candles = await hub.get_candles(exchange, symbol, interval)
        return [_candle_to_response(c) for c in candles[:limit]]
    except SymbolNotSupported:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Symbol {symbol} not found on {exchange}")


@router.get("/symbols/{exchange}", response_model=SymbolsResponse)
async def get_symbols(exchange: str) -> SymbolsResponse:
    hub = _get_hub()
    symbols = hub.symbols.get_symbols(exchange)
    return SymbolsResponse(exchange=exchange.lower(), symbols=symbols)


@router.get("/status/{exchange}/{symbol}", response_model=StatusResponse)
async def get_status(exchange: str, symbol: str) -> StatusResponse:
    hub = _get_hub()
    market_status = await hub.get_status(exchange, symbol)
    alive = await hub.is_alive(exchange, symbol)
    return StatusResponse(
        exchange=exchange.lower(),
        symbol=symbol.upper(),
        status=market_status.value,
        is_alive=alive,
    )


@router.get("/metrics/{exchange}/{symbol}", response_model=MetricsResponse)
async def get_metrics(exchange: str, symbol: str) -> MetricsResponse:
    hub = _get_hub()
    m = await hub.get_metrics(exchange, symbol)
    return MetricsResponse(
        exchange=m.exchange,
        symbol=m.symbol,
        last_update=m.last_update.isoformat() if m.last_update else None,
        latency_ms=round(m.latency_ms, 3),
        reconnect_count=m.reconnect_count,
        dropped_messages=m.dropped_messages,
        message_rate=round(m.message_rate, 3),
        status=m.status.value,
    )


@router.get("/snapshot", response_model=HubSnapshotResponse)
async def get_hub_snapshot() -> HubSnapshotResponse:
    hub = _get_hub()
    snap = hub.snapshot()
    return HubSnapshotResponse(**snap)
