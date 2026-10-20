# Panduan Agentic Coding - PILOG CFR DSS

Dokumen ini berlaku untuk setiap agent yang bekerja di repository `pilog-cfr-dss`.

## Konteks dan batas produk

PILOG CFR DSS adalah Decision Support System (DSS) untuk membantu Business Development/Commercial. **Scope aktif Iterasi 3** ialah menerima kandidat dari tender PI lalu mengevaluasi **GO/NO GO pelaksanaan CFR PILOG**; bukan memilih pemenang tender atau membandingkan profit FOB versus CFR. Model FOB/CFR pra-penawaran di Iterasi 2 adalah **historis**, tetap dipertahankan sebagai regresi. Charter masih di luar simulasi kapal milik I3.

Sistem bersifat **prescriptive DSS**: ia menghitung alternatif, menerapkan constraint/rule yang disetujui, lalu mengusulkan tindakan beserta alasan. Sistem tidak menggantikan Commercial, Operations, Finance, Legal, Procurement, Risk, atau mentor domain.

Saat ini **Simulasi Iterasi 3 telah diimplementasikan dan diuji, tetapi belum diterima mentor**. Fixture I3 adalah **urea granular bulk Bontang→ECI sintetis**, bukan transaksi operasional. Cargo/DWCC **45.000 MT dipakai untuk seluruh hitungan**; tidak ada alokasi 46.000 MT. Indeks, OE/HPS, bid, kandidat, dan asumsi ekonomi yang tidak dapat diturunkan dari CSV wajib berlabel `simulation_only`; provenance input ditampilkan, sedangkan persetujuan domain nyata masih menunggu mentor. Baca `.agents/00_READ_CURRENT.md`, `docs/it_3/ITERATION_03_TENDER_DSS_PLAN.md`, dan `.agents/tasks/ITERATION_03.md` sebelum mengubah kode.

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
- Data kosong yang dibutuhkan hitungan, unit/basis tidak jelas, atau constraint teknis yang gagal tidak boleh diganti diam-diam dengan nol/true. **Output I3 hanya GO/NO GO; masalah data menjadi `NO_GO / DATA_ISSUE` dan harus dijelaskan sebagai belum aman untuk GO, bukan penolakan buyer.** I2 historis tetap memakai outcome HOLD/DEFER sesuai kontrak lamanya.
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
