# 📝 REVISI PROPOSAL TESIS (FINAL - Fokus yang Benar)

**Tanggal:** 20 Desember 2025
**Versi:** 2.0 - Adjusted based on core focus clarification
**Target:** Publikasi Jurnal/Conference Internasional

---

## 🎯 KLARIFIKASI FOKUS PENELITIAN

### **❌ BUKAN Fokus Penelitian:**
- Paper search optimization
- Paper selection algorithms
- Relevance ranking
- **Human-in-the-loop paper selection** ← Ini TRIVIAL, bukan kontribusi!

### **✅ FOKUS PENELITIAN (Core Contribution):**

```
📌 GIVEN (Input):
   User sudah punya N papers (3-10 papers)
   - Bisa dari: Upload PDF, atau Search → Manual pilih
   - Cara dapat papers = NOT THE POINT

🎯 RESEARCH FOCUS (Apa yang terjadi SETELAH papers ada):

   1. COMPARATIVE ANALYSIS
      → Bagaimana analyze multiple papers together?
      → Cross-paper reasoning, identify patterns

   2. SYNTHESIS GAP DETECTION (NOVELTY!)
      → Gaps yang muncul dari COMBINING insights
      → Unexplored combinations, bridging gaps

   3. RAG-ENHANCED (Prevent Hallucination)
      → Grounded in actual paper content
      → No LLM hallucination

   4. LIGHTWEIGHT KNOWLEDGE GRAPH
      → Paper-Concept-Method relationships
      → Graph-based gap detection
```

---

## 📋 RINGKASAN PERUBAHAN UTAMA

| Aspek | OLD (Salah Focus) | NEW (Benar) |
|-------|-------------------|-------------|
| **Novelty #1** | ~~Human-in-the-loop selection~~ | **Comparative Multi-Paper Analysis** |
| **Novelty #2** | ~~Multi-modal gap detection~~ | **Synthesis Gap Detection** |
| **Novelty #3** | ~~Multi-agent framework~~ | **RAG-Enhanced Analysis** |
| **Scope** | Terlalu luas (paper search, citation network, topic modeling) | Focused (comparative analysis, synthesis gaps, recommendations) |

---

# 🎯 REVISI BAB I: PENDAHULUAN

## 1.1 Latar Belakang

### ✏️ **PARAGRAF 1-3: KEEP AS IS** (Tentang volume publikasi, LLM challenges, RAG benefits)

### ➕ **TAMBAH PARAGRAF BARU (Setelah paragraf RAG):**

```
Dalam proses identifikasi research gap, researchers umumnya perlu
membandingkan multiple papers untuk mendapatkan comprehensive understanding.
Proses comparative analysis ini memungkinkan identification tidak hanya gaps
yang explicitly stated dalam individual papers, tetapi juga "synthesis gaps"—
research opportunities yang muncul dari comparing dan combining insights
across multiple papers. Misalnya, Paper A mungkin membahas Method X untuk
Domain Y, sementara Paper B membahas Method Z untuk Domain Y. Synthesis gap
dapat berupa: "Apakah Method X dapat dikombinasikan dengan Method Z untuk
meningkatkan performa di Domain Y?"

Namun, multi-document comparative analysis menghadapi challenges signifikan.
Pertama, Large Language Models memiliki keterbatasan context window yang
membuat sulit untuk process multiple papers secara simultan dengan comprehensive
understanding (Nallapati et al., TACL 2024). Kedua, existing multi-document
summarization models masih struggle dalam melakukan true synthesis
dibandingkan sekadar extractive summarization—mereka aggregate information
tetapi tidak generate novel insights dari comparison (Do Multi-Document
Summarization Models Synthesize?, TACL 2024). Ketiga, LLM-only approaches
tanpa grounding dalam actual paper content rentan terhadap hallucination,
producing research gaps yang tidak supported by evidence (Chelli et al., 2024).

Untuk mengatasi challenges ini, diperlukan framework yang dapat: (1) melakukan
structured comparative analysis across multiple papers, (2) mengidentifikasi
synthesis gaps yang emerge from comparison, bukan hanya explicit gaps dari
individual papers, (3) leverage RAG untuk ensure factual grounding dan prevent
hallucination, dan (4) utilize lightweight knowledge graph untuk capture
semantic relationships tanpa kompleksitas full ontology construction.
```

### ✏️ **REVISI PARAGRAF TERAKHIR:**

**❌ HAPUS paragraf lama tentang "integrating state-of-the-art technologies dalam comprehensive framework"**

**✅ GANTI DENGAN:**

```
Penelitian ini mengusulkan sistem comparative multi-paper analysis berbasis
RAG dan LLM dengan fokus pada deteksi synthesis research gaps. Berbeda dengan
pendekatan existing yang analyze papers secara individual atau melakukan simple
aggregation, sistem yang dikembangkan melakukan structured cross-paper
comparative reasoning untuk mengidentifikasi:

1. Explicit gaps: Limitations yang explicitly stated dalam papers
2. Implicit gaps: Research opportunities yang inferred dari absence or patterns
3. Synthesis gaps (NOVEL): Opportunities yang emerge dari comparing dan
   combining insights across multiple papers

Sistem memanfaatkan RAG architecture untuk ensure bahwa gap detection grounded
dalam actual paper content, serta lightweight knowledge graph untuk capture
paper-concept-method relationships yang mendukung graph-based gap analysis.

Pendekatan ini diharapkan dapat menghasilkan research gap identification yang
lebih comprehensive, novel, dan actionable dibandingkan manual literature review
atau fully-automated LLM-only approaches, dengan particular strength dalam
identifying synthesis gaps yang tidak terdeteksi oleh single-paper analysis.
```

---

## 1.2 Rumusan Masalah

### ❌ **HAPUS SELURUH RUMUSAN MASALAH LAMA**

### ✅ **GANTI DENGAN 3 RUMUSAN MASALAH BARU:**

```
Berdasarkan latar belakang yang telah diuraikan, penelitian ini merumuskan
tiga permasalahan utama sebagai berikut:

1. Bagaimana merancang dan mengimplementasikan algoritma comparative analysis
   yang mampu melakukan structured cross-paper reasoning untuk mengidentifikasi
   commonalities, differences, dan contradictions dari multiple papers, dengan
   memanfaatkan RAG untuk mencegah hallucination dan ensure factual grounding?

   Permasalahan ini muncul karena existing multi-document analysis systems
   masih struggle dalam melakukan true synthesis dibandingkan extractive
   summarization (Nallapati et al., TACL 2024). LLM-only approaches memiliki
   keterbatasan context window dan rentan hallucination (Chelli et al., 2024),
   sementara traditional keyword-based comparison tidak dapat capture semantic
   relationships. Diperlukan framework yang combine semantic understanding via
   LLM dengan factual grounding via RAG untuk structured comparative analysis.

2. Bagaimana mengembangkan framework deteksi synthesis research gaps—yaitu gaps
   yang emerge dari comparing dan combining insights across multiple papers—
   dengan mengintegrasikan text-based analysis dan lightweight knowledge graph
   untuk mengidentifikasi unexplored combinations, bridging opportunities, dan
   contradictions yang memerlukan resolution?

   Existing gap detection mostly fokus pada explicit gaps (stated limitations)
   atau implicit gaps (absence patterns) dari individual papers (Zhang et al.,
   2025). Namun, valuable research opportunities seringkali emerge dari
   cross-paper comparison: Method A dari Paper 1 + Domain B dari Paper 2 =
   unexplored combination. Framework untuk systematic detection synthesis gaps
   belum extensively studied. Lightweight knowledge graph dapat provide
   structured representation untuk facilitate identification unexplored
   combinations tanpa kompleksitas full ontology (Abu-Salih et al., 2024).

3. Bagaimana menghasilkan research recommendations yang actionable dengan
   clear justification dan supporting evidence dari papers yang dianalisis,
   serta bagaimana melakukan comprehensive evaluation terhadap kualitas
   comparative analysis dan synthesis gap detection melalui expert assessment
   dan comparison dengan baseline approaches?

   Research recommendations harus bukan hanya list generic gaps, tetapi
   actionable directions dengan clear methodology suggestions dan feasibility
   assessment. Lebih lanjut, evaluation framework untuk assessing quality
   synthesis gaps masih limited—diperlukan metrics dan protocol yang
   appropriate untuk measuring relevance, novelty, dan feasibility synthesis
   gaps via expert evaluation dan baseline comparisons.
```

