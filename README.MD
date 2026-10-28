# PILOG CFR DSS — Simulasi Iterasi 4

**Status 28 Oktober:** mentor menyetujui Iterasi 4 melalui konfirmasi pengguna. Versi ini menjadi baseline yang diterima untuk logika dan UI advisory. Porting stack/deployment bagi pengguna lain dibahas sebagai Iterasi 5; penerimaan ini tidak mengubah angka, gate atau kewenangan kontrak.

## Format angka — dua desimal (D-069)

Hasil UI dan brief memakai format Indonesia: **23,3896 → 23,39**, **1234,567 → 1.234,57**. Pembulatan biasa HALF_UP; nilai minimum untuk impas/recovery dibulatkan ke atas dua desimal agar tetap cukup menutup biaya. Contoh minimum tarif raw 26.2114 ditampilkan 26,22 USD/MT. Tidak otomatis mengganti freight yang sudah ditetapkan.

Mesin Decimal, JSON, source/snapshot dan audit rinci tetap menyimpan presisi penuh. Form input teknis masih memakai titik desimal tanpa pemisah ribuan. Angka tampilan tidak dipakai menghitung ulang bisnis; total dari presisi penuh dapat sedikit berbeda dari perkalian/penjumlahan angka UI yang sudah dibulatkan. ID, nomor putaran, tanggal dan versi tetap.

Brief aktif baru **I4-BRIEF.8**, formula/rule I4.1 tetap. Tiga contoh format baru ada di review terbaru; hasil finansial/keputusan sama dengan snapshot sebelumnya. Refresh/rerun app untuk melihat format baru.

## Alur UI terbaru — D-067, 28 Oktober

1. **Step 1 — Data Pengiriman & Kapal:** pilih profil sekali melalui **Pilih profil kapal**. Kartu kiri menunjukkan rute/muatan/jarak serta spesifikasi dari sheet. Kartu kanan memisahkan **Target harian**, **Harga bunker** dan **Indeks urea**. Acuan pasar kapal mengikuti kelas profil; Godau menggunakan proxy Handysize yang ditandai.
2. **Step 2 — Voyage Economics:** klik **Hitung ekonomi voyage**. Hasil memakai profil Step 1; tidak ada pemilih kedua. Dua tabel memperlihatkan durasi/kebutuhan fuel oil dan diesel oil, lalu biaya serta kontribusi. Harga bunker manual/estimasi terbaru ditampilkan sesuai nilai yang benar-benar digunakan.
3. Tetapkan freight, isi/terapkan bid dan evaluasi seperti alur sebelumnya.
4. Hasil utama tetap commercial decision brief. **Analisis pendukung** berisi Exposure, Risiko, Dampak logistik dan Konsekuensi harga dalam tabel/metric ringkas. Cakupan saat ini adalah perhitungan dasar; probabilitas/hedging dan kesiapan operasi penuh belum dibangun.

Jarak berasal OD untuk Bontang–Mundra/WCI. Harga urea berasal FOB SEA; Singapore 380 CST/MGO adalah acuan harga fuel oil/diesel oil, bukan lokasi bunkering. Input pelabuhan tetap historis/asumsi. Detail sumber/tanggal dan penanda manual/proxy tersedia tanpa copy footer berulang.

Formula, gate, fixed freight, dataset dan unduhan MD/JSON tetap. Tiga run pada review D-065 tetap acuan; tidak ada dataset/run baru untuk perubahan tampilan ini. Jika layout lama masih terlihat, rerun/refresh halaman app. Bukti 21 AppTest, 18 integrasi dan browser ada di review terbaru.

## Penguatan keputusan komersial — 28 Oktober (D-064/D-065)

Versi aktif **I4-BRIEF.7** membedakan **GO**, **NO GO harga barang**, dan **NO GO ekonomi freight**. Outcome tetap hanya GO/NO GO. Bid tertinggi dapat memenuhi OE/HPS PI tetapi menghasilkan kontribusi freight negatif bagi PILOG.

**Coba di UI:** klik **Muat NO GO ekonomi**, lalu **Evaluasi tender & DSS**. Contoh default memakai freight 25,4513 USD/MT dan bid GO, tetapi estimasi pelabuhan/biaya lain sintetis dinaikkan dari 200.000 ke 450.000 USD. Gate A lolos; Gate B gagal. Ini contoh uji, bukan biaya aktual baru.

