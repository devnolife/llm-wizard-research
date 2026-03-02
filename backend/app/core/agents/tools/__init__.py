"""
Agent Tools - Tools for the LangGraph-based Agentic System

Each tool is a callable function that the Agent Orchestrator can invoke
during its observe→think→act→evaluate loop.

Reference: revisi.md Section 5 - Arsitektur Agent
"""

from backend.app.core.agents.tools.rag_tool import RAGTool
from backend.app.core.agents.tools.paper_analyzer_tool import PaperAnalyzerTool
from backend.app.core.agents.tools.nli_checker_tool import NLICheckerTool
from backend.app.core.agents.tools.kg_querier_tool import KGQuerierTool
from backend.app.core.agents.tools.self_critic_tool import SelfCriticTool

__all__ = [
    "RAGTool",
    "PaperAnalyzerTool",
    "NLICheckerTool",
    "KGQuerierTool",
    "SelfCriticTool",
]