---

## 1.3 Tujuan Penelitian

### ❌ **HAPUS TUJUAN LAMA (5 poin yang terlalu teknis)**

### ✅ **GANTI DENGAN 4 TUJUAN BARU (Aligned dengan Rumusan Masalah):**

```
Berdasarkan rumusan masalah di atas, penelitian ini memiliki tujuan sebagai
berikut:

1. Merancang dan mengimplementasikan algoritma comparative multi-paper analysis
   yang mampu melakukan structured cross-paper reasoning untuk mengidentifikasi
   commonalities (shared concepts, methods), differences (unique contributions),
   dan contradictions (conflicting findings), dengan memanfaatkan RAG untuk
   ensure factual grounding dan prevent hallucination.

   Target: Comparative analysis accuracy ≥ 80% (expert validation untuk
   correctness of identified commonalities, differences, contradictions)

2. Mengembangkan framework untuk deteksi synthesis research gaps yang emerge
   dari comparing multiple papers, dengan mengintegrasikan:
   a. Text-based analysis untuk identifying unexplored combinations dan
      bridging opportunities
   b. Lightweight knowledge graph construction (Paper-Concept-Method
      relationships) untuk graph-based gap detection
   c. Three-level gap taxonomy: Explicit, Implicit, dan Synthesis gaps

   Target: Synthesis gap detection dengan expert-rated relevance ≥ 4.0/5.0,
   novelty ≥ 3.5/5.0, feasibility ≥ 3.5/5.0

3. Mengembangkan recommendation engine yang menghasilkan actionable research
   directions dengan clear justification, methodology suggestions, dan
   supporting evidence dari analyzed papers, berdasarkan detected gaps
   (particularly synthesis gaps).

   Target: Recommendation usefulness rating ≥ 4.0/5.0 (user study)

4. Melakukan comprehensive evaluation melalui:
   a. Quantitative experiments: Precision, Recall, F1-score untuk gap detection;
      comparison dengan baselines (LLM-only, single-paper analysis)
   b. Expert assessment: Gap quality evaluation oleh 3-5 domain experts dengan
      inter-rater reliability (Cohen's Kappa ≥ 0.70)
   c. User study: Usability testing dengan 10-15 researchers; System Usability
      Scale (SUS) ≥ 70
   d. Statistical analysis: Hypothesis testing untuk validating benefits
      comparative analysis, RAG, dan knowledge graph (significance α = 0.05)

   Target: Publikasi hasil penelitian di conference atau journal internasional
```

---

## 1.4 Batasan Penelitian

### ✏️ **SIMPLIFY & REFOCUS (Hapus yang terlalu detail, fokus ke essentials):**

```
Untuk memfokuskan penelitian dan memastikan hasil yang optimal, penelitian ini
memiliki batasan-batasan sebagai berikut:

1. Cakupan Domain dan Temporal
   a. Domain: Computer Science, khususnya sub-domain Artificial Intelligence,
      Machine Learning, Natural Language Processing, dan Information Retrieval

      Justifikasi: Domain-specific focus memungkinkan penggunaan specialized
      embeddings (SciBERT) dan evaluation dengan domain experts yang focused.

   b. Periode publikasi: 2015-2025 (10 tahun terakhir)

      Justifikasi: Memastikan relevansi temporal dan currency dari research gaps.

   c. Bahasa: English

      Justifikasi: Mayoritas publikasi ilmiah CS menggunakan English; pre-trained
      scientific language models (SciBERT) optimized untuk English.

2. Input Papers (BUKAN Fokus Penelitian)
   a. Jumlah papers per analysis session: 3-10 papers

      Justifikasi: Based on cognitive load considerations dan practical
      usability. Too few (< 3) = limited comparative insights; too many (> 10) =
      cognitive overload untuk user review results.

   b. Paper input methods: Manual upload (PDF) atau search & selection
      (via integrated APIs)

      Justifikasi: Providing flexibility untuk users. Paper acquisition
      mechanism BUKAN fokus penelitian—penelitian dimulai SETELAH papers
      tersedia.

   c. Paper sources: arXiv, Semantic Scholar, ACM Digital Library, IEEE Xplore,
      PubMed Central, CORE, CrossRef, Europe PMC

      Justifikasi: Multi-source integration ensures comprehensive coverage.

   PENTING: Paper retrieval dan selection BUKAN kontribusi penelitian ini.
   Research focus adalah apa yang terjadi SETELAH papers sudah tersedia:
   comparative analysis, gap detection, dan recommendation generation.

3. Arsitektur Sistem dan Teknologi
   a. RAG Framework:
      - Vector database: ChromaDB (persistent storage)
      - Embeddings: SciBERT (domain-specific scientific text embeddings)
      - LLM: GPT-4 atau Claude-3.5-Sonnet (untuk experiments & production)
      - Chunking: 512-1024 tokens dengan semantic boundaries

      Justifikasi: Technology stack balance antara performance, cost, dan
      implementation feasibility.

   b. Knowledge Graph:
      - Lightweight approach: Paper + Concepts + Methods only (minimal entity set)
      - NO full ontology engineering
      - NO graph embeddings
      - Storage: NetworkX (in-memory) + optional Neo4j (for visualization)

      Justifikasi: Full ontology construction memerlukan extensive effort dan
      expertise (Abu-Salih et al., 2024). Lightweight approach provides semantic
      insights tanpa requiring comprehensive ontology engineering, achievable
      dalam master's thesis timeline.

   c. Gap Detection:
      - Three-level taxonomy: Explicit, Implicit, Synthesis
      - Synthesis gaps = CORE NOVELTY
      - Focus on text-based + graph-based detection
      - NO traditional topic modeling (LDA/BERTopic) → LLM extraction sufficient
      - NO temporal citation network analysis → Out of scope

      Justifikasi: Focusing on synthesis gap detection (novel contribution)
      rather than comprehensive gap taxonomy. Traditional methods like topic
      modeling dapat be replaced by LLM-based extraction dengan comparable or
      better results.

4. Evaluasi dan Validasi
   a. Test dataset: 100-200 queries dengan ground truth annotations

      Justifikasi: Sample size sufficient untuk statistical validity based on
      power analysis (power ≥ 0.80, α = 0.05).

   b. Expert evaluators: 3-5 domain experts (dosen/peneliti senior CS)

      Justifikasi: Minimum 3 experts untuk reliable inter-rater agreement
      (Cohen's Kappa).

   c. User study participants: 10-15 researchers (mahasiswa S2/S3, dosen muda)

      Justifikasi: Sufficient untuk usability evaluation dan qualitative insights.

   d. Baseline comparisons:
      - Baseline 1: LLM-only (without RAG)
      - Baseline 2: Single-paper analysis (no multi-paper comparison)
      - Baseline 3: Fully-automated (no human guidance/verification)

      Justifikasi: These baselines isolate contributions dari each component
      (RAG, comparative analysis, human guidance).

5. Timeline dan Resources
   a. Implementation & evaluation: 6-8 bulan

   b. Target publication: 1 conference/journal paper internasional

   c. Deployment: Local/cloud for evaluation purposes (not production-ready
      commercial system)

   Justifikasi: Realistic timeline untuk master's thesis dengan publication goal.
```

