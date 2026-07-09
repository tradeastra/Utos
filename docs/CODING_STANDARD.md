# CODING STANDARD

**Version:** 2.0.0  
**Last Updated:** 2026-07-09  
**Status:** DRAFT

---

## 1. PYTHON CODING STANDARDS

### 1.1 Code Style

Follow **PEP 8** style guide with the following specific rules:

**Line Length:**
- Maximum line length: 100 characters
- Soft limit: 88 characters (Black default)

**Indentation:**
- Use 4 spaces per indentation level
- No tabs

**Imports:**
- Group imports in this order:
  1. Standard library imports
  2. Third-party imports
  3. Local application imports
- Separate groups with blank line
- Use `isort` for automatic sorting

**Blank Lines:**
- Two blank lines before top-level functions and classes
- One blank line before method definitions
- Use blank lines sparingly inside functions

**Whitespace:**
- No whitespace inside parentheses, brackets, or braces
- No whitespace before colon
- One space around operators (except after power operator)

### 1.2 Naming Conventions

**Classes:** `PascalCase`
```python
class TradingEngine:
    pass

class OrderService:
    pass
```

**Functions and Methods:** `snake_case`
```python
def place_order():
    pass

def calculate_profit():
    pass
```

**Variables:** `snake_case`
```python
user_id = "123"
order_status = "filled"
```

**Constants:** `UPPER_SNAKE_CASE`
```python
MAX_GRID_LEVELS = 100
DEFAULT_TIMEOUT = 30
API_BASE_URL = "https://api.example.com"
```

**Private Members:** `_leading_underscore`
```python
class TradingEngine:
    def _internal_method(self):
        pass
    
    def __private_method(self):
        pass
```

**Protected Members:** `_leading_underscore` (convention)
```python
class TradingEngine:
    def _protected_method(self):
        pass
```

### 1.3 Type Hints

**Always use type hints for function signatures:**
```python
from typing import Optional, List, Dict, Any
from uuid import UUID

def place_order(
    user_id: UUID,
    symbol: str,
    quantity: float,
    price: Optional[float] = None
) -> OrderResult:
    pass
```

**Use `typing` module for complex types:**
```python
from typing import Dict, List, Optional, Union

def get_orders(
    user_id: UUID,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    pass
```

**Return types must be explicit:**
```python
# Good
def calculate_profit(position: Position) -> float:
    return position.unrealized_pnl

# Bad
def calculate_profit(position: Position):
    return position.unrealized_pnl
```

### 1.4 Docstrings

**Use Google-style docstrings:**
```python
def place_order(
    user_id: UUID,
    symbol: str,
    quantity: float,
    price: Optional[float] = None
) -> OrderResult:
    """Place a new order.
    
    Args:
        user_id: The user ID placing the order.
        symbol: The trading symbol (e.g., "BTCUSDT").
        quantity: The order quantity.
        price: The order price (None for market orders).
    
    Returns:
        OrderResult: The result of the order placement.
    
    Raises:
        InsufficientBalanceError: If user has insufficient balance.
        InvalidOrderError: If order parameters are invalid.
    """
    pass
```

**Class docstrings:**
```python
class TradingEngine:
    """Engine for managing trading operations.
    
    This engine handles order placement, execution, and tracking
    across multiple exchanges.
    
    Attributes:
        exchange_adapter: The exchange adapter for order execution.
        order_manager: The order manager for tracking orders.
    """
    
    def __init__(self, exchange_adapter: ExchangeAdapter):
        pass
```

### 1.5 Error Handling

**Use custom exceptions from `core/exceptions.py`:**
```python
from core.exceptions import (
    InsufficientBalanceError,
    InvalidOrderError,
    ExchangeConnectionError
)

def place_order(order: Order) -> OrderResult:
    try:
        return await exchange_adapter.place_order(order)
    except ExchangeConnectionError as e:
        logger.error(f"Exchange connection failed: {e}")
        raise
    except InsufficientBalanceError as e:
        logger.warning(f"Insufficient balance: {e}")
        raise
```

