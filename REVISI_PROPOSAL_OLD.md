# 📝 DOKUMEN REVISI PROPOSAL TESIS

**Tanggal:** 20 Desember 2025
**Status:** Draft Revisi untuk Hybrid Approach (Balanced + High Novelty)
**Target:** Publikasi Jurnal/Conference Internasional

---

## 📋 RINGKASAN PERUBAHAN

### **Filosofi Revisi:**
- ✅ **Tetap fokus** pada use case asli: Search → Manual Select → Analyze → Recommend
- ✅ **Tambah novelty** untuk publikasi internasional:
  - Human-in-the-loop multi-paper synthesis
  - RAG-enhanced comparative gap analysis
  - Lightweight knowledge graph
- ✅ **Simplify** komponen yang terlalu kompleks
- ✅ **Achievable** dalam 6-8 bulan

---

## 🎯 HALAMAN JUDUL

### ❌ **JUDUL LAMA (Terlalu Panjang & Generic):**
```
INTELLIGENT RESEARCH GAP ANALYZER: SISTEM OTOMATIS BERBASIS
RAG DAN LLM UNTUK GENERASI REKOMENDASI PENELITIAN LANJUTAN
DARI ANALISIS JURNAL
```

### ✅ **JUDUL BARU (Focused + Highlight Novelty):**

**Pilihan 1 (Recommended):**
```
SISTEM ANALISIS RESEARCH GAP BERBASIS HUMAN-IN-THE-LOOP
DAN RAG-LLM: PENDEKATAN COMPARATIVE SYNTHESIS UNTUK
REKOMENDASI PENELITIAN DARI MULTI-PAPER

HUMAN-IN-THE-LOOP RESEARCH GAP ANALYZER BASED ON RAG-LLM:
A COMPARATIVE SYNTHESIS APPROACH FOR RESEARCH RECOMMENDATIONS
FROM MULTIPLE PAPERS
```

**Pilihan 2 (Alternative):**
```
INTEGRASI HUMAN EXPERTISE DAN RAG-ENHANCED LLM UNTUK
DETEKSI RESEARCH GAP MELALUI ANALISIS COMPARATIVE MULTI-PAPER

INTEGRATING HUMAN EXPERTISE WITH RAG-ENHANCED LLM FOR
RESEARCH GAP DETECTION VIA COMPARATIVE MULTI-PAPER ANALYSIS
```

**Pilihan 3 (Short & Punchy):**
```
HUMAN-GUIDED MULTI-PAPER SYNTHESIS MENGGUNAKAN RAG DAN
LIGHTWEIGHT KNOWLEDGE GRAPH UNTUK IDENTIFIKASI RESEARCH GAP

HUMAN-GUIDED MULTI-PAPER SYNTHESIS USING RAG AND LIGHTWEIGHT
KNOWLEDGE GRAPHS FOR RESEARCH GAP IDENTIFICATION
```

**💡 Rekomendasi:** Pilihan 1 - karena menyebutkan 3 novelty points (human-in-the-loop, RAG-LLM, comparative synthesis)

---

# BAB I: PENDAHULUAN

## 1.1 Latar Belakang

### ✏️ **REVISI PARAGRAF 1-3** (Keep struktur, tambah emphasis pada human-in-the-loop)

**PARAGRAF 4 - TAMBAH SETELAH RAG EXPLANATION:**

➕ **INSERT PARAGRAF BARU:**
```
Meskipun RAG telah terbukti efektif dalam meningkatkan akurasi LLM,
pendekatan fully automated masih memiliki keterbatasan dalam konteks
academic research gap identification. Penelitian menunjukkan bahwa
human-in-the-loop (HITL) approaches yang menggabungkan human expertise
dengan AI capabilities lebih efektif dibandingkan full automation
(Huang et al., 2025). Domain experts memiliki kemampuan unik dalam
menilai relevansi paper berdasarkan judul dan abstrak, sementara AI
unggul dalam processing dan synthesis informasi dari multiple sources.
Synergistic combination antara human paper selection dengan AI-powered
multi-document analysis dapat menghasilkan research gap identification
yang lebih berkualitas.

Salah satu tantangan dalam automated research gap detection adalah
kemampuan untuk melakukan comparative analysis across multiple papers.
Existing systems umumnya menganalisis paper secara individual atau
melakukan simple aggregation tanpa true synthesis (Do Multi-Document
Summarization Models Synthesize?, TACL 2024). Padahal, research gaps
yang paling valuable seringkali muncul dari comparative understanding—
ketika peneliti membandingkan multiple approaches, identifying patterns,
contradictions, atau unexplored combinations. Kemampuan untuk melakukan
cross-paper reasoning dan identifying synthesis gaps (gaps yang muncul
dari kombinasi insights across papers) menjadi critical success factor.
```

### ✏️ **REVISI PARAGRAF TERAKHIR (Closing Latar Belakang):**

**❌ HAPUS/GANTI PARAGRAF INI:**
```
Dengan mempertimbangkan potensi dan limitasi dari berbagai pendekatan
yang telah ada, penelitian ini bertujuan untuk mengembangkan "Sistem
Rekomendasi Penelitian Lanjutan Berbasis RAG dan LLM dari Analisis
Multi-Jurnal untuk Identifikasi Research Gap" yang mengintegrasikan
state-of-the-art technologies dalam satu framework komprehensif...
```

**✅ GANTI DENGAN:**
```
Dengan mempertimbangkan potensi dan limitasi dari berbagai pendekatan
yang telah ada, penelitian ini mengusulkan novel approach yang
menggabungkan three key innovations: (1) human-in-the-loop framework
untuk leveraging domain expertise dalam paper selection, (2) RAG-enhanced
comparative analysis untuk multi-document synthesis tanpa halusinasi,
dan (3) lightweight knowledge graph untuk capturing semantic relationships
tanpa kompleksitas full ontology construction.

Pendekatan synergistic ini diharapkan dapat menghasilkan research gap
identification yang lebih relevan, novel, dan feasible dibandingkan
pendekatan fully manual atau fully automated. Sistem yang dikembangkan
akan memungkinkan researchers untuk efficiently analyze multiple papers
yang mereka pilih sendiri, dengan AI providing deep comparative synthesis
dan identifying gaps yang mungkin terlewatkan dalam manual analysis.
```

---

## 1.2 Rumusan Masalah

### ❌ **HAPUS RUMUSAN MASALAH LAMA:**

```
1. Bagaimana merancang dan mengimplementasikan arsitektur sistem berbasis
   RAG dan LLM yang mampu melakukan retrieval, analisis, dan sintesis
   informasi dari multi-jurnal secara simultan untuk mengidentifikasi
   research gap dengan tingkat akurasi dan relevansi yang tinggi?

2. Bagaimana mengembangkan mekanisme deteksi dan klasifikasi research gap
   yang mampu mengidentifikasi baik explicit maupun implicit gaps dengan
   memanfaatkan knowledge graphs, topic modeling, dan temporal citation
   network analysis?
```

