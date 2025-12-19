# 🔄 MAPPING: IMPLEMENTASI SAAT INI vs PROPOSAL

**Tanggal:** 20 Desember 2025
**Tujuan:** Identifikasi apa yang sudah jalan, apa yang perlu ditambah, dan apa yang perlu direvisi di proposal

---

## 📊 EXECUTIVE SUMMARY

| Aspek | Status Implementation | Status Proposal | Action Needed |
|-------|----------------------|-----------------|---------------|
| **Paper Input** | ✅ Upload PDF + Search API | ❌ Terlalu fokus ke selection | ✏️ Simplify proposal |
| **RAG Pipeline** | ✅ Working (ChromaDB + all-MiniLM) | ⚠️ Specify SciBERT | ✏️ Upgrade embeddings |
| **Comparative Analysis** | ⚠️ Basic (via LLM) | ❌ Not detailed in proposal | ➕ Add to proposal + strengthen implementation |
| **Gap Detection** | ✅ Working (3 types) | ⚠️ Over-complex (with topic modeling, citation network) | ✏️ Simplify proposal, align with implementation |
| **Synthesis Gaps** | ❌ Not explicitly implemented | ❌ Not mentioned in proposal | ➕ **CORE CONTRIBUTION - Add to both!** |
| **Knowledge Graph** | ⚠️ Infrastructure only (NetworkX) | ⚠️ Too ambitious (full ontology) | ✏️ Align to "lightweight" |
| **Recommendations** | ✅ Working | ✅ In proposal | ✅ Good alignment |
| **Multi-Agent** | ✅ 4 agents working | ⚠️ Over-engineered in proposal | ✏️ Simplify proposal |
| **Evaluation** | ❌ Not implemented | ✅ Detailed in proposal | ➕ Need to implement |
| **Frontend** | ✅ Polished UI | ❌ Not mentioned in proposal | ➕ Mention in proposal |

---

## 1️⃣ PAPER INPUT & SELECTION

### **A. Implementasi Saat Ini** ✅

```python
# File: backend/app/services/paper_apis.py

class PaperSearchService:
    """Multi-source paper search integration"""

    SUPPORTED_SOURCES = [
        'arxiv',           # ✅ Working
        'semantic_scholar', # ✅ Working
        'core',            # ✅ Working
        'pubmed',          # ✅ Working
        'crossref',        # ✅ Working
        'europe_pmc',      # ✅ Working
        'ieee',            # ⚠️ API wrapper ready, need key
        'springer'         # ⚠️ API wrapper ready, need key
    ]

    def search_papers(self, query: str, sources: List[str]):
        """Search dari multiple sources, deduplicate, return results"""
        # User dapat list papers
        # User MANUAL pilih (via frontend checkbox)
        pass

# File: backend/app/api/routes/documents.py

@router.post("/api/ingest")
def upload_pdf():
    """User upload PDF langsung"""
    # Extract text, metadata
    # Store di vector DB
    pass

@router.post("/api/upload-and-analyze")
def upload_and_auto_analyze():
    """User upload → auto process → return gaps & recommendations"""
    # Batch processing dengan progress tracking
    pass
```

**Fitur yang Sudah Ada:**
1. ✅ Multi-source search (8 APIs)
2. ✅ Upload PDF manual
3. ✅ Deduplication
4. ✅ Metadata extraction
5. ✅ Bulk upload support
6. ✅ Progress tracking (real-time job status)

**User Flow:**
```
Option 1: Search → User picks papers → Analyze
Option 2: Upload PDFs → Analyze
Option 3: Upload PDFs → Auto-analyze (background job)
```

---

### **B. Proposal Saat Ini** ⚠️

**Masalah:**
- ❌ Terlalu banyak emphasis di "human-in-the-loop paper selection"
- ❌ Mengangkat paper selection sebagai novelty (padahal trivial)
- ❌ Detail tentang API integration (not the point)

**Yang Perlu Direvisi:**
1. ✏️ **Simplify** - Paper input adalah **given** (bukan fokus penelitian)
2. ✏️ **Remove** "human-in-the-loop selection" sebagai novelty
3. ✏️ **Add** - Mention bahwa sistem support multiple input methods (upload/search) sebagai **fitur**, bukan kontribusi

**Revisi untuk Proposal:**
```
1.4 Batasan Penelitian
...
2. Input Papers
   a. Sistem menerima papers dari dua cara:
      - Manual upload (PDF files)
      - Search & selection (via integrated APIs)

   b. Jumlah papers per analysis: 3-10 papers

   c. Paper selection mechanism BUKAN fokus penelitian ini.
      Penelitian dimulai setelah papers sudah tersedia.

   Justifikasi: Paper retrieval & selection adalah solved problem.
   Research contribution fokus pada apa yang terjadi SETELAH papers
   tersedia: comparative analysis, gap detection, dan recommendation.
```

---

## 2️⃣ RAG PIPELINE

### **A. Implementasi Saat Ini** ✅

