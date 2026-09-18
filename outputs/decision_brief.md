# Decision Brief — CFR DSS Simulation

> Status: SIMULATION / ADVISORY-ONLY
> 
> Dokumen ini memberikan rekomendasi simulasi beserta alasan dan audit perhitungannya.
> Belum ada keputusan komersial atau eksekusi otomatis.

## 1. Identitas Kasus

- Case ID: `CFR-SIM-BONTANG-ECI-001`
- Mode: `simulation`
- Status data: `advisory-only`
- Gate 1: `CFR_ELIGIBLE`
- Rekomendasi simulasi keseluruhan: **CFR_CONDITIONAL**
- Persetujuan manusia: **Wajib**

## 2. Ringkasan Rekomendasi

Rekomendasi sistem pada tahap simulasi adalah: **CFR_CONDITIONAL**.

Rekomendasi ini belum berarti transaksi harus langsung dilakukan. Business user tetap harus memvalidasi harga, freight, kapal, kontrak, risiko, dan persetujuan internal.

## 3. Detail Setiap Skenario

### 3.1 FOB baseline

- Scenario ID: `FOB-BASELINE`
- Sales term: `FOB`
- Vessel option: `N/A`
- Feasible: `True`
- Comparable: `True`
- Status perhitungan: `CALCULATED`
- Sumber/asumsi: commercial baseline

**Input yang digunakan:**

- Index: USD 250.00/MT
- Alpha: USD 3.00/MT
- Freight selling rate: N/A
- Freight cost: N/A
- Penyesuaian CFR: N/A

**Perhitungan:**

- FOB = Index + Alpha = USD 250.00/MT + USD 3.00/MT = USD 253.00/MT

**Hasil:**

- FOB: USD 253.00/MT
- CFR: N/A
- Freight margin: N/A

**Mengapa skenario ini mendapat status tersebut:**

- Skenario ditandai feasible berdasarkan input simulasi.
- Basis perbandingan dinyatakan comparable: route, tanggal, unit, dan batas biaya dianggap konsisten.
- Perhitungan harga berhasil dijalankan.
- FOB berfungsi sebagai baseline karena PILOG menyerahkan ocean freight kepada buyer.
- Hasil Gate 2: FOB_BASELINE.
- Gate 2: Scenario digunakan sebagai baseline.

**Catatan skenario:** Baseline tanpa ocean freight scope PILOG.

### 3.2 CFR dengan kapal PILOG

- Scenario ID: `CFR-PILOG-VESSEL`
- Sales term: `CFR`
- Vessel option: `PILOG vessel`
- Feasible: `True`
- Comparable: `False`
- Status perhitungan: `CALCULATED`
- Sumber/asumsi: demo assumption - replace with mentor-approved value

**Input yang digunakan:**

- Index: USD 250.00/MT
- Alpha: USD 3.00/MT
- Freight selling rate: USD 20.00/MT
- Freight cost: USD 18.00/MT
- Penyesuaian CFR: USD 0.00/MT

**Perhitungan:**

- FOB = Index + Alpha = USD 250.00/MT + USD 3.00/MT = USD 253.00/MT
- CFR = FOB + Freight selling rate + Adjustment = USD 253.00/MT + USD 20.00/MT + USD 0.00/MT = USD 273.00/MT
- Freight margin = Freight selling rate − Freight cost = USD 20.00/MT − USD 18.00/MT = USD 2.00/MT

**Hasil:**

- FOB: USD 253.00/MT
- CFR: USD 273.00/MT
- Freight margin: USD 2.00/MT

**Mengapa skenario ini mendapat status tersebut:**

- Skenario ditandai feasible berdasarkan input simulasi.
- Skenario belum comparable, sehingga tidak boleh menjadi dasar keputusan final.
- Perhitungan harga berhasil dijalankan.
- Freight margin positif sebesar USD 2.00/MT, sehingga freight menghasilkan kontribusi kotor positif.
- Hasil Gate 2: CFR_CONDITIONAL.
- Gate 2: Basis scenario belum comparable.

**Catatan skenario:** Angka hanya untuk menguji pipeline.

### 3.3 CFR dengan voyage charter

