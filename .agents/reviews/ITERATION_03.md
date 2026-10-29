# Paket review mentor — Simulasi Iterasi 3

## Penataan direktori data - 20 Oktober 2026

Permintaan pengguna: rapikan `data/` menjadi hanya `raw/` dan `processed/`, tanpa data tak terpakai. Tidak ada perubahan bisnis atau implementasi Iterasi 4 pada task ini.

- Tujuh input siap-baca dipindah ke `data/processed/`: CSV voyage I3, dua fixture tender I3, policy kapal, CSV I2, katalog variabel, dan fixture manual I2. Input I2 **masih dipakai** oleh tes regresi dan lineage, sehingga tidak dihapus.
- Workbook audit mentor berada di `data/raw/Voyage_Estimate_all_sheets_variable_value_units.xlsx`. Pemindahan sempat tertahan karena terbuka di Excel, lalu diselesaikan setelah pengguna mengonfirmasi sudah menyimpan/menutup workbook. Versi hasil simpan terakhir pengguna dipertahankan; SHA-256 sesaat sebelum dan setelah pemindahan identik. Lock Excel hilang sendiri setelah workbook ditutup.
- Direktori kosong `data/cases/`, `reference/`, `learning/`, dan `snapshots/` dihapus. Tidak ada dataset substantif dihapus; file sumber/hasil run di luar `data/` tidak disentuh. Git mengabaikan `~$*` agar lock Office tidak ikut terunggah.
- Path default pada CLI I2/I3, orchestrator I2/I3, generator peta variabel, tes, dan dokumentasi diperbarui. Isi CSV/JSON, metadata lineage historis dalam CSV, snapshot output lama, rumus, dan keputusan tidak ditulis ulang.
- Bukti: **38/38 tes lulus sebelum dan sesudah**; hash tujuh CSV/JSON yang dipindah identik dengan baseline. Workbook mengalami penyimpanan oleh pengguna selama task; versi terakhir dibandingkan segera sebelum/sesudah pemindahan, bukan dipaksa sama dengan versi awal. Hasil lengkap `evaluate()` I2, I3 GO, dan I3 NO GO identik sebelum/sesudah penataan.
- Smoke test CLI: `python scripts/run_iteration_03.py`, satu kasus memakai `--case data/processed/i3_go_urea.json`, serta `python scripts/run_iteration_02.py` berhasil. Output smoke test memakai direktori sementara yang dibersihkan otomatis, bukan menambah run permanen.
- `source_reference = data/dataset_ready.csv` dalam CSV I3 tetap label asal historis; file sumber kini berada di `data/processed/dataset_ready.csv`. Tidak ada importer otomatis yang membaca workbook audit.

Struktur akhir diverifikasi: hanya `data/raw/` dan `data/processed/`, tanpa file tersisa di root `data/`. Tidak ada staging, commit, atau push. Perbaikan kalkulasi hasil audit tetap pekerjaan berikutnya, bukan bagian cleanup ini.

**Status:** siap dikritik secara domain; **belum diterima mentor dan bukan MVP/quotation**. Tanggal review teknis: 8 Oktober 2026. Rujukan bisnis dan flow: `docs/it_3/ITERATION_03_TENDER_DSS_PLAN.md`.

## Apa yang berubah dari I2

I2 memeriksa calon penawaran sebelum buyer datang dan membandingkan FOB/CFR secara indikatif. I3 memodelkan **push demand → putaran tender PI → kandidat yang dipilih PI → DSS CFR pasca-tender**. I3 tidak memilih pemenang tender dan tidak menilai profit akuntansi PI. Aksi yang terlihat hanya **GO** (layak dibawa ke review manusia) atau **NO GO**. Kategori alasan yang benar-benar dikeluarkan kode ialah `TENDER_PRICE_FLOOR`, `DATA_OR_TENDER_SELECTION`, `CFR_EXECUTION_OR_ECONOMICS`, `CFR_REVIEW_CANDIDATE`, dan `DATA_ISSUE`; kategori bukan aksi tambahan.

