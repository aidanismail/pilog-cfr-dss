# Current Agentic Control State

## Penataan data 20 Oktober 2026

Penataan selesai: root `data/` hanya berisi `raw/` dan `processed/`. Workbook audit yang sudah disimpan/ditutup pengguna berada di `data/raw/`; tujuh input runtime berada di `data/processed/`. Default CLI I2/I3, policy orchestrator, tes, dan referensi dokumentasi sudah disesuaikan. Seluruh 38 tes lulus sebelum/sesudah penataan; hasil `evaluate()` I2 serta kedua kasus I3 identik dengan baseline. Isi tujuh CSV/JSON tidak berubah; workbook hasil simpan terakhir pengguna dipindah tanpa mengubah byte-nya. Empat folder kosong lama dihapus; lock Excel hilang setelah pengguna menutup workbook, bukan dihapus paksa. Lihat `reviews/ITERATION_03.md`. Tidak ada perubahan rumus, gate, komisi, ballast, atau penerimaan MVP dalam task ini.

## Status as of 2026-10-08

**Simulasi Iterasi 3 sekarang aktif dan siap untuk review mentor, belum disetujui.** Dua fixture sintetis di `data/processed/` menghasilkan GO dan NO GO pasca-tender dengan aksi publik hanya dua nilai tersebut; semua data non-Aqaba berlabel `simulation_only`. Mesin I3 terpisah dari I2, memakai `Decimal`, menampilkan dua Gate beserta source lineage, dan menyimpan decision brief serta input snapshot. **38/38 tes lulus**. Baca `docs/it_3/ITERATION_03_TENDER_DSS_PLAN.md`, `tasks/ITERATION_03.md`, dan `reviews/ITERATION_03.md` untuk pekerjaan aktif. Perintah: `python scripts/run_iteration_03.py`. GO adalah kandidat review manusia, bukan approval, award tender, quotation, atau MVP.

### Konteks historis Iterasi 2

The **revised Iteration 2 simulation is implemented and technically verified**: its 26 historical tests passed before I3 and still pass in the expanded 38-test suite. The pre-offer case reaches both Gates in `outputs/runs/i2_20260923T091307166739Z_f5c4e74a/`. It uses seller-capped DWCC 45,000 MT and versioned DWT class ranges. Its historical task board is `tasks/ITERATION_02_PROPOSED.md`; its plan is `PLANS_ITERATION_02.md`. **Mentor acceptance of I2 was not recorded**; I3 implementation does not retroactively imply that approval. Confirm company permission and repo visibility before publishing Aqaba-derived data or snapshots.

## Current authoritative reading order

1. `AGENTS.md`
2. `PRODUCTS.MD`
3. `PRODUCTS_TIMELINE_PROPOSAL.md` - approved timeline clarification; use it to interpret product maturity.
4. `ITERATION_STATE.json`
5. `../docs/it_3/ITERATION_03_TENDER_DSS_PLAN.md` - bisnis, data, dan Gate I3.
6. `tasks/ITERATION_03.md` - task board aktif.
7. `reviews/ITERATION_03.md` - hasil teknis dan pertanyaan mentor aktif.
8. `DECISIONS.md` - keputusan D-024 sampai D-029 untuk I3.
9. `reviews/ITERATION_02.md` dan `contracts/ITERATION_02_ECONOMICS.md` - basis historis voyage/freight I2.
10. `ARCHITECTURE.md` - arsitektur umum; cek kode aktual untuk modul I3.

`tasks/ITERATION_02.md`, `tasks/ITERATION_02_PROPOSED.md`, `PLANS_ITERATION_02.md`, dan bagian lama `PRODUCTS.MD` adalah konteks historis. Jangan gunakan alur pra-penawaran I2 untuk mengganti flow pasca-tender I3. Jangan perlakukan fixture sintetis sebagai ekonomi yang telah disetujui mentor.

## Work boundary

```text
Simulation -> Iteration 1..N -> Final Simulation Validation -> MVP consideration
```

MVP work is prohibited until the mentor accepts Final Simulation Validation.