```python
# File: backend/app/core/retrieval/vector_store.py

class VectorStore:
    def __init__(self):
        self.collection = ChromaDB(
            name="research_papers",
            persist_directory="./chroma_db",
            embedding_function=SentenceTransformerEmbeddings(
                model_name="all-MiniLM-L6-v2"  # ⚠️ Generic, not scientific
            )
        )

    def add_documents(self, documents: List[Document]):
        # Chunking: 512 chars, 50 overlap
        chunks = self.chunk_documents(documents)

        # Embed & store
        self.collection.add(
            documents=chunks,
            metadatas=[...],
            ids=[...]
        )

    def search(self, query: str, top_k: int = 5):
        # Semantic search dengan cosine similarity
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        return results

# File: backend/app/core/retrieval/rag_retriever.py

class RAGRetriever:
    def retrieve_context(self, query: str, documents: List[str]):
        # 1. Semantic search across all documents
        chunks = self.vector_store.search(query, top_k=10)

        # 2. Re-rank by relevance
        ranked = self.rerank(chunks)

        # 3. Get surrounding context
        context = self.get_context_window(ranked, window=2)

        return context
```

**Apa yang Sudah Working:**
1. ✅ ChromaDB vector storage (persistent)
2. ✅ Document chunking (configurable)
3. ✅ Semantic search
4. ✅ Context retrieval untuk LLM
5. ✅ Re-ranking by relevance

**Apa yang Kurang:**
1. ⚠️ **Embeddings bukan domain-specific** (all-MiniLM-L6-v2 = generic)
2. ⚠️ **No sparse retrieval** (hanya dense)
3. ⚠️ **No cross-encoder re-ranking** (hanya simple relevance score)

---

### **B. Proposal Saat Ini** ⚠️

**Di Proposal:**
```
2.2.1 Arsitektur Sistem RAG-LLM Terintegrasi

Embedding Generation: Menggunakan domain-specific embeddings
(SciBERT, MatSciBERT) untuk scientific text

Retrieval: Hybrid approach (dense + sparse) dengan re-ranking
menggunakan cross-encoder untuk improved relevance
```

**Gap:**
- ❌ Implementation pakai all-MiniLM (generic), proposal bilang SciBERT
- ❌ Implementation pakai dense only, proposal bilang hybrid (dense + sparse)
- ❌ Implementation simple re-rank, proposal bilang cross-encoder

**Action Needed:**

**Option A: Update Implementation** (Recommended)
```python
# Upgrade embeddings
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('allenai/scibert_scivocab_uncased')
# or
model = SentenceTransformer('malteos/scincl')  # Citation-focused
```

**Option B: Update Proposal**
```
Simplify proposal:
"Embedding: Sentence-Transformers dengan scientific text optimization"
"Retrieval: Semantic search dengan ChromaDB"
```

**Recommendation:** **Option A** - Upgrade implementation (mudah, high impact)

---

## 3️⃣ COMPARATIVE ANALYSIS

### **A. Implementasi Saat Ini** ⚠️

```python
# File: backend/app/core/agents/research_analyzer.py

class ResearchAnalyzerAgent:
    def analyze_research_domain(self, query: str):
        # Retrieve top 10 papers
        papers = self.retriever.retrieve(query, top_k=10)

        # LLM analysis (basic)
        analysis = self.llm.generate(
            prompt=f"Analyze these papers: {papers}",
            temperature=0.7
        )

        return analysis
```

**Masalah:**
- ⚠️ **Tidak ada comparative analysis eksplisit**
- ⚠️ LLM di-feed semua papers sekaligus, tapi **no structured comparison**
- ⚠️ **No cross-paper reasoning algorithm**

**Apa yang Perlu Ditambah:**