**Uji perubahan biaya pada kasusmu sendiri:**

1. Hitung ekonomi voyage, tetapkan freight, isi/terapkan bid, lalu evaluasi.
2. Aktifkan **Perbarui estimasi biaya**. Isi biaya terbaru dan **Alasan perubahan biaya**.
3. Klik **Terapkan estimasi biaya**, kemudian **Evaluasi tender & DSS** lagi.
4. Freight, `price_id`, `fixed_at`, cargo/profil dan bid tetap. Estimasi biaya menjadi salinan terversi; input asal dan run lama tetap tersimpan. Hasil/unduhan lama disembunyikan selama editor terbuka.
5. Brief menunjukkan pendapatan, biaya, kontribusi terbaru, penyebab perubahan, risiko gabungan dan opsi menuju impas. Saran penawaran baru bersifat hipotetis; tidak mengganti freight tender otomatis.

Untuk **mengubah penawaran**, buat revisi kasus terlebih dahulu. Pada **Harga penawaran**, isi **Freight penawaran (USD/MT)** dan alasan jika berbeda dari indikasi. Ini menetapkan harga baru secara eksplisit dan membuka tender baru; bukan reforecast biaya pada harga lama. Harga yang dihasilkan model atau ditetapkan pengguna belum menjadi bukti penerimaan buyer.

Pada **Pilihan kapal dan dasar perbandingan**, lihat **Freight yang sama** untuk membandingkan biaya, durasi, kontribusi total/per hari empat profil pada satu tarif. Tab kedua memperlihatkan tarif untuk mengejar target masing-masing profil. Tidak ada pemilihan kapal otomatis; proxy pasar Godau tetap ditandai.

CLI aktif sekarang default **tiga contoh** pada satu harga tetap bersama:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B scripts/run_market_simulation.py
.\.venv\Scripts\python.exe -X utf8 -B scripts/run_market_simulation.py --case no-go-economics
```

Pilihan lain: `go`, `no-go-floor` (`no-go` alias lama), `both` untuk GO+floor, dan `all` untuk ketiganya. Input/sumber template dan snapshot lama tidak ditulis ulang. CLI menyimpan artefak baru di `outputs/runs/`; jangan mengedit snapshot hasil.

Baca [review terbaru](.agents/reviews/ITERATION_04.md) untuk tiga run, bukti tes, hasil rekonsiliasi dan batas penggunaan. Gate A/B serta formula dasar I4.1 tetap. RBAC/award/transaksi/MVP belum dibangun. Bagian D-063 di bawah adalah panduan basis input yang tetap berlaku, kecuali jumlah default CLI yang telah menjadi tiga.

## Basis input — komisi nol, jarak OD dan tabel tender (D-063)

Kasus baru memakai **tiga komisi 0%** dan **OD hanya untuk jarak satu arah dalam NM**. Bontang–Mundra: `Input - OD Intl!H11 = 3906` pada workbook OD asli yang dibaca tanpa diubah. Tarif OD tidak dipakai atau dibandingkan. UI menampilkan logo asli dari `public/Pupuk_Indonesia_Logistik.png`, menghilangkan subtitle/penjelasan langkah berulang, dan memisahkan tabel bid per putaran dengan Alpha/Freight/FOB/CFR/Status. Harga FOB/CFR berasal engine dan bersifat read-only. Tiga menit tetap per putaran dan Gate A/B tidak berubah.

Empat profil **Sheet1, AQABA, Sby, Godau** tetap tersedia sampai Supramax. Kartu **Profil kapal terpilih** merangkum spesifikasi fisik workbook; **Acuan pasar kapal** menunjukkan seri Fearnpulse yang dipakai menghitung tarif atau sekadar referensi kelas lain. Satu pilihan profil bukan dua kapal. Basis input baru **I4-INPUT.2**, jarak **OD-DISTANCE.1**, brief **I4-BRIEF.6**, harga **PRICE.1**, clock **TENDER-CLOCK.1**. Formula dasar I4.1 tetap. **200/200 tes lulus**, smoke browser GO/NO GO/logo/unduhan/narrow lulus, 108 assertion independen dua snapshot cocok; detail pada [review](.agents/reviews/ITERATION_04.md). Server tes dihentikan, app tidak ditinggalkan berjalan.

Jalankan dari PowerShell:

```powershell
cd "C:\AIDAN\SEM 7\PT PUPUK LOGISTIK INDONESIA\pilog-cfr-dss"
.\.venv\Scripts\python.exe -m streamlit run apps/streamlit_app.py
```

Buka **http://127.0.0.1:8501**, hentikan dengan Ctrl+C di terminal yang menjalankan app. Pada komputer ini environment sudah terpasang. Untuk komputer baru, instal requirements seperti panduan baseline di bawah, dan pastikan workbook/catalog/snapshot data ikut tersedia.

```powershell
# Perbarui profil dari workbook read-only dan ambil snapshot pasar:
.\.venv\Scripts\python.exe -X utf8 -B scripts/refresh_market_inputs.py

