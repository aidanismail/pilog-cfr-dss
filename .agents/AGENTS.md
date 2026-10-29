# Panduan Agentic Coding - PILOG CFR DSS

## Aktif D-076 — randomisasi input contoh, bukan keputusan

Pengguna meminta pengacakan editor bid/risiko. Implementasi application/tender_examples.py memakai seed 64-bit, market_summary/minimum alpha existing, tiga buyer/putaran, nonnegative FOB dan clock kasus 180 detik. Tidak memilih desired outcome, mengacak quote/OE/indeks/biaya baseline atau menaruh RNG di calculations/decisions.

UI menahan contoh pada session draft sampai Terapkan. Acak ulang tersedia sesudah ada bid, editor keys mengikuti seed. record_applied_example menyimpan seed/version/basis/hash, actual clock/cutoff/PI selection dan edited_before_apply; apply_tender/apply_scenarios/revise menghapus metadata stale. Snapshot input terpakai adalah kebenaran; seed tidak dianggap mereproduksi edit manusia. Sidebar dan CLI scripted fixtures tetap. Full 262 tes lulus; browser/evidence final di state/task. Empat workbook/profil/fixed quote/gate tetap, deployment belum diizinkan.

## Aktif D-075 — diversifikasi profil selesai teknis

Pengguna memberi EXECUTE dua Handysize dan dua Supramax. Workbook aktif/mirror sekarang HS36/HS38/SUP54/SUP58; spesifikasi fisik sintetis berlabel, tidak diklaim dari Fearnpulse. Stable technical IDs lama tetap lewat PROFILE_IDS alias, case/quote/snapshot historis tidak berubah. Keluarga pasar kelas ditentukan DWT: dua Handysize → benchmark Handysize, dua Supramax → benchmark Supramax. Benchmark bukan harga penawaran kapal aktual; tidak mengarang quote berbeda dalam kelas.

Format workbook/cargo/rute/OD/gate tidak diubah pada revisi ini. VE-PROFILES.3/source_status simulation_only_workbook_vessel_profile membedakan input demo dari observasi pasar. Full 254 tes lulus; task/state mencatat browser final. D-074 di bawah adalah histori pemisahan voyage/kapal. Deployment, persistence dan porting tetap belum dieksekusi.

## Aktif D-074 — implementasi kasus workbook, bukan deploy

Pengguna mengizinkan edit isi/nama keempat sheet dan integrasi Step 1; jangan ubah style, warna, merge, ukuran kolom/baris atau posisi tabel. Pernyataan D-073 belum izin kode digantikan khusus V1..V4 ini. Tidak ada izin deploy/porting. Baca docs/it_5/ITERATION_05_PLAN.md §6.1 dan task I5.

Kasus urea Bontang→Mundra/Davao/Bangkok/Hai Phong, muatan 30k/28k/32k/29k MT; handling/waiting/port biaya contoh berlabel, OD asli tidak diubah. Workbook aktif data/raw/Voyage Estimate.xlsx, mirror Experiments identik; arsip I4 docs/it_4/Voyage Estimate I4.xlsx menjaga replay/preparer lama. Source parsing terpisah voyage/kapal. Stable vessel codes B3 menjaga ID CLI lama saat tab diubah; UI gunakan kelas/DWT/speed, jangan memakai nama rute sebagai nama kapal.

Dua pemilih independen; market target mengikuti kelas, bunker tetap Fearnpulse. JSON processed bukan satu-satunya sumber active app; cache berbasis hash dan penggantian workbook ke kasus lama memerlukan aksi/revisi eksplisit. Jangan mutasi fixed quote/bid/history. Contoh sidebar memuat ulang template voyage/kapal terpilih agar input manual invalid tidak merusak contoh. §6.2/task/state memuat evidence.

