# Modular Architecture and Directory Workflow

## Target I5 — rencana, bukan arsitektur yang sudah diimplementasikan

Plan docs/it_5/ITERATION_05_PLAN.md memisahkan React SPA → FastAPI/auth/revision → application service/repository → engine I4. PostgreSQL menampung shared canonical state, private volume menyimpan artefak; raw Decimal string dan formatter existing tetap. InteractiveCase saat ini masih object mutable plus IO file, sehingga adapter/persistence perlu diuji, bukan langsung diasumsikan multi-user-safe. Tidak mengganti calculations/decisions/reporting dengan FastAPI atau formula frontend. I4 commit 57257c0 adalah parity/rollback baseline; API/web/DB/infra di direktori plan belum dibuat.

## Formatter bersama — D-068/D-069

reporting/formatting.py memiliki number_text dan percent_text untuk presentasi Indonesia dua desimal. UI fmt dan report amount mendelegasikan ke formatter yang sama; minimum=True menggunakan CEILING khusus lower bound preskriptif. Tidak mengubah angka di calculations, decisions, source rows, fixed record atau JSON. String tampilan tidak dipakai sebagai input bisnis. I4-BRIEF.8; audit detail/raw tetap presisi penuh. Empat ekspektasi tampilan legacy diperbarui dan ditest ulang, bukan pelonggaran gate.

## Tampilan sumber dan hasil — D-066/D-067

`ui/presentation.py::active_inputs` membaca current_values dari service dan menyalin provenance override ke record tampilan tanpa memutasi base rows. `source_label` memetakan status ke label UI. Pemilih profil dipanggil oleh review_data pada Step 1 dan memakai apply_profile existing; Step 2 tidak memiliki pilihan kasus kedua. Harga bunker aktif dan benchmark pembanding dipisah; source table memakai effective records.

`supporting_analysis` di views membaca report metrics/scenarios/case/tender serta helper cost_change_lines/pricing_bridge_lines/price_reference existing. Tidak menghitung uang/ranking/gate atau mengubah renderer MD/JSON. UI ringkas; unduhan tetap lima bagian lengkap. Tanggal/fixed quote dan hiding editor tetap. Lihat review J untuk bukti 21+18 tes, browser dan 347 hash identik.

## Commercial review D-064/D-065 — I4-BRIEF.7

`InteractiveCase.reforecast_costs` membuat salinan biaya terbaru tanpa mengganti freight/bid/base rows. `validation/cost_forecast.py` memvalidasi COST-FORECAST.1: whitelist biaya/operasi, unit/finite/range, waktu/alasan, quote ID dan SHA-256 base rows+quote. `effective_case` menjadi input voyage/stress terbaru; base rows asli tetap menghasilkan pembanding ekonomi saat penetapan harga. Tidak ada mutasi dataset, target, cargo, profil, komisi atau harga barang lewat reforecast.

`calculations/commercial_review.py` memiliki matematika kontribusi harian, perubahan/driver biaya, kerugian, pengurangan biaya dan freight impas dengan pembulatan ke atas. `orchestration/iteration_04.py` menambahkan commercial_review/pricing_bridge pada persiapan dan evaluasi versi I4-COMMERCIAL.1. Renderer I4-BRIEF.7 hanya membaca hasil. Aturan keputusan/formula dasar I4.1 tetap.

`fix_freight(rate, reason)` mendukung penawaran manual eksplisit, metadata dan persiapan ulang; `revise()` membawa biaya terbaru sebagai base kasus baru sambil melepas quote/bid lama. `compare_profiles(common_freight)` menjalankan engine empat kali pada freight sama tanpa memutasi kasus, serta menyimpan hasil tarif target masing-masing profil. UI tidak menghitung uang. Skenario gabungan memakai shock existing; bukan gate baru.

`market_case.demo_case` dan CLI aktif membuat GO/floor/economics dari satu anchor quote. Port/other 450.000 USD pada profil default adalah fixture sintetis. Untuk profil lain, helper demo murni menentukan biaya yang cukup menghasilkan rugi; angka tersebut tidak masuk formula ekonomi atau kebijakan gate kasus pengguna. Snapshot mencapture base CSV, forecast context, pasar dan jarak agar replay offline identik. Bukti dan peta detail ada di review I4.

