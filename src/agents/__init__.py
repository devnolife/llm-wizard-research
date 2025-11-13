"""Multi-agent framework for research recommendation"""

from .coordinator import CoordinatorAgent
from .research_analyzer import ResearchAnalyzerAgent
from .gap_detector import GapDetectorAgent
from .recommender import RecommenderAgent

__all__ = [
    "CoordinatorAgent",
    "ResearchAnalyzerAgent",
    "GapDetectorAgent",
    "RecommenderAgent",
]
