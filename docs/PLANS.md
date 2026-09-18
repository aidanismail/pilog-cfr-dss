# Rencana Implementasi PILOG CFR DSS

## Tujuan

Membangun prototipe **Minimum Viable Product (MVP)** untuk membantu Business Development/Commercial PILOG menilai apakah satu peluang ekspor layak dipertimbangkan dengan CFR dibandingkan FOB.

Alur inti:

```text
Input voyage + komersial
→ validasi dan normalisasi
→ snapshot Case berversi
→ hitung FOB/CFR dan biaya voyage
→ bandingkan skenario terbatas
→ Gate 1 dan Gate 2
→ decision brief advisory untuk persetujuan manusia
```

## Batas MVP

### Termasuk

- Satu jenis Case pilot cargo/rute yang disepakati mentor.
- Dataset eksperimen `data/dataset_ready.csv` sebagai input utama Iterasi 1; dataset ini berbasis data Aqaba dengan rute yang diubah menjadi Bontang → ECI hanya untuk simulasi.
- Impor manual dari Excel/CSV; integrasi Fleetra, Procure-X, dan SAP belum diperlukan.
- Model `Case`, `Cargo`, `Voyage`, `Vessel`, `Quote`, `Scenario`, dan hasil Gate.
- Validasi field wajib, satuan, basis harga, nilai tidak wajar, duplikasi, dan freshness.
- Formula transparan:

  ```text
  FOB = Indeks + Alpha
  CFR = FOB + Freight + A
  Margin freight = Freight selling rate − biaya freight relevan
  ```

- Skenario dasar FOB versus CFR.
- Perbandingan kapal PILOG versus charter hanya jika inputnya benar-benar comparable dan disetujui mentor.
- Gate 1 kelayakan awal dan Gate 2 keputusan akhir yang menghasilkan rekomendasi **advisory-only**.
- Decision brief, reason code, versi input/model, asumsi, dan audit trail lokal.
- Unit test untuk ingestion, validasi, formula, skenario, dan Gate.

### Tidak termasuk

- Auto-approval CFR atau pemaksaan target 60% FOB / 40% CFR.
- Auto-vessel selection, RFQ, supplier award, charterparty, customer quotation, atau fixture.
- Eksekusi hedge, auto-trading, posting akuntansi, atau live P&L.
- Integrasi write-back ke Fleetra, Procure-X, SAP, DMS, atau platform eksternal.
- Machine learning/prediksi harga sebelum formula dan data dasar tervalidasi.
- Dukungan semua komoditas, semua rute, atau semua tipe kapal.

## Fase saat ini — Simulation Build sebelum MVP

Kita **belum membangun MVP operasional**. Tahap coding pertama adalah simulasi pipeline untuk menguji apakah alur data, model Case, validasi, kalkulasi, skenario, dan Gate dapat bekerja dari awal sampai akhir. Dataset `data/dataset_ready.csv` digunakan sebagai skenario eksperimen Bontang → ECI; hasil simulasi tidak boleh dianggap sebagai quotation, approval, keputusan penjualan, atau data produksi PILOG.

### Aturan simulation-first

- Setiap batch harus kecil, dapat dijalankan ulang, dan memiliki output yang bisa diperiksa.
- Gunakan data lokal/read-only dan dummy fixture; jangan melakukan write-back ke Fleetra, Procure-X, SAP, DMS, atau platform eksternal.
- Semua keluaran diberi metadata `simulation`, Case ID, input version, formula version, dan `advisory-only`.
- Jangan menyembunyikan data kosong atau asumsi route override; tampilkan sebagai status dan catat di `docs/known_gaps.md`.
- Mentor memvalidasi makna shipping/logistics dan kewajaran hasil; agent/kamu mengimplementasikan pipeline serta test.
- Jangan menambah UI kompleks sebelum batch data dan kalkulasi dapat direproduksi lewat command line/test.

### Rencana coding per batch

| Batch | Fokus | Isi implementasi | Bukti selesai |
|---|---|---|---|
| B0 — Baseline | Reproducibility dan batas simulasi | README eksperimen, konfigurasi path, versi Python/dependensi, identitas dataset, checksum bila tersedia | Satu command menjalankan smoke check tanpa mengubah CSV sumber |
| B1 — Inspect | Memahami CSV | Profil header, tipe, jumlah baris, missingness, duplikasi, nilai unik, dan kandidat field; simpan laporan profil | Laporan profil dan daftar pertanyaan data |
| B2 — Ingest | Membentuk record mentah | Loader CSV read-only, mapping header ke field kanonis, error handling, dan Case ID simulasi | Satu record mentah Bontang–ECI dengan provenance jelas |
| B3 — Quality | Validasi dan status kualitas | Cek kolom wajib, tipe, satuan, angka positif, route, basis, freshness, dan status `pass/warn/block` | Laporan kualitas; data bermasalah tidak diam-diam lolos |
| B4 — Normalize | Snapshot keputusan | Normalisasi nama/satuan/currency/time, pemisahan raw-versus-normalized, versi snapshot, dan issue register | Snapshot Case berversi yang dapat direproduksi |
| B5 — Calculate | Mesin formula | Implementasi dan test `FOB = Indeks + Alpha`, `CFR = FOB + Freight + A`, voyage cost, dan margin eksperimen | Hasil kalkulasi cocok dengan contoh review mentor |
| B6 — Scenario | Perbandingan terbatas | Skenario FOB, CFR dasar, serta owned/chartered jika input comparable; sensitivitas kecil | Tabel perbandingan dengan driver dan asumsi |
| B7 — Gates | Simulasi keputusan | Gate 1/Gate 2 sebagai fungsi aturan; reason code; hasil advisory-only | Case menghasilkan status Gate dengan alasan |
| B8 — Brief | Keluaran manusia | Decision brief Markdown/JSON berisi input, kualitas, formula, skenario, driver, risiko, dan rekomendasi | Mentor dapat membaca dan menantang hasil tanpa membuka kode |
| B9 — Review | Validasi domain dan handover | Jalankan ulang pipeline, kumpulkan feedback mentor, catat gap, regresi, dan backlog MVP | Demo simulasi end-to-end dan keputusan apakah layak masuk MVP |

