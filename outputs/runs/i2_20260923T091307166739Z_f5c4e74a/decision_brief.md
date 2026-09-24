# Decision Brief — Simulation Iteration 2 Revision

- Case ID: `I2-PRE-OFFER-45K`
- Tahap: `pre_offer`; respons buyer: `not_approached`
- Mode: `simulation` / `advisory-only`
- Gate 1: **CFR_ELIGIBLE**
- Gate 2: **CFR_CANDIDATE_PENDING_HUMAN_REVIEW**
- Rekomendasi: **CFR_CANDIDATE_PENDING_HUMAN_REVIEW**
- Approval: **PENDING_HUMAN_REVIEW** — sistem tidak mengirim quote atau melakukan fixture.

## Mengapa dan apa berikutnya

- `PRELIMINARY_DWT_SCREEN_PASS`
- `POSITIVE_PILOG_FREIGHT_CONTRIBUTION`
- `SIMULATION_ASSUMPTIONS_PRESENT`
- `FOB_COMMODITY_PROFIT_NOT_ASSESSED`

**Langkah berikutnya:** Validasi kapal, biaya, harga, dan kewenangan dengan atasan/PI seller; baru setelah disetujui dekati buyer.

## Konteks transaksi dan basis angka

- Seller komoditas: PI Group entity; penyedia jasa freight: PILOG.
- Rute: Bontang → ECI.
- Cargo/DWCC tunggal: **45,000.0000 MT** untuk waktu pelabuhan, screen DWT, freight revenue, komisi, dan biaya per MT.
- Angka 46.000 MT dari input Aqaba lama tidak dipakai dan tidak ada voyage expense allocation quantity dalam kontrak simulasi ini.

## Harga komoditas dan indikasi CFR

- Index: 250.0000 USD/MT; Alpha: 3.0000 USD/MT.
- FOB baseline = Index + Alpha: **253.0000 USD/MT**.
- Tarif jual freight PILOG: 20.0000 USD/MT.
- CFR adjustment: 0.0000 USD/MT.
- CFR indikatif: **273.0000 USD/MT**.
- Harga FOB bukan profit barang PI Group. CFR indikatif belum diuji terhadap willingness-to-pay buyer atau margin komoditas seller.

## Screen kelas kapal — DWT saja

- Versi kebijakan: `I2-R2-DWT-1`.
- Handysize: rentang 20,000.0000 MT–40,000.0000 MT; DWT kapal kasus 58,000.0000 MT; cargo 45,000.0000 MT; hasil `FAIL` (`CARGO_EXCEEDS_CLASS_MAX_DWT`).
- Supramax: rentang 50,000.0000 MT–60,000.0000 MT; DWT kapal kasus 58,000.0000 MT; cargo 45,000.0000 MT; hasil `PASS` (`PRELIMINARY_DWT_SCREEN_PASS`).
- Kandidat kelas dalam CFR: **Supramax**.
- PASS DWT belum membuktikan DWCC aktual, draft, batas terminal, laycan, atau ketersediaan kapal.

## Perhitungan fisik — hasil Python

- laden_sea_days: **6.0863 day** — `distance_nm / (speed_knots * 24)`.
- ballast_sea_days: **15.3333 day** — `distance_nm / (speed_knots * 24)`.
- loading_days: **4.5000 day** — `cargo_mt / loading_rate_mt_day`.
- discharge_days: **7.5000 day** — `cargo_mt / discharge_rate_mt_day`.
- canal_days: **0.0000 day** — `dataset input`.
- total_voyage_days: **33.4196 day** — `sum(laden sea, ballast sea, loading, discharge, canal)`.
- fuel_oil_laden_mt: **176.5030 MT** — `laden_sea_days * fuel_oil_consumption_laden_mt_day`.
- fuel_oil_ballast_mt: **383.3333 MT** — `ballast_sea_days * fuel_oil_consumption_ballast_mt_day`.
- diesel_laden_sea_mt: **0.6086 MT** — `laden_sea_days * diesel_consumption_at_sea_laden_mt_day`.
- diesel_ballast_sea_mt: **1.5333 MT** — `ballast_sea_days * diesel_consumption_at_sea_ballast_mt_day`.
- diesel_port_mt: **40.3200 MT** — `port_days * 24 * power_kw * load_factor * kg_kwh / 1000`.
- fuel_oil_sea_cost_usd: **317,987.0238 USD** — `(fuel_oil_laden_mt + fuel_oil_ballast_mt) * fuel_oil_price_usd_mt`.
- diesel_sea_and_port_cost_usd: **29,765.8370 USD** — `(diesel_laden_sea_mt + diesel_ballast_sea_mt + diesel_port_mt) * diesel_oil_price_usd_mt`.

## Ekonomi jasa freight PILOG — hasil Python

