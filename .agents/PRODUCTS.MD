# Product Charter - PILOG CFR DSS

## Tahap berikutnya — I5 demo web untuk 1–3 pengguna

Kebutuhan terkonfirmasi: aplikasi dapat dibuka dari luar kantor dan membuat/mengubah kasus, tanpa server yang sudah tersedia. Audiens awal mentor dan demonstrasi PIHC. Rekomendasi plan I5 disederhanakan menjadi satu URL HTTPS: React build + FastAPI/engine accepted dalam satu web service, managed PostgreSQL dan akun demo terbatas. Render + Neon kandidat, bukan keputusan provider. GitHub Pages dapat menjadi frontend alternatif, tidak menjalankan Python/backend dan tidak membuat materi internal aman hanya karena repo private.

Pertahankan keputusan/presisi/fixed quote/UX I4; fokus pada akses, persistence, revision, izin dan unduhan. SSO/RBAC enterprise, live auction dan high availability bukan syarat demo kecil. Kotretan pengguna akan diunggah; anggaran/provider belum final. I5 masih plan, belum implementasi/deploy atau produksi/MVP penuh. Memindahkan stack bukan syarat dasar akses browser maupun bukti skalabilitas.

## Mentor menerima I4 — D-070, 28 Oktober

I4 diterima penuh menurut konfirmasi pengguna. Kebutuhan berikutnya adalah aplikasi dapat digunakan dari laptop mentor melalui deployment; porting/deployment disebut Iterasi 5. Mulai dari perencanaan akses bersama dan API/UI dengan engine tetap, bukan otomatis tender/award/produksi penuh. Tidak ada penggantian otomatis kerugian freight dari PI. FOB >= OE/HPS adalah floor barang; kontribusi freight PILOG dinilai Gate B.

## Kejelasan alur dan cakupan analisis — D-066/D-067

Kebingungan pengguna berulang diselesaikan lewat struktur UI: pilih profil sekali di Step 1, lihat sumber yang dipasangkan, lalu lihat kebutuhan/biaya/hasil di Step 2. Rute/jarak OD, profil fisik workbook, target pasar kapal, harga bunker Singapura dan indeks urea SEA memiliki peran berbeda. Effective values manual/reforecast tidak boleh tampil seolah tetap observasi pasar. Pemilih tetap profil perhitungan, bukan kapal aktual yang dijamin tersedia.

Exposure/risiko/dampak logistik/konsekuensi harga adalah ringkasan dasar existing untuk pengembangan lanjutan; tidak menyatakan full risk/exposure, probabilitas/hedging, scheduling/terminal readiness atau optimizer sudah tersedia. UI dirapikan tanpa memperluas model. Copy berulang yang diminta pengguna dihapus, sumber/unit/date/proxy tetap. Bukti tes bukan bukti seluruh stakeholder telah mengerti atau acceptance MVP; langkah berikutnya review pemakaian nyata pengguna.

## Penguatan keputusan ekonomi — D-064/D-065, 28 Oktober

Produk harus menjawab dua kepentingan terpisah: **harga barang PI memenuhi OE/HPS** dan **freight PILOG menutup biaya yang dimodelkan**. Bid tertinggi bukan bukti laba PILOG. I4-BRIEF.7 sekarang menjelaskan GO/floor NO GO/economic NO GO, penyebab perubahan kontribusi, opsi pemulihan dan risiko gabungan; penawaran tetap tidak direprice otomatis saat biaya berubah.

Benchmark pasar, target hasil harian, indikasi tarif dan harga penawaran adalah empat objek berbeda. Target-derived freight belum membuktikan daya saing atau penerimaan buyer. Cost reforecast beralasan mempertahankan quote/bid/base inputs; penawaran baru memerlukan revisi eksplisit. Perbandingan kapal pada freight sama dan kontribusi per hari membantu review tanpa menyatakan kapal tersedia atau otomatis memilih kapal.