```python
class ComparativeAnalyzer:
    """NEW - Perlu diimplementasikan"""

    def compare_multiple_papers(self, papers: List[Paper]):
        """
        Structured comparative analysis:
        1. Identify commonalities (shared concepts, methods)
        2. Identify differences (unique contributions)
        3. Detect contradictions (conflicting findings)
        4. Generate synthesis
        """

        # Step 1: Extract key elements from each paper
        paper_elements = []
        for paper in papers:
            elements = {
                'concepts': self.extract_concepts(paper),
                'methods': self.extract_methods(paper),
                'findings': self.extract_findings(paper),
                'limitations': self.extract_limitations(paper)
            }
            paper_elements.append(elements)

        # Step 2: Cross-paper comparison
        commonalities = self.find_commonalities(paper_elements)
        differences = self.find_differences(paper_elements)
        contradictions = self.find_contradictions(paper_elements)

        # Step 3: LLM synthesis with structured prompts
        synthesis = self.llm.generate(
            prompt=self.build_comparative_prompt(
                commonalities, differences, contradictions
            ),
            context=self.rag_retriever.get_relevant_chunks(papers)
        )

        return {
            'commonalities': commonalities,
            'differences': differences,
            'contradictions': contradictions,
            'synthesis': synthesis
        }

    def find_commonalities(self, paper_elements):
        """
        Find shared concepts/methods across papers
        Using: Set intersection, semantic similarity
        """
        all_concepts = [p['concepts'] for p in paper_elements]

        # Exact matches
        common_exact = set.intersection(*[set(c) for c in all_concepts])

        # Semantic matches (via embeddings)
        common_semantic = self.semantic_clustering(all_concepts)

        return {
            'exact': common_exact,
            'semantic': common_semantic
        }

    def find_differences(self, paper_elements):
        """Find unique contributions in each paper"""
        differences = []

        for i, paper in enumerate(paper_elements):
            # What's unique to this paper?
            unique_concepts = self.get_unique_elements(
                paper['concepts'],
                other_papers=[p for j, p in enumerate(paper_elements) if j != i]
            )

            differences.append({
                'paper_id': i,
                'unique_contributions': unique_concepts
            })

        return differences

    def find_contradictions(self, paper_elements):
        """Detect conflicting findings"""
        contradictions = []

        # Extract claims from each paper
        all_claims = [self.extract_claims(p) for p in paper_elements]

        # Use LLM to detect contradictions
        for i, claims_i in enumerate(all_claims):
            for j, claims_j in enumerate(all_claims[i+1:], start=i+1):
                conflicts = self.llm.detect_conflicts(claims_i, claims_j)
                if conflicts:
                    contradictions.append({
                        'paper_1': i,
                        'paper_2': j,
                        'conflicts': conflicts
                    })

        return contradictions
```

---

### **B. Proposal Saat Ini** ❌

**Masalah:**
- ❌ **Comparative analysis TIDAK disebutkan secara eksplisit di proposal**
- ❌ Proposal fokus ke RAG pipeline, tapi tidak jelaskan **bagaimana melakukan comparison**

**Yang Perlu Ditambah ke Proposal:**

```
2.2.2 Comparative Multi-Paper Analysis Framework

Penelitian ini mengembangkan framework untuk melakukan comparative
analysis terhadap multiple papers secara structured dan systematic.

a. Comparative Analysis Algorithm

   Input: N papers yang sudah dipilih (3-10 papers)

   Output: Structured comparison report containing:
     - Commonalities (shared concepts, methods, approaches)
     - Differences (unique contributions, novel aspects)
     - Contradictions (conflicting findings, disagreements)
     - Synthesis (integrated understanding)

   Algorithm:

   Step 1: Element Extraction
     For each paper P_i:
       Extract(P_i) → {concepts, methods, findings, limitations}

   Step 2: Cross-Paper Comparison
     Commonalities = Intersection(concepts_1, ..., concepts_n)
                     + SemanticClustering(all_concepts)

     Differences = For each P_i:
                     Unique(P_i) = Elements(P_i) - Elements(others)

     Contradictions = For each pair (P_i, P_j):
                        DetectConflicts(Claims(P_i), Claims(P_j))

   Step 3: RAG-Enhanced Synthesis
     Context = RAG.retrieve(query="compare these papers")
     Synthesis = LLM.generate(
       prompt=ComparativePrompt(commonalities, differences, contradictions),
       context=Context
     )

   Step 4: Validation
     Groundedness_check: Ensure synthesis supported by paper content
     Hallucination_detection: Flag unsupported claims

b. RAG Integration untuk Comparative Analysis

   Masalah: LLM context window terbatas, tidak bisa process semua papers

   Solusi: RAG selective retrieval
     - Query: "What are the main methods used?"
     - Retrieve: Relevant chunks dari SEMUA papers
     - LLM: Synthesize comparison dari retrieved chunks

   Benefits:
     - No hallucination (grounded in retrieved chunks)
     - Can handle arbitrary number of papers
     - Focused comparison (query-driven)

c. Comparative Gap Detection (NOVELTY!)

   Synthesis Gaps = Gaps yang muncul dari COMPARISON, bukan dari
                    individual paper analysis

   Types of Synthesis Gaps:

   1. Unexplored Combinations
      - Paper A uses Method X
      - Paper B studies Domain Y
      → Gap: Method X not applied to Domain Y

   2. Bridging Gaps
      - Paper A: Concept C1 (no relation to C2)
      - Paper B: Concept C2 (no relation to C1)
      → Gap: Connecting C1 and C2 unexplored

   3. Resolution Gaps
      - Paper A: Finding F1
      - Paper B: Contradictory finding F2
      → Gap: Need research to resolve contradiction

   Algorithm:
   ```
   function DetectSynthesisGaps(papers):
       gaps = []

       # Extract elements
       methods = ExtractMethods(papers)
       domains = ExtractDomains(papers)
       concepts = ExtractConcepts(papers)

       # Unexplored combinations
       for m in methods:
           for d in domains:
               if not PaperExists(uses=m, domain=d):
                   gaps.add({
                       'type': 'unexplored_combination',
                       'method': m,
                       'domain': d,
                       'from_papers': [paper_with_m, paper_with_d]
                   })

       # Contradictions
       contradictions = FindContradictions(papers)
       for c in contradictions:
           gaps.add({
               'type': 'resolution_needed',
               'contradiction': c,
               'from_papers': c.papers
           })

       return gaps
   ```
```

