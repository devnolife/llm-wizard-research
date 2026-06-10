"""
KG Querier Tool - Knowledge Graph query interface for the Agent.

Provides structured access to the Knowledge Graph: query facts,
find entity neighborhoods, discover paths, and get statistics.
"""

from typing import Any, Dict, List, Optional
from loguru import logger


class KGQuerierTool:
    """Tool for querying the Knowledge Graph."""
    
    name = "kg_querier"
    description = (
        "Query the Knowledge Graph to find relationships between entities, "
        "explore entity neighborhoods, discover paths between concepts, "
        "and retrieve SPO (Subject-Predicate-Object) fact triples. "
        "Use this to understand connections in the research literature."
    )
    
    def __init__(self, graph_builder=None, fact_table=None):
        self.graph_builder = graph_builder
        self.fact_table = fact_table
    
    def run(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a KG query action.
        
        Args:
            action: One of 'query_facts', 'neighborhood', 'find_paths',
                    'statistics', 'contradictions'
            **kwargs: Action-specific parameters
            
        Returns:
            Query results
        """
        actions = {
            "query_facts": self._query_facts,
            "neighborhood": self._neighborhood,
            "find_paths": self._find_paths,
            "statistics": self._statistics,
            "contradictions": self._contradictions,
            "entities": self._list_entities,
        }
        
        handler = actions.get(action)
        if not handler:
            return {
                "error": f"Unknown action: {action}",
                "available_actions": list(actions.keys()),
            }
        
        try:
            return handler(**kwargs)
        except Exception as e:
            logger.error(f"KG query '{action}' failed: {e}")
            return {"error": str(e), "action": action}
    
    def _query_facts(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        obj: Optional[str] = None,
        **_,
    ) -> Dict[str, Any]:
        """Query SPO triples from the fact table."""
        facts = []
        
        # Try graph_builder first (it delegates to fact_table)
        if self.graph_builder:
            raw = self.graph_builder.query_facts(
                subject_id=subject, predicate=predicate, object_id=obj
            )
            facts = raw if isinstance(raw, list) else []
        elif self.fact_table:
            from ...knowledge.fact_table import Fact
            raw = self.fact_table.query(
                subject_id=subject, predicate=predicate, object_id=obj
            )
            facts = [
                {
                    "subject": f.subject_id,
                    "predicate": f.predicate.value if hasattr(f.predicate, 'value') else str(f.predicate),
                    "object": f.object_id,
                    "confidence": f.confidence,
                    "source": f.source,
                }
                for f in raw
            ]
        
        return {
            "action": "query_facts",
            "filters": {"subject": subject, "predicate": predicate, "object": obj},
            "total": len(facts),
            "facts": facts[:50],  # Limit to prevent token overflow
        }
    
    def _neighborhood(
        self, entity_id: str, max_depth: int = 2, **_
    ) -> Dict[str, Any]:
        """Get entity neighborhood from KG."""
        if self.graph_builder:
            neighborhood = self.graph_builder.get_entity_neighborhood(
                entity_id, max_depth=max_depth
            )
            return {
                "action": "neighborhood",
                "entity_id": entity_id,
                "max_depth": max_depth,
                "result": neighborhood,
            }
        return {"action": "neighborhood", "error": "Graph builder not available"}
    
    def _find_paths(
        self, source: str, target: str, max_paths: int = 3, **_
    ) -> Dict[str, Any]:
        """Find paths between two entities."""
        if self.graph_builder:
            paths = self.graph_builder.find_paths_between_entities(
                source, target, max_paths=max_paths
            )
            return {
                "action": "find_paths",
                "source": source,
                "target": target,
                "paths": paths,
                "total_paths": len(paths),
            }
        return {"action": "find_paths", "error": "Graph builder not available"}
    
    def _statistics(self, **_) -> Dict[str, Any]:
        """Get KG statistics."""
        stats = {}
        
        if self.fact_table:
            stats["fact_table"] = self.fact_table.get_statistics()
        
        if self.graph_builder and self.graph_builder.graph:
            g = self.graph_builder.graph
            stats["graph"] = {
                "nodes": g.number_of_nodes(),
                "edges": g.number_of_edges(),
            }
        
        return {"action": "statistics", "stats": stats}
    
    def _contradictions(self, **_) -> Dict[str, Any]:
        """Find contradictions in the fact table."""
        if self.fact_table:
            contradictions = self.fact_table.find_contradictions()
            return {
                "action": "contradictions",
                "total": len(contradictions),
                "contradictions": contradictions[:20],
            }
        return {"action": "contradictions", "error": "Fact table not available"}
    
    def _list_entities(
        self, entity_type: Optional[str] = None, limit: int = 50, **_
    ) -> Dict[str, Any]:
        """List entities from the fact table."""
        if not self.fact_table:
            return {"action": "entities", "error": "Fact table not available"}
        
        if entity_type:
            from ...knowledge.fact_table import EntityType
            try:
                et = EntityType(entity_type)
                entities = self.fact_table.find_entities(entity_type=et)
            except ValueError:
                entities = list(self.fact_table._entities.values())
        else:
            entities = list(self.fact_table._entities.values())
        
        return {
            "action": "entities",
            "filter": entity_type,
            "total": len(entities),
            "entities": [
                {
                    "id": e.entity_id,
                    "type": e.entity_type.value if hasattr(e.entity_type, 'value') else str(e.entity_type),
                    "name": e.name,
                    "source_paper": e.source_paper,
                }
                for e in entities[:limit]
            ],
        }