### ✅ **GANTI DENGAN RUMUSAN MASALAH BARU (3 Pertanyaan Focused):**

```
Berdasarkan latar belakang yang telah diuraikan, penelitian ini
merumuskan tiga permasalahan utama sebagai berikut:

1. Bagaimana merancang dan mengimplementasikan sistem human-in-the-loop
   yang mengintegrasikan manual paper selection dengan RAG-enhanced
   multi-document synthesis untuk identifikasi research gap, sehingga
   menghasilkan output yang lebih relevan dan grounded dibandingkan
   pendekatan fully automated?

   Permasalahan ini muncul karena existing systems umumnya fully automated
   (tidak memanfaatkan human expertise dalam paper selection) atau fully
   manual (tidak mendapat benefit dari AI synthesis). Penelitian terbaru
   menunjukkan bahwa human-in-the-loop approaches lebih efektif (Huang et
   al., 2025), namun belum ada framework yang secara systematic
   mengintegrasikan human paper selection dengan RAG-enhanced comparative
   analysis untuk research gap detection.

2. Bagaimana mengembangkan algoritma comparative gap analysis yang mampu
   mengidentifikasi explicit gaps (stated limitations), implicit gaps
   (inferred from absence), dan synthesis gaps (emerging from paper
   combinations) dari multiple papers yang dipilih user dengan
   memanfaatkan RAG untuk mencegah halusinasi?

   Multi-document analysis masih menghadapi tantangan dalam melakukan
   true synthesis dibandingkan extractive summarization (Do Multi-Document
   Summarization Models Synthesize?, TACL 2024). Lebih lanjut, LLM-only
   approaches rentan terhadap halusinasi (Chelli et al., 2024), sementara
   traditional methods tidak dapat mengidentifikasi implicit dan synthesis
   gaps. Diperlukan algoritma yang dapat perform cross-paper comparative
   reasoning dengan factual grounding melalui RAG.

3. Bagaimana lightweight knowledge graph dapat meningkatkan gap detection
   melalui paper relationship analysis tanpa kompleksitas full ontology
   construction, sehingga achievable untuk implementasi namun tetap
   providing semantic insights?

   Full knowledge graph construction dengan ontology mapping memerlukan
   effort yang sangat besar (Abu-Salih et al., 2024), sementara
   citation-only graphs terlalu simple untuk capturing semantic
   relationships (Ayala-Gómez et al., 2018). Perlu balanced approach
   yang dapat extract meaningful relationships (paper-concept,
   paper-method) untuk enhancing gap detection tanpa requiring
   comprehensive ontology engineering.
```

---

## 1.3 Tujuan Penelitian

### ❌ **HAPUS TUJUAN LAMA (3 poin yang terlalu teknis):**

### ✅ **GANTI DENGAN TUJUAN BARU (Aligned dengan Rumusan Masalah):**

```
Berdasarkan rumusan masalah di atas, penelitian ini memiliki tujuan
sebagai berikut:

1. Merancang dan mengimplementasikan sistem human-in-the-loop yang
   mengintegrasikan manual paper selection dengan RAG-enhanced
   multi-document synthesis untuk research gap identification, dengan
   target gap relevance score ≥ 4.0/5.0 dan gap novelty score ≥ 3.5/5.0
   berdasarkan expert evaluation.

2. Mengembangkan algoritma comparative gap analysis yang mampu
   mengidentifikasi explicit gaps, implicit gaps, dan synthesis gaps
   dari multiple user-selected papers, dengan validasi melalui expert
   assessment dan inter-rater reliability measurement (Cohen's Kappa ≥ 0.70).

3. Mengimplementasikan lightweight knowledge graph construction untuk
   capturing paper relationships (paper-concept, paper-method) dan
   evaluating contribution terhadap gap detection performance
   dibandingkan baseline tanpa knowledge graph.

4. Melakukan comprehensive evaluation melalui:
   a. Quantitative metrics: Precision, Recall, F1-score untuk gap detection
   b. Qualitative assessment: Expert evaluation (3-5 domain experts)
      dengan rubric terstandarisasi
   c. Comparative analysis: Benchmarking terhadap baseline systems
      (LLM-only, single-paper, fully-automated)
   d. User study: Usability testing dengan 10-15 user researchers

5. Menghasilkan publikasi ilmiah di conference atau journal internasional
   yang menyajikan findings, contributions, dan evaluation results dari
   sistem yang dikembangkan.
```

---

## 1.4 Batasan Penelitian

### ✏️ **SIMPLIFY & REFOCUS:**

**❌ HAPUS BATASAN INI (Terlalu Detail/Teknis untuk Pendahuluan):**
- 2.a (detail tentang MatSciBERT citations)
- 2.c (panjang explanation tentang Semantic Scholar)
- 3.b, 3.c (terlalu teknis tentang HITL implementation)
- 4.c (minimum sample 500 queries - too specific)
- 6.a, 6.b (terlalu detail tentang gap classification)

**✅ GANTI DENGAN BATASAN YANG LEBIH CONCISE:**

```
Untuk memfokuskan penelitian dan memastikan hasil yang optimal,
penelitian ini memiliki batasan-batasan sebagai berikut:

1. Cakupan Domain dan Temporal
   a. Domain penelitian: Computer Science, khususnya sub-domain Artificial
      Intelligence, Machine Learning, Natural Language Processing, dan
      Information Retrieval
   b. Periode publikasi: 2015-2025 (10 tahun terakhir)
   c. Bahasa publikasi: English

   Justifikasi: Domain-specific focus memungkinkan penggunaan specialized
   embeddings (SciBERT) dan targeted evaluation dengan domain experts.
   Pembatasan temporal memastikan relevansi dan manageability.

2. Sumber Data dan Paper Selection
   a. Sumber jurnal: arXiv, Semantic Scholar API, ACM Digital Library,
      IEEE Xplore, PubMed Central
   b. Jumlah paper per analysis session: 3-10 papers (user-selected)
   c. Paper selection: Manual by user (human-in-the-loop)

   Justifikasi: Multi-source integration memastikan coverage yang luas.
   Batasan 3-10 papers per session based on cognitive load considerations
   dan practical usability.

3. Arsitektur Sistem
   a. RAG Framework: ChromaDB (vector database) + SciBERT embeddings
      + LLM (GPT-4 atau Claude-3.5-Sonnet untuk experiments)
   b. Knowledge Graph: NetworkX-based lightweight graph (paper-concept-method
      relationships only, tidak full ontology)
   c. Gap Classification: 3 categories (explicit, implicit, synthesis gaps)

   Justifikasi: Technology choices balanced antara performance, cost,
   dan implementation feasibility. Lightweight KG approach achievable
   dalam timeline tanpa sacrificing semantic insights.

4. Evaluasi dan Validasi
   a. Expert evaluators: 3-5 domain experts (dosen/peneliti senior di CS)
   b. User study participants: 10-15 user researchers (mahasiswa S2/S3,
      dosen muda)
   c. Test dataset: 100-200 test cases dengan ground truth annotations
   d. Baseline comparisons: LLM-only, single-paper analysis, fully-automated
   e. Statistical significance: α = 0.05 dengan appropriate tests

   Justifikasi: Sample size sufficient untuk statistical validity
   (based on power analysis). Expert + user evaluation provides both
   quality assessment dan practical usability insights.

5. Implementation dan Deployment
   a. Development platform: Python (backend) + React (frontend)
   b. Deployment: Local/cloud deployment untuk evaluation purposes
   c. Timeline: 6-8 bulan untuk full implementation dan evaluation

   Justifikasi: Technology stack mature dan well-supported. Timeline
   realistic untuk master's thesis dengan target publikasi.
```