# Jalankan pipeline aktif tanpa UI, default GO/NO GO floor/NO GO ekonomi:
.\.venv\Scripts\python.exe -X utf8 -B scripts/run_market_simulation.py
.\.venv\Scripts\python.exe -X utf8 -B scripts/run_market_simulation.py --profile ve_godau --case go
```

UI dimulai dari snapshot tersimpan, sehingga dapat dipakai offline. `Perbarui data Fearnpulse` mengambil snapshot baru; `Gunakan data pasar terbaru` menerapkannya pada draft. Jika freight sudah fixed, tombol membuat kasus revisi tanpa membawa bid/harga lama. Tidak ada repricing diam-diam. Pilihan profil sebelum tender mengganti paket field lengkap; `Bandingkan profil` menghitung semua opsi dengan basis rute/Q sama, lalu pengguna memilih manual.

Review Data tetap dua kartu dengan tabel sumber/unit/tanggal. Singkatan fuel oil/diesel oil diperluas dalam label. Tiga komisi dan jarak OD terikat sumber/kebijakan dan tidak diedit melalui field manual; input eksperimen lain tetap tersedia. Fearnpulse menampilkan dua acuan T/C dan harga bunker yang benar-benar terikat pada kasus. Tidak ada Baltic input pada kasus aktif baru. Harga observasi, fetched_at, calculated_at dan fixed_at dibedakan; tanggal pasar tidak diganti tanggal refresh. Tampilan memakai WIB, audit menyimpan UTC. Kasus lama tanpa timestamp tidak di-backfill.

Godau Handymax 47.175 DWT memakai benchmark kelompok kecil Handysize 38k sebagai **proxy kelas**; tidak ada quote Handymax khusus yang direkayasa. Data T/C digunakan sebagai target TCE net sebelum running berdasarkan asumsi simulasi, bukan hire tambahan. Harga Singapore 380 CST/MGO adalah benchmark bunker, bukan bukti pembelian aktual. Snapshot yang diambil 27 Oktober memuat T/C 21 Oktober dan data bunker 1 Juli; tanggal per seri terlihat apa adanya.

**Putaran tender:** 180 detik tetap sejak jadwal buka. Jendela `[buka, tutup)`; bid tepat pada waktu tutup atau sesudahnya tidak masuk putaran tersebut, dan bid baru tidak memperpanjang waktu. Editor menampilkan start, cutoff dan submitted_at. Jika menambah putaran, isi waktu bid dan perpanjang cutoff ke jadwal putaran yang dikehendaki. Ini analisis jadwal tender, bukan auction realtime/award otomatis. Bid contoh memakai timestamp sintetis dalam jendela; kasus legacy tanpa clock tetap replay dengan aturan sebelumnya.

Sumber aktif: `data/processed/vessel_profiles_i4.json`, snapshot `fp_*.json` dan payload aslinya di `data/raw/fearnpulse/`, serta jarak dari `docs/it_4/Simulasi Tarif Internasional_Mei 2025.xlsx`. Nilai rute/Q/biaya/indeks/bid kasus dasar diwarisi sebagai salinan dari template I4, lalu field fisik diganti dari profil workbook, harga pasar dipetakan, tiga komisi dijadikan nol dan jarak di-resolve dari OD. Snapshot run menyertakan `od_distance.json` (raw cells, basis NM, hash payload) dan referensi/hash workbook; replay tidak memerlukan workbook hidup. Tidak mengklaim seluruh workbook OD ikut disalin. [Plan §7.13](docs/it_4/ITERATION_04_PLAN.md) menggantikan komisi lama dan perbandingan tarif OD pada register historis §7.12.10.

`scripts/run_iteration_04.py` dan dua input I4 awal tetap **baseline replay/regresi**, bukan entry aktif. CSV template dan run lama tetap dengan komisi/basis aslinya; tidak ditulis ulang sebagai hasil baru. Draft lama diarahkan ke salinan basis baru; harga fixed lama tidak direprice. Tidak ada RBAC/login produksi, auto-award, hedge atau integrasi Fleetra. Dashboard per peran dicatat untuk iterasi mendatang, kemungkinan I5. Bagian UI 23 Oktober berikut adalah histori baseline.

## UI lokal — 23 Oktober 2026

UI Streamlit sudah tersedia: review data → profil Handysize → voyage economics → freight tetap → tender → GO/NO GO dan brief lima bagian. Menggunakan engine Python yang sama dengan CLI; bukan e-auction buyer atau approval transaksi. **151/151 tes lulus**, termasuk 28 tes service/paritas/UI tambahan terhadap baseline 123. Smoke browser Edge juga lulus GO/NO GO, error input, editor, unduhan MD/JSON/ZIP dan layar sempit.

Dari root repo di PowerShell:

```powershell
# Pertama kali pada komputer baru:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-ui.txt

