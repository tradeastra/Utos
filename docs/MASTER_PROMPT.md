# MASTER PROMPT

**Version:** 1.0.0  
**Last Updated:** 2026-07-09  
**Status:** DRAFT

---

## PURPOSE

This document is the master prompt for AI assistants (Codex, Cascade, etc.) working on the UTOS project. It provides the context, guidelines, and rules for implementing features consistently.

**ALWAYS READ THIS BEFORE STARTING ANY WORK.**

---

## 1. PROJECT CONTEXT

### 1.1 What is UTOS?

UTOS is an automated cryptocurrency trading system that supports multiple exchanges and trading strategies. Key features:

- Multi-exchange support (Binance, Hyperliquid, Bybit, OKX, MEXC)
- Grid trading strategies (Smart Grid, Adaptive Grid, Infinity Grid)
- DCA (Dollar Cost Averaging) strategy
- Portfolio management and tracking
- Risk management and profit locking
- Real-time market data processing
- Event-driven architecture

### 1.2 Technology Stack

**Backend:**
- Python 3.11+
- FastAPI (web framework)
- PostgreSQL (database)
- Redis (cache + event bus)
- SQLAlchemy (ORM)
- Pydantic (validation)

**Frontend:**
- React / Next.js
- TypeScript
- TailwindCSS
- shadcn/ui
- Zustand (state management)

**Infrastructure:**
- Docker
- Nginx
- GitHub Actions (CI/CD)

---

## 2. WORKING PRINCIPLES

### 2.1 ALWAYS Reference PROJECT_BIBLE.md

Before implementing any feature:
1. Read the relevant section in `docs/PROJECT_BIBLE.md`
2. Understand the data model, API spec, and business rules
3. Follow the defined patterns

**NEVER implement without checking the Project Bible first.**

### 2.2 Documentation-First Approach

- Documentation must be written before code
- API specs must be defined before implementation
- Data models must be designed before database changes
- Event specs must be defined before event handling

### 2.3 Minimal Implementation

- Implement only what is specified
- Don't add "nice-to-have" features without approval
- Keep code simple and maintainable
- Avoid over-engineering

### 2.4 Consistency

- Follow existing patterns in the codebase
- Use the same naming conventions
- Match the existing code style
- Don't reinvent the wheel

---

## 3. CODING GUIDELINES

### 3.1 Python (Backend)

**File Structure:**
```
backend/
├── core/           # Config, security, logging, constants, exceptions
├── api/            # API endpoints (grouped by domain)
├── models/         # SQLAlchemy models
├── schemas/        # Pydantic schemas (request/response)
├── repositories/   # Database access layer
├── services/       # Business logic layer
├── database/       # Session management, migrations
├── kernel/         # Process manager, scheduler, state manager, event bus
├── engine/         # Trading, execution, grid, portfolio, risk, etc.
├── workers/        # Background task workers
├── market/         # Market data hub, cache, connector, replay
├── adapters/       # Exchange adapters (base + implementations)
├── strategies/     # Trading strategy implementations
├── plugins/        # Extensible plugins
├── events/         # Event definitions
├── tasks/          # Scheduled tasks
└── utils/          # Utility functions
```

