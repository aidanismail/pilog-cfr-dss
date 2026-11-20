# PILOG Freight Desk

Kalkulator freight dry bulk dan commercial brief PI/PILOG. UI putih–biru tetap memakai Streamlit; perhitungan Python deterministik memakai Decimal.

## Menjalankan aplikasi

Dari folder repository di PowerShell:

    .\venv\Scripts\python.exe -m streamlit run apps/streamlit_app.py

Buka alamat localhost yang ditampilkan. Pilih komoditas dan pelabuhan, edit tabel input, lalu klik **Hitung freight**. Perubahan port memperbarui jarak otomatis. Jika lookup gagal, isi jarak manual; jarak tidak mengambil OD.

Untuk instalasi baru, gunakan Python 3.12 dan:

    python -m pip install -r requirements.txt

Untuk preview fitur risiko di Streamlit Community Cloud, buat app baru dari branch `feature/freight-risk-mitigation` dengan entry point `apps/streamlit_app.py` dan Python 3.12. App utama tetap memakai `dev`. Versi Streamlit dipasang dari `requirements.txt`.

Untuk mencoba, buka paket [PILOG, hire belum dikunci](outputs/test_cases/fd3_risk_pilog_open_hire.json) atau [PI, freight belum dikunci](outputs/test_cases/fd3_risk_pi_open_freight.json) dari sidebar. Setelah **Hitung freight**, lihat rekomendasi dan opsi mitigasi di **Commercial brief**. Untuk kasus baru, isi **Status transaksi** dan pilih uji perubahan yang relevan. Dokumen demo memakai rujukan komitmen sintetis.

## Alur dan perhitungan

1. Input pengiriman, biaya, terms dan profil dua kelas.
2. Data input dan sumber → tiga skenario muatan → pemeriksaan berat, volume, dan draft.
3. Waktu port/laut → hire, bunker, Port DA terpisah dan biaya lain.
4. Perbandingan kelas → rekomendasi dan commercial brief lima bagian.
5. Spread matrix alternatif rute, Flat/Delta terhadap kasus dasar.

Komoditas aktif: urea granular, ammonium sulphate/ZA dan ammonium chloride. Semuanya dry bulk; ammonia cair/gas tidak termasuk.

Freight biaya = (hire + bunker + Port DA muat + Port DA bongkar + other costs) / cargo.
Hire = Hire/day × hari sewa. Kasus baru memiliki hire/day terpisah untuk Handysize dan Supramax. Nilai awal dapat berasal dari KOBC yang sesuai; pengguna dapat memasukkan quotation manual. Komisi kalkulator 0%; standar indeks KOBC menyebut 5% total, jadi basisnya perlu diperhatikan. TC Rates Fearnpulse adalah benchmark terpisah dan bukan KOBC spot.

KOBC diambil otomatis saat halaman dimuat ulang. Jika sumber gagal, aplikasi dapat memakai observasi terakhir di server selama umurnya 0–7 hari kalender menurut tanggal Seoul. Pencocokan rute terbatas pada Supramax MS5 untuk Bontang–Haldia/Tuticorin, MS6 untuk Bontang–Ningbo, dan Handysize MH3 untuk Bontang–Qingdao. Untuk rute lain, aplikasi memakai TC Average masing-masing kelas. Jika belum pernah ada data kelas tersebut, nilai awal USD 13.000/hari ditandai sebagai asumsi. Benchmark kedaluwarsa perlu diganti dengan input manual.

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

F5 atau **Kasus baru** meminta data Fearnpulse dan KOBC kembali dan memeriksa spesifikasi terhadap halaman Baltic. Perubahan widget bekerja dengan data sesi saat ini. Bila Fearnpulse gagal, data terakhir tetap menampilkan tanggal observasi asli. Bila spesifikasi Baltic berubah atau halaman gagal diverifikasi, kasus menggunakan profil tersimpan dan menampilkan statusnya. F5 memulai sesi baru. Download paket dulu jika ingin menyimpan edit, lalu buka paket tersebut untuk menghitung ulang dengan data yang tersimpan.

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
    .\venv\Scripts\python.exe scripts/run_market_simulation.py --package outputs/contoh_6_kasus/01_urea_bontang_mundra_terms.json

Output CLI: outputs/latest_freight/ berisi case.json, result.json, ledger.csv dan commercial_brief.md. Replay paket memakai snapshot sendiri tanpa fetch baru.

UI menyediakan unduhan paket kasus, brief, hasil rinci dan matrix. Paket PILOG-FREIGHT.1 menyimpan input/sumber/override/hash; impor menghitung ulang hasil. Paket tidak menjadi daftar kasus permanen di server.

Pengujian:

    $env:PYTHONPATH = "src"
    .\venv\Scripts\python.exe -m unittest discover -s tests -t . -q

Untuk smoke test browser lokal, pasang `requirements-ui-test.txt` dan jalankan `python tests/ui/browser_smoke.py` di lingkungan yang sama. Runner memakai Microsoft Edge headless dan menutup server uji secara otomatis.

Rencana, evidence dan batas implementasi: docs/it_5/RENCANA_PENYESUAIAN_INPUT_VOYAGE.md. Task/state pada .agents/. Tidak ada auto-award, booking, hedge, transaksi atau klaim kepastian tersedia kapal.

THEX3: Kamis 12:00 sampai Sabtu 08:00 dikecualikan; faktor estimasi 1,35 sesuai konfirmasi pengguna. Catalog CMN-TERMS.2 mendukung replay CMN-TERMS.1; opsi baru hanya memperbarui catalog saat dipilih.