**Ini adalah CORE CONTRIBUTION yang harus ada di proposal!**

---

## 4️⃣ GAP DETECTION

### **A. Implementasi Saat Ini** ✅

```python
# File: backend/app/core/agents/gap_detector.py

class GapDetectorAgent:
    def detect_gaps(self, papers: List[Paper], query: str):
        # Retrieve relevant papers
        top_papers = self.retriever.retrieve(query, top_k=10)

        # LLM-based gap detection
        gaps = self.llm.generate(
            prompt=f"""
            Analyze these papers and identify research gaps:

            Papers: {top_papers}

            Identify:
            1. Unexplored areas (what's not studied)
            2. Methodological gaps (methods not applied)
            3. Application gaps (domains not covered)

            Format: List of gaps with justification
            """,
            temperature=0.7
        )

        return self.parse_gaps(gaps)
```

**Apa yang Sudah Working:**
1. ✅ LLM-based gap detection
2. ✅ 3 types: unexplored, methodological, application
3. ✅ Justification generation

**Apa yang Kurang:**
1. ❌ **No explicit "synthesis gap" detection**
2. ❌ **No structured algorithm** (semuanya via LLM prompt)
3. ❌ **No graph-based gap detection** (KG not utilized)
4. ⚠️ Pattern matching untuk "future work" could be better

---

### **B. Proposal Saat Ini** ⚠️

**Di Proposal:**
```
2.2.2 Research Gap Detection Framework

1. Multi-Modal Gap Detection
   a. Explicit Gap Detection:
      - Text mining untuk identify explicit statements
      - Classification menggunakan fine-tuned BERT models

   b. Implicit Gap Detection:
      - Topic modeling (LDA, BERTopic)
      - Citation network analysis
      - Temporal analysis

2. Knowledge Graph-based Gap Identification
   - Concept Coverage Analysis
   - Methodological Gap Analysis
   - Cross-Domain Gap Detection
```

**Gap antara Proposal vs Implementation:**

| Fitur | Proposal | Implementation | Gap |
|-------|----------|----------------|-----|
| Explicit gap detection | Fine-tuned BERT | LLM prompt | ⚠️ Simpler in implementation |
| Topic modeling | LDA + BERTopic | LLM extraction | ⚠️ Not using traditional topic models |
| Citation network | Temporal analysis | Not implemented | ❌ Missing |
| KG-based gaps | 3 analyses | Infrastructure only | ⚠️ Partially implemented |
| **Synthesis gaps** | **NOT MENTIONED** | **NOT IMPLEMENTED** | ❌ **CORE MISSING** |

**Action Needed:**

**Priority 1: Add Synthesis Gap Detection** (Both proposal & implementation)

```python
# Implementation to add:

class SynthesisGapDetector:
    def detect_synthesis_gaps(self, papers: List[Paper],
                             comparative_analysis: Dict):
        """
        Detect gaps that emerge from COMPARING multiple papers
        """
        synthesis_gaps = []

        # Type 1: Unexplored Combinations
        methods = comparative_analysis['all_methods']
        domains = comparative_analysis['all_domains']

        for method in methods:
            for domain in domains:
                # Check: Apakah ada paper yang apply method ke domain?
                if not self.combination_exists(method, domain, papers):
                    synthesis_gaps.append({
                        'type': 'unexplored_combination',
                        'gap': f"{method} not applied to {domain}",
                        'method': method,
                        'domain': domain,
                        'evidence': {
                            'method_from': self.find_paper_with_method(method, papers),
                            'domain_from': self.find_paper_with_domain(domain, papers)
                        },
                        'novelty_score': self.calculate_novelty(method, domain)
                    })

        # Type 2: Bridging Gaps
        concepts = comparative_analysis['all_concepts']

        for c1 in concepts:
            for c2 in concepts:
                if c1 != c2:
                    # Check: Apakah ada paper yang connect c1 dan c2?
                    if not self.concepts_connected(c1, c2, papers):
                        synthesis_gaps.append({
                            'type': 'bridging_gap',
                            'gap': f"Connection between {c1} and {c2} unexplored",
                            'concepts': [c1, c2],
                            'evidence': {
                                'c1_from': self.find_paper_with_concept(c1, papers),
                                'c2_from': self.find_paper_with_concept(c2, papers)
                            }
                        })

        # Type 3: Resolution Gaps (from contradictions)
        contradictions = comparative_analysis['contradictions']

        for contradiction in contradictions:
            synthesis_gaps.append({
                'type': 'resolution_gap',
                'gap': f"Contradiction needs resolution: {contradiction['description']}",
                'papers_involved': contradiction['papers'],
                'conflicting_claims': contradiction['claims']
            })

        return synthesis_gaps
```

**Priority 2: Simplify Proposal** (Remove over-complex parts)

