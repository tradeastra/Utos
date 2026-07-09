# API GUIDELINES

**Version:** 2.0.0  
**Last Updated:** 2026-07-09  
**Status:** DRAFT

---

## 1. OVERVIEW

This document defines the API specifications for the UTOS Trading Engine. The API follows RESTful principles and uses JSON for data exchange.

### 1.1 Base URL

- **Development**: `http://localhost:8000/api/v1`
- **Staging**: `https://staging.api.utos.com/api/v1`
- **Production**: `https://api.utos.com/api/v1`

### 1.2 Authentication

All API endpoints (except auth endpoints) require authentication via JWT bearer token.

**Header**: `Authorization: Bearer {token}`

### 1.3 Response Format

**Success Response**:
```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Response**:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": { ... }
  }
}
```

---

## 2. AUTHENTICATION ENDPOINTS

### 2.1 Register

**Endpoint**: `POST /auth/register`

**Description**: Register a new user account.

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe",
  "phone": "+1234567890"
}
```

**Response** (201 Created):
```json
{
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_verified": false,
    "created_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Codes**:
- `VALIDATION_ERROR`: Invalid input data
- `EMAIL_EXISTS`: Email already registered

---

### 2.2 Login

**Endpoint**: `POST /auth/login`

**Description**: Authenticate user and receive JWT token.

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response** (200 OK):
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Codes**:
- `INVALID_CREDENTIALS`: Invalid email or password
- `ACCOUNT_DISABLED`: Account is disabled

---

### 2.3 Refresh Token

**Endpoint**: `POST /auth/refresh`

**Description**: Refresh access token using refresh token.

**Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response** (200 OK):
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Codes**:
- `INVALID_TOKEN`: Invalid or expired refresh token

---

### 2.4 Logout

**Endpoint**: `POST /auth/logout`

**Description**: Invalidate current session.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "message": "Successfully logged out"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

## 3. USER MANAGEMENT ENDPOINTS

### 3.1 Get Current User

**Endpoint**: `GET /users/me`

**Description**: Get current user profile.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "phone": "+1234567890",
    "is_active": true,
    "is_verified": true,
    "subscription_tier": "pro",
    "referral_code": "ABC123",
    "created_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

### 3.2 Update User Profile

**Endpoint**: `PATCH /users/me`

**Description**: Update current user profile.

**Headers**: `Authorization: Bearer {token}`

**Request Body**:
```json
{
  "full_name": "John Smith",
  "phone": "+9876543210"
}
```

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Smith",
    "phone": "+9876543210",
    "updated_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

### 3.3 Change Password

**Endpoint**: `POST /users/me/change-password`

**Description**: Change user password.

**Headers**: `Authorization: Bearer {token}`

**Request Body**:
```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword456!"
}
```

**Response** (200 OK):
```json
{
  "data": {
    "message": "Password changed successfully"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Codes**:
- `INVALID_PASSWORD`: Current password is incorrect

---

## 4. EXCHANGE MANAGEMENT ENDPOINTS

### 4.1 List Exchange Accounts

**Endpoint**: `GET /exchange-accounts`

**Description**: List all connected exchange accounts.

**Headers**: `Authorization: Bearer {token}`

**Query Parameters**:
- `exchange_name` (optional): Filter by exchange name
- `is_active` (optional): Filter by active status

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid",
      "exchange_name": "binance",
      "account_name": "My Binance Account",
      "is_testnet": false,
      "is_active": true,
      "connection_status": "connected",
      "last_synced_at": "2026-07-09T10:00:00Z",
      "created_at": "2026-07-09T10:00:00Z"
    }
  ],
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z",
    "total": 1
  }
}
```

---

### 4.2 Connect Exchange Account

**Endpoint**: `POST /exchange-accounts`

**Description**: Connect a new exchange account.

**Headers**: `Authorization: Bearer {token}`

**Request Body**:
```json
{
  "exchange_name": "binance",
  "account_name": "My Binance Account",
  "api_key": "encrypted_api_key",
  "api_secret": "encrypted_api_secret",
  "is_testnet": false
}
```

**Response** (201 Created):
```json
{
  "data": {
    "id": "uuid",
    "exchange_name": "binance",
    "account_name": "My Binance Account",
    "is_testnet": false,
    "is_active": true,
    "connection_status": "connected",
    "created_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Codes**:
- `INVALID_EXCHANGE`: Invalid exchange name
- `INVALID_API_CREDENTIALS`: Invalid API credentials
- `CONNECTION_FAILED`: Failed to connect to exchange

---

### 4.3 Get Exchange Account

**Endpoint**: `GET /exchange-accounts/{account_id}`

**Description**: Get details of a specific exchange account.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "exchange_name": "binance",
    "account_name": "My Binance Account",
    "is_testnet": false,
    "is_active": true,
    "connection_status": "connected",
    "last_synced_at": "2026-07-09T10:00:00Z",
    "created_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Codes**:
- `NOT_FOUND`: Exchange account not found

---

### 4.4 Update Exchange Account

**Endpoint**: `PATCH /exchange-accounts/{account_id}`

**Description**: Update exchange account details.

**Headers**: `Authorization: Bearer {token}`

**Request Body**:
```json
{
  "account_name": "Updated Account Name",
  "is_active": false
}
```

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "account_name": "Updated Account Name",
    "is_active": false,
    "updated_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

### 4.5 Delete Exchange Account

**Endpoint**: `DELETE /exchange-accounts/{account_id}`

**Description**: Delete (soft delete) an exchange account.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "message": "Exchange account deleted successfully"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

### 4.6 Test Exchange Connection

**Endpoint**: `POST /exchange-accounts/{account_id}/test`

**Description**: Test connection to exchange.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "status": "connected",
    "message": "Connection successful"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Codes**:
- `CONNECTION_FAILED`: Failed to connect to exchange

---

### 4.7 Get Exchange Balances

**Endpoint**: `GET /exchange-accounts/{account_id}/balances`

**Description**: Get balances for an exchange account.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": [
    {
      "currency": "USDT",
      "available": 1000.0,
      "locked": 100.0,
      "total": 1100.0,
      "last_updated_at": "2026-07-09T10:00:00Z"
    },
    {
      "currency": "BTC",
      "available": 0.5,
      "locked": 0.0,
      "total": 0.5,
      "last_updated_at": "2026-07-09T10:00:00Z"
    }
  ],
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z",
    "total": 2
  }
}
```

---

## 5. TRADING ENDPOINTS

### 5.1 List Trading Instances

**Endpoint**: `GET /trading-instances`

**Description**: List all trading instances.

**Headers**: `Authorization: Bearer {token}`

**Query Parameters**:
- `status` (optional): Filter by status
- `symbol` (optional): Filter by symbol
- `exchange_account_id` (optional): Filter by exchange account

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid",
      "symbol": "BTCUSDT",
      "status": "running",
      "strategy_name": "Smart Grid",
      "start_price": 50000.0,
      "current_price": 51000.0,
      "total_investment": 1000.0,
      "unrealized_pnl": 20.0,
      "started_at": "2026-07-09T10:00:00Z",
      "created_at": "2026-07-09T10:00:00Z"
    }
  ],
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z",
    "total": 1
  }
}
```

---

### 5.2 Create Trading Instance

**Endpoint**: `POST /trading-instances`

**Description**: Create a new trading instance.

**Headers**: `Authorization: Bearer {token}`

**Request Body**:
```json
{
  "exchange_account_id": "uuid",
  "strategy_id": "uuid",
  "grid_profile_id": "uuid",
  "symbol": "BTCUSDT",
  "total_investment": 1000.0,
  "profit_lock_enabled": true,
  "profit_lock_trigger_percentage": 10.0,
  "profit_lock_trail_percentage": 2.0,
  "portfolio_lock_enabled": true,
  "portfolio_lock_trigger_percentage": 20.0,
  "portfolio_lock_trail_percentage": 3.0
}
```

**Response** (201 Created):
```json
{
  "data": {
    "id": "uuid",
    "symbol": "BTCUSDT",
    "status": "created",
    "strategy_name": "Smart Grid",
    "start_price": 50000.0,
    "total_investment": 1000.0,
    "created_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Codes**:
- `INSUFFICIENT_BALANCE`: Insufficient balance
- `INVALID_SYMBOL`: Invalid trading symbol
- `GRID_PROFILE_NOT_FOUND`: Grid profile not found

---

### 5.3 Prepare Trading Instance

**Endpoint**: `POST /trading-instances/{instance_id}/prepare`

**Description**: Transition instance from CREATED to READY. Performs API key validation, balance check, grid calculation, order/position sync, market subscription, worker allocation, and ProcessMemory initialization.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "status": "ready",
    "prepared_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Codes**:
- `INVALID_STATUS`: Instance must be in CREATED state
- `INSUFFICIENT_BALANCE`: Insufficient balance
- `EXCHANGE_AUTH_FAILED`: API key validation failed
- `INVALID_GRID_PARAMETERS`: Grid calculation failed

---

### 5.4 Get Trading Instance

**Endpoint**: `GET /trading-instances/{instance_id}`

**Description**: Get details of a specific trading instance.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "symbol": "BTCUSDT",
    "status": "running",
    "strategy_name": "Smart Grid",
    "start_price": 50000.0,
    "current_price": 51000.0,
    "total_investment": 1000.0,
    "unrealized_pnl": 20.0,
    "grid_levels": {
      "total": 10,
      "active": 5,
      "filled": 3
    },
    "started_at": "2026-07-09T10:00:00Z",
    "created_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

### 5.5 Start Trading Instance

**Endpoint**: `POST /trading-instances/{instance_id}/start`

**Description**: Transition instance from READY to RUNNING. The instance must be prepared first via `/prepare`.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "status": "running",
    "started_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Codes**:
- `INVALID_STATUS`: Instance cannot be started in current status
- `INSUFFICIENT_BALANCE`: Insufficient balance

---

### 5.6 Stop Trading Instance

**Endpoint**: `POST /trading-instances/{instance_id}/stop`

**Description**: Stop a trading instance.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "status": "stopping",
    "stopped_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Codes**:
- `INVALID_STATUS`: Instance cannot be stopped in current status

---

### 5.7 Pause Trading Instance

**Endpoint**: `POST /trading-instances/{instance_id}/pause`

**Description**: Pause a trading instance.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "status": "paused"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Codes**:
- `INVALID_STATUS`: Instance cannot be paused in current status

---

### 5.8 Resume Trading Instance

**Endpoint**: `POST /trading-instances/{instance_id}/resume`

**Description**: Resume a paused trading instance.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "status": "running"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Codes**:
- `INVALID_STATUS`: Instance cannot be resumed in current status

---

## 6. ORDER ENDPOINTS

### 6.1 List Orders

**Endpoint**: `GET /orders`

**Description**: List orders for current user.

**Headers**: `Authorization: Bearer {token}`

**Query Parameters**:
- `status` (optional): Filter by status
- `symbol` (optional): Filter by symbol
- `trading_instance_id` (optional): Filter by trading instance
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Offset for pagination (default: 0)

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid",
      "symbol": "BTCUSDT",
      "side": "buy",
      "order_type": "limit",
      "quantity": 0.1,
      "price": 50000.0,
      "filled_quantity": 0.0,
      "status": "open",
      "grid_level": 1,
      "created_at": "2026-07-09T10:00:00Z"
    }
  ],
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z",
    "total": 1,
    "limit": 50,
    "offset": 0
  }
}
```

---

### 6.2 Get Order

**Endpoint**: `GET /orders/{order_id}`

**Description**: Get details of a specific order.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "symbol": "BTCUSDT",
    "side": "buy",
    "order_type": "limit",
    "quantity": 0.1,
    "price": 50000.0,
    "filled_quantity": 0.1,
    "average_fill_price": 50000.0,
    "status": "filled",
    "grid_level": 1,
    "is_profit_lock": false,
    "created_at": "2026-07-09T10:00:00Z",
    "filled_at": "2026-07-09T10:01:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

### 6.3 Cancel Order

**Endpoint**: `POST /orders/{order_id}/cancel`

**Description**: Cancel an open order.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "status": "cancelled",
    "updated_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

**Error Codes**:
- `INVALID_STATUS`: Order cannot be cancelled in current status
- `CANCEL_FAILED`: Failed to cancel order on exchange

---

## 7. PORTFOLIO ENDPOINTS

### 7.1 Get Portfolio

**Endpoint**: `GET /portfolio`

**Description**: Get current portfolio overview.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "total_value": 5000.0,
    "total_investment": 4800.0,
    "total_pnl": 200.0,
    "pnl_percentage": 4.17,
    "positions": [
      {
        "symbol": "BTCUSDT",
        "side": "long",
        "quantity": 0.1,
        "entry_price": 50000.0,
        "current_price": 51000.0,
        "value": 5100.0,
        "unrealized_pnl": 100.0,
        "pnl_percentage": 2.0
      }
    ]
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

### 7.2 Get Positions

**Endpoint**: `GET /portfolio/positions`

**Description**: Get all current positions.

**Headers**: `Authorization: Bearer {token}`

**Query Parameters**:
- `symbol` (optional): Filter by symbol
- `trading_instance_id` (optional): Filter by trading instance

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid",
      "symbol": "BTCUSDT",
      "side": "long",
      "quantity": 0.1,
      "entry_price": 50000.0,
      "current_price": 51000.0,
      "value": 5100.0,
      "unrealized_pnl": 100.0,
      "realized_pnl": 50.0,
      "created_at": "2026-07-09T10:00:00Z"
    }
  ],
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z",
    "total": 1
  }
}
```