---

## 1.5 Manfaat Penelitian

### ✏️ **MINOR EDITS (Keep struktur, update focus):**

```
Penelitian ini diharapkan memberikan manfaat baik secara teoretis maupun praktis:

1. Manfaat Teoretis

   a. Kontribusi terhadap Multi-Document Synthesis Research
      Framework comparative multi-paper analysis yang dikembangkan memberikan
      contribution terhadap addressing current limitations dalam multi-document
      summarization, specifically dalam performing true synthesis vs extractive
      aggregation (Nallapati et al., TACL 2024).

   b. Novel Concept: Synthesis Research Gaps
      Penelitian ini memperkenalkan dan operationalize concept "synthesis gaps"—
      research opportunities yang emerge dari comparing dan combining insights
      across multiple papers. Taxonomy dan detection algorithm untuk synthesis
      gaps merupakan theoretical contribution yang belum extensively explored
      dalam existing literature.

   c. RAG Application untuk Scholarly Analysis
      Framework RAG-enhanced comparative analysis memberikan insights tentang
      how to effectively combine retrieval-augmented generation dengan
      multi-document reasoning untuk scholarly tasks, extending RAG applications
      beyond typical Q&A or single-document summarization use cases.

   d. Lightweight Knowledge Graph Methodology
      Pendekatan lightweight KG construction (Paper-Concept-Method relationships
      only) demonstrates balanced approach antara semantic richness dan
      implementation feasibility, providing practical alternative untuk full
      ontology engineering approaches.

2. Manfaat Praktis

   a. Untuk Individual Researchers
      - Efisiensi waktu: Estimated 60-80% time savings dalam comparative
        literature analysis phase (based on similar studies: Wang et al., 2025)
      - Comprehensive gap identification: Deteksi synthesis gaps yang might be
        missed dalam manual analysis
      - Actionable recommendations: Research directions dengan clear methodology
        suggestions dan justifications
      - Evidence-based: All gaps supported by actual paper content (no hallucination)

   b. Untuk Research Groups dan Labs
      - Systematic literature monitoring: Regular analysis untuk identifying
        emerging research opportunities
      - Research planning: Data-driven decision making untuk research direction
        prioritization
      - Collaboration opportunities: Identifying areas where combining different
        group's expertise could fill synthesis gaps

   c. Untuk Academic Institutions
      - Research supervision tool: Assisting advisors dalam guiding students'
        literature review dan research planning
      - Strategic research planning: Institutional-level analysis untuk
        identifying high-impact research areas
      - Resource allocation: Data-driven decisions untuk research funding
        priorities

   d. Untuk Broader Scientific Community
      - Accelerated knowledge discovery: Faster identification of research
        opportunities accelerates scientific progress
      - Interdisciplinary research: Synthesis gaps often cross disciplinary
        boundaries, facilitating interdisciplinary collaborations
      - Reproducible research: Open-source implementation enables community
        adoption dan extension
```

---

# 🎯 REVISI BAB II: TINJAUAN PUSTAKA

## 2.1 State of The Art

### ✏️ **REDUCE dari 10 → 7 papers paling relevan & ADD novelty comparison**

### ❌ **HAPUS Papers Ini (Kurang Relevan):**
- No. 3 (Ayala-Gómez - Citation recommendation, bukan gap detection)
- No. 5 (Huang - Generic topic modeling)
- No. 6 (Shi - Video recommendation, not relevant)
- No. 9 (Bolanos - Literature review automation, too broad)
- No. 10 (Fang - Conversational recommender, not relevant)

### ✅ **KEEP & EXPAND Papers Ini:**
1. Agarwal et al. (2024) - **LitLLM** [MOST RELEVANT]
2. Wang et al. (2025) - **LLM Agents for RecSys**
3. Zhang et al. (2025) - **Gap detection in biomedical** [CORE]
4. Abu-Salih et al. (2024) - **KG construction**
5. Du et al. (2022) - **Academic Paper KG**

### ➕ **ADD New Papers (Comparative Analysis & Multi-Doc):**
6. Nallapati et al. (2024) - **Multi-Doc Summarization Synthesis** [KEY]
7. Huang et al. (2025) - **Human-in-the-loop AI** [VALIDATION]

### ✏️ **UPDATED TABLE FORMAT dengan Novelty Gap Column:**

