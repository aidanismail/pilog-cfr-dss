# PILOG CFR DSS — Simulasi Iterasi 2

Prototipe **decision support system (DSS)** untuk menilai peluang ekspor pra-penawaran: harga FOB sebagai baseline, ekonomi jasa freight PILOG pada opsi CFR, dan screen awal kelas kapal. Output berupa kandidat tindakan beserta alasan, **bukan** persetujuan transaksi atau quotation. Entitas PI Group menjual komoditas; PILOG menyediakan jasa freight.

## Status dan batas

- Fase: simulasi revisi Iterasi 2. Review/penerimaan mentor masih menunggu.
- Basis kargo kasus contoh: **45.000 MT** untuk hari pelabuhan, screen DWT, freight revenue, komisi, dan biaya per MT. Angka alokasi 46.000 MT dari data lama tidak digunakan.
- Alternatif komersial: FOB dan CFR. Handysize/Supramax adalah pilihan kelas kapal **di dalam** CFR. Kapal diasumsikan milik/dioperasikan PILOG; charter belum dimodelkan.
- Kontribusi freight positif hanya alasan untuk **review manusia**. Profit komoditas FOB PI Group, minimum margin bisnis, kapasitas kapal nyata, dan penerimaan buyer belum dibuktikan.
- Tidak ada integrasi produksi, penawaran otomatis, fixture, maupun approval otomatis.

## Jalankan secara lokal

Gunakan Python 3.11+. Engine dan tes hanya memakai pustaka standar Python. `openpyxl` dalam `requirements.txt` diperlukan hanya bila ingin membuat ulang workbook belajar.

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/run_iteration_02.py
```

Run default membaca `data/dataset_ready.csv`, `data/reference/variable_catalog.csv`, `data/reference/vessel_classes.json`, dan `data/raw/iteration_02_pre_offer_simulation.json`. Untuk kasus baru, salin input CSV dan JSON, lalu berikan `--dataset path\ke\kasus.csv --manual path\ke\kasus.json`. Lihat `python scripts/run_iteration_02.py --help` untuk opsi lain. Jangan mengubah nomor/nama kolom CSV tanpa memperbarui kontrak katalog.

Hasil baru tersimpan di `outputs/runs/<run_id>/`. Baca `decision_brief.md` terlebih dahulu; JSON di folder yang sama menyimpan trace, gate, ekonomi, dan snapshot input. Repo hanya menyimpan **satu contoh run terbaru**. Run lokal berikutnya diabaikan Git agar repo tidak dipenuhi artefak percobaan.

## Peta repo

| Lokasi | Peran |
|---|---|
| `src/pilog_cfr_dss/` | Ingestion, validasi, kalkulasi `Decimal`, skenario, gate, dan pelaporan. |
| `tests/` | Tes unit serta integrasi deterministik. |
| `data/dataset_ready.csv`, `data/raw/`, `data/reference/` | Data kasus, konteks manual, katalog, dan kebijakan kelas kapal simulasi. |
| `.agents/` | Status, rencana, kontrak ekonomi, keputusan, dan review iterasi. Mulai dari `.agents/00_READ_CURRENT.md`. |
| `docs/it_1/` | Catatan historis Iterasi 1. |
| `outputs/learning/iteration_02_variable_map.xlsx` | Peta variabel untuk belajar, bukan mesin perhitungan. |

## Sebelum mengunggah ke GitHub

CSV contoh berasal dari data voyage Aqaba yang kemudian diubah rutenya menjadi Bontang–ECI untuk eksperimen; snapshot pada contoh run dan workbook belajar juga menyalin sebagian nilainya. **Periksa izin berbagi dari mentor/perusahaan dan visibilitas repo** sebelum men-stage dataset, workbook, atau run tersebut. Mengganti nama rute saja tidak menjadikan data otomatis anonim atau siap publikasi.

Alur review dan pertanyaan bisnis yang masih terbuka ada di `.agents/reviews/ITERATION_02.md`. Jangan menganggap hasil tes hijau sebagai persetujuan mentor atau izin melanjutkan ke MVP.
