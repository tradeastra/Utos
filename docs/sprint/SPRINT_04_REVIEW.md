# Sprint 4 Review — Binance Spot Adapter

> Review ini dibuat **sebelum** merge PR Sprint 4 ke `develop`.  
> Tujuan: mengumpulkan fakta implementasi, kekurangan, dan risiko agar keputusan merge bersih dan terdokumentasi.

---

## Executive Summary

| Aspek | Status | Catatan |
|-------|--------|---------|
| Adapter Independence | **OK** | Semua logika Binance tertahan di `backend/exchanges/adapters/binance.py`. Komponen generik (`HttpClient`, `WebSocketManager`, `RateLimiter`, `RetryPolicy`, `ErrorMapper`, `ExchangeFactory`) tidak mengandung string `"binance"` maupun `if exchange == "binance"`. |
| Binance API Coverage (scope Sprint 4) | **OK** | Account, Balance, Order, Cancel, Open Orders, Symbol Info, Exchange Info, User Stream, Ticker, OrderBook, Candles, Trades tersedia. |
| HMAC-SHA256 Signature | **OK** | Helper `BinanceAuthenticator.sign()` terpisah. |
| Timestamp Drift | **PASS** | `recvWindow` dikirim dan `_signed_request` akan auto-resync server time sekali saat menerima `-1021`, lalu retry. |
| Retry Policy | **OK** | Hanya status `429/5xx`, timeout, dan network error yang di-retry. Error auth (`-1022`, `-2014`, `-2015`) langsung raise. |
| WebSocket Reconnect | **PASS** | `WebSocketManager` sekarang mendeduplikasi subscription dan menyimpan subscription **per URL**, sehingga market stream dan account stream tidak berbagi collection. Adapter menggunakan `ws` untuk market dan `ws_account` untuk user stream. |
| Rate Limiting | **Partial** | Token bucket aktif, tetapi belum menggunakan **endpoint weight** dari Binance dan belum ada **queue** eksplisit. |
| Test Suite | **OK** | **210 kasus uji PASS** (termasuk ~85 kasus baru/updated untuk Binance adapter dan WebSocket manager). |
| Merge Recommendation | **APPROVE** | Semua blocker fondasi telah terselesaikan; PR siap merge ke `develop`. |

---

## 1. API yang Sudah Diimplementasikan

### REST API (Binance Spot)

| Fungsi Adapter | Endpoint | Method | Keterangan |
|----------------|----------|--------|------------|
| `authenticate()` / `_sync_time()` | `/api/v3/time` | GET | Sinkronisasi timestamp server. |
| `authenticate()` / `get_account()` | `/api/v3/account` | GET | Akun + balance mentah. |
| `get_exchange_info()` / `get_symbol_info()` | `/api/v3/exchangeInfo` | GET | Metadata simbol, lot size, filters. Di-cache di `_exchange_info`. |
| `get_ticker()` | `/api/v3/ticker/bookTicker` + `/api/v3/ticker/24hr` | GET | Gabungan bid/ask dan statistik 24 jam. |
| `get_order_book()` | `/api/v3/depth` | GET | Order book dengan `limit`. |
| `get_candles()` | `/api/v3/klines` | GET | OHLCV. |
| `get_trades()` | `/api/v3/trades` | GET | Public recent trades. |
| `place_order()` | `/api/v3/order` | POST | Limit/market + parameter stop/iceberg/clientOrderId opsional. |
| `get_order()` | `/api/v3/order` | GET | Status order. |
| `cancel_order()` | `/api/v3/order` | DELETE | Cancel per order. |
| `get_open_orders()` | `/api/v3/openOrders` | GET | Daftar order terbuka. |
| `cancel_all()` | `/api/v3/openOrders` | DELETE | Cancel per simbol; tanpa simbol iterasi `get_open_orders()`. |
| `connect_account()` / `_keepalive_loop()` | `/api/v3/userDataStream` | POST / PUT | Listen key untuk user stream. |
| `health_check()` | `/api/v3/time` | GET | Cek konektivitas. |

### WebSocket API

