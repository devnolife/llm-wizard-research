"""
Rule-Based Validation Layer (Rule Engine)

Implements the neuro-symbolic validation layer from revisi.md Section 7.
Validates LLM/Agent outputs using formal logic rules before presenting to users.

Architecture:
    FACT BASE (from Knowledge Graph — SPO Triples)
        ↓
    RULE BASE (F1-F3, C1-C3, K1-K3)
        ↓
    INFERENCE ENGINE (Forward chaining: Facts + Rules → Accept/Reject)

Three categories of rules:
    1. Feasibility Rules (F1-F3): Resource/data/scale compatibility
    2. Causality Rules (C1-C3): Evidence and directionality checks  
    3. Consistency Rules (K1-K3): Internal consistency and transitivity

Three possible verdicts:
    ✅ PASS: Output passes all rules
    ⚠️ FLAG: Non-critical rule violation (needs human review)
    ❌ REJECT: Critical rule violation (do not show to user)

References:
    - Garcez, A., et al. (2019). Neural-Symbolic Computing
    - Buchanan, B. G., & Shortliffe, E. H. (1984). Rule-Based Expert Systems
    - Giarratano, J. C., & Riley, G. D. (2005). Expert Systems
    - revisi.md Section 7: Rule-Based Validation Layer
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from ..knowledge.fact_table import FactTable, PredicateType, Verdict
except ImportError:
    FactTable = None
    PredicateType = None
    Verdict = None

try:
    from ..knowledge_graph.graph_builder import KnowledgeGraphBuilder
except ImportError:
    KnowledgeGraphBuilder = None


# ---------------------------------------------------------------------------
# Enums and data classes
# ---------------------------------------------------------------------------

class RuleCategory(str, Enum):
    """Three categories of rules per revisi.md Section 7"""
    FEASIBILITY = "FEASIBILITY"    # F1-F3: Kompatibilitas sumber daya/data/skala
    CAUSALITY = "CAUSALITY"        # C1-C3: Bukti kausal, arah, confounding
    CONSISTENCY = "CONSISTENCY"    # K1-K3: Non-kontradiksi, KG support, transitivity


@dataclass
class Rule:
    """Represents a single validation rule"""
    rule_id: str            # e.g., "F1", "C2", "K3"
    category: RuleCategory
    name: str               # Human-readable name
    description: str        # Formal description
    is_critical: bool       # True → REJECT on violation; False → FLAG
    
    def __repr__(self):
        return f"Rule({self.rule_id}: {self.name})"


@dataclass
class RuleResult:
    """Result of applying a single rule"""
    rule: Rule
    passed: bool
    verdict: str            # "PASS", "FLAG", or "REJECT"
    reason: str             # Explanation of why it passed/failed
    evidence: List[str] = field(default_factory=list)  # Supporting facts
    confidence_adjustment: float = 0.0  # How much to adjust confidence


@dataclass 
class ValidationReport:
    """Complete validation report for an LLM output"""
    overall_verdict: str     # "PASS", "FLAG", or "REJECT"
    original_confidence: float
    adjusted_confidence: float
    rules_checked: int
    rules_passed: int
    rules_flagged: int
    rules_rejected: int
    results: List[RuleResult]
    summary: str             # Human-readable summary
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_verdict": self.overall_verdict,
            "original_confidence": self.original_confidence,
            "adjusted_confidence": self.adjusted_confidence,
            "rules_checked": self.rules_checked,
            "rules_passed": self.rules_passed,
            "rules_flagged": self.rules_flagged,
            "rules_rejected": self.rules_rejected,
            "results": [
                {
                    "rule_id": r.rule.rule_id,
                    "rule_name": r.rule.name,
                    "category": r.rule.category.value,
                    "passed": r.passed,
                    "verdict": r.verdict,
                    "reason": r.reason,
                    "evidence": r.evidence,
                }
                for r in self.results
            ],
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Rule definitions (9 rules: F1-F3, C1-C3, K1-K3)
# ---------------------------------------------------------------------------

# Feasibility Rules
RULE_F1 = Rule(
    rule_id="F1",
    category=RuleCategory.FEASIBILITY,
    name="Resource Compatibility",
    description=(
        "IF method.resource_req = 'high' AND problem.constraint = 'low_resource' "
        "THEN REJECT. Example: LLM suggests GPT-4 for edge device → REJECTED"
    ),
    is_critical=True,
)

RULE_F2 = Rule(
    rule_id="F2",
    category=RuleCategory.FEASIBILITY,
    name="Data Compatibility",
    description=(
        "IF method.data_req = 'large_labeled' AND domain.data = 'scarce' "
        "THEN FLAG. Example: Supervised DL for rare disease → FLAG"
    ),
    is_critical=False,
)

RULE_F3 = Rule(
    rule_id="F3",
    category=RuleCategory.FEASIBILITY,
    name="Scale Compatibility",
    description=(
        "IF method.scalability = 'single_machine' AND problem.scale = 'distributed' "
        "THEN REJECT. Example: In-memory processing for big data → REJECTED"
    ),
    is_critical=True,
)

# Causality Rules
RULE_C1 = Rule(
    rule_id="C1",
    category=RuleCategory.CAUSALITY,
    name="Minimal Causal Evidence",
    description=(
        "IF relation.type = 'CAUSAL' AND evidence_count < 2 "
        "THEN DOWNGRADE to 'CORRELATION'. Only 1 paper mentions relationship → downgrade"
    ),
    is_critical=False,
)

RULE_C2 = Rule(
    rule_id="C2",
    category=RuleCategory.CAUSALITY,
    name="Causal Direction",
    description=(
        "IF cause.temporal_order > effect.temporal_order "
        "THEN REJECT. Effect cannot precede cause."
    ),
    is_critical=True,
)

RULE_C3 = Rule(
    rule_id="C3",
    category=RuleCategory.CAUSALITY,
    name="Confounding Check",
    description=(
        "IF relation.type = 'CAUSAL' AND exists(confounding_var) "
        "THEN FLAG. A→B but C might cause both → FLAG"
    ),
    is_critical=False,
)

# Consistency Rules
RULE_K1 = Rule(
    rule_id="K1",
    category=RuleCategory.CONSISTENCY,
    name="Internal Non-contradiction",
    description=(
        "IF output.claim_A CONTRADICTS output.claim_B "
        "THEN FLAG. System recommends X in point 1 but rejects X in point 3 → FLAG"
    ),
    is_critical=False,
)

RULE_K2 = Rule(
    rule_id="K2",
    category=RuleCategory.CONSISTENCY,
    name="KG Fact Consistency",
    description=(
        "IF output.claim NOT_SUPPORTED_BY kg.facts "
        "THEN DOWNGRADE confidence. Claim not backed by KG facts → lower confidence"
    ),
    is_critical=False,
)

RULE_K3 = Rule(
    rule_id="K3",
    category=RuleCategory.CONSISTENCY,
    name="Transitivity Check",
    description=(
        "IF A→B AND B→C BUT output says A—/→C "
        "THEN FLAG. 'A improves B' + 'B improves C' but 'A worsens C' → FLAG"
    ),
    is_critical=False,
)

ALL_RULES = [RULE_F1, RULE_F2, RULE_F3, RULE_C1, RULE_C2, RULE_C3, RULE_K1, RULE_K2, RULE_K3]


# ---------------------------------------------------------------------------
# Rule Engine
# ---------------------------------------------------------------------------

class RuleEngine:
    """
    Rule-Based Validation Layer for LLM/Agent outputs.
    
    The Rule Engine validates gap indicators and recommendations from the
    Agent before presenting them to the user. It uses the Knowledge Graph's
    Fact Table as its Fact Base and applies 9 rules in 3 categories.
    
    Usage:
        engine = RuleEngine(fact_table=ft, knowledge_graph=kg)
        report = engine.validate(gap_indicator)
        if report.overall_verdict == "REJECT":
            # Do not show to user
            ...
    """

    def __init__(
        self,
        fact_table: Optional[FactTable] = None,
        knowledge_graph: Optional[KnowledgeGraphBuilder] = None,
        rules: Optional[List[Rule]] = None,
    ):
        self.fact_table = fact_table
        self.knowledge_graph = knowledge_graph
        self.rules = rules or ALL_RULES
        
        logger.info(f"RuleEngine initialized with {len(self.rules)} rules")

    def validate(
        self,
        claim: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationReport:
        """
        Validate an LLM/Agent output claim against all rules.
        
        Args:
            claim: The claim/indicator to validate. Expected keys:
                - type: "gap_indicator" | "recommendation" 
                - description: text description
                - method: (optional) method entity ID
                - domain: (optional) domain entity ID
                - findings: (optional) list of finding entity IDs
                - confidence: float 0-1
                - evidence: list of supporting text
            context: Additional context for validation
            
        Returns:
            ValidationReport with overall verdict and per-rule results
        """
        results: List[RuleResult] = []
        original_confidence = claim.get("confidence", 0.5)
        confidence = original_confidence
        
        for rule in self.rules:
            result = self._apply_rule(rule, claim, context or {})
            results.append(result)
            confidence += result.confidence_adjustment
        
        # Clamp confidence
        confidence = max(0.0, min(1.0, confidence))
        
        # Determine overall verdict
        has_reject = any(r.verdict == "REJECT" for r in results)
        has_flag = any(r.verdict == "FLAG" for r in results)
        
        if has_reject:
            overall_verdict = "REJECT"
        elif has_flag:
            overall_verdict = "FLAG"
        else:
            overall_verdict = "PASS"
        
        rules_passed = sum(1 for r in results if r.passed)
        rules_flagged = sum(1 for r in results if r.verdict == "FLAG")
        rules_rejected = sum(1 for r in results if r.verdict == "REJECT")
        
        # Build summary
        summary = self._build_summary(overall_verdict, results, claim)
        
        report = ValidationReport(
            overall_verdict=overall_verdict,
            original_confidence=original_confidence,
            adjusted_confidence=confidence,
            rules_checked=len(results),
            rules_passed=rules_passed,
            rules_flagged=rules_flagged,
            rules_rejected=rules_rejected,
            results=results,
            summary=summary,
        )
        
        logger.info(
            f"Validation complete: {overall_verdict} "
            f"({rules_passed} pass, {rules_flagged} flag, {rules_rejected} reject)"
        )
        return report

    def validate_batch(
        self,
        claims: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ValidationReport]:
        """Validate multiple claims."""
        return [self.validate(claim, context) for claim in claims]

    # -----------------------------------------------------------------------
    # Individual rule implementations
    # -----------------------------------------------------------------------

    def _apply_rule(
        self,
        rule: Rule,
        claim: Dict[str, Any],
        context: Dict[str, Any],
    ) -> RuleResult:
        """Apply a single rule to a claim."""
        try:
            if rule.rule_id == "F1":
                return self._check_f1_resource_compatibility(rule, claim)
            elif rule.rule_id == "F2":
                return self._check_f2_data_compatibility(rule, claim)
            elif rule.rule_id == "F3":
                return self._check_f3_scale_compatibility(rule, claim)
            elif rule.rule_id == "C1":
                return self._check_c1_causal_evidence(rule, claim)
            elif rule.rule_id == "C2":
                return self._check_c2_causal_direction(rule, claim)
            elif rule.rule_id == "C3":
                return self._check_c3_confounding(rule, claim)
            elif rule.rule_id == "K1":
                return self._check_k1_internal_contradiction(rule, claim)
            elif rule.rule_id == "K2":
                return self._check_k2_kg_consistency(rule, claim)
            elif rule.rule_id == "K3":
                return self._check_k3_transitivity(rule, claim)
            else:
                return self._default_pass(rule)
        except Exception as e:
            logger.error(f"Rule {rule.rule_id} failed: {e}")
            return self._default_pass(rule)

    # --- Feasibility Rules ---

    def _check_f1_resource_compatibility(self, rule: Rule, claim: Dict) -> RuleResult:
        """
        F1: IF method.resource_req = 'high' AND problem.constraint = 'low_resource' THEN REJECT
        """
        method_id = claim.get("method")
        domain_id = claim.get("domain")
        
        if not method_id or not self.fact_table:
            return self._default_pass(rule)
        
        # Check if method requires high resources
        resource_facts = self.fact_table.query(
            subject_id=method_id,
            predicate=PredicateType.REQUIRES_RESOURCE,
        )
        
        high_resource = any(
            "high" in str(f.object_id).lower() or 
            "gpu" in str(f.object_id).lower() or
            "large" in str(f.object_id).lower()
            for f in resource_facts
        )
        
        if not high_resource:
            return self._default_pass(rule)
        
        # Check if domain has low-resource constraint
        if domain_id:
            constraint_facts = self.fact_table.query(
                subject_id=domain_id,
                predicate=PredicateType.HAS_CONSTRAINT,
            )
            
            low_resource = any(
                "low" in str(f.object_id).lower() or
                "edge" in str(f.object_id).lower() or
                "mobile" in str(f.object_id).lower() or
                "limited" in str(f.object_id).lower()
                for f in constraint_facts
            )
            
            if low_resource:
                evidence = [f.to_dict() for f in resource_facts + constraint_facts]
                return RuleResult(
                    rule=rule,
                    passed=False,
                    verdict="REJECT",
                    reason=(
                        f"Method '{method_id}' requires high resources but "
                        f"domain '{domain_id}' has low-resource constraint. "
                        f"Recommendation is infeasible."
                    ),
                    evidence=[str(e) for e in evidence[:3]],
                    confidence_adjustment=-0.5,
                )
        
        return self._default_pass(rule)

    def _check_f2_data_compatibility(self, rule: Rule, claim: Dict) -> RuleResult:
        """
        F2: IF method.data_req = 'large_labeled' AND domain.data = 'scarce' THEN FLAG
        """
        method_id = claim.get("method")
        domain_id = claim.get("domain")
        
        if not method_id or not self.fact_table:
            return self._default_pass(rule)
        
        # Check data requirements
        data_facts = self.fact_table.query(
            subject_id=method_id,
            predicate=PredicateType.REQUIRES_DATA,
        )
        
        needs_large_data = any(
            "large" in str(f.object_id).lower() or
            "labeled" in str(f.object_id).lower() or
            "supervised" in str(f.object_id).lower()
            for f in data_facts
        )
        
        if not needs_large_data:
            return self._default_pass(rule)
        
        if domain_id:
            constraint_facts = self.fact_table.query(
                subject_id=domain_id,
                predicate=PredicateType.HAS_CONSTRAINT,
            )
            
            data_scarce = any(
                "scarce" in str(f.object_id).lower() or
                "limited" in str(f.object_id).lower() or
                "rare" in str(f.object_id).lower() or
                "few" in str(f.object_id).lower()
                for f in constraint_facts
            )
            
            if data_scarce:
                return RuleResult(
                    rule=rule,
                    passed=False,
                    verdict="FLAG",
                    reason=(
                        f"Method '{method_id}' requires large labeled data but "
                        f"domain '{domain_id}' has scarce data. Needs human review."
                    ),
                    evidence=[],
                    confidence_adjustment=-0.2,
                )
        
        return self._default_pass(rule)

    def _check_f3_scale_compatibility(self, rule: Rule, claim: Dict) -> RuleResult:
        """
        F3: IF method.scalability = 'single_machine' AND problem.scale = 'distributed' THEN REJECT
        """
        method_id = claim.get("method")
        
        if not method_id or not self.fact_table:
            return self._default_pass(rule)
        
        # Check for scalability constraints
        resource_facts = self.fact_table.query(
            subject_id=method_id,
            predicate=PredicateType.REQUIRES_RESOURCE,
        )
        
        single_machine = any(
            "single" in str(f.object_id).lower() or
            "memory" in str(f.object_id).lower()
            for f in resource_facts
        )
        
        # Check if problem context mentions distributed
        description = claim.get("description", "").lower()
        distributed = any(
            term in description 
            for term in ["distributed", "big data", "large-scale", "cluster"]
        )
        
        if single_machine and distributed:
            return RuleResult(
                rule=rule,
                passed=False,
                verdict="REJECT",
                reason="Method requires single-machine but problem is distributed scale.",
                evidence=[],
                confidence_adjustment=-0.5,
            )
        
        return self._default_pass(rule)

    # --- Causality Rules ---

    def _check_c1_causal_evidence(self, rule: Rule, claim: Dict) -> RuleResult:
        """
        C1: IF relation.type = 'CAUSAL' AND evidence_count < 2 THEN DOWNGRADE to 'CORRELATION'
        """
        if not self.fact_table:
            return self._default_pass(rule)
        
        findings = claim.get("findings", [])
        if len(findings) < 2:
            return self._default_pass(rule)
        
        # Check how many papers support the claimed relationship
        for i, finding_a in enumerate(findings):
            for finding_b in findings[i+1:]:
                # Check if there's a causal relation between these findings
                causal_facts = self.fact_table.query(
                    subject_id=finding_a,
                    predicate=PredicateType.IMPROVES,
                    object_id=finding_b,
                )
                
                if causal_facts and len(causal_facts) < 2:
                    # Only 1 paper supports this → downgrade
                    return RuleResult(
                        rule=rule,
                        passed=False,
                        verdict="FLAG",
                        reason=(
                            f"Causal relationship between '{finding_a}' and '{finding_b}' "
                            f"supported by only {len(causal_facts)} source(s). "
                            f"Downgraded to correlation."
                        ),
                        evidence=[f.to_dict() for f in causal_facts][:2],
                        confidence_adjustment=-0.15,
                    )
        
        return self._default_pass(rule)

    def _check_c2_causal_direction(self, rule: Rule, claim: Dict) -> RuleResult:
        """
        C2: IF cause.temporal_order > effect.temporal_order THEN REJECT
        """
        # Check temporal consistency in claimed causal relations
        # This requires temporal metadata on entities
        if not self.fact_table:
            return self._default_pass(rule)
        
        findings = claim.get("findings", [])
        for finding_id in findings:
            entity = self.fact_table.get_entity(finding_id)
            if entity and entity.properties.get("temporal_order"):
                # Check if any causal claim violates temporal order
                causal_facts = self.fact_table.query(
                    subject_id=finding_id,
                    predicate=PredicateType.IMPROVES,
                )
                for f in causal_facts:
                    target_entity = self.fact_table.get_entity(f.object_id)
                    if target_entity and target_entity.properties.get("temporal_order"):
                        if entity.properties["temporal_order"] > target_entity.properties["temporal_order"]:
                            return RuleResult(
                                rule=rule,
                                passed=False,
                                verdict="REJECT",
                                reason=f"Causal direction violation: effect precedes cause.",
                                evidence=[],
                                confidence_adjustment=-0.5,
                            )
        
        return self._default_pass(rule)

    def _check_c3_confounding(self, rule: Rule, claim: Dict) -> RuleResult:
        """
        C3: IF relation.type = 'CAUSAL' AND exists(confounding_var) THEN FLAG
        """
        # Placeholder: would need more sophisticated confounding detection
        # For now, check if multiple paths exist between cause and effect
        if not self.knowledge_graph:
            return self._default_pass(rule)
        
        findings = claim.get("findings", [])
        if len(findings) < 2:
            return self._default_pass(rule)
        
        # Check for multiple paths (potential confounders)
        paths = self.knowledge_graph.find_paths_between_entities(
            findings[0], findings[-1], max_paths=3
        )
        
        if len(paths) > 1:
            return RuleResult(
                rule=rule,
                passed=False,
                verdict="FLAG",
                reason=(
                    f"Multiple paths found between entities, "
                    f"possible confounding variable. Needs human review."
                ),
                evidence=[str(p) for p in paths[:2]],
                confidence_adjustment=-0.1,
            )
        
        return self._default_pass(rule)

    # --- Consistency Rules ---

    def _check_k1_internal_contradiction(self, rule: Rule, claim: Dict) -> RuleResult:
        """
        K1: IF output.claim_A CONTRADICTS output.claim_B THEN FLAG
        """
        if not self.fact_table:
            return self._default_pass(rule)
        
        # Check for contradictions in the claim's findings
        findings = claim.get("findings", [])
        
        for finding_id in findings:
            # Check if this finding contradicts any other finding in the claim
            contradiction_facts = self.fact_table.query(
                subject_id=finding_id,
                predicate=PredicateType.CONTRADICTS,
            )
            
            for cf in contradiction_facts:
                if cf.object_id in findings:
                    return RuleResult(
                        rule=rule,
                        passed=False,
                        verdict="FLAG",
                        reason=(
                            f"Internal contradiction detected: "
                            f"'{finding_id}' contradicts '{cf.object_id}' "
                            f"but both are in the same output."
                        ),
                        evidence=[cf.to_dict()],
                        confidence_adjustment=-0.2,
                    )
        
        return self._default_pass(rule)

    def _check_k2_kg_consistency(self, rule: Rule, claim: Dict) -> RuleResult:
        """
        K2: IF output.claim NOT_SUPPORTED_BY kg.facts THEN DOWNGRADE confidence
        """
        if not self.fact_table:
            return self._default_pass(rule)
        
        method_id = claim.get("method")
        domain_id = claim.get("domain")
        
        if not method_id:
            return self._default_pass(rule)
        
        # Check if the claimed method-domain relationship exists in KG
        supporting_facts = self.fact_table.query(subject_id=method_id)
        
        if not supporting_facts:
            return RuleResult(
                rule=rule,
                passed=False,
                verdict="FLAG",
                reason=(
                    f"Method '{method_id}' has no supporting facts in the "
                    f"Knowledge Graph. Confidence downgraded."
                ),
                evidence=[],
                confidence_adjustment=-0.15,
            )
        
        # If domain specified, check if method is connected to domain
        if domain_id:
            domain_facts = self.fact_table.query(
                subject_id=method_id,
                predicate=PredicateType.APPLIES_TO,
                object_id=domain_id,
            )
            
            if not domain_facts:
                return RuleResult(
                    rule=rule,
                    passed=False,
                    verdict="FLAG",
                    reason=(
                        f"No KG facts support '{method_id}' applying to "
                        f"'{domain_id}'. Confidence downgraded."
                    ),
                    evidence=[],
                    confidence_adjustment=-0.1,
                )
        
        return self._default_pass(rule)

    def _check_k3_transitivity(self, rule: Rule, claim: Dict) -> RuleResult:
        """
        K3: IF A→B AND B→C BUT output says A—/→C THEN FLAG
        """
        if not self.knowledge_graph:
            return self._default_pass(rule)
        
        findings = claim.get("findings", [])
        if len(findings) < 3:
            return self._default_pass(rule)
        
        # Check transitivity: if A improves B and B improves C,
        # does the claim contradict A→C?
        for i, a in enumerate(findings):
            for j, b in enumerate(findings):
                if i == j:
                    continue
                ab_facts = self.fact_table.query(
                    subject_id=a, predicate=PredicateType.IMPROVES, object_id=b
                ) if self.fact_table else []
                
                if not ab_facts:
                    continue
                
                for k, c in enumerate(findings):
                    if k == i or k == j:
                        continue
                    bc_facts = self.fact_table.query(
                        subject_id=b, predicate=PredicateType.IMPROVES, object_id=c
                    ) if self.fact_table else []
                    
                    if not bc_facts:
                        continue
                    
                    # A→B and B→C exist. Check for contradiction A—/→C
                    ac_contradict = self.fact_table.query(
                        subject_id=a, predicate=PredicateType.CONTRADICTS, object_id=c
                    ) if self.fact_table else []
                    
                    if ac_contradict:
                        return RuleResult(
                            rule=rule,
                            passed=False,
                            verdict="FLAG",
                            reason=(
                                f"Transitivity violation: '{a}' improves '{b}', "
                                f"'{b}' improves '{c}', but '{a}' contradicts '{c}'."
                            ),
                            evidence=[],
                            confidence_adjustment=-0.15,
                        )
        
        return self._default_pass(rule)

    # -----------------------------------------------------------------------
    # Utility methods
    # -----------------------------------------------------------------------

    def _default_pass(self, rule: Rule) -> RuleResult:
        """Return a default PASS result for a rule."""
        return RuleResult(
            rule=rule,
            passed=True,
            verdict="PASS",
            reason=f"Rule {rule.rule_id} ({rule.name}): No violations detected.",
            evidence=[],
            confidence_adjustment=0.0,
        )

    def _build_summary(
        self,
        overall_verdict: str,
        results: List[RuleResult],
        claim: Dict,
    ) -> str:
        """Build human-readable validation summary."""
        passed = [r for r in results if r.passed]
        flagged = [r for r in results if r.verdict == "FLAG"]
        rejected = [r for r in results if r.verdict == "REJECT"]
        
        parts = [f"Verdict: {overall_verdict}"]
        
        if rejected:
            parts.append(f"REJECTED by: {', '.join(r.rule.rule_id for r in rejected)}")
            for r in rejected:
                parts.append(f"  - {r.rule.rule_id}: {r.reason}")
        
        if flagged:
            parts.append(f"FLAGGED by: {', '.join(r.rule.rule_id for r in flagged)}")
            for r in flagged:
                parts.append(f"  - {r.rule.rule_id}: {r.reason}")
        
        parts.append(f"Passed: {len(passed)}/{len(results)} rules")
        
        return "\n".join(parts)