## Revisi komisi dan OD-DISTANCE.1 — D-062/D-063

`application/market_case.py::apply_case_basis` membuat basis I4-INPUT.2 (komisi nol, OD distance-only). `sources/od_distance.py` membaca sheet Input - OD Intl read-only dan resolve produk/asaltujuan dari raw cells; `validation/case_basis.py` mengikat unit/value/cell/hash dan policy komisi. Orchestration mencapture ekstrak `od_distance.json` dan menyimpan `route_distance` tanpa `od_comparison` untuk kasus baru. Report I4-BRIEF.6; legacy .4/.5 tetap replay. `InteractiveCase.tender_preview` berbagi bid_prices/evaluate_tender final untuk tabel per putaran; UI tidak menghitung harga. Sidebar memakai logo asli public. Perubahan tidak menyentuh fungsi hitungan/gate inti, source data/template atau histori; RBAC belum dibangun.

## Revisi aktif sumber dan waktu, 27 Oktober

`sources/fearnpulse.py` mengambil empat payload publik relevan dan menormalisasi TC/bunker dengan date/unit/hash. `sources/voyage_profiles.py` membaca empat sheet workbook read-only, menghitung port diesel melalui fungsi fuel existing dan membuat katalog profil. `application/market_case.py` mengikat snapshot/profil ke salinan kasus, mengisi contoh bid bertimestamp dan membandingkan profil. `validation/market_sources.py` memeriksa binding/offline replay, sementara `models/tender_clock.py` mengatur jendela 180 detik. Keputusan clock memakai last valid received timestamp; path legacy tetap round/sequence.

`orchestration/price_records.py` mencatat metadata harga dan actor lokal tanpa auth rekaan; `reporting/formatting.py` hanya memformat recorded time, tidak membaca clock. Orchestration menangkap payload mentah bersama input dan mengekspor PRICE.1; report baru I4-BRIEF.5, engine matematika I4.1 unchanged. UI dua kartu memakai angka yang terikat, bukan feed dekoratif. Source refresh tidak mereprice fixed tender. Entry aktif `scripts/run_market_simulation.py`, refresh `scripts/refresh_market_inputs.py`; runner I4 awal adalah baseline replay. Tidak ada DB/API server/RBAC produksi baru.

## UI lokal I4 — kontrak 23 Oktober 2026

`apps/streamlit_app.py` → `ui/views.py` → `application/interactive_case.py` → validator/orchestration I4 → calculations/decisions/reporting existing. Hanya calculations memiliki matematika uang/Decimal. `voyage_basis()` dipakai preparation dan evaluator final; `prepare_voyage()` tidak membutuhkan bid/market barang dan tidak menghasilkan GO/NO GO. `load_case(pre_tender=True)` adalah jalur persiapan eksplisit; default final tetap memvalidasi seluruh tender/scenario.

Service menyimpan salinan draft, menetapkan tarif dari preparation melalui tindakan eksplisit, memisahkan revisi basis baru dari bid lama, dan menginvalidasi hasil setelah edit. Satu evaluasi dipersist sekali; redraw/download tidak membuat run baru. UI memakai brief existing untuk lima view, bukan aturan/renderer finansial baru. Template/sumber di data/raw dan processed tetap; draft di outputs/ui_cases, run immutable di outputs/runs. Requirements UI/test terpisah dari CLI. 151 tes + smoke browser tercatat pada review; bukan acceptance mentor/MVP. Peta direktori/detail kontrak ada di plan §7.11.

## Kontrak aktif I4 — 22 Oktober 2026

I4 sudah diimplementasikan sebagai modul terpisah; 67 tes lulus, review mentor belum selesai. Peta kode dan input-output yang benar-benar berjalan ada pada [review I4](reviews/ITERATION_04.md). Bagian arsitektur I2 di bawah adalah histori dan prinsip pemisahan lapisan, bukan aturan HOLD/FOB aktif I4.