Streamlit dipertahankan; FastAPI/React/RBAC enterprise ditunda. Simpan/reopen lintas sesi belum diputuskan. Jangan mengklaim cloud durable atau multi-user-safe. Sebut batas asumsi, gunakan Python Decimal, dan berikan kritik beralasan. Sumber I4 57257c0/239 tes release tetap baseline, bukan evidence revisi baru.

## Terbaru D-070 — I4 accepted, push diotorisasi

Pengguna mengonfirmasi I4 accepted dan mengizinkan commit/push origin/dev. Larangan push historis sudah digantikan untuk checkpoint ini; repo PRIVATE diverifikasi. 239/239 regresi lengkap lulus 28 Oktober (252,554 detik), menggantikan status targeted reruns lama. Sesudah checkpoint, rencanakan porting/deployment I5 dengan engine/rule tetap. I5 baru plan, belum izin implementasi/deployment publik. Pertanyaan akses/hosting/pengguna diminta di akhir. Jangan git init vault, force push/main, membawa secrets/cache atau menganggap acceptance I4 izin transaksi/MVP penuh.

## Terbaru D-068/D-069 — aturan format angka

Gunakan reporting/formatting.py::number_text untuk output UI/brief I4: format Indonesia dua desimal HALF_UP. Minimum preskriptif impas/recovery memakai minimum=True (CEILING) agar tidak kurang dari kebutuhan. ID/putaran/tanggal/versi tetap; input/raw/JSON/audit detail mempertahankan presisi. Jangan memakai string tampilan untuk matematika atau mereprice fixed quote. I4-BRIEF.8 menandai format baru, formula/gate tetap I4.1. K0..K3 selesai; bukti regresi dengan targeted reruns/browser dan raw-parity tiga run ada di review. Jangan mengklaim satu run suite 239/239: empat assertion format lama diperbarui dan diulang lulus setelah run lengkap 235 pass.

## Terbaru D-066/D-067 — kejelasan UI selesai

Plan §7.15/task J/review mengendalikan tampilan terbaru: pemilih tunggal di Step 1, Step 2 hanya hasil dari shared case, sumber harga terpisah, nilai efektif manual/reforecast dan copy ringkas. `ui/presentation.py` hanya memproyeksikan effective values/provenance; tidak memiliki rumus. Empat analisis memakai report dan helper reporting existing, tidak mengklaim probabilitas/hedging/operasi lengkap. Jangan mengembalikan footer yang diminta pengguna dihapus, kolom Pemakaian ambigu atau pemilih kedua. Tanggal/source/manual/proxy/unit/error penting dipertahankan. 21 AppTest + 18 integrasi + browser lulus; 347 protected hash identik. Rumus/gate/quote/report backend tetap, run D-065 tetap acuan. Server uji berhenti dan sesi pengguna terpisah tidak disentuh.

## Terbaru D-064/D-065 — penguatan commercial review

Acuan plan §7.14, task H dan review I4. Reforecast biaya harus membuat salinan dengan quote/price_id/fixed_at/bid/base rows tetap, record COST-FORECAST.1 terikat hash dan alasan/waktu. Jangan otomatis mengganti freight agar GO. Penawaran manual berbeda dari indikasi memerlukan alasan; revisi penawaran baru melepas bid lama dan menerapkan biaya terbaru sebagai base baru. Hanya calculations memiliki matematika kontribusi/driver/impas/per hari.

Kasus baru memakai I4-COMMERCIAL.1 dan report I4-BRIEF.7. Tiga contoh GO/floor NO GO/economic NO GO disediakan. GO berarti ekonomi baseline lolos, bukan bukti penerimaan pasar/award/kesiapan berlayar. Perbandingan empat profil pada freight sama tidak memilih kapal otomatis. Stress gabungan bukan veto baru; Gate A/B, threshold >=0, komisi nol dan OD distance-only tetap. Histori/sumber tidak ditulis ulang. RBAC tetap tahap mendatang dan server tes temporer harus berhenti setelah tes. Baca review untuk bukti final dan batas, bukan menghitung ulang rating lama sebagai acceptance.

## Terbaru D-062/D-063 — revisi G selesai teknis

