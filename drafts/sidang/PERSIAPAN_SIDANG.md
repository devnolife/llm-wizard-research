# Persiapan Sidang Tesis — Wizard Research

Pendamping untuk `SIDANG_TESIS_Wizard_Research.pptx` (28 slide: 19 inti + 9 cadangan).
Regenerasi deck: `python3 drafts/sidang/make_figures.py && python3 drafts/sidang/build_deck.py`.

> **Sebelum sidang — wajib diisi:** nama pembimbing dan tanggal pada slide 1; cek nama penguji
> untuk menyesuaikan slide C6 (respons 8 kritik proposal).

---

## 1. Susunan Waktu

### Versi 20 menit (bawaan; total catatan ≈ 22 menit, sisakan cadangan 2 menit)

| # | Slide | Waktu | Pesan satu kalimat |
|---|-------|------:|--------------------|
| 1 | Judul | 0:30 | Alat bantu keputusan, bukan pengganti peneliti |
| 2 | Latar belakang | 1:00 | Sintesis literatur = penalaran induktif; alat yang ada bekerja di level semantik |
| 3 | Rumusan masalah | 1:15 | "Sejauh mana", "bagaimana memengaruhi FDR", "apa batasnya" |
| 4 | Kebaruan | 1:00 | Integrasi neural + simbolik + kalibrasi/provenans, bukan sekadar pipeline |
| 5 | Arsitektur | 1:15 | Empat fase; Fase 4 komponen baru |
| 6 | Fact Table & Rule Engine | 1:30 | 9 aturan → verdict sebagai bukti dalam kalibrasi |
| 7 | Semantik vs logis | 1:15 | Tiga lapis + NLI; kopling & korroborasi bebas LLM |
| 8 | Keyakinan yang dapat dipertanggungjawabkan | 0:45 | Provenans, kalibrasi, abstensi, k/n |
| 9 | Desain eksperimen | 1:15 | Dua korpus, dua rezim (tidak dibandingkan silang), 14 metrik |
| 10 | Hasil benchmark + adversarial | 1:15 | 14 indikator; Rule Engine diskriminatif 6/6 |
| 11 | Ablasi multi-run | 1:30 | H9 signifikan; H6/H7 kualitatif; H10 memangkas |
| 12 | Kontrol negatif | 1:15 | 4/5 bersih; 1 false gap 0,885 → provenans pertahanan terakhir |
| 13 | Korpus aplikatif | 1:45 | Keempat tipe indikator; tiga sinyal independen |
| 14 | Stabilitas k/n | 1:00 | 58% stabil; satu run = satu undian |
| 15 | Status hipotesis | 1:30 | Peta jujur janji BAB III → bukti BAB IV |
| 16 | Kesimpulan RQ | 1:30 | Tiga jawaban, tiap-tiap dengan batasnya |
| 17 | Kontribusi | 1:00 | Tujuh kontribusi |
| 18 | Batas klaim & saran | 1:15 | Evaluasi pakar: prasyarat lengkap |
| 19 | Terima kasih | 0:15 | — |

### Versi 15 menit (bila waktu presentasi dibatasi)

Lewati slide **4** (kebaruan — cukup disebut lisan di slide 3), **8** (gabungkan ke slide 7 dalam satu
kalimat), dan **14** (sebut angka 58% saat slide 13). Persingkat slide 15 menjadi 45 detik dengan
membaca hanya baris hijau/merah. Hasil: ≈ 15 menit 30 detik.

### Alur "katakan–tunjukkan–ulangi"

- **Pembuka (1–3):** fenomena → kesenjangan → tiga pertanyaan.
- **Tubuh (4–14):** metode (4–8) → bukti (9–14). Setiap slide hasil dibuka dengan kesimpulannya
  *sebelum* grafik ("NLI menaikkan deteksi secara signifikan — ini datanya").
- **Penutup (15–18):** peta hipotesis → jawaban RQ → kontribusi → batas & saran.

---

## 2. Lembar Angka Kunci (hafalkan)

