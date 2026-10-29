# Handover singkat — PILOG CFR DSS

**Konteks per 9 Oktober 2026.** Dokumen ini sengaja mandiri agar dapat diunggah ke ChatGPT tanpa riwayat percakapan Codex. Ini ringkasan proyek, **bukan** spesifikasi bisnis yang sudah disahkan, data transaksi, atau izin menjalankan keputusan komersial.

## Apa yang sedang dibangun?

Saya adalah intern IT di Business Development PT Pupuk Indonesia Logistik (PILOG). Kami sedang membangun **simulasi Decision Support System (DSS) untuk ekspor dengan skema CFR**. PI Group menjual komoditas; PILOG menyediakan jasa freight/pengangkutan. Tujuannya membantu PILOG menilai apakah kandidat transaksi CFR setelah tender layak **GO** untuk review manusia atau **NO GO**, beserta alasan, angka yang bisa ditelusuri, risiko, dan tindakan lanjut. Hasil sistem **advisory-only**; ia tidak memilih pemenang tender atau menyetujui transaksi.

Ada target bisnis yang dibahas untuk meningkatkan porsi CFR ekspor pada 2027 (sekitar 40%, dengan 60% FOB). **Target ini bukan rule yang memaksa sistem menghasilkan GO.** FOB sudah memiliki proses bisnis PI sendiri; fokus aktif sistem ini adalah kelayakan pelaksanaan **CFR oleh PILOG**.

## Alur bisnis dan batas sistem saat ini

```text
PI memiliki lot barang dan melakukan push demand
→ PI menetapkan OE/HPS dan mengundang buyer ke tender
→ buyer menyampaikan bid/alpha; PI menjalankan putaran dan memilih kandidat
→ DSS membaca snapshot kandidat pasca-tender
→ Gate A (harga dan kandidat) → Gate B (kapal dan ekonomi freight PILOG)
→ GO/NO GO + alasan → review/keputusan pejabat berwenang
```

**PI**, bukan DSS, mengelola tender dan menentukan kandidat. Tim harga PI menyediakan **OE/HPS** sebagai input fixed; DSS tidak menghitungnya dan tidak menyamakannya dengan HPP/COGS. **Buyer** adalah sumber nilai ekonomi alpha. **PILOG** menyediakan input freight dan menilai kemampuan/ekonomi pengangkutan. Sistem membantu menjelaskan keputusan, tetapi tidak mengirim penawaran, memesan kapal, menandatangani kontrak, atau melakukan approval otomatis.

## Logika yang disimulasikan

Semua harga/rate berikut menggunakan USD/MT; `Q` adalah tonase kargo. Satu kasus eksperimen menggunakan urea granular bulk, rute Bontang–ECI, `Q = 45.000 MT`. Banyak input fisik/biaya diwarisi dari data eksperimen Aqaba yang rutenya diubah; rute dan biaya turunannya **belum divalidasi untuk voyage operasional nyata**.

```text
Index          = rata-rata midpoint dua benchmark FOB SEA urea granular
FOB_bid        = Index + alpha_buyer                  # alpha tepat sekali
gap_OE         = FOB_bid - OE/HPS
eligible       = gap_OE >= 0                         # nol diterima
OD_cost_per_MT = total estimasi biaya voyage / Q     # proxy simulasi
CFR_bid        = FOB_bid + OD_cost_per_MT
revenue_PILOG  = tarif jual freight PILOG × Q
kontribusi_PILOG = revenue_PILOG - komisi relevan - biaya voyage
```

**Jangan campur objek ekonomi:** OE/HPS bukan biaya produksi yang dihitung DSS; `gap_OE` bukan laba akuntansi PI. Biaya OD yang ditambahkan ke harga CFR buyer **bukan otomatis pendapatan PILOG**. Tarif jual jasa PILOG harus dinyatakan terpisah. Saat ini OD berasal dari **proxy biaya voyage**, bukan keluaran OD matrix resmi. Indeks pada fixture berasal dari **angka sintetis berlabel**, bukan kutipan pasar aktual.