# Menjalankan UI:
.\.venv\Scripts\python.exe -m streamlit run apps/streamlit_app.py
```

Buka **http://127.0.0.1:8501**. Untuk menghentikan server pada terminal sendiri, tekan Ctrl+C. Tidak memerlukan login Fleetra, Chrome Allow atau remote debugging.

- **Coba cepat:** `Muat contoh GO` atau `Muat contoh NO GO` → `Evaluasi tender & DSS`.
- **Ikuti proses lengkap:** `Kasus baru` → opsional `Ubah input kasus`/`Terapkan input` → `Hitung ekonomi voyage` → `Tetapkan freight untuk tender` → `Edit bid & risiko` → masukkan bid atau klik `Isi contoh bid tiga putaran` → `Terapkan bid & risiko` → `Evaluasi tender & DSS`.
- Angka diketik tanpa pemisah ribuan, dengan titik untuk desimal. Komisi/shock memakai fraksi. Edit alpha tidak mengubah freight tetap atau kontribusi PILOG pada biaya/Q sama.
- `Kasus baru` membuka revisi basis tanpa membawa bid/tarif lama. Setelah freight tetap, basis voyage dikunci; skenario risiko tetap dapat diubah dan diuji pada tarif yang sama.
- `Simpan draft`/`Buka draft` memakai salinan di `outputs/ui_cases/`. Hasil final tersimpan immutable di `outputs/runs/`; unduhan memakai run yang sama. Template data, workbook/OD dan run lama tidak diubah.
- Saat editor terbuka, hasil/unduhan disembunyikan. Hasil hanya mengacu pada input yang telah diterapkan.
- Pilihan manual profil Handysize aktif. Supramax belum mempunyai paket profil I4 lengkap; tidak dihitung dari rentang DWT saja. Tidak ada auto-optimizer kapal.

Tes opsional UI/browser:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ui-test.txt
.\.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -X utf8 -B tests/ui/browser_smoke.py
```

Smoke browser memakai Microsoft Edge headless yang terpasang, profil browser baru dan storage sementara. Ia menutup proses uji miliknya sendiri, tidak menyentuh browser/login pengguna. Screenshot lokal di `outputs/ui_review/`, diabaikan Git. Core CLI tetap dapat berjalan tanpa Streamlit; tes UI dilewati bila dependency opsional tidak ada. Panduan/peta implementasi dan keterbatasan ada di [review UI](.agents/reviews/ITERATION_04.md), [plan §7.11](docs/it_4/ITERATION_04_PLAN.md) dan [task U](.agents/tasks/ITERATION_04.md).

## Baseline engine dan brief

