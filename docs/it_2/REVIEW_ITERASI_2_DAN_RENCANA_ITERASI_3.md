# Review Iterasi 2 dan rencana terbaik untuk Iterasi 3

**Tanggal review:** 24 September 2026  
**Status:** review teknis independen selesai; **keputusan penerimaan bisnis mentor belum ada**.  
**Tahap produk:** simulasi iteratif, **bukan** final simulation validation, MVP, quotation, atau persetujuan komersial.

## 1. Kesimpulan untuk dibawa ke mentor

Iterasi 2 sudah berhasil sebagai **prototipe DSS pra-penawaran yang dapat direplay**: CSV kasus dibaca, Gate 1 memeriksa kelayakan *memulai analisis*, Python menghitung ekonomi freight kapal milik, Gate 2 menghasilkan kandidat CFR bersyarat, dan manusia tetap memutuskan sebelum buyer didekati. **26 dari 26 tes lulus** pada 24 September 2026. Angka utama run yang dipertahankan juga cocok ketika dihitung ulang secara independen dari input, bukan dengan memanggil helper perhitungan aplikasi.

Namun, hasilnya **belum** membuktikan bahwa CFR lebih menguntungkan daripada FOB untuk PI Group, bahwa buyer akan menerima harga, atau bahwa kapal 58.000 DWT tersedia dan aman memuat 45.000 MT. Kandidat CFR di sini bermakna lebih sempit: *kontribusi freight PILOG positif dalam asumsi simulasi dan screen gross-DWT awal lulus*. Itu cukup untuk diskusi dengan mentor, **belum cukup untuk klaim “pilih CFR” operasional**.

**Rekomendasi:** lanjutkan ke **Iterasi 3 simulasi untuk mengeraskan logika keputusan dan batas bukti**, bukan ke integrasi Fleetra/SAP/AIS atau MVP. Minta kritik mentor atas definisi bisnis sebelum mengunci aturan baru. Jangan mengganti status Iterasi 2 menjadi `accepted` tanpa keputusan beliau.

## 2. Yang diperiksa dan batas review

Saya membaca kontrak/keputusan aktif, modul `src/pilog_cfr_dss/`, tes unit dan integrasi, CSV + input manual + kebijakan kapal, serta **satu** run terakhir yang masih disimpan. Saya menjalankan `python -m unittest discover -s tests -p test_*.py -v` dan menghitung ulang angka utama dengan ekspresi `Decimal` tersendiri dari baris input CSV. Saya **tidak** mengubah engine, dataset, gate, task board, atau status iterasi; tidak menjalankan pipeline baru yang membuat folder output.

| Bukti yang dapat dibuka | Fungsi dalam review |
|---|---|
| [Keputusan aktif](../../.agents/DECISIONS.md), [kontrak ekonomi](../../.agents/contracts/ITERATION_02_ECONOMICS.md), [task revisi](../../.agents/tasks/ITERATION_02_PROPOSED.md) | Menentukan aturan yang memang telah disetujui untuk simulasi, bukan menebak dari kode. |
| [CSV kasus](../../data/processed/dataset_ready.csv), [input manual](../../data/processed/iteration_02_pre_offer_simulation.json), [kelas kapal](../../data/processed/vessel_classes.json) | Sumber angka, konteks pra-penawaran, dan kebijakan gross-DWT. |
| [Pipeline](../../src/pilog_cfr_dss/orchestration/pipeline.py), [validasi](../../src/pilog_cfr_dss/validation/ingest.py), [skenario](../../src/pilog_cfr_dss/scenarios/economics.py), [gate](../../src/pilog_cfr_dss/decisions/gates.py) | Perilaku yang benar-benar dieksekusi. |
| [Decision brief run terakhir](../../outputs/runs/i2_20260923T091307166739Z_f5c4e74a/decision_brief.md), [trace](../../outputs/runs/i2_20260923T091307166739Z_f5c4e74a/calculation_trace.json), [ekonomi](../../outputs/runs/i2_20260923T091307166739Z_f5c4e74a/scenario_economics.json) | Nilai dan alasan yang diterima pengguna. |
| [Review Iterasi 2 lama](../../.agents/reviews/ITERATION_02.md) | Riwayat perubahan; bagian “Arsip review awal” **bukan** kontrak aktif dan run yang dirujuk di sana sudah dibersihkan. |

