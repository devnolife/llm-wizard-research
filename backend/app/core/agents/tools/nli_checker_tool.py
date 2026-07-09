"""
NLI Checker Tool - Natural Language Inference for contradiction detection.

Uses RelationClassifier to detect contradictions, causal claims,
and extensions between paper findings. Supports Rule Engine validation.
"""

from typing import Any, Dict, List, Optional
from loguru import logger


class NLICheckerTool:
    """Tool for checking logical relations between claims using NLI."""
    
    name = "nli_checker"
    description = (
        "Check the logical relationship between two claims or findings. "
        "Detects contradictions, causal relations, extensions, and "
        "co-occurrences. Use this to verify if findings from different "
        "papers agree or conflict."
    )
    
    def __init__(self, relation_classifier=None, llm_interface=None):
        self.relation_classifier = relation_classifier
        self.llm = llm_interface
    
    def run(
        self,
        claim_a: str,
        claim_b: str,
        context: str = "",
        semantic_similarity: Optional[float] = None,
        kg_facts: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Check the relation between two claims.
        
        Args:
            claim_a: First claim / finding
            claim_b: Second claim / finding
            context: Surrounding text context
            semantic_similarity: Pre-computed similarity score (0-1)
            kg_facts: Relevant KG facts for rule-based layer
            
        Returns:
            Classification result with relation_type, confidence, layers_used
        """
        result = {
            "claim_a": claim_a[:200],
            "claim_b": claim_b[:200],
            "relation_type": "UNKNOWN",
            "confidence": 0.0,
            "layers_used": [],
            "explanation": "",
        }
        
        if self.relation_classifier:
            try:
                classified = self.relation_classifier.classify(
                    entity_a=claim_a,
                    entity_b=claim_b,
                    text_context=context,
                    semantic_similarity=(
                        semantic_similarity
                        if semantic_similarity is not None
                        else 0.5
                    ),
                    kg_facts=kg_facts or [],
                )
                result["relation_type"] = classified.relation_type.value
                result["confidence"] = classified.confidence
                result["layers_used"] = classified.layers_used
                result["explanation"] = classified.explanation
            except Exception as e:
                logger.error(f"RelationClassifier failed: {e}")
                # Fallback: LLM-based NLI
                result = self._llm_fallback(claim_a, claim_b, context, result)
        else:
            result = self._llm_fallback(claim_a, claim_b, context, result)
        
        return result
    
    def _llm_fallback(
        self, claim_a: str, claim_b: str, context: str, result: Dict
    ) -> Dict[str, Any]:
        """Fallback to LLM for NLI when RelationClassifier not available."""
        if not self.llm:
            return result
        
        prompt = f"""Determine the logical relationship between these two claims:

Claim A: {claim_a}
Claim B: {claim_b}
{f"Context: {context}" if context else ""}

Classify as exactly one of:
- CONTRADICTION: Claims directly oppose each other
- CAUSAL: One claim implies a causal relationship with the other
- EXTENSION: One claim extends or builds upon the other
- CO_OCCURRENCE: Claims are related but no logical dependency

Respond with JSON:
{{"relation_type": "...", "confidence": 0.0-1.0, "explanation": "..."}}"""
        
        try:
            response = self.llm.generate(prompt)
            import json
            # Try parse JSON from response
            text = response if isinstance(response, str) else str(response)
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.split("```")[0]
            parsed = json.loads(text.strip())
            result["relation_type"] = parsed.get("relation_type", "UNKNOWN")
            result["confidence"] = float(parsed.get("confidence", 0.5))
            result["explanation"] = parsed.get("explanation", "")
            result["layers_used"] = ["llm_fallback"]
        except Exception as e:
            logger.error(f"LLM NLI fallback failed: {e}")
        
        return result
    
    def check_batch(
        self, claim_pairs: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Check multiple claim pairs.
        
        Args:
            claim_pairs: List of dicts with 'claim_a' and 'claim_b'
        """
        results = []
        for pair in claim_pairs:
            r = self.run(
                claim_a=pair["claim_a"],
                claim_b=pair["claim_b"],
                context=pair.get("context", ""),
            )
            results.append(r)
        return results
