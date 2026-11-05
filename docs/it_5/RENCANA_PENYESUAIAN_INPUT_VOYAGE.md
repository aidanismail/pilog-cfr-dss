# Iterasi 5 — rencana dan status penguatan logika pipeline

Diperbarui 4 November 2026. Pengguna mengizinkan implementasi perbaikan review produk. Prioritas bersama mentor: sempurnakan logika pipeline dahulu; kualitas dan kelengkapan data aktual ditingkatkan kemudian. Dokumen ini menjadi acuan aktif dan menggantikan rencana historis yang bertentangan. Aplikasi tetap Streamlit.

### Tindak lanjut review produk

- Peralihan profil mempertahankan TC Rates serta harga bunker yang diedit manual. TC Rates yang belum diedit mengikuti benchmark kelas baru; spesifikasi kapal manual tetap diganti oleh profil baru dengan pemberitahuan.
- Acuan TC Rates dan ukuran serinya ditampilkan; perubahan speed manual ditandai karena konsumsi tidak berubah otomatis.
- Tabel harga menyatakan basis CFR dan kecocokan negara/kawasan. Freight disebut konteks voyage; baris menampilkan kawasan, asal, tujuan, tonase, jenis komoditas, tanggal dan selisih aritmetika hanya ketika kedua kawasan dipetakan cocok. Peringkat global berdasarkan tonase, bukan validasi komersial.
- Kesalahan pembacaan Argus dan Fertecon dinyatakan per penerbit, terpisah dari kondisi seri wilayah tidak tersedia.
- Sensitivitas menyertakan besaran kenaikan bunker, tambahan hari, hasil dan status; freight tetap. Surplus baseline tetap memakai freight indikasi dan bukan bukti penerimaan buyer.
- Verifikasi lokal: suite lengkap 255 tes lulus; setelah penyesuaian label dan status terakhir, 33 tes integrasi dan UI terkait lulus. UAT mentor, kalibrasi data aktual dan validasi deployment belum dilakukan; angka rating bukan jaminan hasil.

## Keputusan bisnis yang berlaku

- Urea granular bulk, kapal milik, satu arah laden. Tender dan commercial decision brief tetap disembunyikan pada UI aktif; engine historis tetap dapat diuji.
- Seluruh biaya satu voyage dibebankan ke cargo kasus; tidak ada alokasi part cargo atau asumsi pendapatan cargo lain. Muatan kecil tetap dapat dihitung tanpa minimum buatan.
- Komisi 0%. PI menjual barang, PILOG menjual freight; tidak ada kompensasi otomatis dari PI atas kerugian PILOG.
- Nama input tetap **TC Rates**. Default berasal dari benchmark Fearnpulse sesuai keluarga kapal. TCE hasil tetap ditampilkan; tidak ada angka target TCE duplikat pada hasil.
- Freight indikasi dihitung untuk memenuhi TC Rates. Surplus pada freight indikasi tidak membuktikan harga tersebut diterima buyer. Tidak menambahkan input freight penawaran manual.
- Allowance bunker dan constants dataset digunakan untuk pemeriksaan kapasitas. Lolos pemeriksaan ini belum membuktikan draft, volume ruang muat, terminal, jadwal atau kapal tersedia.
- Pilihan kelas tetap Handysize/Supramax; profil angka adalah acuan, bukan klaim ukuran universal atau kapal aktual.
- Jarak aktif melalui Searoute atau input manual; tidak memakai OD sebagai default/fallback. Jalur historis tetap memakai kontraknya sendiri.
- Pembanding CFR barang dan freight voyage terpisah, bersifat informasi, dan tidak otomatis menghasilkan quote atau GO/NO GO.
- Ekspor/impor paket kasus lebih dahulu; daftar kasus permanen, database dan RBAC menyusul bila requirement ditetapkan.

## Alur aktif

Pilih rute dan kelas/profil kapal → resolve jarak → edit tabel input → validasi angka, unit, kelas dan kapasitas setelah allowance → hitung hari, bunker, biaya dan freight indikasi → tampilkan TCE, impas dan surplus → sensitivitas dengan freight baseline tetap → pembanding pasar → unduh paket kasus untuk melanjutkan input yang sama.

Perubahan input menghapus hasil yang tidak lagi sesuai. Edit diterapkan secara atomik: jika validasi gagal, basis kasus sebelumnya tidak setengah berubah. Perubahan profil dapat mengganti spesifikasi manual; UI memberitahukan perilaku ini.

## Batch L1 — sumber input dan kontrak kasus