**Never swallow exceptions silently:**
```python
# Bad
try:
    result = some_operation()
except Exception:
    pass

# Good
try:
    result = some_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise
```

**Log errors with context:**
```python
logger.error(
    "Order placement failed",
    extra={
        "user_id": str(user_id),
        "symbol": symbol,
        "quantity": quantity,
        "error": str(e)
    }
)
```

### 1.6 Database (SQLAlchemy)

**Model definition:**
```python
from sqlalchemy import Column, String, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from database.session import Base

class Order(Base):
    """Order model for tracking trading orders."""
    
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="orders")
```

**Repository pattern:**
```python
from sqlalchemy.orm import Session
from models.order import Order
from schemas.order import OrderCreate

class OrderRepository:
    """Repository for order database operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, order_data: OrderCreate) -> Order:
        """Create a new order."""
        order = Order(**order_data.dict())
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order
    
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """Get order by ID."""
        return self.db.query(Order).filter(Order.id == order_id).first()
    
    def get_by_user(self, user_id: UUID) -> List[Order]:
        """Get all orders for a user."""
        return self.db.query(Order).filter(Order.user_id == user_id).all()
```

### 1.7 API (FastAPI)

**Route definition:**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from schemas.order import OrderCreate, OrderResponse
from services.order_service import OrderService
from core.security import get_current_user

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends()
) -> OrderResponse:
    """Create a new order."""
    try:
        return await order_service.create_order(current_user.id, order_data)
    except InsufficientBalanceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

**Dependency injection:**
```python
from fastapi import Depends
from database.session import get_db
from repositories.order_repository import OrderRepository

def get_order_repository(db: Session = Depends(get_db)) -> OrderRepository:
    """Get order repository instance."""
    return OrderRepository(db)
```

**Pydantic schemas:**
```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID

class OrderCreate(BaseModel):
    """Schema for creating an order."""
    symbol: str = Field(..., min_length=1, max_length=20)
    quantity: float = Field(..., gt=0)
    price: Optional[float] = Field(None, gt=0)
    
    @validator('symbol')
    def symbol_uppercase(cls, v):
        return v.upper()

class OrderResponse(BaseModel):
    """Schema for order response."""
    id: UUID
    symbol: str
    quantity: float
    price: Optional[float]
    status: str
    created_at: datetime
    
    class Config:
        orm_mode = True
```

### 1.8 Async/Await

**Use async/await for I/O operations:**
```python
import asyncio

async def place_order(order: Order) -> OrderResult:
    """Place order asynchronously."""
    # Async database operation
    order_record = await order_repository.create(order)
    
    # Async HTTP call
    result = await exchange_adapter.place_order(order)
    
    return result
```

**Don't block the event loop:**
```python
# Bad - blocking operation
def place_order(order: Order) -> OrderResult:
    time.sleep(1)  # Blocks event loop
    return result

# Good - async operation
async def place_order(order: Order) -> OrderResult:
    await asyncio.sleep(1)  # Non-blocking
    return result
```

### 1.9 Logging

**Use structured logging:**
```python
import logging

logger = logging.getLogger(__name__)

def place_order(order: Order) -> OrderResult:
    logger.info(
        "Placing order",
        extra={
            "user_id": str(order.user_id),
            "symbol": order.symbol,
            "quantity": order.quantity
        }
    )
    # ... implementation
```

**Log levels:**
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical errors requiring immediate attention

**Never log sensitive data:**
```python
# Bad
logger.info(f"API key: {api_key}")

# Good
logger.info("API key configured")
```

---

## 2. TYPESCRIPT/REACT CODING STANDARDS

### 2.1 Code Style

Follow **ESLint** and **Prettier** configuration:

**Line Length:**
- Maximum line length: 100 characters

**Indentation:**
- Use 2 spaces per indentation level

**Quotes:**
- Use single quotes for strings
- Use double quotes only for JSX attributes

**Semicolons:**
- Always use semicolons

### 2.2 Naming Conventions