Remove from proposal:
- ❌ Fine-tuned BERT (just use LLM)
- ❌ Traditional topic modeling LDA/BERTopic (LLM extraction cukup)
- ❌ Temporal citation network (too complex, not core)

Keep in proposal:
- ✅ Explicit gap detection (pattern matching + LLM)
- ✅ Implicit gap detection (absence, via LLM reasoning)
- ✅ **ADD: Synthesis gap detection** (core novelty!)
- ✅ KG-based gap detection (lightweight version)

---

## 5️⃣ KNOWLEDGE GRAPH

### **A. Implementasi Saat Ini** ⚠️

```python
# File: backend/app/core/knowledge/graph.py

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()  # NetworkX in-memory

    def add_paper(self, paper: Paper):
        """Add paper node"""
        self.graph.add_node(
            paper.id,
            type='paper',
            title=paper.title,
            authors=paper.authors
        )

    def add_citation(self, from_paper: str, to_paper: str):
        """Add citation edge"""
        self.graph.add_edge(from_paper, to_paper, relation='cites')

    def get_communities(self):
        """Community detection"""
        import networkx.algorithms.community as nx_comm
        communities = nx_comm.greedy_modularity_communities(self.graph)
        return communities
```

**Apa yang Sudah Ada:**
1. ✅ NetworkX infrastructure
2. ✅ Paper nodes
3. ✅ Citation edges
4. ✅ Community detection
5. ✅ Neo4j Docker setup (optional)

**Apa yang Kurang:**
1. ❌ **No concept extraction** (NER tidak ada)
2. ❌ **No method extraction**
3. ❌ **No Paper-Concept-Method relationships**
4. ❌ **No graph-based gap detection algorithm**
5. ❌ **No visualization**

---

### **B. Proposal Saat Ini** ⚠️

**Di Proposal:**
```
2. Knowledge Graph Construction dan Integration

a. Entity Recognition: Automatic extraction entities (authors, concepts,
   methods, datasets) menggunakan Named Entity Recognition (NER)

b. Relation Extraction: Identification relationships menggunakan
   LLM-based relation extraction

c. Ontology Mapping: Mapping extracted entities dan relations ke
   predefined academic ontology

d. Graph Construction: Building knowledge graph dengan Neo4j

e. Graph Embedding: Knowledge graph embeddings untuk enhanced
   semantic search
```

**Gap:**
- Proposal sangat ambitious (full ontology, graph embeddings)
- Implementation hanya basic (paper nodes + citation edges)

**Action Needed:**

**Option A: Strengthen Implementation** (Recommended untuk tesis)

```python
class LightweightKGConstructor:
    """Simplified KG - achievable dalam 6-8 bulan"""

    def __init__(self):
        self.graph = nx.DiGraph()
        self.nlp = spacy.load("en_core_sci_sm")  # Scientific NER

    def extract_entities(self, papers: List[Paper]):
        """Extract minimal entity set: Papers, Concepts, Methods"""
        entities = {
            'papers': [],
            'concepts': set(),
            'methods': set()
        }

        for paper in papers:
            # Paper node
            entities['papers'].append(paper)

            # Extract concepts (via NER)
            doc = self.nlp(paper.text)
            for ent in doc.ents:
                if ent.label_ in ['CONCEPT', 'THEORY', 'PROBLEM']:
                    entities['concepts'].add(ent.text.lower())
                elif ent.label_ in ['METHOD', 'ALGORITHM', 'TECHNIQUE']:
                    entities['methods'].add(ent.text.lower())

        return entities

    def build_graph(self, papers: List[Paper], entities: Dict):
        """Build lightweight graph"""

        # Add nodes
        for paper in papers:
            self.graph.add_node(paper.id, type='paper', **paper.metadata)

        for concept in entities['concepts']:
            self.graph.add_node(concept, type='concept')

        for method in entities['methods']:
            self.graph.add_node(method, type='method')

        # Add relationships (via co-occurrence or LLM)
        for paper in papers:
            # Paper DISCUSSES Concept
            paper_concepts = self.extract_concepts_from_paper(paper)
            for concept in paper_concepts:
                if concept in entities['concepts']:
                    self.graph.add_edge(paper.id, concept, relation='DISCUSSES')

            # Paper USES Method
            paper_methods = self.extract_methods_from_paper(paper)
            for method in paper_methods:
                if method in entities['methods']:
                    self.graph.add_edge(paper.id, method, relation='USES')

        return self.graph

    def detect_graph_gaps(self):
        """Graph-based gap detection"""
        gaps = []

        # Gap 1: Low-degree concepts (underexplored)
        for node, degree in self.graph.degree():
            if self.graph.nodes[node]['type'] == 'concept' and degree < 2:
                gaps.append({
                    'type': 'underexplored_concept',
                    'concept': node,
                    'reason': f'Only {degree} paper(s) discuss this concept'
                })

        # Gap 2: Missing method-concept combinations
        methods = [n for n, d in self.graph.nodes(data=True) if d['type'] == 'method']
        concepts = [n for n, d in self.graph.nodes(data=True) if d['type'] == 'concept']

        for method in methods:
            for concept in concepts:
                # Check: Ada paper yang USES method DAN DISCUSSES concept?
                papers_with_method = [p for p in self.graph.predecessors(method)]
                papers_with_concept = [p for p in self.graph.predecessors(concept)]

                intersection = set(papers_with_method) & set(papers_with_concept)

                if not intersection:
                    gaps.append({
                        'type': 'unexplored_combination',
                        'method': method,
                        'concept': concept,
                        'reason': f'No paper applies {method} to {concept}'
                    })

        return gaps
```