---

## 8. STRATEGY ENDPOINTS

### 8.1 List Strategies

**Endpoint**: `GET /strategies`

**Description**: List available trading strategies.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Smart Grid",
      "type": "smart_grid",
      "description": "Traditional grid trading strategy",
      "min_investment": 100.0,
      "max_investment": 100000.0,
      "is_active": true
    },
    {
      "id": "uuid",
      "name": "Adaptive Grid",
      "type": "adaptive_grid",
      "description": "Grid trading with dynamic adjustment",
      "min_investment": 100.0,
      "max_investment": 100000.0,
      "is_active": true
    }
  ],
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z",
    "total": 2
  }
}
```

---

### 8.2 Get Strategy

**Endpoint**: `GET /strategies/{strategy_id}`

**Description**: Get details of a specific strategy.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "name": "Smart Grid",
    "type": "smart_grid",
    "description": "Traditional grid trading strategy",
    "min_investment": 100.0,
    "max_investment": 100000.0,
    "is_active": true,
    "parameters": {
      "upper_price": {
        "type": "decimal",
        "required": true,
        "description": "Upper price boundary"
      },
      "lower_price": {
        "type": "decimal",
        "required": true,
        "description": "Lower price boundary"
      },
      "grid_count": {
        "type": "integer",
        "required": true,
        "description": "Number of grid levels"
      }
    }
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

## 9. GRID PROFILE ENDPOINTS

### 9.1 List Grid Profiles

**Endpoint**: `GET /grid-profiles`

**Description**: List user's grid profiles.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "BTC Grid",
      "strategy_type": "smart_grid",
      "upper_price": 60000.0,
      "lower_price": 40000.0,
      "grid_count": 10,
      "investment_per_grid": 100.0,
      "is_default": true,
      "created_at": "2026-07-09T10:00:00Z"
    }
  ],
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z",
    "total": 1
  }
}
```