**Components:** `PascalCase`
```typescript
const TradingDashboard: React.FC = () => {
    return <div>...</div>;
};
```

**Functions/Methods:** `camelCase`
```typescript
const handleSubmit = () => {
    // ...
};

const fetchOrders = async () => {
    // ...
};
```

**Constants:** `UPPER_SNAKE_CASE`
```typescript
const API_BASE_URL = "https://api.example.com";
const MAX_RETRY_ATTEMPTS = 3;
```

**Types/Interfaces:** `PascalCase`
```typescript
interface Order {
    id: string;
    symbol: string;
    quantity: number;
}

type OrderStatus = "pending" | "filled" | "cancelled";
```

### 2.3 Type Definitions

**Always use TypeScript types:**
```typescript
interface Order {
    id: string;
    symbol: string;
    quantity: number;
    price?: number;
    status: OrderStatus;
    createdAt: string;
}

type OrderStatus = "pending" | "filled" | "cancelled" | "rejected";
```

**Use union types for enums:**
```typescript
type TradingStatus = "idle" | "running" | "paused" | "error";
```

**Use generics for reusable types:**
```typescript
interface ApiResponse<T> {
    data: T;
    meta: {
        timestamp: string;
    };
}
```

### 2.4 Components

**Functional components with hooks:**
```typescript
import React, { useState, useEffect } from 'react';

interface TradingDashboardProps {
    userId: string;
}

const TradingDashboard: React.FC<TradingDashboardProps> = ({ userId }) => {
    const [orders, setOrders] = useState<Order[]>([]);
    const [loading, setLoading] = useState(false);
    
    useEffect(() => {
        fetchOrders();
    }, [userId]);
    
    const fetchOrders = async () => {
        setLoading(true);
        try {
            const data = await orderService.getOrders(userId);
            setOrders(data);
        } catch (error) {
            console.error('Failed to fetch orders:', error);
        } finally {
            setLoading(false);
        }
    };
    
    if (loading) return <LoadingSpinner />;
    
    return (
        <div>
            <OrderTable orders={orders} />
        </div>
    );
};
```

**Keep components small and focused:**
```typescript
// Good - single responsibility
const OrderTable: React.FC<{ orders: Order[] }> = ({ orders }) => {
    return (
        <table>
            {orders.map(order => (
                <OrderRow key={order.id} order={order} />
            ))}
        </table>
    );
};

// Bad - too many responsibilities
const OrderTable: React.FC<{ orders: Order[] }> = ({ orders }) => {
    const [filter, setFilter] = useState('');
    const [sort, setSort] = useState('date');
    // ... too much logic
};
```

### 2.5 Custom Hooks

**Extract reusable logic into custom hooks:**
```typescript
const useOrders = (userId: string) => {
    const [orders, setOrders] = useState<Order[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    useEffect(() => {
        fetchOrders();
    }, [userId]);
    
    const fetchOrders = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await orderService.getOrders(userId);
            setOrders(data);
        } catch (err) {
            setError('Failed to fetch orders');
        } finally {
            setLoading(false);
        }
    };
    
    return { orders, loading, error, refetch: fetchOrders };
};
```

**Hook naming convention:**
```typescript
// Good - starts with "use"
const useOrders = (userId: string) => { ... };
const useTradingStatus = (processId: string) => { ... };

// Bad - doesn't start with "use"
const getOrders = (userId: string) => { ... };
const fetchTradingStatus = (processId: string) => { ... };
```

### 2.6 State Management (Zustand)

**Keep state minimal and normalized:**
```typescript
import { create } from 'zustand';

interface OrderStore {
    orders: Order[];
    loading: boolean;
    error: string | null;
    setOrders: (orders: Order[]) => void;
    setLoading: (loading: boolean) => void;
    setError: (error: string | null) => void;
}

const useOrderStore = create<OrderStore>((set) => ({
    orders: [],
    loading: false,
    error: null,
    setOrders: (orders) => set({ orders }),
    setLoading: (loading) => set({ loading }),
    setError: (error) => set({ error }),
}));
```

