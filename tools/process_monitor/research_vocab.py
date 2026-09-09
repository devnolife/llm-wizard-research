"""Kosakata UI: nama awam, penjelasan, dan label teknis untuk tiap istilah.

Satu tempat untuk semua istilah yang muncul di UI supaya penjelasannya
konsisten antar halaman. ``label()``/``help_of()`` menghormati toggle
``mode_teknis`` di session: mode awam menampilkan bahasa sehari-hari, mode
teknis menampilkan kunci asli agar cocok dengan kode dan BAB III.
"""

from __future__ import annotations

import streamlit as st

# Kunci metrik StageOutcome → (label awam, penjelasan singkat).
METRIC_LABELS: dict[str, tuple[str, str]] = {
    # chunking
    "pdf_masuk": ("PDF diunggah", "Jumlah berkas PDF yang kamu unggah."),
    "jurnal": ("jurnal terbaca", "PDF yang berhasil diekstrak teksnya."),
    "pdf_gagal": ("PDF gagal", "Berkas yang tidak bisa dibaca sama sekali, bahkan setelah OCR."),
    "chunk": ("potongan teks (chunk)",
              "Teks tiap jurnal dipotong per kalimat jadi potongan ±384 token agar muat "
              "dibaca LLM dan bisa dirujuk balik."),
    "token_total": ("total token", "Jumlah token (≈ ¾ kata) di seluruh chunk."),
    "token_median": ("token per chunk (median)", "Ukuran chunk yang paling umum."),
    "chunk_kecil_pct": ("% chunk kecil (<150 token)",
                        "Chunk terlalu kecil biasanya sisa judul palsu atau tabel; makin kecil "
                        "persentasenya makin bersih hasil ekstraksi."),
    "referensi_ditandai": ("chunk daftar pustaka",
                           "Chunk yang dikenali sebagai daftar pustaka dan dikecualikan dari "
                           "pencarian gap."),
    "section_other_pct": ("% bagian tak dikenali",
                          "Chunk yang judul bagiannya tidak cocok dengan pola abstrak/metode/"
                          "hasil/dst. Tinggi berarti struktur jurnal tidak standar."),
    "distribusi_seksi": ("sebaran bagian jurnal", "Berapa chunk per bagian (abstrak, metode, …)."),
    "jurnal_ditandai_tak_sedomain": ("jurnal di luar bidang",
                                      "Jurnal yang isinya jauh dari jurnal lain di batch ini. "
                                      "Peringatan, bukan penolakan."),
    # gap_mining
    "chunk_masuk": ("chunk masuk", "Semua chunk dari tahap sebelumnya."),
    "kandidat": ("kandidat dibaca LLM",
                 "Chunk yang dipilih untuk dibaca LLM: kesimpulan, diskusi, dan yang memuat "
                 "kata seperti 'limitation' atau 'keterbatasan'."),
    "baseline_regex_saja": ("cocok pola kata saja",
                            "Berapa chunk yang memuat kata kunci gap. Pembanding: tanpa LLM, "
                            "hanya ini yang bisa ditemukan."),
    "gap_mentah": ("gap dari LLM (mentah)", "Kalimat gap yang dikembalikan LLM, belum dicek."),
    "llm_dipanggil": ("panggilan LLM", "Berapa kali LLM diminta membaca kandidat."),
    "llm_tanpa_jawaban": ("LLM tidak menjawab",
                          "Panggilan yang tidak dijawab LLM (layanan mati, timeout, atau "
                          "autentikasi hilang). Bila sama dengan jumlah panggilan, hasil 0 gap "
                          "adalah gagal sistem, bukan temuan."),
    "lolos_verifikasi_verbatim": ("lolos cek verbatim",
                                  "Kalimat yang terbukti benar-benar ada di teks jurnal."),
    "gugur_di_verifikasi": ("gugur cek verbatim",
                            "Kalimat yang TIDAK ditemukan di jurnal — dibuang sebagai dugaan "
                            "karangan LLM (halusinasi)."),
    "duplikat_dibuang": ("duplikat dibuang",
                         "Kalimat sama dari jurnal sama yang muncul lebih dari sekali."),
    "gap_final_setelah_dedup": ("gap final", "Gap unik yang terverifikasi."),
    "jurnal_bergap": ("jurnal yang punya gap", "Berapa jurnal menyumbang minimal satu gap."),
    # novelty
    "gap_dicek": ("gap dicek", "Semua gap yang dicek ke literatur terbaru."),
    "open": ("masih terbuka (open)",
             "Tidak ada paper 2024+ yang sangat cocok — gap ini belum dijawab siapa pun."),
    "partially_addressed": ("sebagian dijawab (partially)",
                            "Ada 1–2 paper baru yang sangat cocok."),
    "addressed": ("sudah dijawab (addressed)", "Ada ≥3 paper baru yang sangat cocok."),
    "punya_match_literatur": ("punya paper terkait", "Gap yang pencariannya menemukan ≥1 paper."),
    "tanpa_match_literatur": ("tanpa paper terkait",
                              "Pencarian tidak menemukan apa pun — bisa benar-benar baru, bisa "
                              "juga OpenAlex sedang membatasi permintaan."),
    # recommendation
    "gap_open": ("gap terbuka", "Gap berstatus open yang layak jadi topik."),
    "gap_bukan_open": ("gap disisihkan", "Gap partially/addressed — sudah ada yang mengerjakan."),
    "proposal_dinilai": ("proposal dinilai", "Gap open yang diberi skor prioritas."),
    "tema": ("tema", "Kelompok gap yang saling mirip."),
    "tema_lintas_jurnal": ("tema lintas-jurnal", "Tema yang didukung ≥2 jurnal berbeda."),
    "tema_satu_gap": ("tema beranggota satu", "Gap yang tidak mirip dengan gap lain mana pun."),
    "tema_satu_gap_pct": ("% tema beranggota satu",
                          "Tinggi berarti literatur terfragmentasi: tiap jurnal bicara hal "
                          "berbeda."),
    "skor_tertinggi": ("skor prioritas tertinggi", "Skor proposal peringkat #1 (maks 1,0)."),
    "narasi_diminta": ("butir dinarasikan LLM",
                       "Butir teratas (tema lintas-jurnal dulu, lalu proposal) yang diminta "
                       "dirumuskan judul, latar belakang, alasan, dan metodenya."),
    "narasi_dibuat": ("narasi judul jadi",
                      "Butir yang berhasil dinarasikan LLM. Peringkat dan skor tidak "
                      "terpengaruh; bila 0, LLM tidak tersedia saat itu."),
}