---

## 1.5 Manfaat Penelitian

### ✅ **MOSTLY OK - Minor Edits:**

**✏️ EDIT BAGIAN MANFAAT TEORETIS:**

```
1. Manfaat Teoretis
   a. Kontribusi terhadap Human-AI Collaboration Research
      Penelitian ini memberikan empirical evidence tentang efektivitas
      human-in-the-loop approach dalam research gap identification,
      memperkaya literature tentang synergistic human-AI collaboration
      untuk knowledge work.

   b. Advancement dalam Multi-Document Synthesis
      Framework comparative analysis yang dikembangkan memberikan
      insights tentang cross-document reasoning dan synthesis gap
      detection, addressing current limitations dalam multi-document
      summarization (TACL 2024).

   c. Lightweight Knowledge Graph Methodology
      Pendekatan lightweight KG construction tanpa full ontology
      engineering memberikan alternative methodology yang lebih
      practical untuk academic paper analysis.
```

**✅ BAGIAN MANFAAT PRAKTIS - KEEP AS IS** (Sudah bagus)

---

# BAB II: TINJAUAN PUSTAKA

## 2.1 State of The Art

### ✏️ **REDUCE & REFOCUS** (Dari 10 paper → 5-7 paper paling relevan)

**❌ HAPUS PAPER INI (Kurang Relevan):**
- No. 3 (Ayala-Gómez - Citation recommendation, bukan gap detection)
- No. 5 (Huang - Topic modeling generic, bukan untuk gap detection)
- No. 6 (Shi - BiLLP untuk video recommendation, not relevant)
- No. 9 (Bolanos - Literature review automation, too broad)
- No. 10 (Fang - MACRS conversational recommender, not relevant)

**✅ KEEP & EXPAND PAPER INI:**
- No. 1 (Agarwal - LitLLM) - **Most Relevant**
- No. 2 (Wang - LLM Agents for RecSys) - **Relevant for architecture**
- No. 4 (Zhang - Gap detection in biomedical) - **Core contribution**
- No. 7 (Abu-Salih - KG construction) - **Relevant for KG component**
- No. 8 (Du - Academic Paper KG) - **Relevant for KG**

**➕ ADD NEW PAPERS (Human-in-the-Loop Focus):**
```
No. 6 (NEW): Huang et al. (2025) - "Application of human-in-the-loop
  hybrid augmented intelligence"
  - Focus: HITL framework
  - Key Finding: Synergistic human-review outperforms fully automated
  - Relevance: Foundation untuk HITL approach
  - Gap: Belum applied to research gap detection

No. 7 (NEW): Chen & Zhang (2025) - "Automated Paper Screening Using LLMs"
  - Focus: LLM untuk literature screening
  - Key Finding: GPT-4 recall 0.894, precision 0.492
  - Relevance: Baseline performance metrics
  - Gap: Single-paper analysis, no synthesis
```

**✏️ REVISI FORMAT TABEL:**

Tambah kolom "**Novelty Gap vs Our Approach**" untuk setiap paper:

```
| No | Peneliti | ... | Keterbatasan/Gap | **Our Novel Contribution** |
|----|----------|-----|------------------|----------------------------|
| 1  | Agarwal  | ... | Belum HITL + comparative | + Human selection + synthesis gaps |
| 2  | Wang     | ... | Not for academic research | + Domain-specific application |
| ...| ...      | ... | ...                      | ...                        |
```

---

## 2.2 Metode yang Digunakan

### 🚨 **MAJOR REVISION NEEDED** (Terlalu Kompleks)

**❌ HAPUS/SIMPLIFY SECTION INI:**

- **2.2.1 Subsection 3** (Multi-Agent LLM Framework dengan 4 modules) → **Too complex**, simplify
- **2.2.2 Subsection 2.b** (Knowledge Graph-based Gap Identification dengan ontology) → **Simplify to lightweight**
- **2.2.3 Subsection 2** (Multi-Criteria Decision Making dengan 5 factors) → **Reduce factors**
- **2.2.5** (Implementation Technology Stack detail) → **Move to Bab III**

**✅ GANTI DENGAN STRUKTUR BARU:**