Selesai teknis bukan acceptance manusia. Reader test tetap perlu memastikan stakeholder dapat menyebut keputusan, alasan, hasil neto PILOG, risiko utama dan tindakan berikutnya. Nilai produk diuji melalui keputusan yang dapat dijelaskan, bukan persentase GO yang diperbanyak. Lifecycle tetap Simulation → Iteration 1..N → Final Simulation Validation → MVP. RBAC per peran tetap kebutuhan tahap mendatang.

## Kebutuhan dashboard per peran dan koreksi D-061

Dashboard RBAC per peran adalah arah produk untuk iterasi mendatang (kemungkinan I5); role resmi, matriks akses, identitas dan kontrol export/backend belum ditentukan atau dibangun. Revisi I4 sudah dilaksanakan sesuai D-062/D-063: tiga komisi 0%, OD hanya jarak NM, kartu tender per putaran dengan harga FOB/CFR turunan, profil fisik versus benchmark jelas, copy ringkas dan logo asli. Gate A/B atau award authority tidak berubah. Plan §7.13/review memuat bukti 200 tes dan browser smoke; acceptance pengguna tetap diperlukan.

## Revisi sumber/UI D-059/D-060 — 27 Oktober

Empat profil workbook sampai Supramax dapat dipilih/dibandingkan, dan pasar Fearnpulse memasok acuan TC/bunker yang ditampilkan dengan tanggal. Profil Godau Handymax memakai proxy pasar kelompok kecil yang dinyatakan; tidak ada quote/profil rekaan. Dua kartu sumber, tabel, timestamps dan putaran 180 detik tetap membantu transparansi trader/operator. UI bukan e-auction, RBAC atau pelaksana transaksi; manusia tetap memilih kapal/award. 180 tes dan browser smoke adalah evidence teknis, bukan acceptance pengguna atau MVP. Source freshness tidak menjadi hard gate baru; source date/fetch time tidak disamakan. Plan §7.12.10 merangkum asumsi yang masih melekat.

## Dialog pengguna I4 — UI lokal, D-056/D-057

Pengguna menyetujui implementasi UI sederhana mengikuti referensi biru-putih. UI kini memperlihatkan data/profil → voyage/pricing → freight tetap → tender → GO/NO GO dan brief. Pilihan kapal manual dan transparan; Handysize siap, belum ada profil Supramax I4 lengkap atau auto-optimizer. UI mendukung eksperimen/review mentor, bukan buyer auction, award, transaksi atau integrasi Fleetra. 151 tes dan browser smoke lulus; penerimaan pengguna/mentor masih diperlukan. Lifecycle tetap Simulation → Iteration 1..N → Final Simulation Validation → MVP, tidak naik otomatis karena UI tersedia.

## Output terkini — D-053, stakeholder brief lima bagian

I4-BRIEF.4/123 tes: keputusan utama menampilkan gross PI/PILOG terpisah, biaya voyage/komisi, hasil neto PILOG; exposure, risk, logistics impact dan pricing consequences mendukungnya. Ini adaptasi struktur informasi ADMISI, bukan klaim integrasi/AI majalah sudah dibangun. Neto PILOG adalah kontribusi dalam cakupan biaya, bukan laba bersih; neto PI tidak dihitung dan OE/HPS bukan HPP. Penawaran CFR total bukan revenue tambahan di atas PI+PILOG. NO GO tetap menolak walau potensi freight positif; tabel diberi “jika terlaksana”. Bahasa brief langsung, sumber/mode/approval tetap benar di evidence. Gate/input/OD tidak berubah, UI/MVP belum dibangun; acceptance mentor tetap pending. Detail pada current-reader/review/plan §7.10.

## Penguatan output terkini — 23 Oktober 2026, D-051

I4-C1..C5 selesai teknis dengan I4-BRIEF.3 dan 109 tes lulus. Dua brief terbaru menamai lot/kandidat, membedakan manfaat PI versus PILOG, meminta hasil review dan trigger, serta menyatakan unknown dan metadata run. NO GO floor tidak tertutup ekonomi positif diagnostik; GO tetap mengungkap stress rugi. Rule I4.1 dan metrics I4-METRICS.1, dataset dan fixed freight tidak berubah. Bukti dan rating subjektif ada pada review I4; mentor belum menerima, UI/MVP tidak dibangun. Bagian revisi R berikut adalah histori versi sebelumnya.

