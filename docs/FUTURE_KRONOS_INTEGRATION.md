# FUTURE INTEGRATION PLAN: Kronos Foundation Model

**Status:** PLANNING ONLY — NOT IMPLEMENTED
**Created:** 2026-07-28
**Owner:** UTOS Team
**Trigger Condition:** Evaluated only if current strategy underperforms in live trading

---

## 1. PURPOSE

Dokumen ini adalah **contingency plan** untuk integrasi Kronos (financial foundation model)
ke UTOS, **bukan komitmen implementasi**. Bot trading UTOS saat ini dirancang untuk berjalan
tanpa dependensi ML berat. Dokumen ini disimpan agar:

- Jika performa UTOS sudah bagus → file ini bisa diabaikan / diarsipkan tanpa beban
- Jika suatu saat dibutuhkan sinyal prediktif tambahan → tim sudah punya blueprint siap pakai
- Tidak ada risiko "tergoda" memasukkan ML premature yang menambah kompleksitas & biaya GPU

**Decision rule:** Jangan implementasi sebelum UTOS v1.0 stable minimal 3 bulan di production
dan menunjukkan underperformance yang terukur (Sharpe < target, drawdown berlebih, atau
missed opportunity yang signifikan).

---

## 2. APA ITU KRONOS (Ringkasan)

- Foundation model (pre-trained Transformer) khusus K-line / candlestick OHLCV
- Dilatih dari 45+ exchange global, 12 miliar K-line records
- Two-stage: tokenizer hirarkis diskrit + autoregressive Transformer
- Output: prediksi N candle ke depan (probabilistik via sampling)
- 4 varian: mini (4.1M), small (24.7M), base (102.3M), large (499M, belum dirilis)

Repo: https://github.com/shiyu-coder/Kronos
Models: https://huggingface.co/NeoQuasar

---

## 3. LISINSI — SUDAH DIAUDIT (Status: AMAN komersial)

| Komponen | Lisensi | Catatan |
|---|---|---|
| Source code (upstream `shiyu-coder`) | MIT | Copyright (c) 2025 ShiYu |
| Source code (fork `andra2112s`) | MIT | Turunan, tidak menambah klausa |
| Weights `Kronos-mini/small/base` | MIT | Lisensi weights = lisensi code, tidak terpisah |
| Tokenizer `Kronos-Tokenizer-base/2k` | MIT | Sama |
| Dependensi (torch, numpy, pandas, einops, huggingface_hub, matplotlib, tqdm, safetensors) | BSD/Apache/MIT/MPL | Semua permissive |
| `qlib` (untuk fine-tuning pipeline, opsional) | MIT | Microsoft |

### 3.1 Kewajiban jika implementasi
Sesuai MIT, **wajib** sertakan:
1. Copyright notice: `Copyright (c) 2025 ShiYu`
2. Teks lengkap MIT License

Cukup di file `THIRD_PARTY_LICENSES.md` di root repo UTOS. Tidak perlu tampil di UI.

### 3.2 Yang TIDAK ada di lisensi (sudah diverifikasi)
- ❌ Tidak ada klausa Non-Commercial (NC)
- ❌ Tidak ada No-Derivatives (ND)
- ❌ Tidak ada Share-Alike / copyleft (SA)
- ❌ Tidak ada royalty / revenue share
- ❌ Tidak ada geographic restriction
- ❌ Tidak ada watermarking wajib
- ❌ Tidak ada patent retaliation clause

### 3.3 Catatan non-lisensi
- **Trademark "Kronos"**: MIT tidak cover trademark. UTOS tidak boleh imply endorsement
  dari ShiYu. Boleh tulis "powered by Kronos (MIT)" tapi tidak boleh branding UTOS = Kronos.
- **Data training**: lisensi data training Kronos tidak didisclosed. Risiko kecil untuk
  inference-only. Jika fine-tune ulang, pastikan data sendiri legal.
- **Regulasi lokal (Indonesia)**: Bappebti (crypto) / OJK (securities) tetap berlaku
  terlepas dari lisensi Kronos. Lisensi MIT tidak lepas UTOS dari kewajiban regulasi.

---

## 4. KAPAN IMPLEMENTASI (Trigger Conditions)

Implementasi hanya jika **minimal salah satu** terpenuhi setelah UTOS v1.0 live ≥ 3 bulan:

| Trigger | Threshold | Diukur dari |
|---|---|---|
| Sharpe ratio di bawah target | < 1.5 pada window 90 hari | Backtest + live |
| Drawdown berlebih | > 25% pada window 90 hari | Live trading |
| Missed opportunity signifikan | Win rate turun > 15% vs backtest | Live vs backtest |
| Volatilitas regime shift | Market condition baru yang strategi UTOS tidak handle | Manual review |
| Permintaan fitur prediktif dari user | User request dengan business case jelas | Product feedback |

Jika **tidak ada** trigger yang terpenuhi → **JANGAN** implementasi. UTOS tetap clean.

---

## 5. INTEGRATION POINTS (jika dipicu)

Struktur folder UTOS saat ini sudah punya `backend/engine/ai/` (kosong, siap diisi).

### 5.1 Modul baru yang akan dibuat
```
backend/engine/ai/
├── __init__.py
├── kronos_predictor.py      # Wrapper KronosPredictor
├── kronos_config.py         # Model selection, device, context length
├── signal_adapter.py        # Konversi output Kronos → UTOS signal format
└── README.md                # Cara pakai & limitation
```

### 5.2 Mapping ke engine existing
| Engine UTOS | Cara pakai output Kronos |
|---|---|
| `engine/trading` | Forecast sebagai konfirmasi sinyal entry/exit (bukan sumber tunggal) |
| `engine/risk` | Distribusi prediksi → dynamic SL/TP & position sizing |
| `engine/grid` | Volatilitas terprediksi → adjust grid spacing |
| `engine/notification/channels.py` | Alert jika probabilitas reversal tinggi |
| `engine/portfolio` | Multi-path simulation untuk Monte Carlo allocation |

### 5.3 Posisi Kronos di arsitektur
**Kronos = optional signal source, bukan decision maker.**

```
[Market Data] → [UTOS existing engines] → [Decision]
                        ↑
              [Kronos (optional, pluggable)]
                        ↑
              [engine/ai/signal_adapter.py]
```

Kronos tidak boleh menggantikan logika UTOS yang sudah ada. Hanya menambah sinyal
probabilistik yang dikonsumsi engine lain sebagai **input tambahan**, bukan perintah.

---

## 6. RENCANA IMPLEMENTASI (jika dipicu)

### Phase 0: Validasi (1 minggu)
- [ ] Cek ulang lisensi Kronos (mungkin berubah sejak dokumen ini dibuat)
- [ ] Cek ulang model card HuggingFace untuk semua varian yang akan dipakai
- [ ] Benchmark inference latency di hardware target (CPU vs GPU)
- [ ] Buat `THIRD_PARTY_LICENSES.md` di root repo

### Phase 1: POC (2 minggu)
- [ ] Implementasi `engine/ai/kronos_predictor.py` (wrapper minimal)
- [ ] Test load model `Kronos-small` dari HuggingFace
- [ ] Test `predict()` pada 1 pair (mis. BTC/USDT) dengan data historis UTOS
- [ ] Bandingkan forecast vs actual → catat MAE/RMSE/Directional accuracy
- [ ] **Decision gate:** lanjut hanya jika POC menunjukkan value

### Phase 2: Adapter (1 minggu)
- [ ] Implementasi `engine/ai/signal_adapter.py`
- [ ] Definisikan format signal: `{direction, confidence, horizon, source: "kronos"}`
- [ ] Integrasikan ke 1 engine dulu (rekomendasi: `engine/risk` untuk dynamic SL/TP)
- [ ] Backtest dengan vs tanpa Kronos pada periode holdout

### Phase 3: Rollout bertahap (2-4 minggu)
- [ ] Paper trading dengan Kronos enabled (1 bulan)
- [ ] Bandingkan KPI vs UTOS tanpa Kronos
- [ ] Jika superior → live trading dengan size kecil
- [ ] Jika tidak superior → rollback, arsipkan dokumen ini sebagai "evaluated, not adopted"

### Phase 4: Fine-tuning (opsional, terpisah)
- [ ] Hanya jika zero-shot kurang dan ada data historis cukup (≥ 2 tahun per pair)
- [ ] Ikuti pipeline `finetune/` Kronos (tokenizer dulu, lalu predictor)
- [ ] Pertimbangkan biaya GPU vs peningkatan performa

