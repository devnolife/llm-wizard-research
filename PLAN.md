# 🎯 IMPLEMENTATION PLAN
## Comparative Multi-Paper Analysis System untuk Synthesis Gap Detection

**Project:** Intelligent Research Gap Analyzer
**Duration:** 6-8 Months
**Target:** Master Thesis + International Publication
**Last Updated:** 20 Desember 2025

---

## 📌 TUJUAN AKHIR SISTEM

### **Core Purpose:**
```
Sistem yang dapat menganalisis multiple papers (3-10) yang dipilih user
untuk mengidentifikasi research gaps—khususnya SYNTHESIS GAPS—yang muncul
dari comparative analysis, dengan memanfaatkan RAG untuk mencegah
hallucination dan lightweight knowledge graph untuk semantic insights.
```

### **Key Features (End State):**

1. **✅ Input Papers** (GIVEN - Already Working)
   - Upload PDF atau search & manual pick
   - 3-10 papers per analysis session
   - **Status:** ✅ Implemented
   - **Note:** BUKAN fokus penelitian

2. **🎯 Comparative Multi-Paper Analysis** (CORE CONTRIBUTION #1)
   - Structured cross-paper reasoning
   - Identify: commonalities, differences, contradictions
   - RAG-enhanced synthesis (grounded, no hallucination)
   - **Status:** ⚠️ Partial (basic via LLM, needs strengthening)
   - **Priority:** 🔴 CRITICAL

3. **⭐ Synthesis Gap Detection** (CORE CONTRIBUTION #2 - NOVELTY!)
   - 3 Types:
     a. Unexplored Combinations (Method A + Domain B)
     b. Bridging Gaps (Concept X ↔ Concept Y)
     c. Resolution Gaps (Contradictions need resolution)
   - **Status:** ❌ Not implemented
   - **Priority:** 🔴 CRITICAL

4. **🔗 Lightweight Knowledge Graph**
   - Entities: Papers + Concepts + Methods (minimal)
   - Relationships: DISCUSSES, USES, RELATED_TO
   - Graph-based gap detection
   - **Status:** ⚠️ Infrastructure only (needs entity extraction)
   - **Priority:** 🟡 HIGH

5. **💡 Research Recommendations**
   - Actionable research directions
   - Methodology suggestions
   - Evidence-backed justifications
   - **Status:** ✅ Basic implemented
   - **Priority:** 🟢 MEDIUM (enhancement)

6. **📊 Evaluation Framework**
   - Ground truth dataset (100-200 queries)
   - Expert evaluation (3-5 experts)
   - Baseline comparisons (LLM-only, single-paper, fully-auto)
   - User study (10-15 participants)
   - **Status:** ❌ Not implemented
   - **Priority:** 🔴 CRITICAL (untuk tesis!)

---

## 🗺️ ROADMAP (6-8 Months)

```
┌─────────────────────────────────────────────────────────────────┐
│ Month 1-2: Foundation & Core Algorithm                         │
│ Month 3-4: Knowledge Graph & Advanced Features                 │
│ Month 5:   Evaluation Framework & Ground Truth                 │
│ Month 6-7: Experiments & Data Collection                       │
│ Month 8:   Analysis, Writing & Submission                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📅 DETAILED TIMELINE

### **MONTH 1-2: Foundation & Comparative Analysis** 🔴

#### **Week 1-2: Upgrade RAG Infrastructure**

**Goal:** Improve retrieval quality dengan domain-specific embeddings

**Tasks:**
- [ ] Replace all-MiniLM-L6-v2 dengan SciBERT
  - Install: `pip install sentence-transformers`
  - Model: `allenai/scibert_scivocab_uncased`
  - Update: `backend/app/core/retrieval/vector_store.py`
- [ ] Test embedding quality (semantic similarity tests)
- [ ] Re-index existing test papers dengan SciBERT
- [ ] Benchmark: Compare retrieval accuracy (old vs new)

**Deliverables:**
- ✅ SciBERT embeddings working
- ✅ Performance comparison report
- ✅ Updated documentation

**Files to Modify:**
```
backend/app/core/retrieval/vector_store.py
backend/app/utils/config_loader.py (update default embedding model)
```

**Code Snippet:**
```python
# backend/app/core/retrieval/vector_store.py

from sentence_transformers import SentenceTransformer

class VectorStore:
    def __init__(self):
        # OLD: self.embedding_model = "all-MiniLM-L6-v2"
        # NEW:
        self.embedding_model = SentenceTransformer(
            'allenai/scibert_scivocab_uncased'
        )

        self.collection = ChromaDB(
            name="research_papers",
            embedding_function=self.embedding_model
        )
```

---

#### **Week 3-4: Comparative Analysis Algorithm**

**Goal:** Implement structured cross-paper reasoning

**Tasks:**
- [ ] Create new module: `backend/app/core/analysis/comparative_analyzer.py`
- [ ] Implement element extraction (concepts, methods, findings)
- [ ] Implement commonality detection (set intersection + semantic similarity)
- [ ] Implement difference detection (unique contributions per paper)
- [ ] Implement contradiction detection (LLM-based conflict analysis)
- [ ] Implement RAG-enhanced synthesis
- [ ] Add groundedness validation

**Deliverables:**
- ✅ ComparativeAnalyzer class functional
- ✅ Unit tests (coverage ≥ 80%)
- ✅ Integration test dengan sample papers

**New File Structure:**
```
backend/app/core/analysis/
├── __init__.py
├── comparative_analyzer.py     # NEW! Main comparative logic
├── element_extractor.py         # NEW! Extract concepts, methods, findings
├── commonality_detector.py      # NEW! Find shared elements
├── difference_detector.py       # NEW! Find unique contributions
└── contradiction_detector.py    # NEW! Detect conflicts
```

**Implementation Outline:**
```python
# backend/app/core/analysis/comparative_analyzer.py

class ComparativeAnalyzer:
    def __init__(self, rag_retriever, llm_service):
        self.rag = rag_retriever
        self.llm = llm_service
        self.extractor = ElementExtractor()

    def analyze(self, papers: List[Paper]) -> ComparativeResult:
        """
        Main comparative analysis pipeline
        """
        # Step 1: Extract elements from each paper
        elements = self.extract_elements(papers)

        # Step 2: Cross-paper comparison
        commonalities = self.find_commonalities(elements)
        differences = self.find_differences(elements)
        contradictions = self.find_contradictions(elements)

        # Step 3: RAG-enhanced synthesis
        context = self.rag.retrieve_comparative_context(papers)
        synthesis = self.llm.generate_synthesis(
            commonalities, differences, contradictions, context
        )

        # Step 4: Validate groundedness
        groundedness_score = self.validate_groundedness(synthesis, papers)

        return ComparativeResult(
            commonalities=commonalities,
            differences=differences,
            contradictions=contradictions,
            synthesis=synthesis,
            groundedness=groundedness_score
        )

    def extract_elements(self, papers):
        """Extract key elements from each paper"""
        return [self.extractor.extract(p) for p in papers]

    def find_commonalities(self, elements):
        """Find shared concepts, methods across papers"""
        # Set intersection + semantic clustering
        pass

    def find_differences(self, elements):
        """Find unique contributions per paper"""
        pass

    def find_contradictions(self, elements):
        """Detect conflicting findings"""
        # LLM-based conflict detection
        pass
```

**Testing:**
```python
# backend/tests/test_comparative_analyzer.py

def test_comparative_analysis_with_sample_papers():
    papers = load_sample_papers(count=5)  # 5 ML papers

    analyzer = ComparativeAnalyzer(rag, llm)
    result = analyzer.analyze(papers)

    # Assertions
    assert len(result.commonalities) > 0
    assert len(result.differences) > 0
    assert result.groundedness >= 0.8  # High factual accuracy
```

---

#### **Week 5-6: API Integration & Frontend**

**Goal:** Expose comparative analysis via API & update UI

**Tasks:**
- [ ] Add API endpoint: `POST /api/comparative-analysis`
- [ ] Update frontend: Show comparative results
- [ ] Add UI sections: Commonalities, Differences, Contradictions
- [ ] Add loading states & progress indicators

**Deliverables:**
- ✅ API endpoint working
- ✅ Frontend displays comparative results
- ✅ E2E test (upload papers → see comparison)

**API Endpoint:**
```python
# backend/app/api/routes/analysis.py

@router.post("/api/comparative-analysis")
async def analyze_papers_comparative(
    request: ComparativeAnalysisRequest
):
    """
    Perform comparative analysis on selected papers

    Request:
    {
        "paper_ids": ["id1", "id2", "id3"],
        "analysis_type": "full"  # or "quick"
    }

    Response:
    {
        "commonalities": [...],
        "differences": [...],
        "contradictions": [...],
        "synthesis": "...",
        "groundedness_score": 0.85
    }
    """
    papers = fetch_papers(request.paper_ids)
    analyzer = ComparativeAnalyzer(rag, llm)
    result = analyzer.analyze(papers)
    return result
```

**Frontend Component:**
```jsx
// frontend/src/components/ComparativeResults.jsx

function ComparativeResults({ analysisId }) {
  const { data, loading } = useComparativeAnalysis(analysisId);

  return (
    <div className="comparative-results">
      <Section title="Commonalities" icon="🔗">
        {data.commonalities.map(item => (
          <CommonalityCard key={item.id} data={item} />
        ))}
      </Section>

      <Section title="Differences" icon="⚡">
        {data.differences.map(item => (
          <DifferenceCard key={item.id} data={item} />
        ))}
      </Section>

      <Section title="Contradictions" icon="⚔️">
        {data.contradictions.map(item => (
          <ContradictionCard key={item.id} data={item} />
        ))}
      </Section>

      <Section title="Synthesis" icon="💡">
        <SynthesisPanel
          text={data.synthesis}
          groundedness={data.groundedness_score}
        />
      </Section>
    </div>
  );
}
```

---

#### **Week 7-8: Refinement & Testing**

**Goal:** Polish comparative analysis & fix issues

**Tasks:**
- [ ] Alpha testing dengan 3-5 test cases
- [ ] Fix bugs & edge cases
- [ ] Optimize performance (reduce API calls, caching)
- [ ] Documentation (API docs, user guide)

**Milestone 1 Complete:** ✅ Comparative Analysis Working

---

### **MONTH 3-4: Synthesis Gap Detection & Knowledge Graph** 🔴

#### **Week 9-10: Synthesis Gap Detection Algorithm**

**Goal:** Implement core novelty - synthesis gap detection!

**Tasks:**
- [ ] Create module: `backend/app/core/gaps/synthesis_detector.py`
- [ ] Implement Type 1: Unexplored Combinations
  - Extract all methods & domains from papers
  - Check: Does any paper combine Method_i with Domain_j?
  - RAG validation: Is combination truly unexplored?
- [ ] Implement Type 2: Bridging Gaps
  - Extract all concepts
  - Check: Are Concept_i and Concept_j connected in any paper?
  - Use KG (if available) untuk path checking
- [ ] Implement Type 3: Resolution Gaps
  - Use comparative analysis contradictions
  - Generate resolution research directions

**Deliverables:**
- ✅ SynthesisGapDetector class
- ✅ Unit tests untuk each gap type
- ✅ Sample outputs validated by manual inspection

**Implementation:**
```python
# backend/app/core/gaps/synthesis_detector.py

class SynthesisGapDetector:
    def __init__(self, rag, llm, kg=None):
        self.rag = rag
        self.llm = llm
        self.kg = kg  # Optional knowledge graph

    def detect_all(self, papers, comparative_analysis):
        """Detect all synthesis gaps"""
        gaps = []

        # Type 1: Unexplored Combinations
        gaps.extend(self.detect_unexplored_combinations(papers))

        # Type 2: Bridging Gaps
        gaps.extend(self.detect_bridging_gaps(papers))

        # Type 3: Resolution Gaps
        gaps.extend(self.detect_resolution_gaps(
            comparative_analysis.contradictions
        ))

        # Validate & rank
        validated_gaps = self.validate_gaps(gaps, papers)
        ranked_gaps = self.rank_gaps(validated_gaps)

        return ranked_gaps

    def detect_unexplored_combinations(self, papers):
        """
        Find Method + Domain combinations not explored in papers
        """
        gaps = []

        # Extract all methods and domains
        methods = set()
        domains = set()

        for paper in papers:
            methods.update(self.extract_methods(paper))
            domains.update(self.extract_domains(paper))

        # Check each combination
        for method in methods:
            for domain in domains:
                # Does any paper apply this method to this domain?
                exists = self.check_combination_exists(
                    method, domain, papers
                )

                if not exists:
                    # RAG validation
                    context = self.rag.retrieve(
                        query=f"research applying {method} to {domain}"
                    )

                    if self.truly_unexplored(context):
                        gap = {
                            'type': 'unexplored_combination',
                            'method': method,
                            'domain': domain,
                            'evidence': {
                                'method_from': self.find_paper_with(method, papers),
                                'domain_from': self.find_paper_with(domain, papers)
                            },
                            'novelty_score': self.calculate_novelty(method, domain)
                        }
                        gaps.append(gap)

        return gaps

    def detect_bridging_gaps(self, papers):
        """
        Find unconnected concepts that could be bridged
        """
        gaps = []
        concepts = self.extract_all_concepts(papers)

        for c1 in concepts:
            for c2 in concepts:
                if c1 == c2:
                    continue

                # Check if any paper connects these concepts
                connected = self.check_concepts_connected(c1, c2, papers)

                # Or check via KG if available
                if self.kg:
                    connected = connected or self.kg.has_path(c1, c2)

                if not connected:
                    gap = {
                        'type': 'bridging_gap',
                        'concepts': [c1, c2],
                        'description': f"Bridge between {c1} and {c2}",
                        'evidence': {
                            'c1_papers': self.find_papers_with_concept(c1),
                            'c2_papers': self.find_papers_with_concept(c2)
                        }
                    }
                    gaps.append(gap)

        return gaps

    def detect_resolution_gaps(self, contradictions):
        """
        Generate gaps from contradictions
        """
        gaps = []

        for contradiction in contradictions:
            gap = {
                'type': 'resolution_gap',
                'description': 'Contradiction needs resolution',
                'conflicting_papers': contradiction['papers'],
                'conflicting_claims': contradiction['claims'],
                'resolution_approaches': [
                    'Experimental validation',
                    'Meta-analysis',
                    'Theoretical reconciliation'
                ]
            }
            gaps.append(gap)

        return gaps
```

**Testing:**
```python
def test_unexplored_combinations():
    # Papers:
    # Paper 1: Uses "CNN" for "Image Classification"
    # Paper 2: Uses "Transformer" for "NLP"
    # Paper 3: Discusses "Medical Imaging" domain

    papers = load_test_papers()
    detector = SynthesisGapDetector(rag, llm)
    gaps = detector.detect_unexplored_combinations(papers)

    # Expected: "CNN for Medical Imaging" might be a gap
    # (if no paper combines them)
    assert any(
        g['method'] == 'CNN' and g['domain'] == 'Medical Imaging'
        for g in gaps
    )
```

---

#### **Week 11-12: Lightweight Knowledge Graph Construction**

**Goal:** Build KG untuk enhancing gap detection

**Tasks:**
- [ ] Install spaCy scientific NER: `pip install scispacy`
- [ ] Download model: `python -m spacy download en_core_sci_sm`
- [ ] Create module: `backend/app/core/knowledge/kg_constructor.py`
- [ ] Implement entity extraction (Papers, Concepts, Methods)
- [ ] Implement relationship extraction (DISCUSSES, USES, RELATED_TO)
- [ ] Build NetworkX graph
- [ ] Graph-based gap detection (isolated nodes, missing edges)
- [ ] Optional: Neo4j integration untuk visualization

**Deliverables:**
- ✅ KG construction working
- ✅ Graph stored & queryable
- ✅ Graph-based gaps detected

**Implementation:**
```python
# backend/app/core/knowledge/kg_constructor.py

import spacy
import networkx as nx

class LightweightKGConstructor:
    def __init__(self):
        self.nlp = spacy.load("en_core_sci_sm")  # Scientific NER
        self.graph = nx.DiGraph()

    def build(self, papers: List[Paper]):
        """Build knowledge graph from papers"""

        # Step 1: Extract entities
        entities = self.extract_entities(papers)

        # Step 2: Add nodes
        self.add_nodes(papers, entities)

        # Step 3: Extract & add relationships
        self.add_relationships(papers, entities)

        return self.graph

    def extract_entities(self, papers):
        """Extract Concepts and Methods using NER"""
        entities = {
            'concepts': set(),
            'methods': set()
        }

        for paper in papers:
            doc = self.nlp(paper.text)

            for ent in doc.ents:
                # Concept entities
                if ent.label_ in ['CONCEPT', 'THEORY', 'PROBLEM']:
                    entities['concepts'].add(ent.text.lower())

                # Method entities
                elif ent.label_ in ['METHOD', 'ALGORITHM', 'TECHNIQUE']:
                    entities['methods'].add(ent.text.lower())

        return entities

    def add_nodes(self, papers, entities):
        """Add paper, concept, and method nodes"""
        # Paper nodes
        for paper in papers:
            self.graph.add_node(
                paper.id,
                type='paper',
                title=paper.title,
                authors=paper.authors
            )

        # Concept nodes
        for concept in entities['concepts']:
            self.graph.add_node(concept, type='concept')

        # Method nodes
        for method in entities['methods']:
            self.graph.add_node(method, type='method')

    def add_relationships(self, papers, entities):
        """Extract and add relationships"""
        for paper in papers:
            # Paper DISCUSSES Concept
            paper_concepts = self.find_concepts_in_paper(
                paper, entities['concepts']
            )
            for concept in paper_concepts:
                self.graph.add_edge(
                    paper.id, concept, relation='DISCUSSES'
                )

            # Paper USES Method
            paper_methods = self.find_methods_in_paper(
                paper, entities['methods']
            )
            for method in paper_methods:
                self.graph.add_edge(
                    paper.id, method, relation='USES'
                )

        # Concept RELATED_TO Concept (co-occurrence)
        self.add_concept_relationships(papers, entities['concepts'])

    def detect_graph_gaps(self):
        """Graph-based gap detection"""
        gaps = []

        # Gap 1: Isolated concepts (low degree)
        for node in self.graph.nodes():
            if self.graph.nodes[node].get('type') == 'concept':
                degree = self.graph.degree(node)
                if degree < 2:
                    gaps.append({
                        'type': 'underexplored_concept',
                        'concept': node,
                        'degree': degree
                    })

        # Gap 2: Missing Method-Concept combinations
        methods = [n for n, d in self.graph.nodes(data=True)
                   if d.get('type') == 'method']
        concepts = [n for n, d in self.graph.nodes(data=True)
                    if d.get('type') == 'concept']

        for method in methods:
            for concept in concepts:
                # Papers using method
                method_papers = set(self.graph.predecessors(method))
                # Papers discussing concept
                concept_papers = set(self.graph.predecessors(concept))

                # Any overlap?
                if not (method_papers & concept_papers):
                    gaps.append({
                        'type': 'missing_combination',
                        'method': method,
                        'concept': concept
                    })

        return gaps
```

---

#### **Week 13-14: Integration & Testing**

**Goal:** Integrate all components & system testing

**Tasks:**
- [ ] Integrate comparative analysis + synthesis gaps + KG
- [ ] Create unified API endpoint: `POST /api/analyze-with-gaps`
- [ ] System testing dengan real papers
- [ ] Performance optimization
- [ ] Bug fixes

**Deliverables:**
- ✅ Full pipeline working (input → comparative → synthesis gaps → recommendations)
- ✅ System test report

**Milestone 2 Complete:** ✅ Synthesis Gap Detection + KG Working

---

### **MONTH 5: Evaluation Framework** 🔴

#### **Week 17-18: Ground Truth Construction**

**Goal:** Build evaluation dataset

**Tasks:**
- [ ] Select 100-200 test queries (CS topics)
- [ ] Recruit 3-5 domain experts (dosen CS)
- [ ] Create annotation guidelines
- [ ] Build annotation interface (Google Sheets or custom web app)
- [ ] Experts annotate: expected gaps, relevance scores
- [ ] Calculate inter-rater reliability (Cohen's Kappa)
- [ ] Resolve disagreements (discussion or third expert)

**Deliverables:**
- ✅ Ground truth dataset (100-200 annotated queries)
- ✅ Cohen's Kappa ≥ 0.70
- ✅ Annotation report

**Annotation Template:**
```
Query: "Machine learning for medical image segmentation"

Papers Selected (by expert):
1. Paper A: CNN for image classification
2. Paper B: U-Net for segmentation
3. Paper C: Transformer in medical imaging
4. Paper D: Active learning
5. Paper E: Few-shot learning

Expected Gaps:
1. Explicit Gap: "Paper B mentions need for multi-modal segmentation"
   Relevance: 5/5, Novelty: 3/5, Feasibility: 4/5

2. Implicit Gap: "No paper discusses privacy-preserving techniques"
   Relevance: 4/5, Novelty: 4/5, Feasibility: 4/5

3. Synthesis Gap: "Combining active learning (Paper D) with U-Net (Paper B)
   for medical segmentation unexplored"
   Relevance: 5/5, Novelty: 5/5, Feasibility: 4/5
   Type: Unexplored Combination
```

---

#### **Week 19-20: Baseline Implementation**

**Goal:** Build baseline systems for comparison

**Tasks:**
- [ ] Baseline 1: LLM-only (no RAG)
  - Direct prompting dengan paper abstracts
  - No retrieval
- [ ] Baseline 2: Single-paper analysis
  - Analyze each paper independently
  - Aggregate gaps (no synthesis)
- [ ] Baseline 3: Fully-automated
  - Auto-select papers (no manual selection)
  - No human verification
- [ ] Implement evaluation metrics
  - Precision@K, Recall@K, F1@K
  - Gap quality scoring
  - Cohen's Kappa calculator

**Deliverables:**
- ✅ 3 baseline systems working
- ✅ Evaluation metrics implemented
- ✅ Evaluation script ready

**Baseline Code:**
```python
# backend/evaluation/baselines.py

class LLMOnlyBaseline:
    """Baseline 1: No RAG, direct LLM"""
    def detect_gaps(self, papers):
        abstracts = [p.abstract for p in papers]
        prompt = f"Identify research gaps from: {abstracts}"
        return self.llm.generate(prompt)

class SinglePaperBaseline:
    """Baseline 2: No comparative synthesis"""
    def detect_gaps(self, papers):
        gaps = []
        for paper in papers:
            gap = self.analyze_single(paper)
            gaps.append(gap)
        return gaps  # No cross-paper synthesis!

class FullyAutomatedBaseline:
    """Baseline 3: No human selection"""
    def detect_gaps(self, query):
        # Auto-select papers
        papers = self.auto_select(query, top_k=5)
        return self.analyze(papers)
```

**Metrics:**
```python
# backend/evaluation/metrics.py

def precision_at_k(predicted_gaps, ground_truth_gaps, k=10):
    predicted_k = predicted_gaps[:k]
    relevant = [g for g in predicted_k if g in ground_truth_gaps]
    return len(relevant) / k

def recall_at_k(predicted_gaps, ground_truth_gaps, k=10):
    predicted_k = predicted_gaps[:k]
    relevant = [g for g in predicted_k if g in ground_truth_gaps]
    return len(relevant) / len(ground_truth_gaps)

def cohens_kappa(rater1, rater2):
    from sklearn.metrics import cohen_kappa_score
    return cohen_kappa_score(rater1, rater2)
```

**Milestone 3 Complete:** ✅ Evaluation Framework Ready

---

### **MONTH 6-7: Experiments & Data Collection** 🔴

#### **Week 21-24: Quantitative Experiments**

**Goal:** Run experiments, collect data

**Tasks:**
- [ ] Run all systems on ground truth dataset
  - Our system (full)
  - Baseline 1 (LLM-only)
  - Baseline 2 (Single-paper)
  - Baseline 3 (Fully-auto)
- [ ] For each query:
  - Record detected gaps (top-10)
  - Compare with ground truth
  - Calculate P@10, R@10, F1@10
- [ ] Statistical analysis
  - Paired t-test (our system vs each baseline)
  - Effect size (Cohen's d)
  - Significance testing (α = 0.05)
- [ ] Collect results in structured format

**Deliverables:**
- ✅ Experiment results (tables, figures)
- ✅ Statistical test results
- ✅ Performance comparison report

**Experiment Script:**
```python
# backend/evaluation/run_experiments.py

def run_full_evaluation():
    ground_truth = load_ground_truth()

    systems = {
        'ours': OurSystem(),
        'llm_only': LLMOnlyBaseline(),
        'single_paper': SinglePaperBaseline(),
        'fully_auto': FullyAutomatedBaseline()
    }

    results = {name: [] for name in systems}

    for query_data in ground_truth:
        papers = query_data['papers']
        expected_gaps = query_data['gaps']

        for name, system in systems.items():
            detected_gaps = system.detect_gaps(papers)

            metrics = {
                'precision_10': precision_at_k(detected_gaps, expected_gaps, 10),
                'recall_10': recall_at_k(detected_gaps, expected_gaps, 10),
                'f1_10': f1_at_k(detected_gaps, expected_gaps, 10)
            }

            results[name].append(metrics)

    # Statistical analysis
    for baseline in ['llm_only', 'single_paper', 'fully_auto']:
        t_stat, p_value = paired_ttest(
            results['ours'], results[baseline]
        )
        print(f"Ours vs {baseline}: t={t_stat}, p={p_value}")

    return results
```

---

#### **Week 25-26: Expert Evaluation**

**Goal:** Qualitative assessment dari experts

**Tasks:**
- [ ] Select 50 queries (stratified sample)
- [ ] Generate gaps dengan our system
- [ ] 3 experts independently rate each gap:
  - Relevance (1-5 Likert)
  - Novelty (1-5)
  - Feasibility (1-5)
  - Clarity (1-5)
- [ ] Calculate inter-rater reliability
- [ ] Aggregate scores (mean, std)
- [ ] Qualitative feedback analysis

**Deliverables:**
- ✅ Expert evaluation results
- ✅ Gap quality scores
- ✅ Qualitative insights

---

#### **Week 27-28: User Study**

**Goal:** Usability testing dengan real researchers

**Tasks:**
- [ ] Recruit 10-15 participants (S2/S3, dosen muda)
- [ ] Prepare user study materials:
  - Tutorial/onboarding
  - Task instructions
  - SUS questionnaire
  - Interview questions
- [ ] Conduct user study sessions (1 hour each)
  - Task 1: Select papers & run analysis
  - Task 2: Review gaps & rate quality
  - Task 3: Compare with baseline
  - Task 4: Complete SUS questionnaire
  - Task 5: Semi-structured interview
- [ ] Analyze results:
  - SUS score calculation
  - Task completion time
  - Gap acceptance rate
  - Thematic analysis of interviews

**Deliverables:**
- ✅ User study report
- ✅ SUS score (target ≥ 70)
- ✅ Usability recommendations

**Milestone 4 Complete:** ✅ All Experiments & Data Collection Done

---

### **MONTH 8: Analysis, Writing & Submission** 📝

#### **Week 29-30: Results Analysis**

**Goal:** Analyze all data & interpret findings

**Tasks:**
- [ ] Quantitative results analysis
  - Aggregate metrics across all queries
  - Statistical tests results
  - Effect size calculations
  - Visualization (charts, tables)
- [ ] Qualitative results analysis
  - Expert feedback themes
  - User study insights
  - Case study selection (3-5 examples)
- [ ] Hypothesis testing
  - H1: RAG > LLM-only (hallucination)
  - H2: Comparative > Single-paper (synthesis gaps)
  - H3: With KG > Without KG (implicit gaps)
- [ ] Interpretation & discussion
  - What worked well?
  - What didn't work?
  - Why?

**Deliverables:**
- ✅ Results chapter draft (BAB IV)
- ✅ All figures & tables ready
- ✅ Statistical analysis complete

---

#### **Week 31-32: Thesis Writing**

**Goal:** Complete thesis document

**Tasks:**
- [ ] BAB I: Pendahuluan (revisi final)
- [ ] BAB II: Tinjauan Pustaka (revisi final)
- [ ] BAB III: Metodologi (lengkap)
- [ ] BAB IV: Hasil dan Pembahasan (tulis)
- [ ] BAB V: Kesimpulan dan Saran (tulis)
- [ ] Abstract (Bahasa Indonesia + English)
- [ ] Formatting & proofreading
- [ ] References check
- [ ] Appendix (kode, data samples)

**Deliverables:**
- ✅ Complete thesis document
- ✅ Reviewed by advisor
- ✅ Ready for submission

---

#### **Week 33-34: Paper Writing & Submission**

**Goal:** Conference/journal paper submission

**Tasks:**
- [ ] Target venue selection
  - Conference: EMNLP, ACL, AAAI, CHI, WWW
  - Journal: TACL, AI Journal, Expert Systems with Applications
- [ ] Paper outline (based on venue format)
- [ ] Introduction (1-2 pages)
- [ ] Related Work (1-2 pages)
- [ ] Methodology (2-3 pages)
- [ ] Experiments & Results (2-3 pages)
- [ ] Discussion & Conclusion (1 page)
- [ ] Abstract (150-250 words)
- [ ] Figures & tables (publication quality)
- [ ] Submit to venue

**Deliverables:**
- ✅ Conference/journal paper submitted
- ✅ Presentation slides (for defense)
- ✅ Demo video (optional)

**Milestone 5 Complete:** ✅ Thesis & Paper Submitted

---

## 📊 TRACKING & MILESTONES

### **Milestones Summary:**

| Milestone | Target Date | Key Deliverables |
|-----------|-------------|------------------|
| M1: Comparative Analysis | End Month 2 | ComparativeAnalyzer working, API + Frontend integrated |
| M2: Synthesis Gaps + KG | End Month 4 | SynthesisGapDetector + KG construction working |
| M3: Evaluation Framework | End Month 5 | Ground truth + Baselines + Metrics ready |
| M4: Experiments Complete | End Month 7 | All data collected, experiments done |
| M5: Submission | End Month 8 | Thesis + Paper submitted |

---

## 🎯 PRIORITY MATRIX

### **MUST HAVE (Critical for Thesis):**
1. ✅ Comparative Analysis Algorithm
2. ✅ Synthesis Gap Detection
3. ✅ Evaluation Framework
4. ✅ Ground Truth Dataset
5. ✅ Baseline Comparisons
6. ✅ Statistical Analysis

### **SHOULD HAVE (High Priority):**
1. ✅ SciBERT Embeddings
2. ✅ Lightweight Knowledge Graph
3. ✅ Expert Evaluation
4. ✅ User Study

### **COULD HAVE (Nice to Have):**
1. ⚪ Neo4j Visualization
2. ⚪ Advanced Graph Algorithms
3. ⚪ Multi-language Support
4. ⚪ Collaborative Filtering

### **WON'T HAVE (Out of Scope):**
1. ❌ Traditional Topic Modeling (LDA/BERTopic)
2. ❌ Temporal Citation Network Analysis
3. ❌ Full Ontology Engineering
4. ❌ Production Deployment (cloud)

---

## 🚧 RISKS & MITIGATION

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Expert recruitment difficult | Medium | High | Start early, leverage advisor network, offer co-authorship |
| Ground truth quality low | Medium | High | Clear guidelines, pilot annotation, multiple experts |
| LLM API costs high | High | Medium | Use local models for dev (Ollama), GPT-4 only for final experiments |
| Implementation delays | Medium | High | Buffer time in plan, prioritize MUST-HAVEs, weekly progress review |
| Baseline performance better | Low | High | Ensure baselines implemented correctly, focus on synthesis gaps (our novelty) |
| User study recruitment | Medium | Medium | Incentives (honorarium), convenient scheduling, online option |

---

## 📝 DOCUMENTATION REQUIREMENTS

### **Code Documentation:**
- [ ] README.md (setup instructions)
- [ ] API documentation (Swagger/OpenAPI)
- [ ] Code comments (key functions)
- [ ] Architecture diagram
- [ ] Deployment guide

### **Research Documentation:**
- [ ] Experiment protocol
- [ ] Annotation guidelines
- [ ] User study materials
- [ ] Data analysis notebooks (Jupyter)
- [ ] Results visualization scripts

### **Thesis Documentation:**
- [ ] All chapters (BAB I-V)
- [ ] Appendices (code, data)
- [ ] References (BibTeX)
- [ ] Figures & tables (high-res)

---

## 🎓 PUBLICATION TARGETS

### **Conference Options (Tier A/B):**

**Tier A (Top Conferences):**
- EMNLP 2025 (Empirical Methods in NLP) - Deadline: May/June
- ACL 2025 (Association for Computational Linguistics) - Deadline: January
- AAAI 2026 (AI Conference) - Deadline: August 2025
- CHI 2026 (Human-Computer Interaction) - Deadline: September 2025

**Tier B (Good Conferences):**
- CIKM 2025 (Conference on Information and Knowledge Management)
- ECIR 2026 (European Conference on Information Retrieval)
- WSDM 2026 (Web Search and Data Mining)

### **Journal Options:**

**Tier A (Top Journals):**
- TACL (Transactions of ACL) - Impact Factor: ~10
- Artificial Intelligence Journal - IF: ~14
- ACM TOIS (Transactions on Information Systems) - IF: ~5

**Tier B (Good Journals):**
- Expert Systems with Applications - IF: ~8
- Information Processing & Management - IF: ~7
- Journal of AI Research - IF: ~5

**Recommendation:** Target conference first (faster review), then extend to journal

---

## 👥 TEAM & RESPONSIBILITIES

### **Core Team:**
- **You:** Main developer, researcher, writer
- **Advisor:** Guidance, feedback, validation
- **Domain Experts (3-5):** Ground truth annotation, gap validation
- **User Study Participants (10-15):** Usability testing

### **External Support:**
- **IT Support:** Server/GPU access (if needed)
- **Librarian:** Literature access, citation management
- **Statistician (optional):** Statistical analysis validation

---

## 💰 BUDGET ESTIMATE

| Item | Cost (Rp) | Notes |
|------|-----------|-------|
| **LLM API (GPT-4)** | 1,500,000 - 3,000,000 | For final experiments only (~$100-200) |
| **Cloud Compute** | 500,000 - 1,000,000 | Optional (DigitalOcean/AWS) |
| **Expert Honorarium** | 1,500,000 - 3,000,000 | 3-5 experts × Rp 500k |
| **User Study Incentives** | 1,500,000 - 2,000,000 | 10-15 participants × Rp 100-150k |
| **Conference Registration** | 5,000,000 - 10,000,000 | If accepted (~$300-700) |
| **Total** | **10,000,000 - 19,000,000** | ~$650-1,300 |

**Cost Reduction Strategies:**
- Use local LLMs (Ollama) for development
- Use advisor funding for conference (if available)
- Recruit participants without monetary incentive (co-authorship, contribution acknowledgment)

---

## 📌 WEEKLY CHECKLIST TEMPLATE

```
Week X: [Description]

Goals:
- [ ] Goal 1
- [ ] Goal 2
- [ ] Goal 3

Tasks:
- [ ] Task 1 (X hours)
- [ ] Task 2 (X hours)
- [ ] Task 3 (X hours)

Blockers:
- None / [Describe blocker]

Progress:
- [What was completed]
- [What's in progress]
- [What's blocked]

Next Week:
- [Planned tasks]
```

---

## 🎯 SUCCESS CRITERIA

### **Minimum Viable Thesis (Must Achieve):**
- ✅ Comparative analysis working & evaluated
- ✅ Synthesis gap detection implemented
- ✅ Evaluation: P@10 ≥ 0.60, expert scores ≥ 3.5/5
- ✅ Statistical significance: p < 0.05 vs baselines
- ✅ User study: SUS ≥ 60
- ✅ Thesis defended successfully

### **Target Quality (Should Achieve):**
- ✅ P@10 ≥ 0.70, R@10 ≥ 0.75
- ✅ Expert scores: Relevance ≥ 4.0, Novelty ≥ 3.5
- ✅ SUS ≥ 70
- ✅ Strong statistical evidence (effect size > 0.5)
- ✅ Conference paper accepted

### **Excellent Outcome (Best Case):**
- ✅ P@10 ≥ 0.80, R@10 ≥ 0.85
- ✅ Expert scores: All ≥ 4.0
- ✅ SUS ≥ 80
- ✅ Tier-A conference acceptance
- ✅ Journal invitation

---

## 📞 CONTACT & SUPPORT

**For Questions:**
- Advisor: [Email/Office Hours]
- Lab/Research Group: [Slack/Discord]
- Technical Issues: [GitHub Issues]

**Resources:**
- Code Repository: https://github.com/[username]/wizard-research
- Documentation: /docs folder
- Experiment Logs: /experiments folder

---

## 🔄 PLAN UPDATES

This plan is a living document. Update as needed based on:
- Progress velocity
- Unexpected challenges
- New insights from experiments
- Advisor feedback
- Conference deadlines

**Last Updated:** 20 Desember 2025
**Next Review:** Weekly (every Monday)

---

## ✅ IMMEDIATE NEXT STEPS (This Week!)

### **Priority 1 (Start Now):**
1. [ ] Review & approve this plan dengan advisor
2. [ ] Setup development environment (SciBERT, spaCy scientific)
3. [ ] Start Week 1-2 tasks (Upgrade to SciBERT)

### **Priority 2 (This Week):**
4. [ ] Create project Kanban board (GitHub Projects / Trello)
5. [ ] Setup weekly progress tracking
6. [ ] Identify potential domain experts untuk recruitment

### **Priority 3 (Plan Ahead):**
7. [ ] Research target conferences (deadlines, requirements)
8. [ ] Setup experiment logging system (MLflow / Weights & Biases)
9. [ ] Draft expert recruitment email

---

**Ready to start? Let's build this! 🚀**
