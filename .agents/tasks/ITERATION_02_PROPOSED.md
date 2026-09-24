# Task aktif — revisi simulasi Iterasi 2

**Status:** `implemented_pending_mentor_review`; R01–R06 selesai dan diverifikasi teknis (26/26 tes, satu contoh run E2E dipertahankan). Sumber kebenaran rencana: `../PLANS_ITERATION_02.md`; bukti dan batas hasil: `../reviews/ITERATION_02.md`. Penerimaan bisnis mentor belum dicatat. Kalimat task di bawah tentang mempertahankan run lama adalah instruksi **saat implementasi**; run pra-revisi kemudian dihapus atas persetujuan cleanup pengguna pada 24 September, sedangkan ringkasan keputusan historis dipertahankan.

## Keputusan yang mengikat task

- Hitung peluang CFR **sebelum** mendekati buyer. `buyer_not_approached` bukan alasan HOLD.
- Hanya dua alternatif komersial: **FOB vs CFR**. `NO_BID`/`DEFER` adalah tindakan akhir. Kelas kapal adalah sub-keputusan CFR, bukan alternatif penjualan terpisah.
- Untuk iterasi ini gunakan kapal milik/dioperasikan PILOG; charter ditunda. Screen kapal memakai DWT saja: Handysize 20–40 ribu, Supramax 50–60 ribu DWT. DWT 58 ribu adalah kapal kasus; 63.500 adalah benchmark, bukan kapal kasus.
- Cargo/DWCC **45.000 MT** dipakai di seluruh hitungan. Baris 46.000 MT pada dataset siap pakai adalah kesalahan data Aqaba, bukan allocation quantity bisnis. Hapus/tolak dari kontrak aktif; riwayat koreksi dicatat di decision log.
- PILOG menanggung biaya voyage relevan; masukkan semua komponen yang berlaku sekali saja. Jangan hitung hire dan running cost sekaligus untuk kapal milik. Tampilkan asumsi komisi dan cakupan biaya agregat.
- Kontribusi freight PILOG adalah ukuran ekonomi yang dapat dihitung sekarang. Minimum margin komersial ditunda. FOB price bukan FOB profit; bila ekonomi FOB tidak diketahui, jangan menyatakan FOB layak/tidak layak secara numerik.
- CSV menjadi contoh angka simulasi. Pemeriksaan sumber/approval dan pengelompokan data domain ditunda, tetapi angka, unit, pembagi, dan trace rumus tetap diperiksa. Semua output `simulation`, `advisory-only`, dan perlu review atasan.

## Urutan kerja

### I2-R01 — koreksi kontrak data dan kuantitas

**Dependensi:** tidak ada. **Target:** dataset siap pakai, mapping kanonik, fixture/snapshot uji.

- Tandai baris `Voyage expense allocation quantity (MT)=46000` sebagai salah menurut mentor; koreksi dataset aktif tanpa menjadikan basis lama input aktif.
- Hilangkan pemakaian `billable_quantity_key` yang dapat memilih 46.000 MT; satu-satunya basis kuantitas adalah `dwcc_cargo_quantity_mt=45000`.
- Pastikan semua artefak baru menunjukkan versi dataset dan satuan; tidak ada angka 46.000 MT masuk revenue, komisi, hari, atau denominator biaya.

**Selesai bila:** perubahan 45.000 MT mengubah hasil yang bergantung padanya; mengubah baris lama 46.000 MT pada salinan input tidak mengubah hasil atau ditolak eksplisit. Tidak ada fallback kuantitas tersembunyi.

### I2-R02 — model dua alternatif dan screen DWT kapal

**Dependensi:** R01. **Target:** kontrak skenario, konfigurasi rentang DWT, pembangun alternatif.

- Hasilkan `FOB` dan `CFR` saja sebagai alternatif komersial. `DEFER`/`NO_BID` disimpan sebagai outcome, bukan kandidat harga.
- Di cabang CFR, screen Handysize dan Supramax memakai DWT kelas dan DWT kasus. Cargo 45.000 MT mengeliminasi Handysize berdasarkan batas atas 40.000 DWT; Supramax kasus 58.000 DWT lolos screen awal.
- Jangan gunakan DWT benchmark 63.500 MT sebagai profil kapal kasus. Jangan membuat klaim kapasitas muat akhir hanya dari DWT; bunker/constants, draft, terminal, dan ketersediaan kapal ditandai belum diuji.
- Simpan rentang kelas sebagai konfigurasi referensi berversi, bukan angka tersembunyi di rumus.

**Selesai bila:** tes boundary kelas lulus dan brief menjelaskan mengapa Handysize tersingkir serta apa yang belum dibuktikan untuk Supramax.

### I2-R03 — Gate 1 pra-penawaran

**Dependensi:** R01. **Target:** aturan Gate 1 dan input manual satu kasus.