**Batas:** hanya satu kasus Aqaba-derived dengan label rute Bontang → ECI yang dapat direplay sebagai run tersimpan. CSV diperlakukan sebagai *ground truth numerik simulasi* sesuai arahan mentor/pengguna, **bukan** bukti tarif pelabuhan, jarak, harga bunker, atau kapal pada transaksi nyata. Pemeriksaan sumber/as-of/approval domain sengaja ditunda; jangan memasukkannya kembali sebagai HOLD Iterasi 3 tanpa keputusan baru.

## 3. Pembacaan pipeline yang sebenarnya

1. **Input dan kontrak:** `dataset_ready.csv` berisi 61 variabel aktif; angka alokasi 46.000 MT lama ditolak. `manual.json` memasok Index, Alpha, adjustment, tahap `pre_offer`, pihak transaksi, serta definisi biaya/komisi simulasi. Konfigurasi kelas kapal terpisah dan berversi.
2. **Quality dan Gate 1:** nilai/denominator kritis, pricing USD/MT, dan konteks pra-penawaran diperiksa. Buyer `not_approached` memang normal. Status sumber/as-of `WARN`, bukan bypass atas nilai teknis yang rusak.
3. **Hitungan fisik:** satu cargo 45.000 MT dipakai untuk hari muat/bongkar; jarak/kecepatan untuk hari laut; konsumsi × hari × harga untuk bunker. Hasil `PARTIAL_PHYSICAL_ESTIMATE` berarti belum lengkap secara operasional.
4. **Alternatif:** FOB berisi **harga baseline saja** (`Index + Alpha`); cabang CFR melakukan screen Handysize/Supramax lalu menghitung biaya, revenue, komisi, dan kontribusi PILOG. `NO_BID/DEFER` adalah outcome, bukan skenario harga.
5. **Gate 2 dan brief:** bila kontribusi CFR > 0 dan screen awal lulus, hasil `CFR_CANDIDATE_PENDING_HUMAN_REVIEW`; bila CFR tidak menarik sedangkan ekonomi FOB belum ada, hasil `DEFER_FOB_REVIEW`. Brief mencantumkan asumsi dan langkah manusia. Sistem tidak mengirim penawaran.

### Rekonsiliasi angka yang paling menentukan

Perhitungan ulang independen memakai 45.000 MT, jarak 2.045/5.520 NM, kecepatan 14/15 knot, loading/discharge 10.000/6.000 MT per hari, konsumsi dan harga di CSV, running USD 5.612/hari, biaya lain USD 200.000, serta tarif jual USD 20/MT:

| Objek | Nilai hasil hitung ulang | Makna |
|---|---:|---|
| Total voyage | 33,4196428571 hari | Termasuk laden, ballast, muat, bongkar; canal = 0. |
| Total biaya freight/voyage | USD 735.303,896488 | Running + fuel oil + diesel + port/other agregat. |
| Gross freight revenue | USD 900.000 | USD 20/MT × 45.000 MT. |
| Komisi simulasi | USD 56.250 | 6,25% kumulatif dari gross; **basis kontrak belum dikonfirmasi**. |
| Kontribusi freight PILOG | USD 108.446,103512 | Revenue − komisi − biaya; **bukan laba bersih perusahaan**. |
| Tarif impas setelah komisi | sekitar USD 17,4294/MT | `biaya / [cargo × (1 − 0,0625)]`; **diagnostik hitung ulang**, belum harga penawaran/kebijakan. |

FOB indikatif = USD 253/MT; CFR indikatif = USD 273/MT pada adjustment nol. Angka ini konsisten dengan run. Selisih harga FOB–CFR **bukan** otomatis laba PILOG: yang diuji adalah revenue jasa freight dikurangi biaya freight dan komisi.

## 4. Penilaian mendalam: yang sudah kuat dan yang belum

