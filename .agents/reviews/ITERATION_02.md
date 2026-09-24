# Review Pack — Simulasi Iteration 2

## Revisi aktif 23 September 2026 — siap untuk kritik mentor, belum diterima

**Status:** R01–R06 diimplementasikan; **26/26 tes lulus**; contoh run pra-penawaran yang dipertahankan: `outputs/runs/i2_20260923T091307166739Z_f5c4e74a/`. Seluruh bagian setelah subjudul “Arsip review awal” adalah catatan **pra-revisi** dan sengaja dipertahankan sebagai histori, bukan aturan/angka aktif. Folder run dan fixture pra-revisi yang disebut di arsip telah dihapus dalam cleanup repo 24 September; angka historis di bawah tidak lagi dapat direplay dari folder tersebut. Keputusan mentor `accepted`, `needs-revision`, atau `blocked` belum diberikan.

| Butir | Bukti revisi aktif |
|---|---|
| Input | `data/dataset_ready.csv` dan katalog kini 61 variabel; alokasi 46.000 MT lama dihapus dari input aktif dan ditolak bila muncul lagi. Fixture aktif: `data/raw/iteration_02_pre_offer_simulation.json`. |
| Kontrak | PI Group menjual komoditas; PILOG menyediakan freight. Cargo/DWCC **45.000 MT** untuk hari port, screen, revenue, komisi, dan biaya/MT. |
| Pilihan | Dua alternatif komersial: FOB baseline harga dan CFR. Dalam CFR, Handysize gagal batas kelas 40.000 DWT; Supramax kasus 58.000 DWT lolos screen DWT awal. Tidak ada klaim availability/DWCC aktual. |
| Gate 1 | `CFR_ELIGIBLE` meski buyer `not_approached`; sumber/as-of yang ditunda adalah WARN, bukan bypass. Input numerik/unit rusak serta buyer decline tetap punya tes negatif. |
| Gate 2 | `CFR_CANDIDATE_PENDING_HUMAN_REVIEW` karena kontribusi freight PILOG positif. Ini kandidat untuk review atasan **sebelum** buyer didekati, bukan approval atau quote. FOB profit belum diketahui. |
| Audit | Run menyimpan snapshot/hash dataset, katalog, manual, dan kebijakan kelas kapal; trace, dua gate, dan decision brief. `python -m unittest discover -s tests -p test_*.py -v` → 26/26 lulus. |

**Angka run Python, bukan hitungan LLM:** FOB USD 253/MT; tarif freight USD 20/MT; CFR indikatif USD 273/MT; gross freight revenue USD 900.000; tiga komisi USD 56.250; running + bunker + port/other USD 735.303,8965; kontribusi freight PILOG USD 108.446,1035. Angka ini hanya kasus simulasi Bontang–ECI; tidak membuktikan margin barang PI Group atau harga yang akan diterima buyer.

**Perbedaan dari run historis:** run awal memakai 46.000 MT billing/alokasi dan menghasilkan revenue USD 920.000 serta kontribusi USD 127.196,1035. Perubahan output terutama akibat koreksi kuantitas menjadi 45.000 MT. Jangan menyamakan dua run dengan dua transaksi berbeda; run awal adalah hasil kontrak data yang kemudian dibatalkan mentor.

**Masukan mentor yang masih diperlukan:** (1) bukti ekonomi FOB PI Group; (2) apakah tiga komisi benar kumulatif atas gross; (3) rincian port/agency di USD 200.000 agar tidak ganda; (4) ambang kontribusi/margin setelah simulasi; (5) kapal aktual, DWCC, draft/terminal/laycan/availability; (6) validitas parameter rute Bontang–ECI sebelum penggunaan nyata. Data lineage/Fleetra/SAP/AIS dan approval formal tetap pekerjaan domain berikutnya, bukan alasan menghambat simulasi ini. Catat kritik dan keputusan mentor di bagian penutup sebelum iterasi berikutnya.