```
Tabel 1. State of The Art (Revised)

┌────┬─────────┬────────┬─────────┬────────┬──────────┬────────┬──────────┐
│ No │Peneliti │ Judul  │ Metode  │ Fokus  │ Dataset  │ Hasil  │  Novelty │
│    │ /Tahun  │        │ /Teknik │        │ /Domain  │ /Kontr │   Gap    │
│    │         │        │         │        │          │ ibusi  │vs Kami   │
├────┼─────────┼────────┼─────────┼────────┼──────────┼────────┼──────────┤
│ 1  │Agarwal  │LitLLM: │RAG +    │Auto    │Scientif  │Improved│+ Tidak   │
│    │et al.   │A       │Plan-    │mated   │ic papers │paper   │ada       │
│    │(2024)   │Toolkit │based    │literat │(multi-   │discov  │comparat  │
│    │         │for Sci │Generat  │ure     │domain)   │ery &   │ive       │
│    │         │entific │ion +    │review  │          │coherent│analysis  │
│    │         │Lit     │Debate   │generat │          │review  │+ Tidak   │
│    │         │Review  │Re-      │ion     │          │gener   │ada       │
│    │         │        │ranking  │        │          │ation   │synthesis │
│    │         │        │         │        │          │        │gaps      │
├────┼─────────┼────────┼─────────┼────────┼──────────┼────────┼──────────┤
│ 2  │Wang et  │A Survey│Multi-   │LLM-    │E-commer  │Taxonomy│+ Domain- │
│    │al.      │on LLM- │agent    │powered │ce, Video,│of 3    │specific  │
│    │(2025)   │powered │framewor │recomme │General   │paradigms│untuk     │
│    │         │Agents  │k        │ndation │RecSys    │+ Unified│academic  │
│    │         │for     │(Profile,│systems │          │arch    │research  │
│    │         │RecSys  │Memory,  │        │          │framew  │+ Synthe  │
│    │         │        │Planning │        │          │ork     │sis gaps  │
├────┼─────────┼────────┼─────────┼────────┼──────────┼────────┼──────────┤
│ 3  │Zhang et │Mapping │LLM-     │Identif │Biomedica │First   │+ Cross-  │
│    │al.      │Sci     │based    │ikasi   │l literat │systemat│domain    │
│    │(2025)   │Knowled │inferenc │celah   │ure       │ic eval │(CS vs    │
│    │         │ge Gaps │e untuk  │penelit │          │for gap │biomed)   │
│    │         │in      │explicit │ian     │          │detect  │+ Synthe  │
│    │         │Biomed  │& implic │(resear │          │ion     │sis gap   │
│    │         │Lit     │it gap   │ch gap) │          │        │taxonomy  │
├────┼─────────┼────────┼─────────┼────────┼──────────┼────────┼──────────┤
│ 4  │Nallapat │Do Multi│Multi-   │Multi-  │News,     │Analysi │+ Apply   │
│    │i et al. │-Doc    │doc      │doc     │Scientific│s showing│to        │
│    │(2024)   │Summar  │summariz │synthes │articles  │models  │research  │
│    │         │Models  │ation    │is      │          │struggle│gap       │
│    │         │Synthe  │eval     │evaluat │          │with    │detection │
│    │         │size?   │         │ion     │          │true    │+ Synthe  │
│    │(TACL)   │        │         │        │          │synthes │sis-aware │
│    │         │        │         │        │          │is      │framework │
├────┼─────────┼────────┼─────────┼────────┼──────────┼────────┼──────────┤
│ 5  │Abu-     │System  │Knowledg │Metodol │Education │Compreh │+ Light   │
│    │Salih et │atic Lit│e Graph  │ogi     │al domain │ensive  │weight    │
│    │al.      │Review  │Construc │konstru │(5 bidang)│survey  │approach  │
│    │(2024)   │of KG   │tion     │ksi KG  │          │(83 cita│(tidak    │
│    │         │Constru │(Entity  │        │          │tions)  │full      │
│    │         │ction   │Recog +  │        │          │        │ontology) │
│    │         │        │Relation │        │          │        │+ Aplikas │
│    │         │        │Extract) │        │          │        │i untuk   │
│    │         │        │         │        │          │        │gap       │
│    │         │        │         │        │          │        │detect    │
├────┼─────────┼────────┼─────────┼────────┼──────────┼────────┼──────────┤
│ 6  │Du et al.│Academi │Ontology │Represe │Academic  │Fine-   │+ Minimal │
│    │(2022)   │c Paper │-based   │ntasi   │papers    │grained │entity    │
│    │         │KG:     │KG +     │pengeta │(general) │ontology│set       │
│    │         │Constr  │Semantic │huan    │          │model   │(Paper-   │
│    │         │& Appli │Annotat  │akademi │          │        │Concept-  │
│    │         │cation  │ion      │k       │          │        │Method)   │
│    │         │        │         │        │          │        │+ Gap-    │
│    │         │        │         │        │          │        │focused   │
├────┼─────────┼────────┼─────────┼────────┼──────────┼────────┼──────────┤
│ 7  │Huang et │Applicat│Human-in │HITL    │Medical   │Synergis│+ Apply   │
│    │al.      │ion of  │-the-loop│hybrid  │AI, Scient│tic     │to resear │
│    │(2025)   │HITL    │hybrid   │augment │ific      │human-AI│ch gap    │
│    │(Front   │Hybrid  │augment  │ed      │review    │outperfo│identify  │
│    │AI)      │Aug Int │ed intel │intelli │          │rms full│+ Focus   │
│    │         │        │ligence  │gence   │          │auto    │on gap    │
│    │         │        │         │        │          │        │quality   │
└────┴─────────┴────────┴─────────┴────────┴──────────┴────────┴──────────┘

ANALYSIS GAP PENELITIAN:

Berdasarkan analisis state of the art, ditemukan research gaps berikut:

1. Integrasi Komponen
   - Existing: Components developed separately (RAG, KG, gap detection)
   - Gap: No integrated framework combining RAG + KG + comparative analysis
     specifically untuk synthesis gap detection dari multi-paper analysis
   - Our Contribution: Integrated framework dengan focus on synthesis gaps

2. Comparative Multi-Paper Analysis
   - Existing: LitLLM does automated review (Agarwal et al.)
   - Gap: No structured comparative analysis algorithm; no cross-paper reasoning
   - Our Contribution: Structured comparison (commonalities, differences,
     contradictions) dengan RAG-enhanced synthesis

3. Synthesis Gap Concept
   - Existing: Gap detection mostly explicit (stated limitations) atau implicit
     (absence patterns) dari INDIVIDUAL papers (Zhang et al.)
   - Gap: Concept "synthesis gaps" (gaps emerging from COMPARING multiple
     papers) not extensively studied; no systematic detection framework
   - Our Contribution: Novel taxonomy + algorithm untuk synthesis gap detection
     (unexplored combinations, bridging gaps, resolution gaps)

4. Lightweight Knowledge Graph
   - Existing: Full ontology engineering (Abu-Salih, Du et al.) = complex
   - Gap: No balanced approach (useful insights tanpa full ontology overhead)
   - Our Contribution: Lightweight KG (Paper-Concept-Method only) dengan
     graph-based gap detection algorithm

5. RAG untuk Multi-Document Analysis
   - Existing: RAG mostly untuk Q&A atau single-document summarization
   - Gap: RAG application untuk comparative multi-document analysis dengan
     focus on preventing hallucination dalam synthesis belum explored
   - Our Contribution: RAG-enhanced comparative framework dengan groundedness
     validation

6. Evaluation untuk Synthesis Gaps
   - Existing: No evaluation framework specifically untuk synthesis gap quality
   - Gap: Metrics, protocol, dan ground truth construction untuk synthesis gaps
   - Our Contribution: Expert evaluation rubric, baseline comparisons,
     statistical testing specifically untuk synthesis gap assessment
```

---

## 2.2 Metode yang Digunakan

### 🚨 **MAJOR SIMPLIFICATION (Remove over-complex parts)**

### ✅ **NEW STRUCTURE (Focused & Aligned with Implementation):**