| Fungsi Adapter | Stream | Arah |
|----------------|--------|------|
| `subscribe_ticker()` | `<symbol>@ticker` | Market |
| `subscribe_orderbook()` | `<symbol>@depth` | Market |
| `subscribe_user_data()` | `<listenKey>` | Account |
| `unsubscribe_ticker()` / `unsubscribe_orderbook()` | Unsubscribe message | Market |

### IExchangeAdapter Interface

Semua method abstrak yang relevan untuk Spot diimplementasikan:

- `initialize()`, `authenticate()`, `connect_market()`, `connect_account()`, `disconnect()`
- `get_account()`, `get_balance()`, `get_exchange_info()`, `get_symbol_info()`, `get_positions()`
- `place_order()`, `get_order()`, `cancel_order()`, `cancel_all()`, `get_open_orders()`
- `get_ticker()`, `get_order_book()`, `get_candles()`, `get_trades()`
- `subscribe_market()`, `unsubscribe_market()`, `subscribe_account()`, `unsubscribe_account()`
- `health_check()`

Catatan: `get_positions()` mengembalikan `[]` karena adapter ini **Spot-only**.

---

## 2. API Binance yang Belum Didukung

API berikut **belum** diimplementasikan dan tidak masuk scope Sprint 4. Perlu diprioritaskan ulang di sprint berikutnya jika diperlukan oleh Trading Process Manager / Market Data Hub:

### Trading Lanjutan
- OCO / OTOCO orders (`/api/v3/order/oco`)
- Trailing stop orders
- Batch orders (`/api/v3/batchOrders`)
- Test order endpoint (`/api/v3/order/test`) untuk pre-flight validasi

### Market Data Lanjutan
- Aggregate trades (`/api/v3/aggTrades`)
- Historical trades (butuh `X-MBX-APIKEY`)
- Premium index / funding rate (futures, tidak relevan untuk Spot)
- Partial book depth levels (e.g., `<symbol>@depth5`, `@depth10`, `@depth20`)
- Individual symbol mini ticker / all symbols tickers

### Account & Wallet
- My trades (`/api/v3/myTrades`)
- Deposit history / withdraw history
- Account status / trading status / API restrictions
- User asset / capital config (`/sapi` tidak tersentuh)

### Margin / Futures / Options
- Tidak ada dukungan cross-margin atau isolated-margin.
- Tidak ada futures USD-M / COIN-M.
- Tidak ada options.

### Rekomendasi
Untuk Sprint 5 (Trading Process Manager), yang paling mungkin dibutuhkan adalah **my trades** dan **test order**, tapi keduanya dapat ditambahkan sebagai incremental PR tanpa mengganggu fondasi adapter.

---

## 3. Error yang Ditangani

### HTTP Status & Binance Error Code

| Kondisi | Mapping | Keterangan |
|---------|---------|------------|
| HTTP `429` atau code `-1003`, `-1015` | `ExchangeRateLimitError` | Rate limit request/order. |
| HTTP `418` | `ExchangeRateLimitError` | IP banned oleh Binance. |
| Code `-1021` | `ExchangeError` (`error_code="TIMESTAMP_DRIFT"`) | Timestamp drift / outside recvWindow. `_signed_request` otomatis `_sync_time()` sekali dan retry; jika masih gagal, raise `ExchangeError`. |
| Code `-1022`, `-2014`, `-2015` | `AuthenticationError` | Invalid signature atau API key. Tidak di-retry. |
| Code `-2013` | `OrderNotFound` | Order tidak ditemukan. |
| Code `-2010` + pesan mengandung "balance" | `InsufficientBalanceError` | Saldo tidak cukup. |
| Code `-1120`, `-1121` | `SymbolNotSupported` | Simbol tidak valid. |
| HTTP `>= 500` | `ExchangeConnectionError` | Server error, masuk retry loop. |
| Lainnya / JSON tidak valid | `ExchangeError` | Fallback generik. |

### Network-Level

| Kondisi | Perilaku |
|---------|----------|
| `httpx.TimeoutException` | Retry sesuai `RetryPolicy`, akhirnya raise `TimeoutError`. |
| `httpx.NetworkError` / `httpx.ConnectError` | Retry, akhirnya raise `ExchangeConnectionError`. |
| Connection reset / broken pipe | Ditangkap oleh `httpx.NetworkError` dan di-retry. |