## Kontrak output revisi — 23 Oktober 2026

Revisi I4 sesuai D-048 telah diimplementasikan dan diuji (91/91 tes); bukan iterasi baru. Buyer mengetahui freight tetap, sehingga tabel latest/all-bid internal memperlihatkan freight bersama alpha/FOB/CFR/rank/status. **OE/HPS, gap FOB−OE/HPS, alpha minimum, bid buyer lain dan ekonomi PILOG hanya internal PI/PILOG**, bukan tampilan/export buyer. Label internal belum berarti access control produksi.

Brief I4-BRIEF.2 menjelaskan asal fixed simulation versus indikasi model, buffer impas, tindakan per penyebab dan batas operasi; Gate A/B/threshold tetap. Metrik bukan minimum margin atau SLA. Harga tetap default diturunkan pricing, bukan bukti approval komersial. Plan §7–9/task/review menjadi acuan. Bukti 67 tes di bagian baseline berikut historis; mentor belum menerima revisi dan MVP tidak diizinkan.

## Kontrak produk aktif — Iterasi 4, 22 Oktober 2026

Bagian ini mengendalikan scope aktif. Bagian charter lama di bawah dipertahankan sebagai histori I1/I2, **bukan alternatif aturan I4**. Acuan: `docs/it_4/ITERATION_04_PLAN.md`, `.agents/reviews/ITERATION_04.md`, keputusan D-042..D-046.

- PI Group menjual barang melalui push-demand tender; PILOG menyediakan freight. Sistem menyiapkan ekonomi freight, menghitung seluruh bid, memberi ranking kandidat dan rekomendasi **GO/NO GO CFR**, bukan award otomatis atau fallback profit FOB.
- Kasus contoh: urea granular bulk, 30.000 MT, Handysize milik, Bontang–Mundra/WCI, satu arah laden-only termasuk muat/bongkar. Bukan model charter/tanker/gas.
- FOB = indeks + alpha sekali; CFR = FOB + freight tetap. Buyer melihat freight dan hanya menawar alpha. Tidak ada adjustment/beta tersembunyi.
- Gate A: bid terakhir aktif pada cutoff kasus dan FOB ≥ OE/HPS; PI selection opsional tetap harus valid. Gate B: screen gross DWT + kontribusi baseline ≥ 0; nol diterima. Stress negatif dijelaskan, bukan veto.
- Kesalahan input kritis menghasilkan NO_GO/DATA_ISSUE, bukan outcome HOLD ketiga. Tanggal sumber boleh berbeda untuk simulasi; unit/produk/basis/numerik tetap diperiksa. Tidak menambah hard gate freshness, authority, laycan atau minimum margin yang belum diminta.
- Tarif OD satu pengiriman satu arah; biaya internalnya mencakup balik. Sistem biaya satu arah; pembanding informatif, bukan gate/margin/penghematan. OD tidak diedit.
- Freight dihitung deterministik dari target TCE net setelah voyage expenses/komisi sebelum running; target tidak menjadi biaya hire. Running dikurangkan pada kontribusi. Seluruh angka Python/Decimal, bukan LLM.
- Nilai aktual dari dua laporan indeks dipisahkan dari OE/HPS/bid/stress sintetis dan proxy operasional. Fearnpulse quote belum terverifikasi; AQABA L38 hanya proxy target TCE berlabel. GO bukan keuntungan aktual/approval dan tidak membuktikan profit siklus kapal penuh.
- Implementasi lokal dan 67 tes selesai; **review/penerimaan mentor belum tercatat**. Otomasi kalkulasi/gate/reporting sudah berjalan, bukan integrasi otomatis semua sumber.
- Lifecycle tetap **Simulation → Iteration 1..N → Final Simulation Validation oleh mentor → pertimbangan MVP**. Tidak ada batas jumlah iterasi atau izin MVP dari keberhasilan satu run.