## Data dan ownership

| Objek | Nilai/asal simulasi | Batas |
|---|---|---|
| Voyage urea granular bulk, Bontang→ECI, 45.000 MT | 29 field aktif di `data/processed/i3_urea_v1.csv`; mayoritas `inherited_experimental` dari I2 | Belum tervalidasi sebagai voyage urea nyata. |
| Indeks barang | Rata-rata midpoint Argus dan Fertecon FOB SEA granular dari **dua angka sintetis berlabel** per publisher | Angka PDF Argus belum terverifikasi; ini **bukan** kutipan Argus/Fertecon aktual. |
| OE/HPS, bid alpha, buyer, kandidat PI | Fixture JSON `simulation_only_synthetic` | Nilai dari PI/buyer nyata tidak tersedia. |
| Biaya OD | `total_voyage_cost / 45.000 MT`, status `derived_from_inherited_experimental_data_not_official_matrix` | Bukan OD matrix resmi. |
| Tarif jual freight PILOG | 20 USD/MT dari dataset I2, `inherited_experimental` | Penerapan pada kontrak PI–PILOG I3 belum dikonfirmasi. |
| Komisi | Tiga rate CSV di atas revenue freight bruto | Basis kontrak dan kemungkinan overlap dengan OD matrix belum dikonfirmasi. |

## Dua varian replay

| Kasus | Putaran bid | Indeks / OE-HPS sintetis | Hasil teknis |
|---|---|---|---|
| `i3_go_urea.json` | Alpha −10 → FOB 400 (gagal); alpha +10 → FOB 420 (gap +5, kandidat PI) | 410 / 415 USD/MT | **GO CFR untuk review**; Gate A/B lolos, kelas Supramax awal, kontribusi PILOG sekitar USD 108.446,10. |
| `i3_no_go_urea.json` | Alpha −20 → FOB 390; alpha −10 → FOB 400 (keduanya gagal) | 410 / 415 USD/MT | **NO GO CFR**; tidak ada kandidat eligible, Gate B tidak dipakai untuk menerima bid. |

Kedua kasus memakai ekonomi voyage yang sama: biaya voyage sekitar USD 735.303,90, proxy OD sekitar 16,3401 USD/MT, tarif jual PILOG 20 USD/MT, revenue freight USD 900.000, dan komisi USD 56.250. Angka pembulatan di tabel hanya untuk membaca; JSON menyimpan nilai `Decimal` penuh. **Jangan menyimpulkan laba PI** atau membagi selisih tarif jual–proxy OD tanpa kontrak PI–PILOG.

## Bukti teknis dan cara menjalankan

1. `python -m unittest discover -s tests -v` → **38/38 lulus** pada 8 Oktober 2026; termasuk tes I2 lama.
2. `python scripts/run_iteration_03.py` → satu run GO dan satu run NO GO di `outputs/runs/i3_*`; baca `decision_brief.md` terlebih dahulu, lalu `decision_brief.json` dan `input_snapshot/`.
3. Tes I3 mencakup batas `FOB = OE/HPS`, alpha positif yang gagal/negatif yang lolos, midpoint/rata-rata, tanggal/basis indeks salah, label sumber hilang, kontribusi PILOG negatif, lineage 29 field terhadap CSV I2, serta snapshot run.

Run terbaru untuk presentasi lokal: `outputs/runs/i3_20261008T032331853553Z_i3_go_urea/` dan `outputs/runs/i3_20261008T032331863983Z_i3_no_go_urea/`. Folder run baru diabaikan Git; jalankan ulang CLI jika folder tersebut tidak ada di mesin mentor.

## Peta arsitektur dan alur file kode — panduan audit Iterasi 3