- [x] Jalur startup aktif membaca Voyage Estimate tanpa membuka, meng-hash atau memvalidasi terhadap OD; pembaca historis tetap tersedia.
- [x] Semua input utama dalam tabel editable; tanpa tombol terapkan atau gunakan pasar terbaru.
- [x] TC Rates, harga bunker, satuan, sumber dan tanggal tampil; waktu fetch dibedakan dari tanggal observasi sumber.
- [x] Perubahan rute menjelaskan bahwa handling/waiting/port cost tetap input kasus, bukan otomatis tarif pelabuhan tujuan.
- [x] Mempertahankan presisi string sumber jika widget numerik tidak berubah, meskipun representasi float tampilan lebih pendek.
- [x] Angka invalid, rentang indeks invalid, perubahan komisi aktif dan edit tidak dikenal gagal sebelum perubahan kasus dikomit.
- [x] Fallback geocoding/routing hanya jarak manual, bukan OD atau jarak rute sebelumnya.

## Batch L2 — kapasitas dan konsistensi profil

- [x] Tolak cargo di atas gross DWT.
- [x] Tolak cargo di atas DWT dikurangi allowance bunker dan constants, memakai nilai dataset yang editable.
- [x] Tolak DWT manual yang keluar dari rentang kebijakan kelas terpilih.
- [x] Pemeriksaan kapasitas berada pada jalur kalkulasi bersama, sehingga prepare dan evaluasi tidak memiliki celah aturan berbeda.
- [x] Tampilkan kapasitas tersisa dan cargo/gross-DWT sebagai informasi; bukan persentase utilisation DWCC yang sudah tervalidasi.
- [ ] Validasi kapal nyata, stowage factor, grain capacity, draft dan terminal: fase data/operasional kemudian; jangan membuat default palsu.

## Batch L3 — penjelasan harga dan sensitivitas

- [x] Pertahankan TC Rates sebagai input dan TCE hasil sebagai output tanpa metrik target duplikat.
- [x] Tampilkan freight indikasi, freight impas dan estimasi surplus/defisit voyage PILOG.
- [x] Perjelas bahwa surplus merupakan hasil pada freight indikasi, belum bukti penerimaan pasar atau laba bersih perusahaan.
- [x] Rincian biaya per MT menunjukkan pengaruh pembebanan seluruh biaya ke cargo kasus, termasuk kasus muatan sangat kecil.
- [x] Skenario biaya dari parameter kasus menggunakan freight baseline tetap. Delay atau kenaikan bunker tidak memicu repricing yang menyembunyikan risiko.
- [x] Tampilkan biaya, TCE, surplus/defisit dan perubahan surplus per skenario.
- [x] Matematika uang memakai Decimal di calculations; UI dan source parser tidak menghitung rumus harga sendiri.
- [ ] Demurrage/despatch, cash flow, charter hire dan biaya kapital: perlu scope/definisi bisnis tersendiri, bukan dipaksakan ke model kapal milik saat ini.

## Batch L4 — assessment pembanding dan sumber pasar

Pembaruan 4 November: parser Argus membaca assessment granular CFR tambahan berdasarkan nama wilayah/negara/port yang eksplisit; FOB North Africa ditampilkan sebagai konteks FOB, bukan CFR. Untuk tujuan Afrika Utara tanpa rute asal yang cocok, contoh freight Fertecon ke Morocco boleh ditampilkan dengan label **asal berbeda**, tanpa gap harga seolah rute sama. Audit katalog saat ini menemukan CFR untuk 19 dari 50 port; sisanya belum terbukti tersedia sebagai CFR pada sumber dan mapping yang dibaca. Angka laporan tetap sesuai tanggal edisi, bukan live.

Pembaruan berikutnya: sesuai arahan pengguna, bila tidak tersedia assessment tujuan atau regional, tampilkan konteks FOB Asia Tenggara sebagai pasar global dengan label wilayah dan basis asli. Freight ditampilkan berjenjang: dua kawasan cocok, tujuan cocok, asal cocok, lalu contoh rute global berdasarkan kedekatan tonase; kelas terakhir tidak diklaim sebagai rute terdekat atau quote kasus. Selisih numerik hanya ditampilkan bila kedua kawasan cocok. Seluruh pasangan 50 port mendapatkan konteks ketika kedua laporan berhasil dibaca; konteks global bukan bukti harga tujuan atau kesebandingan komersial.