```
2.2 Metode yang Digunakan

Penelitian ini menggunakan pendekatan Design Science Research (DSR) dengan
fokus pada development dan evaluation sistem comparative multi-paper analysis
untuk synthesis gap detection. Metode terdiri dari empat komponen utama:

2.2.1 Comparative Multi-Paper Analysis Framework

a. Input Processing
   - User provides N papers (3-10) via upload atau search & manual selection
   - Document processing: PDF extraction, text cleaning, metadata extraction
   - Chunking: Semantic-aware chunking (512-1024 tokens)
   - Embedding: SciBERT embeddings untuk scientific text
   - Storage: ChromaDB vector database

b. RAG-Enhanced Cross-Paper Retrieval
   Masalah: LLM context window terbatas, cannot process semua papers sekaligus

   Solusi:
   Step 1: Query Formulation
     - System generates comparative queries:
       * "What are the main methods used across these papers?"
       * "What are the key concepts discussed?"
       * "What limitations are mentioned?"

   Step 2: Selective Retrieval
     - RAG retrieves relevant chunks from ALL papers untuk each query
     - Ensures comprehensive coverage without context overflow

   Step 3: Context Assembly
     - Aggregate retrieved chunks with source attribution
     - Prepare structured context untuk LLM synthesis

c. Structured Comparative Analysis

   Algorithm:

   ```
   function ComparativeAnalysis(papers):
       # Step 1: Element Extraction
       elements = {}
       for paper in papers:
           elements[paper.id] = {
               'concepts': ExtractConcepts(paper),
               'methods': ExtractMethods(paper),
               'findings': ExtractFindings(paper),
               'limitations': ExtractLimitations(paper)
           }

       # Step 2: Cross-Paper Comparison
       commonalities = FindCommonalities(elements)
       # Using: Set intersection + semantic similarity

       differences = FindDifferences(elements)
       # Unique contributions per paper

       contradictions = FindContradictions(elements)
       # Conflicting findings via LLM conflict detection

       # Step 3: RAG-Enhanced Synthesis
       context = RAG.retrieve(query="synthesize comparison")
       synthesis = LLM.generate(
           prompt=ComparativePrompt(
               commonalities, differences, contradictions
           ),
           context=context,
           temperature=0.7
       )

       # Step 4: Validation
       groundedness = ValidateGroundedness(synthesis, papers)

       return {
           'commonalities': commonalities,
           'differences': differences,
           'contradictions': contradictions,
           'synthesis': synthesis,
           'groundedness_score': groundedness
       }
   ```

   Prompts (Examples):

   Commonality Detection:
   ```
   Based on these papers, identify shared concepts, methods, or approaches.

   Papers:
   {retrieved_chunks_from_all_papers}

   Output format:
   - Concept: [concept name]
     Present in: [Paper 1, Paper 3, Paper 5]
     Description: ...
   ```

   Difference Detection:
   ```
   Identify unique contributions in each paper that are not found in others.

   Paper contexts:
   {per_paper_contexts}

   Output: For each paper, list unique contributions
   ```

   Contradiction Detection:
   ```
   Analyze these findings and identify any contradictions or disagreements:

   Findings from papers:
   {finding_statements}

   Output: List contradictions with papers involved and explanation
   ```

2.2.2 Synthesis Gap Detection Framework (CORE CONTRIBUTION!)

a. Three-Level Gap Taxonomy

   Level 1: Explicit Gaps
   - Definition: Limitations explicitly stated dalam papers
   - Detection method: Pattern matching + LLM extraction
   - Patterns: "future work", "limitation", "should be explored",
     "remains to be investigated"

   Level 2: Implicit Gaps
   - Definition: Gaps inferred dari absence atau patterns
   - Detection method: Analysis apa yang TIDAK dibahas; trends in coverage
   - Examples:
     * Methodology X discussed in multiple papers tapi never applied to Domain Y
     * Dataset Z mentioned but underutilized

   Level 3: Synthesis Gaps (NOVELTY!)
   - Definition: Gaps yang emerge dari COMPARING multiple papers
   - Detection method: Cross-paper reasoning + graph analysis
   - Types:
     a. Unexplored Combinations
     b. Bridging Gaps
     c. Resolution Gaps

b. Synthesis Gap Detection Algorithm

   Type 1: Unexplored Combinations

   ```
   function DetectUnexploredCombinations(papers, comparative_analysis):
       gaps = []

       # Extract all methods and domains
       methods = ExtractMethods(papers)
       domains = ExtractDomains(papers)

       # Check each combination
       for method in methods:
           for domain in domains:
               # Apakah ada paper yang apply method to domain?
               exists = CheckCombinationExists(method, domain, papers)

               if not exists:
                   # Validate via RAG: truly unexplored?
                   context = RAG.retrieve(
                       query=f"Does {method} applied to {domain} exist?"
                   )

                   if ConfirmUnexplored(context):
                       gaps.append({
                           'type': 'unexplored_combination',
                           'method': method,
                           'domain': domain,
                           'evidence': {
                               'method_from': FindPaperWithMethod(method),
                               'domain_from': FindPaperWithDomain(domain)
                           },
                           'novelty_score': CalculateNovelty(method, domain)
                       })

       return gaps
   ```

   Type 2: Bridging Gaps

   ```
   function DetectBridgingGaps(papers, knowledge_graph):
       gaps = []

       concepts = ExtractConcepts(papers)

       for c1 in concepts:
           for c2 in concepts:
               if c1 != c2:
                   # Check: Ada paper yang connect c1 dengan c2?
                   connected = knowledge_graph.has_path(c1, c2)

                   if not connected:
                       # Potential bridging opportunity
                       gaps.append({
                           'type': 'bridging_gap',
                           'concepts': [c1, c2],
                           'description': f"Connection between {c1} and {c2}",
                           'evidence': {
                               'c1_papers': FindPapersDiscussing(c1),
                               'c2_papers': FindPapersDiscussing(c2)
                           }
                       })

       return gaps
   ```

   Type 3: Resolution Gaps

   ```
   function DetectResolutionGaps(comparative_analysis):
       gaps = []

       contradictions = comparative_analysis['contradictions']

       for contradiction in contradictions:
           gaps.append({
               'type': 'resolution_gap',
               'description': f"Contradiction requires resolution",
               'conflicting_papers': contradiction['papers'],
               'conflicting_claims': contradiction['claims'],
               'potential_resolution_approaches': [
                   'Experimental validation',
                   'Meta-analysis of existing studies',
                   'Theoretical framework reconciliation'
               ]
           })

       return gaps
   ```

c. Gap Validation dan Ranking

   Validation (via RAG):
   - Ensure gap is truly unexplored (check against retrieved context)
   - Ensure gap is supported by evidence dari papers

   Ranking Criteria:
   1. Novelty: Seberapa baru/original (semantic distance dari existing work)
   2. Significance: Potential impact (berdasarkan paper importance, citation)
   3. Feasibility: Seberapa realistic untuk diteliti (complexity assessment)
   4. Clarity: Seberapa well-defined (specificity score)

   Multi-criteria scoring:
   ```
   GapScore = w1*Novelty + w2*Significance + w3*Feasibility + w4*Clarity
   Default weights: w1=0.3, w2=0.3, w3=0.25, w4=0.15
   ```

2.2.3 Lightweight Knowledge Graph Construction

a. Minimal Entity Set
   - Papers (dari user selection)
   - Concepts (key research topics, problems, theories)
   - Methods (algorithms, techniques, approaches)

b. Entity Extraction
   Tools:
   - spaCy scientific NER (en_core_sci_sm model)
   - LLM-based verification untuk ambiguous cases

   ```
   function ExtractEntities(papers):
       entities = {'concepts': set(), 'methods': set()}

       for paper in papers:
           # NER extraction
           doc = nlp(paper.text)  # spaCy scientific model

           for ent in doc.ents:
               if ent.label_ in ['CONCEPT', 'THEORY', 'PROBLEM']:
                   entities['concepts'].add(normalize(ent.text))
               elif ent.label_ in ['METHOD', 'ALGORITHM', 'TECHNIQUE']:
                   entities['methods'].add(normalize(ent.text))

           # LLM verification untuk high-importance entities
           verified = LLM.verify_entities(entities, paper)
           entities.update(verified)

       return entities
   ```

c. Relationship Extraction (Simple Approach)
   Relationships:
   - Paper -[DISCUSSES]-> Concept
   - Paper -[USES]-> Method
   - Concept -[RELATED_TO]-> Concept (via co-occurrence)

   ```
   function BuildRelationships(papers, entities):
       graph = nx.DiGraph()

       # Add nodes
       for paper in papers:
           graph.add_node(paper.id, type='paper', **paper.metadata)

       for concept in entities['concepts']:
           graph.add_node(concept, type='concept')

       for method in entities['methods']:
           graph.add_node(method, type='method')

       # Add edges
       for paper in papers:
           # Paper DISCUSSES Concept (via co-occurrence in sentences)
           paper_concepts = FindConceptsInPaper(paper, entities['concepts'])
           for concept in paper_concepts:
               graph.add_edge(paper.id, concept, relation='DISCUSSES')

           # Paper USES Method
           paper_methods = FindMethodsInPaper(paper, entities['methods'])
           for method in paper_methods:
               graph.add_edge(paper.id, method, relation='USES')

       # Concept RELATED_TO Concept (co-occurrence)
       for c1 in entities['concepts']:
           for c2 in entities['concepts']:
               if c1 != c2:
                   # Check co-occurrence dalam same sentence/paragraph
                   if CoOccurs(c1, c2, papers, window=5):
                       graph.add_edge(c1, c2, relation='RELATED_TO',
                                      weight=CoOccurrenceCount(c1, c2))

       return graph
   ```

d. Graph-Based Gap Detection

   ```
   function GraphBasedGapDetection(knowledge_graph):
       gaps = []

       # Gap Type 1: Underexplored Concepts (low degree)
       for node in knowledge_graph.nodes():
           if knowledge_graph.nodes[node]['type'] == 'concept':
               degree = knowledge_graph.degree(node)
               if degree < 2:  # Threshold
                   gaps.append({
                       'type': 'underexplored_concept',
                       'concept': node,
                       'degree': degree,
                       'reason': f'Only {degree} connection(s) in KG'
                   })

       # Gap Type 2: Missing Method-Concept Combinations
       methods = [n for n,d in knowledge_graph.nodes(data=True)
                  if d['type']=='method']
       concepts = [n for n,d in knowledge_graph.nodes(data=True)
                   if d['type']=='concept']

       for method in methods:
           for concept in concepts:
               # Check: Ada paper yang USES method DAN DISCUSSES concept?
               method_papers = set(knowledge_graph.predecessors(method))
               concept_papers = set(knowledge_graph.predecessors(concept))

               intersection = method_papers & concept_papers

               if not intersection:
                   gaps.append({
                       'type': 'missing_combination',
                       'method': method,
                       'concept': concept,
                       'method_papers': method_papers,
                       'concept_papers': concept_papers
                   })

       return gaps
   ```

2.2.4 Recommendation Generation

a. Research Direction Formulation

   ```
   function GenerateRecommendations(detected_gaps, papers):
       recommendations = []

       for gap in detected_gaps:
           # Generate research question
           rq = FormulateResearchQuestion(gap)

           # Suggest methodology
           methodology = SuggestMethodology(gap, papers)

           # Assess feasibility
           feasibility = AssessFeasibility(gap)

           # Predict contribution
           contribution = PredictContribution(gap)

           recommendation = {
               'gap': gap,
               'research_question': rq,
               'methodology': methodology,
               'feasibility': feasibility,
               'expected_contribution': contribution,
               'supporting_evidence': ExtractEvidence(gap, papers),
               'confidence_score': CalculateConfidence(gap)
           }

           recommendations.append(recommendation)

       # Rank recommendations
       ranked = RankRecommendations(
           recommendations,
           criteria=['novelty', 'significance', 'feasibility']
       )

       return ranked
   ```

b. Justification Generation

   Each recommendation includes:
   - Gap description dengan evidence dari papers
   - Why this gap is important (significance)
   - How to address it (methodology suggestions)
   - Expected outcomes (contribution prediction)
   - Citations from analyzed papers yang support gap

2.2.5 Evaluation Framework

a. Ground Truth Construction
   - Select 100-200 test queries (representative CS topics)
   - Expert annotation:
     * 3-5 domain experts independently analyze same papers
     * Identify expected gaps (explicit, implicit, synthesis)
     * Rate each gap (relevance, novelty, feasibility)
     * Provide justifications

   - Inter-rater reliability:
     * Cohen's Kappa untuk measuring agreement
     * Target: Kappa ≥ 0.70 (substantial agreement)

b. Quantitative Metrics

   Gap Detection Performance:
   - Precision@K: % detected gaps yang valid (dalam top-K)
   - Recall@K: % actual gaps yang terdeteksi (dalam top-K)
   - F1@K: Harmonic mean dari Precision dan Recall

   Gap Quality (Expert-Rated, Likert 1-5):
   - Relevance: Seberapa relevan dengan analyzed papers
   - Novelty: Seberapa baru/original
   - Feasibility: Seberapa realistic untuk diteliti
   - Clarity: Seberapa jelas deskripsi gap

   Target:
   - Mean Relevance ≥ 4.0/5.0
   - Mean Novelty ≥ 3.5/5.0
   - Mean Feasibility ≥ 3.5/5.0

c. Baseline Comparisons

   Baseline 1: LLM-Only (No RAG)
   - Direct LLM prompt dengan paper abstracts
   - No retrieval, prone to hallucination

   Baseline 2: Single-Paper Analysis
   - Analyze each paper independently
   - Aggregate gaps (no synthesis)

   Baseline 3: Fully-Automated (No Verification)
   - System auto-selects papers
   - No human guidance atau verification

   Hypothesis Testing:
   H1: Our System > LLM-Only (gap relevance, p < 0.05)
       → RAG reduces hallucination

   H2: Multi-Paper Comparative > Single-Paper (synthesis gaps detected, p < 0.05)
       → Comparative analysis detects synthesis gaps

   H3: With KG > Without KG (implicit gap recall, p < 0.05)
       → KG improves implicit gap detection

d. User Study

   Participants: 10-15 researchers (S2/S3 students, junior faculty)

   Tasks:
   1. Select research topic
   2. Choose 5 papers (manual selection)
   3. Review system-generated gaps & recommendations
   4. Rate gap quality
   5. Compare with baseline system (LLM-only)
   6. Complete System Usability Scale (SUS) questionnaire

   Measures:
   - Task completion time
   - Gap acceptance rate
   - System preference (our system vs baseline)
   - SUS score (target ≥ 70)
   - Qualitative feedback (semi-structured interview)

e. Statistical Analysis

   Tests:
   - Paired t-test: Comparing our system vs baselines (same queries)
   - Cohen's Kappa: Inter-rater reliability untuk expert annotations
   - One-way ANOVA: Comparing multiple conditions (if > 2 baselines)
   - Effect size: Cohen's d untuk measuring magnitude of improvements

   Significance level: α = 0.05
   Power: Target ≥ 0.80
```