| Kelompok | Angka |
|----------|-------|
| Korpus benchmark | 23 paper CS, 4 topik (T1–T4), 3.146 chunk, 248 fakta SPO (22/23 paper), 14 indikator (42,9% ketidaklengkapan / 28,6% / 28,6%), confidence 0,700, PASS 100%, 1.757 s (98,7% ekstraksi fakta) |
| Adversarial | 6/6 benar; F1/F3 REJECT (−0,60); F2, K1, C1 FLAG (−0,15 … −0,20); kontrol PASS |
| Multi-run (llama3.2) | full 17,2 ± 3,2 · no-rule-engine 18,2 ± 5,5 · linear 20 ± 0 · nli 24,3 ± 2,3 · no-nli 15,2 ± 1,9 · cross-critic 4,2 ± 4,1; RERR full 3,8 ± 8,5% |
| H9 | Δmed = 8 indikator; confidence +0,038; U = 35; p Holm = 0,0428 (keluarga 8 uji); Cliff's δ = 1,0 |
| H10 | 153 kandidat → 131 ditolak (85,6%), 13 dibela, 21 akhir; Δmed = −19; conf 0,791 → 0,884; p Holm = 0,0428 |
| H6/H7 | tidak signifikan, p Holm ≥ 0,48 |
| Kontrol negatif | topik "quantum biology in marine ecosystems"; false gap 0, 0, 0, 1, 0 → 0,2 ± 0,45/run; yang lolos confidence 0,885 |
| Korpus aplikatif | 35 jurnal forensika digital, 877 chunk (chunker baru; 3.095 pada Agustus), 5 topik, ~12 menit, LLM claude-opus-4.8-fast |
| Indikator versi akhir | 4 PASS: kopling 0,828 → 0,911 · cakupan 0,750 → 0,825 · isolasi 0,720 → 0,792 (ditahan) · support gap 0,650 → 0,715; korroborasi 2/2 (4 pernyataan, skor 0,68–0,71) |
| Kopling bibliografis | 26 jurnal memenuhi syarat (≥ 5 referensi), 19 komponen, 318/325 pasangan terputus (0,978), modularitas 0,70, 6 karya rujukan bersama, 3 sitasi langsung |
| Stabilitas k/n | 3 run: 388 / 307 / 336 gap → union 528; k=3: 196 (37%), k=2: 111, k=1: 221; stabil 307 (58,1%); Jaccard 0,445 / 0,475 / 0,645; tersurat 63% vs implisit 41% |
| Benchmark Mendeley | 30 paper; 20 menghasilkan gap; kemiripan 0,603 (14/20 ≥ 0,5); LLM-judge 2,75/5 (10/20 ≥ 3) |
| Kalibrasi | temperature 1,0 (identitas; label pakar 0 < 4); PASS ×1,10 · FLAG ×0,80 · REJECT 0; abstain < 0,45 atau ambang konformal α = 0,10 |
| Rekayasa | 894 unit test (892 lulus, 2 dilewati); ~7.900 baris komponen inti; 9 aturan; 8 tipe entitas; 12 + 2 predikat |

---

## 3. Antisipasi Pertanyaan Penguji

Jawaban dirancang **jujur dahulu, bukti kedua, rencana ketiga**. Slide cadangan yang relevan ditandai.

### A. Tentang evaluasi

1. **"Tanpa penilaian pakar, bagaimana Anda tahu indikatornya benar?"** (C1)
   Tidak tahu — dan tesis ini tidak mengklaim itu. Yang diklaim: indikator *terdeteksi dengan bukti yang
   dapat diaudit* (kutipan verbatim, verdict, fakta KG), lapisan validasi *terbukti diskriminatif*
   (adversarial 6/6, kritikus menolak 85,6%), dan sistem *hampir tidak berhalusinasi pada topik fiktif*
   (false gap 0,2/run). EAR/LCS/FDR adalah langkah berikutnya; instrumen dan keluaran finalnya siap.