| Area | Temuan berbasis bukti | Penilaian |
|---|---|---|
| Basis kuantitas | 45.000 MT konsisten untuk hari pelabuhan, revenue, komisi, biaya/MT; baris 46.000 MT ditolak dan dites. | **Kuat untuk simulasi.** |
| Pemisahan entitas dan price object | PI Group = seller komoditas; PILOG = penyedia freight. `Freight rate` CSV dibaca sebagai harga jual PILOG, bukan biaya. | **Kuat**, tetapi kontrak/arus pembayaran nyata belum dibuktikan. |
| Ekonomi kapal milik | Running + bunker + other; hire dan daily assumption tidak ditambahkan. Perubahan USD 10.000 pada `Other voyage costs` mengubah kontribusi USD 10.000 dalam tes. | **Kuat secara rumus**, cakupan agregat/komisi masih asumsi. |
| Gate pra-penawaran | Buyer belum didekati tidak memblokir; buyer menolak membuat CFR di luar scope; data rusak memblokir. | **Sesuai alur mentor.** |
| Preskriptif tetapi aman | Kandidat CFR menyebut alasan, komponen biaya, approval manusia. CFR negatif/tidak feasible tidak otomatis menjadi “FOB profitable”. | **Baik**, tetapi label kelayakan perlu dipertajam. |
| Auditability | Snapshot 4 input + hash + versi formula/rule + trace disimpan dalam run. | **Baik**; snapshot **kode/commit** belum ada sehingga replay lintas revisi engine belum sepenuhnya terjamin. |
| Coverage tes | 26 tes hijau mencakup happy path, sejumlah input gagal, biaya, dan gate. | **Belum membuktikan** konsistensi seluruh perubahan harga/kapal/rute dan batas keputusan. |

### Temuan prioritas (bukan semua adalah bug)

**P1 — “Perbandingan FOB vs CFR” masih tidak simetris.** Pada [pembangun skenario](../../src/pilog_cfr_dss/scenarios/build.py), FOB adalah `PRICE_BASELINE_ONLY` dan tidak memiliki biaya/margin barang; sedangkan CFR memiliki kontribusi freight PILOG. [Gate 2](../../src/pilog_cfr_dss/decisions/gates.py) sebenarnya menilai sinyal CFR, **bukan** memilih alternatif dengan profit komparabel. Ini pembatasan yang sudah diungkap dengan benar, tetapi bahasa “dua alternatif yang dibandingkan” mudah terbaca terlalu kuat. **Tindakan I3:** nyatakan status perbandingan `NOT_COMPARABLE_FOR_TOTAL_ECONOMICS` secara eksplisit dan minta mentor memutuskan apakah FOB cukup menjadi referensi harga atau perlu model ekonomi PI seller terpisah. Jangan mengarang biaya komoditas.

**P1 — Makna `CFR adjustment` terhadap revenue dan kontribusi belum jelas.** [Rumus harga](../../src/pilog_cfr_dss/scenarios/economics.py) menambahkan adjustment ke CFR/MT, tetapi freight revenue tetap `Freight rate × cargo`, tanpa adjustment. Bila adjustment adalah diskon/uplift freight milik PILOG, kontribusi pada Gate 2 seharusnya ikut berubah; bila adjustment adalah penyesuaian harga komoditas PI seller, pemisahan sekarang mungkin benar. **Tindakan I3:** minta pemilik ekonomi/kontrak memberi definisi, owner, dan contoh ± adjustment; lakukan tes invariant harga→revenue→kontribusi sesuai keputusan. Sampai jelas, jangan menjadikan adjustment nonnol dasar rekomendasi.

**P1 — “Pilihan kapal” baru screen satu profil, bukan optimasi Handysize vs Supramax.** [Screen kelas](../../src/pilog_cfr_dss/scenarios/build.py) memakai **DWT kasus yang sama, 58.000 MT**, untuk kedua kelas. Dengan kargo 45.000 MT, Handysize pasti gagal batas 40.000 DWT dan Supramax lolos gross-DWT. Ini keputusan kelas logis, tetapi belum membandingkan dua kapal dengan speed, konsumsi, biaya, ketersediaan, atau DWCC masing-masing. `ScenarioEvidence.feasible=True` saat ini berarti *screen awal pass* saja. **Tindakan I3:** bedakan `class_screen_pass`, `safe_loading_verified`, dan `operational_availability`; jika data kapal kedua belum ada, tampilkan “hanya satu profil dinilai”, bukan “kapal terbaik”. Pertimbangkan allowance bunker/constants 1.800/500 MT dari CSV hanya setelah mentor menyetujui apakah keduanya memang berlaku pada profil kasus.

