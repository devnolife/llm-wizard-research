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
from collections import Counter
from enum import Enum

from loguru import logger
import numpy as np


class GapIndicatorType(str, Enum):
    """Three mainstream synthesis gap indicators (Cooper 1998, Booth 2012)"""
    FRAGMENTATION = "FRAGMENTATION"
    INCONSISTENCY = "INCONSISTENCY"
    INCOMPLETENESS = "INCOMPLETENESS"


@dataclass
class GapIndicator:
    """
    Represents a detected synthesis gap INDICATOR (not a final gap).
    
    The system outputs indicators that must be validated by a human researcher.
    See revisi.md Section 4: Batasan Epistemologis.
    """
    indicator_type: GapIndicatorType
    description: str
    confidence: float                    # 0.0 - 1.0
    related_papers: List[str]            # Paper IDs involved
    evidence: List[str]                  # Supporting evidence texts
    suggested_directions: List[str]      # Potential research directions
    requires_human_validation: bool = True  # Always True per revisi.md
    rule_engine_verdict: str = "PENDING"    # PASS/FLAG/REJECT from Rule Engine
    
    # Metadata for traceability
    detection_method: str = ""           # e.g., "topic_clustering", "nli_check"
    sub_indicators: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "indicator_type": self.indicator_type.value,
            "description": self.description,
            "confidence": self.confidence,
            "related_papers": self.related_papers,
            "evidence": self.evidence[:5],
            "suggested_directions": self.suggested_directions,
            "requires_human_validation": self.requires_human_validation,
            "rule_engine_verdict": self.rule_engine_verdict,
            "detection_method": self.detection_method,
        }


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
        
        # Validate through Rule Engine (if available)
        if self.rule_engine:
            indicators = self._validate_with_rule_engine(indicators)
        
        # Rank by confidence
        indicators.sort(key=lambda x: x.confidence, reverse=True)
        
        logger.info(f"Detected {len(indicators)} gap indicators")
        return indicators
    
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
        
        Methods:
        - Topic clustering: find papers in isolated clusters
        - Citation gap: papers that should cite each other but don't
        - Theory diversity: same phenomenon, different theoretical lenses
        """
        indicators = []
        
        if len(papers) < 2:
            return indicators
        
        # Method 1: Keyword/approach clustering
        paper_approaches = self._extract_approaches(papers)
        clusters = self._cluster_approaches(paper_approaches)
        
        if len(clusters) >= 2:
            # Multiple distinct clusters = potential fragmentation
            cluster_descriptions = []
            for cluster_id, cluster_papers in clusters.items():
                approaches = set()
                for pid in cluster_papers:
                    approaches.update(paper_approaches.get(pid, []))
                cluster_descriptions.append(
                    f"Cluster {cluster_id + 1}: {', '.join(list(approaches)[:3])}"
                )
            
            indicators.append(GapIndicator(
                indicator_type=GapIndicatorType.FRAGMENTATION,
                description=(
                    f"Literature on '{topic}' appears fragmented into "
                    f"{len(clusters)} distinct clusters with different approaches. "
                    f"No integrative framework found."
                ),
                confidence=min(0.5 + len(clusters) * 0.1, 0.85),
                related_papers=[pid for pids in clusters.values() for pid in pids],
                evidence=cluster_descriptions,
                suggested_directions=[
                    f"Develop an integrative framework that unifies the {len(clusters)} approaches",
                    "Conduct a systematic review comparing methodological paradigms",
                ],
                detection_method="topic_clustering",
                sub_indicators=[
                    {"cluster_id": cid, "papers": pids}
                    for cid, pids in clusters.items()
                ],
            ))
        
        # Method 2: Check cross-referencing via KG
        if self.knowledge_graph and self.fact_table:
            isolation_score = self._compute_isolation_score(papers)
            if isolation_score > 0.6:
                indicators.append(GapIndicator(
                    indicator_type=GapIndicatorType.FRAGMENTATION,
                    description=(
                        f"Papers on '{topic}' show low cross-referencing "
                        f"(isolation score: {isolation_score:.2f}). "
                        f"Findings exist in silos."
                    ),
                    confidence=isolation_score,
                    related_papers=[p.get("doc_id", "") for p in papers],
                    evidence=[f"Isolation score: {isolation_score:.2f}"],
                    suggested_directions=[
                        "Investigate connections between isolated research streams",
                    ],
                    detection_method="citation_isolation",
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
        
        # Method 1: Check FactTable for CONTRADICTS relations
        if self.fact_table:
            from ..knowledge.fact_table import PredicateType
            contradictions = self.fact_table.query(
                predicate=PredicateType.CONTRADICTS
            )
            
            for contradiction in contradictions:
                subject = self.fact_table.get_entity(contradiction.subject_id)
                obj = self.fact_table.get_entity(contradiction.object_id)
                
                subject_name = subject.name if subject else contradiction.subject_id
                object_name = obj.name if obj else contradiction.object_id
                
                indicators.append(GapIndicator(
                    indicator_type=GapIndicatorType.INCONSISTENCY,
                    description=(
                        f"Unreconciled contradiction: '{subject_name}' "
                        f"vs '{object_name}'. No study has resolved this "
                        f"inconsistency."
                    ),
                    confidence=contradiction.confidence,
                    related_papers=[contradiction.source_paper],
                    evidence=[contradiction.source],
                    suggested_directions=[
                        f"Investigate conditions under which each finding holds",
                        f"Design a study that reconciles these contradictory findings",
                    ],
                    detection_method="fact_table_contradicts",
                ))
        
        # Method 2: LLM-based contradiction detection
        if self.llm and len(papers) >= 2:
            llm_contradictions = self._detect_contradictions_llm(topic, papers)
            indicators.extend(llm_contradictions)
        
        return indicators
    
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
        
        # Use LLM to identify expected aspects
        if self.llm:
            expected_aspects = self._identify_expected_aspects(topic)
            
            uncovered = [a for a in expected_aspects if a.lower() not in 
                        {c.lower() for c in covered_aspects}]
            
            if uncovered:
                indicators.append(GapIndicator(
                    indicator_type=GapIndicatorType.INCOMPLETENESS,
                    description=(
                        f"Collective incompleteness detected for '{topic}': "
                        f"{len(uncovered)} critical aspect(s) not addressed by "
                        f"any of the {len(papers)} papers analyzed."
                    ),
                    confidence=min(0.4 + len(uncovered) * 0.1, 0.8),
                    related_papers=[p.get("doc_id", "") for p in papers],
                    evidence=[
                        f"Uncovered aspects: {', '.join(uncovered[:5])}",
                        f"Covered aspects: {', '.join(list(covered_aspects)[:5])}",
                    ],
                    suggested_directions=[
                        f"Investigate: {aspect}" for aspect in uncovered[:3]
                    ],
                    detection_method="aspect_coverage",
                ))
        
        # Check for missing methodology diversity
        methods_used = self._extract_methods(papers)
        if len(methods_used) <= 1 and len(papers) >= 3:
            indicators.append(GapIndicator(
                indicator_type=GapIndicatorType.INCOMPLETENESS,
                description=(
                    f"Methodological incompleteness: all {len(papers)} papers "
                    f"use similar methodology ({', '.join(methods_used) or 'unidentified'}). "
                    f"Alternative methodological approaches are absent."
                ),
                confidence=0.6,
                related_papers=[p.get("doc_id", "") for p in papers],
                evidence=[f"Methods found: {', '.join(methods_used)}"],
                suggested_directions=[
                    "Apply alternative methodological approaches to this topic",
                    "Conduct a mixed-methods study",
                ],
                detection_method="methodology_coverage",
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
        Pass each indicator through the Rule Engine for validation.
        Updates the rule_engine_verdict field.
        """
        validated = []
        for indicator in indicators:
            claim = {
                "type": "gap_indicator",
                "description": indicator.description,
                "confidence": indicator.confidence,
                "findings": indicator.related_papers,
            }
            
            report = self.rule_engine.validate(claim)
            indicator.rule_engine_verdict = report.overall_verdict
            indicator.confidence = report.adjusted_confidence
            
            # Only include if not REJECTED
            if report.overall_verdict != "REJECT":
                validated.append(indicator)
            else:
                logger.info(
                    f"Indicator REJECTED by Rule Engine: {indicator.description[:50]}..."
                )
        
        return validated
    
    # -------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------
    
    def _extract_approaches(
        self, papers: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Extract research approaches/keywords from each paper."""
        approaches = {}
        for paper in papers:
            pid = paper.get("doc_id", paper.get("id", ""))
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
        """Simple clustering based on keyword overlap."""
        papers = list(paper_approaches.keys())
        if len(papers) < 2:
            return {0: papers}
        
        # Compute pairwise similarity
        clusters: Dict[int, List[str]] = {}
        assigned = set()
        cluster_id = 0
        
        for i, pid in enumerate(papers):
            if pid in assigned:
                continue
            
            cluster = [pid]
            assigned.add(pid)
            
            for j, other_pid in enumerate(papers[i+1:], i+1):
                if other_pid in assigned:
                    continue
                
                # Jaccard similarity
                set_a = set(k.lower() for k in paper_approaches.get(pid, []))
                set_b = set(k.lower() for k in paper_approaches.get(other_pid, []))
                
                if set_a and set_b:
                    similarity = len(set_a & set_b) / len(set_a | set_b)
                else:
                    similarity = 0
                
                if similarity > 0.3:
                    cluster.append(other_pid)
                    assigned.add(other_pid)
            
            clusters[cluster_id] = cluster
            cluster_id += 1
        
        return clusters
    
    def _compute_isolation_score(
        self, papers: List[Dict[str, Any]]
    ) -> float:
        """
        Compute how isolated papers are from each other in the KG.
        High score = more fragmented.
        """
        if not self.knowledge_graph or len(papers) < 2:
            return 0.0
        
        paper_ids = [p.get("doc_id", "") for p in papers if p.get("doc_id")]
        if len(paper_ids) < 2:
            return 0.0
        
        connected_pairs = 0
        total_pairs = 0
        
        for i, pid_a in enumerate(paper_ids):
            for pid_b in paper_ids[i+1:]:
                total_pairs += 1
                path = self.knowledge_graph.find_shortest_path(pid_a, pid_b)
                if path:
                    connected_pairs += 1
        
        if total_pairs == 0:
            return 0.0
        
        # Isolation = 1 - connectivity ratio
        return 1.0 - (connected_pairs / total_pairs)
    
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
            response = self.llm.generate(prompt, temperature=0.2, max_tokens=1000)
            
            if "no contradiction" not in response.lower():
                indicators.append(GapIndicator(
                    indicator_type=GapIndicatorType.INCONSISTENCY,
                    description=(
                        f"LLM-detected contradictions in '{topic}' literature. "
                        f"These require human verification."
                    ),
                    confidence=0.5,  # Lower confidence for LLM-detected
                    related_papers=[p.get("doc_id", "") for p in papers[:5]],
                    evidence=[response[:500]],
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
            # Extract section headers as aspects
            import re
            headers = re.findall(r'\b(introduction|methodology|results|discussion|conclusion|background|related work)\b', content)
            
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

