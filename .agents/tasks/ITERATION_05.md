# Task Iterasi 5 — deployment Streamlit existing

Status D-074: pengguna mengizinkan perubahan isi/nama empat sheet dan dua pemilih Step 1 sebelum deployment. Format/warna/posisi/ukuran workbook wajib tetap. Implementasi V0..V4 diizinkan; deployment/porting tetap belum dimulai. Acuan [plan I5](../../docs/it_5/ITERATION_05_PLAN.md). I4 accepted/pushed 57257c0; 239/239 release tests baseline.

## Revisi data dan pilihan kasus sebelum deployment

- [x] I5-BID0 — D-076: telaah mengapa contoh lama selalu GO; pengguna meminta pengacakan bid/risiko.
- [x] I5-BID1 — generator TENDER-EXAMPLE.1 ber-seed, alpha di sekitar floor dan risk shock/delay bervariasi, quote/gate tetap.
- [x] I5-BID2 — session draft/acak ulang, apply eksplisit, hash generated/applied/seed dan pembersihan metadata stale.
- [x] I5-BID3 — 262/262 tes lulus (53,546 detik); seeds menghasilkan GO/NO GO valid, replay bebas RNG, stress non-veto, UI draft/quote/re-apply dan browser empat run/unduhan/390px PASS, 0 JS error; server uji berhenti.

- [x] I5-PROFILE0 — D-075, 29 Oktober: pengguna meminta langsung 2 Handysize + 2 Supramax dengan variasi physical profile, benchmark tetap Fearnpulse dan format workbook tetap.
- [x] I5-PROFILE1 — HS36/HS38/SUP54/SUP58 diisi, formula/cache dihitung ulang, format identik dan mirror/catalog disinkronkan.
- [x] I5-PROFILE2 — dua keluarga Fearnpulse tetap; status physical demo eksplisit, ID legacy/quote/histori dipertahankan.
- [x] I5-PROFILE3 — 254/254 tes lulus (45,411 detik), 16 kombinasi/replay/Excel parity; browser GO/NO GO/download/390px PASS, 0 JS error, server uji berhenti.

- [x] I5-V0 — inspeksi workbook, OD, aplikasi dan pemisahan voyage versus kapal; pengguna menerima empat rute urea dan mengizinkan nilai contoh berlabel.
- [x] I5-V1 — isi/nama empat sheet diperbarui; format/ZIP parts terlindungi identik, arsip I4 dan mirror Experiments diverifikasi.
- [x] I5-V2 — pembaca voyage/profil dan cache hash aktif; JSON derived disinkronkan offline, fixed/histori tetap.
- [x] I5-V3 — dua pilihan independen, nama profil kelas/DWT/speed; contoh mengikuti voyage dan pulih dari input manual invalid.
- [x] I5-V4 — 252/252 full suite lulus (45,498 detik), 37 targeted final lulus, 16 kombinasi + offline replay, Excel-engine parity empat sheet serta browser GO/NO GO/unduhan/mobile PASS/0 JS error.

Kontrak: Mundra/Davao/Bangkok/Hai Phong dari Bontang, urea granular, 30k/28k/32k/29k MT. Jarak tetap OD-only, komisi 0%, Fearnpulse tetap untuk target dan bunker. Asumsi port/handling/waiting bukan data aktual. Workbook memilih voyage via route/cargo dan profil via kode di B3; pilihan pada UI tidak saling memaksa. Pergantian basis fixed memerlukan revisi penawaran, tidak membawa bid lama. Raw workbook boleh diedit sesuai instruksi terbaru; arsip I4 disimpan di luar direktori input aktif untuk replay dan regresi.

## Perencanaan

- [x] I5-P0 — periksa repo/service/dependency dan baseline accepted.
- [x] I5-P1 — checkpoint I4 ke origin/dev: 57257c07299cd74d7172a84d3ec158e5679a7c1e.
- [x] I5-P2 — rencana awal API/persistence/deployment dengan sumber primer.
- [x] I5-P3 — jawaban diterima: luar kantor, belum ada server, 1–3 pengguna perlu create/edit.
- [x] I5-P4 — rencana demo awal disusun; rekomendasi portingnya digantikan D-073.
- [x] I5-P6 — kritisi kebutuhan stack; prioritas hosting Streamlit existing, API/RBAC ditunda.
- [ ] I5-P5 — konfirmasi penyimpanan A/B, finalkan host/anggaran; sinkron kotretan ketika tersedia dan tunggu instruksi implementasi.

## Batch aktif setelah instruksi implementasi

- [ ] I5-S0 — pilih penyimpanan A/B, host dan build configuration.
- [ ] I5-S1 — readiness Linux/dependency/binding/assets/path/cached snapshot.
- [ ] I5-S2 — lingkup file per sesi dan penyimpanan terpilih; ekspor/impor atau persistent repository.
- [ ] I5-S3 — regresi input/hasil dan browser smoke GO, floor NO GO, ekonomi NO GO, unduhan serta dua sesi.
- [ ] I5-S4 — deploy private dan verifikasi URL/login/penggunaan dari laptop lain.
- [ ] I5-S5 — UAT create/edit/hitung/unduh/reopen, handover dan fallback PIHC.

Batch porting I5-0..6 sebelumnya tidak pernah dijalankan dan digantikan S0..S5. V1..V4 selesai teknis; deployment S0..S5 belum dijalankan. Bukti bukan acceptance mentor atau izin produksi.

Kandidat Community Cloud private; belum membuat akun/layanan atau mengundang viewer. FastAPI, React, DB wajib dan role enterprise ditunda. Private access tetap perlu; Simpan draft existing ke file server tidak dijanjikan tahan restart. Fitur UI impor paket belum ada. Jika kasus harus permanen, DB dapat diakses langsung dari Streamlit tanpa API terpisah. Gate/rumus/quote/data accepted tetap.