- [x] Fertecon sebagai prioritas awal untuk CFR granular dan tabel freight pupuk dry bulk.
- [x] Memilih edisi PDF berdasarkan tanggal laporan; tidak lagi gagal hanya karena ada lebih dari satu tanggal edisi.
- [x] Dua dokumen berbeda bertanggal sama tidak dipilih sembarangan. Hash file mengikat hasil parsing dan cache.
- [x] Validasi assessment finite, positif, low <= high, berikut produk/basis, seri, halaman, unit, tanggal dan hash sumber.
- [x] Pembanding voyage menyebut asal, tujuan dan tonase asli; tidak menyesuaikan tarif secara linear menjadi quote rute lain.
- [x] Rute tanpa pasangan yang cukup cocok ditampilkan tidak tersedia. Assessment tidak menjadi gate otomatis.
- [x] Snapshot Fearnpulse yang berhasil diambil disimpan atomik di cache runtime, terpisah dari seed; file cache rusak tidak mematikan seluruh fallback.
- [x] Cache runtime menggunakan satu snapshot terakhir agar tidak terus menambah file setiap refresh.
- [ ] Inventarisasi/penyetaraan seluruh seri Argus dan perluasan mapping pasar adalah pengayaan sumber berikutnya; tidak menjadi penghalang pengujian logika. Tidak mengklaim seluruh 50 port punya assessment.
- [ ] Pembaruan data aktual, lisensi/API provider, freshness policy dan kalibrasi TC benchmark memerlukan validasi pemilik data. Belum ada ambang stale atau faktor koreksi buatan.

## Batch L5 — paket kasus dan penyimpanan

- [x] Sidebar menggunakan unduh dan buka paket kasus JSON, menggantikan daftar draft server bersama.
- [x] Paket memuat context dan input, bukan klaim approval atau hasil terkini. Hasil dihitung ulang setelah impor.
- [x] Versi paket, ukuran maksimal 5 MiB, duplicate JSON keys, schema/unit dan nilai input diperiksa.
- [x] Nama dataset pada paket tidak boleh menentukan lokasi filesystem; importer memakai nama internal pada temporary directory.
- [x] Tidak ada daftar file draft sesi lain yang ditampilkan di UI.
- [x] Ruang kerja pengujian terpisah sehingga tes tidak mengotori daftar draft pengguna.
- [ ] Persistence server, SSO/RBAC, konflik edit, retention dan backup produksi menunggu scope operasional; ekspor kasus merupakan cara melanjutkan input antar-refresh saat ini.

## Batch L6 — verifikasi dan penerimaan

- [x] Uji startup aktif tanpa pembacaan OD.
- [x] Uji kapasitas setelah allowance dan DWT di luar kelas.
- [x] Uji rollback edit invalid.
- [x] Uji sensitivitas: freight tetap, tambahan biaya/waktu menurunkan surplus dan TCE.
- [x] Uji paket kasus: ekspor/impor menghasilkan baseline dan skenario yang sama.
- [x] Uji cache korup serta fallback snapshot.
- [x] Tes UI historis yang mengharapkan empat profil/tender aktif diganti kontrak UI I5; regresi engine tender historis tetap diuji.
- [x] Verifikasi final 4 November: seluruh suite aktif 249/249 tes lulus (24,705 detik), termasuk unit, integration dan Streamlit AppTest. Perintah: Python venv dengan src pada sys.path, unittest discover tests; output tes diarahkan ke temporary directory. git diff --check lulus. Server browser tidak dijalankan.
- [ ] UAT mentor: pilih rute/kapal, edit input, hitung, periksa sensitivitas/pembanding, unduh paket, refresh, impor dan hitung ulang.
- [ ] Visual QA browser pada desktop/layar sempit dan verifikasi cloud setelah pengguna mengotorisasi update deployment.

## Modul untuk audit

- application/market_case.py: menyusun default voyage/profil/market; jalur aktif bebas OD.
- application/interactive_case.py: state kasus, edit atomik, invalidasi hasil dan fixed quote.
- application/case_package.py: paket kasus portable.
- calculations/voyage_economics.py: hari, bunker, port/other, running cost.
- calculations/freight_pricing.py: indikasi freight, TCE, surplus, impas, diagnostik harga.
- calculations/capacity.py: pemeriksaan DWT dan headroom.
- orchestration/case_evaluation.py: jalur hitung bersama dan sensitivitas freight tetap.
- sources/market_comparables.py: ekstraksi assessment dan pemetaan terbatas.
- sources/fearnpulse.py: fetch, normalisasi dan cache/fallback.
- ui/views.py dan ui/presentation.py: input/output dan label sumber; tidak menetapkan keputusan komersial.

## Batas penerimaan

Penguatan logika tidak berarti seluruh angka sudah merupakan data operasional. Dataset yang tersedia diterima sebagai basis eksperimen; unit, keterkaitan input, kapasitas dan rumus tetap diperiksa. Tidak menambah gate kualitas data yang menghentikan simulasi hanya karena sumber historis.

Pengguna dan mentor tetap menilai apakah perilaku pipeline sudah tepat. Rating agent bukan approval bisnis. Tidak ada perubahan deployment atau push Git dari pekerjaan lokal ini.