**Separate UI state from data state:**
```typescript
// Data store
const useDataStore = create<DataStore>((set) => ({
    orders: [],
    setOrders: (orders) => set({ orders }),
}));

// UI store
const useUIStore = create<UIStore>((set) => ({
    selectedOrderId: null,
    isModalOpen: false,
    setSelectedOrderId: (id) => set({ selectedOrderId: id }),
    setModalOpen: (open) => set({ isModalOpen: open }),
}));
```

### 2.7 API Calls

**Centralize API calls in services:**
```typescript
// services/orderService.ts
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export const orderService = {
    async getOrders(userId: string): Promise<Order[]> {
        const response = await axios.get(`${API_BASE_URL}/orders`, {
            params: { userId }
        });
        return response.data.data;
    },
    
    async createOrder(orderData: OrderCreate): Promise<Order> {
        const response = await axios.post(`${API_BASE_URL}/orders`, orderData);
        return response.data.data;
    },
    
    async cancelOrder(orderId: string): Promise<void> {
        await axios.delete(`${API_BASE_URL}/orders/${orderId}`);
    }
};
```

**Use TypeScript types for responses:**
```typescript
interface ApiResponse<T> {
    data: T;
    meta: {
        timestamp: string;
    };
}

const response: ApiResponse<Order[]> = await axios.get(url);
const orders = response.data;
```

**Handle errors consistently:**
```typescript
try {
    const orders = await orderService.getOrders(userId);
    setOrders(orders);
} catch (error) {
    if (axios.isAxiosError(error)) {
        setError(error.response?.data?.message || 'Failed to fetch orders');
    } else {
        setError('An unexpected error occurred');
    }
}
```

### 2.8 Error Handling

**Show loading states:**
```typescript
const { orders, loading, error } = useOrders(userId);

if (loading) return <LoadingSpinner />;
if (error) return <ErrorMessage message={error} />;

return <OrderTable orders={orders} />;
```

**Provide meaningful error messages:**
```typescript
const ErrorMessage: React.FC<{ message: string }> = ({ message }) => {
    return (
        <div className="error-message">
            <p>{message}</p>
            <button onClick={() => window.location.reload()}>Retry</button>
        </div>
    );
};
```

---

## 3. GENERAL GUIDELINES

### 3.1 Code Review Checklist