Bagian ini mengikuti **pemanggilan kode yang saat ini berjalan**, bukan arsitektur MVP yang masih direncanakan. Tidak ada database, API Fleetra/SAP, pengambilan laporan harga otomatis, UI tender, atau write-back. Satu eksekusi membaca file lokal, menghitung secara deterministik dengan `Decimal`, mengeluarkan rekomendasi advisory, lalu menyimpan jejaknya. Peran manusianya tetap jelas: **PI menjalankan tender dan menentukan kandidat**, sedangkan **PILOG menilai kesiapan CFR/freight** dari kandidat tersebut; sistem tidak memutuskan award.

```text
JSON kasus + CSV voyage ──> scripts/run_iteration_03.py
                                   │
                                   ▼
                     orchestration/iteration_03.py::evaluate
                                   │
                                   ▼
                    validation/iteration_03.py + CaseSnapshot
                                   │
                                   ▼
                     calculations/tender.py (indeks, bid, voyage)
                           └─> physical.py ─> days/fuel/cost/pricing/capacity
                                   │
                                   ▼
                     CFR indikatif per bid; policy DWT ────────┐
                                   │                           │
                                   ▼                           │
                     decisions/iteration_03.py <───────────────┘
                     Gate A ─> Gate B ─> GO/NO GO
                                   │
                                   ▼
                     reporting/iteration_03.py + persist_run()
                                   │
                                   ▼
                     decision_brief.{md,json} + input_snapshot/*
```

### 1. File masuk dan batas kepercayaan

| File | Siapa/apa yang diwakili | Dibaca saat I3? | Yang perlu dicek auditor |
|---|---|---|---|
| `data/processed/i3_urea_v1.csv` | Satu kasus voyage urea 45.000 MT; 29 **variabel**, bukan 29 transaksi. Nilai fisik/biaya mayoritas diwarisi eksperimen I2. | Ya, melalui nama file `voyage_dataset` di JSON. | `key`, `value`, `unit`, `source_status`, `source_reference` per baris; khususnya rute, jarak, rate pelabuhan, konsumsi, DWT, biaya, tarif jual, komisi. |
| `data/processed/i3_go_urea.json` dan `i3_no_go_urea.json` | Dua **varian tender sintetis** yang memakai CSV voyage yang sama. Di sini ada observasi indeks, OE/HPS PI, bid/alpha buyer, kandidat pilihan PI, dan asumsi ekonomi. | Ya, satu atau keduanya sesuai argumen CLI. | Angka ini **bukan** hasil ekstraksi laporan pasar/tender nyata. Pastikan `pi_selected_bid` menunjuk bid yang memang ada atau `null` bila belum ada kandidat. |
| `data/processed/vessel_classes.json` | Policy screen awal DWT: Handysize 20–40 ribu MT dan Supramax 50–60 ribu MT. | Ya, saat Gate B. | Ini rentang kelas, **bukan** bukti DWCC, draft, laycan, terminal, atau ketersediaan kapal. |
| `data/processed/dataset_ready.csv` dan `data/processed/variable_catalog.csv` | Sumber historis I2/Aqaba-turunan. | **Tidak** dibaca pipeline I3 saat berjalan; tes lineage membandingkannya dengan CSV I3. | Jangan memperbaiki output I3 dengan mengedit file I2 tanpa memahami hubungan turunannya. |

### 2. Urutan eksekusi nyata, pemilik logika, dan titik audit

