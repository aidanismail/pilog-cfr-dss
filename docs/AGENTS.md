# Panduan Agentic Coding — PILOG CFR DSS

Dokumen ini berlaku untuk agent yang bekerja di repository `pilog-cfr-dss/`. Baca `docs/PLANS.md` sebelum mengubah kode.

## Konteks proyek

Repository ini adalah prototipe MVP untuk CFR Decision Support System PILOG. Mentor merupakan domain expert shipping, logistics, dan management. Agent membantu pekerjaan CS/IT; agent tidak menggantikan keputusan bisnis mentor, Commercial, Operations, Finance, Legal, Procurement, atau Risk/Treasury.

Dataset eksperimen utama Iterasi 1 adalah `data/dataset_ready.csv`. Dataset ini berbasis data Aqaba, tetapi rutenya diubah menjadi **Bontang → ECI hanya untuk simulasi eksperimen**. Perubahan ini bukan perubahan rute produksi atau system-of-record PILOG. Perubahan yang diketahui hanya rute; agent tidak boleh mengasumsikan jarak, port time, bunker, freight, biaya, atau field lain sudah dihitung ulang untuk rute baru. File ini dapat digunakan untuk eksperimen teknis, tetapi belum otomatis final dari sisi definisi bisnis, basis harga, freshness, atau otoritas sumber.

## Batas MVP wajib

## Mode kerja saat ini: Simulation Build

Sebelum MVP, semua coding berada dalam mode simulasi. Gunakan `data/dataset_ready.csv` sebagai skenario eksperimen Bontang → ECI, bukan sebagai data produksi. Tujuannya membuktikan bentuk pipeline dan menemukan gap, bukan menghasilkan quotation atau keputusan komersial.

- Kerjakan batch B0–B9 sesuai urutan di `docs/PLANS.md`; jangan melompati validasi demi membuat UI.
- Setiap batch wajib memiliki acceptance criteria, test/fixture, output yang dapat diperiksa, dan catatan gap.
- Semua output simulasi wajib bertanda `simulation` dan `advisory-only`.
- Dilarang write-back atau mengirim data ke Fleetra, Procure-X, SAP, DMS, pelanggan, broker, pemasok, atau sistem eksternal.
- Jika input atau definisi bisnis belum pasti, buat status `warn`/`block` dan catat pertanyaan untuk mentor.

- Fokus pada satu Case pilot cargo/rute.
- Gunakan `data/dataset_ready.csv` sebagai input utama Case eksperimen Bontang → ECI; jangan mengubah file sumbernya dan jangan menganggapnya sebagai data produksi.
- Gunakan impor manual Excel/CSV terlebih dahulu.
- Pertahankan formula yang dapat dijelaskan: `FOB = Indeks + Alpha` dan `CFR = FOB + Freight + A`.
- Semua hasil pricing, margin, dan Gate adalah **advisory-only** sampai manusia berwenang menyetujui.
- Jangan menambahkan integrasi produksi, auto-approval, auto-fixture, auto-quotation, auto-RFQ, atau eksekusi hedge tanpa permintaan dan persetujuan eksplisit.
- Jangan menggunakan target 60% FOB / 40% CFR untuk memaksa hasil CFR ketika data, margin, cash, keselamatan, compliance, atau wewenang tidak terpenuhi.

## Aturan perubahan kode

- Baca file terkait dan ikuti pola repository sebelum mengedit.
- Pisahkan ingestion, validasi, kalkulasi, skenario, Gate, dan UI; jangan menaruh formula bisnis di komponen UI.
- Jangan mengubah workbook sumber di luar repository. Perlakukan `Experiments/` sebagai read-only.
- Perlakukan `data/dataset_ready.csv` sebagai read-only; simpan hasil normalisasi, field tambahan, dan snapshot berversi sebagai artefak terpisah.
- Sebelum memakai kolom CSV dalam formula, periksa header, tipe, satuan, currency, grain, missingness, duplikasi, dan basis bisnisnya.
- Perlakukan perubahan rute Aqaba → Bontang–ECI sebagai transformasi yang harus diaudit; validasi ulang jarak, arah rute, port, waktu, bunker, freight, dan biaya sebelum menyebut hasilnya representatif.
- Jangan memasukkan data komersial rahasia, kredensial, `.env`, atau file besar mentah ke commit.
- Simpan raw value, normalized value, unit, basis, sumber, timestamp, dan versi bila data diproses.
- Data kosong, stale, atau basis tidak jelas harus menghasilkan status error/warning/advisory-only—bukan nilai nol diam-diam.
- Jangan mengubah definisi Indeks, Alpha, Freight, `A`, margin, atau aturan Gate tanpa mencatat keputusan mentor.
- Gunakan perubahan kecil dan mudah direview. Hindari refactor besar yang tidak dibutuhkan MVP.

## Prosedur setiap tugas

1. Baca `docs/PLANS.md` dan identifikasi fase MVP yang relevan.
2. Jelaskan asumsi, file yang akan diubah, dan risiko data sebelum coding.
3. Implementasikan perubahan terkecil yang memenuhi tujuan.
4. Tambahkan atau perbarui test untuk perilaku yang berubah.
5. Jalankan test dan laporkan command serta hasilnya.
6. Periksa unit, currency, basis FOB/CFR, pembulatan, dan propagasi error.
7. Dokumentasikan gap atau keputusan yang memerlukan validasi mentor.

## Standar kualitas kalkulasi

- Setiap formula harus memiliki test angka contoh.
- Gunakan tipe numerik yang sesuai; jangan mencampur USD/MT, USD/day, lump sum, dan MT tanpa konversi eksplisit.
- Bedakan `freight_cost`, `freight_selling_rate`, `contribution_margin`, dan `transaction_value`.
- Skenario harus berasal dari snapshot Case yang sama agar perbandingan adil.
- Output wajib memuat Case ID, as-of date, input/model version, asumsi, status kualitas, dan reason code.

## Gate dan otoritas

- Gate 1: periksa kelayakan awal dan kelengkapan bukti.
- Gate 2: bandingkan kelayakan, ekonomi, risiko, cash, daya saing, dan otoritas.
- Agent boleh menghitung, memberi peringatan, dan merekomendasikan.
- Agent tidak boleh menyatakan transaksi telah disetujui, aman, layak dieksekusi, atau telah di-hedge.

## Handoff dan laporan

Setiap pekerjaan selesai harus melaporkan:

- ringkasan perubahan;
- file yang diubah;
- test yang dijalankan dan hasilnya;
- asumsi atau data gap yang ditemukan;
- langkah manual yang masih diperlukan mentor/user;
- apakah hasilnya masih prototype/advisory-only.
