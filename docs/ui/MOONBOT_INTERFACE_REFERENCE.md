# Moonbot Interface Reference

**Status:** Draft — akan terus dilengkapi seiring tambahan foto/screenshot.
**Purpose:** Dokumen ini menangkap pola UI/UX, layar, dan aturan bisnis yang terlihat dari aplikasi referensi Moonbot, sebagai masukan untuk desain/kelengkapan UTOS.

---

## Screen Inventory (Current)

| # | Screen | Gambar | Fokus Utama |
|---|--------|--------|-------------|
| 1 | Trade / Portfolio | 1 | Daftar aset yang aktif/tidak aktif, harga, profit, posisi terbuka |
| 2 | Moonbot Setting | 2 | Strategy mode & coin group selection |
| 3 | Money Management | 3 | Parameter capital, MM preset, buy amount, max coin, volume filter |
| 4 | Account / Profile | 4 | Informasi akun, voucher, notifikasi, withdrawal address |
| 5 | Home / Dashboard | 5 | Ringkasan saldo, volume, kredit, menu utama |
| 6 | Moonbot Setting (extended) | 6 | Update money management, technical analysis, pause |
| 7 | Coin / Position Detail | 7 | Detail BTC, Force Buy/Sell, grid metrics, settings |
| 8 | Averaging Formula | 8 | Formula buy amount, limit, TP, trailing profit, TA |
| 9 | Averaging Configuration (top) | 9 | Tabel step 1-16: drop rate, multiplier, take profit |
| 10 | Averaging Configuration (bottom) | 10 | Tabel step 20-35: drop rate, multiplier, take profit |

---

## 1. Trade Screen (Portfolio / Open Position)

### Header
- **Title:** Trade
- **Search bar** dengan tombol **Clear**
- **Filter chips:** Price, Change, Profit — Change aktif/terpilih (berwarna ungu)
- **Exchange selector:** Binance (icon + label + icon info `i`)

### Table Header
- Name/Qty
- Price/24H Change
- Profit/Floating

### Row Content (per coin)
| Field | Contoh |
|-------|--------|
| Status dot | Active (hijau) / Inactive (merah) |
| Label | `TOP` (kuning/bintang) |
| Pair | BTC/USDT, BNB/USDT, ETH/USDT, ADA/USDT, SOL/USDT, XRP/USDT, DOT/USDT |
| Quantity | `0.00048`, `0.26120`, `0` |
| Price | `$64882`, `$570.97`, `$1880.09`, `$0.1662`, `$76.92`, `$1.1026`, `$0.814` |
| 24H Change | `0.08%`, `-0.00%`, `0.40%`, `-1.19%`, `0.89%`, `0.54%`, `-2.75%` (hijau/merah) |
| AVG status | `AVG: ON` (hijau) untuk semua baris |
| Profit/Floating | `0.6% / 0.19 USDT`, `-4.15% / -6.45 USDT`, `0% / 0 USDT` |

### Footer / Bottom Sheet
- Tombol expand `^` / `vv`
- Indicator: **2/2 Open Position**
- Bottom navigation: **Home** | **Trade**

### UI Patterns
- **Status badge** dengan dot kecil dan teks Active/Inactive.
- **TOP badge** untuk coin unggulan.
- **Profit positif** = hijau, **negatif** = merah.
- **AVG: ON** sebagai indikator averaging aktif.

---

## 2. Moonbot Setting — Strategy Mode & Coin Groups

### Strategy Mode (Radio Group)
| Code | Mode | Daily Range | Risk Level | Badge |
|------|------|-------------|------------|-------|
| A | Super Bearish | 0 – 0.3% | Very Low Risk | — |
| B | Conventional | 0 – 0.6% | Low Risk | — |
| C | Aggressive | 0 – 0.7% | Medium Risk | — |
| D | Very Aggressive | 0 – 1.5% | High Risk | selected |
| U | Ultimate | 0 – 1.5% | Very Low Risk | `New` |

- Strategy aktif: **D** (Very Aggressive)
- Disclaimer bawah: `*Result May Vary Due to the Fluctuations`
- Link: `Learn more`

