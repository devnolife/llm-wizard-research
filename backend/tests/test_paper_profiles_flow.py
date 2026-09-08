"""The per-journal side-channel must survive the coordinator's THINK node.

``auto_analysis`` puts ``paper_profiles`` into the coordinator context; the
GapDetector must hand it to ``GapAnalyzer.analyze_gaps`` unchanged, otherwise
author-stated weaknesses silently never corroborate any indicator.
"""

from app.core.agents.coordinator import CoordinatorAgent
from app.core.agents.gap_detector import GapDetectorAgent


class _RecordingAnalyzer:
    def __init__(self):
        self.calls = []

    def analyze_gaps(self, topic, papers, depth="standard", paper_profiles=None):
        self.calls.append({"topic": topic, "papers": papers, "paper_profiles": paper_profiles})
        return []


PROFILES = {"a.pdf": {"source": "a.pdf", "title": "A", "weaknesses": {"tersurat": [], "tersirat": []},
                      "author_gaps": [], "workflow": None, "references": []}}


def test_gap_detector_forwards_profiles_from_context():
    analyzer = _RecordingAnalyzer()
    agent = GapDetectorAgent(gap_analyzer=analyzer)

    agent.detect_gaps("topik", {"papers": [{"source": "a.pdf", "content": "x"}],
                                "paper_profiles": PROFILES})

    assert analyzer.calls[0]["paper_profiles"] == PROFILES


def test_gap_detector_without_profiles_passes_none():
    analyzer = _RecordingAnalyzer()
    GapDetectorAgent(gap_analyzer=analyzer).detect_gaps(
        "topik", {"papers": [{"source": "a.pdf", "content": "x"}]})

    assert analyzer.calls[0]["paper_profiles"] is None


def test_think_node_keeps_profiles_in_analysis_context():
    analyzer = _RecordingAnalyzer()
    detector = GapDetectorAgent(gap_analyzer=analyzer)
    agent = CoordinatorAgent(gap_detector=detector)

    agent._node_think({
        "query": "topik",
        "context": {"paper_profiles": PROFILES, "topics": ["topik"]},
        "retrieved_papers": [{"source": "a.pdf", "content": "passage"}],
        "iteration": 0,
    })

    assert analyzer.calls[0]["paper_profiles"] == PROFILES
    assert analyzer.calls[0]["papers"] == [{"source": "a.pdf", "content": "passage"}]
