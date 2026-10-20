# PILOG CFR DSS — Simulasi Iterasi 3

Prototipe **decision support system (DSS)** untuk menilai kandidat **CFR pasca-tender PI**. PI Group menjual komoditas dan menetapkan OE/HPS; buyer menawar alpha; PILOG menyediakan jasa freight. Output Iterasi 3 **hanya GO atau NO GO** dengan kategori alasan, angka, dan tindakan berikutnya—**bukan** keputusan tender, persetujuan transaksi, atau quotation. Pipeline pra-penawaran Iterasi 2 tetap tersedia sebagai arsip/regresi.

## Status dan batas

- Fase: simulasi Iterasi 3 **sudah berjalan secara teknis; review/penerimaan mentor masih menunggu**. Hasil GO berarti kandidat untuk review manusia, bukan komitmen komersial.
- Basis kargo kasus contoh: **45.000 MT** untuk hari pelabuhan, screen DWT, freight revenue, komisi, dan biaya per MT. Angka alokasi 46.000 MT dari data lama tidak digunakan.
- Kasus I3: **urea granular bulk Bontang → ECI**. Rute/angka voyage berasal dari eksperimen Aqaba-turunan; **bukan** quotation voyage urea yang tervalidasi. Handysize/Supramax disaring berdasarkan DWT awal; kapal diasumsikan milik PILOG.
- Indeks, OE/HPS, alpha, buyer, dan pilihan kandidat pada dua fixture adalah **sintetis berlabel**, karena tidak dapat diturunkan dari CSV voyage. Indeks simulasi = rata-rata midpoint dua penerbit FOB SEA granular; **bukan harga Argus/Fertecon aktual**.
- Biaya OD untuk CFR saat ini **proxy = total biaya voyage / 45.000 MT**, bukan keluaran OD matrix resmi. Tarif jual freight PILOG dari CSV I2 adalah objek terpisah. Formula/basis kontrak PI–PILOG masih perlu verifikasi mentor.
- Jika input tidak sah, aksi tetap `NO_GO` dengan `reason_category = DATA_ISSUE`: artinya **belum aman untuk GO**, bukan buyer gagal harga. Profit akuntansi PI dan kemampuan operasional kapal nyata belum dibuktikan.
- Tidak ada integrasi produksi, penawaran otomatis, fixture, maupun approval otomatis.

## Jalankan secara lokal

Gunakan Python 3.11+. Engine dan tes hanya memakai pustaka standar Python. `openpyxl` dalam `requirements.txt` diperlukan hanya bila ingin membuat ulang workbook belajar.

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/run_iteration_03.py
python scripts/run_iteration_02.py
```

Perintah I3 tanpa opsi menjalankan **dua dataset varian**: `data/processed/i3_go_urea.json` dan `data/processed/i3_no_go_urea.json`, yang sama-sama merujuk CSV aktif `data/processed/i3_urea_v1.csv`. Untuk satu kasus: `python scripts/run_iteration_03.py --case data/processed/i3_go_urea.json`. Lihat `python scripts/run_iteration_03.py --help`. **Jangan mengganti angka sintetis dengan harga pasar nyata tanpa verifikasi sumber dan izin penyimpanan.** Perintah I2 tetap membaca `data/processed/dataset_ready.csv`, katalog I2, kebijakan kapal, dan fixture pra-penawaran lama.

Hasil baru tersimpan di `outputs/runs/<run_id>/`. Baca `decision_brief.md` terlebih dahulu; `decision_brief.json` menyimpan trace, kedua Gate, ekonomi, dan label sumber seluruh input. `input_snapshot/` menyimpan fixture yang dipakai. Run lokal baru diabaikan Git agar repo tidak dipenuhi artefak percobaan; rerun untuk menghasilkan brief terbaru.

## Peta repo

| Lokasi | Peran |
|---|---|
| `src/pilog_cfr_dss/` | Ingestion, validasi, kalkulasi `Decimal`, skenario, gate, dan pelaporan. |
| `tests/` | Tes unit serta integrasi deterministik. |
| `data/raw/` | Workbook hasil ekstraksi Voyage Estimate yang diaudit mentor; bukan input runtime otomatis. |
| `data/processed/` | Input siap-baca: CSV I3, dua fixture tender I3, policy kapal, serta tiga input I2 untuk regresi. |
| `.agents/` | Status, rencana, kontrak ekonomi, keputusan, dan review iterasi. Mulai dari `.agents/00_READ_CURRENT.md`. |
| `docs/it_3/` | Rencana/hasil Iterasi 3 serta flowchart mentor. |
| `docs/it_1/` | Catatan historis Iterasi 1. |
| `outputs/learning/iteration_02_variable_map.xlsx` | Peta variabel untuk belajar, bukan mesin perhitungan. |

## Struktur data setelah penataan 20 Oktober 2026

`data/` hanya memakai dua subfolder. `processed` berarti formatnya siap dibaca kode, **bukan** seluruh angka atau rumus bisnisnya sudah disahkan mentor.

```text
data/
  raw/
    Voyage_Estimate_all_sheets_variable_value_units.xlsx
  processed/
    i3_urea_v1.csv
    i3_go_urea.json
    i3_no_go_urea.json
    vessel_classes.json
    dataset_ready.csv
    variable_catalog.csv
    iteration_02_pre_offer_simulation.json
```

Untuk eksperimen I3, ubah input yang sesuai di `data/processed/`; kedua JSON tetap menunjuk nama CSV yang berada di folder yang sama. Tiga input I2 dipertahankan karena dipakai tes regresi dan lineage I3, bukan data sampah. Tidak ada proses otomatis workbook-ke-CSV dalam penataan ini.

Isi workbook, CSV, dan JSON dipertahankan apa adanya. Teks `source_reference` di CSV I3 masih merekam path historis `data/dataset_ready.csv`; lokasi file tersebut sekarang `data/processed/dataset_ready.csv`. Label sumber historis dan snapshot run lama tidak ditulis ulang sebagai sumber baru. Penataan folder ini tidak menerapkan perubahan komisi, ballast, atau biaya dari audit mentor.

File pengunci Excel `~$...` diabaikan Git. Simpan dan tutup workbook sebelum memindahkannya; jangan menghapus file pengunci yang masih aktif.

## Sebelum mengunggah ke GitHub

CSV contoh berasal dari data voyage Aqaba yang kemudian diubah rutenya menjadi Bontang–ECI untuk eksperimen; snapshot pada contoh run dan workbook belajar juga menyalin sebagian nilainya. **Periksa izin berbagi dari mentor/perusahaan dan visibilitas repo** sebelum men-stage dataset, workbook, atau run tersebut. Mengganti nama rute saja tidak menjadikan data otomatis anonim atau siap publikasi.

Alur review dan pertanyaan bisnis yang masih terbuka ada di `.agents/reviews/ITERATION_03.md`. Jangan menganggap hasil tes hijau atau label GO sebagai persetujuan mentor atau izin melanjutkan ke MVP.