### Coin Groups (Radio Group)
| Group | Coins | Option Button |
|-------|-------|---------------|
| 3 Kings | BTC, BNB, ETH | selected |
| 5 Kings | BTC, BNB, ETH, SOL and XRP | — |
| Top 10 | BTC, BNB, ETH and more | Option |
| Top 20 | BTC, BNB, ETH and more | Option |
| Top 50 | BTC, BNB, ETH and more | Option |
| All | All coins | — |

- Group aktif: **3 Kings**
- Badge `New` muncul di area Coin Groups.
- Timestamp filter: `*You have chosen this group coin filter at : 1970-01-01`

### UI Patterns
- Radio button list dengan detail di kanan.
- **Badge `New`** untuk fitur baru.
- **Risk level** sebagai label sekunder (Very Low Risk, Low Risk, Medium Risk, High Risk).
- **Info icon `i`** di header setiap section.

### Money Management Update (Scroll Lanjutan)
- **Minimum Volume (Last 24H)** input: `100,000,000` dengan prefix icon dollar.
- Tombol aksi: **UPDATE MONEY MANAGEMENT** (ungu penuh lebar).
- Link bawah: `Learn more about Money Management.`

### Technical Analysis
- Header dengan icon bintang: `Technical Analysis`.
- Toggle/switch untuk mengaktifkan/nonaktifkan Technical Analysis.
- **Technical Analysis 1**
  - Dropdown: `Fibonacci Retracement`.
  - Time Frame: `15M`.
- **Operator**
  - Dropdown: `OR` (kemungkinan pilihan AND/OR).
- **Technical Analysis 2**
  - Dropdown: `MACD`.
  - Time Frame: `15M`.
- Tombol aksi: **UPDATE TECHNICAL ANALYSIS** (ungu penuh lebar).
- Tombol aksi: **PAUSE** (merah penuh lebar).

### UI Patterns (Extended Moonbot Setting)
- Tombol **Update** ungu untuk setiap section konfigurasi.
- Tombol **PAUSE** merah menonaktifkan bot — muncul di beberapa screen strategi.
- Technical Analysis dapat menggabungkan 2 indikator dengan operator logika.

---

## 3. Money Management

### Section Header
- **Money Management** dengan info icon `i`

### Input Fields
| # | Field | Value / Notes |
|---|-------|---------------|
| 1 | Capital (USDT) | Input kosong, prefix icon USDT |
| 2 | Select MM (Money Management) Preset | Radio group: MM30, MM50, MM70, Custom |

### MM Preset Options
| Preset | Steps | Keterangan |
|--------|-------|------------|
| MM30 | 30 | — |
| MM50 | 50 | **selected** |
| MM70 | 70 | — |
| Custom | 10 – 100 | Input: `10-100` |

### Action Button
- **Calculate** — tombol ungu penuh lebar

### Output Fields (hasil kalkulasi)
| Field | Value | Icon |
|-------|-------|------|
| Buy Amount (USDT) | 15 | USDT |
| Max Coin | 2 | Dollar |
| Minimum Volume (Last 24H) | 100,000,000 | Dollar |

### Notes / Business Rules
- Buy amount must be at least **15 USDT**.
- Requires **Coin Group setup**.
- **MM30** can only be selected if Coin Group is **3 Kings** or **Top 5**.

### UI Patterns
- Input dengan icon prefix di kiri.
- Tombol aksi utama ungu.
- Section output yang terpisah di bawah tombol Calculate.
- Catatan aturan bisnis dalam bullet list di bawah form.

---

## 4. Account / Profile Screen

### Menu Cards (Group atas)
| Menu | Icon | Badge |
|------|------|-------|
| Cashback | Star/coin | — |
| Moonbot Setting | Logo flame | — |
| BNB Fee Setting | Invoice + coin | — |

### Information Section
| Field | Value | Status/Action |
|-------|-------|---------------|
| Phone | Verified | Badge biru check |
| Star Level | `-` | — |
| Expired At | Thu, Jun 24, 2027, 21:18:22 | — |
| Withdraw Address | Warning kuning | Tombol merah: **ADD WITHDRAWAL ADDRESS** |
| Voucher Plan | B+ | Tombol ungu: **UPGRADE** |
| Telegram Notification | Connected | Teks hijau + icon `X` (disconnect) |

### UI Patterns
- Card menu dengan icon rounded di kiri dan chevron `>` di kanan.
- **Status badge** (`Verified`, `Connected`).
- **Warning state** untuk data yang belum lengkap (withdrawal address).
- **CTA upgrade** di dalam baris informasi.