| Urutan | File/fungsi utama | Apa yang terjadi | Bukti/pertanyaan audit |
|---:|---|---|---|
| 0 | `scripts/run_iteration_03.py::main` | Tanpa `--case`, menjalankan JSON GO lalu NO GO. `--case` memilih satu; `--vessel-policy` dan `--output-root` dapat diganti. Untuk tiap kasus memanggil `evaluate()`, lalu `persist_run()`. | Pastikan argumen menunjuk fixture yang dimaksud. CLI **tidak** login ke sistem atau menerbitkan bid. |
| 1 | `validation/iteration_03.py::load_case` dan `validate_commercial_fixture`; `models/contracts.py::CaseSnapshot` | Membaca JSON/CSV dan membekukan nilainya ke `CaseSnapshot` beserta SHA-256. Memeriksa versi/mode, tepat 29 key, unit, nilai/range, label provenance, urea granular Bontang, Q=45.000 MT, dua publisher indeks yang basis/tanggalnya cocok, OE/HPS, bid unik, dan asumsi ekonomi eksplisit. | Input kosong/salah tidak diganti nol. Tanyakan apakah aturan tepat-29-field dan label `simulation_only_*` masih sesuai bila fixture diubah. |
| 2 | `calculations/tender.py::market_index`, `midpoint`, `average_two_publishers` | Menghitung midpoint masing-masing rentang Argus/Fertecon **sintetis**, lalu merata-ratakan keduanya menjadi indeks `I` USD/MT. | Lihat `tender.index` di JSON: dua midpoint, formula, dan label sintetik. Tidak ada parser PDF/laporan pasar dalam pipeline. |
| 3 | `calculations/tender.py::tender_bids`; `calculations/pricing.py::fob_usd_mt` | Untuk **setiap** putaran/bid, `FOB = I + alpha_buyer` tepat sekali; hitung `FOB − OE/HPS` dan tandai eligible bila `≥ 0`. Tanda alpha sendiri **bukan** aturan GO/NO GO. | Cocokkan setiap baris tabel tender di brief dengan alpha di fixture dan OE/HPS. DSS menghitung eligible, tetapi **tidak memilih buyer/pemenang**. |
| 4 | `calculations/tender.py::owned_voyage_economics` → `physical.py` → `voyage_days.py`, `fuel.py`, `costs.py`, `pricing.py`, `capacity.py` | Hitung hari laut/pelabuhan dari jarak, speed, Q/rate; konsumsi dan biaya fuel; biaya running kapal milik + bunker + port/other; proxy OD `total_voyage_cost / Q`; revenue freight PILOG `selling_rate × Q`; komisi atas revenue bruto; kontribusi `revenue − komisi − biaya voyage`; serta DWT headroom setelah allowance. Semua nominal/rate memakai `Decimal`. | Buka `economics` dan `physical_trace` di JSON. **Tarif jual PILOG ≠ biaya OD proxy**. `other_voyage_costs_total_usd` sudah agregat port/other; hire tidak dihitung untuk kapal milik. `CostLine.mechanisms` menolak duplikasi **label mekanisme** yang dideklarasikan, tetapi belum membuktikan bahwa agregat port/other tidak menyembunyikan komponen bunker/running. |
| 5 | `orchestration/iteration_03.py::evaluate` | Menambahkan `CFR indikatif = FOB bid + OD cost proxy` per bid dan `buyer_cfr_total = CFR × Q`; kemudian memanggil Gate. **Kalkulasi ekonomi pada langkah 4 terjadi sebelum Gate A**, sehingga pada contoh NO GO Gate A, ekonomi tetap muncul sebagai diagnostik, bukan persetujuan bid. | Jangan membaca CFR pada bid yang gagal OE/HPS sebagai harga penawaran yang boleh diteruskan. Tidak ada alpha kedua, adjustment generik, atau margin PI yang ditambahkan. |
| 6 | `decisions/iteration_03.py::evaluate_cfr_gates`; `capacity.py::gross_dwt_screen` | **Gate A:** harus ada bid dengan FOB ≥ OE/HPS, PI memilih satu bid, dan bid terpilih juga lolos floor. **Gate B** hanya setelah Gate A lolos: screen kelas DWT awal, headroom `DWT − bunker allowance − constants − Q ≥ 0`, dan kontribusi freight PILOG `≥ 0`. Semua lolos → GO untuk review; selain itu NO GO dengan kategori/reason code/next action. | Lihat `gates` dan `recommendation`. Jika Gate A gagal, Gate B `NOT_EVALUATED`, walau ekonomi diagnostik sudah dihitung. Tidak ada fallback otomatis ke FOB atau perbandingan laba FOB-versus-CFR di I3. |
| 7 | `reporting/iteration_03.py::render_i3_brief`; `orchestration/iteration_03.py::persist_run` | Renderer **memformat**, tidak menghitung keputusan. Orchestrator menulis brief MD/JSON, membuat `input_snapshot` untuk JSON kasus, CSV voyage, dan policy kapal, lalu mencatat SHA-256/versi formula/rule/status approval. | Baca MD untuk keputusan manusia; gunakan JSON + snapshot untuk memverifikasi angka dan sumber. `PENDING_HUMAN_REVIEW` tetap berlaku pada GO. |

