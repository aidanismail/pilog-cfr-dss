# Runbook singkat — Simulasi Iteration 2

## Urutan dan batas kerja

1. Baca `.agents/00_READ_CURRENT.md`, `.agents/tasks/ITERATION_02_PROPOSED.md`, kontrak ekonomi kandidat, dan review Iteration 2.
2. Jangan ubah input contoh menjadi seolah data riil. Untuk demo pra-penawaran pakai `data/processed/iteration_02_pre_offer_simulation.json` (default CLI), lalu duplikasi untuk kasus baru. Source/as-of/owner yang belum ada dicatat sebagai batas simulasi, bukan persetujuan.
3. Pakai CSV **61 variabel** dengan skema `No,Variable,Value` dan katalog `data/processed/variable_catalog.csv`. Baris alokasi 46.000 MT lama ditolak eksplisit. Angka/unit teknis yang salah tetap membuat Gate 1 HOLD.
4. Jalankan dari root repo: `.\venv\Scripts\python.exe -m unittest discover -s tests -p test_*.py -v`, lalu `.\venv\Scripts\python.exe scripts/run_iteration_02.py`. CLI juga menerima `--manual`, `--dataset`, `--catalog`, dan `--output-root` (lihat `--help`). Tidak ada bypass Gate; fixture pra-penawaran memang memenuhi syarat simulasi.
5. Baca `decision_brief.md` di folder run yang baru. Buka JSON trace bila angka atau reason code perlu diuji. Setiap run disimpan terpisah dan berisi SHA-256 input. Git hanya menyertakan satu contoh run revisi; run baru berikutnya diabaikan oleh `.gitignore`.
6. Catat kritik mentor di `.agents/reviews/ITERATION_02.md`, ubah keputusan bisnis di `.agents/DECISIONS.md` hanya dengan otoritas/sumber, kemudian bentuk task iterasi berikutnya. Jangan memberi status `mentor_approved` tanpa persetujuan dan referensi nyata.

## Peta modul

`validation/ingest.py` membaca input dan menguji kualitas; `calculations/` menghitung hari, fuel, capacity, biaya dan harga dengan `Decimal`; `scenarios/` membangun alternatif serta ekonomi bersyarat; `decisions/gates.py` menjalankan Gate 1/2; `reporting/` menjelaskan alasan; `orchestration/pipeline.py` menghubungkan semuanya dan menyimpan audit trail.

Workbook `outputs/learning/iteration_02_variable_map.xlsx` hanya bahan pemetaan. Jangan menjadikan rumus Excel, prompt LLM, atau JSON sebagai sumber hitungan otoritatif. Hasil rekomendasi tidak pernah berarti izin komersial otomatis. Perbandingan dengan basis historis 46.000 MT tinggal berupa ringkasan di review/decision log; folder run historis telah dibersihkan atas instruksi pengguna, bukan dua transaksi yang setara.