```
2.2 Metode yang Digunakan

Penelitian ini menggunakan pendekatan Design Science Research (DSR)
dengan fokus pada development dan evaluation sistem human-in-the-loop
untuk research gap detection. Metode penelitian terdiri dari beberapa
komponen utama:

2.2.1 Human-in-the-Loop Framework
   a. User Interface untuk Paper Search dan Selection
      - Multi-source paper search integration
      - Manual selection interface (checkbox-based)
      - Preview functionality (title, abstract, metadata)

   b. Workflow Integration
      - Phase 1: User search dengan query
      - Phase 2: System retrieve papers dari multiple sources
      - Phase 3: User manually select N papers (3-10)
      - Phase 4: System perform comparative analysis
      - Phase 5: Present gaps dengan justification

   c. Justification Generation
      - Provide evidence dari papers yang support gap
      - Citation-backed recommendations
      - Transparency dalam reasoning process

2.2.2 RAG-Enhanced Comparative Analysis
   a. Document Processing Pipeline
      - Fetch selected papers (metadata + full text if available)
      - Text chunking dengan semantic boundaries
      - Embedding generation dengan SciBERT
      - Vector storage dalam ChromaDB

   b. Cross-Paper Retrieval
      - Query-based semantic search across all selected papers
      - Retrieve relevant chunks dari multiple papers
      - Context assembly untuk LLM input

   c. Comparative Synthesis
      - LLM prompt engineering untuk comparative analysis
      - Identify commonalities, differences, contradictions
      - Generate synthesis insights

   d. Gap Detection Algorithm
      Step 1: Explicit Gap Extraction
        - Pattern matching untuk limitation statements
        - "Future work", "limitation", "should be explored"

      Step 2: Implicit Gap Inference
        - Identify topics discussed in some papers but not others
        - Detect methodological approaches not applied to certain domains
        - Find datasets/benchmarks mentioned but underutilized

      Step 3: Synthesis Gap Detection (NOVEL)
        - Compare methods across papers
        - Identify unexplored combinations (Method A + Domain B)
        - Detect contradictions requiring further research

        Formula:
        SynthesisGap(P1, P2, ..., Pn) = {
          UnexploredCombinations(Methods ∪ Domains ∪ Datasets) ∪
          Contradictions(Claims) ∪
          MissingBridges(Concepts)
        }

2.2.3 Lightweight Knowledge Graph Construction
   a. Entity Extraction (Minimal Set)
      Entities:
        - Papers (dari user selection)
        - Concepts (key terms, research topics)
        - Methods (algorithms, techniques)

      Tools: spaCy scientific NER + LLM-based extraction

   b. Relationship Extraction (Simple Relations)
      Relationships:
        - Paper -[DISCUSSES]-> Concept
        - Paper -[USES]-> Method
        - Paper -[ADDRESSES]-> Problem
        - Concept -[RELATED_TO]-> Concept

      Tools: Rule-based + LLM prompting

   c. Graph-Based Gap Detection
      - Isolated nodes = underexplored entities
      - Missing edges = unexplored relationships
      - Low-degree concepts = emerging topics

      Algorithm:
      ```
      function DetectGraphGaps(KG):
          gaps = []

          # Isolated concept nodes
          for concept in KG.concepts:
              if concept.degree < threshold:
                  gaps.add(UnderexploredArea(concept))

          # Missing method-domain combinations
          for method in KG.methods:
              for domain in KG.concepts:
                  if not KG.hasEdge(method, domain):
                      gaps.add(UnexploredCombination(method, domain))

          return gaps
      ```

   d. Graph Storage dan Query
      - Storage: NetworkX (in-memory graph)
      - Optional: Neo4j untuk complex queries
      - Visualization: NetworkX + Matplotlib/vis.js

2.2.4 Evaluation Framework
   a. Ground Truth Construction
      - Select 100-200 test queries
      - Expert annotation untuk expected gaps
      - Inter-rater reliability (3 experts, Cohen's Kappa)

   b. Quantitative Metrics
      - Precision@K: % gaps yang valid dari K generated
      - Recall@K: % actual gaps yang terdeteksi
      - F1-Score: Harmonic mean
      - Gap Quality Scores (expert-rated, Likert 1-5):
        * Relevance: Seberapa relevan dengan papers
        * Novelty: Seberapa baru/original
        * Feasibility: Seberapa dapat diteliti
        * Clarity: Seberapa jelas deskripsi

   c. Baseline Systems
      Baseline 1: LLM-only (tanpa RAG)
      Baseline 2: Single-paper analysis (no synthesis)
      Baseline 3: Fully-automated (no human selection)

      Hypothesis Testing:
      H1: HITL + RAG > LLM-only (gap relevance, p < 0.05)
      H2: Multi-paper > Single-paper (synthesis gaps detected, p < 0.05)
      H3: With KG > Without KG (implicit gaps detected, p < 0.05)

   d. User Study
      - 10-15 participants (mahasiswa S2/S3, dosen muda)
      - Task: Select papers → Review generated gaps → Rate quality
      - Measures: Task time, satisfaction (SUS), perceived usefulness
      - Qualitative: Interview tentang pros/cons

2.2.5 Statistical Analysis
   - Paired t-test untuk comparing dengan baselines
   - ANOVA untuk comparing multiple conditions
   - Cohen's Kappa untuk inter-rater reliability
   - Thematic analysis untuk qualitative feedback
```

---

## 2.3 Hipotesis

### ✏️ **REVISE TO MATCH NEW APPROACH:**

**❌ HAPUS 4 HIPOTESIS LAMA (Terlalu teknis & tidak aligned)**

**✅ GANTI DENGAN 3 HIPOTESIS BARU (Focused & Testable):**

```
2.3 Hipotesis

Berdasarkan analisis teoritis dan empirical evidence dari penelitian
terkait, penelitian ini merumuskan tiga hipotesis utama:

Hipotesis 1 (H1): Efektivitas Human-in-the-Loop + RAG

"Sistem human-in-the-loop yang mengintegrasikan manual paper selection
dengan RAG-enhanced comparative analysis akan menghasilkan research gaps
dengan relevance score yang secara signifikan lebih tinggi dibandingkan
dengan fully-automated LLM-only approach."

  Metrik:
  - Gap Relevance Score (expert-rated, 1-5 scale)
  - Expected: μ(HITL+RAG) > μ(LLM-only), p < 0.05
  - Target: Mean score ≥ 4.0/5.0 untuk HITL+RAG

  Dasar Teori:
  Penelitian Huang et al. (2025) menunjukkan bahwa human-in-the-loop
  approaches dengan synergistic human-AI collaboration outperform
  fully automated systems. RAG terbukti mengurangi halusinasi dan
  meningkatkan factual accuracy (Gaur et al., 2025).

Hipotesis 2 (H2): Superioritas Multi-Paper Comparative Synthesis

"Sistem yang melakukan comparative analysis dari multiple user-selected
papers akan mengidentifikasi lebih banyak synthesis gaps yang valid
dibandingkan dengan single-paper analysis approach."

  Metrik:
  - Number of synthesis gaps detected per session
  - Synthesis gap validity rate (expert verification)
  - Expected: Multi-paper detects ≥ 40% more synthesis gaps, p < 0.05

  Dasar Teori:
  Multi-document synthesis research menunjukkan bahwa comparative analysis
  dapat mengungkapkan insights yang tidak terlihat dari single-document
  analysis (Nallapati et al., TACL 2024). Namun, existing systems masih
  struggle dengan true synthesis vs extraction.

Hipotesis 3 (H3): Kontribusi Lightweight Knowledge Graph

"Integrasi lightweight knowledge graph untuk paper relationship analysis
akan meningkatkan detection rate untuk implicit gaps dibandingkan
text-based analysis only."

  Metrik:
  - Implicit gap detection recall
  - Expected: With KG > Without KG, recall improvement ≥ 25%, p < 0.05

  Dasar Teori:
  Knowledge graphs terbukti efektif dalam capturing semantic relationships
  yang tidak explicit dalam text (Ayala-Gómez et al., 2018; Du et al., 2022).
  Lightweight approach dapat provide benefits tanpa full ontology overhead.

Hipotesis Null (H0):
Untuk setiap hipotesis alternatif, H0 menyatakan bahwa tidak ada
perbedaan signifikan antara treatment dan control conditions.

Statistical Testing:
- Significance level: α = 0.05
- Power analysis: Target power ≥ 0.80
- Multiple comparison correction: Bonferroni adjustment
- Effect size reporting: Cohen's d untuk mean differences
```

---

## 2.4 Kerangka Pikir

### ✏️ **UPDATE DIAGRAM:**

**❌ HAPUS DIAGRAM LAMA** (Terlalu generic, fokus ke RAG pipeline)

**✅ GANTI DENGAN WORKFLOW DIAGRAM BARU:**

```
[Akan saya buatkan diagram baru di file terpisah yang show:
1. User search & manual selection (HITL component)
2. RAG-enhanced comparative analysis
3. Knowledge graph construction
4. Gap detection (3 types)
5. Recommendation with justification

File: KERANGKA_PIKIR_BARU.md]
```

---

# ➕ BAB III: METODOLOGI PENELITIAN (BARU - LENGKAP)