- **Gate A:** kandidat bid dipilih PI, bid tersebut ada dan `FOB_bid ≥ OE/HPS`. Jika tidak, `NO GO` dengan alasan tender/data; Gate B tidak dipakai untuk meloloskan bid tersebut.
- **Gate B:** setelah Gate A lolos, cek screen awal kelas/kapasitas DWT kapal milik dan kontribusi freight PILOG `≥ 0`. Jika lolos, `GO` **untuk review manusia**, bukan persetujuan final.
- Input penting yang rusak/tidak cukup menghasilkan `NO GO / DATA_ISSUE`: artinya **belum aman untuk GO**, bukan otomatis buyer ditolak secara komersial.

Perhitungan numerik dilakukan fungsi Python deterministik (`Decimal`), **bukan oleh LLM**. Otomasi berada pada pembacaan input, validasi, perhitungan, Gate, dan pembuatan jejak keputusan. Komponen DSS adalah penerapan rule untuk memberi rekomendasi dan tindakan lanjut; otoritas akhir tetap manusia.

## Status implementasi, 9 Oktober 2026

- **Masih fase simulasi Iterasi 3; belum MVP dan belum diterima mentor.** Iterasi 1 membuktikan pipeline sederhana; Iterasi 2 menambah ekonomi voyage dan opsi kapal pra-penawaran; Iterasi 3 mengubah scope aktif menjadi **DSS CFR pasca-tender**. Jalur I2 dipertahankan untuk regresi, bukan dipakai sebagai Gate I3.
- Satu CSV kasus voyage dan dua JSON tender **sintetis** menghasilkan contoh `GO` dan `NO GO`. Data pasar, OE/HPS, bid, pilihan PI, dan beberapa asumsi lain diberi label simulasi. Mesin menyimpan `decision_brief.md`, trace JSON, dan snapshot input per run.
- Verifikasi lokal pada 9 Oktober 2026: **38/38 tes lulus**. Ini hanya bukti teknis terhadap fixture/aturan saat ini; bukan validasi transaksi, harga pasar, atau persetujuan mentor.
- Belum ada integrasi Fleetra, SAP, sumber tender, parser laporan pasar, OD matrix resmi, UI operasional, chartering, write-back, ataupun approval otomatis.

## Hal yang harus dikonfirmasi mentor sebelum logika dianggap matang

1. Apakah rumus tender aktual memang `FOB = Index + alpha_buyer`, dan apakah buyer memasukkan alpha atau harga total?
2. Seri, tanggal, dan basis indeks pasar mana yang disetujui PI? Apakah rata-rata dua penerbit ini hanya eksperimen atau aturan nyata?
3. Apakah proxy biaya voyage setara dengan OD matrix resmi; komponen biaya/komisi apa yang sudah termasuk agar tidak dihitung dua kali?
4. Berapa tarif jual freight PILOG ke PI dalam skema CFR ini, dan apa dasar kontraknya?
5. Apakah screen DWT cukup untuk tahap awal; siapa memvalidasi DWCC, draft, terminal, laycan, dan availability kapal?
6. Apakah redaksi `GO/NO GO`, terutama `DATA_ISSUE`, cukup jelas bagi pengambil keputusan?

Sesudah review mentor, kami akan memperbaiki logika melalui Iterasi 4...N, menjalankan **final simulation validation**, dan baru mempertimbangkan desain MVP jika logika diterima. Jangan melompati urutan ini hanya karena dua contoh menghasilkan output.

## Jika ChatGPT membantu pekerjaan lanjutan

Gunakan dokumen ini sebagai **konteks kerja awal**, bukan bukti bahwa semua aturan sudah disetujui. Jawab dalam bahasa Indonesia yang jelas untuk intern berlatar computer science. Bedakan fakta yang telah diputuskan mentor, asumsi simulasi, pertanyaan terbuka, dan saran baru. Kritik desain dengan alasan konkret; jangan mengarang angka harga pasar, biaya, atau keputusan mentor. Jika diminta memeriksa kode/hasil terbaru, minta file terkait diunggah—dokumen ini **tidak** memberi ChatGPT akses otomatis ke repo lokal, diagram, laporan pasar, atau percakapan Codex.

**Rujukan lokal bila nanti tersedia:** `.agents/00_READ_CURRENT.md`, `docs/it_3/ITERATION_03_TENDER_DSS_PLAN.md`, `.agents/reviews/ITERATION_03.md`, `data/processed/`, `scripts/run_iteration_03.py`, dan `outputs/runs/`. Periksa izin perusahaan sebelum mengunggah dataset, laporan pasar berlisensi, atau snapshot transaksi ke layanan eksternal.
