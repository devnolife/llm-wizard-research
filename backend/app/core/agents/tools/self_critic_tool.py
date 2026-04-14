"""
Self-Critic Tool - Agent self-evaluation and reflection.

Evaluates the agent's own outputs for quality, consistency, and
completeness. Applies Rule Engine validation and generates
improvement suggestions. Implements the "evaluate" phase of the
observe→think→act→evaluate loop.
"""

from typing import Any, Dict, List, Optional
from loguru import logger


class SelfCriticTool:
    """Tool for agent self-evaluation and quality assurance."""
    
    name = "self_critic"
    description = (
        "Critically evaluate analysis results for quality, consistency, "
        "and completeness. Checks if gap indicators are well-supported, "
        "validates claims against the Rule Engine, and suggests improvements. "
        "Use this after generating analysis to ensure output quality."
    )
    
    def __init__(self, rule_engine=None, llm_interface=None, fact_table=None):
        self.rule_engine = rule_engine
        self.llm = llm_interface
        self.fact_table = fact_table
    
    def run(
        self,
        analysis_result: Dict[str, Any],
        original_query: str = "",
    ) -> Dict[str, Any]:
        """
        Evaluate analysis results.
        
        Args:
            analysis_result: The agent's analysis output to evaluate
            original_query: The user's original research query
            
        Returns:
            Evaluation with scores, issues, and suggestions
        """
        evaluation = {
            "overall_score": 0.0,
            "dimensions": {},
            "issues": [],
            "suggestions": [],
            "rule_engine_results": [],
            "requires_revision": False,
        }
        
        # Dimension 1: Completeness
        completeness = self._check_completeness(analysis_result)
        evaluation["dimensions"]["completeness"] = completeness
        
        # Dimension 2: Evidence support
        evidence = self._check_evidence_support(analysis_result)
        evaluation["dimensions"]["evidence_support"] = evidence
        
        # Dimension 3: Internal consistency
        consistency = self._check_consistency(analysis_result)
        evaluation["dimensions"]["consistency"] = consistency
        
        # Dimension 4: Rule Engine validation (if available)
        if self.rule_engine:
            rule_results = self._validate_with_rules(analysis_result)
            evaluation["rule_engine_results"] = rule_results
            evaluation["dimensions"]["rule_validation"] = {
                "score": rule_results.get("pass_rate", 0.0),
                "details": rule_results.get("summary", ""),
            }
        
        # Dimension 5: LLM-based critical evaluation
        if self.llm:
            llm_eval = self._llm_evaluate(analysis_result, original_query)
            evaluation["dimensions"]["llm_critique"] = llm_eval
        
        # Compute overall score
        scores = [
            d.get("score", 0.0)
            for d in evaluation["dimensions"].values()
            if isinstance(d, dict) and "score" in d
        ]
        evaluation["overall_score"] = (
            sum(scores) / len(scores) if scores else 0.0
        )
        
        # Determine if revision is needed
        evaluation["requires_revision"] = (
            evaluation["overall_score"] < 0.6
            or any(i.get("severity") == "critical" for i in evaluation["issues"])
        )
        
        return evaluation
    
    def _check_completeness(self, result: Dict) -> Dict[str, Any]:
        """Check if analysis covers all expected components."""
        expected_keys = [
            "indicators", "gaps", "gap_indicators",
            "recommendations", "fact_stats",
        ]
        
        found = []
        missing = []
        for key in expected_keys:
            if key in result and result[key]:
                found.append(key)
            else:
                missing.append(key)
        
        # Check indicator types coverage
        indicators = result.get("indicators", result.get("gap_indicators", []))
        indicator_types_found = set()
        if isinstance(indicators, list):
            for ind in indicators:
                ind_type = ind.get("type", ind.get("indicator_type", ""))
                if ind_type:
                    indicator_types_found.add(ind_type)
        
        expected_types = {"FRAGMENTATION", "INCONSISTENCY", "INCOMPLETENESS"}
        missing_types = expected_types - indicator_types_found
        
        score = len(found) / max(len(expected_keys), 1)
        if missing_types:
            score *= 0.8  # Penalize missing indicator types
        
        issues = []
        if missing:
            issues.append({
                "type": "missing_component",
                "severity": "warning",
                "message": f"Missing analysis components: {', '.join(missing)}",
            })
        if missing_types:
            issues.append({
                "type": "missing_indicator_type",
                "severity": "warning",
                "message": f"Missing indicator types: {', '.join(missing_types)}",
            })
        
        return {
            "score": round(score, 2),
            "found_components": found,
            "missing_components": missing,
            "indicator_types_found": list(indicator_types_found),
            "missing_indicator_types": list(missing_types),
            "issues": issues,
        }
    
    def _check_evidence_support(self, result: Dict) -> Dict[str, Any]:
        """Check if claims are supported by evidence."""
        indicators = result.get("indicators", result.get("gap_indicators", []))
        if not isinstance(indicators, list):
            return {"score": 0.5, "details": "No indicators to evaluate"}
        
        total = len(indicators)
        supported = 0
        unsupported = []
        
        for ind in indicators:
            evidence = ind.get("evidence", ind.get("supporting_papers", []))
            confidence = ind.get("confidence", 0.0)
            
            if evidence and confidence >= 0.5:
                supported += 1
            else:
                unsupported.append({
                    "indicator": ind.get("title", ind.get("description", "unknown"))[:100],
                    "confidence": confidence,
                    "has_evidence": bool(evidence),
                })
        
        score = supported / max(total, 1)
        
        return {
            "score": round(score, 2),
            "total_indicators": total,
            "supported": supported,
            "unsupported": unsupported[:5],
        }
    
    def _check_consistency(self, result: Dict) -> Dict[str, Any]:
        """Check internal consistency of analysis."""
        issues = []
        
        indicators = result.get("indicators", result.get("gap_indicators", []))
        if not isinstance(indicators, list):
            return {"score": 0.7, "details": "No indicators for consistency check"}
        
        # Check for duplicate descriptions
        descriptions = [
            ind.get("description", "")[:100]
            for ind in indicators
            if ind.get("description")
        ]
        if len(descriptions) != len(set(descriptions)):
            issues.append({
                "type": "duplicate_indicator",
                "severity": "warning",
                "message": "Duplicate indicator descriptions found",
            })
        
        # Check fact table consistency
        if self.fact_table:
            contradictions = self.fact_table.find_contradictions()
            if contradictions:
                issues.append({
                    "type": "fact_contradictions",
                    "severity": "critical" if len(contradictions) > 5 else "warning",
                    "message": f"Found {len(contradictions)} contradictions in fact table",
                })
        
        score = max(0.0, 1.0 - len(issues) * 0.2)
        return {"score": round(score, 2), "issues": issues}
    
    def _validate_with_rules(self, result: Dict) -> Dict[str, Any]:
        """Run Rule Engine on analysis claims."""
        if not self.rule_engine:
            return {"pass_rate": 0.5, "summary": "Rule engine not available"}
        
        indicators = result.get("indicators", result.get("gap_indicators", []))
        if not isinstance(indicators, list) or not indicators:
            return {"pass_rate": 0.5, "summary": "No indicators to validate"}
        
        total = 0
        passed = 0
        flagged = 0
        rejected = 0
        details = []
        
        for ind in indicators:
            claim = ind.get("description", ind.get("title", ""))
            if not claim:
                continue
            
            context = {
                "indicator_type": ind.get("type", ind.get("indicator_type", "")),
                "confidence": ind.get("confidence", 0.0),
                "evidence": ind.get("evidence", []),
            }
            
            try:
                report = self.rule_engine.validate(claim, context)
                total += 1
                
                verdict = str(report.overall_verdict)
                if verdict == "PASS":
                    passed += 1
                elif verdict == "FLAG":
                    flagged += 1
                else:
                    rejected += 1
                
                details.append({
                    "claim": claim[:100],
                    "verdict": verdict,
                    "adjusted_confidence": report.adjusted_confidence,
                })
            except Exception as e:
                logger.error(f"Rule validation failed: {e}")
        
        pass_rate = (passed + flagged * 0.5) / max(total, 1)
        
        return {
            "pass_rate": round(pass_rate, 2),
            "total_validated": total,
            "passed": passed,
            "flagged": flagged,
            "rejected": rejected,
            "details": details[:10],
            "summary": f"{passed} passed, {flagged} flagged, {rejected} rejected out of {total}",
        }
    
    def _llm_evaluate(
        self, result: Dict, original_query: str
    ) -> Dict[str, Any]:
        """Use LLM for critical evaluation."""
        if not self.llm:
            return {"score": 0.5, "details": "LLM not available"}
        
        # Summarize result for LLM
        indicators = result.get("indicators", result.get("gap_indicators", []))
        indicator_summary = ""
        if isinstance(indicators, list):
            for i, ind in enumerate(indicators[:5]):
                desc = ind.get("description", ind.get("title", ""))[:150]
                ind_type = ind.get("type", ind.get("indicator_type", ""))
                indicator_summary += f"\n{i+1}. [{ind_type}] {desc}"
        
        prompt = f"""Critically evaluate this research gap analysis:

Research Query: {original_query}

Gap Indicators Found:{indicator_summary if indicator_summary else " None"}

Evaluate on:
1. Are the gaps well-defined and specific (not vague)?
2. Are they supported by evidence from the literature?
3. Are they actionable (a researcher could address them)?
4. Do they represent genuine synthesis gaps (not just topics)?

Respond with JSON:
{{"score": 0.0-1.0, "strengths": ["..."], "weaknesses": ["..."], "suggestions": ["..."]}}"""
        
        try:
            response = self.llm.generate(prompt)
            import json
            text = response if isinstance(response, str) else str(response)
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.split("```")[0]
            parsed = json.loads(text.strip())
            return {
                "score": float(parsed.get("score", 0.5)),
                "strengths": parsed.get("strengths", []),
                "weaknesses": parsed.get("weaknesses", []),
                "suggestions": parsed.get("suggestions", []),
            }
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            return {"score": 0.5, "details": f"LLM evaluation error: {str(e)}"}