**NOTE: Bab ini TIDAK ADA di draft original Anda. Ini adalah BAB BARU yang HARUS DITAMBAHKAN.**

---

## BAB III
## METODOLOGI PENELITIAN

### 3.1 Desain Penelitian

Penelitian ini menggunakan pendekatan **Design Science Research (DSR)**
yang dikemukakan oleh Hevner et al. (2004) dan Peffers et al. (2007).
DSR merupakan paradigma penelitian yang cocok untuk mengembangkan
artifacts (dalam hal ini: sistem software) yang bertujuan memecahkan
masalah praktis sambil memberikan kontribusi teoretis.

**Framework DSR terdiri dari 6 tahapan:**

```
┌─────────────────────────────────────────────────────────────┐
│  DSR PROCESS MODEL (Peffers et al., 2007)                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Problem         2. Define          3. Design &         │
│     Identification  → Objectives of   → Development        │
│                       Solution                              │
│         ↓                                                   │
│  4. Demonstration  → 5. Evaluation    → 6. Communication   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Pemetaan ke penelitian ini:**

1. **Problem Identification** (Bulan 1)
   - Literature review comprehensive
   - Identifikasi gaps dalam existing systems
   - Definisi problem statement

2. **Define Objectives of Solution** (Bulan 1)
   - Rumusan requirements sistem:
     * Human-in-the-loop paper selection
     * RAG-enhanced comparative analysis
     * Lightweight knowledge graph
     * Gap detection (explicit, implicit, synthesis)
   - Success criteria definition

3. **Design & Development** (Bulan 2-4)
   - System architecture design
   - Component implementation
   - Integration & testing

4. **Demonstration** (Bulan 5)
   - Proof-of-concept dengan sample papers
   - Case studies
   - Alpha testing dengan small user group

5. **Evaluation** (Bulan 5-7)
   - Ground truth construction
   - Quantitative experiments
   - Expert evaluation
   - User study
   - Statistical analysis

6. **Communication** (Bulan 7-8)
   - Thesis writing
   - Conference/journal paper draft
   - Presentation preparation

---

### 3.2 Tahapan Penelitian

Penelitian ini dilaksanakan dalam **5 fase** selama **6-8 bulan**:

#### **FASE 1: Literature Review & Requirement Analysis (Bulan 1)**

**Aktivitas:**
1. Comprehensive literature review:
   - Research gap detection methods
   - RAG architectures
   - Human-in-the-loop systems
   - Multi-document synthesis
   - Knowledge graph construction

2. Requirement gathering:
   - Interview dengan potential users (3-5 researchers)
   - Identifikasi use cases
   - Definisi functional & non-functional requirements

3. Dataset preliminary analysis:
   - Explore available paper sources (arXiv, Semantic Scholar, etc.)
   - API access setup
   - Sample paper collection (100 papers untuk pilot)

**Deliverables:**
- ✅ Literature review report (20-30 papers)
- ✅ System requirements specification (SRS document)
- ✅ Pilot dataset (100 CS papers, 2015-2025)

---

#### **FASE 2: System Design & Architecture (Bulan 1-2)**

**Aktivitas:**
1. Architecture design:
   - High-level system architecture
   - Component diagram
   - Data flow diagram
   - API endpoint design

2. Database schema design:
   - Vector database schema (ChromaDB)
   - Knowledge graph schema (NetworkX/Neo4j)
   - Relational metadata storage (SQLite/PostgreSQL)

3. UI/UX design:
   - Wireframes untuk search interface
   - Paper selection interface mockups
   - Results presentation design

4. Algorithm design:
   - Comparative analysis algorithm pseudocode
   - Gap detection logic (3 types)
   - Graph construction algorithm

**Deliverables:**
- ✅ System architecture document
- ✅ Database schema
- ✅ UI/UX mockups
- ✅ Algorithm specifications

---

#### **FASE 3: Implementation (Bulan 2-4)**

**3.3.1 Sprint 1: Core Infrastructure (Minggu 1-3)**

Implementasi komponen dasar:

```python
# 1. Paper Search Integration
class PaperSearchService:
    def search_papers(self, query: str, sources: List[str]):
        # Multi-source API calls
        # Deduplication
        # Metadata extraction

# 2. RAG Pipeline Setup
class RAGPipeline:
    def __init__(self):
        self.embeddings = SciBERTEmbeddings()
        self.vector_store = ChromaDB(persist_dir="./chroma_db")
        self.llm = LLMService(model="gpt-4")

    def process_papers(self, papers: List[Paper]):
        # Chunking
        # Embedding
        # Storage

# 3. Basic Frontend
- Search page
- Paper list display
- Manual selection (checkbox)
```

**Testing:** Unit tests untuk each component

---

**3.3.2 Sprint 2: Comparative Analysis Engine (Minggu 4-6)**

```python
class ComparativeAnalyzer:
    def analyze_multiple_papers(self, selected_papers: List[Paper]):
        # Step 1: Process all papers via RAG
        chunks = self.rag_pipeline.process_papers(selected_papers)

        # Step 2: Cross-paper retrieval
        contexts = self.retrieve_comparative_contexts(chunks)

        # Step 3: LLM synthesis
        synthesis = self.llm.generate(
            prompt=COMPARATIVE_ANALYSIS_PROMPT,
            context=contexts
        )

        return synthesis

class GapDetector:
    def detect_gaps(self, papers: List[Paper], synthesis: str):
        # Explicit gaps (pattern matching + LLM extraction)
        explicit_gaps = self.extract_explicit_gaps(papers)

        # Implicit gaps (absence detection)
        implicit_gaps = self.infer_implicit_gaps(papers)

        # Synthesis gaps (cross-paper insights)
        synthesis_gaps = self.identify_synthesis_gaps(papers, synthesis)

        return {
            'explicit': explicit_gaps,
            'implicit': implicit_gaps,
            'synthesis': synthesis_gaps
        }
```

**Testing:** Integration tests dengan sample papers

---

**3.3.3 Sprint 3: Lightweight Knowledge Graph (Minggu 7-9)**

```python
class LightweightKGConstructor:
    def __init__(self):
        self.nlp = spacy.load("en_core_sci_sm")  # Scientific NER
        self.graph = nx.DiGraph()

    def extract_entities(self, papers: List[Paper]):
        entities = {
            'concepts': [],
            'methods': [],
            'problems': []
        }

        for paper in papers:
            # NER extraction
            doc = self.nlp(paper.text)

            # Classify entities
            for ent in doc.ents:
                if ent.label_ in ['CONCEPT', 'THEORY']:
                    entities['concepts'].append(ent.text)
                elif ent.label_ in ['METHOD', 'ALGORITHM']:
                    entities['methods'].append(ent.text)

        return entities

    def build_graph(self, papers: List[Paper], entities: Dict):
        # Add nodes
        for paper in papers:
            self.graph.add_node(paper.id, type='paper', **paper.metadata)

        for concept in entities['concepts']:
            self.graph.add_node(concept, type='concept')

        for method in entities['methods']:
            self.graph.add_node(method, type='method')

        # Add edges (via LLM or rules)
        for paper in papers:
            # Paper -[DISCUSSES]-> Concept
            discussed_concepts = self.extract_discussed_concepts(paper)
            for concept in discussed_concepts:
                self.graph.add_edge(paper.id, concept, relation='DISCUSSES')

        return self.graph

    def detect_graph_gaps(self):
        gaps = []

        # Isolated nodes
        for node in self.graph.nodes():
            if self.graph.degree(node) < 2:
                gaps.append({
                    'type': 'underexplored',
                    'entity': node,
                    'reason': 'Low connectivity in knowledge graph'
                })

        # Missing combinations
        methods = [n for n, d in self.graph.nodes(data=True) if d['type'] == 'method']
        concepts = [n for n, d in self.graph.nodes(data=True) if d['type'] == 'concept']

        for method in methods:
            for concept in concepts:
                if not self.graph.has_edge(method, concept):
                    gaps.append({
                        'type': 'unexplored_combination',
                        'method': method,
                        'concept': concept,
                        'reason': 'No research applying this method to this concept'
                    })

        return gaps
