# TESTING STANDARD

**Version:** 2.0.0  
**Last Updated:** 2026-07-09  
**Status:** DRAFT

---

## 1. OVERVIEW

This document defines the testing strategy for the UTOS Trading Engine. Testing is mandatory — no code is merged without tests.

### 1.1 Testing Pyramid

```
        ┌─────────┐
        │   E2E   │  ~5%   (Playwright)
        └─────────┘
       ┌───────────┐
       │ Integration│  ~20%  (pytest + test DB)
       └───────────┘
      ┌───────────────┐
      │  Unit Tests   │  ~75%  (pytest, vitest)
      └───────────────┘
```

### 1.2 Coverage Requirements

| Layer | Minimum Coverage |
|-------|-----------------|
| `core/` | 95% |
| `engine/` | 90% |
| `adapters/` | 85% |
| `api/` | 80% |
| `repositories/` | 85% |
| `strategies/` | 90% |
| `workers/` | 80% |
| `services/` | 85% |
| `utils/` | 100% |
| `frontend/` | 70% |

### 1.3 CI Gate

- All tests must pass before merge
- Coverage must not drop below minimum
- No new code without tests
- Linting must pass (ruff, eslint)

---

## 2. BACKEND TESTING

### 2.1 Tools

| Tool | Purpose |
|------|---------|
| `pytest` | Test runner |
| `pytest-asyncio` | Async test support |
| `pytest-cov` | Coverage reporting |
| `pytest-mock` | Mocking |
| `factory-boy` | Test data factories |
| `freezegun` | Time mocking |
| `httpx` | API testing (AsyncClient) |
| `testcontainers` | Integration test DB/Redis |

### 2.2 Test Structure

```
tests/
├── unit/                     # Unit tests (no external dependencies)
│   ├── core/
│   │   ├── test_security.py
│   │   ├── test_config.py
│   │   └── test_logger.py
│   ├── engine/
│   │   ├── test_trading_engine.py
│   │   ├── test_grid_engine.py
│   │   ├── test_execution_engine.py
│   │   ├── test_portfolio_engine.py
│   │   ├── test_risk_engine.py
│   │   ├── test_profit_lock.py
│   │   └── test_recovery_engine.py
│   ├── adapters/
│   │   ├── test_binance_adapter.py
│   │   └── test_bybit_adapter.py
│   ├── strategies/
│   │   ├── test_smart_grid.py
│   │   ├── test_adaptive_grid.py
│   │   └── test_dca.py
│   ├── repositories/
│   │   ├── test_user_repository.py
│   │   └── test_order_repository.py
│   └── utils/
│       ├── test_math.py
│       └── test_datetime.py
├── integration/              # Integration tests (with DB, Redis)
│   ├── test_auth_flow.py
│   ├── test_trading_flow.py
│   ├── test_order_flow.py
│   ├── test_grid_flow.py
│   └── test_portfolio_flow.py
├── e2e/                      # End-to-end tests
│   ├── test_full_trading_cycle.py
│   └── test_recovery_flow.py
├── conftest.py               # Shared fixtures
├── factories.py              # Test data factories
└── mocks.py                  # Mock implementations
```

### 2.3 Unit Test Standards

**Naming**: `test_{what}_{condition}_{expected_result}`

```python
# Good
def test_grid_engine_on_buy_filled_places_sell_order():
    ...

def test_trading_engine_start_raises_error_when_insufficient_balance():
    ...

def test_exchange_adapter_cancel_order_returns_true_on_success():
    ...

# Bad
def test_grid():
    ...

def test_start():
    ...
```

**Structure**: Arrange-Act-Assert (AAA)

```python
async def test_grid_engine_on_buy_filled_places_sell_order():
    # Arrange
    grid_engine = GridEngine(...)
    process_id = "test-uuid"
    grid_level = 5
    fill_price = Decimal("50000.0")
    quantity = Decimal("0.1")
    
    # Act
    await grid_engine.on_buy_filled(process_id, grid_level, fill_price, quantity)
    
    # Assert
    sell_order = grid_engine.get_level(process_id, grid_level).sell_order
    assert sell_order is not None
    assert sell_order.side == "sell"
    assert sell_order.price > fill_price  # Sell above buy price
```