# Nilai enum → (label awam, penjelasan).
ENUM_LABELS: dict[str, dict[str, tuple[str, str]]] = {
    "gap_type": {
        "stated_limitation": ("keterbatasan yang diakui penulis",
                              "Penulis sendiri menyebut kelemahan penelitiannya."),
        "explicit_future_work": ("saran penelitian lanjutan",
                                 "Penulis secara eksplisit menyarankan apa yang perlu diteliti "
                                 "berikutnya."),
        "implicit_gap": ("gap tersirat",
                         "Tidak dinyatakan langsung, tetapi jelas tersirat dari teks."),
    },
    "novelty_status": {
        "open": ("masih terbuka", "Belum ada paper 2024+ yang menjawabnya."),
        "partially_addressed": ("sebagian dijawab", "1–2 paper baru sangat cocok."),
        "addressed": ("sudah dijawab", "≥3 paper baru sangat cocok."),
    },
    "band": {
        "sweet_spot": ("kebaruan sehat",
                       "Cukup berbeda dari korpus tapi masih di bidang yang sama — ideal."),
        "derivative": ("terlalu mirip korpus",
                       "Hampir sama dengan paper yang sudah ada — risiko mengulang."),
        "off_topic": ("terlalu asing",
                      "Hampir tidak beririsan dengan korpus — cek apakah masih relevan."),
    },
    "topic": {
        "image_forensics": ("forensik citra", ""), "mobile_forensics": ("forensik perangkat "
                                                                          "bergerak", ""),
        "legal": ("aspek hukum", ""), "tools": ("alat & perangkat lunak", ""),
        "multimedia": ("multimedia", ""), "other": ("lainnya", ""),
    },
    "extraction_quality": {
        "good": ("baik", "Lapisan teks PDF utuh."),
        "fair": ("cukup", "Sebagian teks bermasalah."),
        "poor": ("buruk", "Teks rusak/hasil scan; dikirim ke OCR."),
    },
}