**Revisi 23 Oktober: brief I4-BRIEF.4, 123/123 tes lulus.** Ringkasan gross PI/PILOG → biaya voyage → komisi → hasil neto PILOG tampil dalam lima bagian: keputusan komersial, exposure, risk, logistics impact dan pricing consequences. Data/gate/harga tetap tidak berubah. Semua brief/audit/JSON adalah **internal PI/PILOG**, bukan materi buyer. Buyer melihat freight; OE/HPS, gap FOB−OE/HPS, alpha minimum, bid buyer lain dan ekonomi PILOG tidak dibagikan kepada buyer. Label internal bukan kontrol akses produksi; jangan mengirim seluruh output kepada buyer.

DSS preskriptif untuk mendukung **GO/NO GO pelaksanaan CFR PILOG**. PI Group menjual barang dan menyelenggarakan tender; buyer melihat freight tetap lalu menawar alpha; PILOG menghitung jasa freight. Sistem membuat ranking kandidat dan menjelaskan ekonomi/risiko, **bukan menetapkan award atau menjalankan transaksi**.

Kasus I4: **urea granular bulk, 30.000 MT, Handysize milik, Bontang → Mundra/WCI, satu arah bermuatan (laden-only)** termasuk muat/bongkar. Tidak ada biaya perjalanan balik dalam model sistem. Angka kasus dapat diubah melalui input, bukan konstanta di fungsi kalkulasi.

Baca [review implementasi](.agents/reviews/ITERATION_04.md) untuk peta file, rumus, angka, asumsi dan bukti tes. [Plan utama](docs/it_4/ITERATION_04_PLAN.md) tetap menjadi spesifikasi; implementasi teknis belum berarti penerimaan mentor atau MVP.

## Menjalankan

Dari root repo, gunakan Python 3.11+:

```powershell
python -X utf8 -B -m unittest discover -s tests -q
python -X utf8 -B scripts/run_iteration_04.py
```

Perintah kedua menjalankan dua fixture: **GO** dan **NO GO floor tender**, dengan voyage/indeks/biaya/freight tetap yang sama. Perbedaan angka tender hanya alpha buyer; case ID berbeda untuk identifikasi. Verifikasi terakhir: **123/123 tes lulus**, termasuk 38 regresi historis I2/I3 dan 14 tes summary/brief baru; 67/91/109 tes adalah baseline sebelumnya.

Hasil handoff brief sebelum UI: [GO](outputs/runs/i4_20261023T072029597821Z_79698a9f/commercial_decision_brief.md), [NO GO](outputs/runs/i4_20261023T072029607228Z_de76cd6a/commercial_decision_brief.md). Keduanya lokal/diabaikan Git. [Review](.agents/reviews/ITERATION_04.md) mencatat rating subjektif GO/NO GO masing-masing 9,5/10, rekonsiliasi snapshot dan batas; bukan approval mentor/komersial atau akurasi 100%. Implementasi UI terbaru dijelaskan di awal README.

Field JSON baru `commercial_financials` (I4-FINANCIALS.1) berisi total nominal setiap bid dan shared PILOG, dihitung fungsi Decimal. `net_after_voyage_usd` adalah kontribusi setelah seluruh biaya model + komisi; **bukan** `baseline.net_revenue_usd` yang baru setelah komisi. Neto barang PI tidak dimodelkan, OE/HPS bukan HPP. Nilai CFR total bukan pendapatan tambahan di atas PI+PILOG. Pada NO GO angka positif tetap potensi jika terlaksana, bukan realisasi atau alasan melewati gate yang gagal.

Bahasa “simulasi/butuh audit/butuh pertimbangan” dipangkas dari brief utama; mode/source_status/synthetic/proxy/approval tetap utuh pada JSON/audit. Satu catatan basis estimasi dan kewenangan di brief menjaga makna angka. Perubahan tone bukan bukti siap transaksi atau izin MVP.

Untuk satu kasus:

```powershell
python -X utf8 -B scripts/run_iteration_04.py --case data/processed/i4_context.json
python -X utf8 -B scripts/run_iteration_04.py --case data/processed/i4_no_go.json
```

Hasil berada di `outputs/runs/i4_<timestamp>_<id>/`:

| File | Untuk apa |
|---|---|
| `commercial_decision_brief.md` | Baca pertama: keputusan, tabel cek, ekonomi, OD, risiko dan langkah manusia |
| `calculation_audit.md` | Semua bid/putaran, angka per skenario, asumsi, sumber dan hasil lengkap |
| `result.json` | Hasil terstruktur, rule/formula I4.1, alasan dan hash input |
| `input_snapshot/` | Salinan byte CSV + fixture yang benar-benar dipakai; dapat direplay |