```

**Testing:** Graph construction tests, gap detection accuracy

---

**3.3.4 Sprint 4: Frontend Integration & Polish (Minggu 10-12)**

```jsx
// React Components

// 1. Search & Selection
function PaperSelectionPage() {
  const [query, setQuery] = useState('');
  const [papers, setPapers] = useState([]);
  const [selected, setSelected] = useState([]);

  const handleSearch = async () => {
    const results = await api.searchPapers(query);
    setPapers(results);
  };

  const handleAnalyze = async () => {
    const jobId = await api.analyzeSelected(selected);
    navigate(`/results/${jobId}`);
  };

  return (
    <div>
      <SearchBar onSearch={handleSearch} />
      <PaperList
        papers={papers}
        selected={selected}
        onSelect={setSelected}
      />
      <Button onClick={handleAnalyze} disabled={selected.length < 3}>
        Analyze {selected.length} Papers
      </Button>
    </div>
  );
}

// 2. Results Display
function AnalysisResults({ jobId }) {
  const { data, loading } = useAnalysisResults(jobId);

  return (
    <div>
      <Section title="Explicit Gaps">
        {data.explicit_gaps.map(gap => (
          <GapCard gap={gap} evidence={gap.sources} />
        ))}
      </Section>

      <Section title="Implicit Gaps">
        {data.implicit_gaps.map(gap => (
          <GapCard gap={gap} reasoning={gap.inference} />
        ))}
      </Section>

      <Section title="Synthesis Gaps" highlight>
        {data.synthesis_gaps.map(gap => (
          <GapCard gap={gap} papers={gap.from_papers} />
        ))}
      </Section>

      <KnowledgeGraphViz graph={data.knowledge_graph} />
    </div>
  );
}
```

**Testing:** End-to-end tests, usability testing (3-5 users)

---

**Deliverables Fase 3:**
- ✅ Fully functional prototype
- ✅ Unit tests (coverage ≥ 80%)
- ✅ Integration tests
- ✅ Alpha testing report

---

#### **FASE 4: Evaluation Framework & Ground Truth (Bulan 5)**

**Aktivitas:**

**4.1 Ground Truth Dataset Construction**

```
Step 1: Query Selection (Week 1-2)
  - Collect 100-200 research queries dari real researchers
  - Categorize by sub-domain:
    * Machine Learning: 40 queries
    * NLP: 30 queries
    * Computer Vision: 30 queries
  - Ensure diversity (broad topics, specific methods, application domains)

Step 2: Expert Annotation (Week 2-3)
  - Recruit 3-5 domain experts:
    * Dosen senior dengan h-index ≥ 10
    * Active researchers dengan ≥ 5 publications in last 3 years

  - Annotation protocol:
    For each query:
      a. Expert manually selects 5-7 relevant papers
      b. Expert identifies research gaps (explicit, implicit, synthesis)
      c. Expert rates each gap:
         - Relevance: 1-5
         - Novelty: 1-5
         - Feasibility: 1-5
      d. Expert provides justification (text)

  - Inter-rater reliability:
    * 20% overlap untuk Cohen's Kappa calculation
    * Target Kappa ≥ 0.70

Step 3: Ground Truth Compilation
  - Aggregate expert annotations
  - Resolve disagreements (discussion atau third expert)
  - Finalize ground truth dataset
```

**4.2 Baseline System Implementation**

```python
# Baseline 1: LLM-Only (No RAG)
class LLMOnlyBaseline:
    def detect_gaps(self, papers: List[Paper]):
        # Direct LLM call tanpa RAG retrieval
        prompt = f"Identify research gaps from these papers: {papers}"
        gaps = self.llm.generate(prompt)
        return gaps

# Baseline 2: Single-Paper Analysis
class SinglePaperBaseline:
    def detect_gaps(self, papers: List[Paper]):
        gaps = []
        for paper in papers:
            # Analyze each paper independently
            gap = self.analyze_single(paper)
            gaps.append(gap)
        return gaps  # No synthesis!

# Baseline 3: Fully-Automated (No Human Selection)
class FullyAutomatedBaseline:
    def detect_gaps(self, query: str):
        # System auto-selects papers
        papers = self.auto_select_papers(query, top_k=5)
        # Analyze without human intervention
        gaps = self.analyze(papers)
        return gaps
```

**4.3 Evaluation Metrics Implementation**

```python
class EvaluationMetrics:
    def precision_at_k(self, predicted_gaps, ground_truth_gaps, k=10):
        predicted_k = predicted_gaps[:k]
        relevant = [g for g in predicted_k if g in ground_truth_gaps]
        return len(relevant) / k

    def recall_at_k(self, predicted_gaps, ground_truth_gaps, k=10):
        predicted_k = predicted_gaps[:k]
        relevant = [g for g in predicted_k if g in ground_truth_gaps]
        return len(relevant) / len(ground_truth_gaps)

    def f1_score(self, precision, recall):
        return 2 * (precision * recall) / (precision + recall)

    def expert_quality_scores(self, gaps, expert_ratings):
        # Average Likert scores
        avg_relevance = np.mean([r['relevance'] for r in expert_ratings])
        avg_novelty = np.mean([r['novelty'] for r in expert_ratings])
        avg_feasibility = np.mean([r['feasibility'] for r in expert_ratings])

        return {
            'relevance': avg_relevance,
            'novelty': avg_novelty,
            'feasibility': avg_feasibility
        }

    def cohens_kappa(self, rater1, rater2):
        # Inter-rater reliability
        from sklearn.metrics import cohen_kappa_score
        return cohen_kappa_score(rater1, rater2)