- Basis cargo: **45,000.0000 MT**.
- Total hari voyage: **33.4196 hari**.
- Running cost kapal milik: **187,551.0357 USD**.
- Fuel oil cost: **317,987.0238 USD**.
- Diesel cost: **29,765.8370 USD**.
- Total bunker: **347,752.8608 USD**.
- Port/other aggregate: **200,000.0000 USD**.
- Total freight cost: **735,303.8965 USD**.
- Freight cost per MT: **16.3401 USD/MT**.
- Tarif jual freight: **20.0000 USD/MT**.
- Gross freight revenue: **900,000.0000 USD**.
- Komisi freight_commission: 22,500.0000 USD.
- Komisi broker_fee: 11,250.0000 USD.
- Komisi additional_commission: 22,500.0000 USD.
- Total komisi: **56,250.0000 USD**.
- Kontribusi freight PILOG: **108,446.1035 USD**.
- Kontribusi ini bukan laba bersih PILOG atau margin barang PI Group; minimum margin komersial belum ditetapkan.

### Rumus yang dieksekusi

- running: `total voyage days * owned running cost USD/day`.
- bunker: `fuel oil cost + diesel oil cost`.
- total_cost: `owned running + bunker + port/other aggregate`.
- revenue: `freight selling rate USD/MT * DWCC cargo MT`.
- commission: `gross freight revenue * sum(three commission fractions)`.
- contribution: `gross freight revenue - commission - total cost`.
- cfr: `FOB + freight selling rate + one explicit adjustment`.

## Perbandingan alternatif komersial

- `FOB-BASELINE`: **PRICE_BASELINE_ONLY**; alasan: FOB_PRICE_AVAILABLE_NOT_PROFIT, FOB_COMMODITY_PROFIT_NOT_ASSESSED.
- `CFR-PILOG`: **POSITIVE_FREIGHT_CONTRIBUTION_FOR_REVIEW**; alasan: CLASS_SELECTED_BY_GROSS_DWT:Supramax, ACTUAL_CARGO_CAPACITY_NOT_PROVEN, CALCULATED_FROM_DATASET_SIMULATION_BOUNDARY.
- FOB adalah baseline harga; profitabilitas PI seller belum tersedia. Kapal adalah sub-keputusan CFR, bukan skenario komersial tambahan.

## Mutu data dan batas kepercayaan

- Status quality: `WARN`.
- `SOURCE_METADATA_DEFERRED`: WARN; field: source, as_of, owner; Sumber/as-of/approval domain belum menjadi Gate pada simulasi ini.
- Port diesel follows the dataset factor; confirm engine and port-operation basis.
- Fuel oil at loading/discharging port is excluded until its stock-versus-consumption meaning is confirmed.
- Vessel choice uses a separate gross-DWT-only screen; bunker/constants allowance, draft, stowage, terminal constraints, and actual availability are not proven.
- No hire, running cost, port tariff, aggregate other cost, or commission is added to this physical estimate.
- Asumsi: CSV values are one experimental case; Bontang-to-ECI route inputs are not validated transaction data.
- Asumsi: Buyer has not been approached; no offer, acceptance, or sale contract is assumed.
- Asumsi: PILOG-owned/operated vessel is the only cost mode in this revision.
- Asumsi: Three commission rates are applied cumulatively to gross freight revenue as a simulation assumption.
- Asumsi: Other voyage costs aggregate excludes bunker and running cost; port and agency breakdown remains unconfirmed.
- Asumsi: DWT-only screening is preliminary; actual cargo capacity, vessel availability, draft, terminal and laycan remain for human review.
- Asumsi: Positive freight contribution is a review signal, not an approved minimum margin or evidence of PI Group commodity profit.
- Belum diputuskan: `FOB_COMMODITY_COST_AND_MARGIN`.
- Belum diputuskan: `MINIMUM_COMMERCIAL_MARGIN_DEFERRED`.
- Belum diputuskan: `COMMISSION_CONTRACT_BASIS`.
- Belum diputuskan: `OTHER_VOYAGE_COST_BREAKDOWN`.
- Belum diputuskan: `ACTUAL_VESSEL_AVAILABILITY_AND_SAFE_LOADING`.

## Jejak run

- Dataset SHA-256: `f5c4e74a4f9395da0bfd4814bf9de23e4ca5e56a6941e0c8070fd0b9f4a7c9bb`.
- Catalog SHA-256: `5989760a7b3503276c541ea1facdc9c0987329cf3d5dbc67cfdaa57dbaf5572b`.
- Manual input SHA-256: `11ce94779e42761340e4362fa677be1fb6957066ef312a120f3ae42c32321c90`.
- Vessel policy SHA-256: `3589118a094d977e895b5c67838fce1eead6c26c87b2e3b901430b74d7a6c5e0`.
- Formula version: `I2.R2.1`; rule version: `I2.R2.1`.
- Snapshot dataset: `input_snapshot/dataset.csv`.
- Snapshot catalog: `input_snapshot/catalog.csv`.
- Snapshot manual: `input_snapshot/manual.json`.
- Snapshot vessel_policy: `input_snapshot/vessel_policy.json`.

Hasil ini simulasi untuk review mentor/atasan; bukan quote, approval, fixture, atau transaksi otomatis.