### Urutan setiap batch

```text
Baca rencana dan dataset
→ tulis acceptance criteria
→ implementasikan perubahan kecil
→ tambahkan test/fixture
→ jalankan pipeline dan inspeksi output
→ review kewajaran dengan mentor
→ catat gap/keputusan
→ baru lanjut ke batch berikutnya
```

### Kriteria keluar dari Simulation Build

Simulation Build selesai jika pipeline dapat dijalankan ulang dari `data/dataset_ready.csv` sampai decision brief untuk satu Case Bontang → ECI, seluruh transformasi terlihat, formula dan Gate memiliki test, hasil tidak mengklaim approval produksi, serta mentor menyetujui bahwa alurnya cukup representatif untuk mulai merancang MVP.

## Tahapan kerja

### Fase 0 — Kesepakatan pilot dan kontrak data

- Pilih satu Case pilot bersama mentor.
- Tetapkan field minimum, unit, basis, sumber, owner, dan freshness.
- Konfirmasi definisi Indeks, Alpha, Freight, `A`, margin, dan status Gate.
- Bekukan contoh angka yang akan menjadi acceptance test.

### Fase 1 — Data dan pre-process

- Baca `data/dataset_ready.csv` sebagai Case eksperimen Bontang → ECI; perlakukan file sumber sebagai read-only. Jangan menafsirkan perubahan ini sebagai perubahan rute produksi atau system-of-record PILOG.
- Catat bahwa transformasi yang diketahui adalah perubahan rute dari basis Aqaba menjadi Bontang → ECI; jangan menganggap field lain otomatis cocok dengan rute baru.
- Catat asal dataset, tanggal perubahan rute, transformasi lain bila ada, dan checksum/versi bila tersedia.
- Jalankan validasi domain bersama mentor untuk jarak, port, waktu, kapal, biaya, dan basis harga setelah perubahan rute.
- Bentuk model kanonis dan snapshot Case berversi.
- Normalisasi satuan, mata uang, nama pelabuhan/kapal, dan arah rute.
- Tampilkan error sebagai status yang dapat ditindaklanjuti; jangan mengganti data kosong menjadi nol.

### Fase 2 — Kalkulasi dan skenario

- Implementasikan formula dalam modul murni yang tidak bergantung pada UI.
- Pisahkan freight cost, freight selling rate, contribution/margin, dan total transaction value.
- Tambahkan sensitivitas terbatas untuk Indeks, Alpha, Freight, bunker, FX, dan waktu pelabuhan.

### Fase 3 — Gate dan decision brief

- Gate 1 memeriksa apakah CFR berada dalam lingkup kontrak, komersial, operasional, dan PILOG.
- Gate 2 memeriksa kelayakan kapal, ekonomi, daya saing pelanggan, kas, risiko, clause, kualitas data, dan wewenang.
- Hasil dapat berupa CFR Disetujui, CFR Bersyarat, FOB Direkomendasikan, atau Tunda/No-Bid—semuanya tetap menunggu keputusan manusia.

### Fase 4 — Uji, review, dan handover

- Jalankan satu Case pilot serta tiga Case historis/dummy.
- Cocokkan hasil dengan workbook dan validasi mentor.
- Dokumentasikan gap, keputusan, keterbatasan, dan rekomendasi Iterasi 2.
- Handover dilakukan melalui README, test evidence, decision brief contoh, dan cara menjalankan.

## Prioritas implementasi

1. Data contract dan model Case.
2. Importer dan quality checks.
3. Formula dan unit test.
4. Skenario serta Gate.
5. UI tipis dan decision brief.
6. Pengujian mentor dan dokumentasi.

Jika waktu atau data terbatas, kurangi jumlah skenario dan pertahankan impor manual. Jangan menambah integrasi atau automasi keputusan yang belum tervalidasi.

## Definition of done

MVP selesai apabila satu pengguna dapat memasukkan satu Case, melihat status kualitas datanya, mereproduksi kalkulasi FOB/CFR, membandingkan skenario terbatas, menghasilkan decision brief Gate 1/2, dan mencatat keputusan/override manusia tanpa mengubah snapshot awal.
