# Agentic Workflow - PILOG CFR DSS

Folder ini adalah control plane untuk pekerjaan agentic pada repository ini. Ia menyimpan konteks, batas keselamatan, rencana iterasi, task aktif, review, dan keputusan domain. Folder ini **bukan** tempat menyimpan data produksi, kredensial, atau hasil kalkulasi transaksi.

## Urutan baca wajib

1. `AGENTS.md` - aturan kerja dan batas keselamatan.
2. `ITERATION_STATE.json` - memori terstruktur: iterasi aktif, keputusan, blocker, dan task.
3. `PLANS.md` - roadmap dan definition of done.
4. `reviews/ITERATION_01.md` - hasil serta feedback Simulation Iteration 1.
5. `tasks/ITERATION_02_PROPOSED.md` - task revisi R01–R06 yang sudah diimplementasikan; tunggu review mentor sebelum membuat task berikutnya.
6. `reviews/ITERATION_02.md` - hasil aktif dan batas bukti; belum diterima mentor.
7. `DECISIONS.md` - keputusan domain/teknis yang sudah dibekukan atau masih menunggu mentor.

`tasks/ITERATION_02.md` adalah arsip task sebelum revisi. Satu contoh run Iterasi 2 dipertahankan di `outputs/runs/i2_20260923T091307166739Z_f5c4e74a/`; run percobaan lama dibersihkan atas instruksi pengguna pada 24 September 2026.

## Siklus kerja berulang

```text
PLAN
  -> pecah tujuan iterasi menjadi task kecil dan acceptance criteria
TASK
  -> kerjakan satu task kecil dengan sumber data dan batas yang jelas
EXECUTE
  -> implementasi Python deterministik, jalankan test, simpan evidence
REVIEW
  -> bandingkan hasil dengan aturan/domain, catat feedback dan gap
UPDATE STATE
  -> perbarui review, keputusan, task, dan ITERATION_STATE
NEXT ITERATION
```

Satu iterasi dapat menghasilkan status `accepted`, `needs-revision`, atau `blocked`. Iterasi tidak dianggap selesai hanya karena script berhasil berjalan.

## Aturan paling penting

LLM boleh membantu membaca dokumen, memetakan variabel, menulis kode, menjelaskan output, dan menyusun review. LLM **tidak boleh menjadi mesin matematika**.

Semua perhitungan maritime, CFR, voyage cost, TCE, margin, konversi satuan, dan rule keputusan harus berada pada fungsi Python yang deterministik, dapat diuji, dan memakai input eksplisit. Hasil angka harus berasal dari eksekusi fungsi dan test, bukan dari angka yang "ditebak" atau dihitung mental oleh LLM.

## Hierarki sumber kebenaran

1. Keputusan/feedback mentor yang terdokumentasi.
2. Kontrak data dan definisi bisnis yang disetujui mentor.
3. Dataset dan dokumen resmi yang memiliki sumber, unit, timestamp, serta basis jelas.
4. Paper/referensi domain.
5. Saran GPT/Gemini/LLM sebagai hipotesis, bukan requirement otomatis.