## Kerangka produk dan arsitektur yang harus dipakai pada pekerjaan berikutnya

Diperjelas pengguna pada 22 Oktober 2026: **kita bekerja sebagai product architect, product engineer dan solution architect**. Jangan mereduksi proyek menjadi kalkulator CFR, chatbot atau kumpulan skrip. Tugas kita menghubungkan target bisnis, keputusan pengguna, proses tender, sumber informasi, aturan, mesin hitung, pengalaman review dan bukti manfaat. Bagian ini menyimpan konteks produk; tidak mengubah aturan I4 atau mengizinkan fitur baru.

**Pemisahan domain, koreksi eksplisit pengguna:** Fleetra adalah pekerjaan terpisah dan tidak berhubungan dengan proyek DSS ini. Jangan memakai task, data kru, BRD Fleetra atau rollout Fleetra untuk membenarkan kebutuhan, arsitektur, dependency, integrasi maupun outcome DSS. Penyebutan Fleetra pada histori bukan rencana integrasi aktif. Fokus DSS tetap proses komersial/tender CFR dan voyage economics PILOG.

### Tujuan bisnis dan batas klaim

- Target 2027 **60% FOB / setidaknya 40% CFR** berasal dari keterangan internal pengguna/mentor, bukan target yang ditetapkan empat paper. Dokumen target resmi, pemilik/denominator pengukurannya belum diverifikasi dalam repo; jangan menyajikan persentase sebagai KPI terukur yang sudah dicapai. Acuan vault: `PILOG - Proses Bisnis dan Model Laba.md`, bagian konteks strategis internal.
- Arah bisnisnya adalah membantu PI Group menawarkan CFR secara lebih sistematis melalui **push demand dan tender**, serta memperkuat kemampuan PILOG mengelola operasi/layanan freight, sesuai konteks vessel operator yang disampaikan pengguna. Jangan kembali memakai narasi menunggu buyer sebagai alur aktif.
- PI Group menjual komoditas; PILOG menjual jasa freight. CFR dapat membuka peluang scope freight yang dikelola PILOG, tetapi tidak otomatis menjadi revenue PILOG tanpa penugasan/kontrak. FOB juga tidak berarti PILOG selalu memperoleh nol pendapatan pada seluruh bisnisnya.
- Peningkatan CFR adalah hasil bisnis yang ingin didukung, **bukan objective function untuk memperbanyak GO**. Peluang yang tidak layak tetap harus mendapat NO GO yang dapat dijelaskan. Keandalan operasi, kondisi pasar, penerimaan buyer dan keputusan manusia tetap memengaruhi realisasi target.
- Revenue freight, kontribusi setelah biaya dalam model, laba bersih perusahaan dan total harga komoditas CFR adalah objek berbeda. Jangan mengklaim GO I4 membuktikan profit siklus kapal penuh atau kenaikan pendapatan aktual.

### Referensi → pelajaran desain → penerapan dan batas

Nomor halaman di bawah adalah nomor halaman PDF. Referensi adalah dasar desain dan pembelajaran, bukan SOP PILOG, spesifikasi kode yang harus disalin seluruhnya, atau bukti ROI yang sudah terjadi.

