# Task board Iterasi 3 — tender → DSS CFR

**Status 2026-10-08:** pekerjaan teknis simulasi selesai untuk review mentor; **belum mentor-approved**. Dokumen kontrak dan alasan bisnis: `docs/it_3/ITERATION_03_TENDER_DSS_PLAN.md`.

- [x] **I3-0 Kontrak keputusan.** `FOB = I + alpha_buyer`, `CFR = FOB + proxy biaya OD`, `FOB − OE/HPS ≥ 0`, kontribusi freight PILOG `≥ 0`, aksi publik hanya `GO`/`NO_GO`. Pertanyaan P0 yang belum dijawab tetap tercatat, bukan disulap menjadi kebijakan nyata.
- [x] **I3-1 Dataset dan lineage.** CSV aktif 29 variabel urea granular bulk Bontang, dua fixture tender GO/NO GO; semua angka non-Aqaba `simulation_only_synthetic` atau `simulation_only_assumption`.
- [x] **I3-2 Kalkulasi tender.** Midpoint Argus/Fertecon sintetis, rata-rata, bid per putaran, alpha sekali, harga FOB/CFR, gap OE; Python `Decimal` dan tes boundary.
- [x] **I3-3 Voyage/freight.** Pakai ulang physical/cost I2; biaya OD proxy ≠ tarif jual PILOG, tidak ada double count; hanya kapal milik, screen DWT awal.
- [x] **I3-4 Gate pasca-tender.** Gate A: kandidat PI dan floor OE/HPS. Gate B: kelas kapal serta kontribusi PILOG. Input rusak → `NO_GO / DATA_ISSUE`, bukan penolakan komersial buyer.
- [x] **I3-5 E2E dan decision brief.** CLI menjalankan dua fixture dan menyimpan brief, JSON, serta snapshot; 38 tes unit/integrasi/regresi lulus pada 8 Oktober 2026.
- [ ] **I3-6 Review mentor.** Validasi formula tender, seri indeks, OD matrix resmi, tarif jual PI–PILOG, basis komisi, kapal/rute, dan bahasa GO/NO GO. Keputusan Iterasi 4/final simulation validation menunggu hasil review.

**Perintah review:** `python -m unittest discover -s tests -v` lalu `python scripts/run_iteration_03.py`. Baca dua `decision_brief.md` terbaru. Jangan stage/commit/push tanpa meninjau izin berbagi data perusahaan; agent tidak melakukannya.