**P1 — Asumsi konsumsi pada speed ballast perlu rekonsiliasi.** CSV kasus memakai ballast **15 knot** dan `fuel_oil_consumption_ballast=25 MT/hari`; CSV juga memuat kurva **14 knot ballast = 25 MT/hari**, tetapi tidak memuat titik 15 knot. [Hitungan fisik](../../src/pilog_cfr_dss/calculations/physical.py) menerima pasangan angka kasus apa adanya. Ini **bukan bukti angka 25 salah** (bisa saja estimate tersendiri), tetapi asal/basisnya belum dapat dibuktikan; perubahan speed tanpa menyesuaikan konsumsi dapat menghasilkan sensitivitas biaya yang menyesatkan. **Tindakan I3:** beri label `case_estimate` vs `speed_curve`, minta mentor pilih metode; bila kurva dipakai, jangan ekstrapolasi 15 knot tanpa aturan yang disetujui.

**P2 — Kondisi zero-ballast masih diperlakukan sebagai data buruk.** [Quality check](../../src/pilog_cfr_dss/validation/ingest.py) mensyaratkan `ballast_distance_nm > 0`, sementara fungsi [sea_days](../../src/pilog_cfr_dss/calculations/voyage_days.py) membolehkan distance = 0. Kapal yang sudah berada di loading port dapat secara logis mempunyai nol ballast, jadi aturan input lebih sempit dari kalkulator. **Tindakan I3:** konfirmasi konteks voyage dengan mentor, lalu tambahkan kasus zero-ballast sah atau alasan bisnis eksplisit untuk menolaknya.

**P2 — Audit run belum mengikat versi kode secara kuat.** Empat input disalin dan diverifikasi hash, tetapi `formula_version`/`rule_version` adalah string manual dalam [model](../../src/pilog_cfr_dss/models/contracts.py). Jika kode berubah tanpa menaikkan versi, snapshot input lama tidak cukup untuk mereproduksi hasil. **Tindakan I3:** simpan Git commit (bila ada), indikator dirty worktree, serta versi Python/engine di manifest run; tetap simpan versi formula/rule dan hash input. Jangan menyimpan secret.

**Catatan cakupan, bukan alasan HOLD sekarang:** agregat USD 200.000 belum terurai; tiga komisi × gross adalah asumsi; rute/biaya dari data Aqaba-derived belum diverifikasi sebagai Bontang–ECI; buyer willingness-to-pay, FOB commodity margin, draft, terminal, laycan, dan vessel availability belum ada. Semua itu wajib tetap jelas di brief dan pada diskusi mentor, tetapi aturan simulasi yang disetujui memang menunda source/approval gate.

## 5. Iterasi 3 yang disarankan: *decision-logic hardening*, tetap simulasi

### Tujuan dan ukuran selesai

**Tujuan:** reviewer bisa menjelaskan *persis* mengapa kasus menjadi kandidat CFR, kapan harus defer, angka apa yang menentukan perubahan keputusan, dan bukti apa yang belum ada—tanpa salah menyamakan harga CFR, kontribusi PILOG, profit PI Group, atau kapasitas gross-DWT. Satu kasus positif saja tidak cukup; beberapa kasus tandingan harus menunjukkan gate berpindah secara benar dan aman.

**Tidak masuk scope I3:** konektor Fleetra/SAP/AIS, data live, auto-quote/auto-approval, chartered vessel economics, optimasi multi-kapal/rute, ML, hedging otomatis, atau target 40% CFR sebagai objective per transaksi. Target korporat 60% FOB/40% CFR adalah **konteks portofolio**; ia tidak boleh memaksa satu voyage buruk menjadi CFR.

### Urutan PLAN → TASK → EXECUTE → TEST → REVIEW