## Arsip review awal — pra-revisi, jangan gunakan sebagai kontrak aktif

> **Retensi artefak:** tabel arsip di bawah menyebut path run/fixture pra-revisi untuk menjelaskan urutan kerja pada saat itu. File-file tersebut sengaja **tidak ikut repo setelah cleanup 24 September 2026**; hanya ringkasan historisnya yang dipertahankan. Gunakan run aktif di bagian atas untuk audit yang masih dapat dibuka.

> **Arahan revisi 2026-09-23:** pengguna mengklarifikasi bahwa CSV menjadi ground truth numerik simulasi, DWCC 45.000 MT dipakai untuk semua hitungan, seller komoditas adalah entitas PI Group, PILOG menjual freight, dan DSS perlu menilai CFR sebelum buyer dihubungi. Range kelas Handysize 20-40 ribu DWT serta Supramax 50-60 ribu DWT akan menjadi konfigurasi referensi. Keputusan dan task revisi tercatat di `../DECISIONS.md` serta `../tasks/ITERATION_02_PROPOSED.md`. Seluruh angka dan outcome run di bawah adalah **hasil sebelum revisi**. Review akhir mentor tetap menunggu run revisi.

**Tanggal persiapan:** 2026-09-22  
**Status:** feedback mentor parsial sudah diterapkan dan diuji end-to-end; **penerimaan akhir iterasi belum diputuskan**. Keputusan penutup (`accepted`, `needs-revision`, atau `blocked`) masih kosong.  
**Batas:** simulasi advisory-only, bukan quotation, fixture, pemesanan, atau **MVP**.

## 1. Hasil singkat

Iteration 2 memisahkan input, validasi, hitungan fisik, ekonomi skenario, Gate 1/2, dan laporan. Seluruh 62 variabel CSV telah dipetakan; rute dibaca dari dataset. Modul perhitungan memakai `Decimal`, dengan versi rumus/aturan tercatat dalam output. Gate 1 sekarang menghentikan kasus dengan kualitas kritis `BLOCK`. Gate 2 hanya mengurutkan skenario CFR yang feasible, comparable, dan memenuhi objective/floor yang disetujui; hasilnya tetap membutuhkan persetujuan manusia.

Input manual dasar kini memiliki enam bukti komersial bernilai `true`, sehingga Gate 1 `CFR_ELIGIBLE`; Gate 2 tetap HOLD karena definisi ekonomi dan kapal pada file dasar belum lengkap. File simulasi owned-vessel yang terpisah menguji alur sampai Gate 2: Supramax dipilih secara **conditional**, sedangkan Handysize benchmark gagal pemeriksaan DWT. Jangan gunakan hasilnya sebagai harga penawaran atau bukti kapal tersedia.

## 2. Bukti yang bisa diperiksa

| Bukti | Lokasi | Catatan |
|---|---|---|
| Snapshot input | `data/dataset_ready.csv` dan `data/raw/iteration_02_owned_e2e_simulation.json` | CSV 62 baris adalah register satu kasus; Index/Alpha angka demo Iteration 1, bukan harga pasar saat ini. |
| Kontrak variabel | `data/reference/variable_catalog.csv` | 62/62 baris cocok dengan nomor dan nama variabel CSV. |
| Workbook belajar | `outputs/learning/iteration_02_variable_map.xlsx` | 10 sheet: ringkasan, seluruh variabel, tujuh grup, pertanyaan mentor. Bukan sumber rumus sistem. |
| Kontrak ekonomi | `.agents/contracts/ITERATION_02_ECONOMICS.md` | Tarif jual dan basis kuantitas telah dikonfirmasi; komisi gross, floor, dan availability masih asumsi simulasi. |
| Run terbaru | `outputs/runs/i2_20260922T101102273077Z_5a55dc59/` | SHA-256 dataset/katalog/manual, salinan input, formula I2.1, dan rule I2.3 ada di run ini. |
| Laporan untuk dibaca | Run terbaru: `decision_brief.md` | Menjelaskan dua basis kuantitas, layar kelas kapal, ekonomi Supramax, dan status conditional. |
| Bukti mesin | Run terbaru: `quality_report.json`, `calculation_trace.json`, `scenario_comparison.json`, `scenario_economics.json`, `gate_evaluation.json` | Semua angka berasal dari Python; trace dapat diaudit. |
| Tes | `tests/unit/` dan `tests/integration/` | `python -m unittest discover -s tests -p test_*.py -v` → **20/20 lulus**. |

