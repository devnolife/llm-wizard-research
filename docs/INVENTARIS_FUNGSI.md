# Inventaris Fungsi & Tugas — Wizard Research

<a id="bagian-00"></a>
## Bagian 00 — Pengantar & peta arsitektur

> Dibuat otomatis dari pembacaan kode sumber pada branch `streamlit-ui` (commit `9b227d8`), 9 Sep 2026.
> Cakupan: 225 file Python (~57.600 baris) — 1.479 fungsi/kelas non-tes (173 file, 100 % terdokumentasi, diverifikasi via AST) + 806 fungsi tes di 51 file.

## 1. Gambaran umum

**Wizard Research** adalah prototipe riset (tesis S2 Teknik Informatika Unhas) berupa *Neuro-Symbolic Agentic System* untuk mendeteksi **indikator synthesis gap** (Cooper 1998 / Booth): *fragmentation*, *inconsistency*, *incompleteness* — pada kumpulan jurnal ilmiah yang diunggah pengguna.

Pipeline 4 fase:

| Fase | Tugas | Modul utama |
|---|---|---|
| 1. Ingestion | PDF → OCR/parse → bersihkan → chunk per-section → embed → ChromaDB | `core/pipeline/`, `utils/document_processor.py`, `utils/ocr_client.py`, `core/retrieval/vector_store.py` |
| 2. Fact Extraction | Ekstraksi entitas & relasi → triple SPO → Knowledge Graph | `core/knowledge/`, `core/knowledge_graph/` |
| 3. Agentic Analysis | LangGraph: Observe → Think → Act (tools) → Evaluate (self-critique) → loop | `core/agents/coordinator.py`, `core/agents/tools/` |
| 4. Validation | Rule Engine 9 aturan → verdict PASS / FLAG / REJECT; NLI; kalibrasi | `core/validation/`, `core/gap_detection/calibration.py` |

Di atas 4 fase itu ada dua "jalur" pekerjaan (job) yang dikelola antrean `services/analysis_queue.py`:

- **Legacy 8-stage auto-analysis** (`api/auto_analysis.py`) → dipanggil `POST /api/upload-and-analyze`; fase: `ingestion → topics → paper_analysis → neuro_symbolic → summary → gaps → proposal → roadmap`; menghasilkan indikator gap antar-jurnal + KG + proposal/roadmap.
- **Research pipeline bertahap** (`services/research_pipeline.py`, `PIPELINE_NAME="research"`) → `POST /api/research/start` + `/{job}/continue`; tahap `RESEARCH_STAGES`: `chunking → gap_mining → novelty → recommendation` (bisa dihentikan di tahap mana pun dengan `until=`, dilanjutkan dengan `continue`, dan diulang dari tahap tertentu dengan `start_from=`).

Antarmuka pengguna: **Streamlit** di `tools/process_monitor/` (port 8501) yang memanggil FastAPI (port 8001). Halaman pembuka adalah **🧭 Wizard** 4 langkah (unggah & chunk → gap mining → indikator neuro-symbolic → judul siap-pakai).

## 2. Peta direktori → tanggung jawab

```
backend/app/
├── main.py                  Entry FastAPI: lifespan (init vector store, cek OCR, start queue, cleanup job kadaluarsa),
│                            CORS, telemetry middleware, rate-limit, mount 7 router.
├── api/
│   ├── routes/health.py     GET /, /health, /api/system-stats, /api/sources/status, /api/models (+switch)
│   ├── routes/documents.py  /api/ingest, /api/search, /api/stats, DELETE /api/documents/{id}
│   ├── routes/papers.py     /api/papers/* — search, idea-to-query, fetch-pdf, download-and-analyze, ingest-external, batch-ingest
│   ├── routes/analysis.py   /api/upload-and-analyze, /api/analysis-status/{job}(+events/artifacts/chunks/cancel/retry),
│   │                        /api/analysis-jobs, /api/gaps, /api/recommend, /api/chat, /api/analyze-selection, /api/kg/graph, /api/stream/{job}
│   ├── routes/graph.py      GET /api/graph — Knowledge Graph (NetworkX)
│   ├── routes/skills.py     /api/skills (list), /api/skills/ask, /api/skills/recommend
│   ├── routes/research.py   /api/research/* — stages, chunk-preview, start, {job}/continue, {job}/records/{phase}, {job}/fulltext
│   ├── auto_analysis.py     Worker 8-stage legacy analysis (dijalankan antrean)
│   └── dependencies.py      Singleton/DI: document processor, vector store, LLM, dsb.
├── core/
│   ├── pipeline/            Ingestion deterministik: layout, cleaning, section normalizer, token chunker,
│   │                        dedup, references, metadata resolver (Crossref/OpenAlex), corpus relevance
│   ├── retrieval/           ChromaDB vector store, RAG retriever 2 tahap, cross-encoder reranker
│   ├── knowledge/           Fact extractor (LLM → SPO), fact table
│   ├── knowledge_graph/     Graph builder (NetworkX) + metrik
│   ├── gap_detection/       Analyzer 3 indikator + paper profiles, coverage map/axes, workflow stages,
│   │                        citation coupling, support gap, quote grounding, adjudication, calibration
│   ├── gap_mining/          Tambang kandidat gap per-chunk via LLM, verifikasi verbatim, novelty
│   ├── recommendation/      Engine rekomendasi topik, tema lintas-jurnal, novelty (OpenAlex)
│   ├── validation/          Rule engine 9 aturan, relation classifier 3-lapis, model NLI
│   ├── agents/              Koordinator LangGraph + agen (gap_detector, recommender, research_analyzer)
│   │   └── tools/           rag, kg_querier, nli_checker, paper_analyzer, self_critic
│   └── runtime/             AnalysisContext — konteks bersama satu job
├── services/
│   ├── llm_service.py       Abstraksi LLM (Ollama / GitHub Copilot SDK), embeddings
│   ├── copilot_client.py    Klien Copilot SDK (konkurensi, lifecycle)
│   ├── analysis_queue.py    Antrean job berbasis worker thread
│   ├── research_pipeline.py Pipeline riset bertahap (until / continue / start_from)
│   ├── reference_enrichment.py  Perkaya referensi via API
│   ├── skill_guidance.py    Panduan skill (Markdown) untuk UI
│   └── paper_apis/          arXiv, Semantic Scholar, CORE, Crossref, OpenAlex, PubMed, Europe PMC,
│                            Scopus, ScienceDirect, Unpaywall, GROBID + aggregator + http_cache
├── utils/                   config_loader (YAML + env), document_processor (ocrd→pypdf), ocr_client,
│                            job_store (persistensi job JSON), rate_limit, upload_validation, url_guard
├── models/                  Skema Pydantic request/response
└── telemetry/recorder.py    Middleware telemetri request

backend/experiments/         Skrip evaluasi tesis (benchmark gap, retrieval metrics, expert eval, laporan akhir)
backend/scripts/             CLI operasional (run_pipeline, mine_gaps, check_novelty, reindex, vectorstore, doctor)
backend/tests/               52 file pytest
tools/process_monitor/       UI Streamlit (Wizard 4 langkah + halaman teknis per tahap)
flood-geoai-research/        Proyek riset terpisah (fusion & XAI banjir) — tidak terkait pipeline utama
generate_paper_figures.py    Membuat gambar untuk paper
```

## 3. Cara membaca dokumen ini

Bagian-bagian berikut (01–08) memuat inventaris **per file → per kelas/fungsi**, satu baris per fungsi, dengan penanda apakah fungsi tersebut:
- memanggil **LLM** (Ollama/Copilot),
- memanggil **jaringan** (OpenAlex, Crossref, arXiv, dsb.),
- memakai **model lokal** (embedding / cross-encoder / NLI),
- atau murni **rule-based/simbolik**.

Setiap direktori ditutup dengan "**Alur utama**" yang menjelaskan siapa memanggil siapa.

---

## Daftar isi

- [Bagian 00 — Pengantar & peta arsitektur](#bagian-00)
- [Bagian 01 — core/gap_detection — deteksi indikator synthesis gap](#bagian-01)
- [Bagian 02 — core/agents, knowledge, knowledge_graph, validation](#bagian-02)
- [Bagian 03 — core/pipeline, retrieval, recommendation, gap_mining, runtime, models, telemetry, main.py](#bagian-03)
- [Bagian 04 — api — endpoint FastAPI](#bagian-04)
- [Bagian 05 — services, utils, scripts](#bagian-05)
- [Bagian 06 — experiments — skrip evaluasi tesis](#bagian-06)
- [Bagian 07 — tools/process_monitor (UI Streamlit), flood-geoai-research, generate_paper_figures, Makefile](#bagian-07)
- [Bagian 08 — tests — ringkasan suite pytest](#bagian-08)


<a id="bagian-01"></a>
# Bagian 01 — core/gap_detection — deteksi indikator synthesis gap

## backend/app/core/gap_detection/

### `backend/app/core/gap_detection/__init__.py` — modul ekspor: `from .analyzer import GapAnalyzer`; `__all__ = ["GapAnalyzer"]`.

### `backend/app/core/gap_detection/analyzer.py` — mesin deteksi synthesis gap tingkat-atas; mengorkestrasi indikator fragmentation, inconsistency, incompleteness, dan support gap dari paper + side-channel profil, lalu menambah corroboration, rule-engine validation, calibration, dan provenance.
**Konstanta penting:** `_ASPECT_STOPWORDS` — stopword untuk pemecahan aspek agar grounding/quote matching memakai kata isi; `GapIndicatorType` — alias kompatibilitas untuk `IndicatorType`.
**Kelas:**
- `GapIndicator` — model internal satu indikator gap; menyimpan `indicator_type`, `description`, `confidence`, `related_papers`, `evidence`, `suggested_directions`, `requires_human_validation`, `rule_engine_verdict`, `adjusted_confidence`, `detection_method`, `sub_indicators`, `supporting_quotes`, `evidence_subgraph`, `calibrated_confidence`, `needs_review`, `abstention_reasons`, `calibration`, `provenance`.
  - `to_dict()` — serialisasi indikator ke dict ringkas untuk API/penyimpanan.
  - `to_model()` — ubah `GapIndicator` ke `GapIndicatorModel` respons API.
- `GapAnalyzer` — engine utama yang menghubungkan vector store, KG, LLM, fact table, relation classifier, rule engine, dan calibrator.
  - `__init__(vector_store, knowledge_graph, llm_interface, fact_table, relation_classifier, rule_engine)` — simpan dependensi, load calibrator, inisialisasi cache profil per-jurnal.
  - `analyze_gaps(topic, papers, depth="standard", paper_profiles=None) -> List[GapIndicator]` — jalankan pipeline utama berurutan: fragmentation → inconsistency → incompleteness → support gap → corroborate → validate rule engine → calibrate/provenance; tiap indikator membawa `detection_method` berbeda.
  - `analyze_gaps_as_models(topic, papers, depth="standard", paper_profiles=None) -> List[GapIndicatorModel]` — wrapper API yang mengembalikan model respons.
  - `_detect_fragmentation(topic, papers) -> List[GapIndicator]` — cari fragmentasi lewat clustering pendekatan, isolasi struktural KG, dan bibliographic coupling.
  - `_detect_bibliographic_fragmentation(topic, existing) -> List[GapIndicator]` — fragmentasi dari daftar referensi; mengelompokkan jurnal yang tidak berbagi sitiran atau saling sitir (bebas LLM).
  - `_detect_inconsistency(topic, papers) -> List[GapIndicator]` — cari kontradiksi lewat FactTable, NLI teradjudikasi, lalu LLM fallback.
  - `_validate_contradiction(fact, subject, obj)` — validasi satu fakta `CONTRADICTS` agar hanya klaim yang sebanding dan terverifikasi relation classifier yang lolos.
  - `_detect_incompleteness(topic, papers) -> List[GapIndicator]` — cari kekosongan kolektif lewat aspek yang diharapkan, Evidence Gap Map, dan fallback homogenitas metode.
  - `_detect_workflow_homogeneity(topic, workflows) -> Optional[GapIndicator]` — incompleteness dari stage workflow yang seragam lintas jurnal.
  - `_detect_support_gap(topic, papers) -> List[GapIndicator]` — gap karena klaim berulang tidak bisa di-ground ke bukti primer.
  - `_corroborate_with_author_statements(indicators) -> None` — tambahkan weakness/author gap sebagai bukti pendukung tanpa mengubah confidence inti.
  - `_profiles_for_indicator(indicator) -> List[PaperProfile]` — pilih profil yang relevan untuk corroboration, fallback ke semua profil.
  - `_indicator_needles(indicator) -> List[str]` — turunkan kata/frasa target dari indikator untuk matching statement.
  - `_validate_with_rule_engine(indicators) -> List[GapIndicator]` — kirim indikator ke rule engine, set verdict/adjusted confidence, buang yang REJECT.
  - `_apply_calibration(indicator, verdict_value, report=None) -> None` — terapkan calibrator, `needs_review`, abstention reasons, dan provenance chain.
  - `_summarize_rule_report(report) -> str` — ringkas aturan yang benar-benar firing.
  - `_extract_evidence_subgraph(entity_a_id, entity_b_id, max_edges=10) -> List[Dict[str, Any]]` — ambil sub-graf KG penghubung dua entitas (NetworkX).
  - `_link_kg_entities(indicator) -> Dict[str, Any]` — kaitkan indikator ke entitas METHOD/DOMAIN/FINDING agar rule engine bisa reasoning.
  - `_calibrate_fragmentation_confidence(clusters, paper_approaches, cluster_result=None) -> float` — hitung confidence fragmentasi dari separasi cluster dan metrik graf.
  - `_detect_contradictions_nli(topic, papers) -> List[GapIndicator]` — pipeline NLI teradjudikasi: normalize claims → align variables → extract direction → NLI (model lokal) → adjudicate heterogeneity → label.
  - `_extract_approaches(papers) -> Dict[str, List[str]]` — ekstrak keyword/metode untuk clustering fragmentasi.
  - `_cluster_approaches(paper_approaches) -> Dict[int, List[str]]` — wrapper clustering berbasis `graph_metrics.cluster_papers`.
  - `_analyze_structural_isolation(papers) -> Dict[str, Any]` — ukur isolasi entitas KG dan ranking bridge candidate.
  - `_compute_isolation_score(papers) -> float` — view skalar kompatibel dari `_analyze_structural_isolation`.
  - `_detect_contradictions_llm(topic, papers) -> List[GapIndicator]` — fallback **LLM** untuk kontradiksi; kutipan diverifikasi ke korpus.
  - `_extract_covered_aspects(papers) -> Set[str]` — kumpulkan aspek yang sudah tercakup dari keywords dan isi paper.
  - `_ground_aspects(aspects, papers) -> tuple` — pisahkan aspek grounded vs ungrounded berbasis kata isi di korpus.
  - `_identify_expected_aspects(topic) -> List[str]` — pakai **LLM** untuk menebak aspek penting topik.
  - `_extract_methods(papers) -> Set[str]` — ekstrak metode dari teks paper untuk incompleteness berbasis homogeneity.
  - `find_contradictions(papers) -> List[GapIndicator]` — API legacy, memanggil `_detect_inconsistency`.
**Fungsi (level modul):**
- `aspect_terms(aspect: str) -> List[str]` — memecah frasa aspek panjang menjadi kata isi (>3 huruf, bukan `_ASPECT_STOPWORDS`) yang dipakai bersama oleh uji grounding dan ekstraktor kutipan agar rantai provenance tidak putus.
- `_paper_ref(paper) -> str` — referensi stabil & terbaca untuk sebuah paper: prioritas `source` (nama file) → `title` → `doc_id`/`id`, agar `related_papers` menyebut jurnal nyata.
- `_short_ref(name, limit=40) -> str` — nama file tanpa prefiks indeks job-dir (`NN_`), dipotong ke `limit` karakter untuk baris evidence.
- `_paper_refs(papers) -> List[str]` — daftar referensi unik, terurut, non-kosong dari sekumpulan paper (memakai `_paper_ref`).
**Fungsi bersarang:**
- `_node_name(node_id)` — di dalam `_extract_evidence_subgraph`; ambil nama node KG (fallback ke id).
- `_add_path(paths)` — di dalam `_extract_evidence_subgraph`; ubah path menjadi daftar edge evidence terdeduplikasi.

**Urutan `analyze_gaps` dan `detection_method` tiap indikator:**
- fragmentation → `_detect_fragmentation`: `topic_clustering`; bila KG + fact table ada, isolasi struktural ditandai `citation_isolation`; fragmentasi bibliografis dari `_detect_bibliographic_fragmentation` memakai `bibliographic_coupling`.
- inconsistency → `_detect_inconsistency`: FactTable `CONTRADICTS` → `fact_table_contradicts`; NLI teradjudikasi → `nli_adjudicated` (bila NLI tersedia) atau `claim_adjudication`; fallback LLM → `llm_nli`.
- incompleteness → `_detect_incompleteness`: aspek semantik → `aspect_coverage`; Evidence Gap Map → `evidence_gap_map`; workflow homogeneity → `workflow_stage_mining`; fallback metode seragam → `methodology_coverage`.
- support gap → `_detect_support_gap`: `evidence_support`.
- Sesudah itu indikator dikorroborasi pernyataan penulis, divalidasi rule engine, lalu dikalibrasi dan dibangun provenance-nya.

### `backend/app/core/gap_detection/paper_profiles.py` — side-channel per jurnal untuk menyimpan weakness penulis, gap yang dinyatakan penulis, workflow, dan referensi agar bukti bisa di-join dengan passage RAG.
**Konstanta penting:** `AUTHOR_GAP_KINDS` — jenis gap yang dinyatakan penulis; `WEAKNESS_KINDS` — jenis weakness tersurat/tersirat.
**Kelas:**
- `PaperProfile` — profil satu jurnal unggahan; field penting: `source`, `title`, `doi`, `year`, `weaknesses`, `author_gaps`, `workflow`, `references`.
  - `key` — normalisasi key berbasis `source`.
  - `statements()` — ubah weaknesses dan author gaps menjadi statement evidence untuk corroboration.
  - `to_dict()` — serialisasi profil ke dict.
  - `from_dict(data) -> PaperProfile` — rehidrasi profil dari dict.
**Fungsi:**
- `normalize_source(name) -> str` — normalisasi basename sumber agar indeks job-dir/pemisah path hilang dan join key konsisten.
- `build_profiles(paper_contents, weaknesses=None, author_gaps=None, workflows=None, references=None) -> Dict[str, PaperProfile]` — bangun satu profil per paper terunggah dan isi side-channel dari sumber lain.
- `profiles_from_context(raw) -> Dict[str, PaperProfile]` — rehidrasi profil dari context agent (dict atau object).
- `profile_for(paper, profiles) -> Optional[PaperProfile]` — cari profil jurnal untuk dict paper/passage lewat doc_id/id/source/title/metadata.
- `_nonempty(*parts) -> List[str]` — kumpulkan string non-kosong yang sudah di-trim.
- `_as_float(value) -> Optional[float]` — konversi aman ke float untuk confidence/score.

### `backend/app/core/gap_detection/adjudication.py` — adjudikator kontradiksi dua klaim; memisahkan kontradiksi sejati dari heterogenitas, non-comparable, dan inconclusive berdasarkan alignment, arah efek, statistik heterogenitas, dan skor NLI (murni rule-based/statistik; NLI hanya masukan).
**Konstanta penting:** `Q_TEST_ALPHA` — ambang signifikansi heterogenitas; `I2_BANDS` — band I²; `I2_RANDOM_EFFECTS_THRESHOLD` — ambang random-effects; `TAU2_SUBSTANTIAL` — ambang τ²; `NLI_NOISE_FLOOR` — floor skor NLI agar noise tidak dihitung sebagai bukti; `_MODERATOR_CUES` — cue moderator/heterogenitas; `_DESIGN_CUES` — cue desain studi.
**Kelas:**
- `Adjudication` — Enum empat kelas: `CONTRADICTION`, `HETEROGENEOUS`, `NON_COMPARABLE`, `INCONCLUSIVE`.
- `AdjudicationResult` — hasil adjudikasi satu pasangan klaim; field: `label`, `confidence`, `reason`, `alignment`, `nli_score`, `heterogeneity`.
  - `is_contradiction` — property; true jika label `CONTRADICTION`.
  - `to_dict()` — serialisasi hasil adjudikasi (confidence & nli_score dibulatkan 3 desimal).
**Fungsi:**
- `cochran_q(effects, variances) -> float` — hitung statistik Q Cochran heterogenitas antar studi.
- `i_squared(q_stat, k_studies) -> float` — hitung I² (%).
- `tau_squared(q_stat, k_studies, variances) -> float` — estimasi DerSimonian–Laird varians antar studi.
- `_chi_square_p_value(q_stat, df) -> float` — aproksimasi p-value chi-square upper-tail tanpa scipy.
- `i2_band(i2_value) -> str` — petakan I² ke band negligible/low/moderate/substantial.
- `assess_heterogeneity(effects, variances) -> Dict[str, Any]` — ringkas seluruh metrik heterogenitas dan labelnya.
- `_has_cue(text, cues) -> bool` — cek kemunculan cue kata/frasa pada teks (lowercase).
- `_designs_differ(claim_a, claim_b) -> bool` — cek apakah desain studi berbeda dari cue desain di teks klaim.
- `_directions_oppose(claim_a, claim_b) -> bool` — cek apakah `signed_direction` kedua klaim termasuk pasangan berlawanan (increase/decrease/no_effect/not_*).
- `adjudicate_contradiction(claim_a, claim_b, nli_score=0.0, embedder=None, alignment=None, effect_estimates=None, effect_variances=None) -> AdjudicationResult` — jalankan urutan comparability → signal adequacy → heterogeneity explanation → contradiction; NLI hanya salah satu evidence term, bukan keputusan tunggal.
**Fungsi bersarang:**
- `designs(claim)` — di dalam `_designs_differ`; ekstrak himpunan cue desain yang muncul pada klaim.

### `backend/app/core/gap_detection/claim_normalization.py` — normalisasi klaim ilmiah menjadi proposisi terbandingkan, lalu alignment PICO/variabel untuk pipeline kontradiksi; pure Python dengan embedder opsional.
**Konstanta penting:** `ALIGNMENT_GATE` — ambang skor agar dua klaim dianggap comparable; `PICO_FIELDS` — field konteks yang disejajarkan; `_FIELD_WEIGHTS` — bobot tiap field; pola regex `_INCREASE_PATTERNS`, `_DECREASE_PATTERNS`, `_NULL_PATTERNS`, `_NEGATION_PATTERNS`, `_QUANTITY_RE`, `_SENTENCE_SPLIT_RE`, `_CLAIM_CUES`, `_STOPWORDS`, `_ABBREVIATION_RE`.
**Kelas:**
- `NormalizedClaim` — klaim tunggal yang dipecah jadi subject/relation/object/direction/polarity/unit/value/pico/terms.
  - `to_dict()` — serialisasi klaim ternormalisasi.
  - `signed_direction` — property; arah setelah memperhitungkan negasi (`increase` → `not_increase`, dst.).
- `AlignmentResult` — hasil alignment dua klaim; field: `score`, `matched_fields`, `mismatched_fields`, `missing_fields`, `relaxed`, `lexical_overlap`.
  - `comparable` — property; true jika skor melewati `ALIGNMENT_GATE`.
  - `to_dict()` — serialisasi hasil alignment.
**Fungsi:**
- `_expand_abbreviations(text) -> str` — perluas akronim `Long Form (LF)` agar konsep sepadan tidak diperlakukan berbeda.
- `_match_any(patterns, text) -> bool` — helper regex OR.
- `extract_direction(text) -> str` — klasifikasikan arah efek: `increase`, `decrease`, `no_effect`, atau `unknown`.
- `extract_polarity(text) -> str` — deteksi negasi kalimat setelah null-effect dikecualikan.
- `extract_quantity(text) -> Tuple[Optional[float], str]` — ambil magnitudo numerik + unit pertama.
- `content_terms(text, min_len=4) -> List[str]` — ekstrak content words untuk overlap leksikal.
- `_split_spo(sentence) -> Tuple[str, str, str]` — split subject/relation/object kasar di sekitar kata kerja efek.
- `_pico_from_metadata(paper) -> Dict[str, str]` — ambil field PICO dari metadata nested/flat.
- `is_claim_sentence(sentence) -> bool` — filter kalimat yang benar-benar menyatakan finding.
- `normalize_claims(paper, paper_ref, max_claims=5, max_chars=4000) -> List[NormalizedClaim]` — ubah teks paper menjadi klaim terurut, prioritaskan klaim berarah.
- `_jaccard(a, b) -> float` — similaritas leksikal Jaccard.
- `_text_similarity(a, b, embedder=None) -> float` — similaritas leksikal; naik ke cosine embedding bila embedder tersedia.
- `align_claims(claim_a, claim_b, embedder=None) -> AlignmentResult` — skor keterbandingan klaim berbasis PICO + overlap leksikal/semantik; mode relaxed bila struktur tidak lengkap.

**Alur utama (bagian A):**
- `GapAnalyzer.analyze_gaps()` memanggil `_detect_fragmentation()`, `_detect_inconsistency()`, `_detect_incompleteness()`, lalu `_detect_support_gap()`, kemudian `_corroborate_with_author_statements()`, lalu `_validate_with_rule_engine()` (atau `_apply_calibration()` langsung bila rule engine tidak ada).
- `_detect_inconsistency()` memakai `claim_normalization.normalize_claims()` dan `adjudication.adjudicate_contradiction()`, yang di dalamnya memanggil `claim_normalization.align_claims()` serta `adjudication.assess_heterogeneity()` bila data efek tersedia.
- `paper_profiles.build_profiles()` menghasilkan `PaperProfile` yang dibaca `profiles_from_context()` di `GapAnalyzer.analyze_gaps()`; dari sana `_corroborate_with_author_statements()` dan `_detect_bibliographic_fragmentation()` memakai `PaperProfile.statements()` / `PaperProfile.references`.
- `GapAnalyzer` mengimpor modul saudara: `calibration`, `citation_coupling`, `coverage_axes`, `coverage_map`, `graph_metrics`, `quote_grounding`, `semantic_match`, `support_gap`, `workflow_stages`, plus `paper_profiles`, `claim_normalization`, dan `adjudication`.

### `backend/app/core/gap_detection/calibration.py` — kalibrasi confidence, abstention selektif, dan jejak provenance untuk indikator gap. Modul ini menghitung metrik kalibrasi, mem-fit temperature scaling + conformal cutoff dari label ahli, lalu membentuk rantai provenance claim→kutipan→validasi.
**Konstanta penting:** `DEFAULT_BINS` — jumlah bin reliability/ECE; `MIN_CALIBRATION_LABELS` — minimum label agar kalibrator tidak sekadar identity map; `ABSTENTION_THRESHOLD` — ambang confidence terkalibrasi di bawah ini indikator ditahan; `CONFORMAL_ALPHA` — tingkat miscoverage conformal; `_VERDICT_MULTIPLIER` — pengaruh verdict rule engine ke confidence; `DEFAULT_LABEL_FILENAME` — nama file label kalibrasi.
**Fungsi:**
- `expected_calibration_error(confidences, correctness, n_bins)` — menghitung ECE dengan equal-width bins: rata-rata tertimbang `|acc-bin - conf-bin|`.
- `brier_score(confidences, correctness)` — menghitung Brier score dua kelas dari probabilitas positif/negatif vs label benar/salah.
- `reliability_bins(confidences, correctness, n_bins)` — membangun bin reliability berisi jumlah sampel, akurasi, dan mean confidence per bin.
- `risk_coverage_curve(confidences, correctness)` — menghitung kurva selective risk saat sampel diurutkan dari confidence tertinggi.
- `area_under_risk_coverage(confidences, correctness)` — merangkum AURC dari kurva risk-coverage; makin kecil makin baik.
- `_logit(p, eps)` — transformasi logit dengan clipping numerik.
- `_sigmoid(z)` — fungsi sigmoid numerik stabil.
- `fit_temperature(confidences, correctness, grid)` — mencari temperature `T` terbaik via grid search yang meminimalkan NLL.
- `apply_temperature(confidence, temperature)` — menerapkan temperature scaling ke satu confidence.
- `conformal_threshold(confidences, correctness, alpha)` — menghitung cutoff split-conformal berbasis kuantil positif untuk abstention.
- `evaluate_calibration(confidences, correctness, n_bins)` — menggabungkan ECE, Brier, AURC, reliability bins, dan risk-coverage dalam satu laporan.
- `build_provenance(claim, cited_records, retrieved_passages, validation_outcome, validation_detail)` — menyusun `ProvenanceChain` untuk satu indikator.
- `_label_path(path)` — menentukan lokasi file label dari argumen/env/default `backend/data/calibration_labels.json`.
- `load_calibrator(path)` — memuat label expert, mem-fit `Calibrator`, atau kembali ke kalibrator identity bila label kurang/rusak.
**Kelas:**
- `Calibrator` — kalibrator post-hoc dengan field penting `temperature`, `conformal_cutoff`, `abstention_threshold`, `fitted`, `n_labels`; `fit(...)` mem-derive parameter dari label; `calibrate(raw_confidence, rule_verdict)` menerapkan temperature scaling, fusi verdict `PASS/FLAG/REJECT`, dan keputusan `needs_review`.
- `ProvenanceChain` — dataclass jejak traceability minimum; field penting `claim`, `cited_records`, `retrieved_passages`, `validation_outcome`, `validation_detail`; properti `complete` dan `broken_links` mengecek kelengkapan rantai.
**Properti/metode kelas:**
- `Calibrator.fit(...)` — fit temperature + conformal cutoff dari pasangan confidence/benar.
- `Calibrator.calibrate(raw_confidence, rule_verdict)` — mengeluarkan confidence terkalibrasi, alasan abstain, dan flag review.
- `ProvenanceChain.complete` — mengecek apakah semua link provenance hadir.
- `ProvenanceChain.broken_links` — mengembalikan daftar link yang hilang.
- `ProvenanceChain.to_dict()` — serialisasi chain dengan pemangkasan panjang.
- `Calibrator.fit(...)` — line 254 dst; `Calibrator.calibrate(...)` — line 264 dst; `load_calibrator(...)` — line 388 dst (lihat file lengkap).
- `_label_path(...)` — line 377 dst; `evaluate_calibration(...)` — line 298 dst.

### `backend/app/core/gap_detection/citation_coupling.py` — deteksi fragmentasi lewat bibliographic coupling antar jurnal/unggahan. Modul ini membangun graf kopling dari daftar pustaka terurai, menghitung pasangan dengan referensi bersama, sitasi langsung antar paper, komponen terhubung, modularitas, dan skor isolasi.
**Konstanta penting:** `MIN_REFS_PER_PAPER` — minimum referensi terurai agar paper ikut dianalisis; `MIN_PAPERS` — minimum paper eligible agar kopling bermakna; `EDGE_THRESHOLD` — bobot minimum untuk sisi sitasi langsung; `_TITLE_MATCH_WORDS` — ambang kata-isi judul untuk direct-citation berbasis title matching.
**Kelas:**
- `CouplingResult` — ringkasan hasil kopling; field penting `papers`, `eligible`, `skipped`, `pairs`, `direct_citations`, `components`, `modularity`, `disconnected_pairs`, `total_pairs`, `top_shared`, `interpretation`, `skipped_reason`; properti `fragmented` dan `isolation_score`.
**Properti/metode kelas:**
- `CouplingResult.fragmented` — true bila interpretasi “fragmented”.
- `CouplingResult.isolation_score` — `disconnected_pairs / total_pairs`.
- `CouplingResult.to_dict()` — serialisasi hasil plus threshold penting.
**Fungsi:**
- `_profile_view(profile)` — menormalkan `PaperProfile`/dict menjadi `(source, title, doi, entries)`.
- `_direct_citation(entries, title, doi)` — mendeteksi apakah daftar referensi mengutip paper unggahan via DOI yang sama atau kemiripan judul berbasis kata-isi.
- `build_coupling_graph(profiles, min_refs, min_papers)` — membangun matriks kopling, direct citation, komponen terhubung, modularitas Newman, dan interpretasi fragmentasi.
**Dependensi utama:** memakai `connected_components` dan `compute_modularity` dari `graph_metrics.py`.

### `backend/app/core/gap_detection/coverage_axes.py` — resolver sumbu Evidence Gap Map yang sadar domain. Modul ini memilih sumbu dari kurasi YAML, lalu fallback ke usulan LLM yang digrounding ke korpus, lalu fallback terakhir ke kosakata bawaan.
**Konstanta penting:** `MAX_AXIS_TERMS` — batas istilah per sumbu; `MIN_AXIS_TERMS` — minimum baris/kolom valid; `_SNIPPET_PAPERS` dan `_SNIPPET_CHARS` — pembatas cuplikan korpus untuk prompt; `AXES_SOURCES` — asal sumbu valid (`curated`, `llm_grounded`, `default`); `_AXES_PROMPT` — prompt generasi sumbu.
**Kelas:**
- `AxesSpec` — spesifikasi sumbu EGM; field penting `rows`, `columns`, `source`, `slug`, `important_columns`, `aliases`, `dropped_ungrounded`, `notes`.
**Fungsi:**
- `default_axes(note)` — mengembalikan `AxesSpec` bawaan dari `_DEFAULT_ROW_TERMS/_DEFAULT_COLUMN_TERMS`.
- `slugify(topic)` — mengubah topik ke slug aman untuk nama file YAML.
- `axes_dir(path)` — menentukan direktori ontology dari argumen/env/default `backend/data/ontology`.
- `_clean_terms(values, limit)` — normalisasi istilah: lowercase, trim, dedup, batasi jumlah.
- `_parse_yaml_spec(raw, slug)` — mengubah YAML kurasi menjadi `AxesSpec` bila baris/kolom cukup.
- `_matches_topic(raw, stem, topic)` — cek kecocokan YAML ke topik via slug atau `match`.
- `load_curated_axes(topic, directory)` — mencari YAML kurasi pertama yang cocok dan valid.
- `_corpus_text(papers)` — menggabungkan konten korpus menjadi string lowercase.
- `grounded_terms(terms, corpus_text)` — memisahkan istilah yang benar-benar muncul di korpus vs yang tidak; istilah yang tidak grounded dibuang.
- `_extract_json_object(text)` — mengambil objek JSON pertama dari balasan LLM.
- `_snippets(papers)` — menyusun cuplikan korpus pendek untuk prompt LLM.
- `propose_axes(topic, papers, llm, n_terms)` — meminta LLM mengusulkan sumbu, lalu menyaring istilah yang tidak grounded; fallback ke bawaan bila gagal/tidak cukup.
- `resolve_axes(topic, papers, llm, directory)` — entry point prioritas: kurasi YAML > LLM+grounding > bawaan.
**Dependensi utama:** menggunakan `normalize_phrase` dari `semantic_match.py` dan `_DEFAULT_*` dari `coverage_map.py`.

### `backend/app/core/gap_detection/coverage_map.py` — pembangun Evidence Gap Map berbasis hitungan studi per sel, bukan skor weighted evidence. Modul ini memetakan paper ke sel baris×kolom, menandai sel kosong/tipis sebagai kandidat gap, dan memberi overlay “penting” berdasarkan aspek kritis.
**Konstanta penting:** `THIN_CELL_MAX` — batas sel dianggap “thin”; `_DEFAULT_ROW_TERMS` — sumbu baris bawaan generik; `_DEFAULT_COLUMN_TERMS` — sumbu kolom bawaan generik.
**Kelas:**
- `CoverageCell` — satu sel EGM; field penting `row`, `column`, `study_count`, `papers`, `important`; properti `status` mengklasifikasikan `empty/thin/covered`.
- `CoverageMatrix` — matriks EGM; field penting `rows`, `columns`, `cells`, `total_papers`, `unmapped_papers`; properti `empty_cells`, `thin_cells`, `density`.
**Properti/metode kelas:**
- `CoverageCell.status` — label status sel berdasarkan `study_count`.
- `CoverageCell.to_dict()` — serialisasi sel.
- `CoverageMatrix.cell(row, column)` — ambil sel atau sel kosong default.
- `CoverageMatrix.empty_cells` — semua sel kosong.
- `CoverageMatrix.thin_cells` — semua sel tipis.
- `CoverageMatrix.density` — proporsi sel yang terisi ≥1 studi.
- `CoverageMatrix.candidate_gaps(limit)` — sel kosong/tipis yang diurutkan menurut overlay penting.
- `CoverageMatrix.to_grid()` — bentuk tabel row-major untuk rendering.
- `CoverageMatrix.to_dict()` — serialisasi matrix lengkap, termasuk note bahwa sel kosong hanyalah kandidat.
**Fungsi:**
- `_axis_values(paper, keys)` — membaca nilai sumbu terstruktur dari metadata/paper.
- `_terms_present(text, terms, aliases)` — mencocokkan istilah kanonis di teks atau sinonimnya.
- `build_coverage_matrix(papers, row_terms, column_terms, important_columns, paper_ref, matcher, aliases)` — membangun matriks EGM; memakai field terstruktur dulu, lalu fallback ke pencocokan kosakata; satu paper bisa mengisi banyak sel.
- `mark_important_columns(matrix, critical_aspects, matcher)` — menandai kolom yang relevan secara keputusan dengan `SemanticMatcher`.
**Dependensi utama:** `SemanticMatcher` dari `semantic_match.py`.

### `backend/app/core/gap_detection/graph_metrics.py` — metrik fragmentasi berbasis graf untuk klasterisasi, kualitas klaster, deteksi singleton, dan ranking jembatan antar literatur. Modul ini menggantikan heuristik lama yang greedy/binary dengan pengelompokan komponen terhubung, modularitas, silhouette, overlap, dan link prediction klasik.
**Konstanta penting:** `Q_FRAGMENTED_MAX` — ambang Q untuk struktur fragmented; `Q_COHESIVE_MIN` — ambang Q untuk cohesive; `OVERLAP_FRAGMENTED_MAX` — overlap inter-klaster maksimum untuk signal fragmented; `CLUSTER_SIMILARITY_THRESHOLD` — ambang similarity penggabungan klaster; `GENERIC_ENTITY_MAX_RATIO` — batas entitas terlalu umum yang di-filter.
**Kelas:**
- `ClusterResult` — hasil klasterisasi dan kualitasnya; field penting `clusters`, `modularity`, `silhouette`, `inter_cluster_overlap`, `method`; properti `n_clusters` dan `interpretation`.
- `BridgeCandidate` — kandidat jembatan antar node; field penting `source`, `target`, `common_neighbors`, `jaccard`, `adamic_adar`, `resource_allocation`, `preferential_attachment`, `betweenness_broker`, `filtered_reason`, `intermediates`; properti `score` untuk peringkat gabungan.
- `GatingResult` — hasil rescue singleton; field penting `clusters`, `reassigned`, `ambiguous`, `coverage_before`, `coverage_after`.
**Properti/metode kelas:**
- `ClusterResult.n_clusters` — jumlah klaster.
- `ClusterResult.interpretation` — mengubah `Q`, silhouette, dan overlap menjadi label cohesive/fragmented/intermediate.
- `ClusterResult.to_dict()` — serialisasi ringkas metrik klaster.
- `BridgeCandidate.score` — skor ranking gabungan; Adamic-Adar dan resource allocation berbobot terbesar, lalu Jaccard dan preferential attachment.
- `BridgeCandidate.to_dict()` — serialisasi kandidat jembatan.
- `GatingResult.to_dict()` — serialisasi reassignment dan coverage.
**Fungsi:**
- `_squash(value)` — memetakan skor tak berbatas ke `[0,1)`.
- `_cosine(a, b)` — dot product cosine untuk vektor yang sudah dinormalisasi.
- `_jaccard_sets(a, b)` — Jaccard dua himpunan fitur.
- `_build_similarity_matrix(items, features, embedder)` — membangun matriks similarity; embedding jika tersedia, fallback lexical/Jaccard.
- `_connected_components(items, matrix, threshold)` — union-find komponen terhubung; nested `find` dan `union` di dalamnya.
- `connected_components(items, matrix, threshold)` — entry point publik untuk modul lain.
- `compute_modularity(items, matrix, clusters, threshold)` — Newman modularity `Q` pada graf similarity yang ditreshold.
- `compute_silhouette(items, matrix, clusters)` — rata-rata silhouette dengan distance `1 - similarity`.
- `compute_inter_cluster_overlap(clusters, features)` — mean Jaccard antar vocab klaster.
- `cluster_papers(features, embedder, threshold)` — entry point klasterisasi paper berdasarkan vocabulary pendekatan.
- `_entropy(weights)` — Shannon entropy ternormalisasi dari distribusi similarity.
- `rescue_singletons(features, result, embedder, entropy_threshold)` — memindah singleton ke centroid terdekat bila tidak ambigu; singleton yang terlalu ambigu dibiarkan.
- `link_prediction_scores(graph, node_a, node_b)` — menghitung CN, Jaccard, Adamic-Adar, resource allocation, preferential attachment, dan intermediates.
- `_generic_nodes(graph, max_ratio)` — memfilter node yang terlalu umum/hub.
- `rank_bridges(graph, candidate_pairs, node_names, node_types, node_years, top_k)` — memberi skor dan memfilter kandidat jembatan berdasarkan rarity, jenis, temporal plausibility, dan shared intermediate; mengembalikan `(kept, filtered)`.
**Dependensi utama:** bisa dipakai oleh `citation_coupling.py`; juga dipanggil dari `analyzer.py` untuk fragmentasi struktur.

### `backend/app/core/gap_detection/quote_grounding.py` — grounding kutipan verbatim untuk indikator gap. Modul ini mengekstrak kalimat asli dari chunk korpus yang memuat term kunci, dan memverifikasi kutipan LLM secara fuzzy agar halusinasi tidak lolos.
**Konstanta penting:** `QUOTE_MATCH_THRESHOLD` — ambang verifikasi fuzzy kutipan.
**Fungsi:**
- `normalize_text(s)` — lowercase + collapse whitespace untuk substring matching stabil.
- `fuzzy_contains(needle, haystack)` — mencari similarity terbaik `needle` terhadap window sepanjang sama di `haystack` dengan sweep kasar lalu halus.
- `split_sentences(text)` — pemisah kalimat sederhana untuk teks chunk paper.
- `_paper_label(paper)` — memilih label sumber yang paling stabil/readable dari metadata, source, title, atau id.
- `extract_supporting_quotes(terms, papers, max_quotes, max_sentence_len)` — mengambil kutipan verbatim dari paper yang memuat term indikator; satu kutipan per paper, diurutkan menurut jumlah term yang cocok.
- `verify_quote_against_papers(quote, papers)` — memeriksa apakah kutipan LLM benar-benar ada di salah satu paper; mengembalikan `verified`, `match_score`, dan `source_paper` bila lolos ambang.
**Sifat pemrosesan:** sepenuhnya rule-based/fuzzy string matching; tidak memakai LLM atau embedding.

### `backend/app/core/gap_detection/semantic_match.py` — pencocokan semantik aspek pendek dengan fallback deterministik. Modul ini menyelesaikan false positive “aspek tidak ditemukan” lewat embedding bila ada, atau lexical/stem matching bila offline.
**Konstanta penting:** `ASPECT_MATCH_THRESHOLD` — ambang similarity aspek untuk embedding; `LEXICAL_MATCH_THRESHOLD` — ambang lexical fallback; `_STOPWORDS` — kata buang; `_SUFFIXES` — suffix stemming; `_PREFIX_MATCH_MIN` — minimum prefix untuk fuzzy stem match.
**Kelas:**
- `AspectMatch` — hasil pencocokan satu aspek; field penting `aspect`, `covered`, `best_match`, `score`, `method`.
- `SemanticMatcher` — matcher phrase pendek; field `embedder`, `threshold`, cache embedding, dan flag kegagalan embedding.
**Properti/metode kelas:**
- `AspectMatch.to_dict()` — serialisasi hasil match.
- `SemanticMatcher.__init__(embedder=None, threshold=ASPECT_MATCH_THRESHOLD)` — menyimpan embedder opsional (model lokal), ambang similarity, cache embedding kosong, dan flag `_embedding_failed=False`.
- `SemanticMatcher.from_vector_store(vector_store, **kwargs)` — mengambil embedding_model dari vector store.
- `SemanticMatcher.uses_embeddings` — true bila embedder tersedia dan belum gagal.
- `SemanticMatcher._encode(texts)` — encode+cache embedding, fallback lexical bila gagal.
- `SemanticMatcher.similarity(a, b)` — memilih skor tertinggi antara lexical dan embedding cosine.
- `SemanticMatcher.best_match(aspect, candidates)` — menemukan kandidat paling dekat untuk satu aspek dan menentukan apakah covered.
- `SemanticMatcher.split_covered(expected, covered)` — memisahkan aspek yang covered vs uncovered.
**Fungsi:**
- `_stems_match(a, b)` — cek stem/prefix fuzzy.
- `_stem(word)` — buang suffix morfologis.
- `normalize_phrase(text)` — tokenisasi phrase ke stem content-word.
- `lexical_similarity(a, b)` — menghitung overlap stem-level dengan bonus containment.
**Dependensi utama:** dipakai oleh `coverage_map.py`, `coverage_axes.py`, `support_gap.py`, dan `workflow_stages.py`.

### `backend/app/core/gap_detection/support_gap.py` — deteksi evidence-support gap: klaim ada, tapi bukti primer di korpus tidak bisa digrounding. Modul ini melakukan leave-one-out retrieval atas klaim ternormalisasi, memberi label supported/weak/unsupported, dan mendeteksi citation echo serta hedge yang tidak terukur.
**Konstanta penting:** `SUPPORT_FLOOR`/`SUPPORT_GATE` — ambang support untuk mode embedding; `SUPPORT_FLOOR_LEXICAL`/`SUPPORT_GATE_LEXICAL` — ambang fallback lexical; `ECHO_THRESHOLD`/`ECHO_THRESHOLD_LEXICAL` — ambang claim echo; `ECHO_MIN_PAPERS` — minimum paper agar echo dihitung; `UNSUPPORTED_RATIO_MIN` — minimum proporsi unsupported untuk memicu indikator; `MAX_REPORTED_CLAIMS` — batas klaim yang dilaporkan.
**Kelas:**
- `SupportAssessment` — verdict grounding satu klaim; field penting `claim`, `support_score`, `status`, `gate`, `best_source`, `best_passage`, `echo_papers`, `hedged`, `source_is_secondary`, `reasons`; properti `is_gap` dan `severity`.
- `SupportReport` — ringkasan corpus-level; field penting `assessments`, `total_claims`, `unsupported`, `weakly_supported`, `supported`, `echo_claims`; properti `unsupported_ratio` dan `gaps`.
**Properti/metode kelas:**
- `SupportAssessment.is_gap` — true bila unsupported atau weakly_supported yang ter-echokan.
- `SupportAssessment.severity` — skor beratnya kekurangan grounding berdasarkan gap, echo, hedge, dan sumber sekunder.
- `SupportAssessment.to_dict()` — serialisasi verdict klaim.
- `SupportReport.unsupported_ratio` — proporsi klaim unsupported.
- `SupportReport.gaps` — daftar gap yang diurutkan menurut severity.
- `SupportReport.to_dict()` — serialisasi ringkasan dan gap teratas.
**Fungsi:**
- `_paper_text(paper, max_chars)` — mengambil teks konten/abstract/summary untuk indexing.
- `is_secondary_source(paper)` — mendeteksi review/survey/meta-analysis sebagai sumber sekunder.
- `has_primary_evidence(passage)` — heuristik apakah passage terdengar seperti hasil empiris primer.
- `build_evidence_index(papers, paper_ref, max_sentences_per_paper)` — membangun indeks kalimat yang tampak sebagai bukti primer saja.
- `support_bands(matcher)` — memilih ambang floor/gate/echo sesuai mode embedding vs lexical.
- `_echo_papers(claim, claims_by_paper, matcher, threshold)` — mencari paper lain yang mengafirmasi klaim yang sama (repetition, bukan corroboration).
- `assess_support(claim, evidence_index, matcher, claims_by_paper, secondary_refs)` — leave-one-out retrieval untuk satu klaim; menentukan status support dan alasan gap.
- `analyze_support(papers, paper_ref, matcher, max_claims_per_paper)` — entry point corpus-level: indexing, normalisasi klaim, penilaian support, dan agregasi report.
- `support_confidence(report)` — menghitung confidence indikator gap berbasis seberapa luas klaim tidak ter-grounding, dengan penalti/bonus untuk echo dan ukuran sampel.
**Dependensi utama:** memakai `NormalizedClaim`, `normalize_claims`, `content_terms` dari `claim_normalization.py` dan `SemanticMatcher` dari `semantic_match.py`.

### `backend/app/core/gap_detection/workflow_stages.py` — mining homogeneity workflow/metodologi per paper untuk indikator incompleteness. Modul ini merekonstruksi delapan tahap pipeline metode dari teks tiap paper, memverifikasi kutipan verbatim, lalu membandingkan nilai tahap antar paper untuk melihat tahap yang seragam/homogen.
**Konstanta penting:** `STAGES` — delapan tahap metodologi yang dilacak; `STAGE_KEYS` dan `STAGE_LABELS` — peta key→label; `MIN_PAPERS_FOR_HOMOGENEITY` — minimum paper yang menyebut tahap agar dianggap homogen; `METHOD_SECTIONS` — prioritas section `methods/results`; `WORKFLOW_CONTEXT_CHARS` — batas konteks LLM; `_MIN_SECTION_CHARS` — ambang section terlalu tipis; `_STAGE_ALIASES` — alias key stage.
**Kelas:**
- `StageVariant` — satu varian nilai pada sebuah stage; field penting `value`, `papers`, `quotes` (kutipan verbatim terverifikasi).
- `StageSummary` — ringkasan satu stage lintas paper; field penting `stage`, `label`, `variants`, `stated_papers`, `unstated_papers`, `homogeneous`; properti `dominant`.
- `StageMatrix` — view stage×paper; field penting `papers`, `stages`, `min_papers`, `matcher_method`, `verified_quotes`, `total_quotes`; properti `homogeneous`.
**Properti/metode kelas:**
- `StageVariant.to_dict()` — serialisasi satu varian stage.
- `StageSummary.dominant` — varian paling dominan di stage itu.
- `StageSummary.to_dict()` — serialisasi summary stage.
- `StageMatrix.homogeneous` — daftar stage yang memenuhi kriteria homogen.
- `StageMatrix.to_dict()` — serialisasi matrix dan shape `homogeneous` yang dipakai analyzer.
**Fungsi:**
- `build_workflow_prompt(title, context_text)` — prompt LLM untuk mengisi delapan stage metode dengan value + kutipan verbatim.
- `select_workflow_context(chunks, fallback_text, max_chars)` — memilih potongan methods/results dulu, lalu fallback teks awal bila terlalu tipis.
- `_chunk_view(chunk)` — menormalkan akses chunk dict/object menjadi `(text, section, is_reference)`.
- `parse_workflow_json(raw)` — mem-parsing output LLM menjadi mapping stage→{value,kutipan}, mengabaikan stage kosong/tidak dinyatakan.
- `_canonical_stage(raw_key)` — menormalkan key stage lewat alias.
- `verify_workflow(stages, full_text)` — memverifikasi kutipan stage dengan fuzzy match dan menambahkan `verified`/`match_score`.
- `compare_workflows(workflows, matcher, min_papers)` — mengelompokkan nilai stage antar paper, menandai stage yang homogen, dan menghitung jumlah quote terverifikasi.
- `_find_variant(value, variants, matcher)` — mencari varian stage yang sudah ada yang cukup mirip; helper greedy clustering stage.
**Dependensi utama:** memakai `QUOTE_MATCH_THRESHOLD` dan `fuzzy_contains` dari `quote_grounding.py`, serta `SemanticMatcher` dari `semantic_match.py`.

**Alur utama (bagian B):**
- `GapAnalyzer.analyze_gaps(...)` memanggil `resolve_axes`, `build_coverage_matrix`, `mark_important_columns`, `cluster_papers`, `rescue_singletons`, `build_coupling_graph`, `analyze_support`, dan workflow-stage mining via `compare_workflows`.
- Fragmentasi struktural di `analyzer.py` bergantung pada `graph_metrics.cluster_papers()` + `graph_metrics.rescue_singletons()`; bila KG/fact table ada, diperkaya oleh `_analyze_structural_isolation()` dan `rank_bridges()`.
- Fragmentasi bibliografis di `analyzer.py` memakai `citation_coupling.build_coupling_graph()` sebagai sumber evidence tambahan tanpa LLM.
- Incompleteness memakai `coverage_axes.resolve_axes()` lalu `coverage_map.build_coverage_matrix()`; aspek yang di-grounding/dikutip bergantung pada `semantic_match.SemanticMatcher`.
- Evidence-support gap memakai `support_gap.analyze_support()` yang bergantung pada `claim_normalization` + `semantic_match`, lalu hasilnya dikalibrasi lewat `calibration.load_calibrator()` / `Calibrator.calibrate()`.
- Semua indikator yang butuh kutipan verbatim memakai `quote_grounding.extract_supporting_quotes()` atau `verify_quote_against_papers()`; workflow-stage mining juga memakai verifikasi kutipan yang sama.
- `GapAnalyzer._apply_calibration()` menempelkan confidence terkalibrasi dan provenance chain dari `calibration.build_provenance()` ke setiap indikator.
- `workflow_stages.compare_workflows()` menyuplai bentuk `StageMatrix` yang dibaca analyzer untuk deteksi homogeneity metode.


<a id="bagian-02"></a>
# Bagian 02 — core/agents, knowledge, knowledge_graph, validation

## backend/app/core/agents/

### `backend/app/core/agents/coordinator.py` — Orkestrator LangGraph yang menjalankan loop observe→think→act→evaluate, dengan fallback pipeline sekuensial.
**Kelas:**
- `AgentPhase` — Enum fase eksekusi agen: `OBSERVE`, `THINK`, `ACT`, `EVALUATE`, `COMPLETE`, `ERROR`.
- `ReasoningStep` — TypedDict untuk satu langkah reasoning trace; menyimpan `phase`, `iteration`, `action`, `detail`, `timestamp`, `data`.
- `AgentState` — TypedDict state LangGraph; menyimpan input query, konteks, hasil perantara, kontrol loop, dan output akhir.
- `AgentResponse` — Dataclass respons coordinator; field penting: `success`, `result`, `reasoning_trace`, `metadata`, `error`.
- `CoordinatorAgent` — Pengendali utama yang memilih LangGraph atau pipeline sekuensial, lalu mengorkestrasi tool dan komponen analisis.
  - `__init__(...)` — Menerima analyzer/gap detector/recommender dan tool baru, menyimpan state internal, lalu membangun graph bila LangGraph tersedia.
  - `_build_graph()` — Membangun `StateGraph` dengan node `observe`, `think`, `act`, `evaluate`, edge tetap, dan conditional edge `evaluate→think/END`.
  - `_node_observe(state)` — Langkah observe: RAG retrieval via `rag_tool`, ekstraksi fakta via `fact_extractor`, update KG via `graph_builder`, analisis paper via `paper_analyzer_tool`; dominan LLM/RAG/graph update.
  - `_node_think(state)` — Langkah think: memanggil `gap_detector.detect_gaps`, lalu bila ada indikasi inkonsistensi menjalankan `nli_checker_tool.run`; campuran simbolik + LLM/NLI.
  - `_node_act(state)` — Langkah act: validasi setiap indikator via `rule_engine.validate`, lalu generate rekomendasi via `recommender.recommend`; rule-based + retrieval/LLM opsional.
  - `_node_evaluate(state)` — Langkah evaluate: self-critique via `self_critic_tool.run`, memutuskan perlu revisi atau finalisasi.
  - `_enrich_claim_for_validation(indicator)` — Memperkaya indikator menjadi claim dengan `method/domain/findings` dari FactTable agar Rule Engine bisa memverifikasi; simbolik.
  - `_should_continue(state)` — Routing LangGraph: memilih `revise` atau `complete` berdasarkan `needs_revision`.
  - `process_research_query(query, context) -> Dict[str, Any]` — Entry point publik; menjalankan graph bila ada, jika tidak jatuh ke mode sekuensial.
  - `_run_langgraph(query, context) -> Dict[str, Any]` — Menjalankan `self._graph.invoke(...)`, menyimpan history, dan fallback ke sekuensial bila graph gagal.
  - `_run_sequential(query, context) -> Dict[str, Any]` — Pipeline lama: analyze→detect_gaps→recommend; memanggil `research_analyzer`, `gap_detector`, `recommender`.
  - `get_task_history() -> List[AgentResponse]` — Mengembalikan history eksekusi tugas.
  - `clear_history()` — Mengosongkan history tugas.
  - `get_statistics() -> Dict[str, Any]` — Ringkasan jumlah task sukses/gagal dan mode eksekusi.

**Fungsi:**
- Tidak ada fungsi level modul.

**Alur utama:**
- `process_research_query()` adalah entry point.
- Di mode LangGraph: `observe` memakai `rag_tool` → `fact_extractor` → `graph_builder` → `paper_analyzer_tool`; `think` memakai `gap_detector` dan `nli_checker_tool`; `act` memakai `rule_engine` dan `recommender`; `evaluate` memakai `self_critic_tool`.
- Di mode fallback: `research_analyzer` → `gap_detector` → `recommender`.
- `fact_table` menjadi pusat data untuk `rule_engine` dan enrichment claim.
- `graph_builder` dipakai untuk membangun KG dari fact table, lalu bisa di-query tool lain.

---

### `backend/app/core/agents/gap_detector.py` — Agen pendeteksi indikator synthesis gap berbasis model 3 indikator Cooper/Booth.
**Kelas:**
- `GapDetectorAgent` — Mengambil paper, mengekstrak fakta, mendeteksi indikator fragmentasi/inkonsistensi/inkompletensi, lalu menyiapkan hasil untuk validasi manusia.
  - `__init__(...)` — Menyimpan LLM, retriever, knowledge graph, fact table, fact extractor, gap analyzer, relation classifier, rule engine.
  - `detect_gaps(query, context) -> Dict[str, Any]` — Pipeline utama deteksi indikator gap; retrieval paper, fakt ekstraksi bila perlu, analisis gap, ringkasan akhir.
  - `_get_papers(query, context) -> List[Dict[str, Any]]` — Mengambil paper dari `context` atau `retriever`; jika perlu memetakan hasil retrieval jadi dict paper.
  - `_detect_gaps_llm_fallback(query, papers, result) -> Dict[str, Any]` — Jalur fallback LLM jika `gap_analyzer` tidak tersedia; output masih berlabel `LLM_UNVALIDATED`.
  - `_generate_summary(query, result) -> str` — Menyusun ringkasan human-readable dari jumlah indikator per tipe.
- Fungsi level modul: tidak ada.

**Fungsi:**
- Tidak ada fungsi level modul.

**Alur utama:**
- `detect_gaps()` memanggil `_get_papers()`.
- Jika `fact_extractor` + `fact_table` tersedia, fakta diekstrak dan KG di-update.
- Jika `gap_analyzer` tersedia, hasilnya dipakai sebagai indikator utama.
- Jika tidak, `_detect_gaps_llm_fallback()` dipakai.
- Ringkasan akhir dibuat oleh `_generate_summary()`.

---

### `backend/app/core/agents/recommender.py` — Agen rekomendasi paper yang mengurutkan kandidat berdasarkan relevansi, gap-awareness, dan diversitas.
**Kelas:**
- `Recommendation` — Dataclass hasil rekomendasi; field penting: `paper_id`, `title`, `relevance_score`, `reason`, `metadata`, `rank`.
- `RecommenderAgent` — Menyusun dan meranking rekomendasi paper, dengan opsi pemrosesan gap-aware dan LLM reasoning.
  - `__init__(...)` — Menyimpan LLM, retriever, dan knowledge graph.
  - `recommend(query, context, top_k, diversity_weight) -> Dict[str, Any]` — Entry point rekomendasi; retrieval kandidat, gap-awareness, diversifikasi, lalu reasoning LLM opsional.
  - `_generate_reason(result, context) -> str` — Membuat alasan rekomendasi dari skor retrieval, metadata, dan gap context.
  - `_apply_gap_awareness(candidates, gaps) -> List[Recommendation]` — Menambah skor kandidat yang cocok dengan gap; rule-based/heuristic.
  - `_diversify_recommendations(candidates, diversity_weight) -> List[Recommendation]` — Menurunkan skor kandidat yang terlalu mirip untuk mengurangi redundansi.
  - `recommend_by_paper(paper_id, top_k) -> List[Recommendation]` — Mencari paper mirip dengan satu paper sumber; berbasis retrieval.
  - `recommend_reading_order(paper_ids) -> List[Dict[str, Any]]` — Mengurutkan paper secara kronologis dan memberi catatan membaca.
- Tidak ada fungsi level modul.

**Fungsi:**
- Tidak ada fungsi level modul.

**Alur utama:**
- `recommend()` memanggil retriever untuk kandidat.
- `_generate_reason()` menyusun alasan per kandidat.
- `_apply_gap_awareness()` menaikkan bobot paper yang menutup gap.
- `_diversify_recommendations()` menekan duplikasi/topik yang terlalu mirip.
- Jika LLM ada, `recommend_papers()` dipakai untuk reasoning global.

---

### `backend/app/core/agents/research_analyzer.py` — Agen analisis domain/paper untuk mengekstrak tema, metodologi, dan ringkasan.
**Kelas:**
- `ResearchAnalyzerAgent` — Menganalisis query riset dan paper terkait untuk mengidentifikasi tema, metode, dan kontribusi.
  - `__init__(llm_interface=None, retriever=None)` — Menyimpan LLM dan retriever.
  - `analyze(query, context) -> Dict[str, Any]` — Entry point analisis domain; retrieval paper, analisis LLM, ekstraksi tema/metodologi.
  - `_extract_themes(papers) -> List[str]` — Menghitung keywords populer dari metadata paper.
  - `_extract_methodologies(papers) -> List[str]` — Mencari istilah metodologi umum di konten paper; heuristic.
  - `analyze_paper(paper_content, metadata) -> Dict[str, Any]` — Menganalisis satu paper dan membuat ringkasan/contributions/limitations/future_work.
- Tidak ada fungsi level modul.

**Fungsi:**
- Tidak ada fungsi level modul.

**Alur utama:**
- `analyze()` memakai retriever untuk paper relevan.
- Bila LLM ada, `analyze_research()` dipanggil untuk ringkasan.
- `_extract_themes()` dan `_extract_methodologies()` memberi struktur analisis.
- `analyze_paper()` dipakai untuk analisis dokumen tunggal.

---

### `backend/app/core/agents/tools/paper_analyzer_tool.py` — Tool untuk menganalisis satu paper dan, bila tersedia, mengekstrak fakta ke FactTable.
**Kelas:**
- `PaperAnalyzerTool` — Tool analisis paper individual untuk pipeline agentik.
  - `__init__(llm_interface=None, fact_extractor=None, fact_table=None)` — Menyimpan LLM dan komponen ekstraksi fakta.
  - `run(paper) -> Dict[str, Any]` — Analisis satu paper: resolve ID, ekstraksi fakta, ringkasan LLM.
  - `run_batch(papers) -> List[Dict[str, Any]]` — Analisis banyak paper secara iteratif.
- Fungsi level modul:
  - `resolve_paper_id(paper) -> str` — Menentukan ID paper untuk provenance fakta dari `doc_id/id/source/title`; helper non-LLM.

**Fungsi:**
- `resolve_paper_id(paper) -> str` — Memilih identitas paper paling valid; penting untuk provenance fakta.
- `PaperAnalyzerTool.run(paper) -> Dict[str, Any]` — Menjalankan fact extraction dan LLM summarization pada satu paper.
- `PaperAnalyzerTool.run_batch(papers) -> List[Dict[str, Any]]` — Memproses banyak paper dengan memanggil `run()` per item.

**Alur utama:**
- `run()` memakai `resolve_paper_id()` untuk provenance.
- Jika `fact_extractor` dan `fact_table` ada, konten paper diekstrak menjadi fakta.
- Jika LLM ada, ringkasan paper dibuat.
- Dipakai oleh `CoordinatorAgent._node_observe()`.

---

### `backend/app/core/agents/tools/kg_querier_tool.py` — Tool akses terstruktur ke Knowledge Graph dan FactTable.
**Kelas:**
- `KGQuerierTool` — Antarmuka query untuk fakta, neighborhood, path, statistik, kontradiksi, dan daftar entitas.
  - `__init__(graph_builder=None, fact_table=None)` — Menyimpan graph builder dan fact table.
  - `run(action, **kwargs) -> Dict[str, Any]` — Dispatcher aksi query.
  - `_query_facts(subject, predicate, obj, **_) -> Dict[str, Any]` — Query SPO triple dari graph/fact table; simbolik.
  - `_neighborhood(entity_id, max_depth, **_) -> Dict[str, Any]` — Mengambil neighborhood entitas dari KG.
  - `_find_paths(source, target, max_paths, **_) -> Dict[str, Any]` — Mencari path antar entitas.
  - `_statistics(**_) -> Dict[str, Any]` — Mengambil statistik fact table dan graph.
  - `_contradictions(**_) -> Dict[str, Any]` — Mengambil pasangan fakta kontradiktif dari fact table.
  - `_list_entities(entity_type, limit, **_) -> Dict[str, Any]` — Mencantumkan entitas dari fact table; bisa filter tipe.
- Tidak ada fungsi level modul.

**Fungsi:**
- Tidak ada fungsi level modul.

**Alur utama:**
- `run()` memilih handler berdasarkan `action`.
- Query lebih dulu diarahkan ke `graph_builder`, lalu fallback ke `fact_table`.
- `fact_table.find_contradictions()` dipakai untuk aksi kontradiksi.
- Tool ini menjadi antarmuka eksplorasi KG untuk agen.

---

### `backend/app/core/agents/tools/nli_checker_tool.py` — Tool pengecek relasi logis antar klaim memakai RelationClassifier dengan fallback LLM.
**Kelas:**
- `NLICheckerTool` — Memverifikasi hubungan antara dua klaim: kontradiksi, kausal, ekstensi, atau co-occurrence.
  - `__init__(relation_classifier=None, llm_interface=None)` — Menyimpan classifier dan LLM fallback.
  - `run(claim_a, claim_b, context, semantic_similarity, kg_facts) -> Dict[str, Any]` — Menjalankan klasifikasi relasi utama.
  - `_llm_fallback(claim_a, claim_b, context, result) -> Dict[str, Any]` — Memakai LLM jika classifier gagal/tidak tersedia.
  - `check_batch(claim_pairs) -> List[Dict[str, Any]]` — Memproses banyak pasangan klaim.
- Tidak ada fungsi level modul.

**Fungsi:**
- Tidak ada fungsi level modul.

**Alur utama:**
- `run()` memanggil `relation_classifier.classify()`.
- Jika classifier error/tidak ada, `_llm_fallback()` dipakai.
- `check_batch()` hanya loop atas `run()`.
- Dipakai di coordinator saat verifikasi inkonsistensi.

---

### `backend/app/core/agents/tools/rag_tool.py` — Tool retrieval konteks/passage dari vector store untuk mendukung pencarian bukti.
**Kelas:**
- `RAGTool` — Wrapper retrieval untuk mencari passage relevan dari korpus paper.
  - `__init__(retriever=None)` — Menyimpan retriever.
  - `run(query, top_k) -> Dict[str, Any]` — Melakukan retrieval dan mengemas hasil passage.
- Tidak ada fungsi level modul.

**Fungsi:**
- Tidak ada fungsi level modul.

**Alur utama:**
- `run()` memanggil `retriever.retrieve(...)`.
- Hasil dikemas jadi passage singkat dengan title/source/score.
- Dipakai sebagai langkah awal observe di coordinator.

---

### `backend/app/core/agents/tools/self_critic_tool.py` — Tool evaluasi diri agen untuk menilai kualitas, konsistensi, dan kebutuhan revisi.
**Kelas:**
- `SelfCriticTool` — Melakukan self-evaluation atas hasil analisis dan memberi saran perbaikan.
  - `__init__(rule_engine=None, llm_interface=None, fact_table=None)` — Menyimpan rule engine, LLM, dan fact table.
  - `run(analysis_result, original_query) -> Dict[str, Any]` — Entry point evaluasi: skor keseluruhan, dimensi, isu, dan revisi.
  - `_check_completeness(result) -> Dict[str, Any]` — Memeriksa kelengkapan komponen hasil dan cakupan tipe indikator.
  - `_check_evidence_support(result) -> Dict[str, Any]` — Menilai apakah indikator memiliki bukti dan confidence memadai.
  - `_check_consistency(result) -> Dict[str, Any]` — Memeriksa duplikasi dan kontradiksi internal/fact table.
  - `_validate_with_rules(result) -> Dict[str, Any]` — Menjalankan Rule Engine pada indikator; rule-based.
  - `_llm_evaluate(result, original_query) -> Dict[str, Any]` — Meminta kritik evaluatif dari LLM.
- Tidak ada fungsi level modul.

**Fungsi:**
- Tidak ada fungsi level modul.

**Alur utama:**
- `run()` menggabungkan skor dari `_check_completeness()`, `_check_evidence_support()`, `_check_consistency()`.
- Jika ada, `_validate_with_rules()` dan `_llm_evaluate()` menambah dimensi evaluasi.
- Dipakai pada fase evaluate di coordinator.

---

## backend/app/core/knowledge/

### `backend/app/core/knowledge/fact_extractor.py` — Ekstraktor fakta SPO dari teks paper memakai LLM, fallback pattern, dan parsing JSON yang robust.
**Kelas:**
- `FactExtractor` — Mengekstrak entitas dan relasi dari teks paper lalu menuliskannya ke FactTable.
  - `__init__(llm_interface=None)` — Menyimpan LLM interface.
  - `extract_from_text(text, paper_id, fact_table, max_text_length=3000) -> Dict[str, Any]` — Pipeline penuh ekstraksi dari satu paper; fast path combined call lalu fallback 2 langkah.
  - `extract_from_papers(papers, fact_table) -> Dict[str, Any]` — Ekstraksi batch lintas paper, termasuk paralelisasi.
  - `_extract_combined(text, paper_id, fact_table) -> Tuple[List[Entity], List[Fact]]` — Satu call LLM untuk entitas + relasi sekaligus; jika gagal mengembalikan kosong.
  - `_extract_entities(text, paper_id, fact_table) -> List[Entity]` — Ekstraksi entitas via LLM, fallback ke pattern-based entity extraction.
  - `_extract_entities_pattern(text, paper_id, fact_table) -> List[Entity]` — Pattern-based entity extraction untuk method/dataset/metric/finding; simbolik.
  - `_extract_relations(text, entities, paper_id, fact_table) -> List[Fact]` — Ekstraksi relasi via LLM dari entities yang sudah ditemukan.
  - `_extract_pattern_relations(text, entities, paper_id, fact_table) -> List[Fact]` — Deteksi relasi berbasis marker linguistik (causal/contradiction/extension); rule/heuristic.
  - `_generate_json(prompt, system_prompt, max_retries=1) -> List[Any]` — Memanggil LLM dan mem-parsing JSON array; retry dengan prompt lebih ketat.
  - `_generate_json_object(prompt, system_prompt, max_retries=1) -> Optional[Dict[str, Any]]` — Versi JSON object untuk mode combined extraction.
  - `_parse_json_object_response(response) -> Optional[Dict[str, Any]]` — Parser JSON object toleran code fence dan teks ekstra.
  - `_parse_json_response(response) -> Optional[List[Any]]` — Parser JSON array toleran fence/teks ekstra; bisa salvage array terpotong.
  - `_salvage_truncated_array(text) -> Optional[List[Any]]` — Menyelamatkan objek JSON lengkap dari respons array yang terpotong.
  - `_resolve_entity(name, entities) -> Optional[Entity]` — Mencari entity berdasarkan nama fuzzy.
  - `_find_entities_in_text(text, entities) -> List[Entity]` — Menemukan entity yang disebut dalam potongan teks.
  - `_split_sentences(text) -> List[str]` — Pemisah kalimat sederhana.
- Konstanta modul penting:
  - `ENTITY_EXTRACTION_PROMPT` — Prompt LLM untuk entitas.
  - `RELATION_EXTRACTION_PROMPT` — Prompt LLM untuk relasi.
  - `RETRY_SUFFIX` — Tambahan prompt saat parse JSON gagal.
  - `COMBINED_EXTRACTION_PROMPT` — Prompt LLM untuk entitas+relasi dalam satu call.
  - `COMBINED_RETRY_SUFFIX` — Retry suffix untuk combined extraction.
  - `CAUSAL_MARKERS` — Penanda linguistik kausal.
  - `CONTRADICTION_MARKERS` — Penanda linguistik kontradiksi.
  - `EXTENSION_MARKERS` — Penanda linguistik ekstensi.

**Fungsi:**
- Tidak ada fungsi level modul.

**Alur utama:**
- `extract_from_text()` mencoba `_extract_combined()` dulu untuk menghemat LLM call.
- Jika combined gagal, jalur klasik `_extract_entities()` → `_extract_relations()` dipakai.
- `_extract_pattern_relations()` menambah fakta hasil heuristic.
- Semua fakta ditulis ke `FactTable`.
- Parser JSON `_generate_json()` / `_generate_json_object()` penting untuk robust terhadap output LLM yang berantakan.

---

### `backend/app/core/knowledge/fact_table.py` — Penyimpanan terstruktur SPO triple dan entitas untuk reasoning, query, dan validasi rule-based.
**Kelas:**
- `EntityType` — Enum 8 tipe entitas: `METHOD`, `CONCEPT`, `DOMAIN`, `FINDING`, `DATASET`, `METRIC`, `PAPER`, `CONSTRAINT`.
- `PredicateType` — Enum predikat relasi SPO, termasuk `USES_METHOD`, `PROPOSES`, `APPLIES_TO`, `ACHIEVES`, `REQUIRES_RESOURCE`, `REQUIRES_DATA`, `IMPROVES`, `CONTRADICTS`, `EXTENDS`, `EVALUATED_ON`, `HAS_CONSTRAINT`, `DISCUSSES`, serta inferensi `INFEASIBLE_FOR` dan `CORRELATES_WITH`.
- `Verdict` — Enum output Rule Engine: `PASS`, `FLAG`, `REJECT`.
- `Entity` — Dataclass node KG; field penting: `entity_id`, `entity_type`, `name`, `properties`, `source_paper`; punya `__hash__` dan `__eq__`.
- `Fact` — Dataclass triple SPO; field penting: `fact_id`, `subject_id`, `predicate`, `object_id`, `source`, `source_paper`, `confidence`, `is_inferred`, `inferred_by_rule`, `metadata`; punya `to_dict()`.
- `FactTable` — Penyimpanan utama entity/fact dengan index subject/predicate/object/paper dan lock reentrant.
  - `__init__()` — Inisialisasi storage, index, dan lock thread-safe.
  - `add_entity(entity) -> str` — Menyimpan entity.
  - `get_entity(entity_id) -> Optional[Entity]` — Ambil entity by ID.
  - `find_entities(entity_type=None, name_contains=None, source_paper=None) -> List[Entity]` — Query entity dengan filter.
  - `get_or_create_entity(name, entity_type, source_paper=None, properties=None) -> Entity` — Cari entity existing atau buat baru.
  - `add_fact(fact) -> str` — Menyimpan fact dan memperbarui index.
  - `get_fact(fact_id) -> Optional[Fact]` — Ambil fact by ID.
  - `remove_fact(fact_id) -> bool` — Hapus fact dan bersihkan index.
  - `query(subject_id=None, predicate=None, object_id=None, source_paper=None, min_confidence=0.0, include_inferred=True) -> List[Fact]` — Query utama untuk Rule Engine; simbolik.
  - `query_triples(subject_id=None, predicate=None, object_id=None) -> List[Tuple[str, str, str]]` — Query sederhana untuk triple tuple.
  - `find_contradictions() -> List[Tuple[Fact, Fact]]` — Mencari pasangan fakta `CONTRADICTS`.
  - `get_statistics() -> Dict[str, Any]` — Statistik jumlah entity/fact/predicate/paper.
  - `get_all_facts_as_dicts() -> List[Dict[str, Any]]` — Export semua fact sebagai dict.
  - `get_facts_for_paper(paper_id) -> List[Fact]` — Semua fact dari paper tertentu.
  - `add_facts_bulk(facts) -> int` — Insert banyak fact sekaligus.
  - `clear()` — Mengosongkan seluruh table.
  - `__repr__() -> str` — Representasi ringkas tabel.

**Fungsi:**
- Tidak ada fungsi level modul.

**Alur utama:**
- `FactExtractor` menulis entity dan fact ke `FactTable`.
- `RuleEngine` membaca fact via `query()`/`get_entity()`/`get_statistics()`.
- `KnowledgeGraphBuilder.build_from_fact_table()` membaca seluruh isi FactTable untuk membuat graph.
- `GapDetector`, `SelfCriticTool`, dan `KGQuerierTool` memanfaatkan query FactTable untuk analisis dan pemeriksaan kontradiksi.

**Alur utama:**
- `FactTable` adalah basis fakta untuk semua reasoning simbolik.
- `EntityType` dan `PredicateType` menentukan skema semantik data.
- `FactExtractor` mengisi tabel; `RuleEngine` dan `KnowledgeGraphBuilder` membacanya.
- `find_contradictions()` penting untuk indikator inkonsistensi dan self-critique.
- `get_statistics()` dipakai dalam response analitik dan observabilitas.

## backend/app/core/knowledge_graph/

### `backend/app/core/knowledge_graph/graph_builder.py` — Pembuat Knowledge Graph berbasis NetworkX/Neo4j yang menghubungkan paper dan SPO triple.
**Kelas:**
- `PaperNode` — Dataclass node paper; field penting: `paper_id`, `title`, `year`, `authors`, `keywords`, `metadata`.
- `CitationEdge` — Dataclass edge sitasi; field penting: `source_id`, `target_id`, `weight`.
- `KnowledgeGraphBuilder` — Membangun dan meng-query graph paper/citation serta graph entitas dari FactTable.
  - `__init__(use_neo4j=False, neo4j_config=None)` — Inisialisasi graph NetworkX dan opsional Neo4j.
  - `_init_neo4j(config)` — Membuka koneksi Neo4j; jaringan/database.
  - `add_paper(paper) -> bool` — Menambah node paper ke graph.
  - `add_citation(citation) -> bool` — Menambah edge sitasi antar paper.
  - `build_from_documents(documents)` — Membangun graph paper dari dokumen list.
  - `get_paper_neighbors(paper_id, max_neighbors=10) -> List[Tuple[str, Dict]]` — Mengambil tetangga paper.
  - `find_influential_papers(top_k=10) -> List[Tuple[str, float]]` — Mencari paper paling berpengaruh via PageRank.
  - `find_research_communities(method="louvain") -> Dict[int, List[str]]` — Deteksi komunitas riset.
  - `find_topic_clusters(num_clusters=5) -> Dict[str, int]` — Clustering paper berbasis keyword overlap.
  - `find_shortest_path(source_id, target_id) -> Optional[List[str]]` — Jalur terpendek antar paper.
  - `get_citation_count(paper_id) -> int` — Jumlah sitasi masuk.
  - `get_reference_count(paper_id) -> int` — Jumlah referensi keluar.
  - `export_to_dict() -> Dict[str, Any]` — Export graph ke dict.
  - `build_from_fact_table(fact_table) -> Dict[str, Any]` — Mengubah entitas menjadi node dan fact menjadi edge; inti integrasi SPO.
  - `query_facts(subject_id=None, predicate=None, object_id=None) -> List[Dict[str, Any]]` — Query fact dari graph atau fact table.
  - `get_entity_neighborhood(entity_id, max_depth=2) -> Dict[str, Any]` — Ambil neighborhood entitas dalam graph SPO.
  - `find_paths_between_entities(source_id, target_id, max_paths=3) -> List[List[Dict[str, Any]]]` — Cari path antar entitas; dipakai untuk transitivity/confounding.
- Fungsi level modul: tidak ada.

**Fungsi:**
- Tidak ada fungsi level modul.

**Alur utama:**
- `build_from_documents()` membangun graph paper/citation klasik.
- `build_from_fact_table()` adalah jalur utama untuk graph SPO.
- `query_facts()` menjadi jembatan Rule Engine ke graph/fact table.
- `get_entity_neighborhood()` dan `find_paths_between_entities()` dipakai oleh pemeriksaan relasi/transitivitas.

---

### `backend/app/core/knowledge_graph/__init__.py` — Modul ekspor: mengimpor `KnowledgeGraphBuilder` dari `.graph_builder` dan mengekspornya lewat `__all__`.

## backend/app/core/validation/

### `backend/app/core/validation/relation_classifier.py` — Klasifier relasi 3-layer untuk membedakan co-occurrence, kausalitas, kontradiksi, dan ekstensi.
**Kelas:**
- `RelationType` — Enum relasi: `CO_OCCURRENCE`, `CAUSAL`, `CONTRADICTION`, `EXTENSION`, `UNKNOWN`.
- `ClassifiedRelation` — Dataclass hasil klasifikasi; field penting: `entity_a`, `entity_b`, `relation_type`, `semantic_similarity`, `evidence_markers`, `evidence_text`, `rule_validated`, `confidence`, `explanation`, `layers_used`; punya `to_dict()`.
- `RelationClassifier` — Pipeline 3 layer: semantic filtering → evidence extraction → rule-based validation.
  - `__init__(llm_interface=None, similarity_threshold=0.3, causal_confidence_threshold=0.5, nli_model=None)` — Menyimpan LLM, threshold, dan optional dedicated NLI model.
  - `classify(entity_a, entity_b, text_context, semantic_similarity=0.0, kg_facts=None) -> ClassifiedRelation` — Entry point klasifikasi relasi.
  - `classify_batch(pairs, text_context, kg_facts=None) -> List[ClassifiedRelation]` — Klasifikasi banyak pasangan.
  - `_extract_evidence(entity_a, entity_b, text) -> tuple[RelationType, List[str], str]` — Ekstrak evidence berbasis marker linguistik.
  - `_extract_evidence_llm(entity_a, entity_b, text) -> tuple[RelationType, List[str], str]` — Evidence extraction pakai LLM; fallback ke pattern matching bila gagal.
  - `_validate_with_rules(entity_a, entity_b, relation_type, kg_facts) -> tuple[bool, str]` — Validasi hasil klasifikasi terhadap fact/KG.
  - `_find_relevant_sentences(text, entity_a, entity_b) -> List[str]` — Cari kalimat yang memuat kedua entitas.
  - `_calculate_confidence(similarity, relation_type, markers, validated) -> float` — Menghitung confidence gabungan dari similarity, marker, dan validasi.
- Konstanta modul penting:
  - `CAUSAL_MARKERS`
  - `CONTRADICTION_MARKERS`
  - `EXTENSION_MARKERS`

**Fungsi:**
- Tidak ada fungsi level modul.

**Alur utama:**
- `classify()` first gate berdasarkan similarity.
- `_extract_evidence()` menentukan relasi dari marker teks; `_extract_evidence_llm()` dipakai bila perlu.
- Bila `nli_model` tersedia, `check_contradiction()` dapat mempromosikan/menegaskan kontradiksi.
- `_validate_with_rules()` memeriksa dukungan KG/fact.
- Output klasifikasi dipakai `NLICheckerTool`.

---

### `backend/app/core/validation/nli_model.py` — Wrapper model NLI independen untuk sinyal kontradiksi/entailment berbasis cross-encoder.
**Kelas:**
- `NLIModel` — Pembungkus lazy-loaded `sentence_transformers.CrossEncoder` untuk NLI.
  - `__init__(model_name=DEFAULT_NLI_MODEL, device=None)` — Menyimpan nama model dan device.
  - `available` — Property status model tersedia atau tidak.
  - `_try_load() -> bool` — Mencoba memuat model dari sentence-transformers; jaringan/model lokal tergantung cache.
  - `predict(premise, hypothesis) -> Optional[Dict]` — Prediksi label NLI dan skor probabilitas.
  - `check_contradiction(claim_a, claim_b, threshold=0.5) -> Optional[Dict]` — Pemeriksaan kontradiksi dua arah.
- Konstanta modul penting:
  - `DEFAULT_NLI_MODEL = "cross-encoder/nli-deberta-v3-xsmall"`
  - `NLI_LABELS = ["contradiction", "entailment", "neutral"]`

**Fungsi:**
- Tidak ada fungsi level modul.

**Alur utama:**
- `available` memicu `_try_load()` saat pertama kali dipakai.
- `predict()` menghasilkan distribusi NLI.
- `check_contradiction()` dipakai `RelationClassifier` untuk sinyal independen kontradiksi.

---

### `backend/app/core/validation/rule_engine.py` — Mesin validasi simbolik 9-rule untuk memutuskan PASS/FLAG/REJECT pada claim/indikator.
**Kelas:**
- `RuleCategory` — Enum kategori rule: `FEASIBILITY`, `CAUSALITY`, `CONSISTENCY`.
- `Rule` — Dataclass definisi rule; field penting: `rule_id`, `category`, `name`, `description`, `is_critical`.
- `RuleResult` — Dataclass hasil satu rule; field penting: `rule`, `passed`, `verdict`, `reason`, `evidence`, `confidence_adjustment`.
- `ValidationReport` — Dataclass laporan validasi lengkap; field penting: `overall_verdict`, `original_confidence`, `adjusted_confidence`, `rules_checked`, `rules_passed`, `rules_flagged`, `rules_rejected`, `results`, `summary`; punya `to_dict()`.
- `RuleEngine` — Validasi claim terhadap fact table/KG dengan 9 rule.
  - `__init__(fact_table=None, knowledge_graph=None, rules=None, config=None)` — Menyimpan dependensi, memuat config, dan menentukan perilaku missing-evidence.
  - `validate(claim, context=None) -> ValidationReport` — Entry point validasi satu claim/string.
  - `validate_batch(claims, context=None) -> List[ValidationReport]` — Validasi banyak claim.
  - `_apply_rule(rule, claim, context) -> RuleResult` — Dispatcher ke implementasi per rule.
  - `_check_f1_resource_compatibility(rule, claim) -> RuleResult` — Rule F1: method butuh resource tinggi vs domain low-resource → REJECT.
  - `_check_f2_data_compatibility(rule, claim) -> RuleResult` — Rule F2: kebutuhan data besar vs data langka → FLAG.
  - `_check_f3_scale_compatibility(rule, claim) -> RuleResult` — Rule F3: single-machine vs distributed scale → REJECT.
  - `_check_c1_causal_evidence(rule, claim) -> RuleResult` — Rule C1: evidence kausal kurang → downgrade ke correlation/FLAG.
  - `_check_c2_causal_direction(rule, claim) -> RuleResult` — Rule C2: arah sebab-akibat melanggar temporal order → REJECT.
  - `_check_c3_confounding(rule, claim) -> RuleResult` — Rule C3: banyak path/potensial confounder → FLAG.
  - `_check_k1_internal_contradiction(rule, claim) -> RuleResult` — Rule K1: klaim dalam output saling kontradiksi → FLAG.
  - `_check_k2_kg_consistency(rule, claim) -> RuleResult` — Rule K2: klaim tidak didukung fact KG → FLAG dan confidence turun.
  - `_check_k3_transitivity(rule, claim) -> RuleResult` — Rule K3: pelanggaran transitivity pada relasi IMPROVES/CONTRADICTS → FLAG.
  - `_default_pass(rule, reason=None) -> RuleResult` — Hasil PASS default.
  - `_missing_evidence_or_pass(rule, reason, pass_reason=None) -> RuleResult` — FLAG saat evidence hilang, atau PASS jika config legacy mengizinkan.
  - `_missing_entities(entity_ids) -> List[str]` — Mengecek entity yang belum ada di FactTable.
  - `_get_on_missing_evidence(config) -> str` — Membaca mode flag/pass dari config.
  - `_load_rule_engine_config() -> Dict[str, Any]` — Memuat config YAML backend/config.yaml.
  - `_build_summary(overall_verdict, results, claim) -> str` — Merangkai ringkasan verifikasi.
- Konstanta modul penting:
  - `RULE_F1`, `RULE_F2`, `RULE_F3`, `RULE_C1`, `RULE_C2`, `RULE_C3`, `RULE_K1`, `RULE_K2`, `RULE_K3`
  - `ALL_RULES` — daftar 9 rule di atas.
  - `MISSING_EVIDENCE_CONFIDENCE_ADJUSTMENT = -0.05`

**Fungsi:**
- Tidak ada fungsi level modul.

**Alur utama:**
- `validate()` menjalankan semua rule dalam `self.rules` lewat `_apply_rule()`.
- `_apply_rule()` mendispatch ke rule-specific checker F1–K3.
- `FactTable` adalah sumber evidence utama; `KnowledgeGraphBuilder` dipakai untuk path/transitivity/confounding.
- `ValidationReport.to_dict()` dipakai untuk serialisasi hasil validasi.
- Coordinator dan SelfCriticTool memakai `RuleEngine.validate()` untuk memfilter/menilai indikator.

### `backend/app/core/validation/__init__.py` — Modul ekspor lapisan validasi: `RuleEngine`, `Rule`, `RuleCategory` (FEASIBILITY/CAUSALITY/CONSISTENCY), `RuleResult`, `ValidationReport` dari `.rule_engine`; `RelationClassifier`, `RelationType` (CO_OCCURRENCE/CAUSAL/CONTRADICTION/EXTENSION/UNKNOWN), `ClassifiedRelation` dari `.relation_classifier`.

## Tambahan — `__init__.py`, fungsi bersarang, dan daftar 9 rule

### `backend/app/core/agents/__init__.py` — Modul ekspor kerangka multi-agen: `CoordinatorAgent`, `ResearchAnalyzerAgent`, `GapDetectorAgent`, `RecommenderAgent` (semua lewat `__all__`).

### `backend/app/core/agents/tools/__init__.py` — Modul ekspor 5 tool yang dipanggil koordinator di loop observe→think→act→evaluate: `RAGTool`, `PaperAnalyzerTool`, `NLICheckerTool`, `KGQuerierTool`, `SelfCriticTool`.

### `backend/app/core/knowledge/__init__.py` — Modul ekspor sistem triple SPO: `EntityType`, `PredicateType`, `Entity`, `Fact`, `FactTable`, `Verdict` (dari `.fact_table`) dan `FactExtractor` (dari `.fact_extractor`).

### `backend/app/core/knowledge/fact_extractor.py` (fungsi bersarang)
- `_do(item)` — bersarang di `FactExtractor.extract_from_papers(...)`; memanggil `self.extract_from_text(content, pid, fact_table)` untuk satu paper sehingga bisa dipakai baik oleh `ThreadPoolExecutor` (paralel) maupun jalur sekuensial.

### `backend/app/core/validation/rule_engine.py` — daftar 9 rule (kategori → verdict yang mungkin)
| Kode | Nama rule | Kategori | Verdict |
|---|---|---|---|
| F1 | Resource Compatibility | Feasibility | PASS / REJECT |
| F2 | Data Compatibility | Feasibility | PASS / FLAG |
| F3 | Scale Compatibility | Feasibility | PASS / REJECT |
| C1 | Minimal Causal Evidence | Causality | PASS / FLAG |
| C2 | Causal Direction | Causality | PASS / REJECT |
| C3 | Confounding Check | Causality | PASS / FLAG |
| K1 | Internal Non-contradiction | Consistency | PASS / FLAG |
| K2 | KG Fact Consistency | Consistency | PASS / FLAG |
| K3 | Transitivity Check | Consistency | PASS / FLAG |


<a id="bagian-03"></a>
# Bagian 03 — core/pipeline, retrieval, recommendation, gap_mining, runtime, models, telemetry, main.py

## backend/app/core/pipeline/

### `backend/app/core/pipeline/__init__.py` — paket inti pipeline ekstraksi PDF→chunk terstruktur dengan skema baru.
**Fungsi:**
- Tidak ada fungsi/kelas; hanya mengekspor `PaperMeta`, `PipelineChunk`, dan `CANONICAL_SECTIONS`.

### `backend/app/core/pipeline/schema.py` — definisi skema data tingkat-paper dan tingkat-chunk untuk pipeline baru.
**Kelas:**
- `PaperMeta` — metadata paper yang dihitung sekali per dokumen; berisi `source`, `doi`, `paper_title`, `authors`, `year`, `language`, `abstract`, `extraction_quality`, `metadata_source`; tidak memanggil LLM/jaringan.
  - `to_dict()` — mengubah metadata paper menjadi dict serializable.
- `PipelineChunk` — satu record chunk keluaran pipeline lengkap dengan ID stabil dan metadata per-chunk.
  - `make_chunk_id()` — membuat ID stabil dari `source`, `chunk_index`, dan hash pendek teks.
  - `__post_init__()` — mengisi `chunk_id` bila belum ada.
  - `to_json_record()` — menulis record JSONL skema baru untuk CLI.
  - `to_vector_metadata(job_id=None)` — mengubah chunk menjadi metadata flat untuk Chroma, opsional menambahkan `analysis_job_id`.
**Konstanta:**
- `CANONICAL_SECTIONS` — daftar label section kanonik: abstract/introduction/related_work/methods/results/discussion/conclusion/references/other.
- `EXTRACTION_QUALITY` — tier kualitas ekstraksi `good/fair/poor`.

### `backend/app/core/pipeline/metadata_resolver.py` — resolusi metadata paper via GROBID, CrossRef, OpenAlex, lalu heuristik.
**Fungsi:**
- `_current_year()` — mengembalikan tahun saat ini.
- `valid_year(y)` — memvalidasi tahun pada rentang wajar; murni rule-based.
- `extract_doi(text)` — mengambil DOI pertama dari teks yang sudah dinormalisasi.
- `extract_doi_candidates(text)` — mengambil semua DOI unik, memprioritaskan DOI artikel daripada DOI jurnal/ISSN; rule-based.
- `_heuristic_title(text)` — menebak judul dari baris awal sebagai fallback terakhir; rule-based.
- `_heuristic_year(text)` — menebak tahun terbit dari pola copyright/published/accepted atau frekuensi tahun; rule-based.
- `_crossref_by_doi(doi)` — lookup CrossRef sync via `CrossRefAPI.get_by_doi`; jaringan HTTP.
- `_lookup_by_title(title)` — lookup OpenAlex via `http_cache.get_json`; jaringan HTTP ke OpenAlex.
- `resolve_metadata(pdf_path, full_text, source, extraction_quality='good', title_hint=None, doi_hint=None) -> Tuple[PaperMeta, Optional[List[Tuple[str, str]]]]` — menyusun metadata final: GROBID dulu, lalu DOI→CrossRef, lalu heuristik, lalu OpenAlex; juga bisa mengembalikan section hasil GROBID.

### `backend/app/core/pipeline/text_cleaning.py` — pembersihan teks PDF: Unicode, footer/header, de-hyphenation, dan kualitas ekstraksi.
**Fungsi:**
- `_is_table_row(stripped)` — mendeteksi baris tabel/angka agar dibuang; rule-based.
- `normalize_unicode(text)` — memperbaiki ligature/mojibake via `ftfy` lalu NFKC; lokal, non-LLM.
- `dehyphenate(text)` — menggabungkan kata yang terputus karena line-break, sambil menjaga compound yang sah; rule-based.
- `_normalize_line_key(line)` — membuat kunci normalisasi untuk mendeteksi header/footer berulang.
- `find_repeated_lines(pages, threshold=0.5, min_pages=3)` — mendeteksi pola header/footer yang muncul di banyak halaman; rule-based.
- `is_noise_line(line, repeated)` — menandai nomor halaman, ToC leader, baris simbol, tabel, dan repeated headers sebagai noise; rule-based.
- `strip_page_artifacts(page, repeated)` — membuang artifact halaman dari satu halaman teks.
- `assess_quality(text)` — memberi label `good/fair/poor` berdasarkan rasio huruf dan karakter replacement.
- `detect_language(text)` — deteksi bahasa best-effort via `langdetect`; lokal.
- `clean_page_text(page, repeated)` — menjalankan strip artifact, Unicode repair, dan de-hyphenation.
- `clean_pages(pages)` — membersihkan semua halaman sambil mempertahankan batas halaman.
- `collapse_whitespace(text)` — merapikan whitespace menjadi spasi tunggal.
- `reflow_paragraphs(text)` — menyambung baris PDF yang terpecah menjadi paragraf/sentence yang wajar; rule-based.

### `backend/app/core/pipeline/layout.py` — ekstraksi layout font-aware dari PyMuPDF untuk deteksi header berbasis ukuran/tebal font.
**Kelas:**
- `LineInfo` — representasi satu baris teks PDF dengan `text`, `size`, `bold`, `page`; tidak memanggil LLM/jaringan.
**Fungsi:**
- `join_spans(spans)` — menyambung span teks sambil menyisipkan spasi jika jarak antar-span menunjukkan word break.
- `extract_layout_lines(pdf_path)` — membaca PDF via PyMuPDF dan mengembalikan baris dengan ukuran font/bold; lokal.
- `body_font_size(lines)` — mengestimasi ukuran font body berdasarkan bobot jumlah karakter.
- `has_font_variation(lines)` — mengecek apakah ada cukup variasi font-size untuk deteksi header berbasis layout.

### `backend/app/core/pipeline/section_normalizer.py` — normalisasi judul section dan deteksi reference section.
**Fungsi:**
- `_strip_leading_numbering(title)` — membuang penomoran awal section seperti `1.` atau `II`.
- `normalize_section(raw_title)` — memetakan judul section mentah ke label kanonik; rule-based.
- `looks_like_references(text, min_ratio=0.35)` — heuristik apakah teks tampak seperti daftar pustaka; rule-based.
- `classify_reference(section_normalized, text)` — menggabungkan label section dan heuristik isi untuk menentukan `is_reference`; rule-based.

### `backend/app/core/pipeline/token_chunker.py` — chunking berbasis token, sentence-safe, dan bounded per section.
**Fungsi:**
- `count_tokens(text)` — menghitung token via tiktoken atau fallback kasar.
- `split_sentences(text)` — memecah teks menjadi kalimat tanpa kehilangan isi; lokal.
- `_split_long_sentence(sentence, ceiling)` — memecah blob panjang di batas kata bila melampaui ceiling token.
- `_overlap_sentences(sentences, overlap_tokens)` — mengambil trailing sentences untuk overlap antar chunk.
- `_pack_sentences(sentences, target_tokens, max_tokens, min_tokens)` — mengelompokkan kalimat jadi grup token-sized tanpa overlap dulu.
- `chunk_document(sections, meta, target_tokens=384, max_tokens=512, min_tokens=64, overlap_ratio=0.125) -> List[PipelineChunk]` — membentuk chunk final per section, mengisi metadata paper, dan menandai reference chunk; rule-based, tanpa LLM.

### `backend/app/core/pipeline/references.py` — ekstraksi entri daftar pustaka dan pembuatan kunci pencocokan bibliografis.
**Kelas:**
- `ReferenceEntry` — satu entri referensi terurai dengan `raw`, `key`, `doi`, `year`, `first_author`, `title_guess`; tidak memanggil LLM/jaringan.
  - `to_dict()` — serialisasi entri referensi ke dict.
  - `from_dict(data)` — membuat `ReferenceEntry` dari dict.
**Fungsi:**
- `_clean(text)` — merapikan whitespace dan menghapus soft hyphen.
- `content_words(text, limit=6)` — mengambil kata isi untuk kunci judul.
- `split_reference_entries(text)` — memecah blok referensi jadi entri mentah memakai marker `[n]`, `n.`, atau pola author-year; rule-based.
- `_first_author(text)` — menebak penulis pertama dari entri referensi.
- `_title_guess(text, year_match)` — menebak judul referensi dari entri.
- `parse_reference(raw) -> ReferenceEntry` — menurunkan DOI/tahun/author/judul dan `key` pencocokan dari satu referensi; rule-based.
- `_chunk_fields(chunk)` — menormalisasi akses text/metadata dari dict atau objek chunk.
- `_has_entry_markers(text)` — mengecek apakah teks punya cukup marker referensi bernomor.
- `reference_text(chunks, full_text='')` — mengekstrak blok referensi dari chunk berlabel reference atau tail dokumen.
- `extract_references(chunks, full_text='') -> List[ReferenceEntry]` — mengembalikan daftar entri referensi terurai.

### `backend/app/core/pipeline/dedup.py` — penghapusan chunk duplikat identik.
**Fungsi:**
- `_text_hash(text)` — hash SHA1 atas teks yang dinormalisasi.
- `deduplicate_chunks(chunks) -> List[PipelineChunk]` — membuang chunk duplikat dengan mempertahankan kemunculan pertama; rule-based.

### `backend/app/core/pipeline/corpus_relevance.py` — pemeriksaan apakah satu paper “nyambung” dengan korpus batch.
**Kelas:**
- `RelevanceReport` — laporan relevansi per sumber dengan `source`, `score`, `nearest`, `flagged`; tidak memanggil LLM/jaringan.
  - `to_dict()` — serialisasi laporan ke dict.
**Fungsi:**
- `build_probe(title, chunks)` — membangun probe topik dari judul + dua chunk non-reference pertama.
- `_cosine(a, b)` — cosine similarity vektor float.
- `_as_floats(vector)` — mengubah embedding row ke list float.
- `check_corpus_relevance(probes, embedder=None, threshold=0.5) -> List[RelevanceReport]` — memberi skor kesamaan tiap paper terhadap paper lain terdekat; memakai embedding lokal bila tersedia, jika tidak mengembalikan skor nol.

### `backend/app/core/pipeline/io.py` — pembaca/penulis JSONL untuk artefak pipeline.
**Fungsi:**
- `source_name(path)` — menormalkan nama sumber PDF dengan membuang prefix indeks job.
- `write_chunks_jsonl(path, results, job_id, note=...) -> Dict[str, Any]` — menulis file JSONL berisi meta line dan semua chunk; I/O lokal.
- `read_jsonl(path) -> List[Dict[str, Any]]` — membaca JSONL ke list dict.
- `write_jsonl(path, records) -> int` — menulis iterable dict ke JSONL dan mengembalikan jumlah record.

### `backend/app/core/pipeline/pipeline.py` — orchestrator end-to-end PDF→metadata→section→chunk untuk pipeline baru.
**Kelas:**
- `PipelineResult` — hasil ekstraksi satu PDF: `meta`, `chunks`, `full_text`, `num_pages`, `extraction_method`, `grobid_used`; tidak memanggil LLM/jaringan langsung.
- `_CompatChunk` — adaptor bentuk legacy chunk untuk ingestion lama.
- `_CompatDoc` — adaptor bentuk legacy processed document untuk FastAPI ingestion.
  - `__init__(result, job_id=None)` — membungkus hasil pipeline baru menjadi bentuk lama sambil mempertahankan metadata lengkap.
**Fungsi:**
- `_env_flag(name, default)` — membaca env flag boolean.
- `_is_false_header(text)` — menolak baris yang tampak seperti author/identifier line, bukan header.
- `_is_header_line(line)` — deteksi header section yang ketat dari teks mentah; rule-based.
- `_extract_pages(pdf_path) -> Tuple[List[str], str]` — ekstraksi teks per halaman via PyMuPDF lalu PyPDF fallback; lokal.
- `_build_page_index(cleaned_pages) -> Tuple[str, List[int]]` — menggabungkan halaman dan mencatat offset akhir tiap halaman.
- `_page_of_offset(offset, page_ends) -> int` — memetakan offset karakter ke nomor halaman.
- `_detect_sections_with_pages(full_text, page_ends)` — mendeteksi section dari teks bersih dengan track halaman.
- `_grobid_sections_with_pages(grobid_sections, full_text, page_ends)` — menempelkan page_start ke section hasil GROBID.
- `_extract_title_by_font(pdf_path)` — heuristik judul dari blok font terbesar di halaman pertama; local PyMuPDF, bukan LLM.
- `_extract_own_doi(raw_pages)` — menemukan DOI dokumen sendiri, bukan DOI referensi; rule-based.
- `_pages_from_lines(lines)` — merekonstruksi teks per halaman dari `LineInfo`.
- `_layout_is_header(text, size, bold, body_size)` — menilai apakah baris layout merupakan header visual.
- `_sections_from_layout(lines)` — memotong section dari layout-aware lines.
- `_postprocess_sections(sections, min_section_chars=120, min_other_chars=600)` — memperbaiki split mid-sentence dan menggabung section pendek.
- `_apply_section_inheritance(sections)` — memberi label canonical pada subsections dengan pewarisan dari main section.
- `_ocr_pages(pdf_path)` — memanggil `OcrdClient` untuk recovery teks PDF scan; jaringan/servis OCR eksternal.
- `process_pdf(pdf_path, source=None, target_tokens=384, max_tokens=512, overlap_ratio=0.125, ocr_mode='auto') -> PipelineResult` — jalur utama: ekstraksi teks, cleaning, quality check, OCR fallback, metadata resolution (GROBID/CrossRef/OpenAlex/heuristik), sectioning, chunking, dedup, lalu mengembalikan hasil pipeline.
- `process_pdf_as_document(pdf_path, source=None, job_id=None) -> _CompatDoc` — adaptor backward-compatible untuk ingestion FastAPI.

**Alur utama:**
- `process_pdf()` memanggil `_extract_pages()`/`extract_layout_lines()`, lalu `clean_pages()`, lalu `resolve_metadata()`.
- Section dibentuk lewat GROBID jika tersedia, jika tidak lewat `_sections_from_layout()` atau `_detect_sections_with_pages()`, lalu dihealkan `_postprocess_sections()` dan `_apply_section_inheritance()`.
- `chunk_document()` membuat chunk token-aware per section, lalu `deduplicate_chunks()` membuang duplikasi identik.
- `process_pdf_as_document()` membungkus hasil baru ke format legacy agar jalur API lama tetap jalan.
- `io.write_chunks_jsonl()` dipakai untuk ekspor artefak CLI/API secara konsisten.
- `section_normalizer.classify_reference()` menandai chunk referensi agar tidak ikut indexing RAG.

## backend/app/core/retrieval/

### `backend/app/core/retrieval/__init__.py` — paket retrieval RAG.
**Fungsi:**
- Tidak ada fungsi/kelas; hanya mengekspor `VectorStore` dan `RAGRetriever`.

### `backend/app/core/retrieval/vector_store.py` — lapisan penyimpanan vektor ChromaDB untuk embedding, simpan, dan pencarian semantik.
**Kelas:**
- `Document` — representasi dokumen ber-metadata dan embedding opsional; tidak memanggil LLM/jaringan.
- `SearchResult` — hasil pencarian semantik berisi `document`, `score`, `rank`; tidak memanggil LLM/jaringan.
- `VectorStore` — wrapper ChromaDB + sentence-transformers untuk simpan, cari, hapus, dan statistik dokumen.
  - `_get_or_create_collection()` — mengambil atau membuat collection ChromaDB.
  - `_create_embedding_function()` — membuat embedding function custom untuk ChromaDB.
  - `add_document(content, metadata=None, doc_id=None) -> str` — menambah satu dokumen ke koleksi; memakai embedding lokal Chroma.
  - `add_documents(documents, batch_size=100) -> List[str>` — menambah banyak dokumen secara batch; lokal.
  - `search(query, top_k=5, filter_metadata=None, min_score=None) -> List[SearchResult]` — query semantik ke ChromaDB dengan filter metadata; akses DB lokal.
  - `get_document(doc_id) -> Optional[Document]` — mengambil satu dokumen dari Chroma.
  - `delete_document(doc_id) -> bool` — menghapus satu dokumen dari Chroma.
  - `update_document(doc_id, content=None, metadata=None) -> bool` — memperbarui dokumen di Chroma.
  - `count() -> int` — jumlah dokumen di collection.
  - `count_by_source(source) -> int` — menghitung chunk per sumber untuk deteksi duplikasi upload.
  - `delete_by_metadata(filter_metadata) -> int` — menghapus dokumen yang cocok dengan filter metadata.
  - `get_all_documents(limit=None, offset=0) -> List[Document]` — mengambil semua dokumen dengan pagination.
  - `get_chunks_by_sources(sources) -> List[Document]` — mengekspor semua chunk milik sumber tertentu, dideduplikasi menurut `(source, chunk_index)`.
  - `clear_collection()` — menghapus lalu membuat ulang collection.
  - `embed_text(text) -> List[float]` — menghasilkan embedding tunggal via sentence-transformers lokal.
  - `embed_batch(texts) -> List[List[float]]` — menghasilkan embedding batch via sentence-transformers lokal.
  - `similarity(text1, text2) -> float` — menghitung cosine similarity dua teks via embedding lokal.
  - `get_stats() -> Dict[str, Any]` — statistik collection dan model embedding.
  - `__repr__()` — representasi ringkas object.
**Konstanta/efek penting:**
- Menggunakan `chromadb.PersistentClient` dan `SentenceTransformer`; ini local storage + embedding lokal, bukan HTTP.
- `_write_lock` dipakai untuk serialisasi mutasi agar aman terhadap write concurrency.

### `backend/app/core/retrieval/rag_retriever.py` — retriever dua tahap: vector search lalu reranking/heuristik.
**Kelas:**
- `RetrievalResult` — hasil retrieval dengan `document`, `score`, `rank`, `context`, `relevance_explanation`; tidak memanggil LLM/jaringan.
- `RAGRetriever` — pengambil konteks semantik untuk RAG dengan reranker opsional.
  - `retrieve(query, top_k=None, filter_metadata=None, rerank=True) -> List[RetrievalResult]` — mencari dokumen relevan, menambahkan konteks, lalu rerank; memakai ChromaDB + embedding lokal, dan reranker lokal bila tersedia.
  - `_add_context_windows(results)` — menambahkan chunk tetangga sebagai konteks untuk dokumen chunked.
  - `_rerank_results(query, results)` — rerank dua tahap: cross-encoder jika tersedia, jika tidak heuristik.
  - `_heuristic_rerank(query, results)` — reranker fallback berbasis overlap kata, metadata, dan skor semantik; rule-based.
  - `retrieve_with_expansion(query, top_k=None, expansion_terms=None) -> List[RetrievalResult]` — retrieval dengan perluasan kueri.
  - `_expand_query(query) -> str` — perluasan kueri berbasis kamus sinonim domain; offline, tidak LLM.
  - `_fusion_reciprocal_rank(results_lists) -> List[RetrievalResult]` — fusion multi-query via Reciprocal Rank Fusion.
  - `_fusion_score_average(results_lists) -> List[RetrievalResult]` — fusion multi-query via rerata skor.
  - `retrieve_multi_query(queries, top_k=None, fusion_method='reciprocal_rank') -> List[RetrievalResult]` — menjalankan retrieval beberapa kueri lalu mem-fuse hasil.
  - `get_context_for_generation(query, max_tokens=2000, top_k=None) -> Tuple[str, List[RetrievalResult]]` — menyusun konteks teks terformat untuk LLM generation.
  - `get_statistics() -> Dict[str, Any]` — statistik parameter retrieval.
**Konstanta penting:**
- `QUERY_EXPANSION_MAP` — kamus perluasan kueri CS/ML; rule-based, offline.

### `backend/app/core/retrieval/reranker.py` — wrapper cross-encoder reranker untuk precision tahap kedua retrieval.
**Konstanta:**
- `DEFAULT_RERANKER_MODEL` — model default `cross-encoder/ms-marco-MiniLM-L-6-v2`.
**Kelas:**
- `CrossEncoderReranker` — wrapper ringan untuk sentence-transformers CrossEncoder.
  - `available` — property lazy-load untuk mengecek apakah model bisa dipakai.
  - `_try_load()` — mencoba memuat model reranker; local model load, bukan HTTP.
  - `score(query, passages) -> Optional[List[float]]` — memberi skor tiap passage terhadap query; memakai cross-encoder lokal jika tersedia.
  - `rerank(query, passages, top_k=None) -> Optional[List[Tuple[int, float]]]` — mengurutkan passage berdasarkan skor menurun.

**Alur utama:**
- `VectorStore.search()` melakukan pencarian semantik awal memakai embedding lokal dan ChromaDB.
- `RAGRetriever.retrieve()` menambahkan context window lalu memanggil `_rerank_results()`.
- Jika `CrossEncoderReranker.available` true, reranking memakai cross-encoder lokal; kalau gagal, `_heuristic_rerank()` mengambil alih.
- `retrieve_multi_query()` menggabungkan banyak query dengan RRF atau averaging.
- `get_context_for_generation()` membungkus hasil retrieval menjadi konteks prompt untuk LLM.
- `__init__.py` mengekspor `VectorStore` dan `RAGRetriever` untuk dipakai modul lain.

## backend/app/core/recommendation/

### `backend/app/core/recommendation/__init__.py` — paket rekomendasi riset.
**Fungsi:**
- Tidak ada fungsi/kelas; hanya mengekspor `RecommendationEngine`.

### `backend/app/core/recommendation/engine.py` — mesin rekomendasi paper berbasis content, graph, gap-aware, dan hybrid.
**Kelas:**
- `RecommendationItem` — satu item rekomendasi dengan `paper_id`, `title`, `score`, `rank`, `reasons`, `metadata`; tidak memanggil LLM/jaringan.
- `RecommendationEngine` — penghasil rekomendasi dari retriever, knowledge graph, dan gap analyzer.
  - `__init__(retriever=None, knowledge_graph=None, gap_analyzer=None)` — menyimpan dependensi dan menyiapkan engine.
  - `generate_recommendations(query, user_context=None, strategy='hybrid', top_k=10) -> List[RecommendationItem]` — memilih strategi content/graph/gap/hybrid.
  - `_content_based_recommendations(query, top_k) -> List[RecommendationItem]` — rekomendasi berbasis semantic similarity dari retriever; memakai retrieval lokal, bukan LLM.
  - `_graph_based_recommendations(query, user_context, top_k) -> List[RecommendationItem]` — rekomendasi dari tetangga citation/knowledge graph; graph-based, bukan LLM.
  - `_gap_aware_recommendations(query, user_context, top_k) -> List[RecommendationItem]` — rekomendasi yang mencoba menutupi gap yang terdeteksi; memakai gap analyzer internal.
  - `_hybrid_recommendations(query, user_context, top_k) -> List[RecommendationItem]` — fusi berbobot dari content, graph, dan gap-aware.
  - `explain_recommendation(recommendation, detailed=False) -> str` — membentuk penjelasan manusiawi atas satu rekomendasi.
**Efek penting:**
- Jika `retriever` tidak ada, strategi content fallback kosong.
- Jika `knowledge_graph` tidak ada, graph strategy fallback ke content.
- Jika `gap_analyzer` tidak ada, gap-aware fallback ke content.
- Tidak ada HTTP/LLM langsung di kelas ini; bergantung pada komponen yang disuntik.

### `backend/app/core/recommendation/novelty.py` — skoring kebaruan proposal gap-anchored terhadap korpus.
**Kelas:**
- `_Backend` — backend similarity embeddings atau lexical fallback; internal helper.
  - `uses_embeddings` — property yang menyatakan embedder tersedia atau tidak.
  - `prime(texts)` — batch-encode teks kueri/proposal untuk efisiensi; memakai embedder lokal bila ada.
  - `_corpus_matrix(corpus)` — meng-encode korpus sekali per isi yang berbeda.
  - `similarities(query, corpus) -> List[float]` — similarity query terhadap korpus memakai cosine embedding atau lexical fallback.
- `NoveltyScore` — skor novelty dan priority untuk satu proposal.
  - `to_dict()` — serialisasi skor ke dict.
**Fungsi:**
- `_tokens(text)` — tokenisasi sederhana untuk similarity lexical.
- `_lexical_similarity(a, b)` — overlap coefficient campur Jaccard; rule-based.
- `_cosine(a, b)` — cosine similarity numerik.
- `_as_floats(vector)` — mengubah embedding row jadi list float.
- `actionability(text) -> float` — menilai seberapa eksplisit/metodis proposal; rule-based.
- `novelty_band(novelty) -> str` — mengklasifikasikan novelty ke `derivative/sweet_spot/off_topic`.
- `sweet_spot_distance(novelty) -> float` — jarak dari titik tengah sweet-spot.
- `proposal_text(proposal) -> str` — menyusun teks proposal dari field `title/description/how`.
- `score_proposal(proposal, corpus_texts, corpus_refs, backend, gap_confidence=0.0) -> NoveltyScore` — menghitung novelty, actionability, dan priority composite; memakai embedding lokal jika ada, fallback lexical bila tidak.
- `rank_proposals(proposals, papers, gaps=None, embedder=None) -> List[Dict[str, Any]]` — menambahkan blok novelty/priority lalu mengurutkan proposal.
- `priority_label(priority_score) -> str` — memetakan skor prioritas ke `high/medium/low`.
**Konstanta penting:**
- `NOVELTY_SWEET_SPOT`, `W_GAP`, `W_NOVELTY`, `W_ACTIONABILITY`.
- `_ACTIONABLE_CUES`, `_VAGUE_CUES`, `_TOKEN_RE`.

### `backend/app/core/recommendation/themes.py` — pengelompokan proposal menjadi tema lintas-jurnal.
**Kelas:**
- `Theme` — cluster proposal yang merepresentasikan gap yang sama; field utama `theme_id`, `label`, `members`, `journals`, `priority`, `top_priority`, `run_support`, `topics`.
  - `journal_support` — property jumlah jurnal unik yang mendukung tema.
  - `to_dict()` — serialisasi tema ke dict.
**Fungsi:**
- `_terms(text) -> List[str]` — tokenisasi term penting sambil membuang stopword; rule-based.
- `_priority_of(proposal) -> float` — mengambil `novelty.priority_score` dari proposal.
- `build_themes(proposals, embedder=None, threshold=0.75) -> List[Theme]` — mengelompokkan proposal jadi tema berdasarkan cluster similarity lalu mengurutkannya menurut dukungan jurnal dan prioritas; memakai `cluster_papers()` dari modul graph metrics, bukan LLM.

**Alur utama:**
- `RecommendationEngine.generate_recommendations()` memilih strategi lalu memanggil helper internal yang sesuai.
- Strategy content memanfaatkan `RAGRetriever.retrieve()`; strategy graph memanfaatkan knowledge graph; strategy gap-aware memanfaatkan gap analyzer.
- `novelty.rank_proposals()` menilai proposal gap-anchored sebelum dibangun menjadi tema.
- `themes.build_themes()` mengelompokkan proposal jadi cluster lintas-jurnal, dengan `cluster_papers()` sebagai dasar pengelompokan.
- `__init__.py` mengekspor `RecommendationEngine` untuk dipakai service/endpoint lain.

## backend/app/core/gap_mining/

### `backend/app/core/gap_mining/__init__.py` — paket gap mining tahap 2.
**Fungsi:**
- Tidak ada fungsi/kelas; hanya mengekspor `select_candidates`, `GAP_PHRASES_EN`, dan `GAP_PHRASES_ID`.

### `backend/app/core/gap_mining/candidates.py` — seleksi kandidat gap tanpa LLM dari chunk yang sudah bersih dan ber-section.
**Fungsi:**
- `matched_phrases(text) -> List[str]` — mencari frasa gap yang muncul di teks; rule-based.
- `select_candidates(chunks) -> List[Dict[str, Any]]` — memilih chunk kandidat gap dari section conclusion/discussion, phrase match, abstract, intro awal, dan tail dokumen; tanpa LLM.
- `with_context(candidate, by_source) -> str` — membangun konteks LLM dari chunk sebelumnya, kandidat, dan sesudahnya.
**Konstanta penting:**
- `GAP_PHRASES_EN`, `GAP_PHRASES_ID`, `_PHRASE_RE`, `_TARGET_SECTIONS`.
- Semua ini murni rule-based; tidak ada HTTP/LLM langsung.

### `backend/app/core/gap_mining/extractor.py` — ekstraksi gap terstruktur oleh LLM dari kandidat terpilih.
**Fungsi:**
- `_default_generate(prompt, system)` — memanggil `copilot_client.generate(..., json_mode=True)`; ini akses LLM.
- `_parse_json_array(text) -> List[Dict[str, Any]]` — parsing best-effort output JSON array dari LLM.
- `_normalize_gap(raw, candidate) -> Optional[Dict[str, Any]]` — memvalidasi dan memperkaya gap mentah dengan metadata kandidat.
- `extract_gaps_from_candidate(candidate, context_text, generate_fn=_default_generate) -> List[Dict[str, Any]]` — menjalankan prompt LLM untuk satu kandidat lalu mengembalikan gap ternormalisasi.
**Konstanta penting:**
- `GAP_TYPES`, `TOPICS`, `SYSTEM_PROMPT`, `_PROMPT_TEMPLATE`.
- Jalur ini jelas memanggil LLM (Copilot), bukan rule-based.

### `backend/app/core/gap_mining/verify.py` — verifikasi grounding verbatim gap statement terhadap konteks sumber.
**Fungsi:**
- `verify_gap_statement(statement, context_text) -> float` — skor fuzzy containment statement di konteks sumber.
- `is_grounded(statement, context_text, threshold=QUOTE_MATCH_THRESHOLD) -> bool` — memutuskan apakah statement cukup grounded.
- `verify_gaps(gaps, by_source, threshold=QUOTE_MATCH_THRESHOLD) -> List[Dict[str, Any]]` — memberi `grounding_score`, memilih evidence chunk terbaik, dan membuang gap yang tidak grounded.
**Integrasi penting:**
- Menggunakan `fuzzy_contains` dari `gap_detection.quote_grounding`; ini rule-based/fuzzy, bukan LLM.

### `backend/app/core/gap_mining/novelty.py` — cek kebaruan gap terhadap literatur recent (OpenAlex/Semantic Scholar).
**Fungsi:**
- `novelty_disabled() -> bool` — membaca env `OPENALEX_DISABLED` untuk mematikan cek luar.
- `build_keywords(gap, max_terms=8) -> str` — menyusun query search dari `gap_statement` + topic term; rule-based.
- `_overlap_score(query, paper) -> float` — menghitung overlap term query dengan title+abstract paper.
- `classify_novelty(gap, openalex=None, from_date='2024-01-01', max_results=8, strong_threshold=0.5, s2_search_fn=None) -> Dict[str, Any]` — menentukan status `open/partially_addressed/addressed/unchecked`; memakai OpenAlex HTTP, optional Semantic Scholar, dan cache.
- `annotate_gaps(gaps, openalex=None, from_date='2024-01-01', s2_search_fn=None, min_interval=1.0, max_retries=4, on_progress=None, limit=0) -> List[Dict[str, Any]]` — menempelkan novelty info ke semua gap dengan coverage penuh, mengelola quota/retry/cooldown.
**Konstanta penting:**
- `NOVELTY_STATUSES`, `ENV_DISABLED`, `DISABLED_REASON`, `LIMIT_REASON`, `STRONG_MATCH_THRESHOLD`, `_TOPIC_TERMS`.
- Modul ini memanggil jaringan ke OpenAlex (dan opsional S2), bukan LLM.

**Alur utama:**
- `select_candidates()` memilih chunk calon gap dari hasil pipeline tahap 1.
- `with_context()` membungkus kandidat dengan tetangga chunk agar prompt LLM punya bukti cukup.
- `extract_gaps_from_candidate()` mengubah kandidat menjadi struktur gap terverifikasi awal via Copilot LLM.
- `verify_gaps()` memfilter gap yang tidak verbatim-grounded terhadap source chunk.
- `annotate_gaps()` memeriksa apakah gap masih open terhadap literatur recent melalui OpenAlex/S2.
- `__init__.py` mengekspor selektor kandidat untuk dipakai tahap berikutnya.

## backend/app/core/runtime/

### `backend/app/core/runtime/__init__.py` — paket state runtime per analisis.
**Fungsi:**
- Tidak ada fungsi/kelas; hanya mengekspor `AnalysisContext`, `AnalysisContextManager`, `ScopedRAGRetriever`, dan `create_analysis_context`.

### `backend/app/core/runtime/analysis_context.py` — lifecycle state per job analisis, termasuk scoped retriever dan graph/fact state.
**Kelas:**
- `ScopedRAGRetriever` — subclass `RAGRetriever` yang membatasi retrieval hanya ke chunk milik satu `analysis_job_id`.
  - `__init__(*args, analysis_job_id, **kwargs)` — menyimpan job scope lalu memanggil parent init.
  - `retrieve(query, top_k=None, filter_metadata=None, rerank=True)` — memaksa filter metadata `analysis_job_id` atau menggabungkannya dengan filter lain.
- `AnalysisContext` — state mutable milik satu job analisis durabel; berisi `vector_store`, `llm`, `retriever`, `fact_table`, `knowledge_graph`, `fact_extractor`, `relation_classifier`, `rule_engine`, `gap_analyzer`, `coordinator`.
  - `graph_snapshot()` — membangun snapshot serializable graph + fact table stats untuk endpoint graph.
- `AnalysisContextManager` — manager thread-safe untuk konteks aktif.
  - `__init__()` — menyiapkan map konteks dan lock.
  - `get_or_create(job_id)` — mengambil atau membuat konteks baru.
  - `get(job_id)` — mengambil konteks jika ada.
  - `release(job_id)` — membuang konteks transient setelah hasil persisten.
  - `active_job_ids()` — daftar job aktif.
**Fungsi:**
- `create_analysis_context(job_id, scope_retrieval=True) -> AnalysisContext` — merakit ulang graph agentik, fact table, retriever, rule engine, gap analyzer, dan coordinator untuk satu job; memanggil dependency app dan model lokal, bukan HTTP kecuali dependensi yang disuntik.
**Konstanta:**
- `analysis_contexts` — singleton `AnalysisContextManager`.

**Alur utama:**
- `create_analysis_context()` memanggil dependency FastAPI untuk vector store, LLM, reranker, dan NLI model.
- `ScopedRAGRetriever` memastikan retrieval job-specific agar state satu user tidak bocor ke job lain.
- `AnalysisContext.graph_snapshot()` dipakai endpoint graph untuk mengekspor keadaan knowledge graph dengan aman.
- `AnalysisContextManager` menyimpan konteks aktif dan melepasnya setelah durasi job selesai.

## backend/app/telemetry/

### `backend/app/telemetry/__init__.py` — helper telemetry operasional tanpa isi konten.
**Fungsi:**
- Tidak ada fungsi/kelas; hanya mengekspor `record_job_event` dan `telemetry_middleware`.

### `backend/app/telemetry/recorder.py` — middleware telemetry metadata-only dan pencatatan event job.
**Fungsi:**
- `telemetry_middleware(request, call_next) -> Response` — memberi `X-Request-ID`, mengukur durasi, dan logging metadata request/response tanpa menyimpan prompt/query/content; async middleware.
- `record_job_event(job_id, event_type, phase=None, status=None, duration_ms=None, data=None) -> None` — mencatat event job ke `job_store` jika telemetry diaktifkan; metadata-only.
**Integrasi penting:**
- Menggunakan `get_config()` dan `job_store`; tidak memproses konten sensitif.

**Alur utama:**
- `main.py` memasang `telemetry_middleware` sebagai HTTP middleware.
- `record_job_event()` dipanggil oleh komponen job untuk audit metadata saja.
- Modul ini sengaja tidak menyimpan prompt, query, PDF text, atau chat message.

## backend/app/models/

### `backend/app/models/__init__.py` — paket schema request/response.
**Fungsi:**
- Tidak ada fungsi/kelas; file ini kosong pada snapshot ini.

### `backend/app/models/requests.py` — skema request API FastAPI.
**Kelas:**
- `QueryRequest` — request query riset dengan `query`, `top_k`, `filters`.
- `RecommendationRequest` — request rekomendasi dengan `query`, `max_results`, `strategy`, `user_context`.
- `GapDetectionRequest` — request deteksi gap dengan `topic` dan `depth`.
- `ChatRequest` — request chat dengan `message`, `use_history`, `conversation_id`.
- `PaperSearchRequest` — request pencarian paper dengan `query`, `max_results`, `sources`, `deduplicate`, `year_from`, `year_to`, `embedding_model`.
- `PaperToDownload` — satu item paper untuk diunduh, dengan `title`, `doi`, `pdf_url`, `source_api`.
- `DownloadAnalyzeRequest` — request batch download+analisis berisi `papers`.
- `IdeaToQueryRequest` — request konversi ide riset menjadi query akademik dengan field `idea`.
- `MarkedPapersRequest` — request analisis paper yang sudah ditandai user, berisi `papers` dan `query`.
**Catatan:**
- Semua model ini Pydantic, murni validation schema; tidak memanggil LLM/jaringan.

### `backend/app/models/responses.py` — skema response API termasuk gap indicator, rule engine, dan hasil analisis penuh.
**Kelas/Enum:**
- `IngestResponse` — respons ingest dengan `success`, `doc_id`, `message`, `chunks_created`.
- `HealthResponse` — respons health dengan `status`, `components`, `version`.
- `PaperSearchResponse` — respons pencarian paper dengan `query`, `total_results`, `papers`, `sources_searched`, `embedding_model`.
- `IndicatorType` — enum jenis indikator gap: `FRAGMENTATION`, `INCONSISTENCY`, `INCOMPLETENESS`, `SUPPORT_GAP`.
- `RuleVerdictType` — enum verdict rule engine: `PASS`, `FLAG`, `REJECT`.
- `FactTripleModel` — triple fakta KG: `subject`, `predicate`, `object`, `confidence`, `source`, `is_inferred`.
- `RuleResultModel` — hasil satu rule: `rule_id`, `rule_name`, `category`, `verdict`, `confidence`, `explanation`.
- `RuleEngineReportModel` — report agregat rule engine: `overall_verdict`, `adjusted_confidence`, `total_rules`, `passed`, `flagged`, `rejected`, `rules`, `summary`.
- `GapIndicatorModel` — satu indikator gap dengan field penting `indicator_type`, `title`, `description`, `confidence`, `adjusted_confidence`, `calibrated_confidence`, `needs_review`, `abstention_reasons`, `calibration`, `provenance`, `rule_engine_verdict`, `requires_human_validation`, `evidence`, `supporting_quotes`, `evidence_subgraph`, `supporting_papers`, `suggested_directions`, `sub_indicators`.
- `ReasoningStep` — satu langkah reasoning agent dengan `phase`, `timestamp`, `iteration`, `actions`, `status`, `error`.
- `SelfCritiqueModel` — hasil self-critique agent dengan `overall_score`, `dimensions`, `issues`, `suggestions`, `requires_revision`.
- `FactTableStatsModel` — statistik fact table/KG: `total_entities`, `total_facts`, `entity_types`, `predicate_types`, `papers_indexed`.
- `AnalysisResponseModel` — respons penuh pipeline agentik dengan `query`, `execution_mode`, `gap_indicators`, `total_indicators`, `rule_engine_report`, `fact_table_stats`, `recommendations`, `reasoning_trace`, `self_critique`, `metadata`, `analysis`.
**Catatan:**
- Semua model ini Pydantic/Enum; tidak ada panggilan LLM/jaringan di sini.

**Alur utama:**
- `requests.py` mendefinisikan kontrak input endpoint.
- `responses.py` mendefinisikan kontrak output endpoint termasuk report gap, rule engine, dan analisis lengkap.
- `IndicatorType` dan `RuleVerdictType` menjadi basis skema status untuk modul gap detection dan validation.
- `AnalysisResponseModel` menggabungkan semua hasil lintas modul untuk dikirim dari endpoint analisis.

## backend/app/

### `backend/app/__init__.py` — penanda paket aplikasi.
**Fungsi:**
- Tidak ada fungsi/kelas; file kosong pada snapshot ini.

### `backend/app/core/__init__.py` — penanda paket core.
**Fungsi:**
- Tidak ada fungsi/kelas; file kosong pada snapshot ini.

### `backend/app/main.py` — entry point FastAPI yang merakit app, middleware, lifespan, dan router.
**Fungsi/Kelas:**
- `config = get_config()` — memuat konfigurasi runtime global; ini inisialisasi konfigurasi, bukan fungsi.
- `lifespan(app: FastAPI)` — startup/shutdown lifecycle: logging config, membuat direktori data/log, inisialisasi vector store, validasi OCR, start analysis queue, register pipeline handler, lalu shutdown queue/copilot/cleanup; async context manager.
- `app = FastAPI(...)` — instans FastAPI utama dengan `lifespan`.
- `add_request_telemetry(request, call_next)` — middleware HTTP yang meneruskan ke `telemetry_middleware`; async.
- `enforce_rate_limit(request, call_next)` — middleware rate limit dinamis jika diaktifkan; async dan memakai `create_rate_limit_middleware`.
- `if __name__ == "__main__": uvicorn.run(...)` — menjalankan server Uvicorn.
**Router yang di-mount:**
- `health.router` dengan tag `Health`
- `documents.router` prefix `/api`
- `papers.router` prefix `/api/papers`
- `analysis.router` prefix `/api`
- `graph.router` prefix `/api/knowledge graph`
- `skills.router` prefix `/api/skills`
- `research.router` prefix `/api/research`
**Middleware penting:**
- `CORSMiddleware` jika `config.api.cors_enabled`.
- Telemetry middleware selalu dipasang via `@app.middleware("http")`.
- Rate limit middleware dipasang kondisional jika `config.api.rate_limit_enabled`.
**Catatan proses:**
- Startup men-`register()` pipeline kerja ke queue, lalu `queue.start(auto_analysis.process_auto_analysis)`.
- Shutdown memanggil `queue.stop(wait=True)`, `copilot_client.stop()`, lalu cleanup job store dan chunks di vector store.

**Alur utama:**
- `lifespan()` menyiapkan runtime: folder data/log, vector store, OCR check, queue, dan pipeline registration.
- Middleware telemetry mencatat request metadata; rate limit opsional membatasi traffic per IP.
- Router API di-mount langsung di app untuk health, documents, papers, analysis, graph, skills, dan research pipeline.
- Shutdown membersihkan job store, vector store chunks per job, dan input directory yang kedaluwarsa.

## Tambahan — fungsi/kelas bersarang (nested)

### `backend/app/core/pipeline/text_cleaning.py`
- `_join(match: re.Match) -> str` — bersarang di `dehyphenate`; callback `re.sub` yang menyambung kata terpotong tanda hubung di akhir baris: jika ekor kata ada di `_COMPOUND_TAIL` (kata majemuk asli) tanda hubung dipertahankan, selain itu digabung tanpa hubung.

### `backend/app/core/pipeline/metadata_resolver.py`
- `_is_issn_like(doi: str) -> bool` — bersarang di `extract_doi_candidates`; mendeteksi DOI yang sufiksnya berpola ISSN (`dddd-dddX`, DOI tingkat jurnal) agar diurutkan paling akhir setelah DOI artikel.

### `backend/app/core/pipeline/pipeline.py`
- `_flush()` — bersarang di `_sections_from_layout`; menutup section yang sedang dikumpulkan: mereflow paragraf `cur_lines` dan mendorong tuple `(heading, teks, halaman)` ke `sections`, lalu mereset state (`nonlocal`).
- `_issn_like(doi: str) -> bool` — bersarang di `_extract_own_doi`; sama seperti `_is_issn_like` di metadata_resolver — menurunkan prioritas DOI berpola ISSN saat memilih DOI milik paper sendiri dari halaman pertama.

### `backend/app/core/gap_mining/candidates.py`
- `_add(chunk, reason, phrases=None)` — bersarang di `select_candidates`; memasukkan chunk ke dict `selected` dengan `candidate_reason` dan `matched_phrases`; jika chunk sudah ada, alasan baru ditambahkan (dipisah koma) tanpa duplikasi.

### `backend/app/core/retrieval/vector_store.py`
- `CustomEmbeddingFunction(embedding_functions.EmbeddingFunction)` — kelas bersarang di `VectorStore._create_embedding_function`; adaptor agar model Sentence-Transformers lokal bisa dipakai ChromaDB sebagai embedding function.
  - `__init__(model)` — menyimpan model embedding.
  - `__call__(input: List[str]) -> List[List[float]]` — meng-encode batch teks dengan `model.encode(..., show_progress_bar=False)` (model lokal, tanpa jaringan) dan mengembalikannya sebagai list float.


<a id="bagian-04"></a>
# Bagian 04 — api — endpoint FastAPI

## backend/app/api/

### `backend/app/api/__init__.py` — file kosong (0 byte); hanya penanda paket `backend.app.api`.

### `backend/app/api/dependencies.py` — factory dependency singleton untuk komponen inti: vector store, LLM, retrieval, knowledge graph, validasi, dan konteks analisis per-job.
**Fungsi:**
- `get_vector_store() -> VectorStore` — membuat/mengembalikan `VectorStore` singleton dengan konfigurasi persist directory, collection, dan embedding model.
- `get_glm_interface() -> GLMInterface` — membuat/mengembalikan interface LLM utama (`GLMInterface`) dari konfigurasi model runtime.
- `get_reranker()` — membuat/mengembalikan cross-encoder reranker bila diaktifkan; kalau gagal/disabled mengembalikan `None`.
- `get_retriever() -> RAGRetriever` — membuat/mengembalikan retriever RAG yang memakai vector store, reranker, dan batas top-k/min score.
- `get_knowledge_graph() -> KnowledgeGraphBuilder` — membuat/mengembalikan pembangun knowledge graph singleton.
- `get_gap_analyzer() -> GapAnalyzer` — membuat/mengembalikan analyzer gap yang menggabungkan vector store, KG, LLM, fact table, relation classifier, dan rule engine.
- `get_fact_table() -> FactTable` — membuat/mengembalikan `FactTable` singleton untuk fakta SPO.
- `get_fact_extractor() -> FactExtractor` — membuat/mengembalikan `FactExtractor` berbasis LLM.
- `get_rule_engine() -> RuleEngine` — membuat/mengembalikan rule engine yang memvalidasi klaim terhadap fact table.
- `get_nli_model()` — membuat/mengembalikan model NLI dedicated bila diaktifkan; kalau tidak tersedia mengembalikan `None`.
- `get_relation_classifier() -> RelationClassifier` — membuat/mengembalikan classifier relasi berbasis LLM + NLI model.
- `get_recommendation_engine() -> RecommendationEngine` — membuat/mengembalikan engine rekomendasi yang menggabungkan retriever, KG, dan gap analyzer.
- `get_paper_api() -> AggregatedPaperAPI` — membuat/mengembalikan klien agregator API paper eksternal.
- `get_coordinator() -> CoordinatorAgent` — membuat/mengembalikan coordinator agent LangGraph yang merangkai analyzer, detector, recommender, dan tool-agent.
- `get_document_processor() -> DocumentProcessor` — membuat/mengembalikan processor dokumen PDF dengan konfigurasi chunking dan OCR.
- `get_analysis_context(job_id: str)` — mengambil/membuat konteks mutable terisolasi untuk satu job analisis.
- `release_analysis_context(job_id: str) -> None` — melepas konteks analisis job setelah job selesai.
- `create_ephemeral_analysis_context()` — membuat konteks analisis sekali pakai untuk request API tanpa job persisten.

### `backend/app/api/auto_analysis.py` — worker sinkron untuk pipeline lama 8 tahap upload-and-analyze yang berjalan di thread pool queue.
**Fungsi/Kelas:**
- `_set_analysis_job(job_id: str, **updates)` — memuat job dari job store, menggabungkan update, lalu menyimpan kembali state job.
- `_get_analysis_job(job_id: str)` — mengambil job aktif/tersimpan dari job store.
- `JobCancelled` — exception penanda pembatalan job di antara fase analisis.
- `_load_author_gaps(gap_job_id: str) -> tuple[list[dict], str]` — memuat catatan gap mining dari job penelitian lain lalu mengekstrak gap yang dinyatakan penulis.
- `_ensure_job_active(job_id: str) -> None` — memeriksa apakah job dibatalkan dan melempar `JobCancelled` bila perlu.
- `_save_stage_artifact(job_id: str, phase: str, kind: str, label: str = "", payload=None) -> None` — menyimpan artefak tahap secara best-effort ke job store; kegagalan tidak memutus pipeline.
- `_traced_generate(glm, job_id: str, phase: str, label: str, prompt: str, **kwargs) -> str` — memanggil LLM, melacak prompt/response, dan menyimpan artefak LLM beserta skill yang dipakai.
- `_add_uploaded_paper_similarity(papers, vector_store) -> None` — menghitung similarity antar paper yang baru diunggah saja dan menuliskannya ke struktur paper.
- `process_auto_analysis(job_id: str, pdf_paths: List[Path] | None = None)` — menjalankan pipeline lama: ingest PDF → ekstrak topik → analisis basis/persamaan/kekurangan/workflow → sinkronisasi gap/coordinator → ringkasan → gap/rekomendasi → roadmap → intro proposal → simpan hasil final; memakai LLM, vector store, fact table, rule engine, dan job store.

### `backend/app/api/routes/__init__.py` — file kosong (0 byte); penanda paket `backend.app.api.routes` (router diimpor per-modul di `main.py`).

### `backend/app/api/routes/analysis_helpers.py` — helper parsing/validasi hasil LLM untuk analisis seleksi paper, weakness, gap, rekomendasi, dan roadmap.
**Fungsi:**
- `_parse_selection_json(raw: str) -> dict` — parsing JSON hasil analisis seleksi paper dari LLM dengan fallback yang toleran.
- `_ground_selection_suggestions(suggestions: list, papers: list[dict]) -> list[dict]` — memverifikasi/menautkan saran penelitian ke paper input yang benar-benar mendukungnya.
- `_parse_weaknesses_json(raw: str) -> dict` — parsing JSON kelemahan paper dari LLM.
- `_normalize_text(s: str) -> str` — normalisasi teks untuk pencocokan/fuzzy matching.
- `_fuzzy_contains(needle: str, haystack: str, threshold: float = 0.82) -> float` — menghitung kecocokan fuzzy apakah satu teks terkandung di teks lain.
- `_content_word_overlap(claim: str, full_norm: str) -> float` — mengukur overlap kata konten antara klaim dan teks lengkap.
- `_verify_paper_weaknesses(...)` — memverifikasi apakah poin kelemahan LLM benar-benar didukung teks jurnal dan bukti chunk.
- `_parse_gap_json(raw: str) -> list` — parsing JSON gap hasil LLM menjadi daftar struktur gap.
- `_parse_gap_text(text: str) -> list` — fallback parsing gap dari teks non-JSON.
- `_coerce_rec_dict(item: dict, idx: int) -> dict` — memaksa item rekomendasi menjadi struktur dict yang konsisten.
- `_parse_recommendations_json(raw: str) -> list` — parsing JSON rekomendasi penelitian dari LLM.
- `_parse_recommendations_text(text: str) -> list` — fallback parsing rekomendasi dari teks biasa.
- `_is_degenerate_text(s: str) -> bool` — mendeteksi teks degenerat seperti placeholder kosong/generic.
- `_clean_rec_field(s: str) -> str` — membersihkan field teks rekomendasi dari format/marker yang tidak diinginkan.
- `_build_recommendations_from_gaps(gaps: list) -> list` — menyusun rekomendasi deterministik dari gap yang terdeteksi bila LLM gagal.
- `_parse_paper_groups_json(raw: str) -> list` — parsing JSON klasifikasi basis paper.
- `_parse_roadmap_json(raw: str) -> list` — parsing JSON roadmap menjadi daftar fase.
- `_parse_roadmap_text(text: str) -> list` — fallback parsing roadmap dari teks biasa.

### `backend/app/api/routes/analysis.py` — endpoint analisis/rekomendasi/chat yang menghubungkan upload job, job store, retriever, coordinator, LLM, dan stream SSE.
**Endpoint:**
- `POST /api/analysis-status/{job_id}/cancel` → `cancel_analysis(job_id)` — menerima `job_id`, menandai pembatalan job lewat job store, mencatat event, dan mengembalikan job; tidak memanggil LLM.
- `POST /api/analysis-status/{job_id}/retry` → `retry_analysis(job_id)` — menerima `job_id`, mengantre ulang job gagal/cancelled lewat job store dan queue; tidak memanggil LLM.
- `POST /api/analysis-jobs/{job_id}/reanalyze` → `reanalyze_job(job_id)` — menyalin PDF retained dari job lama menjadi job baru, menulis job queued baru, lalu notify queue; tidak langsung memanggil LLM.
- `POST /api/recommend` → `recommend(request: RecommendationRequest)` — menerima query + context, menjalankan coordinator agent (LangGraph) untuk menghasilkan gap indicators, rule engine report, fact table stats, rekomendasi, reasoning trace; memakai pipeline/agent internal, bukan endpoint LLM mentah.
- `POST /api/gaps` → `detect_gaps(request: GapDetectionRequest)` — menerima topik + depth, mengambil paper via retriever, menjalankan gap analyzer, lalu merangkum indikator gap, rule engine stats, dan fact table stats.
- `POST /api/chat` → `chat(request: ChatRequest)` — menerima pesan + opsi history, menjalankan chat LLM durabel, menyimpan history conversation, dan mencoba menambah sumber dari retriever.
- `DELETE /api/chat/{conversation_id}` → `reset_chat(conversation_id)` — menghapus conversation dari job store dan membersihkan lock; tidak memanggil LLM.
- `POST /api/analyze-selection` → `analyze_selection(request: MarkedPapersRequest)` — menerima daftar paper bertanda, membangun prompt LLM, memparsing JSON seleksi, meng-ground saran ke paper input, dan mengembalikan common keywords/shared themes/suggestions.
- `POST /api/upload-and-analyze` → `upload_and_analyze(files, gap_job_id)` — menerima file PDF + opsional job gap mining, menyimpan upload per-job, membuat job queued baru, lalu notify queue untuk diproses worker pipeline lama.
- `GET /api/analysis-status/{job_id}` → `get_analysis_status(job_id, lang="en")` — mengambil status job dari job store; bila selesai dan `lang=id`, menerjemahkan hasil via LLM dan caching translation result.
- `GET /api/analysis-status/{job_id}/events` → `get_analysis_events(job_id, after_event_id=0)` — mengembalikan timeline event job dari job store; hanya membaca job/event store.
- `GET /api/analysis-status/{job_id}/artifacts` → `get_analysis_artifacts(job_id, phase=None)` — mengembalikan artefak per tahap dari job store; hanya membaca artifact store.
- `GET /api/analysis-status/{job_id}/chunks` → `get_analysis_chunks(job_id, format="jsonl")` — mengekspor chunk PDF dari vector store untuk job tertentu dalam JSONL atau Markdown; membaca job store + vector store.
- `GET /api/analysis-jobs` → `list_analysis_jobs(limit=20)` — mengambil daftar ringkas job terbaru dari job store untuk dashboard.
- `DELETE /api/analysis-jobs/{job_id}` → `delete_analysis_job(job_id)` — menghapus job dan membersihkan vector chunks + input dir; tidak memanggil LLM.
- `GET /api/kg/graph` → `get_kg_graph(job_id=None)` — mengambil snapshot graph persisten dari job selesai dan mengembalikan nodes/edges/statistik; hanya membaca job graph store.
- `GET /api/stream/{job_id}` → `stream_analysis(job_id)` — mengalirkan progress job sebagai Server-Sent Events dari job store/events.
**Fungsi:**
- `_conversation_lock(conversation_id: str) -> Lock` — mengembalikan lock per conversation agar chat durabel aman dari race.
- `_translation_lock(job_id: str) -> Lock` — mengembalikan lock per job untuk menghindari translasi ganda hasil selesai.
- `_translate_results(glm, results: dict) -> dict` — membuat salinan hasil job yang diterjemahkan ke Bahasa Indonesia via LLM pada field user-facing.
- `translate_to_indonesian(glm, text)` — menerjemahkan string atau list string ke Bahasa Indonesia via LLM; dipakai oleh hasil job lang=id.
- `cancel_analysis(job_id: str)` — handler cancel yang memanggil `request_cancel`, `record_job_event`; tidak memakai LLM.
- `retry_analysis(job_id: str)` — handler retry yang memanggil `retry_job`, `record_job_event`, dan `get_analysis_queue().notify()`.
- `reanalyze_job(job_id: str)` — handler reanalyze yang menyalin input PDF lama, membentuk job baru, memanggil `_set_analysis_job`, `record_job_event`, dan queue notify.
- `recommend(request: RecommendationRequest)` — handler sync yang memanggil `create_ephemeral_analysis_context()` lalu `coordinator.process_research_query(...)`; mengembalikan indikator gap terstruktur, rekomendasi, reasoning trace, rule engine report, dan fact table stats.
- `detect_gaps(request: GapDetectionRequest)` — handler sync yang memanggil `create_ephemeral_analysis_context()`, `retriever.retrieve`, dan `gap_analyzer.analyze_gaps(...)`; mengembalikan indikator gap plus statistik rule/fact table.
- `chat(request: ChatRequest)` — handler sync yang memanggil `get_glm_interface().chat(...)`, menyimpan histori lewat job store, dan mencoba retriever untuk sumber.
- `reset_chat(conversation_id: str)` — menghapus conversation melalui job store dan lock map; tidak memanggil LLM.
- `analyze_selection(request: MarkedPapersRequest)` — handler async yang membangun prompt analisis seleksi, memanggil `glm.generate(...)`, lalu memproses JSON melalui helper parse/grounding; ada panggilan LLM.
- `upload_and_analyze(...)` — handler upload yang memvalidasi PDF, menyimpan file per-job, menulis job queued ke job store, lalu queue notify; job dikerjakan background worker.
- `get_analysis_status(job_id: str, lang: str = "en")` — handler sync yang membaca job store, menambal hasil selesai, dan bila perlu menerjemahkan hasil via LLM dengan lock.
- `get_analysis_events(job_id: str, after_event_id: int = 0)` — handler async yang hanya membaca event store.
- `get_analysis_artifacts(job_id: str, phase: str | None = None)` — handler async yang hanya membaca artifact store.
- `get_analysis_chunks(job_id: str, format: str = "jsonl")` — handler async yang membaca vector store untuk chunks job dan men-stream ke klien.
- `list_analysis_jobs(limit: int = 20)` — handler async yang hanya membaca job store dan merangkum job.
- `delete_analysis_job(job_id: str)` — handler async yang menghapus job store, chunks vector, dan dir upload.
- `get_kg_graph(job_id: str = None)` — handler async yang membaca snapshot graph job selesai dan mengembalikan nodes/edges/statistik.
- `stream_analysis(job_id: str)` — handler async yang membaca job state dan event store berulang-ulang, lalu men-stream SSE sampai job final.
**Alur utama:**
- Request masuk ke router `analysis` dengan prefix `"/api"` dari `main.py`.
- Endpoint ringan seperti status/events/artifacts/chunks sebagian besar hanya membaca job store/vector store; endpoint rekomendasi/gap/chat memanggil LLM, retriever, coordinator, atau gap analyzer.
- `upload-and-analyze` menulis job queued + file upload ke disk, lalu worker queue memprosesnya di `process_auto_analysis`.
- `analysis-status/{job_id}` menjadi sumber status utama; bila `lang=id`, hasil selesai diterjemahkan dan disimpan sebagai cache hasil terjemahan.
- SSE `/stream/{job_id}` membaca event/job state untuk UI realtime tanpa polling berat.
- Reanalyze/retry/cancel bekerja melalui job store dan analysis queue, bukan mengeksekusi analisis di handler langsung.
**Daftar endpoint:**

| Method | Path | Handler | Tugas |
|---|---|---|---|
| POST | `/api/analysis-status/{job_id}/cancel` | `cancel_analysis(job_id)` | Batalkan job |
| POST | `/api/analysis-status/{job_id}/retry` | `retry_analysis(job_id)` | Antre ulang job gagal/cancelled |
| POST | `/api/analysis-jobs/{job_id}/reanalyze` | `reanalyze_job(job_id)` | Buat job baru dari PDF retained |
| POST | `/api/recommend` | `recommend(request)` | Coordinator-based research recommendation |
| POST | `/api/gaps` | `detect_gaps(request)` | Deteksi gap lewat retriever + gap analyzer |
| POST | `/api/chat` | `chat(request)` | Chat durabel berbasis LLM |
| DELETE | `/api/chat/{conversation_id}` | `reset_chat(conversation_id)` | Hapus conversation |
| POST | `/api/analyze-selection` | `analyze_selection(request)` | Analisis paper bertanda |
| POST | `/api/upload-and-analyze` | `upload_and_analyze(files, gap_job_id)` | Upload dan antre job lama |
| GET | `/api/analysis-status/{job_id}` | `get_analysis_status(job_id, lang)` | Ambil status/result job |
| GET | `/api/analysis-status/{job_id}/events` | `get_analysis_events(job_id, after_event_id)` | Ambil event timeline |
| GET | `/api/analysis-status/{job_id}/artifacts` | `get_analysis_artifacts(job_id, phase)` | Ambil artefak tahap |
| GET | `/api/analysis-status/{job_id}/chunks` | `get_analysis_chunks(job_id, format)` | Ekspor chunk job |
| GET | `/api/analysis-jobs` | `list_analysis_jobs(limit)` | Daftar job ringkas |
| DELETE | `/api/analysis-jobs/{job_id}` | `delete_analysis_job(job_id)` | Hapus job |
| GET | `/api/kg/graph` | `get_kg_graph(job_id)` | Ambil snapshot knowledge graph |
| GET | `/api/stream/{job_id}` | `stream_analysis(job_id)` | SSE progress job |

### `backend/app/api/routes/documents.py` — endpoint ingest/search/statistics/delete untuk dokumen yang diindeks ke vector store.
**Endpoint:**
- `POST /api/search` → `search(request: QueryRequest)` — menerima query pencarian + filters, memanggil retriever, dan mengembalikan hasil ranked dengan metadata; tidak memanggil LLM.
- `POST /api/ingest` → `ingest_document(background_tasks, file, title=None, authors=None, year=None)` — menerima upload PDF, memvalidasi/menulis file sementara, memproses PDF, menambah metadata, lalu menyimpan chunk ke vector store; tidak memakai LLM eksplisit.
- `GET /api/stats` → `get_statistics()` — mengambil statistik vector store dan jumlah dokumen/chunk; hanya membaca vector store.
- `DELETE /api/documents/{doc_id}` → `delete_document(doc_id)` — menghapus dokumen dari vector store; tidak memanggil LLM.
**Fungsi:**
- `search(request: QueryRequest)` — mencari paper relevan via retriever dan mengembalikan daftar hasil, skor, content preview, dan metadata.
- `ingest_document(background_tasks, file, title=None, authors=None, year=None)` — memvalidasi upload PDF, memproses dokumen, menormalkan metadata untuk ChromaDB, lalu menulis semua chunk ke vector store; parameter `BackgroundTasks` dideklarasikan tetapi tidak dipakai di body (sisa desain lama).
- `get_statistics()` — merangkum stats vector store, total dokumen, total chunk, dan count dokumen.
- `delete_document(doc_id: str)` — menghapus document id dari vector store dan mengembalikan status sukses/gagal.
**Alur utama:**
- Request search langsung ke retriever RAG.
- Ingest menulis file sementara, memanggil `DocumentProcessor.process_pdf`, lalu `VectorStore.add_documents`.
- Stats dan delete bekerja hanya pada vector store.
- Endpoint ini adalah lapisan API tipis di atas retrieval + storage.
**Daftar endpoint:**

| Method | Path | Handler | Tugas |
|---|---|---|---|
| POST | `/api/search` | `search(request)` | Cari dokumen lewat retriever |
| POST | `/api/ingest` | `ingest_document(...)` | Upload PDF → proses → simpan ke vector store |
| GET | `/api/stats` | `get_statistics()` | Statistik dokumen/chunk |
| DELETE | `/api/documents/{doc_id}` | `delete_document(doc_id)` | Hapus dokumen |

### `backend/app/api/routes/graph.py` — endpoint visualisasi knowledge graph berbasis facts/job snapshot atau eksperimen terakhir.
**Fungsi:**
- `_facts_from_job(job_id: str | None) -> tuple[List[Dict[str, Any]], Optional[str]]` — memuat fakta graph dari job selesai, default ke latest completed job jika `job_id` kosong.
- `_facts_from_experiment() -> tuple[List[Dict[str, Any]], Optional[str]]` — fallback membaca `all_facts` dari hasil eksperimen full-mode terbaru.
- `get_knowledge_graph(job_id: Optional[str] = Query(None, ...), min_degree: int = Query(1, ...), max_nodes: int = Query(300, ...))` — membentuk graph NetworkX dari facts, memfilter degree/node cap, menjalankan community detection, lalu mengembalikan nodes/links/clusters/stats.
**Alur utama:**
- Sumber data diprioritaskan ke snapshot job selesai.
- Jika job kosong, fallback ke hasil eksperimen terbaru.
- Facts dikonversi menjadi graph NetworkX, difilter, lalu dikelompokkan per komunitas.
**Daftar endpoint:**

| Method | Path | Handler | Tugas |
|---|---|---|---|
| GET | `/api/graph` | `get_knowledge_graph(...)` | Kembalikan network graph dari facts |

### `backend/app/api/routes/health.py` — endpoint landing page, model switching, status sumber API, statistik server, dan health check komponen.
**Endpoint:**
- `GET /` → `root()` — mengembalikan `index.html` statis bila ada atau HTML minimal; tidak memanggil LLM.
- `GET /api/sources/status` → `get_api_sources_status()` — mengecek environment key untuk sumber API eksternal; tidak memanggil LLM.
- `GET /api/models` → `list_models()` — mengambil daftar model tersedia dari interface LLM; membaca daftar model, bukan inference.
- `POST /api/models/switch` → `switch_model(req: ModelSwitchRequest)` — mengganti model aktif bila tidak ada job berjalan; memanggil interface LLM untuk switch model.
- `GET /api/system-stats` → `get_system_stats()` — mengembalikan CPU/RAM/swap/disk/GPU stats dari psutil dan nvidia-smi; tidak memanggil LLM.
- `GET /health` → `health_check()` — mengecek health GLM dan vector store lalu mengembalikan status `healthy/degraded`; memanggil health check LLM dan vector store.
**Kelas:**
- `ModelSwitchRequest` — model request body untuk pergantian model LLM.
  - `model_name` — nama model target yang akan diaktifkan.
**Fungsi:**
- `root()` — melayani landing page.
- `get_api_sources_status()` — membaca env key sumber API dan mengembalikan status boolean.
- `list_models()` — memanggil `get_glm_interface().list_available_models()`.
- `switch_model(req: ModelSwitchRequest)` — memeriksa job running, memvalidasi model, lalu memanggil `glm.switch_model(...)`.
- `_int_or(value: str, fallback: int = 0) -> int` — helper parsing angka aman untuk output nvidia-smi.
- `_collect_gpu_stats() -> list[dict]` — mengumpulkan stats GPU dan proses compute via `nvidia-smi` + psutil.
- `get_system_stats()` — merangkum CPU, memory, swap, disk, dan GPU stats; sengaja sync agar tidak memblok event loop.
- `health_check()` — memeriksa health komponen inti dan mengembalikan `HealthResponse`.
**Alur utama:**
- Root hanya menyajikan halaman HTML.
- Model listing/switching lewat `get_glm_interface`.
- System stats memakai psutil/nvidia-smi, bukan komponen AI.
- Health check memeriksa GLM + vector store.
**Daftar endpoint:**

| Method | Path | Handler | Tugas |
|---|---|---|---|
| GET | `/` | `root()` | Landing page |
| GET | `/api/sources/status` | `get_api_sources_status()` | Status API keys |
| GET | `/api/models` | `list_models()` | Daftar model LLM |
| POST | `/api/models/switch` | `switch_model(req)` | Ganti model aktif |
| GET | `/api/system-stats` | `get_system_stats()` | Statistik server/GPU |
| GET | `/health` | `health_check()` | Health komponen |

### `backend/app/api/routes/papers.py` — endpoint ide→query, fetch PDF legal, unduh+analisis, cari paper eksternal, ingest single/batch paper ke vector store.
**Endpoint:**
- `POST /api/papers/idea-to-query` → `idea_to_query(request: IdeaToQueryRequest)` — menerima ide penelitian, memakai LLM/Copilot untuk menghasilkan query keyword akademik + keywords; memanggil LLM.
- `POST /api/papers/fetch-pdf` → `fetch_pdf(paper: PaperToDownload)` — menerima metadata paper, resolve PDF open-access via pdf_url/Unpaywall, lalu streaming file PDF; jaringan eksternal.
- `POST /api/papers/download-and-analyze` → `download_and_analyze(request: DownloadAnalyzeRequest)` — menerima daftar paper, mengunduh PDF legal untuk tiap paper, menulis job queued, lalu menyalakan analysis queue; jaringan eksternal + background task.
- `POST /api/papers/search` → `search_external_papers(request: PaperSearchRequest)` — mencari paper ke beberapa API eksternal lalu mengembalikan `PaperSearchResponse`; jaringan eksternal.
- `POST /api/papers/ingest-external` → `ingest_external_paper(paper_id, source="semantic_scholar")` — mengambil detail paper dari API eksternal, membuat `Document`, lalu menambahkannya ke vector store; jaringan eksternal + vector store.
- `POST /api/papers/batch-ingest` → `batch_ingest_papers(query, max_results=20, sources=None)` — mencari paper eksternal lalu mengindeks batch hasil ke vector store; jaringan eksternal + vector store.
**Fungsi:**
- `_normalize_pdf_url(url: str | None) -> str | None` — menormalisasi URL PDF dan menolak URL non-http(s).
- `_get_following_redirects(session: aiohttp.ClientSession, url: str) -> aiohttp.ClientResponse` — melakukan GET dengan redirect manual sambil re-check SSRF guard tiap hop.
- `_download_pdf(session: aiohttp.ClientSession, url: str, destination: Path, max_mb: int) -> None` — streaming PDF ke disk dengan pengecekan magic header dan batas ukuran.
- `idea_to_query(request: IdeaToQueryRequest)` — memanggil Copilot/Llama untuk mengubah ide menjadi query keyword akademik yang bersih.
- `fetch_pdf(paper: PaperToDownload)` — resolve URL PDF, validasi keamanan URL, unduh PDF ke file sementara, lalu kembalikan `Response` PDF.
- `download_and_analyze(request: DownloadAnalyzeRequest)` — mengunduh PDF legal per paper, menyusun job queued, menulis payload, lalu queue notify untuk dianalisis worker; job background, jaringan eksternal.
- `clean_paper_metadata(paper) -> Dict[str, Any]` — membersihkan metadata paper agar kompatibel dengan ChromaDB.
- `search_external_papers(request: PaperSearchRequest)` — memanggil `get_paper_api().search_all(...)`, optional deduplicate, lalu membentuk `PaperSearchResponse`.
- `ingest_external_paper(...)` — mengambil detail paper dari source API, lalu menulis document ke vector store.
- `batch_ingest_papers(...)` — mencari paper eksternal, deduplicate, lalu mengindeks batch ke vector store; mengembalikan jumlah sukses/gagal.
**Alur utama:**
- Ide→query dan search/ingest eksternal bergantung pada LLM atau API paper.
- Fetch PDF menjaga keamanan URL dan legal OA download.
- Download-and-analyze membuat job queue agar worker memproses PDF secara background.
- Ingest paper eksternal langsung menulis ke vector store.
**Daftar endpoint:**

| Method | Path | Handler | Tugas |
|---|---|---|---|
| POST | `/api/papers/idea-to-query` | `idea_to_query(request)` | Ide → query keyword |
| POST | `/api/papers/fetch-pdf` | `fetch_pdf(paper)` | Unduh PDF OA legal |
| POST | `/api/papers/download-and-analyze` | `download_and_analyze(request)` | Unduh lalu antre analisis |
| POST | `/api/papers/search` | `search_external_papers(request)` | Cari paper eksternal |
| POST | `/api/papers/ingest-external` | `ingest_external_paper(...)` | Ambil detail paper lalu ingest |
| POST | `/api/papers/batch-ingest` | `batch_ingest_papers(...)` | Cari lalu ingest batch |

### `backend/app/api/routes/research.py` — pipeline penelitian baru yang memecah proses menjadi stage chunking, gap mining, novelty, recommendation, dengan job queue dan artefak per tahap.
**Endpoint:**
- `GET /api/research/stages` → `list_stages()` — mengembalikan deskripsi stage, substep, konstanta, dan status novelty disabled; tidak memanggil LLM.
- `GET /api/research/stages/{stage_key}/source` → `stage_source_code(stage_key)` — mengembalikan fungsi Python yang benar-benar dijalankan untuk stage tertentu; membaca definisi kode, bukan eksekusi.
- `GET /api/research/{job_id}/records/{phase}` → `stage_records(job_id, phase, request, q="", offset=0, limit=100)` — membaca JSONL record penuh dari artefak tahap, mendukung filter facet dan pencarian; hanya membaca job/artifact store.
- `GET /api/research/{job_id}/fulltext` → `journal_fulltext(job_id, source="")` — mengembalikan fulltext hasil chunking per jurnal atau daftar jurnal dalam job; hanya membaca record tahap chunking.
- `POST /api/research/start` → `start_research(files, until="", ocr_mode="auto", gap_runs=1, min_run_hits=0)` — menerima PDF, menulis job queued pipeline penelitian, lalu queue notify; job background.
- `POST /api/research/{job_id}/continue` → `continue_research(job_id, until="", novelty_limit=0, start_from="", gap_runs=0, min_run_hits=0)` — melanjutkan job selesai ke stage berikutnya dengan payload update dan queue notify; background.
- `POST /api/research/chunk-preview` → `chunk_preview(files, ocr_mode="auto")` — mengunggah PDF sementara, menjalankan `process_pdf` di threadpool, lalu mengembalikan preview chunk tanpa job/antrian/vector store/LLM.
**Fungsi:**
- `_validate_runs(gap_runs: int, min_run_hits: int) -> tuple[int, int]` — memvalidasi parameter pengulangan gap mining.
- `list_stages()` — mengembalikan metadata stage dan konstanta pipeline.
- `stage_source_code(stage_key: str)` — mengembalikan sumber fungsi untuk stage pipeline.
- `_record_path(job_id: str, collection: str) -> Path` — menurunkan path berkas record lengkap dari artefak job.
- `stage_records(job_id: str, phase: str, request: Request, q: str = "", offset: int = 0, limit: int = 100)` — membaca record JSONL, menerapkan facet dan keyword filter, lalu memotong page.
- `journal_fulltext(job_id: str, source: str = "")` — menyusun kembali fulltext jurnal dari chunk stage chunking.
- `start_research(...)` — membuat job pipeline baru, menyimpan file upload, menulis payload stage, dan mengantrekan job.
- `continue_research(...)` — melanjutkan job selesai dari stage tertentu dengan validasi stage sequence dan opsi ulang gap mining/novelty limit.
- `_preview_payload(source: str, result: PipelineResult) -> Dict[str, Any]` — membentuk payload preview satu PDF dari `PipelineResult`.
- `chunk_preview(files: List[UploadFile], ocr_mode: str = "auto")` — menjalankan parsing PDF sementara dan mengembalikan ringkasan chunk/section/token, tanpa membuat job.
**Alur utama:**
- Stage metadata dipakai UI untuk timeline/peta proses.
- Start menulis job queued ke job store lalu queue notify, dikerjakan worker pipeline research.
- Continue hanya mengubah payload job selesai dan mengantrekan ulang stage lanjutan.
- Records/fulltext membaca artefak JSONL dari stage output.
- Chunk-preview adalah jalur baca-saja untuk melihat hasil pemotongan sebelum analisis.
**Daftar endpoint:**

| Method | Path | Handler | Tugas |
|---|---|---|---|
| GET | `/api/research/stages` | `list_stages()` | Metadata stage |
| GET | `/api/research/stages/{stage_key}/source` | `stage_source_code(stage_key)` | Sumber kode stage |
| GET | `/api/research/{job_id}/records/{phase}` | `stage_records(...)` | Record penuh per tahap |
| GET | `/api/research/{job_id}/fulltext` | `journal_fulltext(...)` | Fulltext jurnal dari chunk |
| POST | `/api/research/start` | `start_research(...)` | Mulai pipeline penelitian |
| POST | `/api/research/{job_id}/continue` | `continue_research(...)` | Lanjutkan job selesai |
| POST | `/api/research/chunk-preview` | `chunk_preview(...)` | Preview chunk PDF |

### `backend/app/api/routes/skills.py` — endpoint untuk daftar skill AI-Research-SKILLs, tanya skill, dan rekomendasi penelitian lengkap dengan routing skill otomatis.
**Endpoint:**
- `GET /api/skills` → `list_skills()` — membaca direktori `.agents/skills` dan mengembalikan daftar skill terpasang; tidak memanggil LLM.
- `POST /api/skills/ask` → `ask_with_skill(request: SkillAskRequest)` — menerima skill + pertanyaan, memuat `SKILL.md`, lalu memakai Copilot/Ollama untuk menjawab berdasarkan skill; memanggil LLM.
- `POST /api/skills/recommend` → `recommend_research(request: RecommendRequest)` — menerima ide riset, memilih skill relevan via router LLM/heuristik, lalu menghasilkan rekomendasi penelitian lengkap; memanggil LLM.
**Kelas:**
- `SkillAskRequest` — model request untuk tanya satu skill.
  - `skill` — nama folder skill yang akan dipakai.
  - `question` — pertanyaan riset yang akan dijawab dengan panduan skill.
- `RecommendRequest` — model request untuk ide penelitian.
  - `idea` — ide/topik penelitian yang akan dirutekan ke skill relevan.
**Fungsi:**
- `_parse_frontmatter(text: str) -> dict` — mengekstrak `name`/`description` dari YAML frontmatter `SKILL.md`.
- `_safe_skill_path(name: str) -> Path` — membangun path skill yang tervalidasi dan menolak traversal path.
- `list_skills()` — men-scan folder skill dan mengembalikan metadata skill.
- `_llm_generate(prompt: str, system: str, json_mode: bool = False, timeout: float = 120.0, max_tokens: int = 1500) -> tuple[str, str]` — memanggil Copilot terlebih dulu, fallback ke Ollama, mengembalikan teks + label engine.
- `_strip_json_fences(raw: str) -> str` — membuang markdown fence dari JSON model output.
- `ask_with_skill(request: SkillAskRequest)` — memuat isi skill, membangun system prompt, memanggil `_llm_generate`, dan mengembalikan jawaban beserta engine.
- `_catalog() -> list[dict]` — mengambil daftar skill dari `list_skills()`.
- `_route_skills(idea: str, catalog: list[dict]) -> tuple[list[str], str, str]` — memilih 2-3 skill paling relevan via LLM router atau heuristik keyword fallback.
- `recommend_research(request: RecommendRequest)` — memuat skill terpilih, membangun system prompt rekomendasi lengkap, memanggil `_llm_generate`, mem-parsing JSON, dan mengembalikan hasil terstruktur.
**Alur utama:**
- Daftar skill dibaca dari `.agents/skills`.
- `ask` memakai satu skill sebagai system prompt panduan.
- `recommend` melakukan routing skill lalu menggabungkan dokumentasi skill menjadi konteks LLM.
- Copilot adalah prioritas, Ollama lokal menjadi fallback.
**Daftar endpoint:**

| Method | Path | Handler | Tugas |
|---|---|---|---|
| GET | `/api/skills` | `list_skills()` | Daftar skill terpasang |
| POST | `/api/skills/ask` | `ask_with_skill(request)` | Tanya satu skill |
| POST | `/api/skills/recommend` | `recommend_research(request)` | Rekomendasi penelitian lengkap |

### `backend/app/api/routes/analysis.py` — catatan tambahan tentang definisi yang berulang di file ini: handler yang didokumentasikan di atas adalah semua route aktif; helper internals di bawahnya terutama untuk locking, translasi, dan streaming.
**Fungsi tambahan yang sudah tercakup di atas namun penting untuk pemahaman alur:**
- `get_analysis_status(...)` — bila job selesai dan belum punya `results_id`, ia mengisi hasil terjemahan lalu menyimpannya.
- `stream_analysis(...)` — menghasilkan event `progress/phase/complete/error` berdasarkan revision job dan event store.
- `delete_analysis_job(...)` — membersihkan chunk vector dan folder upload setelah job dihapus.
**Alur utama (ringkas):**
- Job analisis dipusatkan pada job store; status dan artefak dibaca dari sana.
- Endpoint yang memanggil LLM mayoritas melakukan work synchronous yang berat, sehingga banyak handler dibuat `def` untuk dieksekusi di threadpool FastAPI.
- Queue dan worker dipakai untuk job yang panjang; request HTTP hanya menulis job/payload dan memantau hasil.

### `backend/app/api/auto_analysis.py` — tahapan otomatis yang dijalankan, urutannya: ingest PDF → ekstrak topik → analisis basis/persamaan/kelemahan/workflow paralel → gabung author gaps opsional → enrich referensi → bangun profil → coordinator neuro-symbolic atau fallback LLM → ringkasan → gap detection → proposal/rekomendasi → roadmap → intro proposal → simpan hasil final.
**Kelas/Fungsi:**
- `_set_analysis_job(...)` — update job store untuk job analisis lama.
- `_get_analysis_job(...)` — baca job store untuk job analisis lama.
- `JobCancelled` — sinyal pembatalan cooperative.
- `_load_author_gaps(...)` — ambil gap statements dari job gap mining lain untuk dijadikan corroborating evidence.
- `_ensure_job_active(...)` — cek cancel request di antara tahapan.
- `_save_stage_artifact(...)` — simpan prompt/response/result per tahap sebagai artefak.
- `_traced_generate(...)` — panggil LLM dan simpan trace prompt/response + skill yang dipakai.
- `_add_uploaded_paper_similarity(...)` — hitung similarity antar paper yang diunggah dalam job ini.
- `process_auto_analysis(...)` — worker utama pipeline lama yang menjalankan seluruh delapan langkah dan menyimpan hasil, event, serta graph snapshot.
**Alur utama:**
- Job dipanggil worker queue, bukan event loop HTTP.
- Ingest menyimpan chunk ke vector store scoped per job.
- Analisis paper tahap awal dijalankan paralel karena independen.
- Coordinator dijalankan jika tersedia, jika gagal ada fallback LLM.
- Semua hasil akhir disimpan ke job store melalui `complete_job`.
- Cancel/failed menulis status final dan membersihkan konteks job.
**Daftar langkah otomatis:**
1. Ingest PDF ke vector store scoped job.
2. Ekstrak topik dari konten gabungan.
3. Jalankan analisis paralel: klasifikasi basis, similarity, kelemahan, workflow stages.
4. Jalankan coordinator neuro-symbolic untuk gap indicators, reasoning trace, rule engine report, fact table stats.
5. Generate ringkasan penelitian via LLM.
6. Deteksi gap bila coordinator tidak memberi indikator lengkap; validasi dengan rule engine.
7. Susun usulan penelitian berbasis gap; fallback deterministik bila LLM gagal.
8. Buat roadmap dan intro proposal, lalu simpan hasil akhir.
**Catatan penting:**
- Berkas ini memuat dependency ke `analysis_helpers`, `skill_guidance`, `research_pipeline`, `reference_enrichment`, `rank_proposals`, dan job store.
- Sebagian helper mengandalkan prompt LLM yang disalurkan lewat `_traced_generate`.
- Hasil final mencakup topics, summary, gaps, recommendations, roadmap, paper profiles, reasoning trace, eval metrics, dan graph snapshot.
**Alur utama:** job queue → `process_auto_analysis(job_id)` → job store/vector store/fact table/rule engine/coordinator/LLM → `complete_job(...)` → hasil tampil di `/api/analysis-status/{job_id}`.

## Tambahan — fungsi bersarang (nested) di backend/app/api/

### `backend/app/api/auto_analysis.py`
- `_compute_groups()` — nested di dalam `process_auto_analysis`; mengirim prompt **LLM** untuk mengklasifikasikan paper berdasarkan basis/metode lalu mem-parsing hasil JSON menjadi grup paper.
- `_compute_similarity()` — nested di dalam `process_auto_analysis`; mengirim prompt **LLM** untuk mengekstrak common keywords/shared themes/summary antar paper lalu mem-parsing JSON hasilnya.
- `_compute_weaknesses()` — nested di dalam `process_auto_analysis`; menyiapkan analisis kelemahan per paper, menjalankan batch prompt **LLM**, lalu memverifikasi hasil terhadap teks paper.
- `_weak_prompt(p)` — nested di dalam `_compute_weaknesses`; membangun prompt ketat untuk satu paper agar LLM mengekstrak kekurangan tersurat/tersirat berbasis bukti.
- `_compute_workflows()` — nested di dalam `process_auto_analysis`; membangun prompt **LLM** untuk mengekstrak tahapan metode/workflow per paper lalu memverifikasi hasilnya.

### `backend/app/api/routes/analysis.py`
- `_lines()` — nested di dalam `get_analysis_chunks`; generator streaming NDJSON yang menulis baris meta lalu satu record per chunk dari vector store.
- `_md()` — nested di dalam `get_analysis_chunks`; generator streaming Markdown yang mengelompokkan chunk per jurnal dan menuliskan full text chunk.
- `event_generator()` — nested di dalam `stream_analysis`; loop SSE yang memantau revision job, mengirim event progress/complete/error, dan men-stream event phase dari job store.

### `backend/app/api/routes/analysis_helpers.py`
- `_normalise(title: str) -> str` — nested di dalam `_ground_selection_suggestions`; menormalkan judul untuk pencocokan case/whitespace-insensitive.
- `_match_title(candidate: str) -> str | None` — nested di dalam `_ground_selection_suggestions`; mencocokkan kandidat judul sumber ke judul paper input yang dikenal.
- `_clean(items)` — nested di dalam `_parse_weaknesses_json`; menormalkan daftar kelemahan menjadi dict `{poin, dasar, kutipan}` dan memotong entri degenerat.
- `_ground_score(text: str) -> float` — nested di dalam `_verify_paper_weaknesses`; menghitung skor grounding kelemahan tersirat lewat vector store atau fallback overlap kata konten.


<a id="bagian-05"></a>
# Bagian 05 — services, utils, scripts

## backend/app/services/

### `backend/app/services/__init__.py` — re-export layanan inti untuk queue, LLM, pengayaan referensi, dan panduan skill.
**Fungsi/ekspor:**
- `AnalysisJobQueue`, `get_analysis_queue` — antrean job lokal berbasis SQLite/job_store untuk worker thread.
- `GLMInterface`, `LLMInterface`, `ModelConfig`, `ChatMessage`, `PromptTemplate` — antarmuka LLM Ollama/Copilot.
- `enrichment_enabled`, `enrich_paper_references`, `referenced_work_entries`, `OpenAlexAPI` (via impor internal di modul lain) — pengayaan referensi.
- `skills_for_phase`, `wrap_prompt` — sisipkan cuplikan skill metodologis ke prompt.
- `__all__` tidak didefinisikan; file ini berfungsi sebagai agregator impor.

### `backend/app/services/analysis_queue.py` — supervisor antrean job analisis lokal yang claim job dari job_store dan mengeksekusi worker thread.
**Kelas:**
- `AnalysisJobQueue` — claim, jalankan, retry, dan reschedule job yang persisten berdasarkan `pipeline`.
  - `__init__(max_workers, poll_interval)` — set worker thread, event wake/stop, handler default, dan registry handler per pipeline.
  - `running` — status thread supervisor masih hidup atau tidak.
  - `register(pipeline, handler)` — daftarkan handler spesifik untuk satu pipeline.
  - `resolve_handler(job)` — pilih handler berdasarkan field `job["pipeline"]`, fallback ke handler default.
  - `start(handler)` — load job tertunda, buat `ThreadPoolExecutor`, start thread supervisor, dan bangunkan scheduler.
  - `stop(wait=True)` — hentikan claim job baru, join supervisor, shutdown executor, reset state.
  - `notify()` — bangunkan supervisor segera setelah ada job baru/retry.
  - `_run()` — loop supervisor: collect finished, claim job tersedia, tunggu event/poll interval.
  - `_claim_available_jobs()` — ambil job satu per satu sampai kapasitas worker penuh atau tidak ada job.
  - `_collect_finished()` — bersihkan future yang selesai dan log exception tak terduga.
  - `_execute(job_id)` — ambil job, pilih handler, catat start/finish, tandai failed bila handler hilang/gagal, dan schedule retry exponential backoff.
**Fungsi:**
- `get_analysis_queue() -> AnalysisJobQueue` — singleton queue process-local sesuai config `queue.max_workers`.

### `backend/app/services/copilot_client.py` — klien GitHub Copilot SDK yang dijalankan sebagai subproses/loop background, dengan fallback ke LLM lokal oleh pemanggil.
**Konstanta/fungsi:**
- `DEFAULT_MODEL` — model Copilot default.
- `DEFAULT_MAX_CONCURRENCY` — batas request serentak Copilot.
- `JSON_INSTRUCTION` — instruksi JSON-only untuk `json_mode`.
- `NO_TOOLS` — daftar tool kosong untuk menonaktifkan tool use.
- `_REPO_ROOT` — root repo untuk config directory default.
- `_default_model() -> str` — baca `COPILOT_MODEL` atau default.
- `config_dir() -> Path` — lokasi config SDK Copilot.
- `_max_concurrency() -> int` — baca `COPILOT_MAX_CONCURRENCY` dengan fallback aman.
- `is_configured() -> bool` — true bila SDK tersedia dan Copilot tidak dimatikan env.
- `_deny(_request, _invocation) -> dict` — permission hook yang selalu menolak tool use.
**Kelas:**
- `_Runtime` — lifecycle manager satu CLI Copilot per proses.
  - `__init__()` — inisialisasi loop/thread/client/slots.
  - `_ensure_started()` — start event loop thread, buat client SDK, login/config, start client async.
  - `_submit(coro) -> Future` — lempar coroutine ke loop background.
  - `stop(timeout=10.0)` — stop client/loop/thread secara bersih.
  - `auth_status() -> dict` — ambil status autentikasi/model dari SDK.
  - `generate(prompt, system, model, timeout) -> Optional[str]` — kirim prompt via session SDK dengan semaphore concurrency.
  - `_generate_async(client, prompt, system, model, timeout) -> Optional[str]` — buat session, kirim prompt, ambil content string, destroy session.
- `stop() -> None` — hentikan runtime global.
- `status(timeout=30.0) -> Optional[dict]` — status autentikasi + metadata runtime Copilot.
- `generate(prompt, system="", json_mode=False, model="", tier="", timeout=90.0, temperature=None) -> Optional[Tuple[str, str]]` — satu giliran Copilot; jika gagal/kosong kembali `None` agar pemanggil fallback ke Ollama. **Memanggil LLM eksternal**.
- **Fallback:** jika Copilot mati/tidak login/kosong, pemanggil harus fallback ke LLM lokal; modul ini sendiri tidak memanggil Ollama.

### `backend/app/services/llm_service.py` — antarmuka LLM generik untuk Ollama, dengan jalur Copilot sebagai engine opsional dan fallback ke Ollama.
**Kelas/dataclass:**
- `ModelConfig` — konfigurasi model/endpoint/runtime.
  - Field penting: `model_name`, `base_url`, `temperature`, `top_p`, `max_tokens`, `timeout`, `num_ctx`, `keep_alive`, `max_parallel`, `engine`.
- `ChatMessage` — satu pesan chat.
  - Field: `role`, `content`.
- `PromptTemplate` — template prompt statis untuk analisis, deteksi gap, rekomendasi, dan ringkasan.
  - `format(template_name, **kwargs) -> str` — render template by name.
- `GLMInterface` — wrapper utama yang memilih engine Copilot atau Ollama, mengatur concurrency, retry transient, streaming, chat history, embedding, dan helper prompt.
  - `__init__(config=None)` — buat client Ollama, set concurrency, pilih engine (`copilot`/`ollama`) berdasarkan config/env dan ketersediaan Copilot.
  - `_copilot_model() -> str` — model Copilot aktif dari env/default.
  - `_copilot_strict() -> bool` — true bila Copilot wajib; jika unavailable tidak boleh silent fallback.
  - `active_model_name` — identifier model yang benar-benar menjawab.
  - `configure_concurrency(max_parallel) -> None` — set semaphore proses-wide untuk request Ollama.
  - `_acquire_request_slot() -> BoundedSemaphore` — ambil slot concurrency.
  - `_is_transient_error(error) -> bool` — deteksi timeout/koneksi/5xx yang layak diretry.
  - `_log_retry(operation_name, error, attempt, delay)` — log retry transient.
  - `_call_with_retries(operation_name, operation) -> Any` — jalankan operasi Ollama dengan retry bounded.
  - `switch_model(model_name)` — ganti model Ollama runtime; berbahaya bila job sedang berjalan.
  - `list_available_models() -> List[Dict[str, Any]]` — list model dari Ollama.
  - `health_check() -> Dict[str, Any]` — cek server/model tersedia.
  - `generate(prompt, system_prompt=None, temperature=None, max_tokens=None, stream=False, format=None) -> Union[str, Generator[str, None, None]]` — bangun messages/options lalu panggil streaming/non-streaming. **Memanggil LLM lokal**; bila engine Copilot, lewat `copilot_client`.
  - `generate_batch(prompts, system_prompt=None, temperature=None, max_tokens=None, format=None, max_workers=None) -> List[str]` — paralelkan banyak prompt dengan ThreadPoolExecutor.
  - `_copilot_complete(messages, format=None) -> Optional[str]` — jalur Copilot dengan retry dan strict fallback policy. **Memanggil Copilot SDK**; fallback bisa ke Ollama via caller.
  - `_generate_complete(messages, options, format=None) -> str` — panggilan chat non-streaming ke Ollama, atau Copilot dulu jika engine Copilot.
  - `_generate_stream(messages, options) -> Generator[str, None, None]` — streaming token/chunk dari Ollama; Copilot dieksekusi non-streaming sekali.
  - `chat(message, role="user", use_history=True, max_history=10, history=None) -> str` — susun history caller-owned lalu generate.
  - `clear_history()` — no-op kompatibilitas; history tidak disimpan global.
  - `analyze_research(content) -> str` — prompt `RESEARCH_ANALYSIS`, temperatur rendah; **LLM lokal/engine aktif**.
  - `detect_gaps(context, papers) -> str` — prompt `GAP_DETECTION`; **LLM lokal/engine aktif**.
  - `recommend_papers(query, papers, top_k=5) -> str` — prompt `RECOMMENDATION`; **LLM lokal/engine aktif**.
  - `summarize_paper(title, content) -> str` — prompt `SUMMARIZATION`; **LLM lokal/engine aktif**.
  - `embed_text(text) -> List[float]` — embeddings via Ollama API; **jaringan ke Ollama lokal**.
  - `__repr__() -> str` — string representasi engine/model/base_url.
- `LLMInterface = GLMInterface` — alias publik.
- `__main__` block — contoh health check/generate/chat.

### `backend/app/services/reference_enrichment.py` — pengayaan referensi paper memakai OpenAlex `referenced_works` secara opsional dan hemat kuota.
**Konstanta/fungsi:**
- `ENV_FLAG = "BIBLIO_OPENALEX_ENRICH"` — flag env untuk mengaktifkan pengayaan.
- `enrichment_enabled() -> bool` — baca env flag.
- `referenced_work_entries(work) -> List[Dict[str, Any]]` — ubah daftar `referenced_works` OpenAlex menjadi entry referensi sintetis.
- `enrich_paper_references(paper_contents, api=None, min_refs=MIN_REFS_PER_PAPER, enabled=None) -> Dict[str, int]` — untuk paper ber-DOI yang referensinya pendek, panggil OpenAlex `get_work_by_doi`, gabungkan entry baru tanpa duplikasi. **Memanggil jaringan OpenAlex** bila aktif; jika gagal/kuota habis dibiarkan apa adanya.

### `backend/app/services/skill_guidance.py` — sisipkan cuplikan AI-Research-SKILLs ke prompt berdasarkan fase pipeline.
**Konstanta/fungsi:**
- `SKILLS_DIR` — lokasi `.agents/skills`.
- `PHASE_SKILLS` — mapping fase pipeline/endpoint ke skill id.
- `_EXCERPT_SINGLE`, `_EXCERPT_MULTI` — budget karakter cuplikan skill.
- `_FRONTMATTER_RE` — regex buang frontmatter YAML.
- `_excerpt(skill_id, budget) -> str` — baca `SKILL.md`, buang frontmatter, potong ke budget; cache `lru_cache`.
- `skills_for_phase(phase) -> List[str]` — ambil skill ids untuk fase.
- `wrap_prompt(phase, prompt) -> Tuple[str, List[str]]` — prepend header + cuplikan skill ke prompt dan kembalikan prompt baru plus skill yang dipakai. **Rule-based**, tidak memanggil LLM.

### `backend/app/services/paper_apis/__init__.py` — re-export semua client API paper agar impor paket tetap stabil.
**Ekspor:**
- `PaperMetadata`, `_strip_markup`
- `ArXivAPI`, `SemanticScholarAPI`, `CrossRefAPI`, `PubMedAPI`, `CoreAPI`, `EuropePMCAPI`, `ScienceDirectAPI`, `ScopusAPI`, `UnpaywallAPI`, `AggregatedPaperAPI`
- Paket ini tidak mendefinisikan logika baru; hanya memperluas namespace publik.

### `backend/app/services/paper_apis/base.py` — primitif bersama untuk metadata paper dan pembersihan markup.
**Fungsi/dataclass:**
- `_strip_markup(text) -> str` — hapus tag JATS/HTML dan rapikan whitespace; **rule-based**.
- `PaperMetadata` — struktur metadata standar.
  - Field penting: `paper_id`, `title`, `authors`, `abstract`, `year`, `journal`, `doi`, `url`, `pdf_url`, `citation_count`, `keywords`, `source_api`, `raw_data`.
  - `to_dict() -> Dict[str, Any]` — serialisasi ke dict; menyatukan `source_api` ke field `source`.

### `backend/app/services/paper_apis/http_cache.py` — cache JSON sinkron berbasis disk dengan rate-limit, cooldown host, dan backoff retry.
**Konstanta/fungsi:**
- `_LAST_REQUEST_AT` — timestamp request terakhir per host.
- `_HOST_COOLDOWN` — cooldown host setelah 429 quota-style.
- `_LONG_RETRY_AFTER_SECONDS = 60` — ambang 429 yang dianggap habis kuota harian.
- `host_cooldown(host_or_url) -> Optional[Dict]` — status cooldown host.
- `clear_cooldowns() -> None` — kosongkan cooldown map.
- `_retry_after_seconds(response) -> Optional[float]` — parse header `Retry-After`.
- `_default_cache_dir() -> Path` — cache lokal `data/cache/api`.
- `_resolve_cache_dir(cache_dir=None) -> Path` — tentukan dan buat direktori cache.
- `cache_path(url, params=None, cache_dir=None) -> Path` — path file cache hash dari URL+query.
- `clear_cache(cache_dir=None) -> int` — hapus file cache `.json`.
- `_rate_limit(host, min_interval) -> None` — sleep agar request ke host tidak terlalu rapat.
- `get_json(url, params=None, headers=None, cache_dir=None, ttl_seconds=2592000, min_interval=1.0, max_retries=4, timeout=30.0) -> Optional[dict]` — fetch JSON via `requests`, cek cache disk, apply rate-limit, retry 429/5xx, simpan cache. **Memanggil jaringan eksternal**; untuk host 429 panjang, langsung return `None` dan tandai cooldown.
- `__main__` block — test OpenAlex singkat.

### `backend/app/services/paper_apis/aggregator.py` — agregator pencarian multi-sumber yang menjalankan API paper paralel lalu deduplicate dan reorder.
**Kelas:**
- `AggregatedPaperAPI`
  - `__init__(semantic_scholar_key=None, pubmed_key=None, crossref_email=None, pubmed_email=None, core_key=None, elsevier_key=None, elsevier_insttoken=None)` — bangun semua client sumber.
  - `search_all(query, max_results_per_source=10, sources=None, year_from=None, year_to=None) -> Dict[str, List[PaperMetadata]]` — jalankan search paralel ke sumber terpilih via `asyncio.gather`; **memanggil jaringan** ke arXiv, Semantic Scholar, Crossref, PubMed, CORE, Europe PMC, ScienceDirect, Scopus.
  - `deduplicate_papers(all_papers, query=None) -> List[PaperMetadata]` — dedup berdasarkan DOI dan title normalized; bila `query` ada, urutkan by relevance score.
  - `_relevance_score(paper, query) -> float` — skor term-match title/abstract + bonus sitasi kecil.

### `backend/app/services/paper_apis/arxiv.py` — client arXiv search metadata.
**Kelas:**
- `ArXivAPI`
  - `search(query, max_results=10, start=0) -> List[PaperMetadata]` — query API arXiv Atom; **memanggil jaringan arXiv**.
  - `_parse_arxiv_response(xml_content) -> List[PaperMetadata]` — parse XML feed ke metadata.

### `backend/app/services/paper_apis/crossref.py` — client Crossref untuk search dan lookup DOI.
**Kelas:**
- `CrossRefAPI`
  - `__init__(email=None)` — set polite pool User-Agent bila ada email.
  - `search(query, max_results=10, filter_params=None) -> List[PaperMetadata]` — search REST Crossref; **memanggil jaringan Crossref**.
  - `_parse_crossref_response(data) -> List[PaperMetadata]` — parse item hasil search.
  - `get_by_doi(doi) -> Optional[PaperMetadata]` — fetch metadata DOI tunggal via `http_cache.get_json`; **memanggil jaringan Crossref + cache disk**.

### `backend/app/services/paper_apis/core.py` — client CORE yang mendukung search, filter tahun, retry, dan detail fetch.
**Kelas:**
- `CoreAPI`
  - `__init__(api_key=None)` — set base URL dan header auth placeholder.
  - `search(query, max_results=10, year_from=None, year_to=None) -> List[PaperMetadata]` — search CORE dengan retry/backoff, filter tahun, parse author/title/abstract/url; **memanggil jaringan CORE**.
  - `get_paper_details(paper_id) -> Optional[PaperMetadata]` — fetch detail satu paper by ID; **memanggil jaringan CORE**.

### `backend/app/services/paper_apis/europe_pmc.py` — client Europe PMC search metadata.
**Kelas:**
- `EuropePMCAPI`
  - `__init__(email=None)` — set header User-Agent.
  - `search(query, max_results=10, year_from=None, year_to=None) -> List[PaperMetadata]` — search Europe PMC, opsional filter tahun; **memanggil jaringan Europe PMC**.
  - `_strip_html(text) -> str` — buang tag HTML/JATS sederhana.
  - `_parse_europepmc_response(data) -> List[PaperMetadata]` — parse result list ke metadata.

### `backend/app/services/paper_apis/pubmed.py` — client PubMed/NCBI search + summary fetch.
**Kelas:**
- `PubMedAPI`
  - `__init__(api_key=None, email=None)` — set API key/email NCBI.
  - `search(query, max_results=10, sort="relevance") -> List[PaperMetadata]` — lakukan ESearch lalu ESummary; **memanggil jaringan PubMed/NCBI**.
  - `_fetch_paper_details(id_list, session) -> List[PaperMetadata]` — fetch summary detail untuk daftar PMID.
  - `_parse_pubmed_response(data) -> List[PaperMetadata]` — parse metadata PubMed.

### `backend/app/services/paper_apis/semantic_scholar.py` — client Semantic Scholar search dan detail paper.
**Kelas:**
- `SemanticScholarAPI`
  - `__init__(api_key=None)` — set header `x-api-key` bila ada.
  - `search(query, max_results=10, fields=None) -> List[PaperMetadata]` — search paper; **memanggil jaringan Semantic Scholar**.
  - `get_paper_details(paper_id) -> Optional[PaperMetadata]` — fetch detail satu paper; **memanggil jaringan Semantic Scholar**.
  - `_parse_semantic_scholar_response(data) -> List[PaperMetadata]` — parse list result.
  - `_parse_single_paper(item) -> PaperMetadata` — parse satu record, termasuk DOI dan PDF OA bila ada.

### `backend/app/services/paper_apis/sciencedirect.py` — client Elsevier ScienceDirect search API.
**Kelas:**
- `ScienceDirectAPI`
  - `__init__(api_key=None, insttoken=None)` — ambil key/token dari env atau argumen.
  - `_headers() -> Dict[str, str]` — susun header auth.
  - `search(query, max_results=10, year_from=None, year_to=None) -> List[PaperMetadata]` — search ScienceDirect bila API key tersedia; **memanggil jaringan Elsevier ScienceDirect**.
  - `_parse_sciencedirect_response(data) -> List[PaperMetadata]` — parse entry result, authors, dates, DOI, link.

### `backend/app/services/paper_apis/scopus.py` — client Elsevier Scopus search API.
**Kelas:**
- `ScopusAPI`
  - `__init__(api_key=None, insttoken=None)` — ambil key/token dari env atau argumen.
  - `_headers() -> Dict[str, str]` — susun header auth.
  - `search(query, max_results=10, year_from=None, year_to=None) -> List[PaperMetadata]` — search Scopus dengan fielded syntax `TITLE-ABS-KEY`; **memanggil jaringan Elsevier Scopus**.
  - `_parse_scopus_response(data) -> List[PaperMetadata]` — parse metadata hasil search.

### `backend/app/services/paper_apis/openalex.py` — client OpenAlex synchronous dengan cache disk, cooldown 429, dan parsing abstract inverted index.
**Kelas:**
- `OpenAlexAPI`
  - `__init__(email=None, cache_dir=None, min_interval=1.0, max_retries=4)` — set polite pool email, cache, dan batas rate-limit/retry.
  - `search_recent(keywords, from_date="2024-01-01", max_results=5) -> Optional[List[PaperMetadata]]` — search karya terbaru via `http_cache.get_json`; `None` berarti tak bisa query (network/quota/cooldown), `[]` berarti valid tapi kosong. **Memanggil jaringan OpenAlex + cache disk**.
  - `get_work_by_doi(doi) -> Optional[Dict]` — fetch `works/https://doi.org/<doi>` untuk pengayaan referensi; **memanggil jaringan OpenAlex + cache disk**.
  - `_parse_work(work) -> PaperMetadata` — convert work JSON ke metadata, termasuk reconstruct abstract.
  - `_reconstruct_abstract(inverted_index) -> str` — susun ulang abstract dari inverted index.
- `__main__` block — test search singkat.

### `backend/app/services/paper_apis/unpaywall.py` — resolver legal OA PDF untuk DOI.
**Kelas:**
- `UnpaywallAPI`
  - `__init__(email=None)` — set email kontak dari env/default.
  - `lookup(doi) -> Optional[Dict[str, Any]]` — ambil record raw Unpaywall; **memanggil jaringan Unpaywall**.
  - `resolve_pdf(doi) -> Optional[str]` — return URL PDF OA terbaik dari record.
  - `extract_pdf_url(record) -> Optional[str]` — pilih URL PDF dari `best_oa_location`/`oa_locations`.
- **Rule-based** untuk pemilihan URL; jaringan hanya di `lookup`.

### `backend/app/services/paper_apis/grobid.py` — wrapper sinkron untuk GROBID service eksternal yang mengekstrak metadata dan struktur IMRaD dari PDF.
**Fungsi:**
- `_grobid_url() -> str` — baca `GROBID_URL` env.
- `is_configured() -> bool` — true jika URL GROBID tersedia.
**Kelas:**
- `GrobidClient`
  - `__init__(base_url=None, timeout=120.0)` — set base URL dan timeout.
  - `is_available() -> bool` — ping `/api/isalive` untuk cek service.
  - `process_fulltext(pdf_path) -> Optional[Dict[str, Any]]` — upload PDF ke `processFulltextDocument`, parse TEI jadi metadata+sections; **memanggil jaringan ke service GROBID**.
  - `_parse_tei(xml_bytes) -> Dict[str, Any]` — ekstrak title/doi/year/authors/abstract/sections dari TEI.
  - `_xtext(node, xpath) -> Optional[str]` — helper ambil teks XPath.
  - `_extract_year(root) -> Optional[int]` — cari tahun publikasi dari TEI.
  - `_extract_authors(root) -> List[str]` — ambil dan dedup nama author.
  - `_extract_abstract(root) -> Optional[str]` — ekstrak abstract dari `profileDesc`.
  - `_extract_sections(root) -> List[Tuple[str, str]]` — ambil pasangan `(head, body)` dari `<body><div>`.
- `__main__` block — cek configured/available.

### `backend/app/services/research_pipeline.py` — orkestrator pipeline riset terpantau: chunking → gap_mining → novelty → recommendation, dengan event/artefak/job-store dan narasi LLM opsional.
**Konstanta penting:**
- `PIPELINE_NAME = "research"` — nama pipeline di job payload/queue.
- `DEFAULT_LLM_TRACE_LIMIT = 15` — maksimum trace prompt/response LLM yang disimpan.
- `DEFAULT_EXTRACT_WORKERS = 4` — worker paralel untuk ekstraksi gap.
- `SAMPLE_ROWS = 8` — jumlah contoh yang ditampilkan di ringkasan.
- `MAX_GAP_RUNS = 5` — batas atas pengulangan gap mining untuk konsensus k/n.
- `NARRATION_TOP = 8` — jumlah butir teratas yang dinarasikan LLM.
- `RESEARCH_STAGES` — urutan dan label UI: `chunking`, `gap_mining`, `novelty`, `recommendation`.
- `SUBSTEPS` — peta sub-langkah per tahap dan metrik in/out/drop yang wajib cocok dengan `StageOutcome.metrics`.
- `PIPELINE_CONSTANTS` — parameter nyata yang dipakai UI.
- `_STAGE_INPUTS` — artefak minimum yang harus ada bila melanjutkan dari tahap tertentu.
- `NARRATION_FIELDS = ("judul", "latar_belakang", "alasan", "metode")`.
- `_NARRATION_SYSTEM` — system prompt narasi Bahasa Indonesia.
- `_NOVELTY_WORDS` — label status novelty untuk narasi.
**Kelas/dataclass:**
- `StageOutcome` — hasil satu tahap.
  - Field penting: `params`, `metrics`, `samples`, `outputs`, `notes`, `substep_samples`.
- `ResearchCancelled(Exception)` — sinyal pembatalan user di antara tahap/kandidat.
- `_StageRecorder` — context manager untuk catat `phase.started/completed/failed/cancelled` dan artefak hasil tahap.
  - `__enter__`, `__exit__`, `_elapsed_ms()`, `finish(outcome)` — catat durasi dan simpan artifact result.
- `_substep` — context manager untuk event `substep.started/completed`.
  - `__enter__`, `done(keluar=None, **extra)`, `__exit__` — catat metrik masuk/keluar/dibuang dan error bila ada.
**Fungsi utilitas:**
- `_sub(...) -> Dict[str, Any]` — builder dict definisi substep untuk UI.
- `_split_duplicates(gaps) -> tuple[List[Dict], List[Dict]]` — pisahkan gap unik vs duplikat berdasarkan `(source, gap_statement.lower())`.
- `_dedup_gaps(gaps) -> List[Dict]` — ambil bagian unik saja.
- `_gap_digest(gap) -> str` — SHA1 kunci gap.
- `default_min_run_hits(runs) -> int` — ambang stabil default `ceil(2n/3)` dengan minimum 1.
- `_merge_runs(gaps, runs, min_run_hits) -> tuple[unique, duplicates, merged, consensus]` — gabungkan gap lintas run, hitung `run_hits/run_total/run_ids/stable`, dan statistik konsensus Jaccard antar-run. **Ini inti k/n consensus gap mining**: gap stabil jika `run_hits >= min_run_hits`; kemunculan ulang di run berbeda dihitung sebagai bukti stabilitas, kemunculan dua kali di run sama dihitung duplikat.
- `merge_gap_runs(gap_runs, min_run_hits=0) -> tuple[List[Dict], Dict[str, Any]]` — wrapper untuk merge beberapa file/run terpisah; `min_run_hits<=0` pakai default `ceil(2n/3)`.
- `_median(values) -> int` — median integer sederhana.
- `_ensure_active(job_id)` — lempar `ResearchCancelled` bila cancel diminta.
- `_progress(job_id, pct, message)` — update progress/message job store.
- `_novelty_summary(items) -> str` — ringkasan status novelty sekelompok proposal.
- `_narration_seeds(ranked, themes, top=NARRATION_TOP) -> List[Dict[str, Any]]` — pilih butir narasi: tema lintas-jurnal dulu, lalu proposal peringkat yang belum terwakili.
- `_narration_prompt(seeds) -> str` — susun prompt JSON-only untuk narasi judul/latar/alasan/metode.
- `_parse_narration(raw, n) -> List[Optional[Dict[str, str]]]` — parse jawaban LLM jadi slot `n` item; toleran code fence/objek pembungkus.
- `_narrate_titles(job_id, seeds, generate=None) -> tuple[List[Dict[str, Any]], Optional[str], str]` — satu panggilan LLM untuk semua butir narasi; jika gagal, pipeline tetap selesai. **Memanggil Copilot/LMM via `copilot_client.generate`**.
- `_narration_markdown(records, requested, reason) -> List[str]` — render blok markdown narasi.
- `_shared_embedder()` — ambil embedding model dari vector store; fallback ke `None` bila tidak tersedia.
- `stage_source(stage_key) -> List[Dict[str, Any]]` — ambil kode sumber fungsi-fungsi nyata yang dijalankan satu tahap (untuk UI/debug).
**Tahap pipeline:**
- `stage_chunking(job_id, pdf_paths, out_path, target_tokens=..., max_tokens=..., overlap_ratio=..., embedder=None, ocr_mode="auto") -> StageOutcome` — proses tiap PDF via `process_pdf`, simpan chunks JSONL, hitung metrik chunking, dan opsional cek koherensi korpus. **Memanggil filesystem, GROBID/OCR/PDF pipeline internal, dan job_store**; bukan LLM.
- `stage_gap_mining(job_id, chunks_path, out_path, limit=0, llm_trace_limit=..., workers=..., runs=1, min_run_hits=0) -> StageOutcome` — pilih kandidat, ekstrak gap via LLM JSON mode, verifikasi verbatim ke chunk sumber, dedup, hitung konsensus k/n, ekspor raw/candidate/clean JSONL. **Memanggil Copilot/LMM** lewat `copilot_client.generate`; fallback kosong menghasilkan 0 gap dan dicatat sebagai kegagalan sistem.
  - Semantik `runs`: ulang lintasan LLM atas kandidat yang sama; `runs>1` mengukur stabilitas.
  - Semantik `min_run_hits`: bila `<=0`, pakai `default_min_run_hits(runs)` yaitu `ceil(2n/3)`.
  - `until/start_from` tidak berlaku di sini, tetapi hasil stage ini dipakai `novelty`.
- `stage_novelty(job_id, gaps_path, out_path, from_date="2024-01-01", min_interval=1.0, max_retries=4, limit=0) -> StageOutcome` — cek gap stabil ke OpenAlex 2024+, klasifikasikan `open/partially_addressed/addressed/unchecked`, lewati gap `stable=false`, dan tulis JSONL novelty. **Memanggil OpenAlex via `annotate_gaps`/`OpenAlexAPI.search_recent`**; jika `OPENALEX_DISABLED`, status `unchecked`.
- `stage_recommendation(job_id, gaps_novelty_path, chunks_path, out_path, embedder=None, top=15, narrate_top=NARRATION_TOP, generate_fn=None) -> StageOutcome` — filter gap open/unchecked, hitung skor prioritas, cluster tema, lalu opsional narasi judul/latar/alasan/metode dengan LLM. **Memanggil Copilot/LMM** untuk narasi, dan fungsi ranking/tema yang rule-based + embedder opsional.
  - `narrate_top=0` mematikan narasi.
- `run_research_pipeline(job_id, pdf_paths, out_dir, embedder=None, limit=0, from_date="2024-01-01", until=None, ocr_mode="auto", start_from=None, novelty_limit=0, stages_done=None, gap_runs=1, min_run_hits=0) -> Dict[str, Any]` — orkestrator penuh; validasi `until/start_from`, bangun path output, jalankan tahap berurutan, catat job status/progress, dan support resume dari tahap tertentu.
  - `until` — hentikan pipeline setelah tahap itu selesai; contoh `gap_mining` berarti belum masuk OpenAlex.
  - `continue` — tidak ada keyword parameter bernama `continue`; yang setara adalah melanjutkan via `start_from` + artefak tahap sebelumnya.
  - `start_from` — lanjut dari tahap tertentu memakai output sebelumnya; `gap_mining` tidak diulang bila resume dari tahap setelahnya.
  - `novelty_limit` — batas jumlah gap yang dicek OpenAlex di tahap novelty; 0 = semua.
  - `gap_runs` — jumlah run gap mining; bila >1, gunakan konsensus k/n.
  - `stages_done` — daftar tahap yang sudah selesai sebelumnya, digabung ke job store saat selesai.
- `run_research_job(job_id) -> None` — handler worker queue: baca payload job tersimpan, validasi PDF/artefak, panggil `run_research_pipeline`, dan catat cancel/fail ke job_store. **Memakai filesystem + job_store**.
- `STAGE_SOURCE_FUNCS` — mapping tahap → fungsi sumber nyata yang dieksekusi.
- `__main__` tidak ada.
**Alur utama:**
- `AnalysisJobQueue` memanggil `run_research_job`, yang membaca payload job dari `job_store`.
- `run_research_pipeline` mengeksekusi `stage_chunking` → `stage_gap_mining` → `stage_novelty` → `stage_recommendation` sesuai `until/start_from`.
- `stage_gap_mining` adalah satu-satunya tahap yang memanggil LLM besar untuk ekstraksi gap; jika `copilot_client.generate()` gagal/kosong, hasil bisa 0 gap dan ditandai sebagai kegagalan sistem.
- `stage_novelty` selalu lewat OpenAlex/cache disk (`http_cache`), dan gap `stable=false` sengaja tidak dikirim untuk hemat kuota.
- `stage_recommendation` memakai gap open/unchecked, ranking/tema rule-based, lalu narasi judul jika Copilot/LLM tersedia.
- `http_cache` menjaga rate-limit, TTL, dan cooldown 429 supaya API paper tidak dihajar ulang saat kuota habis.
- `copilot_client` diprioritaskan oleh `llm_service` bila aktif; bila tidak, `llm_service` jatuh ke Ollama lokal.
- `paper_apis/__init__.py` memastikan semua client sumber paper bisa diimpor dari satu namespace.


## Tambahan — fungsi bersarang (nested) di backend/app/services/

### `backend/app/services/llm_service.py`
- `_one(p: str) -> str` — bersarang di `GLMInterface.generate_batch()`; menjalankan satu prompt di worker thread (LLM), mengembalikan teks atau string kosong bila gagal.

### `backend/app/services/research_pipeline.py`
- `_work(cand: Dict[str, Any], run_idx: int = 0) -> List[Dict[str, Any]]` — bersarang di `stage_gap_mining()`; menjalankan ekstraksi gap untuk satu kandidat pada satu run (k/n), merekam trace LLM, dan menempelkan `_run`.
- `_generate(prompt: str, system: str) -> Optional[str]` — bersarang di `_work()` dalam `stage_gap_mining()`; memanggil `copilot_client.generate()` mode JSON (LLM) dan menyimpan prompt/response/model ke artefak job.
- `_gap_row(g: Dict[str, Any]) -> Dict[str, Any]` — bersarang di `stage_gap_mining()`; merangkum satu gap menjadi baris ringkas untuk `sample`/`substep_samples`.
- `_tick(done: int, total: int) -> None` — bersarang di `stage_novelty()`; mengirim progress berkala ke job store saat pengecekan OpenAlex berjalan lambat.
- `_nov_row(g: Dict[str, Any]) -> Dict[str, Any]` — bersarang di `stage_novelty()`; merangkum satu gap hasil cek kebaruan sebagai contoh `addressed/open/unchecked`.

## backend/app/utils/

### `backend/app/utils/__init__.py` — paket utilitas yang mengekspos helper inti untuk processor dokumen dan loader konfigurasi.
**Fungsi/ekspor:**
- `DocumentProcessor` — diekspor dari `document_processor.py` untuk dipakai pipeline dokumen.
- `ConfigLoader` — diekspor dari `config_loader.py` untuk memuat konfigurasi runtime.
- `__all__` — hanya mengizinkan ekspor `["DocumentProcessor", "ConfigLoader"]`.

### `backend/app/utils/job_store.py` — penyimpanan durabel untuk job analisis, event, artefak stage, dan sesi percakapan berbasis SQLite dengan kompatibilitas JSON legacy.
**Kelas:**
- `JobRecord(TypedDict, total=False)` — skema longgar untuk record job; menyimpan field status/progress/timestamp plus payload tambahan dari pipeline.
**Konstanta modul penting:**
- `_LOCK` — `RLock` untuk serialisasi akses memori/SQLite.
- `_ACTIVE_STATUSES`, `_TERMINAL_STATUSES` — status job untuk recovery, cancel, dan cleanup.
- `_INTERRUPTED_MESSAGE` — pesan standar saat job dipulihkan setelah restart.
- `_SENSITIVE_EVENT_KEYS` — kunci telemetry yang dibuang agar event tetap metadata-only.
- `_ARTIFACT_*` — batas ukuran artefak stage agar snapshot tetap ringan.
**Fungsi:**
- `_default_store_path() -> Path` — menentukan file SQLite default di `data.processed_path/analysis_jobs.sqlite3`.
- `_resolve_store_path(path) -> Path` — memilih path store dari argumen atau default.
- `_json_dumps(value) -> str` — serialisasi JSON aman untuk SQLite.
- `_json_loads(value, fallback) -> Any` — parse JSON dengan fallback deep-copy saat rusak/kosong.
- `_connect(path) -> sqlite3.Connection` — membuka koneksi SQLite WAL, foreign keys aktif, timeout 30s.
- `_ensure_schema(conn) -> None` — membuat tabel `jobs`, `job_events`, `job_stage_artifacts`, `conversations`, `conversation_messages`.
- `_row_to_job(row) -> JobRecord` — mengubah baris SQLite menjadi struktur job gabungan `data_json` + kolom terpisah.
- `_persist_job(conn, job_id, updates) -> dict[str, Any]` — upsert job ke tabel `jobs`, menaikkan `revision`, mengisi `completed_at` bila terminal.
- `_legacy_load(path) -> dict[str, dict[str, Any]]` — memuat store JSON lama, menandai job aktif sebagai `interrupted`, lalu menulis ulang bila berubah.
- `_legacy_write(path) -> None` — menulis JSON legacy via file sementara lalu `os.replace`.
- `_migrate_legacy_json(conn, sqlite_path) -> None` — migrasi `analysis_jobs.json` lama ke SQLite dan mengarsipkan file legacy menjadi `.json.migrated`.
- `_ensure_sqlite(path) -> Path` — memastikan schema SQLite siap; menolak path `.json` untuk operasi SQLite.
- `load_jobs(path=None) -> dict[str, JobRecord]` — memuat semua job; pada SQLite juga merequeue job yang tertinggal setelah restart.
- `save_job(job_id, job) -> None` — menyimpan/update job; pada mode legacy menulis JSON, pada SQLite upsert transaksi.
- `update_job(job_id, **updates) -> JobRecord | None` — merge update atomik pada satu job dan mengembalikan state baru.
- `complete_job(job_id, **updates) -> JobRecord | None` — menandai job `completed` hanya bila `cancel_requested` belum aktif.
- `delete_job(job_id) -> JobRecord | None` — menghapus job dan membiarkan event/artifact cascade di SQLite.
- `get_job(job_id) -> JobRecord | None` — mengambil job terbaru dari storage.
- `list_jobs(statuses=None) -> list[JobRecord]` — daftar job terbaru-ke-terlama, opsional difilter status.
- `claim_next_job() -> JobRecord | None` — klaim atomik job `queued` berikutnya untuk worker lokal; menaikkan attempt dan mencatat event `job.claimed`.
- `request_cancel(job_id) -> JobRecord | None` — pembatalan kooperatif; job queued langsung jadi cancelled, job running diberi flag cancel.
- `retry_job(job_id, delay_seconds=0, reset_attempts=True) -> JobRecord | None` — requeue job terminal jika payload input masih ada.
- `is_cancel_requested(job_id) -> bool` — cek flag cancel job.
- `record_job_event(job_id, event_type, *, phase=None, status=None, duration_ms=None, data=None) -> None` — simpan telemetry event metadata-only ke `job_events`.
- `get_job_events(job_id, after_event_id=0) -> list[dict[str, Any]]` — ambil event berurutan untuk SSE/diagnostik.
- `_bound_artifact_value(value, max_field_chars) -> Any` — membatasi ukuran payload artefak tanpa membuang konten penting.
- `add_stage_artifact(job_id, phase, kind, label="", payload=None, max_field_chars=6000) -> None` — simpan artefak stage seperti hasil LLM, preview ekstraksi, atau trace.
- `get_stage_artifacts(job_id, phase=None) -> list[dict[str, Any]]` — ambil artefak stage per job, opsional difilter fase.
- `get_latest_completed_job() -> JobRecord | None` — ambil job completed terbaru yang punya snapshot hasil.
- `set_job_graph(job_id, graph_snapshot) -> JobRecord | None` — simpan snapshot graph serializable pada job.
- `get_job_graph(job_id) -> dict[str, Any] | None` — ambil snapshot graph job bila ada.
- `get_conversation_messages(conversation_id, limit=10) -> list[dict[str, str]]` — muat window pesan percakapan terbaru dalam urutan kronologis.
- `append_conversation_message(conversation_id, role, content, ttl_days=30) -> None` — tambah pesan chat dan perpanjang/insert sesi conversation.
- `clear_conversation(conversation_id) -> bool` — hapus sesi chat beserta semua pesan.
- `cleanup_expired(retention_days=30, telemetry_retention_days=14) -> dict[str, Any]` — hapus conversation expired, event/artifact lama, dan job terminal tua; mengembalikan ringkasan serta `input_dirs` job yang dibersihkan.
- `_sanitize_event_data(data) -> dict[str, Any]` — memfilter event agar tetap metadata-only, memotong string, dan mengubah list menjadi panjangnya.

### `backend/app/utils/config_loader.py` — pemuat konfigurasi YAML + env yang menormalkan path, memvalidasi batas aman, dan menyediakan summary config ter-redaksi.
**Kelas:**
- `LLMConfig` — parameter model LLM; field utama: `base_url`, `model_name`, `temperature`, `top_p`, `max_tokens`, `context_window`, `timeout`, `keep_alive`, `num_parallel`.
- `VectorDBConfig` — konfigurasi ChromaDB/embedding; field: `persist_directory`, `collection_name`, `embedding_model`, `distance_metric`, `batch_size`.
- `Neo4jConfig` — koneksi graph DB; field: `uri`, `user`, `password`, `database`.
- `RetrievalConfig` — pengaturan retrieval; field: `top_k`, `chunk_size`, `chunk_overlap`, `min_relevance_score`, `rerank_enabled`, `reranker_model`, `chunk_strategy`.
- `APIConfig` — konfigurasi FastAPI; field: `host`, `port`, `workers`, `reload`, `cors_origins`, `cors_enabled`, `rate_limit_enabled`, `rate_limit_per_minute`.
- `DataConfig` — path data dan batas upload; field: `raw_path`, `processed_path`, `allowed_file_types`, `max_file_size_mb`.
- `QueueConfig` — konfigurasi antrean job lokal; field: `max_workers`, `max_attempts`, `retention_days`, `telemetry_retention_days`.
- `TelemetryConfig` — retensi event metadata; field: `enabled`, `retention_days`.
- `RuleConfig` — konfigurasi rule engine; field: `enabled`, `claim_confidence`, `min_confidence_threshold`, `rules`.
- `FactExtractionConfig` — threshold ekstraksi fakta; field: `enabled`, `llm_extracted_confidence`, `pattern_causal_confidence`, `pattern_contradiction_confidence`, `pattern_extension_confidence`.
- `OCRConfig` — konfigurasi layanan OCR ocrd; field: `enabled`, `service_url`, `api_key`, `image_mode`, `dpi`, `timeout`, `prefer_text_layer`, `validate_service_on_startup`.
- `AppConfig` — agregasi semua sub-konfigurasi + `log_level`, `log_file`.
- `ConfigLoader` — memuat, memvalidasi, dan mengekspor konfigurasi runtime aplikasi.
**Fungsi:**
- `load_project_env() -> None` — memuat `.env` root dulu lalu `backend/.env` sebagai override; dipakai sebelum baca env lain.
- `_env_bool(name, default) -> bool` — parser bool env yang menerima `1/true/yes/on`.
- `ConfigLoader._find_config_file() -> Optional[str]` — mencari config YAML di `backend/config.yaml`, `./configs/config.yaml`, `./config.yaml`, `../configs/config.yaml`.
- `ConfigLoader._resolve_path(path) -> str` — menormalkan path relatif terhadap project root agar tidak membuat duplikasi `data/` atau `chroma_db/`.
- `ConfigLoader._load_yaml() -> Dict[str, Any]` — memuat YAML jika file ada; gagal kembali ke `{}`.
- `ConfigLoader._load_config() -> AppConfig` — merakit config final dari YAML + env, lalu memvalidasi.
- `ConfigLoader._validate_config(config) -> None` — memeriksa batas aman; terutama timeout/temperature/top_p, `queue.max_workers` 1–2, OCR dpi/timeout.
- `ConfigLoader.get_config() -> AppConfig` — mengembalikan config ter-load.
- `ConfigLoader.get_effective_config_summary() -> Dict[str, Any]` — snapshot config ter-redaksi; menyamarkan password Neo4j dan `ocr.api_key`.
- `ConfigLoader.reload() -> None` — muat ulang config dari sumber asli.
- `ConfigLoader.save_config(output_path) -> None` — tulis config aktif ke YAML; password disensor.
- `get_config() -> AppConfig` — akses singleton global `ConfigLoader`.
- `reload_config() -> None` — reload singleton global jika sudah dibuat.
- `get_effective_config_summary() -> Dict[str, Any]` — expose summary config ter-redaksi dari singleton.
- `if __name__ == "__main__"` block — contoh penggunaan manual, tidak memengaruhi runtime import.
**Catatan prioritas config:**
- Untuk field tertentu, env mengalahkan YAML; YAML mengalahkan default.
- Jalur env penting: `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `LLM_*`, `CHROMA_*`, `EMBEDDING_MODEL`, `NEO4J_*`, `RETRIEVAL_*`, `CHUNK_*`, `API_*`, `CORS_ENABLED`, `RATE_LIMIT_ENABLED`, `DATA_*`, `MAX_FILE_SIZE_MB`, `ANALYSIS_QUEUE_*`, `ANALYSIS_JOB_*`, `TELEMETRY_*`, `OCR_ENABLED`, `OCR_SERVICE_URL`, `OCR_API_KEY`, `OCR_IMAGE_MODE`, `OCR_DPI`, `OCR_TIMEOUT`, `OCR_PREFER_TEXT_LAYER`, `OCR_VALIDATE_ON_STARTUP`, `LOG_LEVEL`, `LOG_FILE`.

### `backend/app/utils/document_processor.py` — pemroses PDF untuk ekstraksi teks, metadata, chunking section-aware, dan fallback OCR/pypdf.
**Kelas:**
- `DocumentChunk` — representasi satu chunk dokumen; field: `chunk_id`, `content`, `metadata`, `chunk_index`, `total_chunks`.
- `ProcessedDocument` — hasil proses satu PDF; field: `doc_id`, `title`, `content`, `chunks`, `metadata`.
- `DocumentProcessor` — orkestrator ekstraksi teks, metadata, pembersihan, chunking, dan citasi.
**Konstanta modul penting:**
- `_SCANNED_PDF_CHARS_PER_PAGE` — ambang diagnostik untuk menandai PDF pypdf yang kemungkinan scan.
- `_SECTION_KEYWORDS` — daftar header section bahasa Inggris/Indonesia untuk deteksi section.
**Fungsi/method:**
- `DocumentProcessor.__init__(chunk_size=512, chunk_overlap=50, min_chunk_length=100, chunk_strategy="sections", ocr_enabled=False, ocr_options=None)` — set parameter chunking dan mode OCR; OCR client dibuat lazily.
- `DocumentProcessor.ocr_client` — property lazy yang membuat `OcrdClient`; bila gagal, OCR dinonaktifkan dan pipeline lanjut tanpa raise.
- `DocumentProcessor.process_pdf(pdf_path, extract_metadata=True) -> ProcessedDocument` — alur utama proses PDF: ekstrak teks, buat doc_id, ekstrak metadata, bersihkan teks, chunk section-aware atau fixed-window, lalu return `ProcessedDocument`.
- `DocumentProcessor._extract_text_from_pdf(pdf_path) -> Tuple[str, str]` — urutan ekstraksi: OCRD-first (jika enabled) → `pypdf` fallback; mengembalikan teks dan metode (`ocrd_text_layer`, `ocr`, atau `pypdf`).
- `DocumentProcessor._try_ocr(pdf_path)` — memanggil ocrd dengan pengecekan `is_available()` dan menelan semua error; hasil `OcrdResult` atau `None`.
- `DocumentProcessor._extract_metadata(text) -> Dict[str, Any]` — ekstraksi heuristik title, abstract, year, keywords, authors dari teks awal dokumen.
- `DocumentProcessor._clean_text(text) -> str` — normalisasi whitespace, hapus page-number/artifact PDF, dan rapikan line breaks.
- `DocumentProcessor._detect_sections(text) -> List[Tuple[str, str]]` — memecah teks menjadi pasangan `(section_title, section_text)` dengan detektor heading bernomor, keyword, atau ALL-CAPS; balik `[]` bila tidak cukup sinyal.
- `DocumentProcessor._chunk_sections(text, doc_id, metadata) -> List[DocumentChunk]` — chunking section-aware: section → sliding window sub-chunks, tag `section`, dan fallback ke fixed-window jika section tak terdeteksi.
- `DocumentProcessor._chunk_text(text, doc_id, metadata) -> List[DocumentChunk]` — chunking sliding window tradisional dengan overlap dan pemotongan di batas kalimat.
- `DocumentProcessor._generate_doc_id(file_path) -> str` — membuat ID stabil 16 karakter dari path normalisasi MD5.
- `DocumentProcessor.process_directory(directory, recursive=True, file_pattern="*.pdf") -> List[ProcessedDocument]` — memproses semua PDF dalam direktori dan melewatkan yang gagal.
- `DocumentProcessor.extract_citations(text) -> List[str]` — ekstraksi citasi sederhana berbasis regex `[1]` dan `(Author, Year)` lalu dedup maksimal 50.
- `DocumentProcessor.extract_weakness_sections(full_text, max_chars=4000) -> str` — mengambil bagian paper yang memuat limitation/future work/threats/discussion/conclusion, atau tail dokumen jika header tak ditemukan.
- `DocumentProcessor.chunk_by_sections(text, doc_id, metadata) -> List[DocumentChunk]` — strategi section-based lama/alternatif berdasarkan header ALL-CAPS; menghasilkan chunk per section tanpa sliding window.
- `if __name__ == "__main__"` block — contoh penggunaan manual.
**Alur penting:**
- OCRD-first: PDF dikirim ke service OCR eksternal `http://127.0.0.1:8792` bila enabled.
- Bila OCRD mengembalikan text layer, method dicatat sebagai `ocrd_text_layer`; bila OCR nyata, method `ocr`.
- Jika OCR gagal/tidak tersedia, fallback ke `pypdf`.
- Default chunking `sections` lebih dulu mencoba deteksi heading; jika gagal, baru fallback ke fixed-window.

### `backend/app/utils/ocr_client.py` — client HTTP tipis untuk layanan OCR ocrd yang memprioritaskan text layer lalu OCR GPU server-side.
**Kelas:**
- `OcrdResult` — hasil parse `POST /v1/ocr`; field: `text`, `from_text_layer`, `page_count`, `duration_ms`, `engine`, `image_mode`, `pages`.
- `OcrdClient` — pembungkus request ke ocrd dengan caching availability dan kegagalan yang tidak melempar ke caller.
**Fungsi/method:**
- `_env_bool(name, default) -> bool` — parser env boolean untuk konfigurasi OCR.
- `OcrdClient.__init__(service_url=None, api_key=None, image_mode=None, dpi=None, timeout=None, prefer_text_layer=None)` — membaca env `OCR_SERVICE_URL`, `OCR_API_KEY`, `OCR_IMAGE_MODE`, `OCR_DPI`, `OCR_TIMEOUT`, `OCR_PREFER_TEXT_LAYER`; menyiapkan session requests.
- `OcrdClient._headers() -> Dict[str, str]` — menambah `X-API-Key` bila ada.
- `OcrdClient.is_available(force=False) -> bool` — cek `/health` + `model_ready` dengan cache TTL 15 detik; pakai jaringan eksternal.
- `OcrdClient.read_document(file_path) -> Optional[OcrdResult]` — kirim file via multipart ke `POST /v1/ocr`; parse JSON, log status/hint error; return `None` pada semua failure.
- `OcrdClient.ocr_pdf(pdf_path) -> Optional[str]` — wrapper yang mengembalikan hanya teks.
**Catatan:** modul ini murni jaringan eksternal; tidak melakukan ekstraksi lokal.

### `backend/app/utils/rate_limit.py` — middleware rate limiting sliding-window berbasis IP untuk satu proses uvicorn.
**Konstanta modul penting:**
- `EXEMPT_PATHS` — path health/system-stats yang tidak dibatasi.
- `EXEMPT_GET_PREFIXES` — prefix GET polling status/job yang dikecualikan.
**Fungsi/method:**
- `_is_exempt(request) -> bool` — menentukan apakah request dibebaskan dari rate limit.
- `SlidingWindowRateLimiter` — kelas pembatas laju sliding-window
  - `__init__(limit, window_seconds=60.0)` — inisialisasi counter per-IP dan lock.
  - `allow(key) -> bool` — cek dan catat hit secara atomik; menolak bila melewati limit.
  - `reset() -> None` — kosongkan semua hit.
- `create_rate_limit_middleware(limit, window_seconds=60.0)` — buat async middleware Starlette yang mengembalikan `429` + `Retry-After` ketika limit terlampaui.
**Catatan:** ini rule-based/in-memory; tidak ada jaringan atau filesystem.

### `backend/app/utils/upload_validation.py` — validasi upload PDF untuk extension, magic header, ukuran, dan streaming aman ke disk.
**Konstanta modul penting:**
- `PDF_MAGIC` — signature `%PDF-`.
- `CHUNK_SIZE` — ukuran baca stream 1 MiB.
**Fungsi/method:**
- `sanitize_filename(name) -> str` — membersihkan nama file dari path traversal, NUL, karakter non-printable, dan panjang berlebih.
- `_max_bytes(max_mb) -> int` — konversi limit MB ke byte.
- `validate_pdf_upload(file, max_mb) -> None` — cek extension `.pdf`, header magic PDF, dan size sebelum menyimpan; raise `HTTPException` bila gagal.
- `write_validated_pdf_upload(file, destination, max_mb) -> None` — validasi lalu stream upload ke destination; membersihkan file tujuan bila terjadi error.
**Catatan:** murni filesystem + validasi rule-based.

### `backend/app/utils/url_guard.py` — pengaman SSRF untuk URL HTTP(S) agar backend hanya mengunduh host publik.
**Konstanta modul penting:**
- `ALLOWED_SCHEMES` — hanya `http` dan `https`.
**Kelas:**
- `UnsafeURLError(ValueError)` — error bila URL mengarah ke scheme/host berbahaya.
**Fungsi/method:**
- `resolve_host(hostname) -> list[str]` — resolve DNS hostname ke semua IP; dipisah agar test bisa stub.
- `_is_public(address) -> bool` — cek IP global/non-multicast, termasuk IPv4-mapped IPv6.
- `assert_public_http_url(url) -> str` — validasi URL: scheme, tanpa kredensial, bukan localhost, resolve ke IP publik; return URL jika aman.
**Catatan:** rule-based + DNS lookup jaringan, tapi bukan LLM.

**Alur utama:**
- `config_loader.py` memuat konfigurasi global yang dipakai utilitas lain: OCR, data path, rate limit, dan queue.
- `document_processor.py` menjadi pintu utama ingest PDF: OCRD-first, lalu pypdf, lalu chunking section-aware.
- `ocr_client.py` adalah adaptor jaringan ke layanan OCR eksternal.
- `job_store.py` menyimpan state job, event, artefak, dan chat session secara durabel.
- `upload_validation.py`, `url_guard.py`, dan `rate_limit.py` menangani keamanan input dan pembatasan request di level HTTP.

## backend/scripts/

### `backend/scripts/check_novelty.py` — CLI untuk menilai novelty gap yang sudah ditambang terhadap literatur terbaru OpenAlex.
**Fungsi:**
- `main(argv=None)` — parse argumen `--gaps`, `--out`, `--from-date`, `--min-interval`, `--max-retries`; baca JSONL gap, panggil `annotate_gaps`, tulis JSONL hasil dengan metadata novelty, dan gagal bila ada gap tanpa `novelty_status`.
**Argumen utama argparse:**
- `--gaps` — input JSONL gap.
- `--out` — output JSONL ter-enrich.
- `--from-date` — batas tanggal publikasi recent, default `2024-01-01`.
- `--min-interval` — jeda antar request OpenAlex.
- `--max-retries` — retry budget untuk 429/5xx.
**Modul backend yang dipakai:**
- `app.core.gap_mining.novelty.annotate_gaps`
- `app.core.pipeline.io.read_jsonl`, `write_jsonl`
**Sifat kerja:**
- Jaringan eksternal ke OpenAlex.
- Tidak memakai LLM langsung di file ini; hanya orchestration.

### `backend/scripts/mine_gaps.py` — CLI untuk menambang gap penelitian dari chunks JSONL lewat kandidat, ekstraksi LLM, verifikasi grounding, dan deduplikasi.
**Fungsi:**
- `_dedup_gaps(gaps) -> List[Dict[str, Any]]` — dedup gap berdasarkan `(source, gap_statement)` hash SHA-1.
- `_regex_baseline(chunks) -> int` — menghitung baseline lama berbasis regex saja untuk perbandingan.
- `mine(chunks_path, out_path, job_id, limit=0, workers=4)` — load chunk record, pilih kandidat, proses paralel dengan thread pool, ekstrak gap via LLM/helper, simpan raw gap, verifikasi verbatim grounding, dedup, lalu tulis JSONL final + meta.
- `main(argv=None)` — parse `--chunks`, `--out`, `--job-id`, `--limit`, `--workers`, lalu panggil `mine`.
**Argumen utama argparse:**
- `--chunks` — file JSONL chunks.
- `--out` — file output gaps JSONL.
- `--job-id` — label job (default `job`).
- `--limit` — batas kandidat untuk run cepat.
- `--workers` — jumlah thread ekstraksi.
**Modul backend yang dipakai:**
- `app.core.gap_mining.candidates.matched_phrases`, `select_candidates`, `with_context`
- `app.core.gap_mining.extractor.extract_gaps_from_candidate`
- `app.core.gap_mining.verify.verify_gaps`
- `app.core.pipeline.io.read_jsonl`, `write_jsonl`
**Sifat kerja:**
- Memakai LLM/ekstraksi struktur di tahap extractor.
- Verifikasi berbasis aturan/verbatim grounding.
- Menulis artefak raw `.raw.jsonl` sebagai cache verifikasi ulang.

### `backend/scripts/papers_cli.py` — CLI untuk mencari paper eksternal dan opsional meng-ingest-nya ke vector store.
**Konstanta modul penting:**
- `ALL_SOURCES` — daftar sumber API yang bisa dipilih.
- `DEFAULT_SOURCES` — default sumber query (`arxiv`, `europe_pmc`, `crossref`).
**Fungsi/method:**
- `build_paper_api() -> AggregatedPaperAPI` — membangun agregator API paper dengan API key/env yang sama seperti backend.
- `clean_paper_metadata(paper) -> dict` — menormalkan metadata paper agar kompatibel ChromaDB dan membuang `None`.
- `async def _fetch(args)` — query multi-source, over-fetch per source, dedupe opsional, dan return `(papers, per_source_counts)`.
- `_emit(data, as_json, human)` — helper output JSON atau human-readable.
- `cmd_search(args) -> None` — jalankan `_fetch`, cetak hasil pencarian ringkas.
- `cmd_ingest(args) -> None` — fetch lalu buat `VectorStore`, tambah `Document` ke koleksi, dan laporkan hasil ingest.
- `add_common_fetch_args(p) -> None` — tambahkan argumen bersama untuk subcommand `search` dan `ingest`.
- `build_parser() -> argparse.ArgumentParser` — bangun parser CLI dengan subcommand `search` dan `ingest`.
- `main() -> int` — parse argumen dan dispatch ke handler.
**Argumen utama argparse:**
- Positional `query`.
- `-k/--k` jumlah paper total.
- `--sources` daftar sumber API.
- `--year-from`, `--year-to`.
- `--no-dedupe`.
- Untuk `ingest`: `--persist-dir`, `--collection`.
- Global: `--json`.
**Modul backend yang dipakai:**
- `app.services.paper_apis.AggregatedPaperAPI`
- Saat ingest: `app.core.retrieval.vector_store.VectorStore`, `Document`
- `app.utils.config_loader.get_config`
**Sifat kerja:**
- Jaringan eksternal ke berbagai source paper.
- Ingest melakukan write filesystem/chroma persist.

### `backend/scripts/reindex_corpus.py` — CLI migrasi lossless koleksi ChromaDB ke embedding space baru.
**Konstanta modul penting:**
- `DEFAULT_TARGET_MODEL` — multilingual embedding model target.
**Fungsi:**
- `main() -> int` — parse argumen source/target collection/model, baca semua document dari source vector store, buat target collection baru, re-embed dan salin dokumen; dukung `--dry-run`.
**Argumen utama argparse:**
- `--persist-dir`
- `--source-collection`
- `--source-model`
- `--target-collection`
- `--target-model`
- `--batch-size`
- `--dry-run`
**Modul backend yang dipakai:**
- `app.core.retrieval.vector_store.VectorStore`, `Document`
- `app.utils.config_loader.get_config`
**Sifat kerja:**
- Filesystem/persisted ChromaDB.
- Tidak memakai LLM langsung; hanya re-embedding dan migrasi.

### `backend/scripts/run_pipeline.py` — CLI untuk menjalankan pipeline chunking dokumen baru atau baseline legacy pada folder PDF.
**Konstanta modul penting:**
- `_source_name` — alias lama untuk `source_name` agar kompatibel dengan pemanggil existing.
**Fungsi:**
- `_load_embedder()` — mencoba memuat `SentenceTransformer` CPU; return `None` bila tidak tersedia.
- `_report_relevance(results)` — menilai koherensi korpus per jurnal, menandai outlier, dan log statistik median/rentang.
- `_run_new(pdfs, out_path, job_id)` — jalankan pipeline baru `process_pdf` per PDF, lalu tulis chunks JSONL via `write_chunks_jsonl`.
- `_run_legacy(pdfs, out_path, job_id)` — jalankan `DocumentProcessor` legacy/fixed-window, hasilkan JSONL format lama.
- `main(argv=None)` — parse input folder, output, job-id, `--legacy`, `--limit`; validasi direktori dan jumlah PDF, lalu pilih mode baru atau legacy.
**Argumen utama argparse:**
- `--input` direktori PDF.
- `--out` output JSONL.
- `--job-id`.
- `--legacy`.
- `--limit`.
**Modul backend yang dipakai:**
- `app.core.pipeline.corpus_relevance.build_probe`, `check_corpus_relevance`
- `app.core.pipeline.io.source_name`, `write_chunks_jsonl`, `write_jsonl`
- `app.core.pipeline.pipeline.process_pdf`
- Legacy mode: `app.utils.document_processor.DocumentProcessor`
**Sifat kerja:**
- Pipeline inti berbasis filesystem dan chunking.
- `_report_relevance` memakai embedder sentence-transformers bila ada.

### `backend/scripts/runtime_doctor.py` — CLI untuk menampilkan ringkasan konfigurasi runtime ter-redaksi dan opsional mengecek service OCR.
**Fungsi:**
- `main() -> int` — cetak summary config JSON, dan jika `--check-ocr` diaktifkan, probe availability OCR service via `get_document_processor().ocr_client.is_available()`.
**Argumen utama argparse:**
- `--check-ocr` — lakukan probe ke layanan OCR bila OCR diaktifkan.
**Modul backend yang dipakai:**
- `app.api.dependencies.get_document_processor`
- `app.utils.config_loader.get_effective_config_summary`
**Sifat kerja:**
- Diagnostik runtime; bisa menyentuh jaringan ke OCR service jika diminta.

### `backend/scripts/vectorstore_cli.py` — CLI untuk inspeksi dan query ChromaDB/vector store proyek.
**Fungsi:**
- `_build_store() -> VectorStore` — instantiate `VectorStore` dari config aktif.
- `_print(data, as_json, human)` — output JSON atau format manusia.
- `cmd_stats(store, args) -> None` — tampilkan statistik koleksi.
- `cmd_sources(store, args) -> None` — hitung distribusi source dokumen/chunks.
- `cmd_query(store, args) -> None` — semantic search, opsional filter `source`, tampilkan skor dan preview.
- `build_parser() -> argparse.ArgumentParser` — bangun CLI dengan subcommand `stats`, `sources`, `query`.
- `main() -> int` — parse argumen, buat store, dispatch handler.
**Argumen utama argparse:**
- Global `--json`.
- `stats` tanpa argumen tambahan.
- `sources` tanpa argumen tambahan.
- `query text`, `-k/--k`, `--source`, `--min-score`.
**Modul backend yang dipakai:**
- `app.core.retrieval.vector_store.VectorStore`
- `app.utils.config_loader.get_config`
**Sifat kerja:**
- Akses ChromaDB lokal/persisted, tidak ada jaringan eksternal.

**Alur utama:**
- `run_pipeline.py` menghasilkan chunks JSONL dari PDF, baik mode baru maupun legacy.
- `mine_gaps.py` mengubah chunks menjadi kandidat gap, lalu verifikasi grounding dan dedup.
- `check_novelty.py` menilai gap terhadap literatur recent via OpenAlex.
- `papers_cli.py` dan `reindex_corpus.py` mengisi/merombak corpus ChromaDB.
- `vectorstore_cli.py` dan `runtime_doctor.py` dipakai untuk inspeksi dan diagnostik operasional.
- Semua CLI memanfaatkan config/runtime yang sama dengan backend agar perilaku konsisten.


## Tambahan — method dan fungsi bersarang di backend/app/utils/ & backend/scripts/

### `backend/app/utils/config_loader.py` (kelas `ConfigLoader`)
- `__init__(config_path: Optional[str] = None)` — menentukan file config, memuat `.env` project/backend, lalu membangun konfigurasi efektif.
- `_find_config_file() -> Optional[str]` — mencari YAML config di lokasi standar dan mengembalikan path pertama yang ada.
- `_load_config() -> AppConfig` — menggabungkan YAML + env menjadi `AppConfig`, lalu memvalidasi hasilnya.
- `_load_yaml() -> Dict[str, Any]` — membaca YAML config jika ada, atau mengembalikan dict kosong saat file tidak ditemukan/gagal dibaca.
- `_resolve_path(path: str) -> str` — menormalkan path relatif terhadap project root agar konsisten lintas working directory.
- `_validate_config(config: AppConfig) -> None` — memeriksa batas aman parameter LLM, queue, dan OCR lalu melempar `ValueError` bila invalid.
- `save_config(output_path: str)` — menulis config aktif ke YAML dengan kredensial disensor.

### `backend/app/utils/document_processor.py` (kelas `DocumentProcessor`)
- `__init__(chunk_size=512, chunk_overlap=50, min_chunk_length=100, chunk_strategy="sections", ocr_enabled=False, ocr_options=None)` — menyetel parameter chunking/OCR dan menyiapkan client OCR secara lazy.
- `_chunk_sections(text, doc_id, metadata) -> List[DocumentChunk]` — chunking berbasis section dengan sliding window per section.
- `_chunk_text(text, doc_id, metadata) -> List[DocumentChunk]` — chunking sliding-window ukuran tetap dengan overlap dan pemotongan di batas kalimat.
- `_clean_text(text: str) -> str` — membersihkan whitespace, artefak PDF, dan normalisasi line break.
- `_detect_sections(text: str) -> List[Tuple[str, str]]` — mendeteksi heading section dan memecah paper menjadi pasangan (judul, isi).
- `_extract_metadata(text: str) -> Dict[str, Any]` — mengekstrak metadata heuristik: title, abstract, year, keywords, authors (rule-based).
- `_extract_text_from_pdf(pdf_path: str) -> Tuple[str, str]` — mengekstrak teks dengan urutan **ocrd-first → fallback pypdf**, mengembalikan `(teks, extraction_method)`.
- `_generate_doc_id(file_path: str) -> str` — membuat ID dokumen stabil dari hash path file.
- `_try_ocr(pdf_path: str)` — mencoba OCR via layanan ocrd (HTTP), mengecek ketersediaan service, dan menelan semua error.
- `chunk_by_sections(text, doc_id, metadata) -> List[DocumentChunk]` — chunking alternatif lama berbasis header ALL-CAPS per section.
- `extract_citations(text: str) -> List[str]` — mengekstrak sitasi numerik dan author-year via regex lalu dedup.
- `extract_weakness_sections(full_text: str, max_chars: int = 4000) -> str` — mengambil bagian paper yang memuat limitation/future work/discussion/conclusion.
- `process_directory(directory, recursive=True, file_pattern="*.pdf") -> List[ProcessedDocument]` — memproses semua PDF dalam direktori dan mengumpulkan hasil yang sukses.

### `backend/app/utils/ocr_client.py` (kelas `OcrdClient`)
- `__init__(service_url=None, api_key=None, image_mode=None, dpi=None, timeout=None, prefer_text_layer=None)` — membaca konfigurasi OCR dari argumen/env (`OCR_*`) dan menyiapkan session HTTP.
- `_headers() -> Dict[str, str]` — membangun header request, termasuk `X-API-Key` bila ada.
- `read_document(file_path: str) -> Optional[OcrdResult]` — mengirim file ke `POST /v1/ocr` layanan ocrd (jaringan), mem-parsing JSON, mengembalikan hasil atau `None` saat gagal.
- `ocr_pdf(pdf_path: str) -> Optional[str]` — wrapper yang hanya mengembalikan teks OCR hasil `read_document`.

### `backend/app/utils/rate_limit.py`
- `rate_limit_middleware(request, call_next)` — bersarang di `create_rate_limit_middleware`; middleware async yang melewati path exempt (GET monitoring) dan mengembalikan `429` saat limit terlampaui.

### `backend/scripts/mine_gaps.py`
- `_work(cand)` — bersarang di `mine()`; membangun konteks kandidat lalu memanggil `extract_gaps_from_candidate` (LLM) untuk satu kandidat gap (dipakai untuk eksekusi paralel).

### `backend/scripts/papers_cli.py`
- `human(d)` — bersarang di `cmd_search()`; mencetak hasil pencarian paper dalam format ramah manusia.
- `human(d)` — bersarang di `cmd_ingest()`; mencetak ringkasan ingest paper ke vector store.

### `backend/scripts/vectorstore_cli.py`
- `human(d)` — bersarang di `cmd_stats()`; mencetak statistik vector store dalam format tabel sederhana.
- `human(d)` — bersarang di `cmd_sources()`; mencetak ringkasan jumlah chunk per sumber.
- `human(d)` — bersarang di `cmd_query()`; mencetak hasil semantic search beserta skor dan preview.


<a id="bagian-06"></a>
# Bagian 06 — experiments — skrip evaluasi tesis

## backend/experiments/

### `backend/experiments/__init__.py` — Paket penanda untuk modul eksperimen; tidak berisi CLI, fungsi, atau kelas.
**Fungsi:**  
- *(tidak ada)*

### `backend/experiments/annotate_facts.py` — Alat anotasi presisi fakta SPO: sampling fakta dari JSON hasil eksperimen ke XLSX lalu menghitung presisi ketat/longgar + Wilson CI; CLI subcommand `sample` dan `score` (`--results`, `--n`, `--output`, `--sheet`).
**Fungsi:**  
- `cmd_sample(args)` — Mengambil `phase2_fact_extraction.all_facts` dari JSON hasil eksperimen, mensampling deterministik, menulis XLSX anotasi ke `experiments/results/fact_annotation.xlsx` atau `--output`; tidak memanggil LLM/jaringan.  
- `wilson_ci(successes, n, z=1.96)` — Menghitung interval kepercayaan Wilson 95% untuk proporsi benar; input hitungan sukses/N, output `(low, high)`.  
- `cmd_score(args)` — Membaca XLSX anotasi terisi, menghitung presisi ketat, presisi longgar dengan `partial`, CI Wilson, lalu menulis `fact_precision.json` di folder sheet; tidak memakai LLM/jaringan.  
- `main()` — Parser CLI subcommand `sample`/`score` dan dispatch ke fungsi terkait.

### `backend/experiments/audit_chunks.py` — Auditor kualitas chunk JSONL yang mengukur 10 дефect chunking dan gate bagian-E; CLI `new`, `--baseline`, `--gate`, `--json`.
**Fungsi:**  
- `_looks_non_prose(text)` — Mendeteksi chunk yang memang daftar/tabel/caption/metadata agar tidak disalahhitung sebagai prose cut.  
- `_load(path)` — Membaca JSONL chunk dan meta dari file, mengembalikan `(meta, chunks)`.  
- `_title_of(c)` — Mengambil `paper_title` atau `title` dari satu chunk.  
- `_is_prose_midsentence_cut(text)` — Menilai apakah teks benar-benar prose yang terpotong di tengah kalimat.  
- `_ends_terminal(text)` — Mengecek apakah chunk berakhir tanda terminal `.?!`.  
- `audit(path)` — Menghitung metrik defect: midsentence cut, overlap, bad title, null year, section `other`, reference chunks, artefak ekstraksi, bleed header/footer, duplikasi, chunk quality buruk; tanpa LLM/jaringan.  
- `gate(a)` — Mengevaluasi threshold bagian-E dan mengembalikan daftar failure.  
- `print_report(new, base=None)` — Mencetak tabel before/after audit dan status gate.  
- `main(argv=None)` — CLI untuk audit JSONL, baseline opsional, output JSON mentah, dan exit code gate.

### `backend/experiments/breakdown_analysis.py` — Memecah indikator hasil eksperimen menurut tipe Cooper dan metode deteksi, plus EAR/LCS jika ada form pakar; CLI `--results`, `--expert-form`, `--output`.
**Fungsi:**  
- `load_indicators(results_path)` — Meratakan `phase3_gap_detection.topics[].indicators[]` menjadi list indikator dengan tipe/metode/verdict/confidence.  
- `_norm_type(raw)` — Menormalkan tipe ke `FRAGMENTATION`, `INCONSISTENCY`, `INCOMPLETENESS`, atau `UNKNOWN`.  
- `_norm_verdict(raw)` — Menormalkan verdict ke `PASS`, `FLAG`, `REJECT`, atau `NONE`.  
- `_group_stats(rows, key)` — Menghitung count, mean confidence, dan komposisi verdict per grup.  
- `_load_expert(form_path)` — Memetakan deskripsi indikator ke label pakar dan LCS dari XLSX; tidak memakai jaringan.  
- `_expert_stats(rows, key, expert_map)` — Menghitung EAR dan LCS rata-rata per grup bila form pakar tersedia.  
- `render(results_path, expert_form)` — Menyusun Markdown laporan breakdown; membaca JSON hasil eksperimen dan XLSX opsional.  
- `main()` — CLI yang menulis Markdown ke file keluaran atau `<stem>_breakdown.md`.

### `backend/experiments/build_gap_benchmark.py` — Membangun benchmark gold gap dari section Limitations/Future Work/Conclusion paper, dengan opsi phrasing LLM dan assignment topik embedding; CLI `--papers-dir`, `--max-per-paper`, `--model`, `--no-llm`, `--output`.
**Fungsi:**  
- `_parse_gaps(raw)` — Mengambil array `gaps` dari output JSON LLM yang mungkin dibungkus code fence/preamble.  
- `assign_topic(statement, topic_emb, embed_one)` — Memilih topic key paling mirip lewat cosine embedding; memakai `gap_matching.cosine`.  
- `main()` — Mengiterasi PDF, mengekstrak weakness sections via `DocumentProcessor`, memanggil LLM jika aktif, menulis `gap_benchmark.json` dan XLSX kurasi; ada jaringan/LLM dan embedding model lokal.

### `backend/experiments/build_graph_seed.py` — Membangun seed knowledge graph tanpa LLM dari hasil ingest eksperimen untuk endpoint `/api/graph`; CLI tanpa argumen.
**Fungsi:**  
- `main()` — Mengambil chunk dari vector store eksperimen, mengekstrak fakta berbasis pola dengan `FactExtractor`, menambah fakta ko-occurence, lalu menulis `experiment_graph_seed.json`; tidak memanggil LLM/jaringan.

### `backend/experiments/compare_results.py` — Mengagregasi JSON eksperimen menjadi tabel ablation, perbandingan model, adversarial, dan detail topik; CLI `--results-dir`.
**Fungsi:**  
- `load_reports(results_dir)` — Memuat `experiment_*.json`, menyaring backup/run replika/graph seed dan mode yang bukan mode utama.  
- `fmt(value, suffix="")` — Memformat nilai atau `—` bila `None`.  
- `table_ablation(reports, model_filter=None)` — Menyusun Tabel A ablation per mode dan model, termasuk indikator, fakta, confidence, PASS/RERR, waktu fase-3.  
- `table_model_comparison(reports)` — Menyusun Tabel B perbandingan model pada mode `full`.  
- `table_adversarial(reports)` — Menyusun Tabel C hasil validasi adversarial rule engine dari report penuh pertama yang tersedia.  
- `table_topic_detail(reports, model=None)` — Menyusun Tabel D detail per topik dari mode full.  
- `main()` — CLI yang mencetak daftar hasil eksperimen dan seluruh tabel Markdown.

### `backend/experiments/consensus_gaps.py` — Menggabungkan gap dari beberapa run menjadi union beranotasi k/n dan stable flag; CLI `--inputs`, `--out`, `--min-run-hits`, `--stable-only`.
**Fungsi:**  
- `load_run(path)` — Membaca JSONL gap dan menyaring record meta serta item tanpa `gap_statement`.  
- `consensus_table(gaps, runs)` — Membuat baris distribusi berapa gap muncul di tepat k run.  
- `main(argv=None)` — Memanggil `merge_gap_runs`, menulis `gaps_union.jsonl`, dan menampilkan statistik konsensus; tidak memakai LLM/jaringan.

### `backend/experiments/cross_critic.py` — Debat lintas-model untuk mengkritik indikator gap dan opsional fakta SPO; tidak punya CLI sendiri, dipakai oleh `run_experiment.py`.
**Fungsi:**  
- `_parse_json_array(raw)` — Mem-parsing array JSON dari output LLM yang mungkin dibungkus code fence atau preamble.  
**Kelas:**  
- `CrossCritic` — Menjalankan debat critic vs defender untuk indikator gap dan audit fakta SPO.  
  - `__init__(critic_llm, defender_llm, max_tokens=3500)` — Menyimpan dua LLM dan batas token kritik.  
  - `debate_indicators(topic, indicators, facts_summary="", paper_titles=None)` — Mengkritik setiap indikator dengan prompt terstruktur, lalu memberi peluang pembelaan; output keputusan keep/reject, reason, dan confidence delta; memanggil LLM/jaringan.  
  - `critique_facts(paper_title, facts)` — Meminta critic menandai fakta SPO yang noise; fail-open jika error; memanggil LLM/jaringan.

### `backend/experiments/download_papers.py` — Mengunduh dataset PDF benchmark dari arXiv dan menulis manifest metadata; CLI `--list`.
**Fungsi:**  
- `download_paper(paper)` — Mengunduh satu PDF arXiv ke `research_papers/`, memvalidasi signature PDF, dan mengembalikan sukses/gagal; memakai jaringan.  
- `write_manifest()` — Menulis `research_papers/papers_manifest.json` berisi topik dan status downloaded.  
- `main()` — Menampilkan status dataset, mengunduh paper yang hilang, lalu menulis manifest; memakai jaringan.

### `backend/experiments/error_taxonomy.py` — Membangun taksonomi false discovery dari form pakar, dikrosstab dengan tipe indikator dan metode deteksi; CLI `--forms`, `--results`, `--output`.
**Fungsi:**  
- `_norm_type(raw)` — Menormalkan tipe indikator ke tiga kelas Cooper atau `UNKNOWN`.  
- `load_results_method_map(results_path)` — Memetakan potongan deskripsi indikator ke `detection_method` dari JSON hasil eksperimen.  
- `read_form(form_path, method_map)` — Membaca XLSX penilaian pakar dan mengeluarkan daftar `{label, type, method}`.  
- `render(rows)` — Menyusun laporan Markdown taksonomi error beserta FDR, crosstab jenis error × tipe × metode.  
- `main()` — Menggabungkan semua form, menyimpan `error_taxonomy.md`, lalu mencetaknya; tidak memakai LLM/jaringan.

### `backend/experiments/evaluate_gaps.py` — Mengevaluasi precision/recall/F1 gap detector terhadap gold benchmark gap yang diverifikasi; CLI `--gold`, `--results` (repeatable), `--threshold`, `--model`, `--per-topic`, `--output`.
**Fungsi:**  
- `load_gold(path)` — Membaca gold JSON dan menyaring hanya `verified == true`.  
- `load_detected(path)` — Meratakan indikator terdeteksi dari hasil eksperimen beserta label mode.  
- `get_embedder(model_name)` — Membuat fungsi embedding sentence-transformers; memanggil model lokal, bukan jaringan.  
- `score(detected, gold, embed, threshold, per_topic)` — Menghitung PRF greedy one-to-one untuk satu hasil eksperimen, opsional per topik.  
- `render(all_scores, threshold, n_gold)` — Menyusun Markdown tabel precision/recall/F1, TP/FP/FN, dan ringkasan per topik.  
- `main()` — Menjalankan evaluasi untuk satu atau banyak JSON hasil eksperimen, menulis Markdown + JSON skor.

### `backend/experiments/evaluate_retrieval.py` — Mengukur kualitas retrieval known-item dan reranker cross-encoder dengan MRR/nDCG/Recall/P@k, serta breakdown bahasa; CLI `--n`, `--k`, `--pool`, `--seed`, `--by-language`, `--output`.
**Fungsi:**  
- `detect_language(text)` — Heuristik stop-word untuk menebak bahasa ID/EN/unknown.  
- `build_queries(store, n, seed)` — Menyusun query known-item dari chunk yang sumber paper-nya masih punya ≥3 chunk.  
- `relevances(results, query, k)` — Membuat label relevansi biner berdasar source paper yang sama, mengabaikan chunk query sendiri.  
- `per_query_metrics(rels, n_relevant, k)` — Menghitung MRR, nDCG@k, Recall@k, dan P@k per query.  
- `main()` — Mengambil vector store dan reranker dari app, menjalankan evaluasi, menulis Markdown, lalu mencetak hasil; memakai retrieval infra lokal.

### `backend/experiments/expert_eval/calibration.py` — Mengukur kalibrasi confidence indikator terhadap label pakar (Brier, ECE, MCE, reliability table); CLI `--forms`, `--use-adjusted`, `--bins`, `--output`.
**Fungsi:**  
- `_read_pairs(form_path, use_adjusted)` — Membaca pasangan `(confidence, genuine)` dari XLSX pakar; bisa memakai `adjusted_confidence`.  
- `calibration_metrics(pairs, n_bins=10)` — Menghitung Brier score, ECE, MCE, base rate, dan tabel reliabilitas per bin.  
- `render(metrics, use_adjusted)` — Menyusun laporan Markdown kalibrasi confidence.  
- `main()` — Menggabungkan form pakar, menghitung metrik, dan menulis Markdown + JSON; tidak memakai LLM/jaringan.

### `backend/experiments/expert_eval/compute_metrics.py` — Menghitung metrik evaluasi pakar: EAR, FDR, LCS, AS, SHG, REP, plus Cohen’s kappa antar-rater; CLI `--forms`, `--output`.
**Fungsi:**  
- `read_form(path)` — Membaca sheet `Penilaian` dari XLSX pakar dan mengekstrak kolom yang diperlukan.  
- `compute_rater_metrics(rows)` — Menghitung EAR, FDR, LCS, AS, SHG per topik, REP, dan status dukungan H4/H5 untuk satu rater.  
- `cohens_kappa(labels_a, labels_b)` — Menghitung Cohen’s κ dari dua daftar label pakar.  
- `to_markdown(report)` — Menyusun tabel ringkas BAB IV dari report agregat.  
- `main()` — Menggabungkan satu atau banyak form, menghitung metrik per-rater dan agregat, menulis JSON hasil, lalu mencetak tabel.

### `backend/experiments/expert_eval/generate_form.py` — Membuat XLSX form penilaian pakar dari hasil eksperimen dengan kolom sistem dan kolom input pakar; CLI `--results`, `--output`.
**Fungsi:**  
- `collect_indicators(results_path)` — Mengekstrak indikator dari JSON eksperimen, menghitung rank sistem per topik, dan menyiapkan baris form.  
- `build_workbook(rows, source_name)` — Membuat workbook dua sheet (`Petunjuk` dan `Penilaian`) lengkap dengan validasi dropdown dan format warna.  
- `main()` — Memastikan JSON hasil eksperimen ada, membangun XLSX form, lalu menyimpan ke output; tidak memakai LLM/jaringan.

### `backend/experiments/final_report.py` — Menyusun laporan final pipeline dari audit chunk, gap, stabilitas lintas-run, benchmark Mendeley, novelty, open gaps, dan kandidat judul; CLI `--chunks-new`, `--chunks-old`, `--gaps`, `--out`, `--mendeley`, `--no-llm`.
**Fungsi:**  
- `_fmt(v, unit)` — Memformat angka dengan unit.  
- `_chunking_section(new, old)` — Menulis bagian metrik chunking before/after dan status validation gate.  
- `_gaps_section(gaps)` — Merangkum jumlah gap, jurnal, grounding, tipe, dan topik.  
- `_novelty_section(gaps)` — Merangkum status novelty gap.  
- `_stability_section(gaps, meta)` — Merangkum stabilitas lintas-run k/n dan Jaccard antar-run, jika gap union beranotasi run hits.  
- `_open_gaps_per_topic(gaps)` — Mengelompokkan gap open per topik dan menampilkan kutipan/referensi terbaru.  
- `_candidate_titles(by_topic, use_llm)` — Menghasilkan kandidat judul penelitian per topik via Copilot bila aktif; memanggil LLM/jaringan.  
- `_mendeley_section(path)` — Menyisipkan ringkasan benchmark Mendeley jika JSON tersedia.  
- `main(argv=None)` — Menggabungkan seluruh bagian menjadi satu Markdown final dan menulis file laporan.

### `backend/experiments/gap_benchmark_mendeley.py` — Benchmark gap extraction pada dataset Mendeley: fetch abstrak arXiv, ekstraksi gap, evaluasi similarity dan optional LLM-as-judge; CLI `--dataset`, `--sample`, `--judge`, `--out`.
**Fungsi:**  
- `_fetch_abstract(arxiv_id, max_retries=4)` — Mengambil abstrak dari arXiv API dengan retry/backoff untuk 429/5xx; memakai jaringan.  
- `_similarity_model()` — Memuat sentence-transformers multilingual di CPU untuk perbandingan semantik.  
- `_cos(model, a, b)` — Menghitung cosine similarity embedding dua teks.  
- `_judge(gold, machine)` — Meminta Copilot menilai kecocokan gap 1–5; memakai LLM/jaringan.  
- `run(dataset, sample, use_judge, seed=13, out_path=None)` — Menyampel CSV Mendeley, fetch abstrak, mengekstrak gap, menghitung similarity/judge, menulis JSON opsional; memakai jaringan dan LLM opsional.  
- `main(argv=None)` — Parser CLI yang memanggil `run()`.

### `backend/experiments/gap_matching.py` — Utilitas matching berbasis embedding: cosine, similarity matrix, greedy one-to-one match, dan PRF helper; dipakai oleh evaluasi gap.  
**Fungsi:**  
- `cosine(a, b)` — Menghitung cosine similarity antar vektor.  
- `similarity_matrix(detected, gold)` — Membuat matriks cosine similarity full.  
- `greedy_match(sim, threshold=0.5)` — Mencocokkan pasangan deteksi-gold secara greedy satu-ke-satu di atas threshold.  
- `prf(n_detected, n_gold, tp) -> PRF` — Mengonversi hitungan match menjadi precision, recall, F1, FP, FN.  
- `evaluate(detected_emb, gold_emb, threshold=0.5)` — Menjalankan similarity → greedy match → PRF.  
**Kelas:**  
- `PRF` — Dataclass ringkas metrik precision/recall/F1 dan jumlah TP/FP/FN.  
  - `to_dict()` — Mengubah hasil PRF menjadi dict bulat 3 desimal.

### `backend/experiments/gap_matching.py` — utilitas inti; tidak punya CLI.

### `backend/experiments/recommend_topics.py` — Merekomendasikan topik/judul penelitian dari gap open dengan rumus resmi `rank_proposals`; CLI `--gaps`, `--chunks`, `--out`, `--top`, `--per-topic`, `--top-titles`, `--no-embedder`, `--no-llm`, `--min-run-hits`.
**Fungsi:**  
- `_proposals_from_gaps(gaps)` — Mengubah gap open menjadi proposal topik dengan title/description/how dan metadata asal.  
- `_run_hits(g)` — Menghitung kemunculan lintas run; gap tanpa anotasi dianggap 1.  
- `_kn(p)` — Memformat label k/n stabilitas untuk laporan.  
- `_corpus_from_chunks(chunks)` — Mengagregasi chunk menjadi satu entri per paper untuk basis novelty-vs-corpus.  
- `_gap_confidences(gaps)` — Menyiapkan confidence per gap untuk `rank_proposals`.  
- `_load_embedder(disabled)` — Memuat embedder multilingual lokal atau mengembalikan `None` bila dimatikan/gagal.  
- `main(argv=None)` — Membaca gap union dan chunk corpus, memfilter open gap, memberi ranking, menulis Markdown, dan opsional meminta Copilot merumuskan judul; memakai embedding lokal dan LLM opsional.

### `backend/experiments/retrieval_metrics.py` — Fungsi metrik retrieval dasar: MRR, Recall@k, Precision@k, nDCG, dan agregasi per query; tanpa CLI.
**Fungsi:**  
- `reciprocal_rank(rels)` — Mengembalikan RR dari daftar relevansi biner.  
- `recall_at_k(rels, total_relevant, k)` — Menghitung recall@k.  
- `precision_at_k(rels, k)` — Menghitung precision@k.  
- `dcg_at_k(rels, k)` — Menghitung Discounted Cumulative Gain.  
- `ndcg_at_k(rels, total_relevant, k)` — Menghitung nDCG@k.  
- `aggregate(per_query)` — Mengagregasi metrik per query menjadi rata-rata yang dibulatkan 3 desimal.

### `backend/experiments/run_experiment.py` — Runner utama eksperimen neuro-symbolic dengan ablation mode; jalankan dari `backend/` via `python experiments/run_experiment.py --mode {full,no-rule-engine,linear-baseline,nli,no-nli,cross-critic} --model ... --topics ... --fresh-db --skip-ingest --seed ... --critic-model ... --critic-facts --negative-control --output ...`.
**Fungsi:**  
- `seed_python_rngs(seed)` — Menyemai RNG Python dan NumPy agar sampling/bootstrapping repeatable.  
- `_sha256_file(path)` — Menghitung hash SHA-256 artifact lokal untuk provenance.  
- `_git_value(*args)` — Mengambil nilai git (commit/status) secara non-fatal.  
- `capture_experiment_provenance(model_name, seed, config)` — Mengumpulkan provenance tak-sensitif: commit, dirty flag, hash config/requirements/manifest, versi dependensi, hash model, daftar PDF; tanpa LLM/jaringan kecuali cek tag Ollama.  
- `load_topics(topic_filter=None, custom_topics=None)` — Membaca topik dari manifest atau default, memfilter/menambah custom/negative-control topics.  
- `init_components(model_name=None, mode="full", fresh_db=False, use_nli=False, critic_model=None, critic_facts=False)` — Menginisialisasi vector store, LLM, fact table, fact extractor, rule engine, NLI, relation classifier, KG builder, doc processor, gap analyzer, dan cross-critic sesuai mode; memakai LLM/jaringan saat instantiate model.  
- `phase1_ingest_papers(components)` — Mengekstrak PDF ke chunk dan memasukkannya ke vector store, mengembalikan ringkasan ingest.  
- `phase2_fact_extraction(components, papers_data)` — Mengekstrak fakta SPO dari paper, menyimpan `all_facts` terurai, dan bila mode cross-critic+`critic_facts` aktif melakukan audit fakta noise dengan critic lalu menghapus fakta buruk.  
- `phase3_gap_detection(components, topics)` — Menjalankan gap analyzer per topik, opsional debat cross-critic pada indikator, lalu menyusun metrik per topik dan confidence scores; memakai LLM/jaringan.  
- `phase3_linear_baseline(components, topics)` — Menjalankan baseline RAG+LLM satu prompt tanpa fact base/rule engine, lalu mem-parsing gap JSON hasil model; memakai LLM/jaringan.  
- `phase4_rule_engine_analysis(components, gap_results)` — Mengagregasi verdict rule engine PASS/FLAG/REJECT dari gap hasil fase 3 dan menghitung pass/flag/reject rate.  
- `_build_adversarial_fact_table() -> FactTable` — Membangun fact table terisolasi berisi fakta buatan untuk memicu rule tertentu pada validasi adversarial.  
- `phase5_adversarial_validation()` — Menguji rule engine pada kasus adversarial F1/F2/F3/K1/C1 dan kontrol PASS, lalu menghitung akurasi verdict.  
- `compile_results(phase1, phase2, phase3, phase4, phase5, mode, model_name, topics, seed, provenance=None, critic_model=None)` — Menggabungkan seluruh fase menjadi JSON report final, menghitung overall metrics, negative-control metrics, dan statistik debat cross-critic; tidak memanggil LLM langsung.  
- `main()` — Parser CLI runner utama, cek koneksi Ollama, inisialisasi komponen, menjalankan fase sesuai mode, menyimpan JSON hasil eksperimen ke `experiments/results/`.

### `backend/experiments/run_multi.py` — Wrapper multi-run untuk menjalankan konfigurasi berkali-kali, menghitung mean±std, Mann-Whitney U, Holm-Bonferroni, dan effect size/CI; CLI `--model`, `--runs`, `--seed`, `--modes`, `--negative-control`, `--skip-runs`.
**Fungsi:**  
- `run_name(mode, model, run_idx)` — Membuat nama file JSON hasil multi-run per mode/model/run.  
- `execute_runs(model, runs, modes, base_seed, negative_control=False)` — Menjalankan `run_experiment.py` untuk semua kombinasi mode×run; memanggil subprocess dan mengeksekusi eksperimen nyata.  
- `collect_metrics(model, runs, modes)` — Memuat hasil tiap run dan mengekstrak indikator, confidence, fakta, RERR, serta false-gap control.  
- `mean_std(values)` — Memformat mean ± std atau satu nilai tunggal.  
- `mwu(sample_a, sample_b)` — Menghitung Mann-Whitney U dua sisi bila data cukup dan tidak identik.  
- `_comparison_rows(data, exploratory=False)` — Menyusun baris uji signifikansi primer atau eksploratori untuk pasangan mode tertentu.  
- `_format_test_rows(rows)` — Merender baris uji menjadi tabel Markdown termasuk effect size dan CI.  
- `aggregate(model, data)` — Menyusun laporan multi-run lengkap: ringkasan per mode, kontrol negatif, uji primer, uji eksploratori, dan catatan effect size/CI.  
- `main()` — Parser CLI yang opsional menjalankan ulang eksperimen, mengagregasi hasil, dan menulis Markdown statistik ke `results/multirun_stats_<model>.md`.

### `backend/experiments/stats_utils.py` — Helper statistik nonparametrik untuk multi-run: koreksi p-value, effect size, bootstrap CI, dan formatting; tanpa CLI.
**Fungsi:**  
- `holm_bonferroni(pvalues)` — Menghitung p-value terkoreksi Holm-Bonferroni dalam urutan asli.  
- `per_run_mean_confidences(runs)` — Merangkum confidence indikator menjadi mean per run untuk menghindari pseudo-replication.  
- `cliffs_delta(a, b)` — Menghitung Cliff’s delta beserta magnitude effect size.  
- `rank_biserial_from_u(u, n1, n2)` — Menghitung rank-biserial correlation dari statistik U Mann-Whitney.  
- `bootstrap_ci_diff(a, b, stat=statistics.median, n_boot=5000, alpha=0.05, seed=42)` — Menghitung selisih statistik beserta CI bootstrap percentile; default median.  
- `format_effect(a, b, u=None)` — Merangkum Cliff’s delta, rank-biserial, dan CI bootstrap menjadi string Markdown ringkas.

### `backend/experiments/verify_gaps.py` — Mengecek bahwa setiap `gap_statement` benar-benar verbatim-grounded di source chunks dan menghitung gaps eksplisit yang lolos regex lama; CLI `--gaps`, `--chunks`, `--threshold`.
**Fungsi:**  
- `main(argv=None)` — Memuat gap dan chunk JSONL, menghitung skor verifikasi per gap, melaporkan persentase verbatim-verified dan explicit gaps yang dulu terlewat regex; tidak memakai LLM/jaringan.

### `backend/experiments/build_gap_benchmark.py`, `download_papers.py`, `evaluate_gaps.py`, `evaluate_retrieval.py`, `compare_results.py`, `consensus_gaps.py`, `breakdown_analysis.py`, `final_report.py`, `gap_matching.py`, `gap_benchmark_mendeley.py`, `recommend_topics.py`, `run_experiment.py`, `run_multi.py`, `stats_utils.py`, `verify_gaps.py`, `annotate_facts.py`, `audit_chunks.py`, `error_taxonomy.py`, `build_graph_seed.py`, `expert_eval/*` — seluruh skrip di area ini berfokus pada pipeline evaluasi/eksperimen tesis, dari ingest PDF, ekstraksi fakta/gap, audit kualitas chunk, benchmark gold, validasi pakar, hingga statistik multi-run dan laporan final.

**Alur utama eksperimen:**  
- `download_papers.py` → mengunduh PDF benchmark ke `research_papers/` dan menulis `papers_manifest.json`.  
- `run_experiment.py` → ingest PDF ke vector store, ekstraksi fakta SPO, deteksi gap, rule engine, adversarial validation, lalu menulis `experiments/results/experiment_*.json`.  
- `annotate_facts.py` / `expert_eval/generate_form.py` → menyiapkan form XLSX untuk anotasi pakar dari JSON hasil eksperimen.  
- `expert_eval/compute_metrics.py` / `expert_eval/calibration.py` / `breakdown_analysis.py` / `error_taxonomy.py` → menghitung EAR, LCS, AS, SHG, REP, Cohen’s κ, kalibrasi confidence, dan taksonomi false discovery dari form pakar.  
- `audit_chunks.py` / `verify_gaps.py` / `build_gap_benchmark.py` / `evaluate_gaps.py` → memvalidasi kualitas chunk, verifikasi verbatim gap, membangun gold benchmark, lalu mengukur precision/recall/F1 terhadap gold.  
- `consensus_gaps.py` → menggabungkan beberapa run gap mining menjadi union k/n yang stabil.  
- `recommend_topics.py` / `final_report.py` / `compare_results.py` → merangkum gap open menjadi rekomendasi topik, menyusun laporan akhir, dan membandingkan mode/model.  
- `run_multi.py` / `stats_utils.py` → menjalankan multi-run dan uji signifikansi statistik untuk mendukung klaim H6/H7/H9/H10.  
- `build_graph_seed.py` → menyiapkan seed knowledge graph untuk demo endpoint graph tanpa LLM.  

## Tambahan — fungsi bersarang (nested)

### `backend/experiments/audit_chunks.py`
- `_is_body_prose(c) -> bool` — bersarang di `audit`; menyaring chunk isi (bukan referensi; untuk skema v2 juga bukan `section_normalized` `other`/`references`) sebelum menghitung metrik potongan kalimat tengah (`mid-sentence cut`).

### `backend/experiments/expert_eval/compute_metrics.py`
- `avg(key)` — bersarang di `main`; rata-rata (dibulatkan 2 desimal) sebuah metrik (`EAR_percent`, `LCS_mean`, `FDR_percent`, …) lintas penilai valid, mengabaikan `None`.

### `backend/experiments/run_experiment.py`
- `_is_control(t) -> bool` — bersarang di `compile_results`; menandai topik kontrol negatif (kunci topik berawalan `TC`) agar dipisahkan dari topik utama saat merangkum hasil fase 3.


<a id="bagian-07"></a>
# Bagian 07 — tools/process_monitor (UI Streamlit), flood-geoai-research, generate_paper_figures, Makefile

## tools/process_monitor/

### `tools/process_monitor/app.py` — titik masuk Streamlit utama yang merutekan pengguna ke wizard, pipeline penelitian, dan halaman detail teknis.
**Fungsi:**
- `st.set_page_config(...)` — mengatur judul, ikon, dan layout aplikasi.
- `st.navigation(pages).run()` — menjalankan navigasi multipage Streamlit berdasarkan grup halaman di sidebar.

### `tools/process_monitor/common.py` — klien HTTP ke backend FastAPI, helper format tanggal/durasi, dan renderer untuk berbagai hasil pipeline lama.
**Fungsi:**
- `api_base() -> str` — mengembalikan base URL backend dari session state atau default.
- `_get_json(path: str, params: dict | None = None, timeout: int = 15)` — helper GET JSON ke backend dengan penanganan error.
- `fetch_chunk_export(job_id: str, fmt: str = "jsonl") -> tuple[bytes | None, str | None]` — mengambil ekspor chunk dari backend untuk diunduh.
- `fetch_status(job_id: str) -> dict | None` — mengambil status satu job analisis.
- `fetch_events(job_id: str) -> dict | None` — mengambil event log satu job.
- `fetch_artifacts(job_id: str) -> dict | None` — mengambil artefak job dari backend.
- `fetch_system_stats() -> dict | None` — mengambil statistik server/Resource.
- `fetch_jobs(limit: int = 30) -> list[dict]` — mengambil daftar job analisis terbaru.
- `upload_and_analyze(files) -> str | None` — mengunggah PDF lalu memulai analisis lama 8 tahap, mengembalikan job_id.
- `delete_job(job_id: str) -> bool` — menghapus job dari backend.
- `cancel_job(job_id: str) -> bool` — membatalkan job yang sedang antre/berjalan.
- `reanalyze_job(job_id: str) -> str | None` — membuat job baru untuk analisis ulang PDF yang sama.
- `derive_stage_states(events: list[dict], job_status: str) -> dict[str, dict]` — menurunkan status tiap tahap dari event.
- `derive_file_rows(events: list[dict]) -> list[dict]` — membuat ringkasan per file dari event.
- `group_artifacts(artifacts: list[dict]) -> dict[str, dict]` — mengelompokkan artefak berdasarkan tahap/jenis.
- `fmt_duration(ms) -> str` — memformat milidetik menjadi durasi manusiawi.
- `fmt_clock(epoch) -> str` — memformat waktu epoch ke jam-menit-detik.
- `fmt_datetime(epoch) -> str` — memformat epoch menjadi tanggal/waktu lengkap.
- `fmt_gb(mb) -> str` — memformat megabyte ke gigabyte.
- `md_bold(text) -> str` — membungkus teks menjadi bold Markdown.
- `render_server_panel() -> None` — menampilkan panel status server dan resource.
- `_render_extraction_results(extractions: list[dict]) -> None` — merender hasil ekstraksi per berkas PDF.
- `_render_topics_result(payload: dict) -> None` — merender hasil topik dari payload hasil.
- `_first_weak_point(weak: dict) -> str` — mengambil ringkasan titik lemah pertama dari data weakness.
- `_render_weak_points(weak: dict) -> None` — menampilkan poin kekurangan tersurat/tersirat per jurnal.
- `_render_paper_analysis_result(payload: dict, key: str = "stage") -> None` — merender hasil analisis per jurnal.
- `_render_neuro_symbolic_result(payload: dict) -> None` — merender hasil tahap neuro-symbolic.
- `_render_summary_result(payload: dict) -> None` — merender ringkasan hasil job.
- `_miles_lens(gap: dict) -> list[str]` — mengekstrak lensa/atribut gap ala Miles.
- `_gap_year_span(gap: dict, papers_info: list) -> tuple[int, int, int] | None` — menghitung rentang tahun gap dari metadata paper.
- `render_gap_confidence(gap: dict) -> None` — menampilkan keyakinan/verbatim confidence gap.
- `_render_gap_lenses(gap: dict, papers_info: list) -> None` — merender lensa-lensa penjelas gap.
- `_stage_matrix(gap: dict) -> dict` — menyusun matriks status lintas tahap untuk satu gap.
- `_sub_dict(gap: dict, key: str) -> dict` — helper mengambil sub-dict dari gap.
- `render_coverage_map(gap: dict) -> None` — menampilkan peta cakupan/evidence gap.
- `_short_src(name, limit: int = 34) -> str` — memendekkan nama sumber.
- `render_bibliographic_coupling(gap: dict) -> None` — menampilkan kopling bibliografis antar jurnal.
- `render_stage_matrix(gap: dict) -> None` — menampilkan matriks status per tahap untuk gap.
- `render_author_corroboration(gap: dict) -> None` — menampilkan korroborasi/dukungan penulis.
- `_render_gaps_result(payload: dict) -> None` — merender ringkasan hasil gap penelitian.
- `render_gap_method_explainer() -> None` — menjelaskan metode deteksi gap ke pengguna.
- `render_novelty_badge(rec: dict) -> None` — menampilkan badge kebaruan untuk proposal.
- `render_method_layer_status(results: dict) -> None` — menampilkan status lapisan metode/algoritme.
- `_render_proposal_result(payload: dict) -> None` — merender hasil usulan penelitian.
- `_render_roadmap_result(payload: dict) -> None` — merender hasil peta jalan penelitian.
- `_render_llm_traces(traces: list[dict]) -> None` — menampilkan jejak LLM per langkah.
- `fetch_graph(base: str, job_id: str, max_nodes: int) -> dict | None` — mengambil snapshot graf pengetahuan.
- `_build_graph_html(nodes: list, links: list) -> str` — membangun HTML graf interaktif.
- `render_knowledge_graph(job_id: str) -> None` — menampilkan knowledge graph job yang selesai.

### `tools/process_monitor/export_bundle.py` — membangun satu berkas Markdown “paket agen” dari hasil job agar mudah dibaca/diumpankan ke AI.
**Fungsi:**
- `_txt(value: Any) -> str` — menormalkan nilai menjadi teks aman.
- `_block(value: Any) -> str` — memformat nilai sebagai blok teks Markdown.
- `_cell(value: Any) -> str` — memformat nilai sebagai isi sel tabel.
- `_demote_headings(text: str, min_level: int) -> str` — menurunkan level heading agar struktur Markdown rapi.
- `_yaml_str(value: Any) -> str` — memformat nilai sebagai string YAML.
- `_pct(value: Any) -> str` — memformat angka menjadi persen.
- `_num(value: Any, digits: int = 4) -> str` — memformat angka dengan presisi tertentu.
- `_ts(value: Any) -> str` — memformat timestamp.
- `_duration(status: dict) -> str` — menghitung durasi job dari status.
- `_indicator_counts(gaps: list[dict]) -> dict[str, int]` — menghitung jumlah gap per jenis indikator.
- `_front_matter(job_id: str, status: dict, results: dict) -> list[str]` — menyusun YAML front-matter.
- `_how_to_read(results: dict) -> list[str]` — memberi petunjuk membaca bundel.
- `_corpus_section(results: dict) -> list[str]` — menyusun bagian korpus/jurnal.
- `_summary_section(results: dict) -> list[str]` — menyusun bagian ringkasan.
- `_method_status_section(results: dict) -> list[str]` — menyusun status metode/lapisan.
- `_gap_section(results: dict) -> list[str]` — menyusun bagian gap.
- `_recommendation_section(results: dict) -> list[str]` — menyusun bagian rekomendasi.
- `_roadmap_section(results: dict) -> list[str]` — menyusun bagian roadmap.
- `_knowledge_section(results: dict) -> list[str]` — menyusun bagian knowledge graph.
- `_weakness_section(results: dict) -> list[str]` — menyusun bagian kekurangan per jurnal.
- `_metrics_section(results: dict) -> list[str]` — menyusun bagian metrik.
- `_trace_section(results: dict) -> list[str]` — menyusun bagian jejak/pembuktian.
- `_limitations_section(results: dict) -> list[str]` — menyusun bagian keterbatasan.
- `build_agent_bundle_md(job_id: str, status: dict, results: dict) -> str` — merakit seluruh hasil job menjadi satu Markdown.
- `_cli() -> int` — entry point CLI untuk menulis bundle ke stdout/file.

### `tools/process_monitor/page_analysis.py` — halaman lama “Proses & Hasil” untuk memantau job pipeline 8 tahap, melihat ringkasan, hasil akhir, ekspor chunk, dan knowledge graph.
**Fungsi:**
- `_label(job_id: str, jobs: list[dict]) -> str` — membuat label selectbox job yang berisi status, waktu, dan jumlah berkas.
- `build_agent_bundle_md(...)` dipanggil dari `export_bundle.py` — membentuk paket Markdown yang bisa diunduh.
- `render_method_layer_status(results: dict)` — menampilkan status lapisan metode pada tab ringkasan.
- `_render_paper_analysis_result(...)`, `_render_gaps_result(...)`, `_render_topics_result(...)`, `_render_proposal_result(...)`, `_render_roadmap_result(...)`, `_render_llm_traces(...)` — merender tab-tab hasil per tahap (detail di `common.py`).

### `tools/process_monitor/page_dashboard.py` — dashboard ringkasan riwayat job, aksi ulang/hapus/batalkan, dan panel resource server.
**Fungsi:**
- `_label(jid: str) -> str` — label ringkas untuk memilih job dari dropdown.
- `render_server_panel() -> None` — menampilkan penggunaan CPU/RAM/GPU.
- `cancel_job(job_id: str) -> bool` — membatalkan job berjalan/antre.
- `reanalyze_job(job_id: str) -> str | None` — menjalankan ulang analisis sebagai job baru.
- `delete_job(job_id: str) -> bool` — menghapus job beserta riwayatnya.

### `tools/process_monitor/page_events.py` — halaman log event mentah per job, dipakai untuk audit durasi dan error.
**Fungsi:**
- `_label(jid: str) -> str` — label dropdown job.
- `fetch_events(job_id: str)` — mengambil event log job.
- `fmt_clock(epoch) -> str` — memformat waktu event.
- `fmt_datetime(epoch) -> str` — memformat waktu job.
- `fmt_duration(ms) -> str` — memformat durasi event.
- `st.rerun()`/auto-refresh — memperbarui log saat job masih berjalan.

### `tools/process_monitor/page_followup.py` — halaman tindak lanjut gap yang memilih satu gap, menampilkan usulan yang menjawabnya, roadmap, dan ekspor Markdown.
**Fungsi:**
- `_label(jid: str) -> str` — label job di selectbox.
- `_short(text, limit: int = 90) -> str` — memendekkan teks untuk tampilan.
- `_gap_label(i: int) -> str` — label pilihan gap di selectbox.
- `_followup_md() -> str` — menyusun Markdown paket tindak lanjut gap terpilih.
- `render_gap_confidence(gap: dict) -> None` — menampilkan keyakinan gap.
- `_render_gap_lenses(gap: dict, papers_info: list)` — menampilkan lensa gap.
- `render_gap_method_explainer() -> None` — menjelaskan metode pembentukan gap.
- `render_novelty_badge(rec: dict) -> None` — menampilkan badge kebaruan usulan.
- `st.switch_page("page_skills.py")` — memindahkan pengguna ke halaman Skill Riset dengan ide terisi.

### `tools/process_monitor/page_journals.py` — halaman baca per jurnal untuk melihat kekurangan tersurat/tersirat dan gap kolektif yang terkait.
**Fungsi:**
- `_label(jid: str) -> str` — label job.
- `_norm(text) -> str` — menormalkan teks untuk pencocokan.
- `_gaps_for(weak: dict) -> list[tuple[int, dict]]` — mencari gap kolektif yang menyebut jurnal ini.
- `_render_weak_points(weak: dict)` — merender kekurangan tersurat/tersirat per jurnal.
- `md_bold(text) -> str` — memformat teks tebal.
- `fetch_status(job_id: str)` — mengambil status/results job.
- `fetch_jobs(limit: int = 30)` — mengambil daftar job selesai.
- `fmt_datetime(epoch) -> str` — memformat waktu.
- `GAP_TYPE_BADGES`/`JOB_STATUS_BADGES` dipakai untuk penandaan status dan jenis gap.

### `tools/process_monitor/page_method.py` — halaman metode & uji coba yang memetakan metode proposal ke komponen sistem dan menampilkan hasil eksperimen ablasi/adversarial.
**Fungsi:**
- `load_experiment_runs() -> pd.DataFrame` — memuat semua JSON eksperimen ke DataFrame.
- `load_adversarial_cases() -> tuple[str, list[dict]]` — mengambil kasus uji adversarial dari run full terbaru.
- `_fmt_mean_std(series: pd.Series) -> str` — memformat rata-rata ± simpangan baku.
- `fetch_jobs(limit: int = 30)` — dipakai untuk lompat ke job terbaru.
- `st.switch_page("page_analysis.py")` — membuka job contoh nyata dari hasil analisis.

### `tools/process_monitor/page_research_compare.py` — halaman membandingkan dua job penelitian, baik angka per tahap maupun irisan gap antar run.
**Fungsi:**
- `_label(j: dict) -> str` — label job yang dapat dipilih.
- `_norm(s: str | None) -> str` — menormalkan kalimat gap untuk perbandingan.
- `_gap_set(job_id: str) -> dict[tuple[str, str], dict]` — membangun set gap unik per jurnal+kalimat.
- `_list(keys, pool)` — menampilkan daftar gap pada tab sama/hanya-A/hanya-B.
- `fetch_stages()` — mengambil definisi tahapan pipeline.
- `job_events(job_id: str)` — mengambil event job.
- `stage_result_payload(job_id: str, stage_key: str)` — mengambil payload hasil per tahap.
- `stage_states(job_id: str, events: list[dict])` — menghitung durasi/status tahap.

### `tools/process_monitor/page_research_raw.py` — halaman log & artefak mentah untuk audit event dan payload tahap penelitian.
**Fungsi:**
- `require_job() -> str | None` — mengambil job aktif dari session/URL.
- `fetch_events(job_id: str)` — mengambil event job.
- `fetch_artifacts(job_id: str)` — mengambil artefak job.
- `fmt_clock(epoch) -> str` — memformat waktu event.
- `fmt_duration(ms) -> str` — memformat durasi.

### `tools/process_monitor/page_research_source.py` — halaman teks sumber jurnal; menampilkan chunk PDF yang benar-benar dibaca sistem.
**Fungsi:**
- `require_job() -> str | None` — memastikan ada job aktif.
- `render_timeline(job_id: str) -> None` — menampilkan status ringkas empat tahap.
- `fetch_fulltext(job_id: str, source: str = "") -> dict` — mengambil teks full per jurnal atau daftar jurnal dalam job.

### `tools/process_monitor/page_research_wizard.py` — halaman analisis penelitian (pipeline 4 tahap) yang menyatukan upload, monitor live, dan pembacaan hasil per tahap.
**Fungsi:**
- `_label(job_id: str, jobs: list[dict]) -> str` — label job aktif.
- `fetch_stages() -> list[dict]` — mengambil definisi tahapan.
- `research_jobs(limit: int = 30) -> list[dict]` — mengambil job pipeline penelitian.
- `fetch_status(job_id: str)` — mengambil status job aktif.
- `job_events(job_id: str)` — mengambil event job aktif.
- `render_timeline(job_id: str)` — menampilkan ringkasan status tahap.
- `render_overview_charts(...)` — menampilkan ikhtisar grafik pipeline.
- `render_journal_crosstab(job_id: str)` — membuka tabel silang jurnal.
- `render_theme_browser(job_id: str)` — membuka penjelajah tema.
- `render_stage_body(...)` — merender isi tiap tahap pipeline.
- `cancel_job(job_id: str)` — membatalkan job aktif.

### `tools/process_monitor/page_skills.py` — halaman pustaka “Skill Riset” untuk membantu menyusun ide penelitian menjadi metode, langkah, dan narasi yang siap dipakai.
**Fungsi:**
- `recommend(idea: str) -> dict | None` — menghasilkan rekomendasi struktur/metode dari ide pengguna.
- `_esc(s: str) -> str` — escape teks untuk tampilan/Markdown.
- `_norm_steps(raw) -> list[dict]` — menormalkan langkah-langkah dari output rekomendasi.
- `_dot_from_methodology(steps: list[dict]) -> str` — membangun graphviz dari metodologi.
- `_listify(raw) -> list[str]` — menormalkan nilai menjadi list string.

### `tools/process_monitor/page_wizard.py` — wizard 4 langkah dari PDF ke judul penelitian; menjadi entry point utama bagi pengguna.
**Kelas:**
- `_StoredUpload` — menyimpan salinan file upload agar tetap ada saat pindah halaman.
  - `__init__(name, data)` — menyimpan nama berkas dan bytes.
  - `getvalue()` — mengembalikan bytes asli berkas.
**Fungsi:**
- `_remember_uploads(files) -> list` — menyimpan upload di session state atau mengambil upload yang sudah tersimpan.
- `render_summary(item: dict) -> None` — menampilkan ringkasan jurnal hasil chunking.
- `chunk_heading(c: dict) -> str` — membuat judul ringkas untuk satu chunk.
- `render_chunk_card(c: dict) -> None` — menampilkan satu chunk sebagai kartu baca.
- `render_chunks(item: dict, key: str) -> None` — menyaring, menelusuri, dan mengunduh chunk per jurnal.
- `backend_alive(api_base: str) -> bool` — mengecek backend FastAPI hidup.
- `request_chunks(api_base: str, uploads, ocr_mode: str) -> dict` — memanggil endpoint preview chunk tanpa membuat job.
- `step2_gaps.render(...)` — menjalankan langkah 2 pencarian gap via LLM.
- `step3_neuro.render(...)` — menjalankan langkah 3 indikator synthesis gap neuro-symbolic.
- `step4_titles.render(...)` — menjalankan langkah 4 rekomendasi judul/topik.
- `time.sleep(POLL_SECONDS)` + `st.rerun()` — polling bersama saat salah satu job masih berjalan.

### `tools/process_monitor/research_charts.py` — grafik Altair untuk corong angka, distribusi, dan perbandingan tahap penelitian.
**Fungsi:**
- `_short(name: str | None) -> str` — memendekkan nama jurnal pada sumbu grafik.
- `_enum_col(df: pd.DataFrame, field: str) -> pd.Series` — mengubah nilai enum menjadi label awam/teknis.
- `_bar(...) -> alt.Chart` — membangun grafik batang umum.
- `_hist(...) -> alt.Chart` — membangun histogram umum.
- `_show(chart: alt.Chart, caption: str = "") -> None` — merender chart dan caption.
- `render_stage_charts(job_id: str, stage_key: str, events: list[dict]) -> None` — memilih grafik sesuai tahap dan menambah chart durasi sub-langkah.
- `_charts_chunking(job_id: str) -> None` — grafik distribusi ukuran chunk dan sebaran bagian jurnal.
- `_charts_gap_mining(job_id: str) -> None` — grafik kandidat, gap final, dan alasan chunk dipilih.
- `_charts_novelty(job_id: str) -> None` — grafik status kebaruan dan paper terkait.
- `_charts_recommendation(job_id: str) -> None` — grafik skor prioritas, novelty vs actionability, dan tema.
- `_durations_chart(events: list[dict], stage_key: str) -> None` — grafik durasi per sub-langkah.
- `render_overview_charts(stages: list[dict], payloads: dict[str, dict], events: list[dict]) -> None` — corong lintas tahap + durasi tahap.

### `tools/process_monitor/research_common.py` — helper bersama untuk pipeline penelitian 4 tahap: akses backend, status tahap, tabel silang, source code tahap, dan rendering record lengkap.
**Fungsi:**
- `fetch_stages() -> list[dict]` — mengambil definisi tahap dari backend atau fallback lokal.
- `start_research(files) -> str | None` — mengunggah PDF dan memulai job pipeline penelitian.
- `research_jobs(limit: int = 30) -> list[dict]` — mengambil job pipeline penelitian saja.
- `job_events(job_id: str) -> list[dict]` — mengambil event job, mengembalikan list kosong jika backend tidak terjangkau.
- `stage_states(job_id: str, events: list[dict] | None = None) -> dict[str, dict]` — menurunkan status tiap tahap dari event phase.*.
- `substep_states(events: list[dict], phase: str) -> dict[str, dict]` — menurunkan status sub-langkah per tahap.
- `stage_artifacts(job_id: str, phase: str) -> dict[str, list[dict]]` — mengelompokkan artefak hasil per jenis.
- `fetch_records(job_id: str, phase: str, q: str = "", filters: dict | None = None, offset: int = 0, limit: int = 25) -> dict` — mengambil data lengkap record per tahap dengan filter/pencarian.
- `fetch_all_records(job_id: str, collection: str, max_rows: int = 5000) -> list[dict]` — mem-paginasi seluruh record satu koleksi.
- `collection_available(job_id: str, collection: str) -> bool` — mengecek apakah koleksi tersedia pada job.
- `fetch_stage_source(stage_key: str) -> dict` — mengambil source code tahap yang benar-benar dieksekusi backend.
- `fetch_fulltext(job_id: str, source: str = "") -> dict` — mengambil fulltext jurnal/chunk job.
- `set_active_job(job_id: str) -> None` — menyimpan job aktif di session state dan query param.
- `require_job() -> str | None` — mengambil job aktif dari session/URL atau menampilkan petunjuk.
- `render_timeline(job_id: str) -> None` — menampilkan ringkasan status keempat tahap.
- `_render_table(rows: list[dict], caption: str = "") -> None` — merender tabel jika ada isi.
- `_render_metrics(metrics: dict[str, Any]) -> None` — merender metrik skalar dan tabel untuk metrik nested.
- `_display_value(field: str, value: Any) -> str` — mengubah value enum menjadi label tampilan.
- `_render_record(rec: dict) -> None` — merender satu record lengkap; field panjang jadi blok teks.
- `render_records_tab(job_id: str, phase: str, trace=None) -> None` — tab data lengkap per tahap dengan pencarian/filter/paginasi.
- `render_source_tab(stage_key: str, substeps: list[dict] | None = None) -> None` — tab source code tahap dan fungsi yang mengimplementasikannya.
- `stage_result_payload(job_id: str, stage_key: str) -> tuple[dict, dict]` — mengambil artefak per jenis dan payload result terakhir.
- `render_stage_extras(arts: dict, payload: dict) -> None` — merender parameter, rincian berkas, prompt LLM, catatan, dan output.
- `render_metrics_grid(metrics: dict[str, Any]) -> None` — alias rendering metrik.
  
### `tools/process_monitor/research_explorer.py` — penjelajah jejak kandidat, tema, dan narasi judul yang dibentuk dari hasil pipeline.
**Fungsi:**
- `reason_label(reason: str | None) -> str` — menerjemahkan alasan pemilihan chunk menjadi label awam.
- `render_candidate_trace(job_id: str) -> None` — menampilkan rantai chunk → LLM → gap → verifikasi untuk kandidat.
- `_llm_prompts_by_chunk(job_id: str) -> dict[str, dict]` — mengindeks prompt/balasan LLM berdasarkan chunk_id.
- `_render_one_candidate(job_id: str, c: dict, prompt: dict | None) -> None` — merender detail satu kandidat.
- `_find_chunk(job_id: str, chunk_id: str | None) -> dict | None` — mencari chunk sumber di koleksi chunking.
- `render_theme_browser(job_id: str) -> None` — menampilkan tema, dukungan jurnal, dan anggota proposal.
- `render_title_narration(job_id: str) -> None` — menampilkan narasi judul siap-pakai yang ditulis LLM.

### `tools/process_monitor/research_flow.py` — visualisasi alur, checklist, dan trace per tahap/sub-langkah pipeline penelitian.
**Fungsi:**
- `stage_constants(stage_key: str) -> dict` — mengambil konstanta/metadata tahap.
- `_num(metrics: dict, key: str | None)` — helper membaca angka metrik.
- `_funnel_line(sub: dict, metrics: dict, live: dict | None = None) -> str` — membangun teks corong untuk sub-langkah.
- `_sub_title(sub: dict) -> str` — memilih judul sub-langkah awam/teknis.
- `render_live_map(job_id: str, events: list[dict], status: dict) -> None` — menampilkan peta live progres tahap.
- `_render_substep_checklist(...) -> None` — merender checklist sub-langkah.
- `render_activity_log(events: list[dict], status: dict, stages: list[dict], ...) -> None` — merender log aktivitas pipeline.
- `_clock(epoch) -> str` — memformat waktu event.
- `_describe_event(ev: dict, titles: dict, sub_labels: dict) -> str | None` — menjelaskan event menjadi teks ringkas.
- `estimate_stage_durations(api_base: str, max_jobs: int = 5) -> dict[str, int]` — mengestimasi durasi tahap dari job sebelumnya.
- `render_stage_body(job_id: str, stage: dict, events: list[dict]) -> None` — merender isi tab satu tahap.
- `render_stage_flow(job_id: str, stage: dict, payload: dict, events: list[dict]) -> None` — merender flow/detail tahap.
- `_render_substep_samples(sub: dict, samples: dict, recorded: bool, metrics: dict) -> None` — menampilkan sampel sub-langkah.
- `_render_sample_row(row: dict) -> None` — merender satu baris sampel.
- `_md_escape(text: str) -> str` — escape Markdown.
- `_highlight(haystack: str, needle: str) -> tuple[str, bool]` — menandai teks yang cocok.
- `_find_chunk(job_id: str, chunk_id: str) -> dict | None` — mencari chunk sumber.
- `render_record_trace(rec: dict, phase: str, job_id: str) -> None` — merender trace satu record.
- `_render_evidence(rec: dict, job_id: str, phase: str) -> None` — menampilkan bukti per record.
- `_render_novelty_verdict(rec: dict) -> None` — menampilkan verdict kebaruan.
- `_render_score_breakdown(rec: dict) -> None` — menampilkan rincian skor.

### `tools/process_monitor/research_journals.py` — tabel silang per jurnal lintas tahap, lalu drilldown satu jurnal sampai ke gap, novelty, proposal, dan kandidat.
**Fungsi:**
- `_col(key: str, fallback: str) -> str` — memilih label kolom awam atau teknis.
- `build_journal_table(job_id: str) -> tuple[pd.DataFrame, dict]` — membangun satu baris per jurnal plus data mentah per koleksi.
- `render_journal_crosstab(job_id: str) -> None` — merender tabel silang, total, dan drilldown.
- `_render_drilldown(df: pd.DataFrame, extra: dict) -> None` — menampilkan detail satu jurnal pada tab gap/novelty/proposal/kandidat.

### `tools/process_monitor/research_vocab.py` — glosarium dan label kosakata untuk semua halaman agar istilah awam dan teknis konsisten.
**Fungsi:**
- `mode_teknis() -> bool` — membaca toggle mode teknis dari session state.
- `label(key: str) -> str` — memberi label tampilan awam atau teknis untuk metrik/field.
- `help_of(key: str) -> str | None` — memberi penjelasan singkat untuk field/metric.
- `enum_label(field: str, value) -> str` — memberi label awam untuk nilai enum.
- `enum_help(field: str, value) -> str` — memberi penjelasan untuk nilai enum.
- `render_glossary(stage_key: str) -> None` — menampilkan glosarium istilah pada tahap tertentu.

### `tools/process_monitor/step2_gaps.py` — langkah 2 wizard lite: mencari research gap dengan LLM dari chunk jurnal yang diunggah.
**Fungsi:**
- `reset() -> None` — membersihkan state job dan cache hasil langkah 2.
- `_reason_text(reason: str) -> str` — mengubah kode alasan kandidat menjadi teks awam.
- `_multi_run(gaps: list) -> bool` — mengecek apakah job memakai beberapa run LLM.
- `_kn_badge(g: dict) -> str` — badge stabilitas k/n run untuk gap multi-run.
- `_event_line(e: dict) -> str` — memformat event menjadi satu baris progres.
- `_render_progress(api_base: str, job_id: str, status: dict) -> None` — menampilkan progres job, event ringkas, dan tombol batal/reset.
- `_render_gap_card(g: dict, chunks_by_id: dict) -> None` — merender satu gap final beserta chunk sumbernya.
- `_render_gaps(gaps: list, chunks_by_id: dict) -> None` — menampilkan daftar gap final yang bisa difilter dan diunduh.
- `_render_candidate_card(c: dict, chunks_by_id: dict) -> None` — merender satu kandidat chunk dan semua gap hasil LLM darinya.
- `_render_candidates(cands: list, chunks_by_id: dict) -> None` — menampilkan daftar kandidat chunk.
- `_render_results(api_base: str, job_id: str, chunks_by_id: dict) -> list` — mengambil cache results dan menampilkan gap/kandidat.
- `render(api_base: str, uploads, ocr_mode: str, backend_ok: bool, chunks_by_id: dict)` — entry point langkah 2; memulai job `until="gap_mining"` atau menampilkan hasil yang sudah selesai.

### `tools/process_monitor/step3_neuro.py` — langkah 3 wizard lite: indikator synthesis gap neuro-symbolic antar jurnal yang diunggah.
**Fungsi:**
- `reset() -> None` — membersihkan cache hasil langkah 3.
- `_gap_type(g: dict) -> str` — menentukan jenis gap dari record.
- `_norm(text: str) -> str` — normalisasi teks untuk pencarian.
- `_find_quote(quote: str, chunks_by_id: dict)` — mencari kutipan sumber di chunk yang diunggah.
- `_phase_states(events: list) -> dict` — menghitung status sub-tahap dari event.
- `_render_progress(api_base: str, job_id: str, status: dict, phases: dict) -> None` — menampilkan progres job neuro-symbolic.
- `_facts_from_graph(graph: dict) -> list` — mengekstrak fakta dari snapshot graf pengetahuan.
- `_load(api_base: str, job_id: str, status: dict) -> dict | None` — memuat/caching hasil langkah 3.
- `_confidence_text(g: dict) -> str` — memformat confidence gap.
- `_render_indicator_card(g: dict, chunks_by_id: dict) -> None` — merender kartu satu indikator gap.
- `_author_corroboration(g: dict) -> list` — menyiapkan data korroborasi penulis.
- `_stage_matrix(g: dict) -> dict` — menyusun matriks status tahap untuk satu gap.
- `_sub_dict(g: dict, key: str) -> dict` — helper sub-dict.
- `_render_coverage_map(g: dict) -> None` — menampilkan coverage map.
- `_render_bibliographic_coupling(g: dict) -> None` — menampilkan kopling bibliografis.
- `_render_stage_matrix(g: dict) -> None` — menampilkan stage matrix.
- `_render_author_corroboration(g: dict) -> None` — menampilkan dukungan pernyataan penulis.
- `_render_indicators(indicators: list, chunks_by_id: dict) -> None` — menampilkan seluruh indikator gap.
- `_render_fact_detail(f: dict, chunks_by_id: dict) -> None` — merender detail satu fakta.
- `_render_facts(cache: dict, chunks_by_id: dict) -> None` — menampilkan fakta dan bukti yang dipakai.
- `_render_trace(trace: list) -> None` — menampilkan reasoning trace.
- `_render_results(cache: dict, chunks_by_id: dict) -> list` — merender hasil dan mengembalikan indikator.
- `render(api_base: str, uploads, backend_ok: bool, chunks_by_id: dict)` — entry point langkah 3; memulai job penuh `upload-and-analyze` atau menampilkan hasil.

### `tools/process_monitor/step4_titles.py` — langkah 4 wizard lite: rekomendasi topik, peringkat proposal, dan judul siap-pakai dari gap yang sudah ditemukan.
**Fungsi:**
- `reset() -> None` — membersihkan cache hasil langkah 4.
- `_novelty_disabled(api_base: str) -> bool | None` — mengecek apakah novelty/OpenAlex dimatikan di server.
- `_result_payload(api_base: str, job_id: str) -> dict` — mengambil payload hasil tahap recommendation terakhir.
- `_load(api_base: str, job_id: str) -> dict` — memuat proposal + result untuk job.
- `_render_ranking(proposals: list) -> None` — menampilkan tabel/skor proposal berperingkat.
- `_render_results(api_base: str, job_id: str) -> None` — menampilkan metrik, tab judul, ranking, dan tema.
- `render(api_base: str, gap_job_id: str | None, gap_status: dict | None, backend_ok: bool)` — entry point langkah 4; melanjutkan job langkah 2 ke `recommendation`.

### `tools/process_monitor/wl_common.py` — helper bersama wizard lite untuk komunikasi backend, tampilan teks baca, dan peralihan tabel/fokus/stack.
**Fungsi:**
- `_raise_for_status(resp: requests.Response) -> None` — menaikkan error jika respons HTTP gagal.
- `backend_alive(api_base: str) -> bool` — mengecek backend hidup.
- `_upload_files(uploads) -> list` — membentuk multipart upload PDF.
- `request_chunks(api_base: str, uploads, ocr_mode: str) -> dict` — memanggil preview chunk `POST /api/research/chunk-preview`.
- `start_research_job(api_base: str, uploads, ocr_mode: str, until: str, ...) -> dict` — memulai pipeline penelitian sampai tahap tertentu.
- `job_status(api_base: str, job_id: str) -> dict` — mengambil status job.
- `job_events(api_base: str, job_id: str) -> list` — mengambil event job.
- `cancel_job(api_base: str, job_id: str) -> dict` — membatalkan job.
- `continue_research_job(api_base: str, job_id: str, until: str = "recommendation", ...) -> dict` — melanjutkan job yang sudah berhenti di gap_mining.
- `research_stages(api_base: str) -> list` — mengambil daftar tahapan pipeline.
- `stage_records(api_base: str, job_id: str, phase: str) -> list` — mengambil record lengkap per tahap.
- `start_legacy_analysis(api_base: str, uploads, gap_job_id: str | None = None) -> dict` — memulai pipeline 8 tahap lama `upload-and-analyze`.
- `job_artifacts(api_base: str, job_id: str, phase: str) -> list` — mengambil artefak satu tahap.
- `job_graph(api_base: str, job_id: str) -> dict` — mengambil snapshot graf pengetahuan.
- `section_label(key: str) -> str` — memetakan nama seksi ke label awam.
- `short_name(text: str, n: int = 28) -> str` — memendekkan nama.
- `render_reading_text(text: str, highlight: str | None = None) -> None` — merender teks baca dengan highlight aman.
- `render_table_with_reader(...) -> None` — menampilkan tabel dan detail baris yang dipilih.
- `render_focus(n: int, render_detail, key: str) -> None` — mode baca satu-per-satu dengan tombol prev/next.
- `render_view_switch(...) -> None` — memilih mode tampilan tabel/berurutan/fokus.

## flood-geoai-research/src/

### `flood-geoai-research/src/common.py` — utilitas bersama eksperimen flood mapping: loading chip Sen1Floods11, ekstraksi fitur multimodal, dan split sampel.
**Fungsi:**
- `list_chips(split_csv)` — membaca daftar chip dari file split CSV.
- `_read(chip, kind)` — membaca raster `*_S1Hand.tif`, `*_S2Hand.tif`, atau label.
- `chip_features(chip)` — membangun matriks fitur per-piksel dari SAR+optik dan label.
- `sample_split(chips, n_per_class=4000, seed=0)` — mengambil sampel piksel stratified per kelas dari daftar chip.
- `full_pixels(chips)` — mengambil seluruh piksel valid untuk evaluasi serta slice per chip.
- `feat_idx(names)` — mengubah nama fitur menjadi indeks kolom.

### `flood-geoai-research/src/exp1_fusion.py` — eksperimen 1 yang menguji apakah fusi Sentinel-1 + Sentinel-2 mengungguli satu modalitas saja untuk klasifikasi banjir.
**Fungsi:**
- `iou(y_true, y_pred)` — menghitung IoU kelas air.
- `train_model(Xtr, ytr, Xva, yva, cols, name)` — melatih LightGBM dengan early stopping.
- `evaluate(m, Xte, yte, cols, slices)` — menghitung ROC-AUC, F1, IoU, dan statistik per chip.
- `main()` — menjalankan training/evaluasi untuk S1-only, S2-only, dan Fusion, lalu menyimpan metrik, model, dan plot.

### `flood-geoai-research/src/exp2_xai.py` — eksperimen 2 untuk explainable AI: SHAP global, uji faithfulness deletion, dan peta kerawanan yang dapat ditafsirkan.
**Fungsi:**
- `load_cache()` — memuat cache test pixel dari hasil eksperimen 1.
- `deletion_curve(model, X, y, order, fill)` — menghitung penurunan AUC saat fitur dimask berturut-turut.
- `main()` — menjalankan TreeSHAP, deletion test, membuat visualisasi pentingnya fitur dan susceptibility map, lalu menyimpan metrik/PNG.

## root

### `generate_paper_figures.py` — generator gambar publikasi untuk paper/skripsi yang mengubah hasil eksperimen batch menjadi figure 300-dpi.
**Fungsi:**
- `load_runs(mode)` — memuat semua run JSON untuk satu mode eksperimen.
- `indicators_of(run)` — mengekstrak daftar indikator gap dari run.
- `save(fig, name)` — menyimpan figure ke PNG dan PDF.
- `fig1_architecture()` — membuat diagram arsitektur sistem.
- `fig2_ablation()` — membuat grafik ablation indikator dan rule-engine rejection rate.
- `fig3_h9()` — membuat perbandingan NLI vs no-NLI.
- `fig4_adversarial()` — membuat grafik confidence sebelum/sesudah validasi adversarial.
- `fig5_gap_types()` — membuat diagram pie distribusi jenis gap.
- `fig6_gap_flow()` — membuat diagram alur deteksi gap dengan contoh angka nyata.
- `__main__` block — menjalankan seluruh generator figure berurutan.

### `Makefile` — perintah cepat untuk instalasi, menjalankan backend, tes, eksperimen, dan utilitas data.
**Target:**
- `help` — menampilkan daftar target dan deskripsinya.
- `install` — menginstal dependensi backend.
- `install-backend` — menginstal dependensi backend saja.
- `install-backend-locked` — menginstal lock backend CPU-safe lewat `uv`.
- `lock-backend` — memperbarui lock file backend.
- `dev` — menjalankan target backend dalam mode development.
- `backend` — menjalankan server backend lewat `./run_backend.sh`.
- `test` — menjalankan seluruh tes pytest backend.
- `test-unit` — menjalankan tes unit komponen inti.
- `test-integration` — menjalankan tes integrasi.
- `test-api` — menjalankan tes kontrak FastAPI.
- `runtime-doctor` — menampilkan konfigurasi runtime ter-redaksi.
- `experiment-data` — mengunduh dataset benchmark 23 paper.
- `experiment` — menjalankan pipeline eksperimen penuh.
- `experiment-ablation` — menjalankan ablation `no-rule-engine` dan `linear-baseline`.
- `experiment-compare` — mengagregasi hasil eksperimen.
- `experiment-stats` — menjalankan multi-run dengan mean±std dan uji statistik.
- `experiment-ablation-nli` — menjalankan varian NLI dan no-NLI.
- `experiment-breakdown` — breakdown hasil per indikator/metode.
- `experiment-benchmark` — membangun gold benchmark gap.
- `experiment-prf` — menghitung precision/recall/F1 gap terhadap gold.
- `experiment-retrieval` — evaluasi retrieval.
- `experiment-errors` — taksonomi false-discovery error.
- `experiment-calibration` — kalibrasi confidence dari form expert.
- `experiment-annotate` — membuat sheet anotasi fakta SPO.
- `lint` — menjalankan flake8.
- `format` — menjalankan black.
- `clean` — membersihkan cache/bytecode.
- `docker-up` — menyalakan layanan optional via Docker Compose.
- `docker-down` — mematikan layanan optional via Docker Compose.
- `docker-logs` — melihat log layanan optional.
- `db-stats` — menampilkan statistik vector store.
- `db-sources` — menampilkan sumber dokumen dan jumlah chunk.
- `db-query` — melakukan semantic search ke vector store.
- `papers-search` — mengambil paper eksternal tanpa ingest.
- `papers-ingest` — mengambil paper dan memasukkannya ke corpus searchable.
- `setup` — instalasi awal dan pembuatan `.env` dari contoh.


## Tambahan — fungsi bersarang (nested)

### `generate_paper_figures.py`
- `box(x, y, w, h, label, fc, fontsize, weight)` — bersarang di `fig1_architecture`; menggambar kotak berlabel (Rectangle + teks tengah) pada axes matplotlib.
- `arrow(x1, y1, x2, y2)` — bersarang di `fig1_architecture`; menggambar panah `->` antar kotak dengan `ax.annotate`.
- `find(method)` — bersarang di `fig6_gap_flow`; mengambil gap indicator pertama dengan `detection_method` tertentu (`topic_clustering`, `aspect_coverage`, …) dari daftar `gis`.

### `tools/process_monitor/common.py`
- `_fmt(idx: int) -> str` — bersarang di `_render_paper_analysis_result`; memformat label opsi selectbox kelemahan per jurnal (`"n. judul[:80]"`).
- `norm(t) -> str` — bersarang di `_gap_year_span`; menormalkan judul (rapikan spasi, lowercase) untuk mencocokkan gap ke tahun paper.

### `tools/process_monitor/export_bundle.py`
- `_get(path: str) -> dict` — bersarang di `_cli`; GET JSON ke backend FastAPI (`urllib`, timeout 60 s) untuk mengambil daftar job/hasil saat ekspor via CLI.

### `tools/process_monitor/page_research_wizard.py`
- `_live(job_id: str) -> None` — didefinisikan di level modul dalam blok `elif langkah == 2:` sebagai `@st.fragment(run_every=every)` (auto-refresh); mem-poll `fetch_status`, menampilkan progress & event, dan `st.rerun(scope="app")` bila status bukan `queued`/`running` agar halaman pindah ke Langkah 3.

### `tools/process_monitor/page_wizard.py`
- `row(c: dict) -> dict` — bersarang di `render_chunks`; memetakan satu chunk ke baris tabel (`#`, Bagian, Hal., Token, Teks) untuk `render_view_switch`.

### `tools/process_monitor/research_journals.py`
- `row(src: str) -> dict` — bersarang di `build_journal_table`; mengambil/membuat baris agregat per sumber jurnal (`rows.setdefault`).

### `tools/process_monitor/step2_gaps.py`
- `row(g: dict) -> dict` — bersarang di `_render_gaps`; memetakan satu gap ke baris tabel (Jurnal, Jenis, skor Verbatim, dan `Run k/n` bila multi-run).

### `tools/process_monitor/step3_neuro.py`
- `name(node_id)` — bersarang di `_facts_from_graph`; mengembalikan `(nama, entity_type)` node KG untuk menyusun kalimat fakta SPO dari edge.
- `row(g: dict) -> dict` — bersarang di `_render_indicators`; memetakan satu indikator gap ke baris tabel (Jenis, Metode, Keyakinan terkalibrasi, Vonis rule engine, tanda Tinjauan).


<a id="bagian-08"></a>
# Bagian 08 — tests — ringkasan suite pytest

## backend/tests/

### `backend/tests/conftest.py`
- Fixture: `test_data_dir` — path ke `backend/tests/test_data` untuk data uji.
- Fixture: `setup_logging` — sink log `logs/test.log` sekali per session, lalu dibersihkan.
- Fixture: `_openalex_check_enabled_by_default` — memaksa `OPENALEX_DISABLED=0` agar perilaku default konsisten.
- Marker/konfigurasi pytest: `testpaths=tests`, `python_files=test_*.py *_test.py`, `python_classes=Test*`, `python_functions=test_*`, `asyncio_mode=auto`, marker terdaftar: `unit`, `integration`, `api`, `ocr`, `slow`.

### `backend/tests/test_agent_tools.py` — `backend/app/core/agents/tools/rag_tool.py`, `backend/app/core/agents/tools/kg_querier_tool.py`
- Jumlah tes: 17 fungsi dalam 4 kelas.
- Cakupan: validasi `RAGTool` dan `KGQuerierTool`, termasuk evaluasi skor/relevansi, seleksi konteks, dan perilaku ketika hasil kecil/hasil buruk.
- Banyak memakai `MagicMock`; tampak murni unit tanpa jaringan/LLM nyata.

### `backend/tests/test_analysis_context.py` — `backend/app/core/runtime/analysis_context.py`
- Jumlah tes: 2 fungsi dalam 0 kelas.
- Cakupan: `ScopedRAGRetriever` menjaga scope retriever dan memulihkan state setelah konteks keluar.
- Murni unit, dengan mock retriever.

### `backend/tests/test_analysis_queue.py` — `backend/app/services/analysis_queue.py`, `backend/app/utils/job_store.py`
- Jumlah tes: 5 fungsi dalam 0 kelas.
- Cakupan: antrean job analisis, persistensi/refresh status job, dan sinkronisasi dengan job store.
- Murni unit; pakai `threading` dan stub `job_store`.

### `backend/tests/test_api.py` — `backend/app/api/*`, `backend/app/main.py`
- Jumlah tes: 33 fungsi dalam 1 kelas.
- Cakupan: kontrak endpoint FastAPI untuk health, model switching, chat/session, job lifecycle, artifact/job-events, graph, stats, upload, reanalyze, dan fallback perilaku error.
- Mayoritas memakai `TestClient` + monkeypatch; ditandai `@pytest.mark.api` pada banyak kasus.

### `backend/tests/test_citation_coupling.py` — `backend/app/core/gap_detection/citation_coupling.py`
- Jumlah tes: 12 fungsi dalam 3 kelas.
- Cakupan: build graph coupling sitasi, ambang minimum paper/references, serta efek ketika dependensi/fitur jaringan dimatikan.
- Unit dengan `MagicMock`; ada verifikasi bahwa jaringan tidak dipanggil saat fitur dinonaktifkan.

### `backend/tests/test_config_runtime.py` — `backend/app/utils/config_loader.py`
- Jumlah tes: 3 fungsi dalam 0 kelas.
- Cakupan: loader konfigurasi runtime dan sumber env/default.
- Murni unit.

### `backend/tests/test_consensus_gaps.py` — `backend/app/core/pipeline/io.py`
- Jumlah tes: 4 fungsi dalam 1 kelas.
- Cakupan: baca/tulis JSONL dan skenario file/missing-path terkait artefak gap consensus.
- Murni unit filesystem; tidak ada jaringan.

### `backend/tests/test_coordinator_provenance.py` — `backend/app/core/agents/coordinator.py`, `backend/app/core/agents/tools/paper_analyzer_tool.py`
- Jumlah tes: 3 fungsi dalam 3 kelas.
- Cakupan: provenance/metadata coordinator agent dan integrasi tool analyzer paper.
- Unit dengan mock tool.

### `backend/tests/test_copilot_client.py` — `backend/app/services/copilot_client.py`
- Jumlah tes: 20 fungsi dalam 5 kelas.
- Cakupan: client Copilot/remote inference, concurrency/thread safety, retry/error handling, dan fallback behavior.
- Murni unit dengan stub asyncio/threading; tidak menyentuh layanan eksternal.

### `backend/tests/test_corpus_relevance.py` — `backend/app/core/pipeline/corpus_relevance.py`
- Jumlah tes: 10 fungsi dalam 4 kelas.
- Cakupan: probe/check relevansi korpus, ambang warning, dan klasifikasi hasil relevansi.
- Murni unit.

### `backend/tests/test_coverage_axes.py` — `backend/app/core/gap_detection/coverage_axes.py`, `backend/app/core/gap_detection/analyzer.py`
- Jumlah tes: 16 fungsi dalam 4 kelas.
- Cakupan: build/normalisasi axes coverage, scoring/labeling gap, dan interaksi hasil analyzer.
- Unit; banyak `MagicMock`/`pytest.mark.parametrize`.

### `backend/tests/test_cross_critic.py` — `backend/experiments/cross_critic.py` (`CrossCritic`, `_parse_json_array`)
- Jumlah tes: 19 fungsi dalam 4 kelas.
- Cakupan: evaluasi/aggregasi kritik silang dan hasil eksperimen dari data JSON; ada path impor skrip top-level.
- Perlu verifikasi detail modul karena import berasal dari util skrip, bukan package `app`.

### `backend/tests/test_evidence_subgraph.py` — `backend/app/core/gap_detection/analyzer.py`, `backend/app/core/knowledge/fact_table.py`, `backend/app/core/knowledge_graph/graph_builder.py`
- Jumlah tes: 5 fungsi dalam 2 kelas.
- Cakupan: bangun evidence subgraph dari fact table/knowledge graph dan indikator gap.
- Murni unit.

### `backend/tests/test_fact_extractor.py` — `backend/app/core/knowledge/fact_extractor.py`
- Jumlah tes: 16 fungsi dalam 3 kelas.
- Cakupan: ekstraksi fakta dari JSON/LLM output, parsing array/object, retry suffix, dan validasi format respons.
- Ada skenario `ollama` JSON mode; tetap unit dengan mock, bukan model nyata.

### `backend/tests/test_fact_table.py` — `backend/app/core/knowledge/fact_table.py`
- Jumlah tes: 45 fungsi dalam 11 kelas.
- Cakupan: model `Entity/Fact/Verdict`, normalisasi/lookup, serialisasi, deduplikasi, relasi, dan edge case tabel fakta.
- Murni unit.

### `backend/tests/test_gap_analyzer.py` — `backend/app/core/gap_detection/analyzer.py`, `backend/app/core/knowledge/fact_table.py`
- Jumlah tes: 31 fungsi dalam 9 kelas.
- Cakupan: analisis gap, skor/indikator, bukti, rules, dan perubahan verdict dari fact table.
- Banyak mock; unit.

### `backend/tests/test_gap_matching.py` — skrip `gap_matching.py` (top-level)
- Jumlah tes: 13 fungsi dalam 4 kelas.
- Cakupan: cosine/greedy matching, precision-recall-F1, dan evaluasi matching gap.
- Murni unit pada modul skrip.

### `backend/tests/test_gap_mining.py` — `backend/app/core/gap_mining/*`
- Jumlah tes: 18 fungsi dalam 5 kelas.
- Cakupan: kandidat gap, parsing ekstraksi, verifikasi grounded, dan klasifikasi novelty.
- Ada test yang mematikan `OPENALEX`/HTTP fetch; tidak memakai jaringan nyata.

### `backend/tests/test_gap_upgrade.py` — `backend/app/core/gap_detection/calibration.py`, `backend/app/core/gap_detection/coverage_map.py`, `backend/app/core/gap_detection/analyzer.py`
- Jumlah tes: 39 fungsi dalam 10 kelas.
- Cakupan: calibration/temperature scaling, ECE/Brier/AURC, provenance, coverage matrix, dan upgrade gap detection.
- Murni unit; ada data sintetis.

### `backend/tests/test_integration.py` — `backend/app/core/validation/rule_engine.py`, `backend/app/core/knowledge/fact_table.py`
- Jumlah tes: 23 fungsi dalam 4 kelas.
- Cakupan: integrasi rule engine dengan fact table, agregasi verdict, dan alur validasi batch.
- Tetap unit/integration ringan; bergantung pada mock `MagicMock`.

### `backend/tests/test_job_store.py` — `backend/app/utils/job_store.py`
- Jumlah tes: 13 fungsi dalam 0 kelas.
- Cakupan: persistensi job store, listing/status/update, dan recovery dari JSON job artifacts.
- Filesystem-based, tanpa layanan eksternal.

### `backend/tests/test_llm.py` — `backend/app/services/llm_service.py`
- Jumlah tes: 11 fungsi dalam 0 kelas.
- Cakupan: inisialisasi client Ollama/HTTP, timeout, fallback engine, dan error handling generate/chat.
- Ada `skipif` untuk ketergantungan `ollama`/varian model tertentu; unit dengan mock network client.

### `backend/tests/test_negative_control.py` — `backend/experiments/run_experiment.py` (`compile_results` — pemisahan topik kontrol negatif `TC*`)
- Jumlah tes: 6 fungsi dalam 2 kelas.
- Cakupan: negative-control/aggregasi hasil eksperimen untuk memastikan baseline tidak “menang” secara semu.
- Perlu verifikasi detail modul impor top-level.

### `backend/tests/test_nli_checker_tool.py` — `backend/app/core/agents/tools/nli_checker_tool.py`, `backend/app/core/validation/relation_classifier.py`
- Jumlah tes: 1 fungsi dalam 0 kelas.
- Cakupan: tool NLI checker yang memanggil relation classifier dan memetakan hasilnya.
- Unit dengan mock classifier.

### `backend/tests/test_nli_integration.py` — `backend/app/core/validation/relation_classifier.py`
- Jumlah tes: 6 fungsi dalam 2 kelas.
- Cakupan: integrasi relation classifier/NLI, klasifikasi entailment/contradiction/extension, dan edge case kalimat.
- Unit dengan `MagicMock`.

### `backend/tests/test_ocr_config.py` — `backend/app/utils/document_processor.py`
- Jumlah tes: 10 fungsi dalam 2 kelas.
- Cakupan: konfigurasi OCR/doc processor, availability checks, dan toggling fitur OCR.
- Unit; tidak menjalankan OCR nyata.

### `backend/tests/test_ocr_recovery.py` — `backend/app/core/pipeline/pipeline.py`
- Jumlah tes: 11 fungsi dalam 5 kelas.
- Cakupan: recovery OCR `_ocr_pages` dan fallback ketika page render/OCR gagal.
- Unit dengan monkeypatch pada pipeline internal.

### `backend/tests/test_paper_download.py` — `backend/app/api/routes/papers.py`
- Jumlah tes: 19 fungsi dalam 2 kelas.
- Cakupan: download/legal OA paper, antrian analisis, validasi input, dan kontrak endpoint papers.
- Ditandai `@pytest.mark.api`/`@pytest.mark.asyncio`; komentar menyebut no network, jadi pakai mock/stub.

### `backend/tests/test_paper_profiles.py` — `backend/app/core/gap_detection/paper_profiles.py`
- Jumlah tes: 13 fungsi dalam 3 kelas.
- Cakupan: normalisasi source, build profile, ekstraksi profil dari konteks, dan serialisasi.
- Murni unit.

### `backend/tests/test_paper_profiles_flow.py` — `backend/app/core/agents/coordinator.py`, `backend/app/core/agents/gap_detector.py`
- Jumlah tes: 3 fungsi dalam 1 kelas.
- Cakupan: flow profil paper dari coordinator ke gap detector.
- Unit dengan mock agent.

### `backend/tests/test_paper_relevance.py` — `backend/app/services/paper_apis/aggregator.py`
- Jumlah tes: 7 fungsi dalam 2 kelas.
- Cakupan: relevansi paper metadata dan pembersihan CrossRef JATS/HTML.
- No network calls (sesuai komentar file).

### `backend/tests/test_pipeline.py` — `backend/app/core/pipeline/text_cleaning.py`, `backend/app/core/pipeline/section_normalizer.py`, `backend/app/core/pipeline/token_chunker.py`
- Jumlah tes: 29 fungsi dalam 8 kelas.
- Cakupan: cleaning teks, normalisasi section, chunking token/sentence, dan heuristik kualitas input.
- Murni unit, synthetic input.

### `backend/tests/test_quote_grounding.py` — `backend/app/core/gap_detection/quote_grounding.py`
- Jumlah tes: 14 fungsi dalam 5 kelas.
- Cakupan: fuzzy match quote, split sentence, extract supporting quotes, dan verifikasi quote terhadap paper.
- Unit dengan data teks sintetis.

### `backend/tests/test_rate_limit.py` — `backend/app/utils/rate_limit.py`
- Jumlah tes: 8 fungsi dalam 2 kelas.
- Cakupan: sliding-window limiter dan middleware FastAPI.
- Unit; fixture conftest mematikan rate limiting global untuk test suite, tapi file ini menguji implementasinya sendiri.

### `backend/tests/test_references.py` — `backend/app/core/pipeline/references.py`
- Jumlah tes: 14 fungsi dalam 3 kelas.
- Cakupan: parse/extract referensi, split entry, word-content helper.
- Unit.

### `backend/tests/test_relation_classifier.py` — `backend/app/core/validation/relation_classifier.py`
- Jumlah tes: 38 fungsi dalam 12 kelas.
- Cakupan: marker causal/contradiction/extension, relation classification, scoring, prompt parsing, dan edge case teks ilmiah.
- Unit; banyak `pytest.mark.parametrize` dan mock patch.

### `backend/tests/test_reranker.py` — `backend/app/core/retrieval/reranker.py`, `backend/app/core/retrieval/rag_retriever.py`, `backend/app/core/retrieval/vector_store.py`
- Jumlah tes: 7 fungsi dalam 2 kelas.
- Cakupan: cross-encoder reranker, integrasi hasil retrieval, dan skema document/ranking.
- Unit dengan `MagicMock`.

### `backend/tests/test_research_api.py` — `backend/app/main.py`, `backend/app/api/routes/research.py`
- Jumlah tes: 49 fungsi dalam 7 kelas.
- Cakupan: endpoint research workflow, upload/ingest/retrieval, kontrak response, dan handling folder temp/research artifacts.
- Mayoritas API contract; menggunakan `TestClient`, filesystem temp, dan monkeypatch.

### `backend/tests/test_research_pipeline.py` — `backend/app/services/research_pipeline.py`
- Jumlah tes: 68 fungsi dalam 18 kelas.
- Cakupan: seluruh pipeline riset: ingest, analyze, job orchestration, persist artefak, cancellation, cleanup, dan recovery state.
- Terlihat paling berat; kemungkinan ada komponen yang berhubungan dengan file-store, tapi tetap dominan unit/integration ringan.

### `backend/tests/test_retrieval_metrics.py` — skrip `retrieval_metrics.py` (top-level)
- Jumlah tes: 16 fungsi dalam 5 kelas.
- Cakupan: precision@k, recall@k, MRR, NDCG/DCG, aggregate metrics.
- Murni unit pada skrip util.

### `backend/tests/test_rule_engine.py` — `backend/app/core/validation/rule_engine.py`, `backend/app/core/knowledge/fact_table.py`
- Jumlah tes: 49 fungsi dalam 14 kelas.
- Cakupan: definisi rule, kategori/ID, F1/F2/F3/C1/C2/C3/K1/K2/K3, agregasi verdict, confidence adjustment, batch validate, dan summary report.
- Murni unit; memakai `MagicMock`/`patch`, tidak ada jaringan/LLM nyata.

### `backend/tests/test_section_chunking.py` — `backend/app/utils/document_processor.py`
- Jumlah tes: 4 fungsi dalam 1 kelas.
- Cakupan: chunking section dokumen dari processor.
- Unit.

### `backend/tests/test_skill_guidance.py` — `backend/app/services/skill_guidance.py`
- Jumlah tes: 5 fungsi dalam 0 kelas.
- Cakupan: rekomendasi guidance/skill dan format keluaran layanan.
- Unit.

### `backend/tests/test_skills.py` — `backend/app/api/routes/skills.py`, `backend/app/main.py`
- Jumlah tes: 9 fungsi dalam 0 kelas.
- Cakupan: endpoint skills/AI-Research-SKILLs.
- Ditandai `@pytest.mark.api`; komentar file menyebut no LLM network.

### `backend/tests/test_stats_utils.py` — skrip `stats_utils.py` (top-level)
- Jumlah tes: 18 fungsi dalam 7 kelas.
- Cakupan: Holm-Bonferroni, effect size, bootstrap CI, rank-biserial, dan formatting hasil statistik.
- Unit.

### `backend/tests/test_themes.py` — `backend/app/core/recommendation/themes.py`
- Jumlah tes: 7 fungsi dalam 1 kelas.
- Cakupan: theme similarity, `Theme`, dan builder tema rekomendasi.
- Unit.

### `backend/tests/test_upload_validation.py` — `backend/app/utils/upload_validation.py`
- Jumlah tes: 8 fungsi dalam 0 kelas.
- Cakupan: validasi upload, ukuran/jenis file, dan exception FastAPI.
- Unit.

### `backend/tests/test_url_guard.py` — `backend/app/utils/url_guard.py`
- Jumlah tes: 8 fungsi dalam 0 kelas.
- Cakupan: anti-SSRF URL guard, validasi HTTP/public URL, dan penolakan URL unsafe.
- Unit; komentar file menyebut DNS/network distub.

### `backend/tests/test_vector_store.py` — `backend/app/core/retrieval/vector_store.py`
- Jumlah tes: 8 fungsi dalam 0 kelas.
- Cakupan: vector store CRUD/search dasar, path temp, dan persistence sederhana.
- Ditandai `pytest.mark.slow` di file.

### `backend/tests/test_workflow_stages.py` — `backend/app/core/gap_detection/workflow_stages.py`
- Jumlah tes: 12 fungsi dalam 5 kelas.
- Cakupan: build prompt, parsing JSON workflow, stage labels/keys, seleksi konteks, dan verifikasi workflow output.
- Unit.

**Cara menjalankan:** `cd backend && python -m pytest tests/` untuk semua tes; subset yang disediakan Makefile: `make test-unit`, `make test-integration`, `make test-api`. Marker yang tersedia: `unit`, `integration`, `api`, `ocr`, `slow`. Tes yang cenderung butuh layanan eksternal/ketergantungan opsional: `test_llm.py` (Ollama/HTTP client, skip bila `ollama` tidak ada), `test_paper_download.py`/`test_skills.py`/`test_api.py` (API contract tapi dimock), `test_vector_store.py` (`slow`/resource-heavy), dan file-file yang eksplisit menyebut jaringan/OA/OpenAlex dipalsukan tetap unit.

**Peta cakupan:**

| Modul sumber | File tes yang menguji |
|---|---|
| `backend/app/core/validation/rule_engine.py` | `backend/tests/test_rule_engine.py`, `backend/tests/test_integration.py` |
| `backend/app/core/validation/relation_classifier.py` | `backend/tests/test_relation_classifier.py`, `backend/tests/test_nli_integration.py`, `backend/tests/test_nli_checker_tool.py` |
| `backend/app/core/knowledge/fact_table.py` | `backend/tests/test_fact_table.py`, `backend/tests/test_gap_analyzer.py`, `backend/tests/test_evidence_subgraph.py`, `backend/tests/test_integration.py` |
| `backend/app/core/gap_detection/analyzer.py` | `backend/tests/test_gap_analyzer.py`, `backend/tests/test_coverage_axes.py`, `backend/tests/test_evidence_subgraph.py`, `backend/tests/test_gap_upgrade.py` |
| `backend/app/core/gap_detection/paper_profiles.py` | `backend/tests/test_paper_profiles.py`, `backend/tests/test_paper_profiles_flow.py`, `backend/tests/test_citation_coupling.py` |
| `backend/app/core/pipeline/*` | `backend/tests/test_pipeline.py`, `backend/tests/test_references.py`, `backend/tests/test_section_chunking.py`, `backend/tests/test_corpus_relevance.py`, `backend/tests/test_consensus_gaps.py`, `backend/tests/test_ocr_recovery.py` |
| `backend/app/core/retrieval/*` | `backend/tests/test_reranker.py`, `backend/tests/test_vector_store.py`, `backend/tests/test_analysis_context.py` |
| `backend/app/core/gap_mining/*` | `backend/tests/test_gap_mining.py` |
| `backend/app/services/*` | `backend/tests/test_analysis_queue.py`, `backend/tests/test_copilot_client.py`, `backend/tests/test_llm.py`, `backend/tests/test_paper_relevance.py`, `backend/tests/test_research_pipeline.py`, `backend/tests/test_skill_guidance.py`, `backend/tests/test_paper_profiles_flow.py` |
| `backend/app/api/routes/*` | `backend/tests/test_api.py`, `backend/tests/test_paper_download.py`, `backend/tests/test_research_api.py`, `backend/tests/test_skills.py` |
| `backend/app/utils/*` | `backend/tests/test_config_runtime.py`, `backend/tests/test_job_store.py`, `backend/tests/test_rate_limit.py`, `backend/tests/test_upload_validation.py`, `backend/tests/test_url_guard.py`, `backend/tests/test_ocr_config.py`, `backend/tests/test_section_chunking.py` |
| Skrip top-level util (`gap_matching.py`, `retrieval_metrics.py`, `stats_utils.py`, `run_experiment.py`) | `backend/tests/test_gap_matching.py`, `backend/tests/test_retrieval_metrics.py`, `backend/tests/test_stats_utils.py`, `backend/tests/test_negative_control.py` |

Modul sumber utama yang **belum punya tes langsung** (hasil verifikasi grep terhadap `backend/tests/`): `backend/app/core/agents/recommender.py`, `backend/app/core/agents/research_analyzer.py`, `backend/app/core/gap_detection/claim_normalization.py` & `adjudication.py` (hanya tersentuh tidak langsung lewat `GapAnalyzer`), `backend/app/core/knowledge_graph/graph_builder.py` (hanya lewat `test_evidence_subgraph.py`), `backend/app/telemetry/recorder.py` (hanya retensi lewat `test_job_store.py`), `backend/app/api/dependencies.py`, dan hampir semua klien per-API di `backend/app/services/paper_apis/*` (`arxiv.py`, `crossref.py`, `europe_pmc.py`, `grobid.py`, `openalex.py`, `pubmed.py`, `sciencedirect.py`, `scopus.py`, `semantic_scholar.py`, `unpaywall.py`).

Catatan koreksi: `graph_metrics.py`, `support_gap.py`, dan `recommendation/novelty.py` **sudah** diuji oleh `backend/tests/test_gap_upgrade.py`.

**Total tes terhitung:** 806 fungsi `test_*` di 51 file (`grep -rhoE '^\s*(async )?def test_' backend/tests/*.py | wc -l`).