| Lapisan | File I4 | Kontrak utama |
|---|---|---|
| Persiapan opsional | `scripts/prepare_iteration_04.py` | Workbook/PDF read-only → CSV/JSON baru berlabel; menolak overwrite |
| Entry | `scripts/run_iteration_04.py` | Dua kasus default atau `--case` eksplisit |
| Models/validation | `models/iteration_04.py`, `validation/iteration_04.py` | Case04/I4.1, unit/basis/critical arithmetic, metadata tanggal bukan hard gate |
| Calculation | `calculations/voyage_04.py`, `pricing_04.py`, `tender_04.py` | Satu arah/biaya/pricing/semua bid; Python Decimal, fungsi murni |
| Decisions | `decisions/iteration_04.py` | Latest-active/floor/ranking; gross-DWT dan baseline >=0; GO/NO GO, bukan award |
| Orchestration | `orchestration/iteration_04.py` | Urutkan modul, stress dengan freight tetap, captured bytes/hash dan persistensi |
| Reporting | `reporting/iteration_04.py` | Brief komersial, audit, JSON; format saja, tidak menghitung ekonomi |

Input runtime: `data/processed/i4_voyage.csv` dan `i4_context.json`/`i4_no_go.json`. Snapshot hasil dapat direplay tanpa workbook live. Target TCE proxy berlabel, bukan hire expense; komisi/cost boundary eksplisit. OD satu pengiriman satu arah dengan internal return cost, bukan gate. Gate A gagal membuat Gate B belum dievaluasi; kesalahan input menjadi NO_GO/DATA_ISSUE. Tidak ada freshness, laycan atau minimum margin hard gate baru.

## Arsitektur historis I2 dan prinsip umum

## Purpose

Iteration 1 proved the pipeline using standalone scripts. Iteration 2 reorganises logic into small, deterministic modules. The nine standalone scripts were removed after replacement tests passed, per the user's cleanup approval; their tracked versions remain recoverable in Git history. Generated Iteration 1 root outputs and older Iteration 2 run folders were later removed during the approved repository cleanup. One complete revised Iteration 2 run remains as example evidence.

The architecture has one direction of dependency:

```text
data and policy inputs
-> canonical models
-> validation and constraints
-> deterministic calculations
-> scenarios
-> gates and recommendation
-> reporting / review artefacts
-> human decision
```

No reporting, UI, prompt, Excel, or LLM component may contain authoritative business formulas.

## Target directory structure