2. **"Kriteria keberhasilan Anda EAR ≥ 50% — terpenuhi atau tidak?"**
   Belum dapat dinyatakan keduanya (Tabel 4.10). Kriteria ini bergantung pada label pakar. Kriteria teknis
   yang tidak bergantung pada pakar terpenuhi seluruhnya.

3. **"Mengapa tidak melakukan evaluasi pakar pada versi Agustus saja?"**
   Karena versi Agustus belum memuat korroborasi, kopling dalam pipeline, dan perbaikan fusi
   verdict–kalibrasi; menilai keluaran yang kemudian berubah akan membuang waktu pakar dan menghasilkan
   angka yang tidak berlaku bagi sistem akhir.

4. **"Apa itu H6/H7 tidak signifikan — berarti agentic dan Rule Engine tidak berguna?"** (C3)
   Tidak signifikan pada *proksi kuantitatif* (jumlah indikator, confidence) dengan 5 run. Efeknya memang
   bukan kuantitas: baseline linear justru menghasilkan *lebih banyak* indikator (20) tetapi identik antar
   topik (templat), tanpa fakta, verdict, atau jejak. Rule Engine terbukti pada adversarial dan menjadi
   bukti dalam kalibrasi. Uji FDR yang sesungguhnya menunggu pakar.

### B. Tentang metode

5. **"Bukankah ini hanya RAG + LLM dengan tambahan aturan?"** (slide 4, C6)
   Perbedaannya pada tiga hal yang tidak ada di pipeline linear: representasi fakta terstruktur (SPO) yang
   ditalar secara deduktif; verdict simbolis yang difusikan ke keyakinan (bukan dirata-ratakan); dan
   disiplin pelaporan — provenans wajib, abstensi selektif, k/n. Bukti bahwa ini bukan kosmetik: kontrol
   negatif menunjukkan lapisan neural *dan* simbolis bisa lolos, hanya provenans yang menolak.

6. **"Bagaimana Anda membedakan kontradiksi dari perbedaan hasil yang wajar?"** (C4)
   Klaim dinormalisasi (arah efek, PICO), diuji NLI, lalu diadjudikasi: bila desain/populasi berbeda dan
   heterogenitas (Q, I², τ²) menjelaskannya → *heterogenitas*, bukan kontradiksi. Sistem tidak menjelaskan
   *mengapa* bertentangan (batas RQ3).

7. **"Apa beda ketidaklengkapan dan ketiadaan dukungan bukti?"** (C4)
   Ketidaklengkapan: aspek *tidak dibahas* siapa pun (sel kosong peta bukti). Ketiadaan dukungan bukti:
   aspek *dibahas dan diklaim berulang* tetapi tidak ada paragraf bukti primer di korpus (uji leave-one-out,
   kemiripan < 0,45; *citation echo*). Tindak lanjutnya berbeda: studi perintis vs replikasi/pengujian primer.

8. **"Mengapa dua LLM berbeda? Itu mencampur variabel."** (C2)
   Disengaja dan diumumkan: model lokal untuk seed/ulangan (uji statistik), model penyedia untuk dokumen
   Indonesia. Kedua kelompok *tidak dibandingkan silang* (4.2.5, keterbatasan 8).

9. **"Seberapa reproducible hasil Anda kalau LLM stokastik?"** (slide 14, C7)
   Diukur, bukan diasumsikan: Jaccard antar-run 0,45–0,65; 58% stabil; gap implisit paling rapuh (41%).
   Karena itu temuan LLM selalu dilaporkan dengan k/n, dan sinyal bebas-LLM (kopling, kutipan) menjadi jangkar.

10. **"Rule Engine PASS 100% — bukankah itu artinya tidak melakukan apa-apa?"** (C3)
    Sifat input, bukan engine: adversarial 6/6, RERR multi-run 3,8%, dan verdict FLAG "bukti tidak cukup"
    pada C3/K3 di lapisan analyzer. Batas yang diakui: klaim tanpa entitas KG lolos secara default → saran
    memperluas cakupan fakta.

### C. Tentang data dan validitas