**One assertion per test** (preferred, but not strict):

```python
# Good - focused test
async def test_create_user_returns_user_with_id():
    user = await user_service.create(create_user_dto)
    assert user.id is not None

# Acceptable - related assertions
async def test_create_user_persists_to_database():
    user = await user_service.create(create_user_dto)
    db_user = await user_repository.get_by_id(user.id)
    assert db_user is not None
    assert db_user.email == user.email
```

### 2.4 Mock Standards

**Use dependency injection for mocking**:

```python
# Good - inject mock via interface
async def test_trading_engine_start():
    mock_exchange = MockExchangeAdapter()
    mock_event_bus = MockEventBus()
    mock_grid_engine = MockGridEngine()
    
    engine = TradingEngine(
        exchange_adapter=mock_exchange,
        event_bus=mock_event_bus,
        grid_engine=mock_grid_engine,
    )
    
    result = await engine.start_process("test-process-id")
    
    assert result is True
    mock_grid_engine.activate_grid.assert_called_once()

# Bad - patching internal imports
async def test_trading_engine_start():
    with patch("engine.trading_engine.ExchangeAdapter") as mock:
        ...
```

### 2.5 Test Data Factories

```python
import factory
from models import User, Order, TradingProcess

class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    id = factory.LazyFunction(lambda: str(uuid4()))
    email = factory.Faker("email")
    password_hash = "$2b$12$..."
    full_name = factory.Faker("name")
    is_active = True
    is_verified = True
    role = "user"
    subscription_tier = "free"

class OrderFactory(factory.Factory):
    class Meta:
        model = Order
    
    id = factory.LazyFunction(lambda: str(uuid4()))
    user_id = factory.SubFactory(UserFactory).id
    symbol = "BTCUSDT"
    side = "buy"
    order_type = "limit"
    quantity = Decimal("0.1")
    price = Decimal("50000.0")
    status = "pending"

class TradingProcessFactory(factory.Factory):
    class Meta:
        model = TradingProcess
    
    id = factory.LazyFunction(lambda: str(uuid4()))
    user_id = factory.SubFactory(UserFactory).id
    symbol = "BTCUSDT"
    status = "created"
    total_investment = Decimal("1000.0")
```

### 2.6 Integration Test Standards

```python
import pytest
from httpx import AsyncClient
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:16") as pg:
        yield pg

@pytest.fixture(scope="session")
def redis():
    with RedisContainer("redis:7") as r:
        yield r

@pytest.fixture
async def client(postgres, redis):
    app = create_app(
        database_url=postgres.get_connection_url(),
        redis_url=redis.get_connection_url(),
    )
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

async def test_full_trading_flow(client, auth_token):
    # 1. Create exchange account
    response = await client.post(
        "/api/v1/exchange-accounts",
        json={...},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 201
    exchange_account_id = response.json()["data"]["id"]
    
    # 2. Create grid profile
    response = await client.post(
        "/api/v1/grid-profiles",
        json={...},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 201
    grid_profile_id = response.json()["data"]["id"]
    
    # 3. Create trading process
    response = await client.post(
        "/api/v1/trading-processes",
        json={...},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 201
    process_id = response.json()["data"]["id"]
    
    # 4. Start trading process
    response = await client.post(
        f"/api/v1/trading-processes/{process_id}/start",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "running"
```

### 2.7 Exchange Adapter Testing

Use mock exchange servers for testing:

