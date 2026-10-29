# Kontrak ekonomi voyage — revisi simulasi Iterasi 2

**Status:** aktif untuk simulasi pra-penawaran; belum menjadi kebijakan quotation atau transaksi. Sumber keputusan: D-016 sampai D-022 dalam `../DECISIONS.md`. Angka di `data/processed/dataset_ready.csv` adalah ground truth numerik **simulasi**, bukan validasi transaksi nyata.

## Price object, pihak, dan satuan

| Objek | Satuan | Definisi yang dipakai |
|---|---|---|
| Seller komoditas | entitas | Entitas PI Group, bukan PILOG. |
| Penyedia freight | entitas | PILOG menjual jasa pengangkutan dan menanggung biaya voyage relevan. |
| Index, Alpha | USD/MT | Input harga komoditas dan penyesuaian komersial manual. |
| FOB baseline | USD/MT | `Index + Alpha`; **bukan** profit komoditas PI Group. |
| Freight selling rate | USD/MT | Kolom `Freight rate` CSV; tarif jual jasa freight PILOG, bukan freight cost. |
| CFR indikatif | USD/MT | `FOB baseline + freight selling rate + satu adjustment CFR eksplisit`. Belum diuji terhadap buyer atau margin barang seller. |
| Cargo/DWCC | MT | `dwcc_cargo_quantity_mt`, 45.000 MT untuk **semua** hitungan berbasis kuantitas. |
| Gross freight revenue | USD | `freight selling rate × cargo MT`. |
| Freight cost | USD | Running kapal milik + bunker + `Other voyage costs total`, masing-masing sekali. |
| Komisi | USD | Tiga rate dataset × gross freight revenue; basis kumulatif gross adalah **asumsi simulasi**, perlu konfirmasi kontrak. |
| Kontribusi freight PILOG | USD | `gross freight revenue − komisi − freight cost`. Bukan laba bersih perusahaan atau margin komoditas. |

Baris Aqaba lama `Voyage expense allocation quantity = 46.000 MT` dinyatakan salah oleh mentor. Baris itu dihapus dari dataset/katalog aktif; snapshot run lama tetap historis. Tidak ada billable/allocation quantity kedua dalam kontrak ini. Hari pelabuhan = cargo MT ÷ rate muat/bongkar MT/hari. Freight cost per MT = freight cost total ÷ cargo MT.

## Batas biaya kapal milik

| Komponen | Perlakuan dalam simulasi |
|---|---|
| Hari voyage | Laden, ballast, muat, bongkar, dan canal days dari input kasus. |
| Bunker | Fuel oil dan diesel menurut konsumsi, hari, serta harga input. |
| Running cost | Hari voyage × owned running cost USD/hari. |
| Port/other | Agregat `Other voyage costs total` USD 200.000; mentor menyatakan terpisah dari bunker dan running. Rincian port/agency belum diketahui. |
| Hire dan `Daily cost assumption` | **Tidak** ditambahkan ke running cost kapal milik. |
| Charter | Ditunda; jangan menganggap struktur biaya owned sama dengan time/voyage charter. |

Jangan menambahkan port charge terpisah bila sudah berada di agregat tersebut. Adjustment CFR adalah perubahan harga jual yang dicatat sekali, bukan komponen biaya kedua. Tidak ada target minimum margin komersial yang disetujui sekarang. Kontribusi positif hanya memberi sinyal untuk review atasan; kontribusi nol/negatif tidak mendukung penawaran CFR pada harga yang sama.

## Gate dan keluaran

1. **Gate 1, pra-perhitungan:** cek input minimum, unit, nilai teknis, konteks seller/PILOG, dan penolakan CFR yang sudah diketahui. `buyer_not_approached` normal; metadata sumber dan approval formal menjadi WARN, bukan HOLD pada simulasi ini.
2. **Perhitungan deterministik:** fungsi Python `Decimal` membuat trace hari, konsumsi, biaya, harga, revenue, komisi, dan kontribusi. LLM tidak menghitung angka otoritatif.
3. **Screen kapal di dalam CFR:** Handysize 20–40 ribu DWT; Supramax 50–60 ribu DWT; DWT kasus 58 ribu. Cargo 45 ribu melampaui batas Handysize; Supramax lolos **screen gross-DWT awal** saja. DWCC aktual, bunker/constants allowance, draft, terminal, laycan, dan availability belum dibuktikan.
4. **Gate 2:** bila kontribusi freight positif dan screen awal lolos, keluarkan `CFR_CANDIDATE_PENDING_HUMAN_REVIEW`, bukan approval. Bila CFR tidak menarik/feasible tetapi profit FOB belum diketahui, keluarkan `DEFER_FOB_REVIEW`; jangan otomatis merekomendasikan FOB atau NO_BID. NO_BID hanya bila kedua alternatif terbukti tidak layak dengan kriteria yang disetujui.
5. **Handoff manusia:** atasan/PI seller memeriksa economics, harga, kapal, biaya, kewenangan, lalu baru dapat memutuskan pendekatan buyer. Sistem tidak mengirim quotation, melakukan fixture, atau write-back.

FOB dan CFR adalah dua alternatif komersial. Supramax/Handysize adalah sub-keputusan CFR; DEFER/NO_BID adalah outcome, bukan skenario harga.

## Pertanyaan mentor yang tetap terbuka

1. Apa biaya/margin komoditas PI Group dan kriteria untuk menilai ekonomi FOB?
2. Apakah semua tiga komisi berlaku kumulatif atas gross freight revenue dalam transaksi nyata?
3. Apa saja rincian `Other voyage costs total`, terutama port/agency/canal?
4. Kapan batas minimum kontribusi/margin komersial ditetapkan, setelah fase simulasi ini?
5. Kapan gross-DWT screen dinaikkan menjadi bukti kapasitas kapal aktual dan constraint terminal?
6. Bagaimana route Bontang–ECI, jarak, harga bunker, dan vessel availability divalidasi sebelum quotation?