Plan §7.13/task G/review mengikat implementasi komisi 0% (ketiga jenis), OD hanya jarak NM (Input - OD Intl!H11), tabel/editor per putaran dengan FOB/CFR read-only engine, fuel/diesel lengkap, copy ringkas dan logo aset public asli. I4-INPUT.2/OD-DISTANCE.1/I4-BRIEF.6; 200 tes, dua tes UI final ulang, browser smoke dan 108 assertion independen lulus. Gate A/B dan fungsi hitungan inti tetap. Jangan mengembalikan tarif OD ke kasus baru atau mengubah fixed/histori agar tampak nol komisi; legacy replay tetap mendukung input aslinya. RBAC dashboard per peran untuk iterasi mendatang (sementara I5), hak/role belum ditentukan. G0..G5 selesai teknis, acceptance pengguna/MVP belum dinyatakan. Streamlit harus tetap berhenti setelah kerja. Detail D-061/D-060 di bawah adalah histori.

## Terbaru D-059/D-060 — revisi sumber/UI selesai teknis

Pengguna memberi execute 27 Oktober, menerima seluruh profil workbook sampai Supramax dan 1-year T/C sebagai target TCE. Empat profil Sheet1/AQABA/Sby/Godau aktif; kelompok Supramax serta Handymax/lebih kecil, klasifikasi fisik Handysize/Handymax/Supramax. Godau memakai proxy pasar Handysize 38k yang terlihat. **F0..F6 selesai: 180 tes, browser smoke, 82 assertion independen dua kasus.** Baca plan **§7.12/§7.12.10**, task/review/current-reader. Sumber fisik workbook, pasar Fearnpulse; Baltic hanya pengetahuan/histori. Jangan memasukkan Baltic ke kasus aktif atau menyebut tariff TC sebagai quote voyage/HPP/hire tambahan. Timestamp source/fetch/calc/fix berbeda, jangan backfill legacy unknown. Rule tambahan TENDER-CLOCK.1: putaran 180 detik tetap, receipt `[open,close)`, bid baru tidak reset; last valid timestamp mengalahkan sequence yang diedit. Legacy tanpa clock tetap replay. I4-BRIEF.5/PRICE.1 baru, formula/gate dasar tetap. Tidak ada transaksi/RBAC/MVP atau auto-award yang diizinkan. Larangan execute D-058 di bawah merupakan histori yang sudah digantikan D-059.

## Terbaru D-056/D-057 — UI lokal selesai teknis

Pengguna menerima pilihan manual profil dan memberi EXECUTE seluruh UI, mengikuti biru/putih `Desktop - 1.png` dengan tampilan sederhana/tegas. I4-U0..U5 selesai teknis: Streamlit 1.66.1, workflow service, persiapan voyage tanpa bid, fixed freight, editor tender/risiko, brief lima bagian, draft/unduhan dan pengujian. **151/151 tes lulus**, smoke browser GO/NO GO dan unduhan MD/JSON/ZIP lulus. Baca plan **§7.11**, task, review dan README. Rumus, rule, workbook/OD dan histori tetap; hanya validator/orchestration existing direfactor agar persiapan berbagi engine. Handysize siap; Supramax tidak dipalsukan menjadi profil lengkap/optimizer. Catatan lama tanpa UI/perencanaan belum execute adalah histori yang digantikan D-056. UI tetap internal/single-user lokal; bukan e-auction buyer, transaksi, MVP atau acceptance mentor. Jangan memakai field net_revenue_usd sebagai neto setelah voyage.

## Revisi terkini — D-053, stakeholder brief I4-BRIEF.4