# Nama kolom record → (label awam, penjelasan).
FIELD_LABELS: dict[str, tuple[str, str]] = {
    "source": ("jurnal", "Nama berkas PDF asal."),
    "paper_title": ("judul jurnal", ""),
    "chunk_index": ("nomor chunk", "Urutan potongan di dalam jurnalnya."),
    "chunk_id": ("ID chunk", "Pengenal unik untuk merujuk balik."),
    "section_normalized": ("bagian jurnal", "Abstrak, metode, hasil, diskusi, kesimpulan, …"),
    "section_raw": ("judul bagian asli", "Teks judul bagian seperti tertulis di PDF."),
    "token_count": ("token", "Panjang potongan (≈ ¾ kata per token)."),
    "is_reference": ("daftar pustaka?", ""),
    "page_start": ("halaman", ""),
    "text": ("teks", ""),
    "gap_type": ("jenis gap", ""),
    "gap_statement": ("kalimat asli (verbatim)",
                      "Disalin apa adanya dari jurnal; inilah yang dicek verbatim."),
    "gap_paraphrase": ("parafrase", "Ringkasan satu kalimat dalam Bahasa Indonesia oleh LLM."),
    "topic": ("topik", ""),
    "grounding_score": ("skor kecocokan verbatim",
                        "1,0 = kalimat ditemukan persis di jurnal. Di bawah ambang → dibuang."),
    "evidence_chunk_ids": ("chunk bukti", "Chunk tempat kalimat ini ditemukan."),
    "candidate_reason": ("alasan dipilih",
                         "Kenapa potongan ini dibaca LLM: seksi kesimpulan, pola kata, dst."),
    "novelty_status": ("status kebaruan", ""),
    "novelty_query": ("kata kunci dicari", "Kueri yang dikirim ke OpenAlex."),
    "related_recent_papers": ("paper 2024+ terkait", ""),
    "checked_at": ("dicek pada", ""),
    "rank": ("peringkat", ""),
    "title": ("judul usulan", "Parafrase gap; judul akhir tetap perlu dirumuskan sendiri."),
    "description": ("dasar gap", "Kalimat asli yang jadi dasar usulan ini."),
    "priority_score": ("skor prioritas",
                       "0,5×keyakinan gap + 0,3×kredit kebaruan + 0,2×keterlaksanaan."),
    "gap_confidence": ("keyakinan gap", "Sama dengan skor kecocokan verbatim gap ini."),
    "novelty": ("kebaruan", "1 − kemiripan tertinggi ke jurnal mana pun di korpus."),
    "novelty_credit": ("kredit kebaruan",
                       "Nilai kebaruan setelah dipotong bila terlalu mirip/terlalu asing."),
    "band": ("kategori kebaruan", ""),
    "actionability": ("keterlaksanaan",
                      "Seberapa konkret bisa dikerjakan: menyebut dataset, eksperimen, "
                      "protokol, dsb."),
    "nearest_paper": ("jurnal paling mirip", "Jurnal di korpus yang paling dekat dengan usulan."),
    "nearest_similarity": ("kemiripan ke jurnal itu", ""),
    "score_notes": ("catatan penilai", ""),
    "theme_id": ("nomor tema", ""),
    "theme_label": ("nama tema", ""),
    "theme_journal_support": ("jurnal pendukung tema",
                              "Batas atas, bukan bukti N jurnal menyatakan hal yang sama."),
    "theme_size": ("anggota tema", ""),
    "year": ("tahun", ""),
    "language": ("bahasa", ""),
    "extraction_quality": ("kualitas ekstraksi", ""),
    # jejak kandidat
    "seq": ("nomor kandidat", "Urutan kandidat (per jurnal, per posisi chunk)."),
    "matched_phrases": ("pola kata cocok", "Kata kunci gap yang ditemukan di chunk ini."),
    "context_chars": ("panjang konteks", "Karakter yang dikirim ke LLM: chunk ini plus satu "
                                          "chunk sebelum & sesudahnya."),
    "llm_answered": ("LLM menjawab?", "False = panggilan tidak dijawab (gagal sistem), bukan "
                                       "'tidak ada gap'."),
    "response": ("balasan mentah LLM", "Teks apa adanya yang dikembalikan model."),
    "gap_mentah": ("gap mentah", "Gap yang ter-parse dari balasan, sebelum verifikasi."),
    "gap_lolos": ("lolos verbatim", ""),
    "gap_final": ("gap final", "Lolos verbatim dan bukan duplikat."),
    "lolos_verifikasi": ("lolos verbatim?", ""),
    "duplikat": ("duplikat?", ""),
    "model": ("model", ""),
    # tema
    "journal_support": ("jurnal pendukung", "Batas atas, bukan bukti kesepakatan."),
    "journals": ("jurnal", ""),
    "size": ("anggota", ""),
    "priority": ("skor rata-rata anggota", ""),
    "top_priority": ("skor tertinggi anggota", ""),
    "topics": ("topik anggota", ""),
    "match_score": ("skor kecocokan paper", "Porsi kata kunci gap yang muncul di judul+abstrak "
                                             "paper; ≥0,5 dihitung 'kuat'."),
}