**Option B: Simplify Proposal** (Align dengan lightweight implementation)

```
Revisi proposal:

2.2.3 Lightweight Knowledge Graph Construction

Penelitian ini menggunakan lightweight knowledge graph approach yang
balance antara simplicity dan semantic richness.

Entity Set (Minimal):
  - Papers (dari user selection)
  - Concepts (key research topics, problems)
  - Methods (algorithms, techniques, approaches)

Relationship Types (Simple):
  - Paper -[DISCUSSES]-> Concept
  - Paper -[USES]-> Method
  - Paper -[CITES]-> Paper (optional)

Construction Method:
  - Entity Extraction: spaCy scientific NER + LLM verification
  - Relationship Extraction: Co-occurrence + LLM-based validation
  - NO full ontology mapping (too complex)
  - NO graph embeddings (not needed for gap detection)

Gap Detection via Graph:
  - Isolated nodes = underexplored entities
  - Missing edges = unexplored combinations
  - Low-degree concepts = emerging topics
```

**Recommendation:** **Option A + B** - Implement lightweight KG & simplify proposal

---

## 6️⃣ RECOMMENDATIONS

### **A. Implementasi Saat Ini** ✅

```python
# File: backend/app/core/agents/recommender.py

class RecommenderAgent:
    def recommend(self, query: str, top_k: int = 5, strategy: str = 'hybrid'):
        """
        Generate research recommendations

        Strategies:
        - 'content': Based on semantic similarity
        - 'graph': Based on citation network
        - 'gap_aware': Based on detected gaps
        - 'hybrid': Combination of above
        """

        if strategy == 'content':
            recommendations = self.content_based_recommend(query, top_k)
        elif strategy == 'graph':
            recommendations = self.graph_based_recommend(query, top_k)
        elif strategy == 'gap_aware':
            # Align recommendations dengan detected gaps
            gaps = self.gap_detector.detect_gaps(query)
            recommendations = self.align_with_gaps(gaps, top_k)
        else:  # hybrid
            recommendations = self.hybrid_recommend(query, top_k)

        return recommendations
```

**Apa yang Sudah Ada:**
1. ✅ Multiple recommendation strategies
2. ✅ Gap-aware recommendations
3. ✅ Ranking & scoring
4. ✅ Justification generation

**Apa yang Kurang:**
1. ⚠️ Recommendations mostly for "next papers to read"
2. ⚠️ Tidak ada "research direction recommendations" yang spesifik
3. ⚠️ No methodology suggestions

---

### **B. Proposal Saat Ini** ✅

**Di Proposal:**
```
2.2.3 Recommendation Algorithm

1. Hybrid Recommendation Approach
   a. Content-Based Filtering
   b. Collaborative Filtering
   c. Knowledge Graph-Enhanced
   d. Trend-Aware Recommendation

2. Multi-Criteria Decision Making
   - Research gap significance
   - User expertise level
   - Citation impact prediction
   - Collaboration potential
   - Resource availability
```

**Alignment:** Pretty good!

**Minor Improvement Needed:**

Add to implementation:
```python
class ResearchDirectionRecommender:
    """Generate actionable research directions, not just paper recs"""

    def recommend_research_directions(self, detected_gaps: List[Gap]):
        """
        Input: Detected gaps
        Output: Concrete research directions with methodology
        """
        directions = []

        for gap in detected_gaps:
            direction = {
                'gap': gap,
                'research_question': self.generate_rq(gap),
                'methodology': self.suggest_methodology(gap),
                'expected_contribution': self.predict_contribution(gap),
                'feasibility': self.assess_feasibility(gap),
                'potential_impact': self.estimate_impact(gap)
            }
            directions.append(direction)

        # Rank by multiple criteria
        ranked = self.multi_criteria_ranking(
            directions,
            weights={
                'novelty': 0.3,
                'feasibility': 0.25,
                'impact': 0.25,
                'resources': 0.2
            }
        )

        return ranked
```

---

## 7️⃣ EVALUATION FRAMEWORK

### **A. Implementasi Saat Ini** ❌

**Status:** **NOT IMPLEMENTED**

No code exists for:
- Ground truth construction
- Metrics calculation (Precision@K, Recall@K, NDCG)
- Baseline systems
- Expert evaluation interface
- User study framework

---

### **B. Proposal Saat Ini** ✅