I4-D1..D4 selesai teknis, 123 tes lulus. Plan §7.10 menggantikan layout/copy lama §7.9. Gross PI/PILOG dipisah, biaya/komisi/neto PILOG tampil; neto PI null, OE/HPS bukan HPP. Hasil neto setelah voyage = contribution_usd, **bukan net_revenue_usd** (setelah komisi saja). Hanya calculations menghitung nominal; commercial_financials additive dengan versi I4-FINANCIALS.1. Lima bagian satu brief, bukan lima output baru. Mode simulation/advisory/source/human status tetap pada JSON/audit; brief memakai bahasa estimasi langsung dan satu catatan basis/kewenangan, tanpa banner jargon. Data/rule/gate/fixed freight/OD/histori utuh. UI belum diimplementasikan. Baca current-reader/task/review terbaru; rating agent bukan approval mentor. Riwayat C/R di bawah bukan kontrak layout aktif.

## Pembaruan penguatan brief — D-051, 23 Oktober 2026

I4-C1..C5 selesai teknis: I4-BRIEF.3, 109/109 tes, dua run final dan self-review pada review I4. Baca current-reader/task/state sebelum memakai histori R/baseline di bawah. Headline, cause-specific layout, actions/deliverable/trigger dan metadata run ditambahkan; tidak mengubah rumus/gate/dataset/harga tetap/OD. UI tetap dilarang dalam scope ini. Rating subjektif GO 9/10, NO GO 9,5/10 bukan approval atau skor otomatis checklist; penerimaan mentor belum tercatat.

## Revisi hasil I4 — selesai teknis 23 Oktober 2026

D-048 mengizinkan execute revisi; I4-R1..R7 selesai, **91/91 tes lulus**. Baca `.agents/00_READ_CURRENT.md`, plan §7–9, task dan review I4. Formula/rule I4.1 tetap; brief I4-BRIEF.2 dan metrics I4-METRICS.1.

**Semua output internal PI/PILOG**, bukan materi/portal buyer. Buyer melihat freight, bukan OE/HPS, gap **FOB−OE/HPS**, alpha minimum, bid buyer lain atau ekonomi PILOG. Label bukan implementasi kontrol akses produksi.

Freight tampil per baris latest/all-bid. Fixture default kini menyimpan harga tetap turunan pricing; perubahan biaya/target TCE tidak otomatis mengubahnya. Legacy input tanpa fixed record tetap jalur indikasi dengan label jujur. Tambahan metrik/actions tidak mengubah gate/threshold. Sumber, OD dan histori dipertahankan. 67 tes adalah baseline lama; bukti revisi di review, bukan klaim acceptance mentor/MVP.

## Otorisasi terbaru — D-045, 22 Oktober 2026

**Pengguna memberi EXECUTE untuk seluruh I4-1 sampai I4-7 setelah pemeriksaan akhir rencana selesai, tanpa menunggu pengguna membaca ulang.** Pemeriksaan dokumentasi lulus; implementasi/tes simulasi lokal diizinkan. Batas lama menunggu execute di catatan sebelumnya adalah histori yang telah dipenuhi. Tidak ada izin transaksi, auto-award, integrasi produksi atau MVP; OD/workbook sumber dan histori I3 dipertahankan. Acuan tetap `docs/it_4/ITERATION_04_PLAN.md` dan task turunannya.

Dokumen ini berlaku untuk setiap agent yang bekerja di repository `pilog-cfr-dss`.

## Batas aktif — I4 diimplementasikan, menunggu review mentor

Per 22 Oktober 2026, **acuan utama I4 adalah `docs/it_4/ITERATION_04_PLAN.md`**; task `.agents/tasks/ITERATION_04.md` menurunkan rencana, bukan aturan alternatif. Kasus: urea granular bulk, kapal milik, 30.000 MT, Handysize, Bontang → Mundra/WCI, **satu arah laden-only**. Liquid/gas round voyage adalah konteks mentor, bukan scope tanker/gas I4.