**Perbedaan satuan yang tidak boleh tertukar:** `I`, alpha, FOB, OE/HPS, OD proxy, CFR, dan tarif jual freight semuanya **USD/MT**; total biaya, revenue, komisi, dan kontribusi PILOG **USD per voyage**; Q **MT**. `CFR = FOB + OD proxy` adalah **harga barang indikatif ke buyer** dalam simulasi ini, sedangkan `tarif jual freight PILOG × Q` adalah **revenue jasa PILOG yang diasumsikan** dari dataset; hubungan kontraktual kedua objek tersebut masih pertanyaan mentor.

### 3. Cara menelusuri satu keputusan tanpa membaca seluruh repo

1. Mulai dari `data/processed/i3_go_urea.json`: indeks dua publisher 400–420 memberi midpoint 410 dan indeks 410; OE/HPS 415; alpha bid `R2-B1` +10. Di `tender.bids` hasilnya FOB 420, gap +5, eligible. **PI memilih `R2-B1` di fixture**, bukan dipilih otomatis oleh DSS.
2. Cocokkan `data/processed/i3_urea_v1.csv`: Q 45.000 MT, tarif jual freight PILOG 20 USD/MT, kapal kasus 58.000 DWT, serta biaya/rate voyage yang diwarisi. Jejak fisik → biaya voyage → OD proxy dan kontribusi ada di `decision_brief.json`; ringkasannya di `decision_brief.md`.
3. Periksa `gates`: Gate A `PASS`; Gate B `PASS` karena Supramax lolos screen awal, headroom tidak negatif, dan kontribusi PILOG tidak negatif. Maka aksi **GO untuk review manusia**, bukan izin transaksi.
4. Bandingkan `i3_no_go_urea.json`: CSV voyage dan indeks/OE sama, tetapi alpha −20 dan −10 menghasilkan FOB 390 dan 400, keduanya `< 415`. Gate A `FAIL`, Gate B `NOT_EVALUATED`, aksi **NO GO / TENDER_PRICE_FLOOR**. Contoh ini menunjukkan keputusan berbeda berasal dari **fixture tender**, bukan dua dataset voyage yang berbeda.

Untuk hasil yang baru dijalankan, buka folder `outputs/runs/<run_id>/`: `decision_brief.md` untuk narasi; `decision_brief.json` untuk `tender`, `economics`, `physical_trace`, `gates`, `recommendation`, `input_lineage`, `limitations`, versi dan hash; `input_snapshot/case_fixture.json`, `voyage_dataset.csv`, `vessel_policy.json` untuk input persis saat run. Jika data di disk berubah setelah run, audit **snapshot run**, bukan hanya file `data/` terbaru. `persist_run()` membandingkan hash snapshot dengan hash yang dihitung saat `evaluate()` bila hash tersebut tersedia.

### 4. File yang *bukan* jalur utama I3 dan bukti tes

`scripts/run_iteration_02.py`, `orchestration/pipeline.py`, `validation/ingest.py`, `scenarios/`, `decisions/gates.py`, `reporting/brief.py`, dan `calculations/economics.py` adalah jalur pra-penawaran **I2 historis** atau utilitasnya; jangan menyimpulkan Gate I3 dari file tersebut. Sebaliknya, `calculations/physical.py`, `voyage_days.py`, `fuel.py`, `costs.py`, `pricing.py`, dan `capacity.py` memang **dipakai ulang oleh I3**. Karena itu `physical_trace.formula_version` masih `I2.R2.1`, sedangkan versi laporan/aturan I3 adalah `I3.1`; ini menunjukkan reuse modul fisik, **bukan** bahwa keputusan I3 memakai Gate I2. Versi per submodul perlu diperjelas bila audit formal menuntut satu jejak formula yang konsisten.

