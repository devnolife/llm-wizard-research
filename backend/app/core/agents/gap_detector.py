"""
Gap Detector Agent

Detects synthesis gap indicators using the 3-indicator model
(Cooper 1998, Booth 2012): Fragmentation, Inconsistency, Incompleteness.

This agent orchestrates gap detection by:
1. Extracting facts from papers (via FactExtractor)
2. Classifying relations (via RelationClassifier)
3. Detecting gap indicators (via GapAnalyzer)
4. Validating through Rule Engine

NOTE: Outputs are INDICATORS, not final gaps.
      Requires human validation (decision support tool).

References:
    - revisi.md Sections 3, 4, 6, 7
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict

from loguru import logger


class GapDetectorAgent:
    """
    Detects synthesis gap INDICATORS (not final gaps) in research literature.
    
    Three indicators (Cooper 1998, Booth 2012):
    1. Fragmentation — papers don't integrate with each other
    2. Inconsistency — contradictory findings without reconciliation
    3. Incompleteness — critical aspects not collectively covered
    
    All outputs require human validation.
    """
    
    def __init__(
        self,
        llm_interface=None,
        retriever=None,
        knowledge_graph=None,
        fact_table=None,
        fact_extractor=None,
        gap_analyzer=None,
        relation_classifier=None,
        rule_engine=None,
    ):
        self.llm = llm_interface
        self.retriever = retriever
        self.knowledge_graph = knowledge_graph
        self.fact_table = fact_table
        self.fact_extractor = fact_extractor
        self.gap_analyzer = gap_analyzer
        self.relation_classifier = relation_classifier
        self.rule_engine = rule_engine
        
        logger.info("GapDetectorAgent initialized (Cooper/Booth 3-indicator model)")
    
    def detect_gaps(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect synthesis gap indicators for a given query/domain.
        
        Pipeline:
        1. Retrieve relevant papers
        2. Extract facts (SPO triples) from papers
        3. Detect gap indicators (fragmentation, inconsistency, incompleteness)
        4. Validate through Rule Engine
        5. Return indicators with confidence + evidence
        
        Args:
            query: Research query or domain
            context: Additional context (analyzed papers, themes, etc.)
            
        Returns:
            Dict with gap indicators, fact stats, and validation results
        """
        logger.info(f"Detecting synthesis gap indicators for: '{query[:50]}...'")
        
        result = {
            "query": query,
            "indicators": [],
            "fact_extraction_stats": {},
            "summary": "",
            "total_indicators": 0,
            "indicators_by_type": {
                "FRAGMENTATION": 0,
                "INCONSISTENCY": 0,
                "INCOMPLETENESS": 0,
            },
            "rule_engine_stats": {
                "passed": 0,
                "flagged": 0,
                "rejected": 0,
            },
        }
        
        # Step 1: Get papers
        papers = self._get_papers(query, context)
        if not papers:
            result["summary"] = "No papers found for analysis."
            return result
        
        # Step 2: Extract facts from papers (if FactExtractor available)
        # PERF: Skip if the FactTable is already populated (e.g. the Coordinator
        # already ran fact extraction for this same analysis). Re-extracting the
        # same papers doubles the LLM calls for zero new information.
        if self.fact_extractor and self.fact_table:
            try:
                existing_facts = 0
                try:
                    existing_facts = self.fact_table.get_statistics().get("total_facts", 0)
                except Exception:
                    existing_facts = 0

                if existing_facts > 0:
                    logger.info(
                        f"Skipping fact extraction — FactTable already has "
                        f"{existing_facts} facts (reusing prior extraction)."
                    )
                else:
                    extraction_stats = self.fact_extractor.extract_from_papers(
                        papers, self.fact_table
                    )
                    result["fact_extraction_stats"] = extraction_stats

                    # Build KG from fact table
                    if self.knowledge_graph:
                        self.knowledge_graph.build_from_fact_table(self.fact_table)

            except Exception as e:
                logger.error(f"Fact extraction failed: {e}")
        
        # Step 3: Detect gap indicators
        if self.gap_analyzer:
            try:
                indicators = self.gap_analyzer.analyze_gaps(
                    topic=query,
                    papers=papers,
                    depth="standard",
                )
                
                for indicator in indicators:
                    result["indicators"].append(indicator.to_dict())
                    itype = indicator.indicator_type.value
                    result["indicators_by_type"][itype] = \
                        result["indicators_by_type"].get(itype, 0) + 1
                    
                    # Track rule engine stats
                    if indicator.rule_engine_verdict == "PASS":
                        result["rule_engine_stats"]["passed"] += 1
                    elif indicator.rule_engine_verdict == "FLAG":
                        result["rule_engine_stats"]["flagged"] += 1
                    elif indicator.rule_engine_verdict == "REJECT":
                        result["rule_engine_stats"]["rejected"] += 1
                
                result["total_indicators"] = len(indicators)
                
            except Exception as e:
                logger.error(f"Gap analysis failed: {e}")
        else:
            # Fallback: use LLM directly
            result = self._detect_gaps_llm_fallback(query, papers, result)
        
        # Generate summary
        result["summary"] = self._generate_summary(query, result)
        
        logger.info(
            f"Detected {result['total_indicators']} gap indicators: "
            f"F={result['indicators_by_type']['FRAGMENTATION']}, "
            f"I={result['indicators_by_type']['INCONSISTENCY']}, "
            f"C={result['indicators_by_type']['INCOMPLETENESS']}"
        )
        
        return result
    
    def _get_papers(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Get papers from context or retriever."""
        papers = []
        
        # Try from context first
        if context and "analysis" in context:
            papers = context["analysis"].get("key_papers", [])
        
        if context and "papers" in context:
            papers = context["papers"]
        
        # Fallback to retriever
        if not papers and self.retriever:
            try:
                results = self.retriever.retrieve(query, top_k=10)
                papers = [
                    {
                        "doc_id": r.document.metadata.get("doc_id", f"paper_{i}"),
                        "title": r.document.metadata.get("title", "Unknown"),
                        "content": r.document.content,
                        "metadata": r.document.metadata,
                    }
                    for i, r in enumerate(results)
                ]
            except Exception as e:
                logger.error(f"Paper retrieval failed: {e}")
        
        return papers
    
    def _detect_gaps_llm_fallback(
        self,
        query: str,
        papers: List[Dict],
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fallback when GapAnalyzer is not available: use LLM directly."""
        if not self.llm:
            return result
        
        try:
            papers_summary = "\n\n".join([
                f"- {p.get('metadata', {}).get('title', 'Unknown')}: "
                f"{p.get('content', '')[:300]}"
                for p in papers[:5]
            ])
            
            llm_gaps = self.llm.detect_gaps(
                context=query,
                papers=[p.get('metadata', {}).get('title', '') for p in papers[:10]]
            )
            
            result["summary"] = llm_gaps
            result["indicators"].append({
                "indicator_type": "LLM_UNVALIDATED",
                "description": llm_gaps[:500],
                "confidence": 0.3,  # Low confidence for unvalidated LLM output
                "requires_human_validation": True,
                "rule_engine_verdict": "PENDING",
            })
            result["total_indicators"] = 1
            
        except Exception as e:
            logger.error(f"LLM fallback gap detection failed: {e}")
        
        return result
    
    def _generate_summary(
        self, query: str, result: Dict[str, Any]
    ) -> str:
        """Generate human-readable summary of findings."""
        total = result["total_indicators"]
        by_type = result["indicators_by_type"]
        
        if total == 0:
            return f"No synthesis gap indicators detected for '{query}'."
        
        parts = [
            f"Detected {total} synthesis gap indicator(s) for '{query}':",
        ]
        
        if by_type["FRAGMENTATION"] > 0:
            parts.append(
                f"  - {by_type['FRAGMENTATION']} fragmentation indicator(s): "
                f"Literature is divided into isolated clusters"
            )
        if by_type["INCONSISTENCY"] > 0:
            parts.append(
                f"  - {by_type['INCONSISTENCY']} inconsistency indicator(s): "
                f"Contradictory findings without reconciliation"
            )
        if by_type["INCOMPLETENESS"] > 0:
            parts.append(
                f"  - {by_type['INCOMPLETENESS']} incompleteness indicator(s): "
                f"Critical aspects not collectively covered"
            )
        
        parts.append("\n⚠️ All indicators require human validation.")
        
        return "\n".join(parts)


# Example usage
if __name__ == "__main__":
    gap_detector = GapDetectorAgent()
    print("GapDetectorAgent ready (Cooper/Booth 3-indicator model)")