| Batch | Tugas konkret | Ketergantungan / output yang diharapkan | Acceptance criteria sebelum disebut selesai |
|---|---|---|---|
| **I3-0: putusan mentor** | Bawa review ini + brief I2. Dapatkan koreksi/konfirmasi `adjustment`, komisi, isi USD 200.000, arti `freight rate` per kontrak, dan apakah FOB tetap baseline harga saja. Catat status I2 `accepted`/`needs-revision`/`blocked` secara jujur. | Mentor BusDev/shipping; revisi decision log dan task I3 **setelah** jawaban. Pekerjaan tes non-kebijakan boleh disiapkan sambil menunggu. | Tidak ada aturan ekonomi baru hanya karena AI menyarankan; setiap keputusan punya owner, tanggal, contoh angka, dan unit. |
| **I3-1: kontrak keputusan** | Pisahkan price object dan owner: FOB barang PI Group, tarif jual freight PILOG, adjustment (siapa menerima/membayar), biaya voyage, komisi, kontribusi. Nyatakan FOB `PRICE_ONLY` dan CFR `CONTRIBUTION_ESTIMATED`, bukan ranking profit setara. | Keputusan I3-0; update kontrak, tipe output, reason codes, brief. | Adjustment +/− mempengaruhi komponen yang benar menurut keputusan mentor; input yang tidak terdefinisi menghasilkan status aman, bukan angka seolah valid. |
| **I3-2: diagnosa ekonomi & sensitivitas** | Gunakan fungsi `required_rate_net_of_commission_usd_mt` yang sudah ada untuk tampilkan **tarif impas diagnostik**, gap tarif jual vs impas, dan sensitivitas kecil yang dikendalikan (mis. tarif jual, biaya bunker, hari, cargo), tanpa membuat floor margin baru. | Basis komisi dan adjustment disetujui atau tetap dilabel asumsi simulasi. | Seluruh angka dihasilkan Python `Decimal`; baseline dan skenario perubahan merekonsiliasi revenue − komisi − biaya; tidak ada optimasi harga/quote otomatis. |
| **I3-3: status kapal & konsumsi** | Bedakan gross-DWT pass dari kapasitas aman/availability. Konfirmasi pasangan speed–consumption; buat pemeriksaan konsistensi atau peringatan yang tepat, bukan interpolasi diam-diam. Uji zero-ballast sesuai keputusan mentor. | Bukti spesifikasi kapal dan kebijakan konsumsi; jika tidak tersedia, pertahankan `UNKNOWN`. | Brief tidak menyebut Supramax “feasible final/terbaik” dari satu profil; kapasitas aktual tetap `UNKNOWN` tanpa bukti; perubahan speed tidak memakai kurva tak cocok secara tersembunyi. |
| **I3-4: matriks kasus dan regresi** | Buat fixture **sintetis/non-komersial** dari salinan input untuk: positif, tepat impas, negatif, cargo di/di atas batas DWT, buyer decline, missing Index/Alpha, komisi invalid, adjustment ±, zero-ballast, perubahan route/distance, dan ketidakcocokan speed–fuel. | Aturan I3-1 s.d. I3-3; tidak mengganti CSV sumber kasus I2. | Setiap fixture menyatakan expected Gate 1, Gate 2, alasan, angka kunci; tes membuktikan perubahan input relevan mengubah output yang benar dan input tak relevan tidak. |
| **I3-5: review paket & replay** | Jalankan suite dan beberapa E2E, simpan *satu* set artefak ringkas untuk mentor, manifest versi kode, tabel “apa berubah dari I2”, dan daftar isu tersisa. | Semua batch sebelumnya; review bersama mentor. | Kasus positif dan negatif bisa dijelaskan end-to-end dari snapshot, rumus, reason code sampai human action. Mentor memberi status I3; **belum** naik otomatis ke Final Simulation Validation/MVP. |

**Prioritas jika waktu terbatas:** I3-0 → I3-1 → I3-4 terlebih dahulu. I3-2 dan I3-3 hanya sedalam definisi/data yang benar-benar tersedia. Lebih baik decision brief jujur yang menahan klaim daripada model “lebih lengkap” tetapi berasumsi diam-diam.

### Matriks hasil yang seharusnya dapat dijelaskan

| Kondisi | Hasil yang diharapkan secara prinsip | Alasan utama |
|---|---|---|
| Input minimum valid, buyer belum didekati, kontribusi CFR positif, gross-DWT pass | Kandidat CFR **untuk review manusia** | Boleh dianalisis, belum boleh ditawarkan otomatis. |
| Kontribusi tepat nol atau negatif | Review reprice/redesign CFR dan ekonomi FOB; bukan auto-FOB-profit/NO_BID | FOB profit tidak tersedia, floor komersial belum ada. |
| Cargo melampaui screen kelas | Tidak ada kandidat kapal dari kelas yang diuji; minta desain/kapal lain atau review FOB | Screen fisik awal gagal, bukan bukti semua opsi dunia nyata gagal. |
| Input teknis/price object tidak terdefinisi atau unit salah | HOLD dengan field dan sebab spesifik | Jangan membiarkan angka palsu mencapai Gate 2. |
| Buyer sudah menolak CFR atau seller tidak punya freight scope | CFR out of scope; arahkan review FOB | Perbedaan *scope* dengan ekonomi harus terlihat. |