### WebSocket

- Disconnect dan reconnect ditangani oleh `WebSocketManager`.
- Pesan yang tidak dikenali (`_dispatch`) di-log debug dan diabaikan.
- Event `outboundAccountPosition`, `executionReport`, `balanceUpdate` diteruskan ke user callback.

---

## 4. Error yang Belum Ditangani

| Error / Skenario | Alasan Tidak Ditangani | Risiko |
|------------------|------------------------|--------|
| **HTTP `451` / `-1008` / `-1009` (server overload / maintenance)** | Tidak ada mapping khusus; jatuh ke `ExchangeError`. | Pesan error kurang informatif, tapi tidak fatal karena retry 5xx masih bekerja. |
| **WebSocket error code khusus Binance** | Manager hanya reconnect untuk `ConnectionClosed`; error parsing frame tidak dimapping ke domain exception. | Caller tidak mendapat exception domain untuk error WS. |
| **Order cancellation rejected karena order sudah filled** | Response order status di-mapping apa adanya; tidak ada exception khusus. | Trading engine perlu memeriksa status sendiri. |
| **Dust order / LOT_SIZE / MIN_NOTIONAL** | Filter simbol tidak diterapkan sebelum place order. | Order bisa ditolak oleh Binance; harusnya ditangani oleh engine dengan data dari `get_symbol_info()`. |
| **Listen key expired** | `_keepalive_loop` hanya PUT setiap 30 menit; tidak mendeteksi error expired saat WS receive. | User stream bisa diam tanpa notifikasi jika keep-alive gagal diam-diam. |

---

## 5. Known Limitations (Keterbatasan Diketahui)

1. **Spot-only**  
   `get_positions()` selalu kosong. Leverage, short, margin, futures tidak didukung.

2. **Rate limiter belum weight-aware**  
   `RateLimiter` memakai token bucket, tetapi setiap request dikonsumsi 1 token saja. Binance menggunakan **weight** per endpoint (contoh: `exchangeInfo` = 20, `account` = 10). Belum ada parsing header `X-MBX-USED-WEIGHT-1M` atau `Retry-After`.

3. **Quote asset heuristic**  
   `_quote_asset()` memakai heuristic sederhana (3–4 karakter terakhir). Simbol non-USDT seperti `BTCBRL` atau token length anomali bisa salah.

4. **No real integration test**  
   Semua tes menggunakan `AsyncMock`. Tidak ada pengujian nyata terhadap Binance Testnet.

5. **Order result average price**  
   `average_fill_price = cummulativeQuoteQty / executedQty`. Logika ini benar untuk fill normal, tapi tidak memperhitungkan fee/rebate Binance.

---

## 6. Technical Debt

### Debt yang Bisa Ditangani di Sprint 5 (Ringan)
1. **Logging / health check listen key**: deteksi error saat PUT keepalive agar user stream dapat reconnect segera jika listen key expired.

### Debt Menengah
1. **Weight-aware rate limiter**: parsing response header atau konfigurasi weight per endpoint, lalu `acquire(endpoint, weight)`.
2. **Quote asset resolver** yang mengambil dari `exchangeInfo.symbols.quoteAsset` alih-alih heuristic.
3. **Listen key expiration handling**: reconnect user stream otomatis saat listen key expired.

### Debt Besar (Tidak Urgent untuk Sprint 5)
1. Dukungan margin/futures memerlukan adapter terpisah atau perluasan konfigurasi.
2. Dukungan batch orders dan OCO.
3. Redis-backed rate limiter untuk multi-instance deployment.

---

## 7. Test Coverage

### Unit Tests

File utama: `backend/tests/test_unit/test_binance_adapter.py`