| Referensi | Pelajaran yang diambil | Penerapan / batas pada proyek |
|---|---|---|
| Paper 1, *From Bilateral Bargains to Indices*, PDF 4–6 dan 13 | Ada banyak objek harga; unit, waktu, spesifikasi dan TCE conversion harus eksplisit | Kontrak data, pemisahan USD/MT versus USD/hari, harga versus biaya, benchmark versus transaksi. Bukan model forecast pasar |
| Paper 2, *From Fixing to Forward Curves*, PDF 4–12 | Harga freight terkait voyage economics, kontrak dan benchmark; hedge menyisakan basis/liquidity risk | Target TCE → freight, rekonsiliasi biaya dan skenario. Tidak menyalin premi contoh, hedge ratio atau instrumen contoh menjadi aturan PILOG |
| Paper 3, *What Automation Can Change…*, terutama PDF 4–5 dan Figure 3 PDF 9 | Otomasi mengubah workflow informasi menjadi proposal keputusan yang bisa ditelusuri; bukan sekadar rate prediction | Input → normalisasi → hitungan → skenario → proposal → human review + audit. I4 belum punya AIS nowcast, freshness gate produksi, execution/hedging atau actual P&L monitoring |
| Paper 4, *Dry Bulk Freight Buying in 2030*, PDF 3–6 dan 9–12 | Pisahkan penyesuaian angka, hard screen dan residual risk; bangun perbandingan dahulu, kemudian memori dan controlled scale | Floor/cek kapasitas/baseline dipisahkan dari OD dan stress informatif. Estimate-to-actual dan post-fixture learning adalah arah berikutnya, bukan fitur aktif |
| ADMISI Q3 2026, *AI and Agentic Systems to the Rescue*, halaman majalah 13–15 / PDF 2–4 | Informasi tersebar → orchestration → exposure, risk, logistics impact dan pricing consequences → keputusan manusia | Visi produk yang lebih luas; orchestrator Python saat ini adalah fondasi alur deterministik, **belum** AI agent lintas sistem |
| Flow resmi `docs/it_4/official_flowchart.jpeg`, kotretan mentor, flow final `docs/it_4/flowchart.png`, D-042..D-046 | Adaptasi ke PI/PILOG: kontrak payung/OD → kebutuhan/kapal → finalisasi freight/CFR → tender → instruksi/kontrak/delivery | Membatasi posisi otomasi/DSS serta pemilik keputusan. Implementasi I4 hanya mensimulasikan bagian yang disepakati, tidak menjalankan tahap pascakeputusan |

Lokasi paper dan majalah: `../references/` dari root repo. Ringkasan belajar ada di `../summary_papers/`; gunakan PDF asli untuk menyelesaikan konflik. BRD Fleetra bukan dasar kebutuhan/desain DSS dalam scope ini.

**Adaptasi yang tidak boleh tertukar:** paper sering mengambil sudut pandang pembeli freight yang membandingkan biaya penawaran kapal. Pada tender komoditas PI di proyek ini, buyer menawar alpha dan ranking mengutamakan penawaran eligible tertinggi, sementara PILOG menilai ekonomi freight-nya. Jangan menyalin objective “freight termurah” menjadi aturan penentuan buyer komoditas. Sekalipun contoh paper memakai charterer, PILOG I4 tetap kasus kapal milik yang ditetapkan.

**Indeks komoditas ≠ benchmark freight.** Argus/Fertecon granular FOB SEA menopang harga barang. Baltic/Fearnpulse adalah konteks profil/pasar freight/TCE dengan unit dan basis berbeda. OD adalah acuan tarif kontrak payung. Ketiganya tidak dapat saling menggantikan hanya karena disebut benchmark. Temuan ambigu dalam paper, misalnya tabel unit atau instrumen hedge contoh yang tidak konsisten, tidak boleh diwariskan diam-diam ke kontrak data/kode.

### Arsitektur kapabilitas, bukan daftar teknologi

| Bagian | Keputusan/masalah yang didukung | Posisi I4 |
|---|---|---|
| Data layer | Informasi apa yang diketahui tentang cargo, kapal, biaya, pasar, OD dan bid? | Snapshot CSV/JSON; raw sumber dipertahankan; pengumpulan/penetapan belum terintegrasi live |
| Pre-process layer | Apakah arti, unit dan basis informasi cukup konsisten untuk dihitung? | Kontrak I4.1, validasi teknis, mapping sumber/asumsi; toleransi tahun sumber sesuai mentor |
| Calculation layer | Berapa hari, fuel, biaya, freight, FOB/CFR dan kontribusi? | Python Decimal; fungsi deterministik terpisah, bukan aritmetika LLM |
| Decision layer | Bid mana eligible dan apakah pelaksanaan CFR PILOG layak pada batas model? | Gate A/B dan ranking kandidat; baseline versus stress; OD informatif |
| Orchestration/reporting | Bagaimana tahapan terhubung dan alasan keputusan dapat diperiksa? | Urutan pipeline, brief sederhana, audit terperinci, exact input snapshot dan replay |
| Human decision/execution | Siapa mengesahkan award, menanggung risiko dan menjalankan kontrak? | Manusia; sistem tidak mengesahkan atau mengeksekusi transaksi |
| Learning/AI masa depan | Apa yang perlu diubah dari bukti voyage berikutnya, dan informasi mana dapat diekstrak otomatis? | Arah pengembangan setelah fondasi diterima, bukan tambahan scope otomatis |