`NO_BID` baru layak diuji sebagai keputusan ketika **kedua** alternatif memiliki bukti ketidaklayakan berdasarkan kriteria yang disetujui; belum ada dasar itu di I2. Hindari membuat test yang sekadar memaksa `NO_BID` muncul.

## 6. Pertanyaan singkat untuk mentor—urut dari yang paling mengubah aturan

1. **Adjustment CFR itu uang siapa?** Bila harga CFR naik/turun USD X/MT, berapa bagian yang mengubah pendapatan freight PILOG dan berapa yang masuk harga barang PI Group? Mohon satu contoh kontrak/angka hipotetis.
2. **FOB ingin dinilai sampai mana di DSS ini?** Apakah hanya harga pembanding pra-penawaran, atau mentor ingin margin barang PI Group dihitung juga? Jika yang kedua, apa biaya/otoritas datanya?
3. **Komisi 2,5% + 1,25% + 2,5%:** ketiganya selalu berlaku bersama dan semuanya dari gross freight, atau bersyarat/berbasis objek berbeda?
4. **USD 200.000 `Other voyage costs total`:** komponen apa saja di dalamnya? Khususnya port, agency, canal, dan apakah semua dibayar PILOG dalam skenario ini?
5. **Speed 15 knot ballast vs konsumsi 25 MT/hari:** angka 25 ini estimate khusus 15 knot atau salinan tabel 14 knot? Jika speed berubah, aturan fuel mana yang harus dipakai?
6. **Kapal:** untuk 45.000 MT, apakah allowance bunker 1.800 MT dan constants 500 MT pada CSV berlaku untuk kapal 58.000 DWT kasus? Apakah mentor ingin Iterasi 3 hanya *screen* DWCC kasar, atau menunggu data draft/port/laycan agar tidak memberi klaim kapasitas palsu?
7. **Kapan kontribusi positif cukup untuk dibawa ke buyer?** Saat ini jawabannya hanya “layak ditinjau atasan”; minimum margin ditunda. Pertahankan status ini sampai mentor menentukan kebijakan, bukan menyisipkan target 40% sebagai ambang.

## 7. Cara menutup review dan memulai I3

- Presentasikan **hasil I2, batas klaim, dan 7 pertanyaan** di atas kepada mentor. Catat perubahan definisi di `.agents/DECISIONS.md`; jangan mengedit arsip review pra-revisi seolah menjadi aturan aktif.
- Setelah mentor menilai I2, perbarui `.agents/reviews/ITERATION_02.md` dan `.agents/ITERATION_STATE.json`; lalu turunkan task I3 yang disetujui. Dokumen ini adalah **usulan rencana**, bukan persetujuan bisnis atau instruksi untuk langsung mengeksekusi seluruh batch.
- Lakukan satu feedback loop lagi setelah I3. Perpindahan ke *Final Simulation Validation* hanya ketika logika telah lolos kasus representatif, batas, dan gagal serta mentor menyatakan cukup kuat; **MVP adalah keputusan terpisah**.

## Referensi domain untuk menjaga batas peran

- [ICC Incoterms® 2020, FOB dan CFR](https://library.iccwbo.org/content/tfb/BOOKS/BK_0049/BK_0049_05_RulesSea.htm): CFR mengatur kewajiban seller untuk mengadakan/membayar carriage ke tujuan yang dinamai, tetapi ini tidak menjadikan PILOG otomatis seller komoditas; kontrak jasa freight PI Group–PILOG tetap harus dimodelkan tersendiri.
- [Baltic Exchange, Dry Services](https://www.balticexchange.com/en/data-services/market-information0/dry-services.html): referensi benchmark pasar/kelas dry bulk, **bukan** bukti bahwa kapal PILOG tertentu tersedia, cocok dengan terminal, atau memiliki DWCC aktual untuk kasus ini.
