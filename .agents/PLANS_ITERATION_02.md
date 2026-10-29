# Rencana aktif revisi simulasi Iterasi 2 — keputusan FOB vs CFR pra-penawaran

**Status:** R01–R06 telah diimplementasikan dan diuji secara teknis pada 23 September 2026; keputusan penerimaan mentor masih menunggu review. Arahan bisnis berasal dari pengguna setelah diskusi dengan mentor. Setelah cleanup repo 24 September, hanya satu contoh run revisi yang dipertahankan; ringkasan hasil lama tetap tertulis dalam review/decision log.

## 1. Tujuan dan batas keputusan

Sebelum buyer didekati, hitung terlebih dahulu apakah PILOG punya peluang freight CFR yang menarik untuk dibawa ke review Commercial. Entitas PI Group menjual komoditas; PILOG menyediakan dan menjual jasa freight serta menanggung biaya voyage yang relevan. Sistem hanya menghasilkan rekomendasi simulasi beserta alasan dan trace, bukan mengirim penawaran, melakukan fixture, atau memberi approval.

Alternatif **komersial** hanya dua: **FOB** dan **CFR**. `NO_BID`/`DEFER` adalah tindakan akhir bila keduanya tidak layak atau bukti belum cukup; keduanya bukan skenario penjualan ketiga. Pilihan Supramax/Handysize adalah **sub-keputusan kapal di dalam CFR**, bukan empat skenario komersial terpisah. Untuk iterasi ini kapal diasumsikan milik/dioperasikan PILOG; charter ditunda.

## 2. Kontrak input yang sudah dikoreksi

| Objek | Aturan aktif untuk rancangan revisi |
|---|---|
| `data/processed/dataset_ready.csv` | Contoh angka satu kasus simulasi, bukan data produksi tervalidasi. Mentor menangani pengelompokan, provenance, freshness, dan approval sumber di tahap lanjut. Cek teknis yang diperlukan untuk menghitung tetap berlaku. |
| Cargo / DWCC | **45.000 MT untuk seluruh perhitungan**: hari pelabuhan, screen kapasitas, freight revenue, komisi, dan biaya per MT. Ini kuantitas kargo yang dibatasi seller. |
| Angka 46.000 MT | Baris `Voyage expense allocation quantity` pada data Aqaba keliru menurut mentor. **Tidak ada objek allocation quantity** dalam kasus PILOG ini. Dataset dan model aktif menghapus/menolak baris itu; run lama telah dibersihkan atas instruksi pengguna, sedangkan perbedaan basisnya dicatat dalam review/decision log. |
| Harga | `FOB = Index + Alpha`; `CFR indikatif = FOB + freight selling rate PILOG + adjustment`, dengan unit USD/MT dan adjustment eksplisit. Harga FOB/CFR ditampilkan, bukan bukti margin komoditas PI Group. |
| Biaya | PILOG menanggung biaya voyage relevan seperti bunker, port, running cost, dan biaya lain. Semua komponen yang berlaku harus masuk **sekali**; biaya tidak diabaikan hanya karena sudah ditangani PILOG. Untuk kapal milik, jangan sekaligus memakai hire, `Daily cost assumption`, dan running cost sebagai mekanisme harian ganda. Cakupan agregat `Other voyage costs total` ditampilkan agar port tidak dihitung dua kali. |
| Tujuan ekonomi | Kontribusi freight PILOG = freight revenue − komisi yang berlaku − biaya freight/voyage relevan. Ini bukan laba perusahaan penuh. **Minimum margin komersial belum ditetapkan**; jangan menyamakan kontribusi positif dengan approval untuk menawarkan harga. |

Komisi yang tersedia di CSV tetap ditunjukkan satu per satu; penerapan ketiganya pada gross freight revenue merupakan asumsi simulasi yang harus terlihat pada output, sampai basis kontraknya dikonfirmasi.

## 3. Gate dan pilihan yang diusulkan

```text
Peluang ekspor pra-penawaran + cargo 45.000 MT
  -> input CSV terkoreksi + Index/Alpha/adjustment manual
  -> Gate 1: data minimum dapat dihitung? ruang lingkup CFR mungkin?
  -> FOB: tampilkan harga baseline; kelayakan margin barang belum diketahui
  -> CFR: screen kelas kapal berdasarkan DWT -> hitung ekonomi freight PILOG
  -> Gate 2: bandingkan bukti FOB dan CFR yang benar-benar tersedia
  -> kandidat CFR / review FOB / DEFER / NO_BID, dengan alasan dan next action
  -> validasi atasan; baru kemudian pendekatan buyer
```

**Gate 1** tidak mensyaratkan buyer sudah menerima CFR. `buyer_not_approached` normal untuk pra-penawaran; penolakan CFR yang sudah diketahui tetap relevan. Pemeriksaan asal data, tanggal sumber, sistem Fleetra/SAP/AIS, dan approval formal ditunda untuk simulasi ini. Input angka/unit yang hilang atau mustahil, pembagi nol, dan formula tidak konsisten tetap tidak boleh diloloskan.