**Naming Conventions:**
- Classes: `PascalCase` (e.g., `TradingEngine`, `OrderService`)
- Functions/Methods: `snake_case` (e.g., `place_order`, `calculate_profit`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_GRID_LEVELS`, `DEFAULT_TIMEOUT`)
- Private members: `_leading_underscore` (e.g., `_internal_method`)

**Type Hints:**
- Always use type hints for function signatures
- Use `typing` module for complex types
- Return types must be explicit

**Error Handling:**
- Use custom exceptions from `core/exceptions.py`
- Never swallow exceptions silently
- Log errors with context
- Provide meaningful error messages to users

**Database:**
- Use SQLAlchemy models in `models/`
- Use Pydantic schemas in `schemas/`
- Separate read/write operations in `repositories/`
- Business logic goes in `services/`

**API:**
- Use FastAPI dependency injection
- Define routes in `api/` subdirectories
- Use Pydantic for request/response validation
- Return consistent response structure

### 3.2 TypeScript/React (Frontend)

**File Structure:**
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

**Naming Conventions:**
- Components: `PascalCase` (e.g., `TradingDashboard`, `OrderTable`)
- Functions/Methods: `camelCase` (e.g., `handleSubmit`, `fetchOrders`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `API_BASE_URL`)
- Types/Interfaces: `PascalCase` (e.g., `Order`, `UserProfile`)

**Component Structure:**
- Use functional components with hooks
- Keep components small and focused
- Extract reusable logic into custom hooks
- Use TypeScript for all components

**State Management:**
- Use Zustand for global state
- Keep state minimal and normalized
- Separate UI state from data state

**API Calls:**
- Centralize API calls in `services/`
- Use TypeScript types for responses
- Handle errors consistently
- Show loading states

---

## 4. ARCHITECTURAL PATTERNS

### 4.1 Layered Architecture

```
API Layer (FastAPI routes)
    ↓
Service Layer (Business logic)
    ↓
Repository Layer (Database access)
    ↓
Database (PostgreSQL)
```

**Rules:**
- API layer should not contain business logic
- Service layer should not access database directly
- Repository layer should not contain business logic

### 4.2 Event-Driven Architecture

**Event Flow:**
```
Event Producer → Event Bus → Event Consumer
```

**Rules:**
- Define events in `events/` directory
- Use Redis as event bus
- Events must be immutable
- Consumers should be idempotent

**Event Naming:**
- Use past tense for events (e.g., `ORDER_FILLED`, `PRICE_UPDATED`)
- Use uppercase with underscores
- Be descriptive but concise

### 4.3 Adapter Pattern

**Exchange Adapters:**
- Base adapter in `adapters/base/`
- Exchange-specific implementations in `adapters/{exchange}/`
- All adapters must implement the same interface
- Normalize exchange-specific differences

**Interface Methods:**
```python
class ExchangeAdapter(ABC):
    @abstractmethod
    async def place_order(self, order: Order) -> OrderResult:
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        pass
    
    @abstractmethod
    async def get_balance(self) -> Balance:
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        pass
    
    @abstractmethod
    async def subscribe_ticker(self, symbol: str, callback: Callable):
        pass
```

### 4.4 Strategy Pattern

**Trading Strategies:**
- Base strategy in `strategies/templates/`
- Strategy implementations in `strategies/{strategy_type}/`
- All strategies must implement the same interface
- Strategies should be stateless (state stored elsewhere)

---

## 5. DATABASE GUIDELINES

### 5.1 Model Design

- Use SQLAlchemy declarative base
- All models must have `id` (UUID) and `created_at`, `updated_at`
- Use proper foreign key relationships
- Add indexes for frequently queried fields
- Use cascade deletes appropriately

### 5.2 Migration Strategy

- Use Alembic for migrations
- Generate migration scripts automatically
- Review migrations before applying
- Never modify existing migrations

### 5.3 Query Optimization

- Use select_related/join_related for relationships
- Avoid N+1 queries
- Use database indexes properly
- Consider read replicas for heavy read loads

---

## 6. API GUIDELINES

### 6.1 RESTful Conventions

- Use appropriate HTTP methods (GET, POST, PUT, DELETE, PATCH)
- Use plural nouns for resource names (e.g., `/orders`, `/users`)
- Use kebab-case for URLs (e.g., `/trading-processes`)
- Return proper HTTP status codes

### 6.2 Response Format

**Success Response:**
```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Response:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": { ... }
  }
}
```

### 6.3 Authentication

- Use JWT tokens for authentication
- Include token in `Authorization: Bearer {token}` header
- Validate tokens on protected endpoints
- Use role-based access control for admin endpoints

---

## 7. TESTING GUIDELINES

### 7.1 Test Structure

```
tests/
├── unit/           # Unit tests for individual functions/classes
├── integration/    # Integration tests for API and database
├── e2e/            # End-to-end tests for user flows
└── performance/    # Performance and load tests
```

### 7.2 Test Coverage

- Aim for 80%+ code coverage
- Test critical paths thoroughly
- Test edge cases and error conditions
- Use fixtures for test data

### 7.3 Test Naming

- Use descriptive test names
- Follow pattern: `test_{feature}_{scenario}_{expected_result}`
- Example: `test_place_order_insufficient_balance_returns_error`

---

## 8. SECURITY GUIDELINES

### 8.1 API Key Management

- Never log API keys
- Encrypt API keys at rest
- Use environment variables for secrets
- Rotate keys regularly

### 8.2 Input Validation

- Validate all user inputs
- Use Pydantic schemas for validation
- Sanitize data before database operations
- Prevent SQL injection (use parameterized queries)

### 8.3 Rate Limiting

- Implement rate limiting on all public endpoints
- Use Redis for rate limit storage
- Return 429 status when limit exceeded
- Log rate limit violations

---

## 9. PERFORMANCE GUIDELINES

### 9.1 Caching Strategy

- Cache frequently accessed data in Redis
- Use appropriate TTL (time-to-live)
- Invalidate cache on data changes
- Consider cache warming for critical data

### 9.2 Async Operations

- Use async/await for I/O operations
- Don't block the event loop
- Use connection pooling for database
- Use async HTTP clients (aiohttp/httpx)

### 9.3 Database Performance

- Use indexes effectively
- Avoid large transactions
- Batch operations when possible
- Monitor slow queries

---

## 10. LOGGING GUIDELINES

### 10.1 Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical errors requiring immediate attention

### 10.2 Log Format

- Include timestamp, level, module, message
- Add context (user ID, request ID, etc.)
- Structure logs as JSON for parsing
- Avoid logging sensitive data

### 10.3 Log Retention

- Keep logs for 30 days
- Archive important logs
- Monitor log volume
- Set up log alerts for errors

---

## 11. WORKFLOW FOR IMPLEMENTING FEATURES

### 11.1 Before Coding

1. Read the relevant section in `PROJECT_BIBLE.md`
2. Understand the data model
3. Review the API specification
4. Check for existing patterns
5. Plan the implementation

### 11.2 During Coding

1. Follow the architectural patterns
2. Write tests alongside code
3. Add logging at key points
4. Handle errors properly
5. Document complex logic

### 11.3 After Coding

1. Run all tests
2. Check code coverage
3. Review the code
4. Update documentation
5. Commit with clear message

---

## 12. COMMON MISTAKES TO AVOID

- ❌ Implementing without reading documentation
- ❌ Adding features not in specifications
- ❌ Breaking existing patterns
- ❌ Ignoring error handling
- ❌ Hardcoding configuration values
- ❌ Skipping tests
- ❌ Committing sensitive data
- ❌ Making large, monolithic commits
- ❌ Not using type hints
- ❌ Swallowing exceptions

---

## 13. WHEN TO ASK FOR HELP

Ask for clarification when:
- The specification is unclear
- Multiple approaches seem valid
- A decision affects architecture
- You're unsure about security implications
- The implementation seems overly complex

---

## 14. REFERENCES

- Project Bible: `docs/PROJECT_BIBLE.md`
- Coding Standard: `docs/CODING_STANDARD.md`
- Database Design: `docs/DATABASE.md`
- API Guidelines: `docs/API_GUIDELINES.md`
- Architecture Docs: `docs/architecture/`

---

## 15. VERSION CONTROL

### 15.1 Commit Messages

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Maintenance tasks

Example: `feat(trading): add smart grid strategy implementation`

### 15.2 Branch Strategy

- `main`: Production code
- `develop`: Integration branch
- `feature/*`: Feature branches
- `fix/*`: Bug fix branches
- `hotfix/*`: Production hotfixes

---

**REMEMBER: The Project Bible is the single source of truth. Always reference it before implementing anything.**