- Scenario ID: `CFR-VOYAGE-CHARTER`
- Sales term: `CFR`
- Vessel option: `Voyage charter`
- Feasible: `True`
- Comparable: `False`
- Status perhitungan: `CALCULATED`
- Sumber/asumsi: demo assumption - replace with mentor-approved value

**Input yang digunakan:**

- Index: USD 250.00/MT
- Alpha: USD 3.00/MT
- Freight selling rate: USD 27.00/MT
- Freight cost: USD 24.00/MT
- Penyesuaian CFR: USD 0.00/MT

**Perhitungan:**

- FOB = Index + Alpha = USD 250.00/MT + USD 3.00/MT = USD 253.00/MT
- CFR = FOB + Freight selling rate + Adjustment = USD 253.00/MT + USD 27.00/MT + USD 0.00/MT = USD 280.00/MT
- Freight margin = Freight selling rate − Freight cost = USD 27.00/MT − USD 24.00/MT = USD 3.00/MT

**Hasil:**

- FOB: USD 253.00/MT
- CFR: USD 280.00/MT
- Freight margin: USD 3.00/MT

**Mengapa skenario ini mendapat status tersebut:**

- Skenario ditandai feasible berdasarkan input simulasi.
- Skenario belum comparable, sehingga tidak boleh menjadi dasar keputusan final.
- Perhitungan harga berhasil dijalankan.
- Freight margin positif sebesar USD 3.00/MT, sehingga freight menghasilkan kontribusi kotor positif.
- Hasil Gate 2: CFR_CONDITIONAL.
- Gate 2: Basis scenario belum comparable.

**Catatan skenario:** Angka hanya untuk menguji pipeline.

### 3.4 Defer atau no-bid

- Scenario ID: `DEFER-NO-BID`
- Sales term: `DEFER`
- Vessel option: `N/A`
- Feasible: `False`
- Comparable: `False`
- Status perhitungan: `BLOCKED`
- Sumber/asumsi: decision option

**Input yang digunakan:**

- Index: N/A
- Alpha: N/A
- Freight selling rate: N/A
- Freight cost: N/A
- Penyesuaian CFR: N/A

**Perhitungan:**

- FOB = Index + Alpha = N/A + N/A = N/A

**Hasil:**

- FOB: N/A
- CFR: N/A
- Freight margin: N/A

**Mengapa skenario ini mendapat status tersebut:**

- Skenario tidak feasible atau memenuhi persyaratan operasional.
- Skenario belum comparable, sehingga tidak boleh menjadi dasar keputusan final.
- Perhitungan belum lengkap dengan status BLOCKED.
- Alasan pemblokiran: Freight selling rate belum tersedia.
- Hasil Gate 2: INFEASIBLE.
- Gate 2: Scenario ditandai tidak feasible.

**Catatan skenario:** Dipakai bila data atau kelayakan tidak cukup.

## 4. Cara Membaca Rekomendasi

Sistem tidak memilih skenario hanya karena harga CFR paling tinggi.Skenario harus memenuhi urutan berikut:

1. Data wajib tersedia dan lolos pemeriksaan kualitas.
2. Skenario feasible secara operasional.
3. Basis perbandingan comparable.
4. FOB dan CFR dihitung dengan unit serta batas biaya yang sama.
5. Freight margin dan risiko diperiksa.
6. Gate 1 dan Gate 2 memberikan status yang dapat diterima.
7. Business user memberikan persetujuan manusia.

## 5. Batasan dan Asumsi

- Laporan ini adalah hasil simulasi, bukan keputusan komersial final.
- Nilai demo harus diganti dengan data tervalidasi dari sumber resmi.
- Skenario comparable=false tidak boleh digunakan untuk keputusan final.
- Tidak ada kontrak, booking kapal, hedging, atau transaksi yang dieksekusi.

## 6. Status Implementasi

- Ini masih **simulation build**.
- Script hanya menyusun analisis dan decision brief.
- Belum ada koneksi otomatis ke Fleetra, Procurex, SAP, atau sistem eksternal.
- Belum ada booking kapal, penerbitan kontrak, hedging, atau pengiriman instruksi transaksi.
- Field `choice_made` tetap `false` sampai ada proses persetujuan manusia.
