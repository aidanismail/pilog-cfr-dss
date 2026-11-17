# PILOG Freight Desk

Kalkulator freight dry bulk dan commercial brief PI/PILOG. UI putih–biru tetap memakai Streamlit; perhitungan Python deterministik memakai Decimal.

## Menjalankan aplikasi

Dari folder repository di PowerShell:

    .\venv\Scripts\python.exe -m streamlit run apps/streamlit_app.py

Buka alamat localhost yang ditampilkan. Pilih komoditas dan pelabuhan, edit tabel input, lalu klik **Hitung freight**. Perubahan port memperbarui jarak otomatis. Jika lookup gagal, isi jarak manual; jarak tidak mengambil OD.

Untuk instalasi baru, gunakan Python 3.11 dan:

    python -m pip install -r requirements.txt -r requirements-ui.txt

## Alur dan perhitungan

1. Input pengiriman, biaya, terms dan profil dua kelas.
2. Data input dan sumber → tiga skenario muatan → pemeriksaan berat, volume, dan draft.
3. Waktu port/laut → hire, bunker, Port DA terpisah dan biaya lain.
4. Perbandingan kelas → rekomendasi dan commercial brief lima bagian.
5. Spread matrix alternatif rute, Flat/Delta terhadap kasus dasar.

Komoditas aktif: urea granular, ammonium sulphate/ZA dan ammonium chloride. Semuanya dry bulk; ammonia cair/gas tidak termasuk.

Freight biaya = (hire + bunker + Port DA muat + Port DA bongkar + other costs) / cargo.
Hire = Hire/day × hari sewa. Komisi 0%. TC Rates Fearnpulse hanya benchmark, tidak ditambahkan lagi sebagai biaya.

Tarif jual freight bersifat opsional. Jika diisi:
- Pendapatan freight = tarif jual × cargo.
- Surplus/defisit = pendapatan freight − voyage expenses − hire.
- TCE = (pendapatan freight − voyage expenses) / total hari.

Tanpa tarif jual independen, hasil memberi batas penawaran penutup biaya dan alternatif operasi; tidak mengarang laba. Pendapatan penjualan barang PI tidak dicampur dengan freight PILOG.

SF default 1,315 m³/MT dan tolerance ±10% editable. Nominal adalah hasil utama; minimum/maksimum dihitung ulang, bukan otomatis dipilih. SF/draft adalah constraint dan tidak harus menaikkan freight bila tidak mengikat.

Terms: 23 opsi dari referensi pengguna, per port. Basis faktor adalah estimasi waktu; kalender operasi memakai jadwal/zona waktu/holiday yang diisi pengguna dan menggantikan faktor. Ini bukan settlement laytime/demurrage/despatch.

Margin waktu pelabuhan dapat diisi terpisah untuk muat dan bongkar, default 25% untuk kasus baru sesuai arahan pengguna. Margin menambah waktu setelah faktor terms atau kalender; waiting dan allowance ditambahkan satu kali. Durasi ini memengaruhi hire dan bahan bakar pelabuhan. Periksa kemungkinan overlap dengan asumsi kalender. Nilai margin adalah input kasus, bukan standar CMN yang terverifikasi atau nilai yang diperoleh otomatis. Paket kasus yang sudah ada mempertahankan margin tersimpan; paket FD.1 dimigrasikan dengan 0% agar hasilnya tetap sama.

Jarak Searoute adalah estimasi satu arah dari jaringan laut terdekat, bukan jarak terminal-ke-terminal yang terverifikasi. Perubahan port memperbarui nilai jarak dan mengosongkan identitas editor jarak lama; jika lookup gagal, masukkan jarak manual. Hasil menampilkan rute dan jarak yang dihitung. Paket lama FD.1 diperiksa hash-nya sebelum dimigrasikan ke FD.2 dengan margin 0%; file asal tidak diubah.

Draft summer, grain capacity dan TPC berasal dari satu set profil Baltic BHSI38/BSI63. Penyesuaian draft memakai pendekatan linear TPC, bukan loading approval. Batas draft port yang kosong ditandai belum dimodelkan.

