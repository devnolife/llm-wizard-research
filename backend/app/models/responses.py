"""
Response models for API endpoints

Includes Pydantic models for gap indicators, rule engine validation,
fact triples, and the full analysis response.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum


# ── Existing models ─────────────────────────────────────────────

class IngestResponse(BaseModel):
    success: bool
    doc_id: str
    message: str
    chunks_created: int


class HealthResponse(BaseModel):
    status: str
    components: Dict[str, bool]
    version: str


class PaperSearchResponse(BaseModel):
    query: str
    total_results: int
    papers: List[Dict[str, Any]]
    sources_searched: List[str]
    embedding_model: Optional[str] = None


# ── New models (revisi.md) ──────────────────────────────────────

class IndicatorType(str, Enum):
    """Types of synthesis gap indicators (Cooper 1998 / Booth 2012)."""
    FRAGMENTATION = "FRAGMENTATION"
    INCONSISTENCY = "INCONSISTENCY"
    INCOMPLETENESS = "INCOMPLETENESS"


class RuleVerdictType(str, Enum):
    """Rule Engine verdict types."""
    PASS = "PASS"
    FLAG = "FLAG"
    REJECT = "REJECT"


class FactTripleModel(BaseModel):
    """A Subject-Predicate-Object fact triple from the Knowledge Graph."""
    subject: str = Field(..., description="Subject entity name/ID")
    predicate: str = Field(..., description="Relation type (e.g., USES, IMPROVES)")
    object: str = Field(..., description="Object entity name/ID")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Extraction confidence")
    source: Optional[str] = Field(None, description="Source paper ID")
    is_inferred: bool = Field(False, description="Whether this fact was inferred by a rule")


class RuleResultModel(BaseModel):
    """Result of a single Rule Engine rule."""
    rule_id: str = Field(..., description="Rule identifier (e.g., F1, C2, K3)")
    rule_name: str = Field("", description="Human-readable rule name")
    category: str = Field("", description="FEASIBILITY / CAUSALITY / CONSISTENCY")
    verdict: RuleVerdictType
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    explanation: str = ""


class RuleEngineReportModel(BaseModel):
    """Aggregated Rule Engine validation report."""
    overall_verdict: RuleVerdictType = RuleVerdictType.PASS
    adjusted_confidence: float = Field(0.0, ge=0.0, le=1.0)
    total_rules: int = 0
    passed: int = 0
    flagged: int = 0
    rejected: int = 0
    rules: List[RuleResultModel] = Field(default_factory=list)
    summary: str = ""


class GapIndicatorModel(BaseModel):
    """A synthesis gap indicator detected in the literature."""
    indicator_type: IndicatorType
    title: str = ""
    description: str = ""
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    adjusted_confidence: Optional[float] = None
    rule_engine_verdict: Optional[RuleVerdictType] = None
    requires_human_validation: bool = True
    evidence: List[str] = Field(default_factory=list)
    supporting_quotes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Verbatim quotes from source chunks grounding this indicator: "
                    "[{quote, source_paper, match_score}]",
    )
    evidence_subgraph: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="KG edges evidencing the inter-paper relation: "
                    "[{from, from_name, to, to_name, predicate, source_paper}]",
    )
    supporting_papers: List[str] = Field(default_factory=list)
    suggested_directions: List[str] = Field(default_factory=list)


class ReasoningStep(BaseModel):
    """A single step in the agent's reasoning trace."""
    phase: str = Field(..., description="observe / think / act / evaluate")
    timestamp: Optional[str] = None
    iteration: Optional[int] = None
    actions: List[str] = Field(default_factory=list)
    status: Optional[str] = None
    error: Optional[str] = None


class SelfCritiqueModel(BaseModel):
    """Agent self-evaluation results."""
    overall_score: float = Field(0.0, ge=0.0, le=1.0)
    dimensions: Dict[str, Any] = Field(default_factory=dict)
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    requires_revision: bool = False


class FactTableStatsModel(BaseModel):
    """Statistics from the FactTable / Knowledge Graph."""
    total_entities: int = 0
    total_facts: int = 0
    entity_types: Dict[str, int] = Field(default_factory=dict)
    predicate_types: Dict[str, int] = Field(default_factory=dict)
    papers_indexed: int = 0


class AnalysisResponseModel(BaseModel):
    """Full analysis response from the agentic pipeline."""
    query: str
    execution_mode: str = Field("sequential", description="langgraph or sequential")
    
    # Gap analysis
    gap_indicators: List[GapIndicatorModel] = Field(default_factory=list)
    total_indicators: int = 0
    
    # Rule Engine
    rule_engine_report: Optional[RuleEngineReportModel] = None
    
    # Fact Table / KG
    fact_table_stats: Optional[FactTableStatsModel] = None
    
    # Recommendations
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Agent trace
    reasoning_trace: List[ReasoningStep] = Field(default_factory=list)
    self_critique: Optional[SelfCritiqueModel] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    analysis: Optional[Dict[str, Any]] = None