| Yang hendak diverifikasi | File tes paling langsung | Perintah dari root repo |
|---|---|---|
| Midpoint, rata-rata publisher, `FOB = I + alpha`, batas `FOB = OE/HPS` | `tests/unit/test_iteration_03_tender.py` | `python -m unittest tests.unit.test_iteration_03_tender -v` |
| GO/NO GO end-to-end, data issue, kontribusi negatif, DWT, lineage, snapshot | `tests/integration/test_iteration_03.py` | `python -m unittest tests.integration.test_iteration_03 -v` |
| Rumus hari, fuel, biaya, revenue, anti-double-count, screen DWT | `tests/unit/test_calculations.py`, `tests/unit/test_economics_policy.py` | `python -m unittest tests.unit.test_calculations tests.unit.test_economics_policy -v` |
| I2 tidak rusak setelah I3 | Seluruh `tests/`, terutama `tests/integration/test_iteration_02.py` | `python -m unittest discover -s tests -p "test_*.py" -v` |

**Hasil verifikasi dokumentasi ini:** seluruh **38/38 tes lulus** pada 8 Oktober 2026. Untuk audit berikutnya, uji juga input JSON dengan bentuk tipe yang rusak (bukan hanya nilai kosong): blok `evaluate()` saat ini menangkap `ValueError`, `KeyError`, `OSError`, dan `JSONDecodeError`, tetapi belum membuktikan semua bentuk data rusak selalu menjadi `NO_GO / DATA_ISSUE` alih-alih error Python. Ini **catatan cakupan tes**, bukan klaim bahwa fixture presentasi yang ada gagal. Demikian pula persetujuan rumus tender, OD matrix, kontrak PI–PILOG, dan kemampuan kapal aktual tetap berada pada mentor/pemilik proses, bukan disahkan oleh 38 tes.

## Pertanyaan yang harus diputus mentor

1. Apakah formula tender aktual benar `FOB_bid = indeks + alpha_buyer`, dan bagaimana buyer memasukkan bid di UI/auction?
2. Apakah **rata-rata Argus+Fertecon regional** disetujui PI sebagai basis tender, seri spesifiknya apa, dan bagaimana menyelaraskan tanggal/lot 45k?
3. Apakah biaya OD matrix resmi sama dengan total running+bunker+port/other yang dihitung di sini? Apakah komisi termasuk atau di luar matriks?
4. Apakah 20 USD/MT pada CSV I2 benar tarif jual PILOG ke PI untuk kontrak I3? Jika berbeda, berapa objek dan sumber yang benar?
5. Apakah DWT + allowances cukup untuk screen awal sebelum pimpinan, dan siapa yang mengonfirmasi DWCC, draft, terminal, laycan serta availability?
6. Apakah bahasa **NO GO / DATA_ISSUE** dapat diterima stakeholder sebagai “jangan lanjut karena bukti belum cukup”, tanpa disalahartikan sebagai penolakan komersial buyer?

**Keputusan review mentor:** _belum diisi_. Setelah feedback diterima, revisi rule/data/brief yang relevan, replay kedua fixture, dan putuskan apakah perlu Iterasi 4. Jangan pindah ke MVP hanya karena output GO sudah tampil.

**Belum diimplementasikan dalam I3:** input bid berupa harga CFR all-in yang harus diurai balik menjadi FOB/alpha; cabang ini menunggu format tender aktual. Demikian pula integrasi laporan harga asli, OD matrix resmi, sumber OE/HPS PI, dan tindakan operasional tetap di luar simulasi ini.