```text
pilog-cfr-dss/
|
|-- .agents/                         # Agent instructions, state, plans, reviews
|   |-- 00_READ_CURRENT.md
|   |-- AGENTS.md
|   |-- PRODUCTS.MD
|   |-- ARCHITECTURE.md
|   |-- ITERATION_STATE.json
|   |-- DECISIONS.md
|   |-- reviews/
|   |-- tasks/
|   `-- templates/
|
|-- data/
|   |-- raw/                         # Workbook sumber/audit mentor; pertahankan isinya
|   `-- processed/                   # Input siap-baca I3, policy/katalog, dan fixture regresi I2
|
|-- src/
|   `-- pilog_cfr_dss/
|       |-- __init__.py
|       |-- models/                  # Typed input/output contracts and units
|       |-- validation/              # Data quality, route, and evidence checks
|       |-- calculations/            # Pure Decimal calculation functions only
|       |-- scenarios/               # Scenario construction from one Case snapshot
|       |-- decisions/               # Gate 1, Gate 2, reason codes, recommendation
|       |-- reporting/               # Decision brief and learning/report generators
|       `-- orchestration/           # Explicit pipeline sequencing; no business math
|
|-- scripts/
|   |-- build_variable_workbook.py   # Learning artefact generator, not pricing engine
|   `-- run_iteration_02.py          # Thin command-line entry point
|
|-- tests/
|   |-- unit/                        # One module/function behaviour per test
|   |-- integration/                 # End-to-end simulation pipeline tests
|   `-- fixtures/                    # Small safe/dummy input cases for tests
|
|-- outputs/
|   |-- runs/<run_id>/               # Generated pipeline evidence; one curated example tracked
|   |-- learning/                    # Generated Excel for intern/mentor learning
|   `-- reviews/                     # Generated review evidence, not agent policy
|
|-- docs/
|   `-- it_1/                        # Historical source feedback from Iteration 1
|
`-- app/                             # Empty until Final Simulation Validation permits MVP UI work
```

## Responsibility of each code layer

| Layer | May do | Must not do |
|---|---|---|
| `models` | Define dataclasses/types, units, validation result structures | Calculate business values or read files |
| `validation` | Validate presence, type, unit, source, freshness, route evidence | Choose commercial action |
| `calculations` | Calculate capacity, days, fuel, cost, economics with `Decimal` | Read CLI args, write files, call LLM, make approval decisions |
| `scenarios` | Build alternatives from the same validated case snapshot | Invent inputs or compare incompatible snapshots |
| `decisions` | Apply approved rules, emit status/reason codes/recommendation | Recalculate hidden economics or execute action |
| `reporting` | Render deterministic outputs as Markdown/JSON/learning Excel | Alter calculation results or policy |
| `orchestration` | Sequence modules and persist immutable run artefacts | Hide errors or contain business formulas |
| `scripts` | Parse explicit command inputs and invoke orchestration | Hold reusable business logic |

## Calculation-module workflow

```text
CaseSnapshot
-> validate_case()
-> validate_route_inputs()
-> calculate_capacity()              # only when supported by data contract
-> calculate_voyage_days()
-> calculate_fuel_consumption()
-> calculate_fuel_cost()
-> calculate_commission()
-> calculate_voyage_cost()
-> calculate_freight_economics()
-> build_scenarios()
-> evaluate_gate_1()
-> evaluate_gate_2()
-> recommend_action()
-> build_decision_brief()
```

Any missing required dependency halts its dependent calculation with a structured status:

```text
PASS | WARN | HOLD_DATA_ISSUE | HOLD_DEFINITION_REQUIRED | BLOCK
```

## Route-agnostic contract

The selected dataset/manual input owns the route. Code must not branch on port/country names.

```text
loading_port + discharging_port
-> selected route inputs
-> validated route-specific evidence
-> calculation or HOLD
```

For example, distance, port time, tariff, port restriction, and terminal condition are data, not code constants. If unavailable, the result is an explicit HOLD; the system must not borrow a value from another route.

## Migration from Iteration 1

The standalone scripts have been replaced by tested modules and removed from the worktree with user authorization. Their historical source is recoverable from Git; prior output artefacts were not deleted. Do not recreate a `legacy/` script tree. Preserve useful input/output semantics where possible, but do not preserve known incorrect logic such as quality `BLOCK` coexisting with Gate 1 eligibility. See `.agents/reviews/ITERATION_02.md` for task, formula, test, and review evidence.

## Output workflow

```text
one pipeline run
-> unique run_id
-> input snapshot copy/hash
-> validation report
-> calculation trace
-> scenario comparison
-> gate evidence
-> recommendation / safe hold
-> decision brief
-> review record
```

Generated outputs are evidence. They must not become inputs for a new run unless explicitly versioned and approved as a snapshot/reference source.

## First directory changes allowed in Iteration 2

The following are safe now because they contain no unapproved business logic:

```text
src/pilog_cfr_dss/
src/pilog_cfr_dss/models/
src/pilog_cfr_dss/validation/
src/pilog_cfr_dss/calculations/
src/pilog_cfr_dss/scenarios/
src/pilog_cfr_dss/decisions/
src/pilog_cfr_dss/reporting/
src/pilog_cfr_dss/orchestration/
tests/unit/
tests/integration/
tests/fixtures/
data/raw/
data/processed/
outputs/runs/
outputs/learning/
outputs/reviews/
```

Do not start adding calculation logic until I2-T01 variable mapping is reviewed.

## Penataan data 20 Oktober 2026

Struktur data aktif hanya `raw/` dan `processed/`; folder kosong `cases/`, `reference/`, `learning/`, dan `snapshots/` di bawah `data/` dihapus. CLI, default policy pada orchestrator, tes, dan dokumentasi memakai path `data/processed/`. CSV, JSON, dan workbook tidak ditulis ulang. Input historis I2 tetap diperlukan oleh regresi dan tes lineage I3; generated learning workbook dan snapshot eksekusi tetap berada di `outputs/`, bukan `data/`.

`processed` tidak berarti sumber sudah disahkan untuk transaksi. Teks lineage historis di CSV I3 dipertahankan; `source_reference = data/dataset_ready.csv` menunjuk sumber yang kini dipindah ke `data/processed/dataset_ready.csv`. Rumus/gate dan perbaikan bisnis hasil audit belum diimplementasikan oleh penataan direktori ini.