---

## 2.3 Hipotesis

### ✏️ **REVISE TO MATCH NEW FOCUS (3 Hipotesis Focused):**

```
2.3 Hipotesis

Berdasarkan analisis teoritis dan empirical evidence, penelitian ini
merumuskan tiga hipotesis utama:

Hipotesis 1 (H1): Efektivitas RAG dalam Mencegah Hallucination

"Sistem comparative analysis yang menggunakan RAG untuk factual grounding
akan menghasilkan gaps dengan factual accuracy yang secara signifikan lebih
tinggi dibandingkan LLM-only approach tanpa retrieval."

  Operasionalisasi:
  - Dependent Variable: Factual accuracy (% gaps supported by paper evidence)
  - Independent Variable: RAG (dengan RAG vs tanpa RAG)
  - Expected: Accuracy_RAG > Accuracy_LLM-only, p < 0.05

  Measurement:
  - Expert assessment: Untuk setiap detected gap, check apakah supported
    by actual paper content
  - Hallucination rate: % gaps yang NOT supported by papers

  Target: Factual accuracy ≥ 90% untuk RAG system vs ≤ 70% untuk LLM-only

  Theoretical Basis:
  RAG terbukti mengurangi hallucination dan meningkatkan factual accuracy
  dalam various domains (Gaur et al., PLOS Digital Health 2025). Retrieval-
  augmented generation ensures LLM responses grounded dalam actual content.

Hipotesis 2 (H2): Superioritas Comparative Multi-Paper Analysis untuk
                   Synthesis Gap Detection

"Sistem yang melakukan structured comparative analysis dari multiple papers
akan mendeteksi lebih banyak valid synthesis gaps dibandingkan single-paper
aggregation approach."

  Operasionalisasi:
  - Dependent Variable: Number of valid synthesis gaps detected
  - Independent Variable: Analysis approach (comparative vs single-paper)
  - Expected: Synthesis_Gaps_Comparative > Synthesis_Gaps_Single-Paper,
              p < 0.05

  Measurement:
  - Count synthesis gaps detected by each system
  - Expert validation: Which gaps are truly synthesis gaps?
  - Synthesis gap validity rate: % detected synthesis gaps yang valid

  Target:
  - Comparative system detects ≥ 40% more synthesis gaps
  - Validity rate ≥ 75% (ensuring quality, not just quantity)

  Theoretical Basis:
  Multi-document synthesis research shows that comparative analysis reveals
  insights not apparent from individual documents (Nallapati et al., TACL 2024).
  True synthesis requires cross-document reasoning, which single-paper
  aggregation cannot provide.

Hipotesis 3 (H3): Kontribusi Lightweight Knowledge Graph untuk Gap Detection

"Integrasi lightweight knowledge graph (Paper-Concept-Method relationships)
akan meningkatkan detection rate untuk implicit gaps dan unexplored
combinations dibandingkan text-based analysis only."

  Operasionalisasi:
  - Dependent Variable: Implicit gap detection recall
  - Independent Variable: KG usage (with KG vs without KG)
  - Expected: Recall_WithKG > Recall_WithoutKG, p < 0.05

  Measurement:
  - Implicit gap recall: % actual implicit gaps yang terdeteksi
  - Unexplored combination detection rate
  - Comparison: System dengan KG vs system tanpa KG (same papers)

  Target:
  - Recall improvement ≥ 25% untuk implicit gaps
  - Detection rate improvement ≥ 30% untuk unexplored combinations

  Theoretical Basis:
  Knowledge graphs effectively capture semantic relationships yang tidak
  explicit dalam text (Ayala-Gómez et al., 2018). Graph-based analysis dapat
  identify structural patterns (isolated nodes, missing edges) yang correspond
  to research gaps. Lightweight approach balances benefits dengan feasibility
  (Abu-Salih et al., 2024).

Hipotesis Null (H0):
Untuk setiap hipotesis alternatif, H0 menyatakan bahwa tidak ada perbedaan
yang signifikan antara treatment dan control conditions.

Statistical Considerations:
- Significance level: α = 0.05
- Power: Target ≥ 0.80 (adequate untuk detecting medium-large effects)
- Multiple comparison correction: Bonferroni adjustment jika testing > 3 hypotheses
- Effect size reporting: Cohen's d untuk mean differences, untuk interpretability

Validation Approach:
Setiap hipotesis akan di-test melalui:
1. Quantitative experiments dengan ground truth dataset
2. Expert validation untuk gap quality
3. Statistical tests (paired t-test, ANOVA)
4. Replication across multiple query sets untuk robustness
```