Sumber pasar dan sistem lain hanya menjadi calon integrasi bila kebutuhan DSS-nya memang ditetapkan; jangan mengasumsikan konektor tersedia atau menambahkan dependency Fleetra. AI kelak dapat mencari/membaca dokumen, mengusulkan ekstraksi terstruktur, memanggil fungsi dan menjelaskan evidence; tidak mengganti mesin matematika atau mengarang aturan komersial. FFA membutuhkan model exposure, basis, settlement dan liquidity tersendiri; tidak otomatis menyelesaikan semua risiko delay/bunker/operasi.

### Output, outcome dan kontribusi terhadap target

1. **Output sekarang:** data terstruktur, hitungan, ranking bid, GO/NO GO, tabel cek, stress dan audit.
2. **Outcome antara yang perlu dibuktikan:** reviewer lebih cepat memeriksa kasus; hitungan lebih konsisten; kesalahan berulang dan pekerjaan rekonsiliasi berkurang; alasan keputusan lebih mudah diterangkan.
3. **Outcome komersial yang diharapkan:** PILOG/PI lebih siap menilai dan menindaklanjuti peluang CFR yang layak dengan biaya/risiko yang terlihat, tanpa menambah beban analisis secara tidak terkendali.
4. **Impact strategis yang ingin didukung:** penangkapan jasa freight/kemampuan operator dan pencapaian komposisi ekspor CFR yang ditargetkan, sepanjang didukung kontrak, pasar dan kesiapan operasi. **Belum diukur atau terbukti disebabkan sistem ini.**

Keberhasilan produk tidak diukur hanya dari jumlah test, banyaknya GO atau kecanggihan AI. Baseline pembanding proses, sampel kasus yang direview mentor dan bukti estimate-versus-actual diperlukan sebelum mengklaim penghematan, peningkatan kontribusi, atau dampak target. Jangan menciptakan persentase manfaat yang belum diukur.

### Peran dan prinsip kerja selanjutnya

- Kita menerjemahkan pengetahuan mentor/domain menjadi model proses, data contract, keputusan, modul, tes dan pengalaman review yang dapat dipertanggungjawabkan; bukan mengambil alih otoritas Commercial/Operations/Finance/Risk/Legal.
- Jelaskan setiap perubahan sebagai **masalah bisnis → keputusan pengguna → kebutuhan data → logika/aturan → output → bukti outcome**. Bedakan fakta sumber, instruksi mentor, asumsi simulasi dan usulan arsitektur.
- Sebutkan apakah kemampuan **sudah diimplementasikan, masih proxy simulasi, atau baru roadmap**. Jangan menjadikan visi agentic sebagai klaim fitur saat ini, dan jangan menilai fondasi hanya dari kesederhanaan rumus.
- Simulation → Iteration 1..N → Final Simulation Validation → pertimbangan MVP tetap mengikat. Tidak ada perubahan gate, fitur produksi atau jadwal MVP yang disetujui melalui pencatatan konteks ini.

## Charter historis I1/I2 — jangan diterapkan sebagai aturan I4

## Product identity

PILOG CFR DSS is a prescriptive decision support system for evaluating a shipment as FOB, CFR with PILOG-owned/operated tonnage, CFR with chartered tonnage, or HOLD/NO_BID. It is currently a simulation-only product: all recommendations require human commercial approval and no system action may execute a quote, booking, fixture, hedge, or external write-back.