```python
class MockExchangeServer:
    """Simulates exchange API responses for testing."""
    
    def __init__(self):
        self.orders = {}
        self.balances = {"USDT": Decimal("10000"), "BTC": Decimal("1.0")}
        self.prices = {"BTCUSDT": Decimal("50000")}
    
    async def place_order(self, symbol, side, order_type, quantity, price=None):
        order_id = str(uuid4())
        self.orders[order_id] = {
            "id": order_id,
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "price": price,
            "status": "open",
            "filled_quantity": Decimal("0"),
        }
        return self.orders[order_id]
    
    async def cancel_order(self, symbol, order_id):
        if order_id in self.orders:
            self.orders[order_id]["status"] = "cancelled"
            return True
        return False
    
    async def simulate_fill(self, order_id, fill_price):
        """Simulate order fill for testing."""
        if order_id in self.orders:
            order = self.orders[order_id]
            order["status"] = "filled"
            order["filled_quantity"] = order["quantity"]
            order["average_fill_price"] = fill_price
            return order
```

---

## 3. FRONTEND TESTING

### 3.1 Tools

| Tool | Purpose |
|------|---------|
| `vitest` | Test runner |
| `@testing-library/react` | Component testing |
| `@testing-library/user-event` | User interaction simulation |
| `msw` (Mock Service Worker) | API mocking |
| `playwright` | E2E testing |

### 3.2 Test Structure

```
frontend/src/
├── components/
│   ├── __tests__/
│   │   ├── Button.test.tsx
│   │   ├── OrderCard.test.tsx
│   │   └── TradingProcessList.test.tsx
├── hooks/
│   ├── __tests__/
│   │   ├── useTradingProcess.test.ts
│   │   └── useWebSocket.test.ts
├── stores/
│   ├── __tests__/
│   │   └── tradingStore.test.ts
├── services/
│   ├── __tests__/
│   │   └── api.test.ts
└── utils/
    ├── __tests__/
    │   └── format.test.ts
```

### 3.3 Component Test Standards

```typescript
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { OrderCard } from "../OrderCard";

describe("OrderCard", () => {
  it("displays order symbol and price", () => {
    render(<OrderCard order={mockOrder} />);
    
    expect(screen.getByText("BTCUSDT")).toBeInTheDocument();
    expect(screen.getByText("50,000.00")).toBeInTheDocument();
  });

  it("calls onCancel when cancel button clicked", async () => {
    const onCancel = vi.fn();
    render(<OrderCard order={mockOrder} onCancel={onCancel} />);
    
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));
    
    expect(onCancel).toHaveBeenCalledWith(mockOrder.id);
  });

  it("shows filled status badge when order is filled", () => {
    render(<OrderCard order={{ ...mockOrder, status: "filled" }} />);
    
    expect(screen.getByText(/filled/i)).toBeInTheDocument();
  });
});
```

### 3.4 Hook Test Standards

```typescript
import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { useTradingProcess } from "../useTradingProcess";

describe("useTradingProcess", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts trading process", async () => {
    const { result } = renderHook(() => useTradingProcess());
    
    await act(async () => {
      await result.current.start("test-process-id");
    });
    
    expect(result.current.status).toBe("running");
  });

  it("handles error when start fails", async () => {
    const { result } = renderHook(() => useTradingProcess());
    
    await act(async () => {
      await result.current.start("invalid-id");
    });
    
    expect(result.current.error).not.toBeNull();
    expect(result.current.status).toBe("error");
  });
});
```

### 3.5 Store Test Standards

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { useTradingStore } from "../tradingStore";

describe("tradingStore", () => {
  beforeEach(() => {
    useTradingStore.setState({ processes: [], selectedProcess: null });
  });

  it("adds trading process", () => {
    const { addProcess } = useTradingStore.getState();
    
    addProcess(mockProcess);
    
    expect(useTradingStore.getState().processes).toHaveLength(1);
  });

  it("updates process status", () => {
    useTradingStore.setState({ processes: [mockProcess] });
    
    const { updateProcessStatus } = useTradingStore.getState();
    updateProcessStatus(mockProcess.id, "running");
    
    expect(useTradingStore.getState().processes[0].status).toBe("running");
  });
});
```

---

## 4. E2E TESTING

### 4.1 Playwright Setup

```typescript
// playwright.config.ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  retries: 2,
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { browserName: "chromium" } },
    { name: "firefox", use: { browserName: "firefox" } },
  ],
});
```

### 4.2 E2E Test Example

```typescript
import { test, expect } from "@playwright/test";