---

### 9.2 Create Grid Profile

**Endpoint**: `POST /grid-profiles`

**Description**: Create a new grid profile.

**Headers**: `Authorization: Bearer {token}`

**Request Body**:
```json
{
  "name": "BTC Grid",
  "strategy_type": "smart_grid",
  "upper_price": 60000.0,
  "lower_price": 40000.0,
  "grid_count": 10,
  "investment_per_grid": 100.0,
  "take_profit_enabled": true,
  "take_profit_percentage": 10.0
}
```

**Response** (201 Created):
```json
{
  "data": {
    "id": "uuid",
    "name": "BTC Grid",
    "strategy_type": "smart_grid",
    "upper_price": 60000.0,
    "lower_price": 40000.0,
    "grid_count": 10,
    "grid_spacing": 2000.0,
    "investment_per_grid": 100.0,
    "take_profit_enabled": true,
    "take_profit_percentage": 10.0,
    "created_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

### 9.3 Update Grid Profile

**Endpoint**: `PATCH /grid-profiles/{profile_id}`

**Description**: Update a grid profile.

**Headers**: `Authorization: Bearer {token}`

**Request Body**:
```json
{
  "name": "Updated BTC Grid",
  "take_profit_percentage": 15.0
}
```

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "name": "Updated BTC Grid",
    "take_profit_percentage": 15.0,
    "updated_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

### 9.4 Delete Grid Profile

**Endpoint**: `DELETE /grid-profiles/{profile_id}`

**Description**: Delete a grid profile.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "message": "Grid profile deleted successfully"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

## 10. NOTIFICATION ENDPOINTS

### 10.1 List Notifications

**Endpoint**: `GET /notifications`

**Description**: List user notifications.

**Headers**: `Authorization: Bearer {token}`

**Query Parameters**:
- `is_read` (optional): Filter by read status
- `type` (optional): Filter by notification type
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Offset for pagination (default: 0)

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid",
      "type": "order_filled",
      "title": "Order Filled",
      "message": "Your order for 0.1 BTC has been filled",
      "data": {
        "order_id": "uuid",
        "symbol": "BTCUSDT"
      },
      "is_read": false,
      "created_at": "2026-07-09T10:00:00Z"
    }
  ],
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z",
    "total": 1,
    "unread_count": 1
  }
}
```