- Gate 1 menilai apakah analisis CFR dapat dimulai dari input minimum yang dapat dihitung; buyer belum didekati adalah keadaan normal.
- Penolakan CFR yang sudah diketahui tetap dicatat sebagai alasan tidak menyarankan CFR, bukan mengarang persetujuan buyer.
- Metadata provenance/freshness, sistem sumber, dan approval formal tidak membuat simulasi valid menjadi HOLD. Input angka/unit yang rusak, route/distance yang diperlukan hilang, atau pembagi nol tetap gagal dengan alasan spesifik.

**Selesai bila:** fixture `pre_offer + buyer_not_approached` lolos ke perhitungan; fixture data rusak/penolakan eksplisit menghasilkan outcome aman.

### I2-R04 — ekonomi deterministik dari 45.000 MT

**Dependensi:** R01–R03. **Target:** modul Python `Decimal`, kontrak biaya, trace.

- Hitung hari laut/pelabuhan, bunker, running cost kapal milik, `Other voyage costs total` yang tidak tumpang tindih, freight revenue, ketiga komisi sesuai asumsi simulasi, dan kontribusi freight PILOG.
- Hitung `FOB = Index + Alpha` dan CFR indikatif dengan freight selling rate dataset dan adjustment yang diberi alasan. Pisahkan harga komoditas dari kontribusi jasa freight.
- Jangan menambah hire atau `Daily cost assumption` pada owned running cost. Perlihatkan bila port sudah tercakup agregat USD 200.000; jangan menambah port lagi tanpa pemisahan biaya.
- Jangan membuat minimum margin komersial palsu. Kontribusi positif hanya bukti aritmetika untuk review; nol/negatif adalah peringatan ekonomi.

**Selesai bila:** unit/boundary/missing-input tests lulus, semua angka output dapat ditelusuri ke input dan fungsi, dan tidak ada biaya/kuantitas ganda.

### I2-R05 — Gate 2, tindakan, dan decision brief preskriptif

**Dependensi:** R02–R04. **Target:** aturan pilihan, reason codes, laporan.

- Bandingkan FOB dan CFR sesuai bukti yang tersedia. Pilihan kapal berada di dalam penilaian CFR. Jelaskan pilihan, apa yang tidak diketahui, alternatif yang ditolak, dan tindakan berikutnya.
- Jika kontribusi CFR positif dan screen awal lolos, hasilnya **kandidat CFR untuk review atasan sebelum buyer dihubungi**, bukan approval/quote otomatis.
- Jika CFR tidak menarik dan ekonomi FOB belum bisa dinilai, gunakan `DEFER_FOB_REVIEW`. `NO_BID` hanya jika kedua alternatif terbukti gagal dengan kriteria yang disetujui. Jangan otomatis menyatakan FOB menguntungkan karena CFR gagal.
- Brief memuat input, basis 45.000 MT, harga FOB/CFR, vessel screen, hari, biaya per komponen, freight revenue, komisi, kontribusi, reason code, asumsi, batas kepercayaan, dan human handoff.

**Selesai bila:** output bisa dijelaskan kepada mentor tanpa membaca source code; rekomendasi berubah konsisten ketika input relevan diubah.

### I2-R06 — verifikasi E2E dan review iterasi

**Dependensi:** R01–R05. **Target:** test suite, satu run positif dan beberapa run negatif, `../reviews/ITERATION_02.md`, state.

- Jalankan satu kasus pra-penawaran dari dataset terkoreksi sampai decision brief lengkap; tidak ada HOLD hanya karena buyer belum dihubungi atau metadata/approval domain yang ditunda.
- Jalankan tes negatif: cargo melebihi DWT, unit/angka invalid, biaya ganda, kontribusi nol/negatif, Index/Alpha hilang, buyer menolak CFR, dan FOB economics belum diketahui.
- Simpan input snapshot/hash, versi rumus/aturan, trace, status simulasi, dan hasil tes pada satu contoh run revisi. Perbandingan basis historis 46.000 MT tercatat sebagai ringkasan, bukan folder run yang masih tersedia.
- Minta mentor menilai definisi ekonomi FOB, dasar komisi, cakupan `Other voyage costs total`, dan kapan minimum margin serta screen kapasitas lebih lengkap diperlukan.

**Selesai bila:** review mencatat `accepted`, `needs-revision`, atau `blocked` beserta bukti; iterasi berikutnya diturunkan dari feedback, bukan otomatis masuk MVP.

## Batas pekerjaan

Tidak ada integrasi Fleetra/SAP/AIS, validasi sumber domain lengkap, approval otomatis, penawaran ke buyer, charter economics, optimasi kecepatan, atau klaim bahwa DWT saja membuktikan kapal bisa memuat kargo. Spesifikasi tambahan di CSV (bunkers/constants allowance, speed–fuel curve, draft, dimensi, holds, cranes) dicatat sebagai kandidat pengembangan berikutnya, bukan aturan baru tanpa keputusan mentor.