test("complete trading flow", async ({ page }) => {
  // Login
  await page.goto("/login");
  await page.fill('[data-testid="email"]', "test@utos.com");
  await page.fill('[data-testid="password"]', "TestPassword123!");
  await page.click('[data-testid="login-button"]');
  
  // Navigate to trading
  await page.waitForURL("/dashboard");
  await page.click('[data-testid="nav-trading"]');
  
  // Create trading process
  await page.click('[data-testid="create-process"]');
  await page.selectOption('[data-testid="exchange-account"]', "binance");
  await page.selectOption('[data-testid="strategy"]', "smart_grid");
  await page.fill('[data-testid="symbol"]', "BTCUSDT");
  await page.fill('[data-testid="investment"]', "1000");
  await page.click('[data-testid="submit"]');
  
  // Verify process created
  await expect(page.locator('[data-testid="process-status"]')).toHaveText("Created");
  
  // Start process
  await page.click('[data-testid="start-process"]');
  await expect(page.locator('[data-testid="process-status"]')).toHaveText("Running");
  
  // Stop process
  await page.click('[data-testid="stop-process"]');
  await expect(page.locator('[data-testid="process-status"]')).toHaveText("Stopped");
});
```

---

## 5. PERFORMANCE TESTING

### 5.1 Load Testing

| Scenario | Target |
|----------|--------|
| API login | 1000 req/s |
| API order creation | 500 req/s |
| WebSocket connections | 10,000 concurrent |
| Event bus publish | 10,000 events/s |
| Database writes | 5,000 writes/s |

### 5.2 Tools

- `locust` for HTTP load testing
- `k6` for WebSocket load testing
- `pgbench` for database benchmarking

### 5.3 Example Locust Test

```python
from locust import HttpUser, task, between

class UTOSUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        response = self.client.post("/api/v1/auth/login", json={
            "email": "test@utos.com",
            "password": "TestPassword123!",
        })
        self.token = response.json()["data"]["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task
    def get_portfolio(self):
        self.client.get("/api/v1/portfolio", headers=self.headers)
    
    @task
    def list_trading_processes(self):
        self.client.get("/api/v1/trading-processes", headers=self.headers)
    
    @task(3)
    def list_orders(self):
        self.client.get("/api/v1/orders?limit=20", headers=self.headers)
```

---

## 6. TEST COMMANDS

### 6.1 Backend

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/unit/engine/test_grid_engine.py

# Run with verbose output
pytest -v

# Run only failed tests
pytest --lf

# Run in parallel
pytest -n auto
```

### 6.2 Frontend

```bash
# Run all tests
vitest

# Run with coverage
vitest --coverage

# Run in watch mode
vitest watch

# Run E2E tests
npx playwright test

# Run specific E2E test
npx playwright test e2e/trading-flow.spec.ts
```

---

## 7. TEST ENVIRONMENT

### 7.1 Backend Test Environment

- **Database**: PostgreSQL testcontainer (isolated per test session)
- **Redis**: Redis testcontainer (isolated per test session)
- **Exchange**: Mock exchange server (in-process)
- **External APIs**: Mocked via `responses` or `respx`

### 7.2 Frontend Test Environment

- **API**: Mock Service Worker (MSW)
- **WebSocket**: Mock WebSocket class
- **Browser**: jsdom (unit), Chromium/Firefox (E2E)

---

## 8. CONTINUOUS INTEGRATION

### 8.1 CI Pipeline

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r backend/requirements-dev.txt
      - run: pytest --cov=backend --cov-report=xml --cov-fail-under=85
      - uses: codecov/codecov-action@v4

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: cd frontend && npm ci
      - run: cd frontend && npm run test:coverage
      - run: cd frontend && npx playwright install --with-deps
      - run: cd frontend && npx playwright test
```

### 8.2 Pre-Commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v9.0.0
    hooks:
      - id: eslint
```

---

## 9. CHANGE LOG

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-09 | 1.0.0 | Initial testing standard |
| 2026-07-09 | 2.0.0 | Architecture revision: project rename, UTOS Trading Engine |
