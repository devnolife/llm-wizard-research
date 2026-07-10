"""
Relation Classifier - 3-Layer Mechanism to Distinguish Semantic Association vs Logical Relations

Implements the mechanism from revisi.md Section 6:
    Layer 1: SEMANTIC FILTERING (similarity > threshold?)
    Layer 2: EVIDENCE EXTRACTION (LLM finds causal/contradiction markers in text)
    Layer 3: RULE-BASED VALIDATION (check against KG facts)

Three types of relations:
    - CO_OCCURRENCE: Two concepts frequently appear together (NOT a logical relation)
    - CAUSAL: Concept A logically affects Concept B (supported by evidence)
    - CONTRADICTION: Finding A contradicts Finding B (supported by evidence)

References:
    - revisi.md Section 6: Pembeda Asosiasi Semantik vs Hubungan Logis
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


# ---------------------------------------------------------------------------
# Linguistic markers (from revisi.md Section 6)
# ---------------------------------------------------------------------------

CAUSAL_MARKERS = [
    "causes", "leads to", "results in", "because", "therefore",
    "consequently", "due to", "effect of", "contributes to",
    "enables", "prevents", "inhibits",
]

CONTRADICTION_MARKERS = [
    "however", "contradicts", "in contrast", "whereas",
    "on the other hand", "inconsistent with", "conflicts with",
    "contrary to", "disputes", "challenges",
]

EXTENSION_MARKERS = [
    "extends", "builds upon", "based on", "inspired by",
    "modification of", "improvement over",
]


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class RelationType(str, Enum):
    """Three types of relationships per revisi.md Section 6"""
    CO_OCCURRENCE = "CO_OCCURRENCE"   # Sering muncul bersama, BUKAN hubungan logis
    CAUSAL = "CAUSAL"                 # Hubungan kausal (A → B)
    CONTRADICTION = "CONTRADICTION"   # Temuan bertentangan
    EXTENSION = "EXTENSION"           # Konsep memperluas konsep lain
    UNKNOWN = "UNKNOWN"               # Belum terklasifikasi


@dataclass
class ClassifiedRelation:
    """Result of classifying a relation between two entities"""
    entity_a: str
    entity_b: str
    relation_type: RelationType
    semantic_similarity: float      # From Layer 1
    evidence_markers: List[str]     # Markers found in Layer 2
    evidence_text: str              # Text evidence from Layer 2
    rule_validated: bool            # Passed Layer 3?
    confidence: float               # Overall confidence
    explanation: str                # Human-readable explanation
    layers_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_a": self.entity_a,
            "entity_b": self.entity_b,
            "relation_type": self.relation_type.value,
            "semantic_similarity": self.semantic_similarity,
            "evidence_markers": self.evidence_markers,
            "evidence_text": self.evidence_text[:200] if self.evidence_text else "",
            "rule_validated": self.rule_validated,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "layers_used": self.layers_used,
        }


# ---------------------------------------------------------------------------
# RelationClassifier
# ---------------------------------------------------------------------------

class RelationClassifier:
    """
    3-Layer mechanism to distinguish semantic association from logical relations.
    
    Pipeline:
        Candidate relation (from semantic similarity)
            ↓
        [Layer 1] SEMANTIC FILTERING
            Similarity > threshold? Yes → continue, No → discard
            ↓
        [Layer 2] EVIDENCE EXTRACTION (LLM Agent)
            Find explicit evidence in text:
            • Causal markers: "causes", "leads to", "results in", ...
            • Contradiction markers: "however", "contradicts", ...
            • No markers → CO_OCCURRENCE ONLY
            ↓
        [Layer 3] RULE-BASED VALIDATION
            Check against KG facts
            Passes? → VALID RELATION | Fails → REJECTED + reason
    """

    def __init__(
        self,
        llm_interface=None,
        similarity_threshold: float = 0.3,
        causal_confidence_threshold: float = 0.5,
        nli_model=None,
    ):
        """
        Args:
            llm_interface: GLMInterface for evidence extraction
            similarity_threshold: Minimum semantic similarity for Layer 1
            causal_confidence_threshold: Minimum confidence for causal classification
            nli_model: Optional dedicated NLIModel (validation.nli_model) —
                provides an independent discriminative signal in Layer 2,
                decoupling contradiction detection from the generative LLM
        """
        self.llm = llm_interface
        self.similarity_threshold = similarity_threshold
        self.causal_confidence_threshold = causal_confidence_threshold
        self.nli_model = nli_model
        
        logger.info(
            "RelationClassifier initialized (3-layer pipeline"
            + (", dedicated NLI enabled" if nli_model else "")
            + ")"
        )

    def classify(
        self,
        entity_a: str,
        entity_b: str,
        text_context: str,
        semantic_similarity: float = 0.0,
        kg_facts: Optional[List[Dict]] = None,
    ) -> ClassifiedRelation:
        """
        Classify the relationship between two entities using 3-layer pipeline.
        
        Args:
            entity_a: First entity name/ID
            entity_b: Second entity name/ID
            text_context: Text containing both entities
            semantic_similarity: Pre-computed similarity score
            kg_facts: Facts from KG about these entities
            
        Returns:
            ClassifiedRelation with type and evidence
        """
        # Layer 1: Semantic Filtering
        if semantic_similarity < self.similarity_threshold:
            return ClassifiedRelation(
                entity_a=entity_a,
                entity_b=entity_b,
                relation_type=RelationType.UNKNOWN,
                semantic_similarity=semantic_similarity,
                evidence_markers=[],
                evidence_text="",
                rule_validated=False,
                confidence=semantic_similarity,
                explanation=(
                    f"Discarded: semantic similarity ({semantic_similarity:.2f}) "
                    f"below threshold ({self.similarity_threshold})"
                ),
                layers_used=["semantic_filter"],
            )
        
        # Layer 2: Evidence Extraction
        relation_type, markers, evidence = self._extract_evidence(
            entity_a, entity_b, text_context
        )
        
        # Layer 2b (optional): dedicated NLI model — independent signal that
        # can PROMOTE a co-occurrence to contradiction or corroborate one
        nli_note = ""
        if self.nli_model is not None:
            nli_result = self.nli_model.check_contradiction(entity_a, entity_b)
            if nli_result is not None:
                if nli_result["is_contradiction"] and relation_type != RelationType.CONTRADICTION:
                    relation_type = RelationType.CONTRADICTION
                    markers = markers + ["nli_model"]
                    nli_note = (
                        f" NLI model detected contradiction "
                        f"(p={nli_result['confidence']:.2f})."
                    )
                elif nli_result["is_contradiction"]:
                    markers = markers + ["nli_model"]
                    nli_note = (
                        f" Corroborated by NLI model "
                        f"(p={nli_result['confidence']:.2f})."
                    )
        
        # Layer 3: Rule-Based Validation
        validated, explanation = self._validate_with_rules(
            entity_a, entity_b, relation_type, kg_facts or []
        )
        if nli_note:
            explanation += nli_note
        
        # Calculate final confidence
        confidence = self._calculate_confidence(
            semantic_similarity, relation_type, markers, validated
        )
        
        return ClassifiedRelation(
            entity_a=entity_a,
            entity_b=entity_b,
            relation_type=relation_type,
            semantic_similarity=semantic_similarity,
            evidence_markers=markers,
            evidence_text=evidence,
            rule_validated=validated,
            confidence=confidence,
            explanation=explanation,
            layers_used=[
                "semantic_filter",
                "evidence_extraction",
                "rule_validation",
            ],
        )

    def classify_batch(
        self,
        pairs: List[Dict[str, Any]],
        text_context: str,
        kg_facts: Optional[List[Dict]] = None,
    ) -> List[ClassifiedRelation]:
        """
        Classify multiple entity pairs.
        
        Args:
            pairs: List of dicts with 'entity_a', 'entity_b', 'similarity'
            text_context: Full text context
            kg_facts: KG facts for validation
            
        Returns:
            List of ClassifiedRelation
        """
        results = []
        for pair in pairs:
            result = self.classify(
                entity_a=pair["entity_a"],
                entity_b=pair["entity_b"],
                text_context=text_context,
                semantic_similarity=pair.get("similarity", 0.5),
                kg_facts=kg_facts,
            )
            results.append(result)
        return results

    # -----------------------------------------------------------------------
    # Layer 2: Evidence Extraction
    # -----------------------------------------------------------------------

    def _extract_evidence(
        self,
        entity_a: str,
        entity_b: str,
        text: str,
    ) -> tuple[RelationType, List[str], str]:
        """
        Layer 2: Find explicit linguistic evidence of relation type in text.
        
        Returns:
            (relation_type, markers_found, evidence_text)
        """
        # Find sentences containing both entities
        sentences = self._find_relevant_sentences(text, entity_a, entity_b)
        relevant_text = " ".join(sentences)
        relevant_lower = relevant_text.lower()
        
        # Check for causal markers
        causal_found = []
        for marker in CAUSAL_MARKERS:
            if marker in relevant_lower:
                causal_found.append(marker)
        
        # Check for contradiction markers
        contradiction_found = []
        for marker in CONTRADICTION_MARKERS:
            if marker in relevant_lower:
                contradiction_found.append(marker)
        
        # Check for extension markers
        extension_found = []
        for marker in EXTENSION_MARKERS:
            if marker in relevant_lower:
                extension_found.append(marker)
        
        # Determine relation type based on evidence
        if contradiction_found:
            return (
                RelationType.CONTRADICTION,
                contradiction_found,
                relevant_text[:500],
            )
        elif causal_found:
            return (
                RelationType.CAUSAL,
                causal_found,
                relevant_text[:500],
            )
        elif extension_found:
            return (
                RelationType.EXTENSION,
                extension_found,
                relevant_text[:500],
            )
        else:
            # No markers found → CO_OCCURRENCE only
            return (
                RelationType.CO_OCCURRENCE,
                [],
                relevant_text[:500] if relevant_text else "",
            )

    def _extract_evidence_llm(
        self,
        entity_a: str,
        entity_b: str,
        text: str,
    ) -> tuple[RelationType, List[str], str]:
        """
        Layer 2 (LLM-enhanced): Use LLM to extract evidence.
        Only called when pattern matching is insufficient.
        """
        if not self.llm:
            return self._extract_evidence(entity_a, entity_b, text)
        
        prompt = f"""Analyze the relationship between "{entity_a}" and "{entity_b}" in the following text.