`NO_GO / DATA_ISSUE` berarti belum aman memberi GO karena input tidak dapat dihitung, bukan keputusan bahwa buyer gagal ekonomi. CLI tetap menyimpan penjelasannya; periksa hasil, bukan hanya exit code proses. Run baru diabaikan Git agar repo tidak penuh output tes.

## Input yang dipakai

| Input | Isi dan cara eksperimen |
|---|---|
| `data/processed/i4_voyage.csv` | 26 field: rute/Q, profil, speed/fuel, rates pelabuhan, biaya dan komisi. Kolom sumber/asumsi/peran disertakan |
| `data/processed/i4_context.json` | Indeks, target TCE, OE/HPS, seluruh bid/alpha, cutoff, referensi OD, policy kelas dan stress; varian GO |
| `data/processed/i4_no_go.json` | Varian NO GO floor; merujuk CSV yang sama |
| `data/raw/` | Workbook asli dan register audit; **bukan input runtime yang dihitung ulang setiap run** |

Untuk mengubah alpha: edit `bids[].alpha_usd_mt` di JSON kasus yang dipilih, lalu jalankan kasus itu. Round/buyer/bid ID harus konsisten dan unik; bid terakhir per buyer yang masih berlaku pada cutoff yang dievaluasi. Tidak perlu mengisi `pi_selected_bid_id`; tanpa field itu sistem memberi kandidat ranking, bukan award otomatis. Pilihan PI opsional tetap harus eligible.

Kedua fixture default sekarang memiliki record `freight_tender`: **24,8957 USD/MT**, diturunkan Python dari pricing awal, bukan konstanta kode atau bukti persetujuan komersial. Semua buyer dan stress memakai rate yang sama. Perubahan biaya/target TCE tidak menimpa rate itu; perubahan biaya bisa membuat NO GO. Indikasi pricing pembanding tetap dihitung dan dicatat terpisah di audit.

Snapshot lama tanpa `freight_tender` masih didukung sebagai **indikasi model**, bukan harga tetap yang telah disetujui. Untuk menyiapkan salinan input menjadi kasus dengan harga tetap, tanpa membaca workbook/PDF:

```powershell
python -X utf8 -B scripts/prepare_iteration_04.py --from-case data/processed/i4_context.json --output-dir outputs/i4_prepared_experiment
python -X utf8 -B scripts/run_iteration_04.py --case outputs/i4_prepared_experiment/i4_context.json
```

Pilih folder tujuan baru; persiapan menolak overwrite. Record fixed yang sudah ada dipertahankan. Jika sengaja membuat **penawaran baru** dengan pricing baru, hapus `freight_tender` hanya pada salinan eksperimen sebelum persiapan. Jangan menghapusnya saat menguji kenaikan biaya pada tender yang harganya tetap. Tidak perlu mengetik rate hasil kalkulasi secara manual.

Jangan edit snapshot hasil lama. Salin kasus untuk eksperimen terpisah dan gunakan `--case`. Replay hasil lama memakai `--case <run>/input_snapshot/case_fixture.json`; CSV pendamping sudah tersedia di folder yang sama.

## Rumus dan gate

- Indeks = rata-rata midpoint dua laporan urea granular FOB SEA.
- FOB = indeks + alpha buyer sekali; CFR = FOB + freight tender tetap.
- Freight sistem = (bunker + port/other + target TCE × total hari) / (Q × (1 − total fraksi komisi)), dibulatkan **naik 4 desimal USD/MT**.
- Target TCE adalah net setelah voyage expenses/komisi, **sebelum running**; bukan biaya hire kapal milik.
- Kontribusi PILOG = revenue freight − komisi − bunker − port/other − running.
- **Gate A:** bid terakhir aktif pada cutoff + FOB ≥ OE/HPS; ranking kandidat untuk PI.
- **Gate B:** screen awal gross DWT/kelas + kontribusi baseline ≥ 0. Impas lolos; stress negatif dijelaskan, bukan otomatis veto.
- Gate A gagal → Gate B belum dievaluasi; angka ekonominya hanya indikatif. Outcome bisnis hanya GO/NO GO.