## Product problem

PILOG needs a repeatable way to decide whether accepting freight scope under CFR creates acceptable value after considering physical constraints, voyage economics, availability, risk, and authority. A higher CFR selling price alone is not a recommendation.

```text
case data
-> validated snapshot
-> deterministic calculation
-> eligible scenarios
-> rules and evidence
-> advisory recommendation
-> human review and learning
```

## Users

| Role | Need | System output | Human authority |
|---|---|---|---|
| Commercial/Business Development | Choose offer structure | FOB/CFR comparison and reasons | Validate buyer/contract and approve commercial action |
| Operations/Chartering | Validate operational choice | Capacity, timing, and cost evidence | Confirm availability and operational feasibility |
| Finance/Risk/Legal | Review exposure and controls | Margin, assumptions, status, reason codes | Approve policy, cost, risk, and contract matters |
| Management | Make authorised decision | Concise decision brief/audit trace | Approve, reject, or override |
| IT | Build safe, reproducible workflow | Deterministic pipeline and tests | Must not invent policy or approve action |

## Product principles

1. Prescriptive, not merely descriptive: propose an action with evidence.
2. Explainability first: facts, assumptions, formula trace, constraints, reasons, and authority status must be separate.
3. Human-in-the-loop: `CFR_RECOMMENDED` is not `CFR_APPROVED`.
4. Safe failure: missing, stale, non-comparable, or unvalidated input returns HOLD/BLOCK/CONDITIONAL, not false certainty.
5. Deterministic math: standard Python functions using `Decimal` are the sole authoritative calculator.
6. LLM boundary: LLMs may map variables, write/review code, and explain executed results; they must not invent inputs, calculate authoritative business values, or override Python results.
7. Mentor feedback is authoritative. GPT/Gemini notes are hypotheses until confirmed.

## Decision scope

### In scope for current simulation

- local CSV/manual case inputs;
- controlled manual Index and Alpha;
- deterministic voyage economics after data definitions are approved;
- Supramax and Handysize scenario families only;
- Gate 1 eligibility, Gate 2 choice, reason codes, decision brief, human handover;
- review/feedback loop across iterations.

### Out of scope

- auto-quotation, chartering, fixture, booking, hedge, approval, or write-back;
- live Fleetra, SAP, Procure-X, or market integration;
- ML pricing/prediction;
- CII, terminal/draft, and API-based checks without an approved data contract;
- production claims from the experimental Bontang -> ECI case.

## Core lifecycle

```text
DRAFT
-> DATA_CHECK
-> HOLD_DATA_ISSUE | READY_FOR_SCENARIOS
-> SCENARIOS_CALCULATED
-> GATE_1_EVALUATED
-> GATE_2_EVALUATED
-> RECOMMENDATION_READY
-> PENDING_HUMAN_REVIEW
-> APPROVED | OVERRIDDEN | REJECTED | NO_BID | EXPIRED
```

Only humans may transition a case to `APPROVED` or `OVERRIDDEN`.

## Decision architecture

```text
Data layer
  raw case, master vessel data, market inputs, policy inputs
->
Pre-process layer
  parse, normalize, validate unit/currency/source/freshness, snapshot
->
Process layer
  constraints, deterministic economics, scenario construction, Gate 1, Gate 2
->
Output layer
  recommendation, calculation trace, reasons, assumptions, approval handover
```

## Gate 1 - eligibility

Question: is the shipment sufficiently defined and permitted to enter CFR analysis?

Minimum evidence:

- cargo, quantity, origin, destination, and laycan;
- commercial/contractual CFR scope and PILOG authority;
- critical quality status is not BLOCK;
- enough decision time;
- controlled Index and Alpha inputs for the simulation.

Output: `CFR_ELIGIBLE`, `HOLD_DATA_ISSUE`, or `FOB_RECOMMENDED`.

## Gate 2 - scenario choice

Question: for each scenario, is it feasible, comparable, economically acceptable, within policy, and ready for human review?

Expected evidence:

