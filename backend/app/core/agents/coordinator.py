"""
Coordinator Agent — LangGraph-based Agentic Orchestrator

Implements the observe → think → act → evaluate loop using LangGraph StateGraph.
This replaces the old sequential 3-step pipeline with an agentic system that can
dynamically plan, execute tools, and self-correct.

Reference: revisi.md Section 5 — Arsitektur Agent
"""

from typing import Any, Dict, List, Optional, Literal, TypedDict, Annotated
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import operator

from loguru import logger

# ---------- LangGraph imports (with graceful fallback) ----------
try:
    from langgraph.graph import StateGraph, END
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    logger.warning("langgraph not installed — falling back to sequential mode")


# ────────────────────────────────────────────────────────────────
#  State definitions
# ────────────────────────────────────────────────────────────────

class AgentPhase(str, Enum):
    """Current phase in the observe→think→act→evaluate loop."""
    OBSERVE = "observe"
    THINK = "think"
    ACT = "act"
    EVALUATE = "evaluate"
    COMPLETE = "complete"
    ERROR = "error"


class AgentState(TypedDict, total=False):
    """State carried through the LangGraph execution."""
    # Input
    query: str
    context: Dict[str, Any]
    
    # Tracking
    phase: str
    iteration: int
    max_iterations: int
    reasoning_trace: Annotated[List[Dict[str, Any]], operator.add]
    
    # Intermediate results
    retrieved_papers: List[Dict[str, Any]]
    fact_table_stats: Dict[str, Any]
    analysis_result: Dict[str, Any]
    gap_indicators: List[Dict[str, Any]]
    rule_engine_report: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    self_critique: Dict[str, Any]
    
    # Control
    needs_revision: bool
    current_tool: str
    tool_results: Dict[str, Any]
    
    # Output
    final_result: Dict[str, Any]
    error: Optional[str]


@dataclass
class AgentResponse:
    """Response from the coordinator."""
    success: bool
    result: Any
    reasoning_trace: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


# ────────────────────────────────────────────────────────────────
#  Coordinator Agent
# ────────────────────────────────────────────────────────────────