# Istilah umum untuk glosarium per tahap.
GLOSSARY: dict[str, list[tuple[str, str]]] = {
    "chunking": [
        ("chunk", "Potongan teks ±384 token (≈300 kata). Semua analisis merujuk ke chunk, "
                  "sehingga tiap temuan bisa dilacak ke bagian jurnal yang persis."),
        ("token", "Satuan teks yang dibaca model bahasa; kira-kira ¾ kata."),
        ("OCR", "Pembacaan teks dari gambar, dipakai bila PDF adalah hasil scan."),
        ("bagian (seksi)", "Abstrak, pendahuluan, metode, hasil, diskusi, kesimpulan, "
                           "daftar pustaka — dikenali dari judul bagiannya."),
    ],
    "gap_mining": [
        ("gap penelitian", "Keterbatasan, kekurangan, atau saran lanjutan yang disebut "
                           "penulis jurnal sendiri."),
        ("kandidat", "Chunk yang dipilih untuk dibaca LLM karena kemungkinan besar memuat gap."),
        ("alasan kandidat", "section:conclusion/discussion = bagian kesimpulan/diskusi; phrase = "
                            "memuat kata seperti 'limitation'/'keterbatasan'; abstract, "
                            "introduction, tail = aturan cadangan agar jurnal tanpa struktur "
                            "tetap terbaca."),
        ("verbatim", "Kata demi kata. Kalimat gap harus tersalin persis dari jurnal, bukan "
                     "diringkas atau dikarang."),
        ("halusinasi", "Kalimat yang dikarang LLM padahal tidak ada di sumber. Tahap "
                       "verifikasi verbatim dibuat untuk membuangnya."),
        ("skor kecocokan (grounding)", "Seberapa persis kalimat LLM cocok dengan teks jurnal; "
                                        "1,0 = identik."),
    ],
    "novelty": [
        ("OpenAlex", "Basis data literatur ilmiah terbuka (gratis), dipakai untuk mencari "
                     "paper terbaru."),
        ("open / partially / addressed", "Belum dijawab / sebagian dijawab / sudah dijawab "
                                          "oleh paper 2024+."),
        ("strong match", "Paper yang memuat ≥50% kata kunci gap di judul+abstraknya."),
        ("throttle", "OpenAlex membatasi permintaan; saat kena, gap dihitung 'open' secara "
                     "konservatif — jadi angka open bisa terlalu optimistis."),
    ],
    "recommendation": [
        ("skor prioritas", "0,5×keyakinan gap + 0,3×kredit kebaruan + 0,2×keterlaksanaan. "
                           "Maksimum 1,0."),
        ("sweet spot", "Rentang kebaruan 0,25–0,65: cukup baru tapi masih di bidang yang "
                       "sama. Di luar rentang ini kreditnya dipotong."),
        ("tema", "Kelompok gap yang mirip satu sama lain. Tema yang didukung beberapa jurnal "
                 "lebih kuat daripada satu jurnal yang banyak bicara."),
        ("jurnal pendukung", "Berapa jurnal berbeda ada di satu tema. Pada tema besar ini "
                             "batas atas, bukan bukti kesepakatan."),
    ],
}


def mode_teknis() -> bool:
    return bool(st.session_state.get("mode_teknis", False))


def label(key: str) -> str:
    """Nama tampilan untuk kunci metrik/kolom."""
    if mode_teknis():
        return key
    entry = METRIC_LABELS.get(key) or FIELD_LABELS.get(key)
    return entry[0] if entry else key.replace("_", " ")


def help_of(key: str) -> str | None:
    entry = METRIC_LABELS.get(key) or FIELD_LABELS.get(key)
    return entry[1] or None if entry else None


def enum_label(field: str, value) -> str:
    """Nilai enum dengan padanan awam; mode teknis menampilkan nilai asli."""
    entry = ENUM_LABELS.get(field, {}).get(str(value))
    if not entry:
        return str(value)
    return str(value) if mode_teknis() else f"{entry[0]} ({value})"


def enum_help(field: str, value) -> str:
    entry = ENUM_LABELS.get(field, {}).get(str(value))
    return entry[1] if entry else ""


def render_glossary(stage_key: str) -> None:
    items = GLOSSARY.get(stage_key)
    if not items:
        return
    with st.expander("📚 Arti istilah di tahap ini", expanded=False):
        for term, meaning in items:
            st.markdown(f"**{term}** — {meaning}")