- [ ] Code follows naming conventions
- [ ] Type hints are present and correct
- [ ] Docstrings are present for public functions/classes
- [ ] Error handling is appropriate
- [ ] Logging is present at key points
- [ ] No hardcoded values (use constants)
- [ ] No sensitive data in logs
- [ ] Tests are present for critical paths
- [ ] Code is DRY (Don't Repeat Yourself)
- [ ] Functions are small and focused

### 3.2 Commit Message Format

Follow conventional commits:

```
feat(scope): description

fix(scope): description

docs(scope): description

refactor(scope): description

test(scope): description

chore(scope): description
```

**Examples:**
```
feat(trading): add smart grid strategy implementation
fix(auth): resolve JWT token expiration issue
docs(api): update order endpoint documentation
refactor(database): optimize order query performance
test(order): add order creation unit tests
chore(deps): update FastAPI to version 0.100.0
```

### 3.3 File Organization

**Backend:**
```
backend/
├── core/           # Config, security, logging, constants, exceptions
├── api/            # API endpoints (grouped by domain)
├── models/         # SQLAlchemy models
├── schemas/        # Pydantic schemas
├── repositories/   # Database access layer
├── services/       # Business logic layer
├── database/       # Session management, migrations
├── kernel/         # Process manager, scheduler, state manager, event bus
├── engine/         # Trading, execution, grid, portfolio, risk, etc.
├── workers/        # Background task workers
├── market/         # Market data hub, cache, connector, replay
├── adapters/       # Exchange adapters
├── strategies/     # Trading strategies
├── plugins/        # Extensible plugins
├── events/         # Event definitions
├── tasks/          # Scheduled tasks
└── utils/          # Utility functions
```

**Frontend:**
```
frontend/
├── app/            # App pages and layouts
├── components/     # Reusable UI components
├── features/       # Feature-specific components and logic
├── hooks/          # Custom React hooks
├── services/       # API calls and external services
├── stores/         # State management (Zustand)
├── lib/            # Utility libraries
├── types/          # TypeScript type definitions
├── styles/         # Global styles and themes
└── public/         # Static assets
```

### 3.4 Code Quality Tools

**Backend (Python):**
- `black` - Code formatting
- `isort` - Import sorting
- `flake8` - Linting
- `mypy` - Type checking
- `pylint` - Advanced linting

**Frontend (TypeScript):**
- `eslint` - Linting
- `prettier` - Code formatting
- `typescript` - Type checking

---

## 4. TESTING STANDARDS

### 4.1 Python Tests

**Unit tests:**
```python
import pytest
from services.order_service import OrderService
from core.exceptions import InsufficientBalanceError

def test_place_order_insufficient_balance():
    """Test that placing order with insufficient balance raises error."""
    service = OrderService()
    
    with pytest.raises(InsufficientBalanceError):
        service.place_order(
            user_id="test-user",
            symbol="BTCUSDT",
            quantity=100.0,
            price=50000.0
        )
```

**Integration tests:**
```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_order():
    """Test order creation endpoint."""
    response = client.post(
        "/orders/",
        json={
            "symbol": "BTCUSDT",
            "quantity": 0.1,
            "price": 50000.0
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 201
    assert response.json()["symbol"] == "BTCUSDT"
```

### 4.2 TypeScript Tests

**Component tests:**
```typescript
import { render, screen } from '@testing-library/react';
import TradingDashboard from './TradingDashboard';

describe('TradingDashboard', () => {
    it('renders order table', () => {
        render(<TradingDashboard userId="test-user" />);
        expect(screen.getByText('Orders')).toBeInTheDocument();
    });
});
```

**Hook tests:**
```typescript
import { renderHook, act } from '@testing-library/react-hooks';
import { useOrders } from './useOrders';

describe('useOrders', () => {
    it('fetches orders on mount', async () => {
        const { result, waitForNextUpdate } = renderHook(() => useOrders('test-user'));
        
        expect(result.current.loading).toBe(true);
        
        await waitForNextUpdate();
        
        expect(result.current.loading).toBe(false);
        expect(result.current.orders).toHaveLength(10);
    });
});
```

---

## 5. DOCUMENTATION STANDARDS

### 5.1 Code Comments

**Use comments to explain WHY, not WHAT:**
```python
# Bad - explains what the code does
# Increment the counter by 1
counter += 1

# Good - explains why the code does this
# Counter must be incremented to track total order attempts
counter += 1
```

**Keep comments up to date:**
- Remove outdated comments
- Update comments when code changes

### 5.2 README Files

Each directory should have a README.md explaining:
- Purpose of the directory
- Key files and their responsibilities
- How to use the code in this directory

---

## 6. SECURITY STANDARDS

### 6.1 Secrets Management

- Never commit secrets to version control
- Use environment variables for sensitive data
- Use `.env.example` as template for environment variables

### 6.2 Input Validation

- Validate all user inputs
- Use Pydantic schemas for backend validation
- Use TypeScript types for frontend validation

### 6.3 SQL Injection Prevention

- Use parameterized queries (SQLAlchemy handles this)
- Never concatenate user input into SQL queries

---

## 7. PERFORMANCE STANDARDS

### 7.1 Database Queries

- Use indexes for frequently queried fields
- Avoid N+1 queries (use eager loading)
- Use pagination for large result sets

### 7.2 Caching

- Cache frequently accessed data in Redis
- Use appropriate TTL (time-to-live)
- Invalidate cache on data changes

### 7.3 Async Operations

- Use async/await for I/O operations
- Don't block the event loop
- Use connection pooling

---

## 8. CHANGE LOG

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-09 | 1.0.0 | Initial coding standard creation |
| 2026-07-09 | 2.0.0 | Architecture revision: version bump for consistency |
