"""
Coordinator Agent

Orchestrates the multi-agent system for research recommendation tasks.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from loguru import logger


class AgentTask(Enum):
    """Types of tasks agents can perform"""
    ANALYZE_RESEARCH = "analyze_research"
    DETECT_GAPS = "detect_gaps"
    RECOMMEND_PAPERS = "recommend_papers"
    SUMMARIZE = "summarize"
    EXTRACT_METADATA = "extract_metadata"


@dataclass
class AgentResponse:
    """Response from an agent"""
    task: AgentTask
    success: bool
    result: Any
    metadata: Dict[str, Any]
    error: Optional[str] = None


class CoordinatorAgent:
    """
    Coordinates multiple specialized agents for research recommendation
    
    Responsibilities:
    - Task decomposition and delegation
    - Agent orchestration and workflow management
    - Result aggregation and synthesis
    - Error handling and recovery
    """
    
    def __init__(
        self,
        research_analyzer=None,
        gap_detector=None,
        recommender=None
    ):
        """
        Initialize coordinator agent
        
        Args:
            research_analyzer: ResearchAnalyzerAgent instance
            gap_detector: GapDetectorAgent instance
            recommender: RecommenderAgent instance
        """
        self.research_analyzer = research_analyzer
        self.gap_detector = gap_detector
        self.recommender = recommender
        
        self.task_history: List[AgentResponse] = []
        
        logger.info("CoordinatorAgent initialized")
    
    def process_research_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a research query through the multi-agent pipeline
        
        Workflow:
        1. Analyze the query and retrieve relevant papers
        2. Detect research gaps in the domain
        3. Generate recommendations based on gaps and relevance
        
        Args:
            query: User research query
            context: Additional context (papers, preferences, etc.)
            
        Returns:
            Complete response with recommendations and analysis
        """
        logger.info(f"Processing research query: '{query[:50]}...'")
        
        context = context or {}
        results = {
            "query": query,
            "analysis": None,
            "gaps": None,
            "recommendations": None,
            "metadata": {}
        }
        
        # Step 1: Analyze research domain
        if self.research_analyzer:
            logger.info("Step 1: Analyzing research domain")
            analysis_response = self._execute_task(
                AgentTask.ANALYZE_RESEARCH,
                lambda: self.research_analyzer.analyze(query, context)
            )
            
            if analysis_response.success:
                results["analysis"] = analysis_response.result
                context["analysis"] = analysis_response.result
            else:
                logger.warning(f"Research analysis failed: {analysis_response.error}")
        
        # Step 2: Detect research gaps
        if self.gap_detector:
            logger.info("Step 2: Detecting research gaps")
            gap_response = self._execute_task(
                AgentTask.DETECT_GAPS,
                lambda: self.gap_detector.detect_gaps(query, context)
            )
            
            if gap_response.success:
                results["gaps"] = gap_response.result
                context["gaps"] = gap_response.result
            else:
                logger.warning(f"Gap detection failed: {gap_response.error}")
        
        # Step 3: Generate recommendations
        if self.recommender:
            logger.info("Step 3: Generating recommendations")
            recommend_response = self._execute_task(
                AgentTask.RECOMMEND_PAPERS,
                lambda: self.recommender.recommend(query, context)
            )
            
            if recommend_response.success:
                results["recommendations"] = recommend_response.result
            else:
                logger.warning(f"Recommendation failed: {recommend_response.error}")
        
        # Add metadata
        results["metadata"] = {
            "task_count": len(self.task_history),
            "successful_tasks": sum(1 for t in self.task_history if t.success),
            "failed_tasks": sum(1 for t in self.task_history if not t.success)
        }
        
        logger.info("Research query processing completed")
        return results
    
    def _execute_task(
        self,
        task_type: AgentTask,
        task_func
    ) -> AgentResponse:
        """
        Execute a task with error handling
        
        Args:
            task_type: Type of task
            task_func: Function to execute
            
        Returns:
            AgentResponse object
        """
        try:
            result = task_func()
            response = AgentResponse(
                task=task_type,
                success=True,
                result=result,
                metadata={"task_type": task_type.value}
            )
        except Exception as e:
            logger.error(f"Task {task_type.value} failed: {e}")
            response = AgentResponse(
                task=task_type,
                success=False,
                result=None,
                metadata={"task_type": task_type.value},
                error=str(e)
            )
        
        self.task_history.append(response)
        return response
    
    def get_task_history(self) -> List[AgentResponse]:
        """Get history of executed tasks"""
        return self.task_history
    
    def clear_history(self):
        """Clear task history"""
        self.task_history = []
        logger.info("Task history cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get coordinator statistics"""
        return {
            "total_tasks": len(self.task_history),
            "successful_tasks": sum(1 for t in self.task_history if t.success),
            "failed_tasks": sum(1 for t in self.task_history if not t.success),
            "tasks_by_type": self._count_tasks_by_type()
        }
    
    def _count_tasks_by_type(self) -> Dict[str, int]:
        """Count tasks by type"""
        counts = {}
        for task in self.task_history:
            task_name = task.task.value
            counts[task_name] = counts.get(task_name, 0) + 1
        return counts


# Example usage
if __name__ == "__main__":
    coordinator = CoordinatorAgent()
    print("CoordinatorAgent ready")