---

## 2.4 Kerangka Pikir

### ✏️ **UPDATE DIAGRAM dengan Workflow yang Benar:**

```
┌──────────────────────────────────────────────────────────────────────┐
│                     SISTEM ARCHITECTURE                              │
│           Comparative Multi-Paper Analysis Framework                │
└──────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 1: INPUT (User Provides Papers - NOT RESEARCH FOCUS)        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌──────────────┐              ┌──────────────┐                   │
│   │  Option A:   │              │  Option B:   │                   │
│   │ Upload PDFs  │       OR     │ Search & Pick│                   │
│   │  (3-10)      │              │ Papers (3-10)│                   │
│   └──────────────┘              └──────────────┘                   │
│          │                               │                          │
│          └───────────┬───────────────────┘                          │
│                      ↓                                              │
│              ┌───────────────┐                                      │
│              │  N Papers     │                                      │
│              │  Ready for    │                                      │
│              │  Analysis     │                                      │
│              └───────────────┘                                      │
└─────────────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 2: PROCESSING (RESEARCH FOCUS STARTS HERE!)                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Step 1: Document Processing & RAG Setup                           │
│  ┌────────────────────────────────────────────────┐                │
│  │ • PDF text extraction                          │                │
│  │ • Semantic chunking (512-1024 tokens)          │                │
│  │ • SciBERT embedding generation                 │                │
│  │ • ChromaDB vector storage                      │                │
│  └────────────────────────────────────────────────┘                │
│                      ↓                                              │
│  Step 2: Comparative Analysis (CORE CONTRIBUTION #1)               │
│  ┌────────────────────────────────────────────────┐                │
│  │ RAG-Enhanced Cross-Paper Retrieval             │                │
│  │ • Query: "What methods are used?"              │                │
│  │ • Retrieve relevant chunks from ALL papers     │                │
│  │ • Assemble multi-paper context                 │                │
│  │                                                │                │
│  │ Structured Comparison                          │                │
│  │ • Identify commonalities (shared concepts)     │                │
│  │ • Identify differences (unique contributions)  │                │
│  │ • Detect contradictions (conflicting findings) │                │
│  │                                                │                │
│  │ LLM Synthesis with Grounding Check             │                │
│  │ • Generate comparative synthesis               │                │
│  │ • Validate factual accuracy                    │                │
│  └────────────────────────────────────────────────┘                │
│                      ↓                                              │
│  Step 3: Knowledge Graph Construction (Lightweight)                │
│  ┌────────────────────────────────────────────────┐                │
│  │ Entity Extraction (spaCy Scientific NER)       │                │
│  │ • Papers (nodes)                               │                │
│  │ • Concepts (key topics)                        │                │
│  │ • Methods (algorithms, techniques)             │                │
│  │                                                │                │
│  │ Relationship Building                          │                │
│  │ • Paper -[DISCUSSES]-> Concept                 │                │
│  │ • Paper -[USES]-> Method                       │                │
│  │ • Concept -[RELATED_TO]-> Concept              │                │
│  │                                                │                │
│  │ Graph Storage: NetworkX                        │                │
│  └────────────────────────────────────────────────┘                │
│                      ↓                                              │
│  Step 4: Three-Level Gap Detection (CORE CONTRIBUTION #2)          │
│  ┌────────────────────────────────────────────────┐                │
│  │ Level 1: Explicit Gaps                         │                │
│  │ • Pattern matching ("future work", etc.)       │                │
│  │ • LLM extraction dari limitations sections     │                │
│  │                                                │                │
│  │ Level 2: Implicit Gaps                         │                │
│  │ • Absence detection (what's NOT discussed)     │                │
│  │ • Graph analysis (underexplored concepts)      │                │
│  │                                                │                │
│  │ Level 3: SYNTHESIS GAPS ★ (NOVELTY!)           │                │
│  │ • Unexplored Combinations                      │                │
│  │   (Method A + Domain B = no paper?)            │                │
│  │ • Bridging Gaps                                │                │
│  │   (Concept X & Concept Y not connected?)       │                │
│  │ • Resolution Gaps                              │                │
│  │   (Contradictions need resolution)             │                │
│  └────────────────────────────────────────────────┘                │
│                      ↓                                              │
│  Step 5: Gap Validation & Ranking                                  │
│  ┌────────────────────────────────────────────────┐                │
│  │ Validation (RAG-based)                         │                │
│  │ • Check gap truly unexplored                   │                │
│  │ • Verify evidence support                      │                │
│  │                                                │                │
│  │ Multi-Criteria Ranking                         │                │
│  │ • Novelty score                                │                │
│  │ • Significance score                           │                │
│  │ • Feasibility assessment                       │                │
│  │ • Clarity metric                               │                │
│  └────────────────────────────────────────────────┘                │
│                      ↓                                              │
│  Step 6: Recommendation Generation                                 │
│  ┌────────────────────────────────────────────────┐                │
│  │ For each gap:                                  │                │
│  │ • Formulate research question                  │                │
│  │ • Suggest methodology                          │                │
│  │ • Assess feasibility                           │                │
│  │ • Predict expected contribution                │                │
│  │ • Extract supporting evidence from papers      │                │
│  │ • Generate justification with citations        │                │
│  └────────────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 3: OUTPUT                                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────┐                  │
│  │ RESEARCH GAPS (Categorized & Ranked)         │                  │
│  │                                              │                  │
│  │ 📌 Explicit Gaps (3 items)                   │                  │
│  │    Evidence: [Quotes from Paper 2, Paper 5]  │                  │
│  │                                              │                  │
│  │ 📌 Implicit Gaps (4 items)                   │                  │
│  │    Reasoning: [Absence pattern detected]     │                  │
│  │                                              │                  │
│  │ ⭐ Synthesis Gaps (5 items) ← NOVELTY!       │                  │
│  │    From Papers: [Paper 1 + Paper 3]          │                  │
│  │    Type: Unexplored Combination              │                  │
│  │                                              │                  │
│  │ Rankings:                                    │                  │
│  │ • Novelty: ⭐⭐⭐⭐⭐                          │                  │
│  │ • Significance: ⭐⭐⭐⭐                       │                  │
│  │ • Feasibility: ⭐⭐⭐                          │                  │
│  └──────────────────────────────────────────────┘                  │
│                      ↓                                              │
│  ┌──────────────────────────────────────────────┐                  │
│  │ RESEARCH RECOMMENDATIONS                     │                  │
│  │                                              │                  │
│  │ For Gap #1:                                  │                  │
│  │ • Research Question: "How can Method X..."   │                  │
│  │ • Methodology: [Experimental design]         │                  │
│  │ • Expected Contribution: [Impact statement]  │                  │
│  │ • Supporting Evidence: [Paper citations]     │                  │
│  │ • Confidence: 85%                            │                  │
│  └──────────────────────────────────────────────┘                  │
│                      ↓                                              │
│  ┌──────────────────────────────────────────────┐                  │
│  │ KNOWLEDGE GRAPH VISUALIZATION                │                  │
│  │                                              │                  │
│  │      [Paper1] ──uses──> [Method_A]           │                  │
│  │          │                                   │                  │
│  │       discusses                              │                  │
│  │          │                                   │                  │
│  │          ↓                                   │                  │
│  │    [Concept_X] ──related_to─> [Concept_Y]    │                  │
│  │                                   │          │                  │
│  │                             discussed_by     │                  │
│  │                                   │          │                  │
│  │                                   ↓          │                  │
│  │                              [Paper2]        │                  │
│  │                                              │                  │
│  │ 🔍 Gap: Method_A not applied to Concept_Y    │                  │
│  └──────────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 4: EVALUATION (untuk Validasi Penelitian)                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────┐                  │
│  │ Quantitative Evaluation                      │                  │
│  │ • Precision@10, Recall@10, F1@10             │                  │
│  │ • Gap quality scores (expert-rated)          │                  │
│  │ • Baseline comparisons (LLM-only, etc.)      │                  │
│  └──────────────────────────────────────────────┘                  │
│                      ↓                                              │
│  ┌──────────────────────────────────────────────┐                  │
│  │ Expert Assessment                            │                  │
│  │ • 3-5 domain experts                         │                  │
│  │ • Gap relevance, novelty, feasibility        │                  │
│  │ • Inter-rater reliability (Cohen's Kappa)    │                  │
│  └──────────────────────────────────────────────┘                  │
│                      ↓                                              │
│  ┌──────────────────────────────────────────────┐                  │
│  │ User Study                                   │                  │
│  │ • 10-15 researchers                          │                  │
│  │ • System usability (SUS ≥ 70)                │                  │
│  │ • Qualitative feedback                       │                  │
│  └──────────────────────────────────────────────┘                  │
│                      ↓                                              │
│  ┌──────────────────────────────────────────────┐                  │
│  │ Statistical Analysis                         │                  │
│  │ • Hypothesis testing (t-test, ANOVA)         │                  │
│  │ • Effect size calculation (Cohen's d)        │                  │
│  │ • Results interpretation                     │                  │
│  └──────────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘

KEY NOVELTY POINTS:
1. ⭐ Comparative Multi-Paper Analysis (structured cross-paper reasoning)
2. ⭐ Synthesis Gap Detection (novel taxonomy + algorithm)
3. ⭐ RAG-Enhanced Grounding (prevent hallucination dalam synthesis)
4. ⭐ Lightweight KG (practical balance: insights tanpa full ontology)
```

