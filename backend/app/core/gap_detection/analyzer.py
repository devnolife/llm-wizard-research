"""
Gap Analyzer - Synthesis Gap Detection using 3 Mainstream Indicators

Detects synthesis gaps following Cooper (1998) and Booth, Sutton & Papaioannou (2012):

    Synthesis Gap = condition where existing literature about a phenomenon
    has NOT produced a unified, conclusive understanding, due to:
    
    1. FRAGMENTATION: Papers address the same phenomenon from different angles
       but do not integrate their findings
    2. INCONSISTENCY: Empirical findings contradict each other without 
       reconciliation  
    3. COLLECTIVE INCOMPLETENESS: Critical aspects of the phenomenon are
       not collectively covered by existing literature

NOTE: System outputs are INDICATORS, not final gaps.
      The system is a decision-support tool, NOT a replacement for human reasoning.

References:
    - Cooper, H. (1998). Synthesizing Research
    - Booth, A., Sutton, A., & Papaioannou, D. (2012). Systematic Approaches
    - Pare, G., et al. (2015). Synthesizing Information Systems Knowledge
    - revisi.md Sections 3, 6, 7
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from loguru import logger

from ...models.responses import (
    IndicatorType,
    RuleVerdictType,
    GapIndicatorModel,
)
from ..knowledge.fact_table import EntityType
from .quote_grounding import extract_supporting_quotes, verify_quote_against_papers
from .claim_normalization import (
    ALIGNMENT_GATE,
    NormalizedClaim,
    normalize_claims,
)
from .adjudication import (
    NLI_NOISE_FLOOR,
    AdjudicationResult,
    adjudicate_contradiction,
)
from .semantic_match import SemanticMatcher
from .coverage_map import build_coverage_matrix, mark_important_columns
from .calibration import Calibrator, build_provenance, load_calibrator
from .support_gap import (
    MAX_REPORTED_CLAIMS,
    analyze_support,
    support_confidence,
)
from .graph_metrics import (
    OVERLAP_FRAGMENTED_MAX,
    Q_COHESIVE_MIN,
    cluster_papers,
    rank_bridges,
    rescue_singletons,
)

# Re-export for backward compatibility
GapIndicatorType = IndicatorType

_ASPECT_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "in", "on", "to",
    "with", "by", "from", "vs", "versus", "such", "as", "e.g",
    "dan", "atau", "yang", "dalam", "pada", "untuk", "dari",
}


def aspect_terms(aspect: str) -> List[str]:
    """Content words of an expected aspect, used for grounding AND quoting.

    Aspects arrive as long phrases ("Chain of custody dan integritas bukti
    digital"), so whole-phrase substring matching never hits a sentence. Both
    the grounding test and the quote extractor must therefore work on the same
    content words, otherwise an aspect can be reported as corpus-grounded while
    no quote is retrievable and the provenance chain breaks permanently.
    """
    return [
        w for w in (
            token.strip(".,()[]:;\"'") for token in (aspect or "").lower().split()
        )
        if len(w) > 3 and w not in _ASPECT_STOPWORDS
    ]


def _paper_ref(paper: Dict[str, Any]) -> str:
    """Human-readable, stable reference for a paper.

    Prefers the source filename (reliably clean and journal-identifying),
    then the extracted title (often a running header/URL in scanned PDFs),
    then internal ids, so `related_papers` in gap indicators names the actual
    journals instead of empty strings (retrieval passages carry title/source
    but no doc_id).
    """
    meta = paper.get("metadata") or {}
    for candidate in (
        paper.get("source"), meta.get("source"),
        paper.get("title"), meta.get("title"),
        paper.get("doc_id"), paper.get("id"),
    ):
        text = " ".join(str(candidate).split()) if candidate else ""
        if text and text.lower() != "unknown":
            return text
    return ""


def _paper_refs(papers: List[Dict[str, Any]]) -> List[str]:
    """Unique, ordered, non-empty references for a list of papers."""
    seen: Set[str] = set()
    refs: List[str] = []
    for p in papers:
        ref = _paper_ref(p)
        if ref and ref not in seen:
            seen.add(ref)
            refs.append(ref)
    return refs


@dataclass
class GapIndicator:
    """
    Represents a detected synthesis gap INDICATOR (not a final gap).
    
    The system outputs indicators that must be validated by a human researcher.
    See revisi.md Section 4: Batasan Epistemologis.
    """
    indicator_type: IndicatorType
    description: str
    confidence: float                    # 0.0 - 1.0
    related_papers: List[str]            # Paper IDs involved
    evidence: List[str]                  # Supporting evidence texts
    suggested_directions: List[str]      # Potential research directions
    requires_human_validation: bool = True  # Always True per revisi.md
    rule_engine_verdict: Optional[RuleVerdictType] = None  # PASS/FLAG/REJECT from Rule Engine
    adjusted_confidence: Optional[float] = None  # Confidence after Rule Engine adjustment
    
    # Metadata for traceability
    detection_method: str = ""           # e.g., "topic_clustering", "nli_check"
    sub_indicators: List[Dict] = field(default_factory=list)
    # Verbatim quotes from source chunks grounding this indicator
    # (ala paper-qa): [{"quote", "source_paper", "match_score"}]
    supporting_quotes: List[Dict] = field(default_factory=list)
    # KG evidence subgraph (ala SciAgentsDiscovery): edge dicts
    # [{"from","from_name","to","to_name","predicate","source_paper"}]
    evidence_subgraph: List[Dict] = field(default_factory=list)
    # Post-hoc calibrated confidence + selective abstention (P9). `needs_review`
    # means the system declines to present this as a finding.
    calibrated_confidence: Optional[float] = None
    needs_review: bool = False
    abstention_reasons: List[str] = field(default_factory=list)
    calibration: Dict[str, Any] = field(default_factory=dict)
    # claim -> cited record -> retrieved passage -> validation outcome
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "indicator_type": self.indicator_type.value,
            "description": self.description,
            "confidence": self.confidence,
            "calibrated_confidence": self.calibrated_confidence,
            "needs_review": self.needs_review,
            "abstention_reasons": self.abstention_reasons,
            "calibration": self.calibration,
            "provenance": self.provenance,
            "related_papers": self.related_papers,
            "evidence": self.evidence[:5],
            "supporting_quotes": self.supporting_quotes[:5],
            "evidence_subgraph": self.evidence_subgraph[:10],
            "suggested_directions": self.suggested_directions,
            "requires_human_validation": self.requires_human_validation,
            "rule_engine_verdict": self.rule_engine_verdict.value if self.rule_engine_verdict else None,
            "detection_method": self.detection_method,
        }

    def to_model(self) -> GapIndicatorModel:
        """Convert internal GapIndicator to the API response model."""
        return GapIndicatorModel(
            indicator_type=self.indicator_type,
            title=self.description.split(":")[0].strip() if ":" in self.description else self.description[:80],
            description=self.description,
            confidence=self.confidence,
            adjusted_confidence=self.adjusted_confidence,
            calibrated_confidence=self.calibrated_confidence,
            needs_review=self.needs_review,
            abstention_reasons=self.abstention_reasons,
            calibration=self.calibration,
            provenance=self.provenance,
            rule_engine_verdict=self.rule_engine_verdict,
            requires_human_validation=self.requires_human_validation,
            evidence=self.evidence[:5],
            supporting_quotes=self.supporting_quotes[:5],
            evidence_subgraph=self.evidence_subgraph[:10],
            supporting_papers=self.related_papers,
            suggested_directions=self.suggested_directions,
        )


class GapAnalyzer:
    """
    Synthesis Gap Detection Engine
    
    Detects 3 types of gap indicators:
    1. Fragmentation — papers don't integrate with each other
    2. Inconsistency — contradictory findings without reconciliation
    3. Incompleteness — critical aspects not collectively covered
    
    Inputs:
    - Papers (text + metadata)
    - FactTable (SPO triples from Knowledge Graph)
    - Relation classifications (from RelationClassifier)
    
    Outputs:
    - List of GapIndicator objects
    - Each indicator has confidence score and requires human validation
    """
    
    def __init__(
        self,
        vector_store=None,
        knowledge_graph=None,
        llm_interface=None,
        fact_table=None,
        relation_classifier=None,
        rule_engine=None,
    ):
        self.vector_store = vector_store
        self.knowledge_graph = knowledge_graph
        self.llm = llm_interface
        self.fact_table = fact_table
        self.relation_classifier = relation_classifier
        self.rule_engine = rule_engine
        # Post-hoc calibration (P9). Stays an identity map until enough expert
        # labels exist, so confidences are never silently rescaled.
        self.calibrator = load_calibrator()
        
        logger.info("GapAnalyzer initialized (Cooper/Booth 3-indicator model)")
    
    def analyze_gaps(
        self,
        topic: str,
        papers: List[Dict[str, Any]],
        depth: str = "standard"
    ) -> List[GapIndicator]:
        """
        Comprehensive gap analysis using 3 mainstream indicators.
        
        Args:
            topic: Research topic/domain
            papers: List of papers to analyze
            depth: Analysis depth ('quick', 'standard', 'comprehensive')
            
        Returns:
            List of GapIndicator objects (NOT final gaps — indicators only)
        """
        logger.info(f"Analyzing synthesis gap indicators for: {topic} (depth: {depth})")
        
        indicators: List[GapIndicator] = []
        
        # Indicator 1: Fragmentation
        indicators.extend(self._detect_fragmentation(topic, papers))
        
        # Indicator 2: Inconsistency
        if depth in ["standard", "comprehensive"]:
            indicators.extend(self._detect_inconsistency(topic, papers))
        
        # Indicator 3: Collective Incompleteness
        indicators.extend(self._detect_incompleteness(topic, papers))
        
        # Indicator 4: Evidence-support gap (retrieval failure)
        if depth in ["standard", "comprehensive"]:
            indicators.extend(self._detect_support_gap(topic, papers))
        
        # Validate through Rule Engine (if available)
        if self.rule_engine:
            indicators = self._validate_with_rule_engine(indicators)
        else:
            # Calibration and provenance are independent of the symbolic layer;
            # without a rule engine the chain simply records no verdict.
            for indicator in indicators:
                self._apply_calibration(indicator, "")
        
        # Rank by confidence
        indicators.sort(key=lambda x: x.confidence, reverse=True)
        
        logger.info(f"Detected {len(indicators)} gap indicators")
        return indicators
    
    def analyze_gaps_as_models(
        self,
        topic: str,
        papers: List[Dict[str, Any]],
        depth: str = "standard",
    ) -> List[GapIndicatorModel]:
        """Run gap analysis and return API-ready GapIndicatorModel list."""
        indicators = self.analyze_gaps(topic, papers, depth)
        return [ind.to_model() for ind in indicators]
    
    # -------------------------------------------------------------------
    # Indicator 1: FRAGMENTATION
    # -------------------------------------------------------------------
    
    def _detect_fragmentation(
        self,
        topic: str,
        papers: List[Dict[str, Any]],
    ) -> List[GapIndicator]:
        """
        Detect fragmentation: papers address the same phenomenon from
        different angles but do not integrate their findings.

        Methods (upgraded per the P6 review):
        - Embedding clustering reported with modularity Q and silhouette,
          replacing an order-dependent greedy keyword pass
        - Entropy-gated centroid reassignment so niche topics are not dropped
        - Link prediction (CN / Jaccard / Adamic-Adar / resource allocation /
          preferential attachment) with betweenness brokers to rank concrete
          bridge candidates, replacing a binary path-exists isolation ratio
        """
        indicators = []

        if len(papers) < 2:
            return indicators

        # Method 1: approach clustering with structural quality metrics
        paper_approaches = self._extract_approaches(papers)
        embedder = getattr(self.vector_store, "embedding_model", None) if self.vector_store else None
        cluster_result = cluster_papers(paper_approaches, embedder=embedder)
        gating = rescue_singletons(paper_approaches, cluster_result, embedder=embedder)
        clusters = gating.clusters

        if len(clusters) >= 2:
            cluster_descriptions = []
            for cluster_id, member_papers in clusters.items():
                approaches = set()
                for pid in member_papers:
                    approaches.update(paper_approaches.get(pid, []))
                cluster_descriptions.append(
                    f"Cluster {cluster_id + 1} ({len(member_papers)} paper(s)): "
                    f"{', '.join(list(approaches)[:3])}"
                )

            evidence = cluster_descriptions + [
                f"Structural metrics: modularity Q={cluster_result.modularity:.2f}, "
                f"silhouette={cluster_result.silhouette:.2f}, inter-cluster "
                f"vocabulary overlap={cluster_result.inter_cluster_overlap:.0%} "
                f"(clustering: {cluster_result.method}).",
                f"Interpretation: {cluster_result.interpretation}.",
            ]
            if gating.reassigned or gating.ambiguous:
                evidence.append(
                    f"Entropy gating: {len(gating.reassigned)} singleton paper(s) "
                    f"reassigned to the nearest centroid, {len(gating.ambiguous)} left "
                    f"ambiguous; cluster coverage {gating.coverage_before:.0%} "
                    f"-> {gating.coverage_after:.0%}."
                )

            indicators.append(GapIndicator(
                indicator_type=GapIndicatorType.FRAGMENTATION,
                description=(
                    f"Literature on '{topic}' appears fragmented into "
                    f"{len(clusters)} distinct clusters with different approaches "
                    f"(modularity Q={cluster_result.modularity:.2f}). "
                    f"No integrative framework found."
                ),
                confidence=self._calibrate_fragmentation_confidence(
                    clusters, paper_approaches, cluster_result,
                ),
                related_papers=[pid for pids in clusters.values() for pid in pids],
                evidence=evidence,
                supporting_quotes=extract_supporting_quotes(
                    terms=[a for pids in clusters.values() for pid in pids
                           for a in paper_approaches.get(pid, [])][:8],
                    papers=papers,
                ),
                suggested_directions=[
                    f"Develop an integrative framework that unifies the {len(clusters)} approaches",
                    "Conduct a systematic review comparing methodological paradigms",
                ],
                detection_method="topic_clustering",
                sub_indicators=[
                    {"cluster_id": cid, "papers": pids}
                    for cid, pids in clusters.items()
                ] + [
                    {"cluster_metrics": cluster_result.to_dict()},
                    {"entropy_gating": gating.to_dict()},
                ],
            ))

        # Method 2: structural isolation + ranked bridge candidates via the KG
        if self.knowledge_graph and self.fact_table:
            isolation = self._analyze_structural_isolation(papers)
            if isolation["isolation_score"] > 0.6:
                bridges = isolation["bridges"]
                evidence = [
                    f"Isolation score: {isolation['isolation_score']:.2f} "
                    f"(mean normalized path distance between paper entities; "
                    f"1.00 = no connecting path at all).",
                    f"Disconnected entity pairs: {isolation['disconnected_pairs']}"
                    f"/{isolation['total_pairs']}.",
                ]
                for bridge in bridges[:3]:
                    evidence.append(
                        f"Bridge candidate: '{bridge['source']}' <-> '{bridge['target']}' "
                        f"(score {bridge['score']:.2f}; CN={bridge['common_neighbors']}, "
                        f"AA={bridge['adamic_adar']:.2f}, RA={bridge['resource_allocation']:.2f}, "
                        f"Jaccard={bridge['jaccard']:.2f}"
                        + (f", broker via '{bridge['broker']}'" if bridge["broker"] else "")
                        + ")."
                    )
                if isolation["filtered"]:
                    evidence.append(
                        f"False-bridge filters rejected {len(isolation['filtered'])} "
                        f"candidate(s): "
                        + "; ".join(
                            f"{f['source']}<->{f['target']} ({f['filtered_reason']})"
                            for f in isolation["filtered"][:3]
                        )
                        + "."
                    )

                indicators.append(GapIndicator(
                    indicator_type=GapIndicatorType.FRAGMENTATION,
                    description=(
                        f"Papers on '{topic}' show low structural connectivity "
                        f"(isolation score: {isolation['isolation_score']:.2f}). "
                        + (
                            f"{len(bridges)} ranked bridge candidate(s) identified "
                            f"between the isolated streams."
                            if bridges else "Findings exist in silos."
                        )
                    ),
                    confidence=round(isolation["isolation_score"], 3),
                    related_papers=_paper_refs(papers),
                    evidence=evidence,
                    suggested_directions=(
                        [
                            f"Investigate the link between '{b['source']}' and "
                            f"'{b['target']}'"
                            for b in bridges[:2]
                        ] or ["Investigate connections between isolated research streams"]
                    ),
                    detection_method="citation_isolation",
                    sub_indicators=[{"bridge_candidates": bridges}],
                ))

        return indicators

    # -------------------------------------------------------------------
    # Indicator 2: INCONSISTENCY
    # -------------------------------------------------------------------
    
    def _detect_inconsistency(
        self,
        topic: str,
        papers: List[Dict[str, Any]],
    ) -> List[GapIndicator]:
        """
        Detect unreconciled inconsistencies: findings that contradict 
        each other without resolution.
        
        Methods:
        - NLI-based contradiction detection (via LLM)
        - FactTable CONTRADICTS relations
        - Linguistic marker detection
        """
        indicators = []
        
        # Method 1: Check FactTable for CONTRADICTS relations.
        # Each raw CONTRADICTS fact is validated before it may become an
        # inconsistency indicator (guards against extraction artifacts such
        # as method names being flagged as "contradicting" each other).
        if self.fact_table:
            from ..knowledge.fact_table import PredicateType
            contradictions = self.fact_table.query(
                predicate=PredicateType.CONTRADICTS
            )
            
            for contradiction in contradictions:
                subject = self.fact_table.get_entity(contradiction.subject_id)
                obj = self.fact_table.get_entity(contradiction.object_id)
                
                valid, adjusted_conf, reason = self._validate_contradiction(
                    contradiction, subject, obj
                )
                if not valid:
                    logger.debug(
                        f"Discarded CONTRADICTS fact "
                        f"{contradiction.subject_id} vs {contradiction.object_id}: {reason}"
                    )
                    continue
                
                subject_name = subject.name if subject else contradiction.subject_id
                object_name = obj.name if obj else contradiction.object_id
                
                indicators.append(GapIndicator(
                    indicator_type=GapIndicatorType.INCONSISTENCY,
                    description=(
                        f"Unreconciled contradiction: '{subject_name}' "
                        f"vs '{object_name}'. No study has resolved this "
                        f"inconsistency."
                    ),
                    confidence=adjusted_conf,
                    related_papers=[contradiction.source_paper],
                    evidence=[contradiction.source] + ([reason] if reason else []),
                    supporting_quotes=extract_supporting_quotes(
                        terms=[subject_name, object_name],
                        papers=papers,
                    ),
                    evidence_subgraph=self._extract_evidence_subgraph(
                        contradiction.subject_id, contradiction.object_id,
                    ),
                    suggested_directions=[
                        f"Investigate conditions under which each finding holds",
                        f"Design a study that reconciles these contradictory findings",
                    ],
                    detection_method="fact_table_contradicts",
                ))
        
        # Method 2: Dedicated cross-encoder NLI — independent signal, decoupled
        # from the generative LLM (only runs when an NLI model is wired in).
        nli_indicators = self._detect_contradictions_nli(topic, papers)
        indicators.extend(nli_indicators)

        # Method 3: LLM-based contradiction detection (complementary). Skipped
        # when the NLI model already produced grounded contradiction signals,
        # to avoid duplicate low-trust indicators.
        if self.llm and len(papers) >= 2 and not nli_indicators:
            llm_contradictions = self._detect_contradictions_llm(topic, papers)
            indicators.extend(llm_contradictions)
        
        return indicators
    
    def _validate_contradiction(self, fact, subject, obj):
        """
        Validate a raw CONTRADICTS fact before it becomes an inconsistency
        indicator. Guards against extraction artifacts (e.g. two method names
        in a "however" sentence being flagged as a scientific contradiction).
        
        Checks:
        1. Both entities must exist and be FINDING-type (comparable claims —
           a METHOD cannot "contradict" another METHOD).
        2. Entity names must be substantive (not short acronyms/labels).
        3. If a RelationClassifier is available, the source sentence must be
           confirmed as CONTRADICTION by the 3-layer classifier; unconfirmed
           facts are kept only with reduced confidence.
        
        Returns:
            (valid: bool, adjusted_confidence: float, reason: str)
        """
        from ..knowledge.fact_table import EntityType
        
        # Check 1: comparable claim types
        if subject is None or obj is None:
            return False, 0.0, "entity missing from fact table"
        if subject.entity_type != EntityType.FINDING or obj.entity_type != EntityType.FINDING:
            return False, 0.0, (
                f"non-comparable entity types "
                f"({subject.entity_type.value} vs {obj.entity_type.value})"
            )
        
        # Check 2: substantive claim names — a genuine finding statement is
        # longer than a bare model/method label like 'SSD' or 'ResNet'.
        min_words = 3
        if (len(subject.name.split()) < min_words
                or len(obj.name.split()) < min_words):
            return False, 0.0, "entity names too short to be claim statements"
        
        # Check 3: classifier verification of the source sentence
        if self.relation_classifier and fact.source:
            try:
                from ..validation.relation_classifier import RelationType
                classified = self.relation_classifier.classify(
                    entity_a=subject.name,
                    entity_b=obj.name,
                    text_context=fact.source,
                    semantic_similarity=1.0,  # already co-mentioned in source
                )
                if classified.relation_type != RelationType.CONTRADICTION:
                    return False, 0.0, (
                        f"classifier verdict: {classified.relation_type.value} "
                        f"(not contradiction)"
                    )
                if classified.rule_validated:
                    return True, min(fact.confidence, classified.confidence), (
                        "verified by 3-layer classifier"
                    )
                # Contradiction detected but not rule-validated: keep, but
                # cap confidence to reflect the weaker evidence.
                return True, min(fact.confidence, classified.confidence, 0.5), (
                    "classifier detected contradiction (unvalidated) — confidence capped"
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(f"Contradiction verification failed: {exc}")
        
        # No classifier available: keep with pattern-level confidence cap.
        return True, min(fact.confidence, 0.5), "unverified (no classifier) — confidence capped"
    
    # -------------------------------------------------------------------
    # Indicator 3: COLLECTIVE INCOMPLETENESS
    # -------------------------------------------------------------------
    
    def _detect_incompleteness(
        self,
        topic: str,
        papers: List[Dict[str, Any]],
    ) -> List[GapIndicator]:
        """
        Detect collective incompleteness: critical aspects of the phenomenon 
        are not collectively covered by existing literature.
        
        Methods:
        - LLM identifies expected aspects for the topic
        - Check which aspects are covered by the papers
        - Flag uncovered critical aspects
        """
        indicators = []
        
        # Extract covered aspects from papers
        covered_aspects = self._extract_covered_aspects(papers)
        expected_aspects: List[str] = []
        
        # Use LLM to identify expected aspects
        if self.llm:
            expected_aspects = self._identify_expected_aspects(topic)
            
            # Semantic matching instead of exact lowercase comparison (P8).
            # An exact match treated "reproducibility" and "reproducible
            # experiments" as different aspects and reported the second as an
            # uncovered gap — a pure false positive.
            matcher = SemanticMatcher.from_vector_store(self.vector_store)
            covered_matches, uncovered_matches = matcher.split_covered(
                expected_aspects, sorted(covered_aspects)
            )
            uncovered = [m.aspect for m in uncovered_matches]
            
            if uncovered:
                # Ground each uncovered aspect against the corpus vocabulary:
                # aspects whose terms never appear anywhere in the analyzed
                # papers are likely parametric LLM knowledge (pre-training
                # bias), so they carry less evidential weight than aspects
                # whose terminology IS present but never systematically covered.
                grounded, ungrounded = self._ground_aspects(uncovered, papers)
                
                # Calibrated: confidence scales with the measured coverage gap
                # (fraction of expected aspects that no paper addresses),
                # weighted by how many of those aspects are corpus-grounded.
                coverage_gap = len(uncovered) / max(1, len(expected_aspects))
                grounding_ratio = len(grounded) / max(1, len(uncovered))
                conf = round((0.3 + 0.6 * coverage_gap) * (0.6 + 0.4 * grounding_ratio), 3)
                indicators.append(GapIndicator(
                    indicator_type=GapIndicatorType.INCOMPLETENESS,
                    description=(
                        f"Collective incompleteness detected for '{topic}': "
                        f"{len(uncovered)} critical aspect(s) not addressed by "
                        f"any of the {len(papers)} papers analyzed."
                    ),
                    confidence=min(conf, 0.85),
                    related_papers=_paper_refs(papers),
                    evidence=[
                        f"Uncovered aspects: {', '.join(uncovered[:5])}",
                        f"Covered aspects: {', '.join(list(covered_aspects)[:5])}",
                        f"Coverage gap: {len(uncovered)}/{len(expected_aspects)} "
                        f"expected aspects uncovered ({coverage_gap:.0%}).",
                        f"Corpus grounding: {len(grounded)}/{len(uncovered)} "
                        f"uncovered aspects have terminology present in the corpus"
                        + (f"; ungrounded (parametric): {', '.join(ungrounded[:3])}"
                           if ungrounded else "") + ".",
                        f"Aspect matching: semantic "
                        f"({'embedding' if matcher.uses_embeddings else 'lexical fallback'}), "
                        f"{len(covered_matches)} expected aspect(s) matched to corpus "
                        f"vocabulary despite different wording.",
                    ],
                    # Kutipan utk aspek grounded: terminologinya ADA di korpus
                    # tapi tidak dibahas sistematis — tunjukkan kalimatnya.
                    # Pakai kata-isi aspek (bukan frasa utuh) agar konsisten
                    # dengan uji grounding; frasa panjang tidak pernah cocok.
                    supporting_quotes=extract_supporting_quotes(
                        terms=[
                            term
                            for aspect in grounded[:5]
                            for term in aspect_terms(aspect)[:4]
                        ],
                        papers=papers,
                    ),
                    suggested_directions=[
                        f"Investigate: {aspect}" for aspect in (grounded + ungrounded)[:3]
                    ],
                    detection_method="aspect_coverage",
                    sub_indicators=[
                        {"aspect_matches": [m.to_dict() for m in uncovered_matches[:12]]}
                    ],
                ))
        
        # Evidence Gap Map (P8): an explicit domain/setting x outcome matrix
        # whose cells hold STUDY COUNTS, not weighted scores. Empty cells are
        # gap CANDIDATES — the literature provides no prespecified rule such as
        # "count < k and quality < q", so significance comes from the explicit
        # importance overlay rather than an invented threshold.
        if len(papers) >= 3:
            matrix = build_coverage_matrix(papers, paper_ref=_paper_ref)
            # A map needs at least a 2x2 grid to say anything: with a single row
            # or column there is nothing to compare against, and every cell is
            # trivially "the whole corpus".
            if len(matrix.rows) >= 2 and len(matrix.columns) >= 2:
                matrix = mark_important_columns(
                    matrix,
                    expected_aspects,
                    matcher=SemanticMatcher.from_vector_store(self.vector_store),
                )
                candidates = matrix.candidate_gaps()
                significant = [c for c in candidates if c.important and c.status == "empty"]
                # Thin cells alone are not a gap — the P8 signal is an EMPTY
                # cell. Without one the description degenerates into "0 of N
                # cells hold no study", which is a non-finding.
                if matrix.empty_cells:
                    # Confidence follows how sparse the map actually is, and is
                    # capped below the aspect-coverage signal because an empty
                    # cell is weaker evidence than a named uncovered aspect.
                    sparsity = 1.0 - matrix.density
                    importance_ratio = len(significant) / max(1, len(candidates))
                    conf = round(min(0.75, 0.25 + 0.35 * sparsity + 0.2 * importance_ratio), 3)
                    indicators.append(GapIndicator(
                        indicator_type=GapIndicatorType.INCOMPLETENESS,
                        description=(
                            f"Evidence gap map for '{topic}': "
                            f"{len(matrix.empty_cells)} of "
                            f"{len(matrix.rows) * len(matrix.columns)} "
                            f"row x column cells hold no study "
                            f"({len(matrix.rows)} domain/setting rows x "
                            f"{len(matrix.columns)} outcome columns; "
                            f"coverage density {matrix.density:.0%})."
                        ),
                        confidence=conf,
                        related_papers=_paper_refs(papers),
                        evidence=[
                            f"Rows (domain/setting/intervention): "
                            f"{', '.join(matrix.rows[:6])}",
                            f"Columns (outcome/question dimension): "
                            f"{', '.join(matrix.columns[:6])}",
                            f"Cell values are study counts, not weighted evidence "
                            f"scores; one study may occupy several cells "
                            f"(many-to-many mapping).",
                        ] + [
                            f"Candidate gap: '{c.row}' x '{c.column}' — "
                            f"{c.study_count} study(ies) [{c.status}]"
                            + (" — flagged decision-relevant" if c.important else "")
                            for c in candidates[:5]
                        ] + [
                            "No prespecified count/quality rule is applied: empty "
                            "cells are candidates for reviewer judgement, not "
                            "confirmed gaps.",
                        ] + (
                            [f"Unmapped papers (no row or column matched): "
                             f"{len(matrix.unmapped_papers)}"]
                            if matrix.unmapped_papers else []
                        ),
                        suggested_directions=[
                            f"Study '{c.column}' in the '{c.row}' context"
                            for c in (significant or candidates)[:3]
                        ],
                        # Sel kosong adalah klaim tentang KETIADAAN, jadi yang
                        # dapat dikutip adalah kalimat yang membuktikan baris dan
                        # kolomnya memang ada di korpus — hanya tidak pernah
                        # bertemu dalam satu studi.
                        supporting_quotes=extract_supporting_quotes(
                            terms=[
                                term
                                for cell in (significant or candidates)[:2]
                                for axis in (cell.row, cell.column)
                                for term in aspect_terms(axis)
                            ],
                            papers=papers,
                        ),
                        detection_method="evidence_gap_map",
                        sub_indicators=[{"coverage_matrix": matrix.to_dict()}],
                    ))
        
        # Check for missing methodology diversity
        methods_used = self._extract_methods(papers)
        if len(methods_used) <= 1 and len(papers) >= 3:
            # Calibrated: a single shared method across MORE papers is a stronger
            # incompleteness signal than across the minimum of 3.
            dominance = min(1.0, len(papers) / 5.0)
            conf = round(0.4 + 0.4 * dominance, 3)
            indicators.append(GapIndicator(
                indicator_type=GapIndicatorType.INCOMPLETENESS,
                description=(
                    f"Methodological incompleteness: all {len(papers)} papers "
                    f"use similar methodology ({', '.join(methods_used) or 'unidentified'}). "
                    f"Alternative methodological approaches are absent."
                ),
                confidence=conf,
                related_papers=_paper_refs(papers),
                evidence=[
                    f"Methods found: {', '.join(methods_used) or 'unidentified'}",
                    f"All {len(papers)} papers share a single methodological approach.",
                ],
                # Klaim "semua jurnal memakai metode yang sama" justru dibuktikan
                # oleh kalimat tempat metode itu disebut, jadi provenansnya bisa
                # ditelusuri, bukan sekadar hitungan.
                supporting_quotes=extract_supporting_quotes(
                    terms=[
                        term
                        for method in list(methods_used)[:3]
                        for term in aspect_terms(method)
                    ],
                    papers=papers,
                ),
                suggested_directions=[
                    "Apply alternative methodological approaches to this topic",
                    "Conduct a mixed-methods study",
                ],
                detection_method="methodology_coverage",
            ))
        
        return indicators
    
    # -------------------------------------------------------------------
    # Indicator 4: EVIDENCE-SUPPORT GAP
    # -------------------------------------------------------------------
    
    def _detect_support_gap(
        self,
        topic: str,
        papers: List[Dict[str, Any]],
    ) -> List[GapIndicator]:
        """
        Detect claims the corpus asserts but cannot ground in primary evidence.

        Per the P5/P9 reviews, retrieval failure is itself a finding: when a
        claim recurs across papers yet leave-one-out retrieval turns up no
        primary-evidence passage, the literature is echoing rather than
        demonstrating. This complements INCOMPLETENESS, which covers aspects
        that are never raised at all.
        """
        indicators: List[GapIndicator] = []

        if len(papers) < 3:
            return indicators

        matcher = SemanticMatcher.from_vector_store(self.vector_store)
        report = analyze_support(papers, _paper_ref, matcher=matcher)
        confidence = support_confidence(report)
        if confidence <= 0.0:
            logger.debug(
                f"Support gap: {report.unsupported}/{report.total_claims} claims "
                f"ungrounded (ratio {report.unsupported_ratio}) — below threshold"
            )
            return indicators

        gaps = report.gaps[:MAX_REPORTED_CLAIMS]
        if not gaps:
            return indicators

        involved = []
        for assessment in gaps:
            if assessment.claim.paper_ref not in involved:
                involved.append(assessment.claim.paper_ref)

        evidence = [
            f"{report.unsupported} dari {report.total_claims} klaim terperiksa "
            f"({report.unsupported_ratio:.0%}) tidak menemukan paragraf bukti "
            f"primer pendukung di jurnal lain.",
        ]
        if report.echo_claims:
            evidence.append(
                f"{report.echo_claims} klaim diulang lintas jurnal tanpa bukti "
                f"primer baru (citation echo)."
            )
        evidence.extend(
            f"[{a.claim.paper_ref}] \"{a.claim.text[:150]}\" — "
            f"dukungan {a.support_score:.2f}; {'; '.join(a.reasons[:2])}"
            for a in gaps[:3]
        )

        supporting_quotes = [
            {
                "quote": a.claim.text[:300],
                "source_paper": a.claim.paper_ref,
                "match_score": round(1.0 - a.support_score, 4),
                "context": "; ".join(a.reasons[:2]),
                "verified": True,
            }
            for a in gaps[:5]
        ]

        directions = [
            "Lakukan studi primer untuk menguji klaim yang selama ini hanya diulang",
            "Replikasi klaim inti dengan data dan protokol yang dilaporkan terbuka",
        ]
        if report.echo_claims:
            directions.append(
                "Telusuri rantai sitasi klaim berulang untuk menemukan sumber "
                "primer aslinya (atau membuktikan ketiadaannya)"
            )

        indicators.append(GapIndicator(
            indicator_type=GapIndicatorType.SUPPORT_GAP,
            description=(
                f"Ketiadaan dukungan bukti pada '{topic}': "
                f"{report.unsupported} dari {report.total_claims} klaim yang "
                f"diperiksa diasersikan tanpa bukti primer yang dapat ditemukan "
                f"di korpus. Aspeknya dibahas, tetapi tidak dibuktikan."
            ),
            confidence=confidence,
            related_papers=involved,
            evidence=evidence[:5],
            supporting_quotes=supporting_quotes,
            suggested_directions=directions,
            detection_method="evidence_support",
        ))

        return indicators
    
    # -------------------------------------------------------------------
    # Rule Engine Validation
    # -------------------------------------------------------------------
    
    def _validate_with_rule_engine(
        self,
        indicators: List[GapIndicator],
    ) -> List[GapIndicator]:
        """
        Pass each indicator through the Rule Engine for validation, then apply
        post-hoc calibration, selective abstention and provenance (P9).

        The symbolic verdict is treated as *evidence about* the claim rather
        than a second opinion to average: PASS corroborates, FLAG discounts,
        REJECT abstains. Indicators that survive but fall below the abstention
        band are kept with ``needs_review=True`` instead of being presented as
        findings.
        """
        validated = []
        for indicator in indicators:
            claim = {
                "type": "gap_indicator",
                "description": indicator.description,
                "confidence": indicator.confidence,
                "related_papers": indicator.related_papers,
            }
            # Link the indicator to concrete KG entities (METHOD / DOMAIN /
            # FINDING) so the Rule Engine's feasibility (F1-F3), causality
            # (C1-C3) and consistency (K1-K3) rules can actually fire instead
            # of defaulting to PASS for lack of an entity to reason over.
            claim.update(self._link_kg_entities(indicator))
            
            report = self.rule_engine.validate(claim)
            indicator.rule_engine_verdict = RuleVerdictType(report.overall_verdict) \
                if isinstance(report.overall_verdict, str) else report.overall_verdict
            indicator.adjusted_confidence = report.adjusted_confidence
            indicator.confidence = report.adjusted_confidence

            verdict_value = (
                indicator.rule_engine_verdict.value
                if hasattr(indicator.rule_engine_verdict, "value")
                else str(indicator.rule_engine_verdict or "")
            )
            self._apply_calibration(indicator, verdict_value, report)
            
            # Only include if not REJECTED
            if indicator.rule_engine_verdict != RuleVerdictType.REJECT:
                validated.append(indicator)
            else:
                logger.info(
                    f"Indicator REJECTED by Rule Engine: {indicator.description[:50]}..."
                )
        
        return validated

    def _apply_calibration(
        self,
        indicator: GapIndicator,
        verdict_value: str,
        report: Any = None,
    ) -> None:
        """Attach calibrated confidence, abstention flag and provenance chain."""
        result = self.calibrator.calibrate(indicator.confidence, verdict_value)
        indicator.calibrated_confidence = result["calibrated_confidence"]
        indicator.needs_review = bool(result["needs_review"])
        indicator.abstention_reasons = list(result["abstention_reasons"])
        indicator.calibration = result
        # A gap that cannot be traced back to a passage is not defensible even
        # when its number looks good, so a broken chain forces human review.
        detail = self._summarize_rule_report(report)
        chain = build_provenance(
            claim=indicator.description,
            cited_records=indicator.related_papers,
            retrieved_passages=indicator.supporting_quotes,
            validation_outcome=verdict_value,
            validation_detail=detail,
        )
        indicator.provenance = chain.to_dict()
        if not chain.complete:
            indicator.needs_review = True
            indicator.abstention_reasons.append(
                "provenans belum lengkap: " + ", ".join(chain.broken_links) + " hilang"
            )
        indicator.requires_human_validation = (
            indicator.requires_human_validation or indicator.needs_review
        )

    @staticmethod
    def _summarize_rule_report(report: Any) -> str:
        """One-line summary of which rules actually fired."""
        results = getattr(report, "results", None)
        if not results:
            return ""
        fired = []
        for r in results:
            rule = getattr(r, "rule", None)
            rule_id = getattr(rule, "rule_id", "") if rule is not None else ""
            verdict = getattr(r, "verdict", "")
            verdict = getattr(verdict, "value", verdict)
            if rule_id and verdict != "PASS":
                fired.append(f"{rule_id}:{verdict}")
        if not fired:
            checked = getattr(report, "rules_checked", len(results))
            return f"{checked} aturan diuji, tidak ada pelanggaran"
        return ", ".join(fired[:9])
    
    # -------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------

    def _extract_evidence_subgraph(
        self,
        entity_a_id: str,
        entity_b_id: str,
        max_edges: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Ekstrak subgraph KG kecil yang MENGHUBUNGKAN dua entitas dari paper
        berbeda (ala SciAgentsDiscovery) — bukti struktural bahwa gap yang
        diklaim benar-benar berakar pada relasi antar-jurnal di basis fakta.

        Returns list edge dict: {from, from_name, to, to_name, predicate,
        source_paper, confidence}. Kosong bila KG tak tersedia / tak terhubung.
        """
        kg = self.knowledge_graph
        if kg is None or not hasattr(kg, "find_paths_between_entities"):
            return []
        edges: List[Dict[str, Any]] = []
        seen = set()

        def _node_name(node_id: str) -> str:
            try:
                return kg.graph.nodes[node_id].get("name", node_id)
            except Exception:
                return node_id

        def _add_path(paths):
            for path in paths:
                for e in path:
                    key = (e.get("from"), e.get("to"), e.get("predicate"))
                    if key in seen:
                        continue
                    seen.add(key)
                    edge_data = {}
                    try:
                        edge_data = kg.graph.get_edge_data(e["from"], e["to"]) or {}
                    except Exception:
                        pass
                    edges.append({
                        "from": e.get("from"),
                        "from_name": _node_name(e.get("from")),
                        "to": e.get("to"),
                        "to_name": _node_name(e.get("to")),
                        "predicate": e.get("predicate", "UNKNOWN"),
                        "source_paper": edge_data.get("source_paper", ""),
                        "confidence": edge_data.get("confidence"),
                    })

        try:
            _add_path(kg.find_paths_between_entities(entity_a_id, entity_b_id, max_paths=3))
            # Graf berarah: cek arah sebaliknya juga.
            if not edges:
                _add_path(kg.find_paths_between_entities(entity_b_id, entity_a_id, max_paths=3))
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(f"Evidence subgraph extraction failed: {exc}")
        return edges[:max_edges]

    def _link_kg_entities(self, indicator: "GapIndicator") -> Dict[str, Any]:
        """
        Resolve the most relevant METHOD / DOMAIN / FINDING entities for an
        indicator's related papers, so the Rule Engine can reason over them.

        Without this, gap-indicator claims carried no `method`/`domain`/finding
        entity IDs, so every feasibility/causality rule fell through to a
        default PASS — making the "symbolic" validation layer inert in practice.
        """
        links: Dict[str, Any] = {}
        if not self.fact_table:
            return links

        methods: List[Any] = []
        domains: List[Any] = []
        findings: List[Any] = []
        for pid in indicator.related_papers or []:
            if not pid:
                continue
            try:
                methods += self.fact_table.find_entities(
                    entity_type=EntityType.METHOD, source_paper=pid
                )
                domains += self.fact_table.find_entities(
                    entity_type=EntityType.DOMAIN, source_paper=pid
                )
                findings += self.fact_table.find_entities(
                    entity_type=EntityType.FINDING, source_paper=pid
                )
            except Exception as e:
                logger.debug(f"Entity linking failed for paper {pid}: {e}")

        if methods:
            links["method"] = methods[0].entity_id
        if domains:
            links["domain"] = domains[0].entity_id
        if findings:
            links["findings"] = [f.entity_id for f in findings]
        return links

    def _calibrate_fragmentation_confidence(
        self,
        clusters: Dict[int, List[str]],
        paper_approaches: Dict[str, List[str]],
        cluster_result=None,
    ) -> float:
        """
        Derive fragmentation confidence from measured structure.

        When the graph metrics are available (P6), the dominant term is the
        distance from the cohesive reference band: a corpus whose modularity
        sits near the fragmented reference (Q≈0.42 with inter-cluster overlap
        below 15 %) scores high, one near the cohesive reference (Q≈0.93,
        silhouette≈0.97) scores low. Without them the estimator falls back to
        approach-set separation.
        """
        n_clusters = len(clusters)
        if n_clusters < 2:
            return 0.3

        # Approach-set per cluster
        cluster_sets: List[Set[str]] = []
        for pids in clusters.values():
            approaches: Set[str] = set()
            for pid in pids:
                approaches.update(a.lower() for a in paper_approaches.get(pid, []))
            cluster_sets.append(approaches)

        # Average pairwise Jaccard distance between clusters
        distances: List[float] = []
        for i in range(len(cluster_sets)):
            for j in range(i + 1, len(cluster_sets)):
                a, b = cluster_sets[i], cluster_sets[j]
                if not a and not b:
                    continue
                inter = len(a & b)
                union = len(a | b) or 1
                distances.append(1.0 - inter / union)
        separation = sum(distances) / len(distances) if distances else 0.5

        total_papers = len(paper_approaches) or 1
        breadth = min(1.0, n_clusters / total_papers)

        if cluster_result is None:
            confidence = 0.35 + 0.4 * separation + 0.15 * breadth
            return round(max(0.3, min(confidence, 0.9)), 3)

        # Cohesion penalty: high modularity WITH high silhouette means the
        # clusters are well-formed and mutually distinct — that is a cohesive
        # field, not a fragmented one.
        cohesion = 0.0
        if cluster_result.modularity >= Q_COHESIVE_MIN:
            cohesion = min(1.0, cluster_result.silhouette + 0.2)
        # Low vocabulary overlap between clusters is the fragmentation signal.
        disconnection = 1.0 - min(1.0, cluster_result.inter_cluster_overlap
                                  / max(OVERLAP_FRAGMENTED_MAX, 1e-6))

        confidence = (
            0.30
            + 0.30 * disconnection
            + 0.20 * separation
            + 0.10 * breadth
            - 0.25 * cohesion
        )
        return round(max(0.25, min(confidence, 0.9)), 3)

    def _detect_contradictions_nli(
        self,
        topic: str,
        papers: List[Dict[str, Any]],
    ) -> List[GapIndicator]:
        """
        Detect contradictions through the adjudicated pipeline mandated by the
        P7 literature review:

            normalize claims -> align variables (PICO) -> extract effect
            direction -> NLI -> adjudicate heterogeneity -> label

        Raw pairwise NLI is deliberately NOT the decision rule. The report
        states plainly that "pairwise NLI alone is insufficient" and that "no
        universal final contradiction-score cutoff is reported", so the NLI
        probability enters only as one evidence term inside
        `adjudicate_contradiction`, which returns one of four labels
        (contradiction / heterogeneous / non-comparable / inconclusive).

        Only `contradiction` becomes an INCONSISTENCY indicator; screened-out
        pairs are kept in `sub_indicators` so a reviewer can see what was
        rejected and why.
        """
        nli = getattr(self.relation_classifier, "nli_model", None) if self.relation_classifier else None
        nli_available = nli is not None and getattr(nli, "available", False)

        # Normalize each paper into comparable propositions. Papers with no
        # claim-bearing sentence contribute nothing, which alone removes a
        # large class of false positives coming from background prose.
        claims_by_paper: List[Tuple[str, List[NormalizedClaim]]] = []
        for p in papers[:8]:
            pid = _paper_ref(p)
            normalized = normalize_claims(p, pid, max_claims=3)
            if normalized:
                claims_by_paper.append((pid, normalized))

        if len(claims_by_paper) < 2:
            return []

        embedder = getattr(self.vector_store, "embedding_model", None) if self.vector_store else None
        indicators: List[GapIndicator] = []
        screened: List[Dict[str, Any]] = []

        for i in range(len(claims_by_paper)):
            for j in range(i + 1, len(claims_by_paper)):
                pid_a, claims_a = claims_by_paper[i]
                pid_b, claims_b = claims_by_paper[j]

                best = None  # (verdict, claim_a, claim_b)
                for claim_a in claims_a:
                    for claim_b in claims_b:
                        nli_score = 0.0
                        if nli_available:
                            try:
                                result = nli.check_contradiction(claim_a.text, claim_b.text)
                                if result:
                                    nli_score = float(result.get("confidence", 0.0))
                                    if not result.get("is_contradiction"):
                                        # Entailment/neutral: keep the score but
                                        # never let it argue FOR a contradiction.
                                        nli_score = min(nli_score, NLI_NOISE_FLOOR - 0.01)
                            except Exception as e:
                                logger.debug(f"NLI check failed: {e}")

                        verdict = adjudicate_contradiction(
                            claim_a, claim_b, nli_score=nli_score, embedder=embedder,
                        )
                        if best is None:
                            best = (verdict, claim_a, claim_b)
                        elif verdict.is_contradiction and (
                            not best[0].is_contradiction
                            or verdict.confidence > best[0].confidence
                        ):
                            best = (verdict, claim_a, claim_b)

                if best is None:
                    continue
                verdict, claim_a, claim_b = best
                if not verdict.is_contradiction:
                    screened.append({
                        "papers": [pid_a, pid_b],
                        "adjudication": verdict.label.value,
                        "reason": verdict.reason,
                    })
                    continue

                alignment_note = ""
                if verdict.alignment:
                    alignment_note = (
                        f"Variable alignment: {verdict.alignment.score:.2f} "
                        f"(gate {ALIGNMENT_GATE:.2f}"
                        + (", relaxed matching — PICO context incomplete"
                           if verdict.alignment.relaxed else "")
                        + ")"
                    )
                nli_note = (
                    f"NLI contradiction probability: {verdict.nli_score:.2f} "
                    f"(evidence term, not the decision rule)."
                ) if nli_available else (
                    "NLI model unavailable — decision rests on normalized effect "
                    "directions and variable alignment."
                )

                indicators.append(GapIndicator(
                    indicator_type=GapIndicatorType.INCONSISTENCY,
                    description=(
                        f"Adjudicated contradiction between two papers on "
                        f"'{topic}': {claim_a.signed_direction} vs "
                        f"{claim_b.signed_direction}. Screened against "
                        f"heterogeneity and comparability; requires human "
                        f"verification."
                    ),
                    confidence=round(verdict.confidence, 3),
                    related_papers=[pid_a, pid_b],
                    evidence=[e for e in [
                        f"Paper A claim: {claim_a.text[:200]}",
                        f"Paper B claim: {claim_b.text[:200]}",
                        f"Adjudication: {verdict.label.value} — {verdict.reason}",
                        alignment_note,
                        nli_note,
                    ] if e],
                    supporting_quotes=[
                        {"quote": claim_a.text[:300], "source_paper": pid_a, "match_score": 1.0},
                        {"quote": claim_b.text[:300], "source_paper": pid_b, "match_score": 1.0},
                    ],
                    suggested_directions=[
                        "Verify whether these findings genuinely conflict",
                        "Investigate moderators that could explain the divergence",
                        "Design a study that reconciles the contradiction",
                    ],
                    detection_method="nli_adjudicated" if nli_available else "claim_adjudication",
                    sub_indicators=[verdict.to_dict()],
                ))

        if screened:
            logger.info(
                f"Contradiction adjudication screened out {len(screened)} pair(s): "
                + ", ".join(sorted({s["adjudication"] for s in screened}))
            )
            for indicator in indicators:
                indicator.sub_indicators.append({"screened_pairs": screened[:10]})
        return indicators

    
    def _extract_approaches(
        self, papers: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Extract research approaches/keywords from each paper."""
        approaches = {}
        for paper in papers:
            pid = _paper_ref(paper)
            keywords = paper.get("metadata", {}).get("keywords", [])
            content = paper.get("content", "").lower()
            
            paper_approaches = list(keywords)
            
            # Extract methodology mentions
            method_terms = [
                "quantitative", "qualitative", "mixed methods",
                "survey", "experiment", "case study", "meta-analysis",
                "systematic review", "simulation", "deep learning",
                "machine learning", "statistical", "interview",
            ]
            for term in method_terms:
                if term in content:
                    paper_approaches.append(term)
            
            approaches[pid] = paper_approaches
        
        return approaches
    
    def _cluster_approaches(
        self, paper_approaches: Dict[str, List[str]]
    ) -> Dict[int, List[str]]:
        """Cluster papers by approach vocabulary (order-independent).

        Thin wrapper over `graph_metrics.cluster_papers` kept for callers that
        only need the grouping; `_detect_fragmentation` uses the full
        `ClusterResult` so it can report modularity and silhouette.
        """
        embedder = getattr(self.vector_store, "embedding_model", None) if self.vector_store else None
        return cluster_papers(paper_approaches, embedder=embedder).clusters

    def _analyze_structural_isolation(
        self, papers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Measure how isolated the corpus entities are in the KG and propose
        ranked bridges between the disconnected parts.

        Replaces the previous binary "is there a path" ratio, which threw away
        path length and could not say *which* connection is worth making. The
        isolation score is now the mean normalized path distance: unreachable
        pairs score 1.0, directly linked pairs score 0.0, and everything in
        between decays with hop count.
        """
        empty = {
            "isolation_score": 0.0,
            "disconnected_pairs": 0,
            "total_pairs": 0,
            "bridges": [],
            "filtered": [],
        }
        graph = getattr(self.knowledge_graph, "graph", None)
        if graph is None or not self.fact_table:
            return empty

        # Work on entities that actually carry findings, not raw paper ids:
        # retrieval passages rarely expose a doc_id, which made the old
        # implementation silently return 0.0 on real jobs.
        paper_refs = {_paper_ref(p) for p in papers if _paper_ref(p)}
        node_names: Dict[str, str] = {}
        node_types: Dict[str, str] = {}
        candidates: List[str] = []
        for node_id, data in graph.nodes(data=True):
            source_paper = str(data.get("source_paper") or "")
            if paper_refs and source_paper and not any(
                source_paper in ref or ref in source_paper for ref in paper_refs
            ):
                continue
            node_names[node_id] = data.get("name", node_id)
            node_types[node_id] = data.get("entity_type", "")
            candidates.append(node_id)

        if len(candidates) < 2:
            return empty

        try:
            import networkx as nx
            undirected = graph.to_undirected()
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(f"Structural isolation unavailable: {exc}")
            return empty

        sample = candidates[:30]
        distances: List[float] = []
        disconnected: List[Tuple[str, str]] = []
        for i, node_a in enumerate(sample):
            for node_b in sample[i + 1:]:
                try:
                    hops = nx.shortest_path_length(undirected, node_a, node_b)
                    # Normalize: 1 hop -> 0.0, 2 hops -> 0.5, 3 -> 0.67 ...
                    distances.append(1.0 - 1.0 / max(1, hops))
                except Exception:
                    distances.append(1.0)
                    disconnected.append((node_a, node_b))

        if not distances:
            return empty

        isolation_score = sum(distances) / len(distances)
        node_years = {
            node_id: data.get("year")
            for node_id, data in graph.nodes(data=True)
            if data.get("year")
        }
        kept, filtered = rank_bridges(
            undirected,
            disconnected[:60],
            node_names=node_names,
            node_types=node_types,
            node_years=node_years,
        )
        return {
            "isolation_score": round(isolation_score, 3),
            "disconnected_pairs": len(disconnected),
            "total_pairs": len(distances),
            "bridges": [b.to_dict() for b in kept],
            "filtered": [f.to_dict() for f in filtered],
        }

    def _compute_isolation_score(
        self, papers: List[Dict[str, Any]]
    ) -> float:
        """Backward-compatible scalar view of `_analyze_structural_isolation`."""
        return self._analyze_structural_isolation(papers)["isolation_score"]

    def _detect_contradictions_llm(
        self,
        topic: str,
        papers: List[Dict[str, Any]],
    ) -> List[GapIndicator]:
        """Use LLM to detect contradictions between papers."""
        indicators = []
        
        # Create summaries for comparison
        summaries = []
        for p in papers[:5]:
            title = p.get("metadata", {}).get("title", "Unknown")
            content = p.get("content", "")[:500]
            summaries.append(f"Paper: {title}\nFindings: {content}")
        
        if len(summaries) < 2:
            return indicators
        
        prompt = f"""Analyze these research papers on "{topic}" and identify any contradictory findings between them.

Papers:
{chr(10).join(summaries[:5])}

For each contradiction found, provide:
1. What paper A claims
2. What paper B claims  
3. Why these are contradictory
4. Whether any paper reconciles this contradiction

List contradictions (if none found, say "No contradictions detected"):"""

        try:
            from ...services.skill_guidance import wrap_prompt as _skill_wrap
            prompt, _sk = _skill_wrap("contradictions", prompt)
            response = self.llm.generate(prompt, temperature=0.2, max_tokens=1000)
            
            if "no contradiction" not in response.lower():
                # Anti-halusinasi: klaim LLM diverifikasi fuzzy terhadap chunk
                # korpus; hanya kalimat yang benar-benar ada di paper yang
                # disimpan sebagai kutipan pendukung.
                verified_quotes = []
                from .quote_grounding import split_sentences
                for candidate in split_sentences(response)[:6]:
                    check = verify_quote_against_papers(candidate, papers)
                    if check["verified"]:
                        verified_quotes.append({
                            "quote": candidate[:300],
                            "source_paper": check["source_paper"],
                            "match_score": check["match_score"],
                        })
                indicators.append(GapIndicator(
                    indicator_type=GapIndicatorType.INCONSISTENCY,
                    description=(
                        f"LLM-detected contradictions in '{topic}' literature. "
                        f"These require human verification."
                    ),
                    confidence=0.4,  # LLM-only signal: lower trust than the
                    # dedicated NLI cross-encoder (used as a fallback when NLI
                    # is unavailable or finds nothing).
                    related_papers=_paper_refs(papers[:5]),
                    evidence=[response[:500]],
                    supporting_quotes=verified_quotes[:3],
                    suggested_directions=[
                        "Verify these contradictions manually",
                        "Design study to reconcile contradictory findings",
                    ],
                    detection_method="llm_nli",
                ))
        except Exception as e:
            logger.error(f"LLM contradiction detection failed: {e}")
        
        return indicators
    
    def _extract_covered_aspects(
        self, papers: List[Dict[str, Any]]
    ) -> Set[str]:
        """Extract aspects/topics covered by the papers."""
        covered = set()
        for paper in papers:
            keywords = paper.get("metadata", {}).get("keywords", [])
            covered.update(k.lower() for k in keywords)
            
            content = paper.get("content", "").lower()
            # Extract topic-specific aspects
            aspect_terms = [
                "effectiveness", "efficiency", "scalability", "usability",
                "reliability", "validity", "generalizability", "reproducibility",
                "equity", "accessibility", "cost", "implementation",
                "ethical", "privacy", "security", "sustainability",
            ]
            for term in aspect_terms:
                if term in content:
                    covered.add(term)
        
        return covered
    
    def _ground_aspects(
        self,
        aspects: List[str],
        papers: List[Dict[str, Any]],
    ) -> tuple:
        """
        Split uncovered aspects into corpus-grounded vs ungrounded.

        An aspect is *grounded* when at least one of its content words appears
        somewhere in the analyzed papers' text — meaning the topic exists in
        the corpus but is not systematically covered. Ungrounded aspects come
        purely from the LLM's parametric knowledge and may reflect
        pre-training bias rather than a real coverage gap in this corpus.
        """
        stopwords = _ASPECT_STOPWORDS
        corpus_text = " ".join(
            p.get("content", "").lower() for p in papers
        )
        grounded, ungrounded = [], []
        for aspect in aspects:
            words = aspect_terms(aspect)
            if words and any(w in corpus_text for w in words):
                grounded.append(aspect)
            else:
                ungrounded.append(aspect)
        return grounded, ungrounded

    def _identify_expected_aspects(self, topic: str) -> List[str]:
        """Use LLM to identify expected aspects for a research topic."""
        if not self.llm:
            return []
        
        prompt = f"""For the research topic "{topic}", list 8-10 critical aspects that a comprehensive literature review should cover.

Return ONLY a numbered list, one aspect per line. Example:
1. Effectiveness
2. Scalability
3. Ethical considerations
...

Critical aspects for "{topic}":"""

        try:
            from ...services.skill_guidance import wrap_prompt as _skill_wrap
            prompt, _sk = _skill_wrap("aspects", prompt)
            response = self.llm.generate(prompt, temperature=0.3, max_tokens=300)
            aspects = []
            for line in response.strip().split('\n'):
                line = line.strip()
                if line and line[0].isdigit():
                    # Remove numbering
                    aspect = line.lstrip('0123456789.').strip()
                    if aspect:
                        aspects.append(aspect)
            return aspects
        except Exception as e:
            logger.error(f"Failed to identify expected aspects: {e}")
            return []
    
    def _extract_methods(
        self, papers: List[Dict[str, Any]]
    ) -> Set[str]:
        """Extract research methods from papers."""
        methods = set()
        for paper in papers:
            content = paper.get("content", "").lower()
            method_map = {
                "quantitative": "quantitative",
                "qualitative": "qualitative",
                "mixed method": "mixed methods",
                "survey": "survey",
                "experiment": "experiment",
                "case study": "case study",
                "simulation": "simulation",
                "deep learning": "deep learning",
                "machine learning": "machine learning",
                "statistical analysis": "statistical analysis",
            }
            for keyword, method in method_map.items():
                if keyword in content:
                    methods.add(method)
        
        return methods

    def find_contradictions(
        self,
        papers: List[Dict[str, Any]]
    ) -> List[GapIndicator]:
        """
        Legacy-compatible method: find contradictions.
        Now returns GapIndicator objects (INCONSISTENCY type).
        """
        return self._detect_inconsistency("", papers)


# Example usage
if __name__ == "__main__":
    analyzer = GapAnalyzer()
    print("GapAnalyzer ready (Cooper/Booth 3-indicator model)")