**Di Proposal:**
```
2.2.4 Evaluation Framework

1. Quantitative Metrics
   a. RAG Performance: Precision@k, Recall@k, F1@k, Hit Rate, MRR
   b. Recommendation Quality: NDCG, RMSE, MAE, Coverage, Diversity
   c. Gap Detection: Gap relevance, novelty, feasibility (expert-rated)

2. Qualitative Evaluation
   a. Expert Assessment
   b. User Study
   c. Case Study Analysis
```

**Status:** ✅ **Very detailed in proposal**

**Action Needed:** ➕ **IMPLEMENT ALL OF THIS** (Fase 5-6 bulan)

---

## 8️⃣ MULTI-AGENT SYSTEM

### **A. Implementasi Saat Ini** ✅

```python
# File: backend/app/core/agents/

class CoordinatorAgent:
    """Orchestrates workflow"""

    def __init__(self):
        self.analyzer = ResearchAnalyzerAgent()
        self.gap_detector = GapDetectorAgent()
        self.recommender = RecommenderAgent()

    def process_request(self, query: str, papers: List[Paper]):
        # 1. Analyze research domain
        analysis = self.analyzer.analyze(query, papers)

        # 2. Detect gaps
        gaps = self.gap_detector.detect_gaps(papers, analysis)

        # 3. Generate recommendations
        recommendations = self.recommender.recommend(gaps)

        return {
            'analysis': analysis,
            'gaps': gaps,
            'recommendations': recommendations
        }

# 4 specialized agents:
# - ResearchAnalyzerAgent
# - GapDetectorAgent
# - RecommenderAgent
# - CoordinatorAgent
```

**Apa yang Sudah Ada:**
1. ✅ 4 agents working
2. ✅ Coordinator orchestration
3. ✅ Workflow automation

---

### **B. Proposal Saat Ini** ⚠️

**Di Proposal:**
```
3. Multi-Agent LLM Framework

Unified architecture dengan 4 komponen:
1. Profile Module: User research profile construction
2. Memory Module: Long-term dan short-term memory
3. Planning Module: Strategic planning
4. Action Module: Execution engine
```

**Gap:**
- Implementation punya 4 **task-specific agents** (analyzer, detector, recommender, coordinator)
- Proposal punya 4 **capability modules** (profile, memory, planning, action)
- **Berbeda framework!**

**Action Needed:**

**Option A:** Update proposal to match implementation
```
Revisi:

Sistem menggunakan multi-agent architecture dengan 4 specialized agents:

1. Research Analyzer Agent
   - Analyze research domain dari papers
   - Extract key themes, methodologies
   - Retrieve relevant context via RAG

2. Gap Detector Agent
   - Detect explicit, implicit, synthesis gaps
   - Utilize knowledge graph for gap analysis
   - Rank gaps by significance

3. Recommender Agent
   - Generate research direction recommendations
   - Multi-strategy approach (content, graph, gap-aware)
   - Provide justification & evidence

4. Coordinator Agent
   - Orchestrate workflow
   - Task decomposition & delegation
   - Result aggregation
```

**Option B:** Add modules to implementation
- Add UserProfileService (untuk personalization)
- Add MemoryService (untuk conversation history)
- Add PlanningService (untuk strategic recommendations)

**Recommendation:** **Option A** (simpler, fokus ke task agents)

---

## 9️⃣ FRONTEND/UI

### **A. Implementasi Saat Ini** ✅

```jsx
// File: frontend/src/components/

// Pages:
- UploadPage.jsx         // Drag-and-drop PDF upload
- AnalysisResults.jsx    // Results display dengan real-time polling
- (No search page yet)

// Features:
- ✅ Dark mode toggle
- ✅ Drag-and-drop upload
- ✅ Progress tracking (0-100%)
- ✅ Real-time job status
- ✅ Expandable sections (topics, gaps, recommendations)
- ✅ Language switch (EN/ID)
- ✅ JSON export
- ✅ Beautiful animations (Framer Motion)
```

**Kekuatan:**
1. ✅ Polished UI/UX
2. ✅ Real-time feedback
3. ✅ Bilingual support (bonus!)
4. ✅ Responsive design

**Yang Kurang:**
1. ⚠️ No search page (hanya upload)
2. ⚠️ No manual paper selection UI (checkbox list)
3. ⚠️ No knowledge graph visualization
4. ⚠️ No comparative analysis visualization

---

### **B. Proposal Saat Ini** ❌

**Status:** ❌ **Frontend TIDAK disebutkan sama sekali di proposal**

**Action Needed:** ➕ **Add to proposal as implementation detail**

```
3.4 Implementation Technology Stack

Frontend:
  - Framework: React 19.2 + Vite 5.4
  - UI Library: Tailwind CSS + Framer Motion
  - Features:
    * PDF upload interface (drag-and-drop)
    * Real-time analysis progress tracking
    * Interactive results display
    * Bilingual support (English/Indonesian)
    * Dark mode
    * Export functionality (JSON)
```

---