class CoordinatorAgent:
    """
    LangGraph-based Coordinator that orchestrates the agentic system.
    
    Architecture:
        observe  → Retrieve papers, extract facts, build KG
        think    → Detect gaps, classify relations
        act      → Validate with Rule Engine, generate recommendations
        evaluate → Self-critique; loop back to think if quality < threshold
        
    Falls back to a simple sequential pipeline when langgraph is unavailable.
    """
    
    def __init__(
        self,
        research_analyzer=None,
        gap_detector=None,
        recommender=None,
        # New components
        rag_tool=None,
        paper_analyzer_tool=None,
        nli_checker_tool=None,
        kg_querier_tool=None,
        self_critic_tool=None,
        fact_extractor=None,
        fact_table=None,
        rule_engine=None,
        relation_classifier=None,
        graph_builder=None,
        llm_interface=None,
        max_iterations: int = 3,
    ):
        # Legacy components (kept for backward compat)
        self.research_analyzer = research_analyzer
        self.gap_detector = gap_detector
        self.recommender = recommender
        
        # New agentic tools
        self.rag_tool = rag_tool
        self.paper_analyzer_tool = paper_analyzer_tool
        self.nli_checker_tool = nli_checker_tool
        self.kg_querier_tool = kg_querier_tool
        self.self_critic_tool = self_critic_tool
        
        # Core components
        self.fact_extractor = fact_extractor
        self.fact_table = fact_table
        self.rule_engine = rule_engine
        self.relation_classifier = relation_classifier
        self.graph_builder = graph_builder
        self.llm = llm_interface
        
        self.max_iterations = max_iterations
        self.task_history: List[AgentResponse] = []
        
        # Build LangGraph if available
        self._graph = None
        if HAS_LANGGRAPH:
            self._graph = self._build_graph()
        
        logger.info(
            f"CoordinatorAgent initialized "
            f"(langgraph={'enabled' if HAS_LANGGRAPH else 'fallback'})"
        )
    
    # ── Graph construction ──────────────────────────────────────
    
    def _build_graph(self) -> "StateGraph":
        """Build the LangGraph StateGraph."""
        graph = StateGraph(AgentState)
        
        # Add nodes
        graph.add_node("observe", self._node_observe)
        graph.add_node("think", self._node_think)
        graph.add_node("act", self._node_act)
        graph.add_node("evaluate", self._node_evaluate)
        
        # Set entry point
        graph.set_entry_point("observe")
        
        # Add edges
        graph.add_edge("observe", "think")
        graph.add_edge("think", "act")
        graph.add_edge("act", "evaluate")
        
        # Conditional edge: evaluate → think (revise) or END
        graph.add_conditional_edges(
            "evaluate",
            self._should_continue,
            {
                "revise": "think",
                "complete": END,
            },
        )
        
        return graph.compile()
    
    # ── Node implementations ────────────────────────────────────
    
    def _node_observe(self, state: AgentState) -> Dict[str, Any]:
        """
        OBSERVE: Retrieve papers, extract facts, build knowledge graph.
        """
        query = state["query"]
        context = state.get("context", {})
        trace_entry = {
            "phase": "observe",
            "timestamp": datetime.now().isoformat(),
            "actions": [],
        }
        
        retrieved_papers = []
        fact_stats = {}
        
        # 1. RAG retrieval
        if self.rag_tool:
            try:
                rag_result = self.rag_tool.run(query, top_k=10)
                retrieved_papers = rag_result.get("results", [])
                trace_entry["actions"].append(
                    f"RAG retrieved {len(retrieved_papers)} papers"
                )
            except Exception as e:
                logger.error(f"RAG retrieval failed: {e}")
                trace_entry["actions"].append(f"RAG failed: {e}")
        
        # 2. Fact extraction
        if self.fact_extractor and self.fact_table and retrieved_papers:
            try:
                seen_signatures = set()
                to_extract = []
                for paper in retrieved_papers[:5]:  # Limit for performance
                    content = paper.get("content", "")
                    paper_id = paper.get("doc_id", paper.get("id", "unknown"))
                    if not content:
                        continue
                    # PERF: skip identical chunks (RAG often returns near-duplicate
                    # passages from the same source) — re-extracting them is wasted
                    # LLM work that yields no new facts.
                    signature = (paper_id, content[:200])
                    if signature in seen_signatures:
                        continue
                    seen_signatures.add(signature)
                    to_extract.append((paper_id, content))

                # Extract concurrently — LLM calls dominate; FactTable is lock-safe.
                if len(to_extract) > 1:
                    from concurrent.futures import ThreadPoolExecutor
                    import os as _os
                    workers = max(1, min(len(to_extract), int(_os.getenv("OLLAMA_NUM_PARALLEL", "4"))))
                    with ThreadPoolExecutor(max_workers=workers) as _pool:
                        _futs = [
                            _pool.submit(
                                self.fact_extractor.extract_from_text,
                                content, pid, self.fact_table,
                            )
                            for pid, content in to_extract
                        ]
                        for _f in _futs:
                            try:
                                _f.result()
                            except Exception as e:
                                logger.error(f"Fact extraction (parallel) failed: {e}")
                else:
                    for pid, content in to_extract:
                        self.fact_extractor.extract_from_text(content, pid, self.fact_table)

                fact_stats = self.fact_table.get_statistics()
                trace_entry["actions"].append(
                    f"Extracted facts: {fact_stats.get('total_facts', 0)} facts, "
                    f"{fact_stats.get('total_entities', 0)} entities"
                )
            except Exception as e:
                logger.error(f"Fact extraction failed: {e}")
                trace_entry["actions"].append(f"Fact extraction failed: {e}")
        
        # 3. Build/update Knowledge Graph
        if self.graph_builder and self.fact_table:
            try:
                self.graph_builder.build_from_fact_table(self.fact_table)
                trace_entry["actions"].append("Knowledge Graph updated from FactTable")
            except Exception as e:
                logger.error(f"KG build failed: {e}")
        
        # 4. Paper analysis (optional enrichment)
        if self.paper_analyzer_tool and retrieved_papers:
            try:
                for paper in retrieved_papers[:3]:
                    self.paper_analyzer_tool.run(paper)
                trace_entry["actions"].append(
                    f"Analyzed {min(3, len(retrieved_papers))} papers"
                )
            except Exception as e:
                logger.error(f"Paper analysis failed: {e}")
        
        return {
            "retrieved_papers": retrieved_papers,
            "fact_table_stats": fact_stats,
            "phase": AgentPhase.THINK.value,
            "reasoning_trace": [trace_entry],
        }
    
    def _node_think(self, state: AgentState) -> Dict[str, Any]:
        """
        THINK: Detect gaps, classify relations, analyze the literature.
        """
        query = state["query"]
        context = state.get("context", {})
        papers = state.get("retrieved_papers", [])
        iteration = state.get("iteration", 0)
        
        trace_entry = {
            "phase": "think",
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "actions": [],
        }
        
        gap_indicators = []
        analysis_result = {}
        
        # Prepare context for gap detector
        analysis_context = {
            **context,
            "papers": papers,
            "iteration": iteration,
        }
        
        # Previous self-critique feedback (for revision loops)
        if state.get("self_critique"):
            analysis_context["revision_feedback"] = state["self_critique"]
            trace_entry["actions"].append("Incorporating self-critique feedback")
        
        # Run gap detection
        if self.gap_detector:
            try:
                gap_result = self.gap_detector.detect_gaps(query, analysis_context)
                
                if isinstance(gap_result, dict):
                    gap_indicators = gap_result.get("indicators", 
                                      gap_result.get("gap_indicators", []))
                    analysis_result = gap_result
                elif isinstance(gap_result, list):
                    gap_indicators = gap_result
                    analysis_result = {"indicators": gap_result}
                
                trace_entry["actions"].append(
                    f"Detected {len(gap_indicators)} gap indicators"
                )
                
                # Count by type
                type_counts = {}
                for gi in gap_indicators:
                    t = gi.get("type", gi.get("indicator_type", "UNKNOWN"))
                    type_counts[t] = type_counts.get(t, 0) + 1
                trace_entry["actions"].append(f"Gap types: {type_counts}")
                
            except Exception as e:
                logger.error(f"Gap detection failed: {e}")
                trace_entry["actions"].append(f"Gap detection failed: {e}")
        
        # NLI cross-checking on contradictions
        if self.nli_checker_tool and gap_indicators:
            try:
                contradiction_gaps = [
                    g for g in gap_indicators
                    if g.get("type", g.get("indicator_type", "")) == "INCONSISTENCY"
                ]
                for gap in contradiction_gaps[:3]:
                    evidence = gap.get("evidence", [])
                    if len(evidence) >= 2:
                        nli_result = self.nli_checker_tool.run(
                            claim_a=str(evidence[0]),
                            claim_b=str(evidence[1]),
                        )
                        gap["nli_verification"] = nli_result.get("relation_type")
                
                trace_entry["actions"].append(
                    f"NLI verified {len(contradiction_gaps)} contradiction indicators"
                )
            except Exception as e:
                logger.error(f"NLI check failed: {e}")
        
        return {
            "gap_indicators": gap_indicators,
            "analysis_result": analysis_result,
            "phase": AgentPhase.ACT.value,
            "reasoning_trace": [trace_entry],
        }
    
    def _node_act(self, state: AgentState) -> Dict[str, Any]:
        """
        ACT: Validate with Rule Engine, generate recommendations.
        """
        query = state["query"]
        context = state.get("context", {})
        gap_indicators = state.get("gap_indicators", [])
        papers = state.get("retrieved_papers", [])
        
        trace_entry = {
            "phase": "act",
            "timestamp": datetime.now().isoformat(),
            "actions": [],
        }
        
        rule_report = {}
        recommendations = []
        
        # 1. Rule Engine validation on each gap indicator
        if self.rule_engine and gap_indicators:
            try:
                validated_indicators = []
                pass_count = 0
                flag_count = 0
                reject_count = 0
                
                for indicator in gap_indicators:
                    # Build a rich claim dict for the Rule Engine
                    claim = self._enrich_claim_for_validation(indicator)
                    ind_context = {
                        "indicator_type": indicator.get("type", 
                                           indicator.get("indicator_type", "")),
                        "confidence": indicator.get("confidence", 0.0),
                        "evidence": indicator.get("evidence", []),
                    }
                    
                    report = self.rule_engine.validate(claim, ind_context)
                    
                    verdict = str(report.overall_verdict)
                    
                    indicator["rule_engine_verdict"] = verdict
                    indicator["adjusted_confidence"] = report.adjusted_confidence
                    indicator["requires_human_validation"] = verdict != "PASS"
                    
                    if verdict == "PASS":
                        pass_count += 1
                    elif verdict == "FLAG":
                        flag_count += 1
                    else:
                        reject_count += 1
                    
                    # Keep non-rejected indicators
                    if verdict != "REJECT":
                        validated_indicators.append(indicator)
                
                rule_report = {
                    "total": len(gap_indicators),
                    "passed": pass_count,
                    "flagged": flag_count,
                    "rejected": reject_count,
                }
                
                gap_indicators = validated_indicators
                trace_entry["actions"].append(
                    f"Rule Engine: {pass_count} pass, {flag_count} flag, "
                    f"{reject_count} reject"
                )
            except Exception as e:
                logger.error(f"Rule Engine validation failed: {e}")
                trace_entry["actions"].append(f"Rule validation failed: {e}")
        
        # 2. Generate recommendations
        if self.recommender:
            try:
                rec_context = {
                    **context,
                    "gaps": gap_indicators,
                    "papers": papers,
                }
                rec_result = self.recommender.recommend(query, rec_context)
                
                if isinstance(rec_result, list):
                    recommendations = rec_result
                elif isinstance(rec_result, dict):
                    recommendations = rec_result.get(
                        "recommendations", rec_result.get("papers", [])
                    )
                
                trace_entry["actions"].append(
                    f"Generated {len(recommendations)} recommendations"
                )
            except Exception as e:
                logger.error(f"Recommendation failed: {e}")
                trace_entry["actions"].append(f"Recommendation failed: {e}")
        
        return {
            "gap_indicators": gap_indicators,
            "rule_engine_report": rule_report,
            "recommendations": recommendations,
            "phase": AgentPhase.EVALUATE.value,
            "reasoning_trace": [trace_entry],
        }
    
    def _node_evaluate(self, state: AgentState) -> Dict[str, Any]:
        """
        EVALUATE: Self-critique the results and decide if revision is needed.
        """
        iteration = state.get("iteration", 0) + 1
        gap_indicators = state.get("gap_indicators", [])
        
        trace_entry = {
            "phase": "evaluate",
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "actions": [],
        }
        
        self_critique = {}
        needs_revision = False
        
        # Self-critic evaluation
        if self.self_critic_tool:
            try:
                analysis_for_eval = {
                    "indicators": gap_indicators,
                    "recommendations": state.get("recommendations", []),
                    "fact_stats": state.get("fact_table_stats", {}),
                }
                
                self_critique = self.self_critic_tool.run(
                    analysis_result=analysis_for_eval,
                    original_query=state["query"],
                )
                
                overall_score = self_critique.get("overall_score", 0.0)
                needs_revision = self_critique.get("requires_revision", False)
                
                trace_entry["actions"].append(
                    f"Self-critique score: {overall_score:.2f}, "
                    f"revision needed: {needs_revision}"
                )
                
                if self_critique.get("suggestions"):
                    trace_entry["actions"].append(
                        f"Suggestions: {self_critique['suggestions'][:3]}"
                    )
            except Exception as e:
                logger.error(f"Self-critique failed: {e}")
                trace_entry["actions"].append(f"Self-critique failed: {e}")
        
        # Don't revise beyond max_iterations
        if iteration >= state.get("max_iterations", self.max_iterations):
            needs_revision = False
            trace_entry["actions"].append(
                f"Max iterations ({self.max_iterations}) reached, finalizing"
            )
        
        # Build final result
        final_result = {
            "query": state["query"],
            "analysis": state.get("analysis_result", {}),
            "gap_indicators": gap_indicators,
            "recommendations": state.get("recommendations", []),
            "rule_engine_report": state.get("rule_engine_report", {}),
            "fact_table_stats": state.get("fact_table_stats", {}),
            "self_critique": self_critique,
            "metadata": {
                "iterations": iteration,
                "total_papers_retrieved": len(state.get("retrieved_papers", [])),
                "total_indicators": len(gap_indicators),
                "total_recommendations": len(state.get("recommendations", [])),
            },
        }
        
        return {
            "iteration": iteration,
            "self_critique": self_critique,
            "needs_revision": needs_revision,
            "final_result": final_result,
            "phase": AgentPhase.COMPLETE.value if not needs_revision else AgentPhase.THINK.value,
            "reasoning_trace": [trace_entry],
        }
    
    # ── Routing ─────────────────────────────────────────────────
    
    def _enrich_claim_for_validation(self, indicator: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a gap indicator with method/domain/findings from FactTable
        so the Rule Engine can actually validate it.
        """
        claim = {
            "type": "gap_indicator",
            "description": indicator.get("description", indicator.get("title", "")),
            "confidence": indicator.get("confidence", 0.5),
            "evidence": indicator.get("evidence", []),
            "method": indicator.get("method"),
            "domain": indicator.get("domain"),
            "findings": indicator.get("findings", []),
        }
        
        # Try to extract method/domain from FactTable if not already present
        if self.fact_table and (not claim["method"] or not claim["domain"]):
            from ..knowledge.fact_table import EntityType
            
            desc_lower = claim["description"].lower()
            
            # Find METHOD entities mentioned in the description
            if not claim["method"]:
                for entity in self.fact_table.find_entities(entity_type=EntityType.METHOD):
                    if entity.name.lower() in desc_lower:
                        claim["method"] = entity.entity_id
                        break
            
            # Find DOMAIN entities mentioned in the description
            if not claim["domain"]:
                for entity in self.fact_table.find_entities(entity_type=EntityType.DOMAIN):
                    if entity.name.lower() in desc_lower:
                        claim["domain"] = entity.entity_id
                        break
            
            # Find FINDING entities mentioned in the description
            if not claim["findings"]:
                findings = []
                for entity in self.fact_table.find_entities(entity_type=EntityType.FINDING):
                    if entity.name.lower() in desc_lower:
                        findings.append(entity.entity_id)
                claim["findings"] = findings[:5]
        
        return claim
    
    def _should_continue(self, state: AgentState) -> Literal["revise", "complete"]:
        """Decide whether to loop back for revision or finish."""
        if state.get("needs_revision", False):
            return "revise"
        return "complete"
    
    # ── Public API ──────────────────────────────────────────────
    
    def process_research_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a research query through the agentic pipeline.
        
        If LangGraph is available → runs the StateGraph.
        Otherwise → falls back to sequential pipeline.
        """
        logger.info(f"Processing research query: '{query[:80]}...'")
        context = context or {}
        
        if self._graph and HAS_LANGGRAPH:
            return self._run_langgraph(query, context)
        else:
            return self._run_sequential(query, context)
    
    def _run_langgraph(
        self, query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute via LangGraph StateGraph."""
        initial_state: AgentState = {
            "query": query,
            "context": context,
            "phase": AgentPhase.OBSERVE.value,
            "iteration": 0,
            "max_iterations": self.max_iterations,
            "reasoning_trace": [],
            "retrieved_papers": [],
            "fact_table_stats": {},
            "analysis_result": {},
            "gap_indicators": [],
            "rule_engine_report": {},
            "recommendations": [],
            "self_critique": {},
            "needs_revision": False,
            "current_tool": "",
            "tool_results": {},
            "final_result": {},
            "error": None,
        }
        
        try:
            final_state = self._graph.invoke(initial_state)
            
            result = final_state.get("final_result", {})
            result["reasoning_trace"] = final_state.get("reasoning_trace", [])
            result["execution_mode"] = "langgraph"
            
            # Record in history
            self.task_history.append(AgentResponse(
                success=True,
                result=result,
                reasoning_trace=result.get("reasoning_trace", []),
                metadata=result.get("metadata", {}),
            ))
            
            logger.info(
                f"LangGraph execution complete — "
                f"{result.get('metadata', {}).get('iterations', '?')} iterations, "
                f"{result.get('metadata', {}).get('total_indicators', 0)} indicators"  # noqa: E501
            )
            return result
            
        except Exception as e:
            logger.error(f"LangGraph execution failed: {e}")
            self.task_history.append(AgentResponse(
                success=False,
                result=None,
                error=str(e),
            ))
            # Fallback to sequential
            logger.info("Falling back to sequential pipeline")
            return self._run_sequential(query, context)
    
    def _run_sequential(
        self, query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Legacy sequential pipeline (fallback)."""
        results = {
            "query": query,
            "analysis": None,
            "gaps": None,
            "gap_indicators": [],
            "recommendations": None,
            "reasoning_trace": [],
            "execution_mode": "sequential",
            "metadata": {},
        }
        
        # Step 1: Analyze
        if self.research_analyzer:
            logger.info("Sequential Step 1: Analyzing research domain")
            try:
                results["analysis"] = self.research_analyzer.analyze(query, context)
                context["analysis"] = results["analysis"]
                results["reasoning_trace"].append({
                    "phase": "analyze",
                    "status": "success",
                })
            except Exception as e:
                logger.warning(f"Analysis failed: {e}")
                results["reasoning_trace"].append({
                    "phase": "analyze",
                    "status": "failed",
                    "error": str(e),
                })
        
        # Step 2: Detect gaps
        if self.gap_detector:
            logger.info("Sequential Step 2: Detecting gaps")
            try:
                gap_result = self.gap_detector.detect_gaps(query, context)
                if isinstance(gap_result, dict):
                    results["gaps"] = gap_result
                    results["gap_indicators"] = gap_result.get(
                        "indicators", gap_result.get("gap_indicators", [])
                    )
                else:
                    results["gaps"] = gap_result
                context["gaps"] = results["gaps"]
                results["reasoning_trace"].append({
                    "phase": "detect_gaps",
                    "status": "success",
                })
            except Exception as e:
                logger.warning(f"Gap detection failed: {e}")
                results["reasoning_trace"].append({
                    "phase": "detect_gaps",
                    "status": "failed",
                    "error": str(e),
                })
        
        # Step 3: Recommend
        if self.recommender:
            logger.info("Sequential Step 3: Generating recommendations")
            try:
                results["recommendations"] = self.recommender.recommend(
                    query, context
                )
                results["reasoning_trace"].append({
                    "phase": "recommend",
                    "status": "success",
                })
            except Exception as e:
                logger.warning(f"Recommendation failed: {e}")
                results["reasoning_trace"].append({
                    "phase": "recommend",
                    "status": "failed",
                    "error": str(e),
                })
        
        results["metadata"] = {
            "task_count": 3,
            "successful_tasks": sum(
                1 for t in results["reasoning_trace"] if t.get("status") == "success"
            ),
            "failed_tasks": sum(
                1 for t in results["reasoning_trace"] if t.get("status") == "failed"
            ),
        }
        
        self.task_history.append(AgentResponse(
            success=True,
            result=results,
            reasoning_trace=results["reasoning_trace"],
            metadata=results["metadata"],
        ))
        
        return results
    
    # ── Utility ─────────────────────────────────────────────────
    
    def get_task_history(self) -> List[AgentResponse]:
        """Get history of executed tasks."""
        return self.task_history
    
    def clear_history(self):
        """Clear task history."""
        self.task_history = []
        logger.info("Task history cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get coordinator statistics."""
        return {
            "total_tasks": len(self.task_history),
            "successful_tasks": sum(1 for t in self.task_history if t.success),
            "failed_tasks": sum(1 for t in self.task_history if not t.success),
            "execution_mode": "langgraph" if self._graph else "sequential",
        }


# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    coordinator = CoordinatorAgent()
    print(f"CoordinatorAgent ready (mode: {'langgraph' if HAS_LANGGRAPH else 'sequential'})")