**D-042: tarif OD berlaku untuk satu pengiriman satu arah; rumus biaya internalnya sengaja memasukkan perjalanan balik.** Jangan menyebut tarif OD sebagai tarif round voyage/dua pengiriman. OD read-only dan tidak dibagi dua/direbase; jelaskan perbedaan cakupan biaya sistem versus OD, bukan selisih sebagai margin/penghematan. D-043 mengizinkan perbedaan tanggal/tahun sumber untuk simulasi tanpa hard gate freshness/provenance, termasuk tanggal dua laporan indeks. Unit, basis produk/FOB, angka finite dan technical checks tetap wajib; bid aktif mengikuti cutoff kasus, bukan tanggal komputer. D-044 mengikat plan/task dan acceptance criteria.

Audit pengguna selesai dan izin D-045 telah dilaksanakan. **I4 diimplementasikan; 67/67 tes lulus**, termasuk 38 regresi I2/I3. Baca `.agents/reviews/ITERATION_04.md` dan task I4 untuk bukti. Input numerik/snapshot tersedia; 3.906 NM tetap acuan workbook, bukan aktual terverifikasi. Workbook sumber/OD, I2/I3, PNG/Draw.io/deck tidak diubah. Target TCE memakai proxy AQABA berlabel karena quote Fearnpulse belum terverifikasi. D-046 mencatat kontrak pricing engineering; bukan approval komersial.

## Konteks dan batas produk

PILOG CFR DSS adalah Decision Support System (DSS) untuk membantu Business Development/Commercial. **Scope aktif I4** ialah persiapan freight, perhitungan seluruh bid/ranking kandidat tender PI, lalu **GO/NO GO pelaksanaan CFR PILOG**. Gate A = last active + FOB >= OE/HPS; Gate B = gross-DWT screen + kontribusi baseline >= 0. Stress negatif dijelaskan, tidak veto baseline lolos. Tidak menetapkan award atau membandingkan profit FOB versus CFR. Tidak perlu hardcoded PI winner ID. Model FOB/CFR pra-penawaran di Iterasi 2 adalah **historis**, tetap dipertahankan sebagai regresi. Charter masih di luar simulasi kapal milik I3.

Sistem bersifat **prescriptive DSS**: ia menghitung alternatif, menerapkan constraint/rule yang disetujui, lalu mengusulkan tindakan beserta alasan. Sistem tidak menggantikan Commercial, Operations, Finance, Legal, Procurement, Risk, atau mentor domain.

**Konteks historis, bukan input aktif I4:** Simulasi Iterasi 3 telah diimplementasikan dan diuji, tetapi belum diterima mentor. Fixture I3 adalah **urea granular bulk Bontang→ECI sintetis**, bukan transaksi operasional. Cargo/DWCC **45.000 MT dipakai untuk seluruh hitungan**; tidak ada alokasi 46.000 MT. Indeks, OE/HPS, bid, kandidat, dan asumsi ekonomi yang tidak dapat diturunkan dari CSV wajib berlabel `simulation_only`; provenance input ditampilkan, sedangkan persetujuan domain nyata masih menunggu mentor. Untuk pekerjaan aktif, baca `.agents/00_READ_CURRENT.md`, `docs/it_4/ITERATION_04_PLAN.md`, `.agents/tasks/ITERATION_04.md` dan `.agents/reviews/ITERATION_04.md`; kontrak I3 hanya untuk regresi.

## File yang wajib dibaca sebelum mengubah kode

1. `.agents/ITERATION_STATE.json`
2. `.agents/PLANS.md`
3. `.agents/reviews/ITERATION_01.md`
4. task iterasi aktif di `.agents/tasks/`
5. file kode, test, dan input yang akan diubah

## Kebijakan matematika dan keputusan

- Jangan membiarkan LLM menghitung angka bisnis, fuel, port tariff, voyage cost, TCE, margin, atau output keputusan.
- Tulis kalkulasi dalam fungsi Python murni, deterministik, dan dapat diuji. Gunakan `Decimal` untuk nilai uang/rate; konversi unit harus eksplisit.
- Formula tidak boleh berada di UI, Markdown generator, prompt, atau JSON policy file.
- Setiap fungsi kalkulasi wajib memiliki test angka contoh, test boundary, unit input/output, dan penanganan missing/invalid input.
- Jangan menyamakan `freight_selling_rate`, `freight_cost`, `contribution_margin`, `TCE`, `revenue`, dan `profit`.
- Jangan mengubah definisi Index, Alpha, Freight, Adjustment, TCE, margin floor, atau Gate tanpa mencatat keputusan di `.agents/DECISIONS.md`.