---

### 10.2 Mark Notification as Read

**Endpoint**: `POST /notifications/{notification_id}/read`

**Description**: Mark a notification as read.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "is_read": true,
    "read_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

### 10.3 Mark All Notifications as Read

**Endpoint**: `POST /notifications/read-all`

**Description**: Mark all notifications as read.

**Headers**: `Authorization: Bearer {token}`

**Response** (200 OK):
```json
{
  "data": {
    "message": "All notifications marked as read"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

## 11. ADMIN ENDPOINTS

### 11.1 List All Users

**Endpoint**: `GET /admin/users`

**Description**: List all users (admin only).

**Headers**: `Authorization: Bearer {admin_token}`

**Query Parameters**:
- `subscription_tier` (optional): Filter by subscription tier
- `is_active` (optional): Filter by active status
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Offset for pagination (default: 0)

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "full_name": "John Doe",
      "subscription_tier": "pro",
      "is_active": true,
      "created_at": "2026-07-09T10:00:00Z"
    }
  ],
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z",
    "total": 1
  }
}
```

---

### 11.2 Update User Status

**Endpoint**: `PATCH /admin/users/{user_id}/status`

**Description**: Update user active status (admin only).

**Headers**: `Authorization: Bearer {admin_token}`

**Request Body**:
```json
{
  "is_active": false
}
```