Brief menampilkan setiap latest bid (termasuk gagal) dengan alpha, FOB, **freight terlihat buyer**, CFR, gap **internal**, rank dan alasan. Audit memuat seluruh bid. Tindak lanjut berbeda menurut penyebab; tidak ada auto-award pada ranking/ties/pilihan PI.

Metrik tambahan: alpha floor = OE/HPS−indeks; freight impas = biaya kas sebelum komisi / [Q×(1−komisi)]; biaya tambahan port day = running/hari + DO pelabuhan/hari×harga DO; tambahan delay impas = kontribusi / biaya tambahan per hari pada baseline positif. Semua dihitung dalam fungsi Python. Metrik ini **bukan gate, SOP harga minimum atau SLA**; baseline rugi/tambahan biaya harian nol tidak menghasilkan buffer delay negatif/infinity.

## Batas data yang harus diketahui

- Argus PDF p2: SEA granular FOB 415–425; Fertecon PDF p1: SEA granular FOB 410–410, tanggal laporan 10 September 2026. Indeks kasus = **415 USD/MT**.
- Fearnpulse belum menghasilkan quote numerik terverifikasi. **Target TCE 13.000 USD/hari memakai AQABA L38 sebagai proxy simulasi historis**, bukan quote Fearnpulse atau biaya hire tambahan.
- Baltic Handysize 38 adalah benchmark, bukan kapal PILOG nyata. Rates/fuel pelabuhan, biaya dan komisi masih proxy/asumsi berlabel.
- **3.906 NM adalah referensi workbook**, belum diverifikasi independen. Tahun sumber berbeda boleh untuk simulasi; bukan bukti layak dipakai untuk penawaran aktual.
- OD asli tetap utuh: tarif untuk **satu pengiriman satu arah**, tetapi biaya internalnya memasukkan balik. Sistem I4 menghitung biaya satu arah. Selisih tarif **bukan margin/penghematan** dan OD bukan gate.
- Screen DWT belum membuktikan DWCC, terminal, draft, availability, laycan atau profit seluruh siklus kapal.

## Menyiapkan ulang input dari sumber

Engine/tes hanya membutuhkan pustaka standar. `openpyxl` dan `pypdf` diperlukan untuk skrip persiapan opsional:

```powershell
python -m pip install -r requirements.txt
python -X utf8 -B scripts/prepare_iteration_04.py --output-dir outputs/i4_inputs_rebuild
```

Skrip membaca workbook Voyage Estimate, OD dan dua PDF laporan di vault. Ia **menolak overwrite input yang sudah ada**, memeriksa hash workbook, mengekstrak persentase komisi/divisor rate dari rumus sumber tanpa mengeksekusi rumus Excel, dan menandai substitusi/asumsi. PDF dengan layout/seri berbeda perlu mapping baru; ini bukan importer semua laporan pasar.

## Peta modul

`scripts/run_iteration_04.py` → `orchestration/iteration_04.py` → `validation/iteration_04.py` + `models/iteration_04.py` → `calculations/{voyage_04,pricing_04,tender_04}.py` → `decisions/iteration_04.py` → `reporting/iteration_04.py`.

Semua berada di `src/pilog_cfr_dss/` kecuali entry point. Orchestrator mengurutkan proses; fungsi kalkulasi memakai Decimal; gate menerapkan aturan; renderer memformat hasil tanpa menghitung ekonomi.

## Histori dan batas publikasi

I2/I3 tetap tersedia untuk regresi, **bukan scope aktif**:

```powershell
python -X utf8 -B scripts/run_iteration_03.py
python -X utf8 -B scripts/run_iteration_02.py
```

I3 memakai kasus 45.000 MT Bontang–ECI serta indeks sintetis; I4 tidak menulis ulang histori tersebut. `data/` tetap hanya `raw/` dan `processed/`; input I2/I3 tidak dihapus karena dipakai regresi.

Tidak ada integrasi produksi, auto-award, hedge, quotation atau approval otomatis. Lifecycle: **Simulation → Iteration 1..N → Final Simulation Validation oleh mentor → pertimbangan MVP**. Tidak ada git add/commit/push dalam implementasi ini. Repo berisi data kerja; izin publikasi dan visibilitas tetap tanggung jawab pengguna/perusahaan.