**Gate 2** tidak memakai minimum margin bisnis yang belum ada. Kontribusi CFR yang positif adalah sinyal untuk **review**, bukan keputusan otomatis bahwa CFR “menarik” secara komersial. Kontribusi nol/negatif tidak boleh menghasilkan rekomendasi menawarkan CFR pada harga yang sama. FOB tidak boleh diklaim “menguntungkan” hanya dari harga `Index + Alpha`: biaya/margin komoditas PI Group tidak tersedia dalam dataset. Jika CFR gagal dan ekonomi FOB belum diketahui, hasil aman adalah `DEFER_FOB_REVIEW`, bukan otomatis `FOB_RECOMMENDED` atau `NO_BID`. `NO_BID` hanya bila dua alternatif terbukti tidak layak menurut kriteria yang disetujui. Definisi ekonomi FOB ini adalah pertanyaan terbuka untuk mentor.

## 4. Pilihan kapal: DWT-only pada iterasi ini

Gunakan rentang proyek Handysize 20.000–40.000 DWT dan Supramax 50.000–60.000 DWT sebagai konfigurasi referensi berversi. DWT kasus di CSV adalah **58.000 MT**; `Reference DWT 63.500 MT` adalah kapal benchmark Baltic, bukan kapal kasus. Kargo 45.000 MT melampaui bahkan batas atas DWT Handysize, sehingga Handysize gagal screen awal. Supramax 58.000 DWT lolos **screen DWT awal**; itu belum membuktikan kapasitas muat aktual, ketersediaan kapal, draft, atau kesesuaian terminal.

Dataset juga memuat bunkers allowance 1.800 MT dan constants allowance 500 MT. Dua angka ini berguna untuk pemeriksaan deadweight/cargo yang lebih realistis **di iterasi selanjutnya**; jangan diam-diam memasukkannya ke aturan DWT-only yang disepakati sekarang. Speed dan tabel konsumsi MFO pada 11–14 knot berguna untuk simulasi waktu/bunker; draft, LOA, beam, grain/bale capacity, hold/hatch, crane, dan grab berguna bila kelak ada data pelabuhan dan karakteristik kargo yang cocok. Semua spesifikasi itu harus dibedakan antara kapal kasus dan kapal referensi Baltic.

## 5. Pelaksanaan rencana yang disetujui

| Urutan | Task | Hasil yang harus dibuktikan |
|---|---|---|
| 1 | I2-R01 | Kontrak 45.000 MT tunggal; buang/isolasi baris 46.000 MT yang salah dari dataset siap pakai dan model; keputusan koreksi historis tetap terlacak di log. |
| 2 | I2-R02 | Model dua alternatif FOB/CFR; screen DWT Handysize/Supramax hanya di cabang CFR; tidak membuat empat skenario komersial. |
| 3 | I2-R03 | Gate 1 pra-penawaran menerima buyer belum didekati dan memeriksa hanya syarat teknis minimum yang relevan untuk simulasi. |
| 4 | I2-R04 | Modul Python `Decimal` menghitung hari, bunker, biaya, revenue, komisi, kontribusi, dan FOB/CFR indikatif dari 45.000 MT serta menyajikan trace. |
| 5 | I2-R05 | Gate 2 dan decision brief memberi pilihan bersyarat, sebab, penjelasan angka, risiko/asumsi, serta tindakan manusia berikutnya. |
| 6 | I2-R06 | Tes unit, failure cases, run E2E, review mentor, dan catatan iterasi; tidak naik ke MVP hanya karena tes hijau. |

**Hasil demo E2E:** kasus dari CSV terkoreksi berjalan sampai brief tanpa HOLD akibat buyer belum didekati atau metadata/approval sumber yang ditunda. Gate tetap menahan input teknis yang rusak. Brief menunjukkan harga FOB/CFR, vessel-class screen, semua biaya relevan tanpa double count, freight revenue, komisi, kontribusi PILOG, alasan keputusan, status advisory-only, dan kebutuhan validasi atasan. Bukti yang dipertahankan: `outputs/runs/i2_20260923T091307166739Z_f5c4e74a/`; run pra-revisi telah dibersihkan pada 24 September.

## 6. Pertanyaan yang masih perlu konfirmasi mentor

1. Apa ukuran dan data yang diperlukan untuk menyebut **FOB** menarik/tidak menarik bagi PI Group? Tanpanya sistem hanya bisa menampilkan FOB sebagai baseline dan menyerahkan review.
2. Selain kontribusi positif, kondisi apa yang membuat CFR cukup menarik untuk diajukan? Minimum margin komersial secara eksplisit **ditunda**.
3. Apakah tiga jenis komisi seluruhnya berlaku pada satu transaksi, dan apakah semuanya berbasis gross freight revenue?
4. Komponen tepat apa yang telah masuk `Other voyage costs total` USD 200.000, terutama port/agency, agar biaya port tidak diduplikasi?
5. Pada tahap berikutnya, kapan screen DWT harus dinaikkan ke DWCC riil setelah bunker/constants, draft, gear, serta batas terminal?

Selama jawaban 1–2 belum ada, rekomendasi adalah **kandidat untuk review manusia**, bukan klaim optimalitas/approval komersial. Pengelompokan sumber data, integrasi, freshness, dan approval formal adalah pekerjaan lanjutan mentor domain.