**Response** (200 OK):
```json
{
  "data": {
    "id": "uuid",
    "is_active": false,
    "updated_at": "2026-07-09T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

### 11.3 Get System Stats

**Endpoint**: `GET /admin/stats`

**Description**: Get system statistics (admin only).

**Headers**: `Authorization: Bearer {admin_token}`

**Response** (200 OK):
```json
{
  "data": {
    "total_users": 1000,
    "active_users": 800,
    "total_trading_instances": 150,
    "active_trading_instances": 100,
    "total_orders_today": 5000,
    "total_volume_today": 1000000.0
  },
  "meta": {
    "timestamp": "2026-07-09T10:00:00Z"
  }
}
```

---

## 12. ERROR CODES

| Code | HTTP Status | Description |
|------|------------|-------------|
| VALIDATION_ERROR | 400 | Invalid input data |
| INVALID_CREDENTIALS | 401 | Invalid email or password |
| UNAUTHORIZED | 401 | Missing or invalid authentication token |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| EMAIL_EXISTS | 409 | Email already registered |
| INVALID_STATUS | 409 | Invalid status for operation |
| INSUFFICIENT_BALANCE | 400 | Insufficient balance |
| INVALID_EXCHANGE | 400 | Invalid exchange name |
| INVALID_API_CREDENTIALS | 400 | Invalid API credentials |
| CONNECTION_FAILED | 503 | Failed to connect to exchange |
| CANCEL_FAILED | 503 | Failed to cancel order |
| INTERNAL_ERROR | 500 | Internal server error |

---

## 13. RATE LIMITING

| Endpoint | Rate Limit |
|----------|------------|
| Auth endpoints | 10 requests per minute |
| Trading endpoints | 100 requests per minute |
| Data endpoints | 200 requests per minute |
| Admin endpoints | 50 requests per minute |

**Rate Limit Headers**:
- `X-RateLimit-Limit`: Rate limit per window
- `X-RateLimit-Remaining`: Remaining requests in window
- `X-RateLimit-Reset`: Unix timestamp when window resets

---

## 14. WEBSOCKET ENDPOINTS

### 14.1 Connection

**Endpoint**: `wss://api.utos.com/ws`

**Authentication**: Send JWT token in query parameter: `?token={jwt_token}`

### 14.2 Subscribe to Updates

**Message**:
```json
{
  "action": "subscribe",
  "channels": [
    "orders",
    "portfolio",
    "trading_instance:{instance_id}"
  ]
}
```

### 14.3 Event Messages

**Order Filled**:
```json
{
  "channel": "orders",
  "event": "ORDER_FILLED",
  "data": {
    "order_id": "uuid",
    "symbol": "BTCUSDT",
    "filled_quantity": 0.1,
    "average_fill_price": 50000.0
  },
  "timestamp": "2026-07-09T10:00:00Z"
}
```

**Portfolio Update**:
```json
{
  "channel": "portfolio",
  "event": "PORTFOLIO_UPDATE",
  "data": {
    "total_value": 5100.0,
    "total_pnl": 100.0,
    "pnl_percentage": 2.0
  },
  "timestamp": "2026-07-09T10:00:00Z"
}
```

---

## 15. API VERSIONING STRATEGY

- Current version is `/api/v1`.
- Backward-compatible changes remain in v1.
- Breaking changes require a new version (e.g., `/api/v2`).
- Maintain two live versions simultaneously during transition periods.
- Deprecated endpoints return `Sunset` header with removal date.

---

## 16. CHANGE LOG

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-09 | 1.0.0 | Initial API specification |
| 2026-07-09 | 2.0.0 | Architecture revision: Trading Instance, /prepare endpoint, ProcessMemory, TP/ProfitLock/PortfolioLock separation, API versioning strategy |