Run di atas menyimpan `input_snapshot/dataset.csv`, `catalog.csv`, dan `manual.json` yang diverifikasi dengan SHA-256, serta tidak ditimpa. Jika input berubah, jalankan lagi dan rujuk ID run baru.

## 3. Penyelesaian task

| Task | Hasil | Status review |
|---|---|---|
| I2-T01 | 62 variabel dipetakan; workbook dan dependency/pertanyaan mentor dibuat; rute tidak ditanam dalam kode baru. | Siap review. |
| I2-T02 | Freight Rate ditetapkan tarif jual; 45.000 MT fisik dan 46.000 MT billing/alokasi; other costs terpisah dari bunker/running. Basis gross untuk tiga komisi dan floor masih asumsi simulasi. | Sebagian dikonfirmasi; rincian kontrak masih direview. |
| I2-T03 | Modul capacity, voyage days, fuel, cost, pricing, physical, economics, dan tes deterministik dibuat. Tidak menghitung TCE karena definisinya belum disetujui. | Siap review teknis; ekonomi bersyarat. |
| I2-T04 | Kualitas kritis tersambung ke Gate 1; rute dari input; DWT headroom hanya screen parsial. Draft, stowage, terminal/port, dan vessel availability belum terbukti. | Parsial aman; data domain diperlukan. |
| I2-T05 | Simulasi baru membatasi opsi pada kapal PILOG. Supramax memakai profile kasus; Handysize memakai DWT benchmark Baltic untuk capacity screen. Gate 2 memberi pilihan conditional bila masih ada asumsi. | E2E teruji; bukti availability nyata belum ada. |
| I2-T06 | Review pack, trace, tes, daftar asumsi, dan formulir keputusan mentor tersedia. | Menunggu isian/keputusan mentor. |

## 4. Pembacaan angka yang benar

Trace fisik kasus contoh menghitung ~33,4196 hari voyage; FO laut ~USD 317.987,02 dan DO laut/pelabuhan ~USD 29.765,84. Angka itu **belum** mencakup daily vessel cost, port/other cost yang disetujui, komisi, atau batas kontrak yang berbeda antar mode kapal. DWT headroom ~10.700 MT adalah pemeriksaan bobot saja, bukan bukti kelayakan penuh. Asal data Bontang → ECI merupakan override eksperimental atas data yang semula berasal dari Aqaba; jarak, waktu, biaya pelabuhan, dan kapal perlu validasi rute nyata.

Run owned-vessel memakai 45.000 MT untuk hari pelabuhan (4,5 hari muat; 7,5 hari bongkar) dan 46.000 MT untuk revenue. Python menghitung gross freight revenue USD 920.000, komisi tiga rate USD 57.500, total freight cost USD 735.303,8965, dan net freight contribution USD 127.196,1035. Benchmark Baltic Handysize DWT 38.200 MT lebih kecil dari muatan fisik 45.000 MT; skenario itu `INFEASIBLE` tanpa mengasumsikan bunker allowance. Gate 2 memilih Supramax dengan status `CFR_CONDITIONAL_PENDING_HUMAN_REVIEW`. Semua availability dan otorisasi dalam input run masih simulasi, bukan bukti transaksi nyata.

## 5. Perbandingan dengan Iteration 1