---

# 📋 QUICK REFERENCE: Apa yang Harus Direvisi

## File: `Draft Proposal.pdf`

### **Halaman Cover:**
- ✏️ **REVISI JUDUL** (pilih salah satu dari 3 opsi - lihat file lengkap)

### **BAB I (Hal 1-8):**
- Latar Belakang:
  - ✅ Paragraf 1-3: **KEEP**
  - ➕ **ADD** 2 paragraf baru (comparative analysis & synthesis gaps)
  - ✏️ **REVISE** paragraf terakhir (closing)

- Rumusan Masalah:
  - ❌ **DELETE ALL** (2 poin lama)
  - ✅ **REPLACE** dengan 3 poin baru (comparative, synthesis, evaluation)

- Tujuan:
  - ❌ **DELETE** (5 poin lama)
  - ✅ **REPLACE** dengan 4 poin baru

- Batasan:
  - ✏️ **SIMPLIFY** (remove over-detail, focus essentials)
  - ➕ **ADD** explicit statement: "Paper selection BUKAN fokus"

- Manfaat:
  - ✅ **MOSTLY OK** - minor edits for alignment

### **BAB II (Hal 9-20):**
- State of Art:
  - ❌ **REMOVE** 5 papers (No. 3, 5, 6, 9, 10)
  - ➕ **ADD** 2 papers baru (Nallapati, Huang HITL)
  - ✏️ **ADD COLUMN** "Novelty Gap vs Kami"

- Metode:
  - 🚨 **MAJOR REVISION**
  - ✏️ Simplify 2.2.1 (RAG pipeline)
  - ➕ **ADD** 2.2.2 (Comparative Analysis - NEW!)
  - ➕ **ADD** 2.2.3 (Synthesis Gap Detection - CORE!)
  - ✏️ Simplify 2.2.4 (Lightweight KG)
  - ❌ Remove over-complex parts (topic modeling, citation network)

- Hipotesis:
  - ❌ **DELETE** 4 hipotesis lama
  - ✅ **REPLACE** dengan 3 baru (RAG, comparative, KG)

- Kerangka Pikir:
  - ✏️ **UPDATE** diagram (new workflow)

### **➕ BAB III (BARU - Hal 21-40):**
- Create entire new chapter (ada di REVISI_PROPOSAL_OLD.md, bagian BAB III lengkap)

---

## 🎯 FILES YANG SUDAH SAYA BUAT:

1. ✅ **REVISI_PROPOSAL.md** (ini file) - Proposal revisi dengan fokus yang benar
2. ✅ **IMPLEMENTATION_VS_PROPOSAL.md** - Mapping implementasi vs proposal
3. ✅ **REVISI_PROPOSAL_OLD.md** (backup) - Versi lama

---

## 📞 NEXT STEPS:

Saya sudah buatkan 2 file comprehensive. Sekarang Anda bisa:

1. **Review** REVISI_PROPOSAL.md ini (fokus yang benar)
2. **Review** IMPLEMENTATION_VS_PROPOSAL.md (apa yang harus ditambah ke implementasi)
3. **Tanya** jika ada yang perlu klarifikasi
4. **Minta** saya buatkan:
   - [ ] BAB III lengkap dalam .docx
   - [ ] Diagram kerangka pikir (visual)
   - [ ] Template evaluation (ground truth annotation)
   - [ ] Outline paper untuk publikasi
   - [ ] Implementation roadmap detail

**Mana yang mau dikerjakan dulu?** 🚀