---

## 7. RISIKO & MITIGASI

| Risiko | Impact | Mitigasi |
|---|---|---|
| GPU cost untuk inference | Tinggi untuk base/large | Mulai dari `Kronos-mini` (CPU-friendly), upgrade jika perlu |
| Context length 512 (small/base) | Lookback terbatas | Design lookback ≤ 512 candle; gunakan `Kronos-mini` (2048) jika perlu |
| Forecast bukan pure alpha | Sinyal mentah, perlu portfolio optimization | Kronos sebagai input, bukan output final |
| Model drift | Performa turun seiring waktu | Re-evaluate bulanan; pertimbangkan fine-tune ulang per kuartal |
| Lisensi Kronos berubah | Compliance risk | Cek ulang lisensi setiap kali upgrade version Kronos |
| HuggingFace unavailability | Tidak bisa load model | Cache model lokal setelah first download |
| Over-reliance pada ML | Strategy fragility | Kronos max 30% weight dalam signal blending, sisanya engine UTOS |
| Regulator view pada AI trading | Bisa berubah di Indonesia | Dokumentasi decision trail; audit log setiap prediksi Kronos |

---

## 8. HARDWARE REQUIREMENTS (estimasi)

| Model | Params | Inference (CPU) | Inference (GPU) | Rekomendasi |
|---|---|---|---|---|
| Kronos-mini | 4.1M | ~100-500ms / prediksi | ~10-50ms | POC & low-latency |
| Kronos-small | 24.7M | ~1-3s | ~50-200ms | Production awal |
| Kronos-base | 102.3M | ~5-15s | ~200-500ms | Hanya jika ada GPU dedicated |
| Kronos-large | 499M | Tidak realistis | ~1-3s | Hanya untuk research |

Catatan: angka estimasi, perlu diukur ulang di Phase 0.

---

## 9. DEPENDENCIES YANG AKAN DITAMBAH (jika implementasi)

```toml
# Tambahan ke pyproject.toml
[tool.poetry.dependencies]
torch = ">=2.0.0"
einops = "0.8.1"
huggingface_hub = "0.33.1"
safetensors = "0.6.2"
# numpy, pandas, tqdm sudah ada di UTOS
```

**Peringatan:** `torch` adalah dependensi berat (~2GB install). Pertimbangkan
install terpisah / optional extras agar UTOS tanpa Kronos tetap ringan:

```toml
[tool.poetry.extras]
kronos = ["torch", "einops", "huggingface_hub", "safetensors"]
```

Install hanya jika user enable Kronos: `poetry install -E kronos`

---

## 10. CHECKLIST SEBELUM IMPLEMENTASI

Sebelum mulai Phase 1, pastikan semua ini terjawab:

- [ ] UTOS v1.0 sudah live ≥ 3 bulan
- [ ] Minimal 1 trigger condition terpenuhi (lihat section 4)
- [ ] Lisensi Kronos di-verify ulang (bisa berubah sejak 2026-07-28)
- [ ] Hardware budget untuk GPU disetujui (jika pakai small/base)
- [ ] `THIRD_PARTY_LICENSES.md` dibuat sebelum code Kronos masuk repo
- [ ] Stakeholder setuju bahwa Kronos = optional, bisa di-rollback kapan saja
- [ ] Audit log mechanism siap untuk mencatat setiap prediksi Kronos (compliance)

---

## 11. REFERENSI

- Kronos GitHub: https://github.com/shiyu-coder/Kronos
- Kronos paper (arXiv): https://arxiv.org/abs/2508.02739
- Kronos live demo: https://shiyu-coder.github.io/Kronos-demo/
- HuggingFace org: https://huggingface.co/NeoQuasar
- AAAI 2026 acceptance (news): lihat README Kronos
- Lisensi audit internal: lihat section 3 dokumen ini

---

## 12. CHANGELOG

| Tanggal | Perubahan |
|---|---|
| 2026-07-28 | Dokumen dibuat sebagai future planning. Status: NOT IMPLEMENTED. |

---

**END OF DOCUMENT**

Dokumen ini bukan approval implementasi. Hanya blueprint untuk evaluasi masa depan.
UTOS dirancang untuk berdiri sendiri tanpa Kronos. Implementasi hanya jika terbukti
diperlukan dan melewati semua decision gate di section 4 & 10.