```

**Deliverables:**
- ✅ Ground truth dataset (100-200 annotated queries)
- ✅ Baseline systems implemented & tested
- ✅ Evaluation metrics codebase
- ✅ Evaluation protocol document

---

#### **FASE 5: Experiments & Analysis (Bulan 6-7)**

**5.1 Quantitative Experiments**

```
Experiment 1: System Performance Benchmarking
  Goal: Measure Precision@K, Recall@K, F1

  Procedure:
    1. Run all systems (Ours + 3 baselines) on ground truth dataset
    2. For each query:
       - System generates top-10 gaps
       - Compare dengan ground truth
       - Calculate P@10, R@10, F1
    3. Aggregate results across all queries

  Analysis:
    - Mean, std, median untuk each metric
    - Statistical tests (paired t-test):
      * Our system vs Baseline 1 (LLM-only)
      * Our system vs Baseline 2 (Single-paper)
      * Our system vs Baseline 3 (Fully-auto)
    - Effect size (Cohen's d)
    - Significance: p < 0.05

Experiment 2: Gap Quality Assessment
  Goal: Expert evaluation of gap relevance, novelty, feasibility

  Procedure:
    1. Sample 50 queries (stratified by domain)
    2. For each query:
       - Generate gaps dengan our system
       - 3 experts independently rate each gap (1-5 Likert)
    3. Calculate inter-rater reliability (Cohen's Kappa)

  Analysis:
    - Mean quality scores (target: ≥ 4.0 relevance, ≥ 3.5 novelty)
    - Kappa statistic (target: ≥ 0.70)
    - Compare dengan baseline quality scores

Experiment 3: Ablation Study
  Goal: Measure contribution of each component

  Configurations:
    - Full system (HITL + RAG + KG)
    - Without KG (HITL + RAG only)
    - Without RAG (HITL + LLM only)
    - Without HITL (Auto + RAG + KG)

  Metrics: Same as Experiment 1

  Analysis: Which components contribute most?

Experiment 4: Synthesis Gap Detection
  Goal: Validate H2 (multi-paper synthesis superiority)

  Procedure:
    1. Count synthesis gaps detected by:
       - Our system (multi-paper comparative)
       - Baseline 2 (single-paper aggregation)
    2. Expert validation: Are synthesis gaps valid?

  Analysis:
    - Number of synthesis gaps per system
    - Validity rate
    - Statistical comparison
```

**5.2 User Study**

```
Participants: 10-15 user researchers
  - Mahasiswa S2/S3: 7-10 participants
  - Dosen muda (<5 years experience): 3-5 participants
  - Recruitment: Email, poster, incentive (honorarium kecil)

Tasks:
  Task 1: Familiarization (10 mins)
    - Tutorial sistem
    - Practice dengan sample query

  Task 2: Real Research Task (30 mins)
    - User pilih topik research mereka
    - Search & manually select 5 papers
    - Review generated gaps
    - Rate each gap (relevance, novelty, feasibility)
    - Select top 3 gaps they would pursue

  Task 3: Comparative Task (20 mins)
    - Same query, but with baseline system (LLM-only)
    - Compare outputs
    - Preference: Which system better? Why?

Measurements:
  Quantitative:
    - Task completion time
    - Number of papers selected
    - Gap rating scores
    - System preference (ours vs baseline)

  Qualitative:
    - System Usability Scale (SUS) questionnaire
    - Semi-structured interview:
      * What did you like?
      * What was confusing/frustrating?
      * Would you use this in your research?
      * Suggestions for improvement

Analysis:
  - SUS score calculation (target: ≥ 70)
  - Thematic analysis of interview transcripts
  - User preference statistics
```

**5.3 Case Studies (Optional but Recommended)**

```
Select 3-5 specific research domains, e.g.:
  1. "Transfer Learning in Medical Imaging"
  2. "Explainable AI for NLP"
  3. "Federated Learning Privacy"

For each case:
  - Expert researcher in that domain uses system
  - In-depth analysis of generated gaps
  - Validation: Are gaps truly novel and valuable?
  - Follow-up: Did expert pursue any suggested gaps?

Purpose: Rich qualitative evidence for publication
```

**Deliverables:**
- ✅ Experimental results (tables, figures)
- ✅ Statistical analysis report
- ✅ User study report
- ✅ Case study narratives

---

#### **FASE 6: Thesis Writing & Publication (Bulan 7-8)**

**Aktivitas:**

Week 1-2: Results Analysis
  - Data cleaning & visualization
  - Statistical analysis finalization
  - Interpretation of findings

Week 3-4: Thesis Writing
  - BAB IV: Hasil dan Pembahasan
  - BAB V: Kesimpulan dan Saran
  - Abstract & Ringkasan
  - Formatting & proofreading

Week 5-6: Conference/Journal Paper
  - Paper outline
  - Draft sections (Introduction, Related Work, Method, Results, Discussion)
  - Figures & tables preparation
  - Revision based on advisor feedback

Week 7-8: Finalization
  - Thesis submission preparation
  - Presentation slides
  - Paper submission to target venue
  - Demo video (optional)

**Deliverables:**
- ✅ Complete thesis document
- ✅ Conference/journal paper draft
- ✅ Presentation slides
- ✅ Source code repository (GitHub)
- ✅ Demo video

---

### 3.3 Jadwal Penelitian (Gantt Chart)

```
┌────────────────────────────────────────────────────────────────────────┐
│ TIMELINE: 8 Bulan (Januari - Agustus 2025)                            │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│ Fase 1: Literature Review & Requirement                               │
│ ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ (Bulan 1)                         │
│                                                                        │
│ Fase 2: System Design                                                 │
│ ░░░░████░░░░░░░░░░░░░░░░░░░░░░░░░░ (Bulan 1-2)                       │
│                                                                        │
│ Fase 3: Implementation                                                │
│ ░░░░░░░░████████████░░░░░░░░░░░░░░ (Bulan 2-4)                       │
│   Sprint 1: Core Infrastructure                                       │
│   Sprint 2: Comparative Analysis                                      │
│   Sprint 3: Lightweight KG                                            │
│   Sprint 4: Frontend Integration                                      │
│                                                                        │
│ Fase 4: Evaluation Preparation                                        │
│ ░░░░░░░░░░░░░░░░░░░░████░░░░░░░░░░ (Bulan 5)                         │
│   Ground Truth Construction                                           │
│   Baseline Implementation                                             │
│                                                                        │
│ Fase 5: Experiments                                                   │
│ ░░░░░░░░░░░░░░░░░░░░░░░░████████░░ (Bulan 6-7)                       │
│   Quantitative Evaluation                                             │
│   User Study                                                          │
│   Statistical Analysis                                                │
│                                                                        │
│ Fase 6: Writing & Publication                                         │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░████ (Bulan 7-8)                       │
│   Thesis Writing                                                      │
│   Paper Draft                                                         │
│   Submission                                                          │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘

Milestones:
  M1 (End Month 1): Requirements & Design Complete
  M2 (End Month 4): Prototype Working
  M3 (End Month 5): Evaluation Ready
  M4 (End Month 7): Experiments Complete
  M5 (End Month 8): Thesis Submitted
```

---

### 3.4 Technology Stack (Detail)

**Backend:**
```yaml
Language: Python 3.10+

Core Libraries:
  - FastAPI 0.109+          # Web framework
  - Pydantic 2.0+           # Data validation
  - Uvicorn                 # ASGI server

RAG & LLM:
  - LangChain 0.1+          # RAG framework
  - ChromaDB 0.4.22+        # Vector database
  - Sentence-Transformers    # Embeddings
    - Model: allenai/scibert_scivocab_uncased
  - OpenAI API / Anthropic API
    - GPT-4-turbo (untuk experiments)
    - Claude-3.5-Sonnet (alternative)

Knowledge Graph:
  - NetworkX 3.2+           # Graph library
  - spaCy 3.7+              # NER
    - Model: en_core_sci_sm (scientific)
  - Neo4j 5.14 (optional)   # Graph database

Data Processing:
  - NumPy, Pandas           # Data manipulation
  - Scikit-learn            # Metrics, clustering
  - NLTK, spaCy             # NLP preprocessing

Paper APIs:
  - arxiv                   # arXiv API wrapper
  - semanticscholar         # Semantic Scholar API
  - requests                # HTTP client

Testing:
  - Pytest 7.4+             # Testing framework
  - Pytest-asyncio          # Async testing
  - Coverage.py             # Code coverage

Development:
  - Black, Isort            # Code formatting
  - Flake8, MyPy            # Linting, type checking
```

**Frontend:**
```yaml
Framework: React 19.2+ with Vite 5.4+

UI Libraries:
  - Tailwind CSS 3.4+       # Styling
  - Framer Motion 12+       # Animations
  - Lucide React            # Icons
  - Recharts                # Data visualization
  - vis.js / Cytoscape.js   # Graph visualization

State Management:
  - React Context API       # Global state
  - TanStack Query (React Query) # Server state

HTTP Client:
  - Axios 1.13+             # API requests

Routing:
  - React Router DOM 6.30+  # Client-side routing

Development:
  - ESLint, Prettier        # Code quality
  - TypeScript (optional)   # Type safety
```

**DevOps & Deployment:**
```yaml
Containerization:
  - Docker                  # Containerization
  - Docker Compose          # Multi-container orchestration

CI/CD:
  - GitHub Actions          # Automated testing & deployment

Cloud (Production):
  - Option 1: AWS
    - EC2 (compute)
    - S3 (storage)
    - RDS (database)
  - Option 2: Google Cloud
    - Compute Engine
    - Cloud Storage
  - Option 3: DigitalOcean (cost-effective untuk MVP)

Monitoring:
  - Logs: Python logging module
  - Metrics: Prometheus (optional)
  - Error tracking: Sentry (optional)
```

**Development Environment:**
```yaml
IDE: VSCode

Extensions:
  - Python (Microsoft)
  - Pylance
  - ESLint
  - Prettier
  - Docker

Version Control:
  - Git
  - GitHub (repository hosting)
  - Conventional Commits (commit message standard)

Documentation:
  - Markdown (README, docs)
  - Swagger/OpenAPI (API documentation)
  - Jupyter Notebooks (analysis, experiments)
```

---

### 3.5 Risiko dan Mitigasi

| Risiko | Likelihood | Impact | Mitigasi |
|--------|------------|--------|----------|
| **API Rate Limits** (arXiv, Semantic Scholar) | Medium | High | - Caching results<br>- Implement retry with backoff<br>- Use multiple API keys |
| **LLM API Costs** (GPT-4 expensive) | High | Medium | - Use GPT-4 hanya untuk final experiments<br>- Development pakai local LLM (Ollama)<br>- Budget allocation: ~$200-300 |
| **Ground Truth Quality** (Expert disagreement) | Medium | High | - Clear annotation guidelines<br>- Inter-rater reliability checks<br>- Third expert untuk resolve conflicts |
| **Recruitment Difficulty** (User study participants) | Medium | Medium | - Early recruitment<br>- Incentives (honorarium, co-authorship)<br>- Leverage advisor network |
| **KG Complexity** (Relation extraction hard) | High | Medium | - Start simple (rule-based)<br>- Iterate with LLM-based extraction<br>- Fallback: Manual annotation for pilot |
| **Implementation Delays** | Medium | High | - Buffer time dalam timeline<br>- Prioritize MVP features first<br>- Parallel development where possible |
| **Evaluation Dataset Size** (Hard to get 200 annotations) | Medium | Medium | - Start with 100 (still valid)<br>- Stratified sampling untuk maximize coverage<br>- Supplement dengan case studies |

---

### 3.6 Ethical Considerations

**Data Privacy:**
- User queries dan selected papers tidak akan disimpan permanently
- Anonymization untuk user study data
- Compliance dengan institutional IRB (if required)

**Bias & Fairness:**
- Acknowledge potential biases dalam:
  - Paper selection (user bias)
  - LLM outputs (model biases)
  - Expert annotations (domain bias)
- Mitigation: Diverse expert panel, multiple baseline comparisons

**Intellectual Property:**
- Respect copyright untuk papers (no full-text redistribution)
- Proper attribution dalam generated recommendations
- Open-source license untuk code (MIT atau Apache 2.0)

**Responsible AI:**
- Transparency tentang system limitations
- Clear disclosure: AI-assisted, not AI-generated research
- Human-in-the-loop ensures accountability

---

## 📋 SUMMARY: Files yang Harus Direvisi

### File Original: `Draft Proposal.pdf`

**Halaman 1 (Cover):**
- ✏️ Update JUDUL (pilih salah satu dari 3 opsi di atas)

**BAB I (Halaman 1-8):**
- ✏️ Latar Belakang: Tambah 2 paragraf baru (HITL emphasis)
- ✏️ Rumusan Masalah: Replace dengan 3 pertanyaan baru
- ✏️ Tujuan: Replace dengan 5 tujuan baru
- ✏️ Batasan: Simplify & refocus
- ✅ Manfaat: Minor edits only

**BAB II (Halaman 9-20):**
- ✏️ State of Art: Reduce 10→7 papers, add novelty comparison column
- 🚨 Metode: MAJOR revision (simplify components)
- ✏️ Hipotesis: Replace 4→3 hipotesis baru
- ✏️ Kerangka Pikir: New workflow diagram

**➕ BAB III (BARU):**
- Create entire new chapter (halaman 21-40)
- 3.1 Desain Penelitian
- 3.2 Tahapan Penelitian (5 fase)
- 3.3 Jadwal (Gantt chart)
- 3.4 Technology Stack
- 3.5 Risiko & Mitigasi
- 3.6 Ethical Considerations

**Daftar Pustaka:**
- ➕ Add 3-5 new references (HITL, DSR)

---

## 🎯 NEXT ACTIONS

Saya siap membantu Anda:

1. **Buatkan file .docx yang sudah direvisi** untuk Anda tinggal copy-paste?

2. **Buatkan BAB III lengkap** dalam format LaTeX atau Word?

3. **Buatkan diagram baru** untuk Kerangka Pikir (workflow diagram)?

4. **Buatkan template untuk ground truth annotation** (Excel/Google Sheets)?

5. **Buatkan outline paper untuk publikasi** (conference/journal format)?

Mana yang mau saya kerjakan dulu? 🚀