## Sumber

- Voyage Estimate.xlsx: cargo/handling/waiting default serta tambahan profil kapal. Workbook asli tidak diubah oleh aplikasi.
- Baltic GMB: spesifikasi dua profil acuan. Supramax BSI63 63.500 DWT memakai speed/konsumsi dari baris yang sama.
- Fearnpulse: TC Rates dan harga bunker. Singapore 380 CST/MGO dipakai sebagai harga pembanding untuk input VLSFO/LSMGO; jenis bahan bakar sebenarnya perlu diperiksa.
- Argus/Fertecon Nitrogen PDF di public/: assessment produk, grade, basis, halaman dan tanggal. Parser cache mengikuti hash file. Ini bukan download otomatis edisi berbayar.
- Chloride tersedia pada Argus CFR Southeast Asia; tidak mengarang pasangan Fertecon.
- Ports.xlsx dan catalog koordinat: lookup jarak laut satu arah. Port DA/rate yang diwariskan untuk rute lain tetap asumsi editable.

Data Fearnpulse diambil otomatis dengan cache 60 detik. Jika gagal terhubung, aplikasi memakai data tersimpan dengan tanggal aslinya; input manual tidak ditimpa. Setiap hasil menggunakan data yang tersimpan pada kasus tersebut. Jika input berubah, hitung kembali untuk memperbarui hasil.

## File utama

    apps/streamlit_app.py                  entry UI
    src/pilog_cfr_dss/
      models/freight_desk.py               schema, komoditas, catalog terms
      validation/numbers.py               validasi angka/waktu
      sources/                            pembaca workbook, PDF, pasar dan rute
      calculations/                       kapasitas, waktu, aktivitas dan freight
      application/freight_desk.py          snapshot, workflow, paket dan matrix
      decisions/freight_desk.py            pemilihan opsi dan tindakan
      reporting/commercial_brief.py       brief tanpa rumus tersembunyi
      ui/views.py                         input, hasil dan sumber

Kode tender, putaran, alpha buyer, OE/HPS, winner serta gate tender telah dikeluarkan dari jalur aktif. Riwayat Git dan sumber historis dipertahankan; modul matematika generik tertentu tetap untuk regresi. Paket lama tidak dikonversi otomatis.

## CLI, ekspor dan pengujian

    .\venv\Scripts\python.exe scripts/run_market_simulation.py
    .\venv\Scripts\python.exe scripts/run_market_simulation.py --refresh
    .\venv\Scripts\python.exe scripts/run_market_simulation.py --package outputs/latest_freight/case.json

Output CLI: outputs/latest_freight/ berisi case.json, result.json, ledger.csv dan commercial_brief.md. Replay paket memakai snapshot sendiri tanpa fetch baru.

UI menyediakan unduhan paket kasus, brief, hasil rinci dan matrix. Paket PILOG-FREIGHT.1 menyimpan input/sumber/override/hash; impor menghitung ulang hasil. Paket tidak menjadi daftar kasus permanen di server.

Pengujian:

    $env:PYTHONPATH = "src"
    .\venv\Scripts\python.exe -m unittest discover -s tests -t . -q

Browser smoke memakai Playwright dan browser terpisah, tidak memakai Chrome/login pengguna. Runner lokal yang tersedia: .venv/Scripts/python.exe tests/ui/browser_smoke.py; server aplikasi memakai venv Python 3.11 dan ditutup otomatis.

Rencana, evidence dan batas implementasi: docs/it_5/RENCANA_PENYESUAIAN_INPUT_VOYAGE.md. Task/state pada .agents/. Tidak ada auto-award, booking, hedge, transaksi atau klaim kepastian tersedia kapal.

THEX3: Kamis 12:00 sampai Sabtu 08:00 dikecualikan; faktor estimasi 1,35 sesuai konfirmasi pengguna. Catalog CMN-TERMS.2 mendukung replay CMN-TERMS.1; opsi baru hanya memperbarui catalog saat dipilih.