11. **"Paper benchmark Anda (BERT, ResNet) pasti ada di data latih LLM."** (C7)
    Benar — ancaman validitas internal yang diakui (4.4.3 butir 6). Mitigasi: grounding kutipan verbatim,
    validasi simbolis, dan korpus aplikatif lokal (jurnal Indonesia) yang jauh lebih kecil kemungkinannya
    terkontaminasi.

12. **"Hanya 2–4 indikator per topik — terlalu sedikit untuk disimpulkan apa pun."**
    Setuju untuk statistik per korpus; itulah mengapa ada protokol multi-run (5–7 run) dan union k/n, dan
    mengapa evaluasi pakar disarankan pada union beberapa run. Jumlah kecil juga konsekuensi desain yang
    *menahan* klaim lemah — abstensi selektif lebih baik daripada 20 indikator templat.

13. **"Bagaimana kalau daftar pustaka PDF tidak terbaca?"**
    Terjadi pada 5–10 dari 35 jurnal (editorial, bab buku, Cyrillic, terpotong). Jurnal itu *dilewati*,
    bukan dihitung terputus — isolasi 0,978 adalah properti 26 jurnal yang daftar pustakanya terbaca.
    Saran: GROBID/anystyle untuk penguraian referensi.

14. **"Anda menemukan bug saat menulis hasil — bagaimana kami yakin tidak ada bug lain?"** (C5)
    Empat cacat *silent* ditemukan justru karena sistem diuji pada korpus nyata dan hasilnya diaudit
    (provenans, kalibrasi vs verdict). Setiap cacat menjadi uji regresi berbentuk data produksi (39 uji;
    total 894). Menemukan dan melaporkannya adalah bagian dari kejujuran metodologis, bukan kelemahan.

### D. Tentang kontribusi dan posisi

15. **"Apa yang benar-benar baru di sini?"** (slide 17)
    Operasionalisasi empat indikator (termasuk ketiadaan dukungan bukti) yang dapat diukur; verdict simbolis
    sebagai bukti dalam kalibrasi; kopling bibliografis sebagai sinyal fragmentasi bebas-LLM di dalam
    pipeline deteksi gap; korroborasi penulis sebagai bukti; dan protokol k/n untuk sistem RAG+LLM analisis
    literatur.

16. **"Kalau pakar tetap harus memutuskan, apa gunanya sistem?"**
    Mempersempit ruang pencarian dari 35 jurnal menjadi beberapa indikator berbukti; menyediakan kutipan
    dan fakta yang bisa diaudit; menandai klaim tanpa bukti primer yang mudah terlewat manusia. Ini posisi
    *decision support*, dinyatakan sejak BAB I 1.5 — konsisten dengan kritik penguji #3.

17. **"Apa langkah yang paling penting setelah sidang?"**
    Sesi ≥ 2 pakar forensika digital dengan formulir yang sudah dibangkitkan dari keluaran final; kontrol
    negatif pada semua mode; lalu laporkan EAR/LCS/FDR/κ dan aktifkan kalibrasi.

---

## 4. Daftar Periksa Hari-H

- [ ] Slide 1: nama pembimbing & tanggal terisi; nama penguji dicek untuk C6
- [ ] Uji tampil di proyektor: kontras teks putih pada bar biru; font ≥ 13 pt pada tabel terbaca dari
      baris belakang; bila tidak, gunakan versi 15 menit dan bahas tabel secara lisan
- [ ] Buka `SIDANG_TESIS_Wizard_Research.pptx` dalam mode *Presenter View* agar catatan pembicara terlihat
- [ ] Siapkan tab cadangan: `drafts/BAB_IV_HASIL_DAN_PEMBAHASAN.md` (Tabel 4.9–4.10), `backend/experiments/results/multirun_stats_llama3.2_latest.md`, formulir pakar
- [ ] Bila diminta demo: jalankan Streamlit (`tools/process_monitor`, :8501) pada job `5b2017ea` yang sudah selesai — jangan menjalankan analisis baru saat sidang (~12 menit)
- [ ] Latih tiga kalimat pembuka dan tiga kalimat penutup sampai tidak perlu melihat slide