| Iteration 1 | Iteration 2 |
|---|---|
| Gate 1 bisa menyatakan CFR eligible walau quality `BLOCK`. | `BLOCK` memaksa `HOLD_DATA_ISSUE`; diuji. |
| Freight cost/selling rate dan kelayakan banyak berasal dari input skenario statis. | Komponen fisik dihitung dari CSV; ekonomi hanya dihitung bila kontrak, profile, harga, dan bukti cocok. Bila tidak, HOLD dengan reason code. |
| Alur proof-of-concept berupa skrip bertahap. | Paket `src/pilog_cfr_dss/` modular dan testable; sembilan skrip lama dihapus dari worktree setelah tes lulus, tetapi versi tracked dapat dipulihkan dari riwayat Git dan output I1 tetap ada. |
| Trace keputusan terbatas. | Output run tidak ditimpa; hash input, formula/rule version, trace, alasan Gate, dan status approval tersedia. |

## 6. Hal yang harus diputuskan mentor

1. Tarif jual per MT telah dikonfirmasi; bagaimana sumber quote dan tanggalnya dibuktikan pada setiap kasus nyata?
2. USD 200.000 terpisah dari bunker dan running cost; komponen port, agency, canal, dan biaya lainnya apa saja di dalamnya?
3. Kapal PILOG dipakai dalam simulasi; apakah `running costs` tepat sebagai biaya incremental? Model charter ditunda ke iterasi berikutnya.
4. Basis 45.000 MT fisik versus 46.000 MT billing/alokasi telah dikonfirmasi; apakah terdapat deadfreight, minimum quantity, atau toleransi kontrak?
5. Semua tiga komisi dipakai; apakah masing-masing benar berbasis gross freight revenue dan kumulatif menurut kontrak?
6. Objective net freight contribution dan floor USD 0 masih asumsi simulasi; apakah ini akan menjadi kebijakan Gate 2 dan bagaimana FOB baseline dibandingkan?
7. Baltic menyediakan benchmark Handysize 38.200 DWT, bukan kapal PILOG. Di mana data kapal/availability/laycan/draft/stowage/terminal aktual per skenario?
8. Validitas override rute Bontang → ECI, termasuk laden/ballast distance, port time, port cost, dan tanggal/freshness setiap variabel biaya/pasar.
9. Siapa pemilik setiap bukti komersial di Gate 1 dan siapa yang boleh mengubah statusnya menjadi `true`/`false`?

## 7. Keputusan review mentor — isi setelah diskusi

| Butir | Konfirmasi / koreksi | Pemilik | Tanggal / referensi |
|---|---|---|---|
| Price objects dan sumber | Freight Rate = tarif jual PILOG; sumber/as-of quote per kasus masih terbuka. | Mentor BusDev via pengguna | 2026-09-22 / D-004 |
| Cost boundary owned/charter | Owned vessel untuk simulasi; USD 200.000 other costs terpisah dari bunker/running; charter ditunda. | Mentor direction + pengguna | 2026-09-22 / D-012 |
| Denominator dan komisi | 45.000 MT operasional; 46.000 MT revenue/alokasi; ketiga komisi dipakai, basis gross masih asumsi. | Mentor commercial via pengguna | 2026-09-22 / D-011, D-013 |
| Objective/floor Gate 2 | Belum diisi | Mentor BusDev | — |
| Kapal/rute/operasional | Belum diisi | Mentor shipping | — |
| Kasus gagal tambahan dan perubahan formula | Belum diisi | Mentor + intern IT | — |

**Keputusan iterasi:** belum ditetapkan. Pilih `accepted`, `needs-revision`, atau `blocked` setelah umpan balik di atas. **Jangan lanjut ke MVP**; bila logika perlu diperbaiki, bentuk task Iteration 3 dari keputusan ini. Final Simulation Validation baru dimulai setelah mentor menerima logika simulasi.