Determine if their relationship is:
1. CAUSAL: one directly affects or influences the other
2. CONTRADICTION: they have opposing/conflicting findings or claims
3. CO_OCCURRENCE: they merely appear together without logical connection

Text: {text[:2000]}

Respond with JSON:
{{"relation_type": "CAUSAL|CONTRADICTION|CO_OCCURRENCE", "evidence": "quote from text", "markers": ["list of linguistic markers found"]}}"""

        try:
            response = self.llm.generate(prompt, temperature=0.1, max_tokens=300)
            import json
            import re
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                rel_type = RelationType(data.get("relation_type", "CO_OCCURRENCE"))
                return (
                    rel_type,
                    data.get("markers", []),
                    data.get("evidence", ""),
                )
        except Exception as e:
            logger.error(f"LLM evidence extraction failed: {e}")
        
        # Fallback to pattern matching
        return self._extract_evidence(entity_a, entity_b, text)

    # -----------------------------------------------------------------------
    # Layer 3: Rule-Based Validation
    # -----------------------------------------------------------------------

    def _validate_with_rules(
        self,
        entity_a: str,
        entity_b: str,
        relation_type: RelationType,
        kg_facts: List[Dict],
    ) -> tuple[bool, str]:
        """
        Layer 3: Validate the classified relation against KG facts.
        
        Returns:
            (is_valid, explanation)
        """
        if relation_type == RelationType.CO_OCCURRENCE:
            return (
                True,
                f"Co-occurrence between '{entity_a}' and '{entity_b}'. "
                f"NOT a logical relationship — they merely appear together."
            )
        
        if relation_type == RelationType.CAUSAL:
            # Check if KG has supporting evidence
            supporting = [
                f for f in kg_facts
                if (f.get("subject_id") == entity_a and f.get("object_id") == entity_b)
                or (f.get("subject_id") == entity_b and f.get("object_id") == entity_a)
            ]
            
            if supporting:
                return (
                    True,
                    f"Causal relation '{entity_a}' → '{entity_b}' "
                    f"supported by {len(supporting)} KG fact(s)."
                )
            else:
                return (
                    False,
                    f"Causal relation '{entity_a}' → '{entity_b}' "
                    f"NOT supported by KG facts. Needs verification."
                )
        
        if relation_type == RelationType.CONTRADICTION:
            return (
                True,
                f"Contradiction between '{entity_a}' and '{entity_b}' "
                f"detected via linguistic evidence."
            )
        
        return (True, f"Relation validated: {relation_type.value}")

    # -----------------------------------------------------------------------
    # Utility methods
    # -----------------------------------------------------------------------

    def _find_relevant_sentences(
        self,
        text: str,
        entity_a: str,
        entity_b: str,
    ) -> List[str]:
        """Find sentences containing both entities."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        relevant = []
        a_lower = entity_a.lower()
        b_lower = entity_b.lower()
        
        for sentence in sentences:
            s_lower = sentence.lower()
            if a_lower in s_lower and b_lower in s_lower:
                relevant.append(sentence)
        
        # If no sentences contain both, find adjacent sentences
        if not relevant:
            for i, sentence in enumerate(sentences):
                s_lower = sentence.lower()
                if a_lower in s_lower or b_lower in s_lower:
                    # Include this and neighboring sentences
                    start = max(0, i - 1)
                    end = min(len(sentences), i + 2)
                    relevant.extend(sentences[start:end])
                    break
        
        return relevant[:5]  # Limit to 5 sentences

    def _calculate_confidence(
        self,
        similarity: float,
        relation_type: RelationType,
        markers: List[str],
        validated: bool,
    ) -> float:
        """Calculate overall confidence for the classified relation."""
        base_confidence = similarity * 0.3  # Semantic similarity contributes 30%
        
        # Evidence markers contribute up to 40%
        marker_score = min(len(markers) * 0.1, 0.4)
        
        # Rule validation contributes 30%
        validation_score = 0.3 if validated else 0.0
        
        # Adjust based on relation type
        if relation_type == RelationType.CO_OCCURRENCE:
            # Co-occurrence has lower confidence inherently
            return min(similarity * 0.5, 0.5)
        
        confidence = base_confidence + marker_score + validation_score
        return min(confidence, 1.0)