| Kelas Uji | Jumlah Kasus Uji | Fokus |
|-----------|------------------|-------|
| `TestBinanceAdapterConstruction` | 4 | Factory registration, default instantiation, dependency injection |
| `TestBinanceAuthenticator` | 4 | HMAC sign, headers, timestamp offset, set credentials |
| `TestBinanceLifecycle` | 9 | initialize, authenticate, connect, disconnect, health check |
| `TestBinanceSignatureAndTimestamp` | 7 | Signature di GET/POST/DELETE, offset, `recvWindow`, unauthenticated guard |
| `TestBinanceErrorMapping` | 13 | Mapping 12 error code + network timeout |
| `TestBinanceTimestampResync` | 2 | Auto-resync saat `-1021` dan persistence drift |
| `TestBinanceAccount` | 6 | Account, balance, exchange info, symbol info |
| `TestBinanceMarketData` | 4 | Ticker, order book, candles, trades |
| `TestBinanceOrders` | 7 | Place, get, cancel, open orders, cancel all |
| `TestBinanceWebSocket` | 12 | Subscribe/unsubscribe/dispatch, deduplication, market vs user stream separation |
| `TestBinanceCertification` | 10 | Exchange Certification checklist Sprint 4 |
| `TestBinanceEdgeCases` | 4 | Custom URL, avg price, cache, positions |
| **Total Project** | **210 PASS** | Semua test suite project (termasuk adapter, exchanges, API, repositories, core). |

### Coverage yang Lemah / Butuh Penambahan
- Rate limiter weight parsing.
- Order placement dengan filter LOT_SIZE / MIN_NOTIONAL.
- Integration test live ke Binance Testnet.

---

## 8. Risiko untuk Sprint 5

### Risiko Tinggi
*Tidak ada risiko tinggi yang tersisa setelah perbaikan Sprint 4.*

### Risiko Sedang
1. **Rate limit weight tidak terhitung**  
   Polling berat (misalnya `get_open_orders()` per simbol untuk banyak simbol) bisa memicu rate limit lebih cepat dari prediksi token bucket. Diperlukan integrasi weight header atau conservative default.

2. **Listen key expiration diam-diam**  
   User stream yang berhenti karena listen key expired tidak memberi sinyal eksplisit ke Trading Process Manager. Perlu health check dan reconnect user stream.

3. **Spot-only mengikat strategi**  
   Jika roadmap nanti memerlukan margin/futures, `BinanceSpotAdapter` tidak bisa langsung dipakai. Trading Process Manager harus memastikan hanya simbol Spot yang digunakan.

### Risiko Rendah
4. **`_quote_asset()` heuristic**  
   Bisa menghasilkan `fee_currency` salah untuk simbol non-standar. Dampak terbatas pada PnL/fee reporting.

5. **Ketergantungan pada testnet Binance**  
   Testnet URL sudah dikonfigurasi, tapi belum ada pengujian live. Jika testnet berbeda perilaku dengan mainnet (misalnya delay), baru akan terdeteksi saat staging.

---

## 9. Review Checklist Hasil

| # | Poin Review | Status |
|---|-------------|--------|
| 1 | Adapter tidak mempengaruhi interface umum | **PASS** |
| 2 | Binance API Coverage minimal 10 endpoint utama | **PASS** |
| 3 | HMAC SHA256 di helper terpisah | **PASS** |
| 4 | Timestamp drift: server time → offset → auto sync | **PASS** |
| 5 | Retry hanya untuk timeout/429/5xx, tidak untuk auth | **PASS** |
| 6 | WebSocket reconnect tanpa duplikat subscription | **PASS** |
| 7 | Rate limit: weight → token bucket → queue | **PARTIAL** (token bucket aktif, weight & queue belum) |

---

## 10. Rekomendasi Merge

**Sprint 4 Approved — PR siap merge ke `develop`.**

Semua acceptance criteria tambahan telah terpenuhi:

- ✅ 200+ test PASS (210 PASS).
- ✅ Auto-resync timestamp saat `-1021`.
- ✅ WebSocket deduplication.
- ✅ Market/User stream terpisah.
- ✅ Configurable `recvWindow`.
- ✅ Tidak ada perubahan pada `IExchangeAdapter`.
- ✅ Tidak ada breaking change.

**Tindak lanjut setelah merge:**
1. Merge `sprint-4` → `develop`.
2. Jalankan audit akhir dan commit.
3. Lanjut ke Sprint 5: Trading Process Manager.

---

*Dokumen ini diperbarui setelah fix PR Sprint 4. Status: **Ready for Merge**.*