## Batas simulation-first

- Semua output harus berstatus `simulation` dan `advisory-only`.
- Tidak ada write-back, auto-quotation, auto-fixture, auto-RFQ, auto-approval, hedge, transaksi, atau integrasi produksi.
- Data kosong yang dibutuhkan hitungan, unit/basis tidak jelas, atau constraint teknis yang gagal tidak boleh diganti diam-diam dengan nol/true. **Output I3/I4 hanya GO/NO GO; masalah data menjadi `NO_GO / DATA_ISSUE` dan harus dijelaskan sebagai belum aman untuk GO, bukan penolakan buyer.** I2 historis tetap memakai outcome HOLD/DEFER sesuai kontrak lamanya.
- Jangan memaksakan target 60% FOB / 40% CFR sebagai outcome keputusan.
- Jangan mengklaim bahwa data eksperimen adalah quote, approval, P&L, atau keputusan produksi.

## Urutan desain yang wajib dijaga

```text
data contract
-> quality and normalization
-> physical/operational constraints
-> deterministic calculation modules
-> scenarios
-> prescriptive rules and gates
-> decision brief
-> human review and iteration feedback
```

Financial recommendation tidak boleh berjalan sebagai `approved` jika hard constraint fisik, data quality kritis, atau evidence dasar belum lolos.

## Aturan sumber dan evidence

- Simpan raw value, normalized value, unit, currency, dan model/rule version bila data diproses. Source dan timestamp/as-of disimpan bila tersedia; ketidakhadirannya dicatat, tetapi tidak otomatis HOLD untuk simulasi revisi Iterasi 2.
- Bedakan master data, transaction/case data, market data, policy/rule configuration, calculation result, dan human decision.
- Policy JSON hanya menyimpan rule/threshold yang disetujui; bukan tempat menyembunyikan angka kalkulasi atau keputusan yang seharusnya berasal dari data.
- Setiap output keputusan harus menunjukkan Case ID, snapshot/input version, formula version, rule version, data-quality status, alasan/reason code, dan human approval status.

## Cara menyelesaikan task

1. Ambil satu task yang `ready` dari task file iterasi aktif.
2. Tulis acceptance criteria dan input/output contract sebelum kode.
3. Implementasikan perubahan terkecil yang dapat diuji.
4. Tambahkan/ubah test dahulu atau bersamaan dengan fungsi.
5. Jalankan test dan pipeline yang relevan.
6. Periksa unit, currency, basis biaya, rounding, dan kondisi gagal.
7. Catat evidence, asumsi, gap, dan perubahan state pada review/decision log.
8. Jangan memulai task berikutnya jika task saat ini masih `blocked` tanpa mencatat blocker.

## Penanganan feedback

- Feedback mentor adalah requirement sampai mentor merevisi/mencabutnya.
- Takeaway GPT adalah guardrail desain MVP: explainability, human-in-the-loop, dan jangan over-engineer.
- Takeaway Gemini adalah kandidat desain teknis; setiap requirement tambahan harus diperiksa terhadap data yang tersedia dan disetujui mentor.
- Konflik antar sumber dicatat sebagai pertanyaan/keputusan terbuka, bukan diselesaikan dengan asumsi agent.

## Handoff wajib

Setiap pekerjaan harus menyebutkan:

- tujuan dan task ID;
- file yang diubah;
- test/perintah yang dijalankan serta hasil;
- asumsi dan input yang dipakai;
- hasil yang dapat dipercaya dan yang belum dapat dipercaya;
- blocker/pertanyaan untuk mentor;
- update yang dibuat pada iteration state/review.