---

## 5. Home / Dashboard

### Header
- Logo **MOONBOT** di kiri
- Exchange selector: **Exchanger** → **Binance** (dropdown)
- Icon notifikasi (bell) dengan badge angka
- Hamburger menu (3 garis)

### Balance Cards
| Card | Value | Keterangan |
|------|-------|------------|
| USDT | 838.1358 | icon refresh |
| Coin Asset | 180.284 USDT | — |
| My Trading Volume (D-1) | 108.8926 USDT | navigasi ke detail `>` |

### Credit Banner
- **Credit: $85.058**
- Link: **Recharge Now** (hijau) + info icon `i`

### Quick Actions (icon + label)
- API
- Credit
- Profit
- FAQ

### Banner Promo
- **MOONBOT MOBILE APP** — “One App. All Your Trades.” + CTA Google Play **GET THE APP**

### Main Menu Cards
- Saving
- Cashback
- Moonbot Setting
- Fee Setting (terpotong di bagian bawah)

### Bottom Navigation
- Home (aktif, ungu)
- Trade

### UI Patterns
- Dashboard ringkas dengan metric utama di atas.
- **Icon grid** untuk aksi cepat.
- **Promo banner** horizontal.
- **Bottom nav** tetap hanya 2 tab: Home & Trade.

---

## 6. Coin / Position Detail (BTC)

### Header
- **Back button** kiri, icon chart & notifikasi di kanan.

### Price Card
| Field | Value |
|-------|-------|
| Coin | BTC |
| Price | $64858.6 |
| Exchanger | Binance |
| Amount | $30.957744 |
| Avg Price | 64495.3 |
| Step | 1 |
| Quantity | 0.00048 |
| Change | 0.56% |

### Manual Action Buttons
- **FORCEBUY** — tombol hijau (buy manual paksa).
- **FORCESELL** — tombol merah (sell manual paksa).

### Grid / Averaging Metrics
| Metric | Value |
|--------|-------|
| Next Step Price | 63914.20994 |
| Drop Rate for Next Step | 0.6% |
| Take Profit Price | 65333.7389 |
| Take Profit Percentage | 1.3% |
| Buy Amount | 15 |
| Averaging Limit | 35 |

### Per-Coin Settings (Icon Grid)
| Setting | Icon | Status |
|---------|------|--------|
| Avg | Balance scale | ON |
| Moon Logic | Shield | `New` badge |
| Formula | Wrench | — |
| Non-Stop | Traffic light | — |
| Partial | Box | — |

### Action Button
- **PAUSE** — tombol kuning penuh lebar.

### UI Patterns
- Card besar di atas untuk ringkasan posisi coin.
- **Dual CTA** berdampingan: Force Buy (hijau) & Force Sell (merah).
- **Metric list** dengan icon di kiri dan angka di kanan.
- **Icon grid** untuk toggle fitur per coin.
- Tombol **PAUSE** kuning muncul di level detail coin (berbeda warna dengan Pause merah di setting).

---

## 7. Averaging Formula

### Input Fields
| Field | Value | Unit |
|-------|-------|------|
| Buy Amount | 15 | USDT |
| Averaging Limit | 35 | Steps |
| Take Profit Percentage | 1.3 | % |

### Navigation Cards
- **Averaging Configuration** — card dengan icon gear + chevron `>`.
- **Trailing Profit** — card dengan icon + badge `New` + toggle switch.

### Technical Analysis
- Toggle switch: **ON** (hijau).
- **Technical Analysis 1**: `Fibonacci Retracement` | Time Frame `15M`.
- **Operator**: `OR`.
- **Technical Analysis 2**: `MACD` | Time Frame `15M`.

### Action Button
- **SAVE** — tombol ungu penuh lebar.

### UI Patterns
- Input dengan unit suffix di kanan (`USDT`, `Steps`, `%`).
- Card toggle fitur baru dengan badge `New`.
- Technical Analysis toggle ON/OFF mengontrol visibilitas section TA.

---

## 8. Averaging Configuration

### Table Header
| Step | Drop Rate | Multiple Buy Amount | Take Profit |
|------|-----------|---------------------|-------------|