## 🎯 SUMMARY: GAP ANALYSIS

### **A. Fitur Implemented tapi Tidak di Proposal (BONUS)**

| Fitur | Status | Action |
|-------|--------|--------|
| Multi-source search (8 APIs) | ✅ Implemented | ➕ Mention in proposal |
| Real-time job progress | ✅ Implemented | ➕ Add to proposal |
| Bilingual support (EN/ID) | ✅ Implemented | ➕ Add to proposal |
| Dark mode UI | ✅ Implemented | Optional mention |
| Drag-and-drop upload | ✅ Implemented | ➕ Add to proposal |
| JSON export | ✅ Implemented | Optional mention |

**Recommendation:** Mention these as **system features** (bukan kontribusi utama)

---

### **B. Fitur di Proposal tapi Belum Implemented (NEED TO ADD)**

| Fitur | Priority | Timeline |
|-------|----------|----------|
| **Synthesis gap detection** | 🔴 CRITICAL | Month 3-4 |
| **Comparative analysis algorithm** | 🔴 CRITICAL | Month 3 |
| SciBERT embeddings | 🟡 High | Month 2 |
| Lightweight KG construction | 🟡 High | Month 3-4 |
| Graph-based gap detection | 🟡 High | Month 4 |
| Evaluation framework | 🔴 CRITICAL | Month 5-7 |
| Ground truth dataset | 🔴 CRITICAL | Month 5 |
| Baseline systems | 🔴 CRITICAL | Month 5-6 |
| User study | 🔴 CRITICAL | Month 6-7 |

---

### **C. Proposal Over-Ambitious (SIMPLIFY)**

| Item | Proposal | Recommendation |
|------|----------|----------------|
| Topic modeling | LDA + BERTopic + DTM | ❌ Remove (LLM extraction cukup) |
| Citation network temporal | Required | ❌ Remove (too complex) |
| Full ontology | Required | ✏️ Change to "lightweight KG" |
| Graph embeddings | Required | ❌ Remove (not needed) |
| Cross-encoder re-ranking | Required | ⚠️ Optional (simple relevance OK) |
| Collaborative filtering | Required | ❌ Remove (no user data) |
| Trend forecasting | Required | ❌ Remove (out of scope) |

---

## 📋 RECOMMENDED ACTIONS

### **Phase 1: Align Proposal dengan Reality (Week 1-2)**

1. ✏️ **Revisi fokus proposal:**
   - Remove "human-in-the-loop selection" as novelty
   - **ADD "synthesis gap detection"** as CORE contribution
   - **ADD "comparative multi-paper analysis"** framework
   - Simplify knowledge graph (lightweight only)
   - Remove over-ambitious features

2. ➕ **Add implemented features:**
   - Multi-source paper search
   - Real-time progress tracking
   - Bilingual UI
   - Frontend details

3. ✏️ **Update rumusan masalah, tujuan, hipotesis:**
   - Focus on comparative analysis, synthesis gaps, RAG benefits

---

### **Phase 2: Strengthen Implementation (Month 2-4)**

1. 🔴 **Priority 1: Comparative Analysis Algorithm**
   - Structured comparison (commonalities, differences, contradictions)
   - RAG-enhanced synthesis
   - Cross-paper reasoning

2. 🔴 **Priority 2: Synthesis Gap Detection**
   - Unexplored combinations
   - Bridging gaps
   - Resolution gaps
   - Algorithm implementation

3. 🟡 **Priority 3: Upgrade Embeddings**
   - Switch to SciBERT
   - Test performance improvement

4. 🟡 **Priority 4: Lightweight KG**
   - NER with spaCy scientific
   - Paper-Concept-Method relationships
   - Graph-based gap detection

---

### **Phase 3: Evaluation (Month 5-7)**

1. 🔴 **Build ground truth** (100-200 test cases)
2. 🔴 **Implement baselines** (LLM-only, single-paper, fully-auto)
3. 🔴 **Run experiments** (quantitative + qualitative)
4. 🔴 **User study** (10-15 participants)

---

## 🎓 FINAL RECOMMENDATION

**Untuk Proposal:**
1. ✏️ **Revisi** fokus ke comparative analysis & synthesis gaps (CORE)
2. ✏️ **Simplify** over-ambitious parts
3. ➕ **Add** implemented features (bonus)
4. ✏️ **Align** dengan implementasi yang achievable

**Untuk Implementation:**
1. 🔴 **Add** synthesis gap detection (MUST HAVE)
2. 🔴 **Add** comparative analysis algorithm (MUST HAVE)
3. 🟡 **Upgrade** embeddings ke SciBERT (SHOULD HAVE)
4. 🟡 **Implement** lightweight KG (SHOULD HAVE)
5. 🔴 **Build** evaluation framework (MUST HAVE untuk tesis)

**Timeline:** 6-8 bulan **ACHIEVABLE** dengan prioritization yang tepat!

---

Apakah ada aspek spesifik yang mau saya jelaskan lebih detail? 🚀