- Supramax/Handysize vessel class;
- capacity/timing evidence where available;
- deterministic voyage cost and freight economics;
- comparable route, quantity, date, unit, currency, and cost boundary;
- approved margin/TCE/contribution rule;
- risk, clause, cash, and approval state;
- reason codes for every failed/unknown condition.

Output: `CFR_RECOMMENDED`, `CFR_CONDITIONAL`, `FOB_RECOMMENDED`, `HOLD_DATA_ISSUE`, or `NO_BID_RECOMMENDED`.

## Calculation contract

```text
FOB = Index + Alpha
CFR = FOB + Freight Selling Rate + Adjustment
Freight Contribution = Freight Selling Rate - Relevant Freight Cost
```

The above is a starting price abstraction, not complete transaction profit. Complete voyage economics require a mentor-approved cost boundary.

Required deterministic modules:

| Module | Purpose |
|---|---|
| Capacity | Determine cargo/vessel capacity status |
| Voyage days | Calculate laden, ballast, port, and total days |
| Fuel | Calculate approved fuel use and cost |
| Cost | Combine cost components without double-counting |
| Revenue | Calculate freight revenue/commission treatment |
| Economics | Calculate contribution and TCE only after definitions are approved |
| Scenarios | Build FOB, owned, chartered, and no-bid alternatives |
| Gates | Convert deterministic evidence to statuses/reason codes |
| Recommendation | Select among eligible scenarios using an approved objective |

## Data ownership and mandatory lineage

| Category | Examples | Owner/source |
|---|---|---|
| Master data | vessel class, DWT, equipment | approved Fleetra/master data |
| Case data | cargo, quantity, route, laycan, Incoterm | Commercial/Operations/manual import |
| Market data | Index, bunker, charter reference, FX | approved controlled source |
| Cost data | port cost, hire, running cost, commission | Finance/Chartering/approved source |
| Policy data | margin floor, authority, risk rules | approved management policy |
| Calculation output | days, cost, contribution, TCE | deterministic Python |
| Human decision | approval, override, comment | authorised user |

Every decision-critical input must carry: `case_id`, `scenario_id` if applicable, raw/normalized value, unit, currency, source, as-of/valid-until time, snapshot version, formula version, rule version, and approval state.

## Iteration 2 product requirements

1. Classify all 62 variables by calculation role or explicit unused reason.
2. Confirm what `Freight rate (USD/MT)` means before treating it as a selling rate, benchmark, or cost input.
3. Derive Freight Cost and Freight Selling Rate only where their business definitions are approved.
4. Keep Index and Alpha as controlled manual inputs.
5. Split calculations into pure, tested Python modules.
6. Make Gate 1 consume critical quality status.
7. Replace hardcoded feasibility/comparability with derived evidence where available; otherwise HOLD/CONDITIONAL.
8. Generate a prescriptive recommendation plus calculation trace and unresolved assumptions.

## Product output contract

Every decision brief must separate:

```text
Facts          - received data and lineage
Assumptions    - controlled/manual inputs and unresolved gaps
Calculations   - deterministic formula trace
Constraints    - pass/fail/unknown evidence
Scenarios      - FOB/owned/chartered/no-bid comparison
Recommendation - proposed action and reason codes
Authority      - human approval or override status
```

## MVP readiness

The product may move from simulation toward MVP only after formulas/cost boundary and Gate rules are mentor-approved, critical inputs have traceable source/unit/freshness metadata, multiple representative/edge cases are reproducible, and human approval/override is designed. A single successful simulation is not MVP readiness.

## Agent pre-change checklist

Before changing the product, an agent must answer:

1. Which user decision improves?
2. Is this simulation, MVP, or later production scope?
3. Which Python module owns the calculation?
4. What source, unit, timestamp, and owner are required?
5. What happens when input is missing/stale/not comparable?
6. Has the mentor approved the business definition/threshold?
7. Which test proves the expected behaviour?
8. Which iteration review/state item will record the result?

If an answer is unknown, create a blocker/task rather than inventing a policy.

