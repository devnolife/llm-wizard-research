"""
Agent Tools - Tools for the LangGraph-based Agentic System

Each tool is a callable function that the Agent Orchestrator can invoke
during its observe→think→act→evaluate loop.

Reference: revisi.md Section 5 - Arsitektur Agent
"""

from .rag_tool import RAGTool
from .paper_analyzer_tool import PaperAnalyzerTool
from .nli_checker_tool import NLICheckerTool
from .kg_querier_tool import KGQuerierTool
from .self_critic_tool import SelfCriticTool

__all__ = [
    "RAGTool",
    "PaperAnalyzerTool",
    "NLICheckerTool",
    "KGQuerierTool",
    "SelfCriticTool",
]