### Table Rows (1-35)
| Step | Drop Rate | Multiple Buy Amount | Take Profit |
|------|-----------|---------------------|-------------|
| 1 | 0.6% | 1 X | 1.3% |
| 2 | 0.6% | 1 X | 1.3% |
| 3 | 0.6% | 1 X | 1.3% |
| 4 | 0.6% | 1 X | 1.3% |
| 5 – 14 | 1.2% | 1 X | 1.3% |
| 15 – 16 | 1.1% | 1 X | 1.3% |
| 17 – 19 | 1.0% | 1 X | 1.3% |
| 20 | 1.1% | 1 X | 1.3% |
| 21 – 25 | 1.0% | 1 X | 1.3% |
| 26 – 35 | 2.0% | 1 X | 1.3% |

### Action Buttons
- **RESET AVG** — merah (reset ke default).
- **CHANGE ALL** — kuning (bulk edit semua baris).
- **SAVE** — ungu (simpan konfigurasi).

### UI Patterns
- Tabel grid editable dengan input field per cell.
- **Multiple Buy Amount** format: `{nilai} X` (multiplier terhadap buy amount base).
- Tombol aksi tersusun: secondary (Reset/Change) di atas, primary Save di bawah.
- Screen ini di-scroll secara vertikal karena jumlah step banyak (35 steps).

---

## Cross-Screen Patterns

- **Color theme:** Ungu dominant + putih, aksen hijau (profit/positif/success), merah (loss/warning), kuning (TOP badge).
- **Typography:** Angka besar untuk saldo/harga, teks kecil untuk label.
- **Iconography:** Icon prefix pada input (USDT, dollar), icon status (verified, connected), icon info `i`.
- **Navigation:** Bottom tab hanya 2 item — Home & Trade. Drawer/hamburger menu untuk halaman lain.
- **Status indicators:**
  - Active/Inactive dot
  - Verified badge
  - Connected badge
  - New badge
  - Warning badge untuk setup yang belum lengkap.
- **Exchange selector:** Muncul di Home & Trade.
- **Disclaimer:** Selalu ada note/disclaimer terkait risiko / hasil bervariasi.

---

## Business Rules & Constraints Observed

1. **Minimum buy amount:** 15 USDT.
2. **MM30 restriction:** hanya untuk grup `3 Kings` atau `Top 5`.
3. **Coin group setup required** sebelum Money Management bisa digunakan.
4. **Withdrawal address** wajib ditambahkan jika belum ada (warning).
5. **Strategy mode** menentukan rentang harian dan level risiko.
6. **AVG (averaging)** bisa aktif/non-aktif per coin di Trade screen.
7. **Technical Analysis** dapat menggabungkan 2 indikator dengan operator logika (`OR`/`AND`) dan time frame per indikator (contoh: `15M`).
8. **Per-position/coin metrics:** Step, Next Step Price, Drop Rate, Take Profit Price, Take Profit Percentage, Buy Amount, Averaging Limit.
9. **Averaging Limit** menentukan jumlah step maksimal (contoh: 35 steps).
10. **Trailing Profit** adalah fitur toggleable (badge `New`).
11. **Force Buy / Force Sell** tersedia untuk intervensi manual per coin.
12. **Averaging Configuration** mengizinkan customisasi per step: Drop Rate, Multiple Buy Amount, dan Take Profit.

---

## Pending / Will Be Completed

- [x] Foto detail halaman Coin/Position Detail (BTC).
- [x] Foto detail Averaging Formula & Configuration.
- [x] Foto detail Technical Analysis setting.
- [ ] Foto detail halaman Saving, Cashback, Profit, FAQ.
- [ ] Foto detail API configuration & exchange connection.
- [ ] Foto detail deposit/withdraw flow.
- [ ] Foto detail order history & transaction log.
- [ ] Foto notifikasi / Telegram setup.
- [ ] Foto dark mode / light mode (jika ada).
- [ ] Foto splash screen / onboarding.

---

## Notes for UTOS Implementation

- Pantau agar **top navigation** (exchange selector) dan **bottom navigation** konsisten di seluruh screen.
- Pertimbangkan **status badge** dan **warning state** untuk setup yang belum lengkap.
- Pertahankan **disclaimer risiko** di area strategy & money management.
- Design system perlu mendefinisikan color token: ungu utama, hijau profit, merah loss, kuning badge, abu-abu inaktif.
