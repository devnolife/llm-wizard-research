"""
Knowledge Graph Builder for Research Papers

Builds and manages knowledge graphs of research papers, citations, and relationships.
Now integrated with FactTable (SPO triples) for structured fact-based reasoning.

References:
    - Ji, S., et al. (2021). A Survey on Knowledge Graphs
    - revisi.md Section 9: Skema Fakta Knowledge Graph (Tabel SPO)
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import networkx as nx
from collections import defaultdict

from loguru import logger

# Import FactTable types for integration
try:
    from ..knowledge.fact_table import FactTable, Entity, Fact, EntityType, PredicateType
except ImportError:
    FactTable = None
    Entity = None
    Fact = None
    EntityType = None
    PredicateType = None


@dataclass
class PaperNode:
    """Represents a paper node in the knowledge graph"""
    paper_id: str
    title: str
    year: Optional[int]
    authors: List[str]
    keywords: List[str]
    metadata: Dict[str, Any]


@dataclass
class CitationEdge:
    """Represents a citation relationship"""
    source_id: str
    target_id: str
    weight: float = 1.0


class KnowledgeGraphBuilder:
    """
    Builds and manages knowledge graphs of research papers.
    
    Now supports two modes:
    1. Legacy: Paper-citation graph (PaperNode + CitationEdge)
    2. SPO-based: Built from FactTable triples (Entity nodes + Predicate edges)
    
    Features:
    - Paper relationship modeling
    - SPO triple graph construction (from FactTable)
    - Fact querying for Rule Engine
    - Citation network analysis
    - Topic clustering
    - Influence propagation
    - Community detection
    
    Uses NetworkX for MVP (can be extended to Neo4j)
    """
    
    def __init__(self, use_neo4j: bool = False, neo4j_config: Optional[Dict] = None):
        """
        Initialize knowledge graph builder
        
        Args:
            use_neo4j: Whether to use Neo4j (otherwise uses NetworkX)
            neo4j_config: Neo4j connection configuration
        """
        self.use_neo4j = use_neo4j
        self.graph = nx.DiGraph()  # Directed graph for citations
        self._fact_table: Optional[FactTable] = None  # Reference to FactTable
        
        if use_neo4j and neo4j_config:
            self._init_neo4j(neo4j_config)
        
        logger.info(f"KnowledgeGraphBuilder initialized (backend: {'Neo4j' if use_neo4j else 'NetworkX'})")
    
    def _init_neo4j(self, config: Dict):
        """Initialize Neo4j connection"""
        try:
            from neo4j import GraphDatabase
            self.neo4j_driver = GraphDatabase.driver(
                config.get("uri", "bolt://localhost:7687"),
                auth=(config.get("user", "neo4j"), config.get("password", ""))
            )
            logger.info("Connected to Neo4j")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.use_neo4j = False
    
    def add_paper(self, paper: PaperNode) -> bool:
        """
        Add a paper to the knowledge graph
        
        Args:
            paper: PaperNode object
            
        Returns:
            True if successful
        """
        try:
            self.graph.add_node(
                paper.paper_id,
                title=paper.title,
                year=paper.year,
                authors=paper.authors,
                keywords=paper.keywords,
                metadata=paper.metadata,
                node_type="paper"
            )
            logger.debug(f"Added paper node: {paper.paper_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add paper: {e}")
            return False
    
    def add_citation(self, citation: CitationEdge) -> bool:
        """
        Add a citation relationship
        
        Args:
            citation: CitationEdge object
            
        Returns:
            True if successful
        """
        try:
            self.graph.add_edge(
                citation.source_id,
                citation.target_id,
                weight=citation.weight,
                edge_type="cites"
            )
            logger.debug(f"Added citation: {citation.source_id} -> {citation.target_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add citation: {e}")
            return False
    
    def build_from_documents(self, documents: List[Dict[str, Any]]):
        """
        Build knowledge graph from document list
        
        Args:
            documents: List of document dictionaries
        """
        logger.info(f"Building knowledge graph from {len(documents)} documents")
        
        # Add all papers
        for doc in documents:
            metadata = doc.get("metadata", {})
            paper = PaperNode(
                paper_id=doc.get("doc_id", doc.get("id")),
                title=metadata.get("title", "Unknown"),
                year=metadata.get("year"),
                authors=metadata.get("authors", []),
                keywords=metadata.get("keywords", []),
                metadata=metadata
            )
            self.add_paper(paper)
        
        # Citation extraction is intentionally deferred until a structured
        # parser is introduced; paper nodes are still available for analysis.
        
        logger.info(f"Knowledge graph built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
    
    def get_paper_neighbors(
        self,
        paper_id: str,
        max_neighbors: int = 10
    ) -> List[Tuple[str, Dict]]:
        """
        Get neighboring papers (cited and citing)
        
        Args:
            paper_id: Paper ID
            max_neighbors: Maximum neighbors to return
            
        Returns:
            List of (neighbor_id, data) tuples
        """
        neighbors = []
        
        if paper_id not in self.graph:
            return neighbors
        
        # Get predecessors (papers that cite this one)
        for pred in self.graph.predecessors(paper_id):
            neighbors.append((pred, self.graph.nodes[pred]))
        
        # Get successors (papers cited by this one)
        for succ in self.graph.successors(paper_id):
            neighbors.append((succ, self.graph.nodes[succ]))
        
        return neighbors[:max_neighbors]
    
    def find_influential_papers(self, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Find most influential papers using PageRank
        
        Args:
            top_k: Number of top papers to return
            
        Returns:
            List of (paper_id, influence_score) tuples
        """
        try:
            pagerank = nx.pagerank(self.graph)
            sorted_papers = sorted(
                pagerank.items(),
                key=lambda x: x[1],
                reverse=True
            )
            return sorted_papers[:top_k]
        except Exception as e:
            logger.error(f"PageRank calculation failed: {e}")
            return []
    
    def find_research_communities(
        self,
        method: str = "louvain"
    ) -> Dict[int, List[str]]:
        """
        Detect research communities/clusters
        
        Args:
            method: Clustering method ('louvain', 'label_propagation')
            
        Returns:
            Dictionary mapping community_id to list of paper_ids
        """
        try:
            # Convert to undirected for community detection
            undirected = self.graph.to_undirected()
            
            if method == "louvain":
                import community as community_louvain
                communities = community_louvain.best_partition(undirected)
            else:
                # Label propagation
                communities_gen = nx.community.label_propagation_communities(undirected)
                communities = {}
                for i, community in enumerate(communities_gen):
                    for node in community:
                        communities[node] = i
            
            # Group by community
            community_groups = defaultdict(list)
            for paper_id, comm_id in communities.items():
                community_groups[comm_id].append(paper_id)
            
            logger.info(f"Found {len(community_groups)} research communities")
            return dict(community_groups)
            
        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            return {}
    
    def find_topic_clusters(self, num_clusters: int = 5) -> Dict[str, int]:
        """
        Cluster papers by topic using keywords
        
        Args:
            num_clusters: Number of clusters
            
        Returns:
            Dictionary mapping paper_id to cluster_id
        """
        # Extract keyword vectors
        paper_keywords = {}
        all_keywords = set()
        
        for node_id, data in self.graph.nodes(data=True):
            keywords = data.get("keywords", [])
            paper_keywords[node_id] = set(keywords)
            all_keywords.update(keywords)
        
        # Simple clustering based on keyword overlap
        # In production, use proper embeddings and clustering
        clusters = {}
        cluster_id = 0
        clustered = set()
        
        for paper_id, keywords in paper_keywords.items():
            if paper_id in clustered:
                continue
            
            # Find similar papers
            cluster = [paper_id]
            for other_id, other_keywords in paper_keywords.items():
                if other_id in clustered or other_id == paper_id:
                    continue
                
                # Calculate Jaccard similarity
                similarity = len(keywords & other_keywords) / len(keywords | other_keywords) if keywords or other_keywords else 0
                
                if similarity > 0.3:  # Threshold
                    cluster.append(other_id)
                    clustered.add(other_id)
            
            # Assign cluster
            for pid in cluster:
                clusters[pid] = cluster_id
                clustered.add(pid)
            
            cluster_id += 1
            
            if cluster_id >= num_clusters:
                break
        
        # Assign remaining papers to closest cluster
        for paper_id in paper_keywords:
            if paper_id not in clusters:
                clusters[paper_id] = cluster_id % num_clusters
        
        return clusters
    
    def find_shortest_path(
        self,
        source_id: str,
        target_id: str
    ) -> Optional[List[str]]:
        """
        Find shortest citation path between two papers
        
        Args:
            source_id: Source paper ID
            target_id: Target paper ID
            
        Returns:
            List of paper IDs in the path, or None if no path exists
        """
        try:
            path = nx.shortest_path(self.graph, source_id, target_id)
            return path
        except nx.NetworkXNoPath:
            logger.debug(f"No path between {source_id} and {target_id}")
            return None
        except Exception as e:
            logger.error(f"Path finding failed: {e}")
            return None
    
    def get_citation_count(self, paper_id: str) -> int:
        """Get number of papers citing this paper"""
        if paper_id not in self.graph:
            return 0
        return self.graph.in_degree(paper_id)
    
    def get_reference_count(self, paper_id: str) -> int:
        """Get number of papers cited by this paper"""
        if paper_id not in self.graph:
            return 0
        return self.graph.out_degree(paper_id)
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export graph to dictionary format"""
        return {
            "nodes": [
                {"id": node_id, **data}
                for node_id, data in self.graph.nodes(data=True)
            ],
            "edges": [
                {"source": u, "target": v, **data}
                for u, v, data in self.graph.edges(data=True)
            ]
        }
    
    # -----------------------------------------------------------------------
    # FactTable integration (revisi.md Section 9)
    # -----------------------------------------------------------------------

    def build_from_fact_table(self, fact_table: FactTable) -> Dict[str, Any]:
        """
        Build/populate the NetworkX graph from a FactTable's SPO triples.
        
        Each Entity becomes a node, each Fact becomes a directed edge.
        This transforms the flat SPO table into a traversable graph
        that the Rule Engine and Gap Detectors can query.
        
        Args:
            fact_table: FactTable instance containing entities and facts
            
        Returns:
            Dict with build statistics
        """
        self._fact_table = fact_table
        
        nodes_added = 0
        edges_added = 0
        
        # Add all entities as nodes
        for entity in fact_table.find_entities():
            if entity.entity_id not in self.graph:
                self.graph.add_node(
                    entity.entity_id,
                    name=entity.name,
                    entity_type=entity.entity_type.value if entity.entity_type else "UNKNOWN",
                    node_type="entity",
                    source_paper=entity.source_paper,
                    **entity.properties,
                )
                nodes_added += 1
        
        # Add all facts as edges
        all_facts = fact_table.query()
        for fact in all_facts:
            # Ensure both endpoints exist as nodes
            if fact.subject_id not in self.graph:
                self.graph.add_node(fact.subject_id, node_type="entity")
            if fact.object_id not in self.graph:
                self.graph.add_node(fact.object_id, node_type="entity")
            
            self.graph.add_edge(
                fact.subject_id,
                fact.object_id,
                edge_type=fact.predicate.value if fact.predicate else "UNKNOWN",
                predicate=fact.predicate.value if fact.predicate else "UNKNOWN",
                confidence=fact.confidence,
                source=fact.source,
                source_paper=fact.source_paper,
                fact_id=fact.fact_id,
                is_inferred=fact.is_inferred,
            )
            edges_added += 1
        
        stats = {
            "nodes_added": nodes_added,
            "edges_added": edges_added,
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
        }
        
        logger.info(
            f"Built graph from FactTable: {nodes_added} nodes, "
            f"{edges_added} edges added"
        )
        return stats

    def query_facts(
        self,
        subject_id: Optional[str] = None,
        predicate: Optional[str] = None,
        object_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query facts from the graph by SPO pattern.
        
        Can query from FactTable (if available) or directly from graph edges.
        This is the main interface used by the Rule Engine to check facts.
        
        Args:
            subject_id: Filter by subject entity ID
            predicate: Filter by predicate type string (e.g., "REQUIRES_RESOURCE")
            object_id: Filter by object entity ID
            
        Returns:
            List of matching fact dicts
        """
        # Prefer FactTable if available (more efficient indexing)
        if self._fact_table is not None:
            pred_enum = None
            if predicate:
                try:
                    pred_enum = PredicateType(predicate)
                except (ValueError, TypeError):
                    pass
            
            facts = self._fact_table.query(
                subject_id=subject_id,
                predicate=pred_enum,
                object_id=object_id,
            )
            return [f.to_dict() for f in facts]
        
        # Fallback: query from graph edges directly
        results = []
        for u, v, data in self.graph.edges(data=True):
            match = True
            if subject_id and u != subject_id:
                match = False
            if predicate and data.get("predicate") != predicate:
                match = False
            if object_id and v != object_id:
                match = False
            
            if match:
                results.append({
                    "subject_id": u,
                    "predicate": data.get("predicate", "UNKNOWN"),
                    "object_id": v,
                    "confidence": data.get("confidence", 1.0),
                    "source": data.get("source", ""),
                    "source_paper": data.get("source_paper", ""),
                    "fact_id": data.get("fact_id", ""),
                    "is_inferred": data.get("is_inferred", False),
                })
        
        return results

    def get_entity_neighborhood(
        self,
        entity_id: str,
        max_depth: int = 2,
    ) -> Dict[str, Any]:
        """
        Get the neighborhood of an entity in the graph.
        Useful for understanding context around a specific entity.
        
        Args:
            entity_id: The entity to explore
            max_depth: How many hops to traverse
            
        Returns:
            Dict with neighbors, edges, and subgraph info
        """
        if entity_id not in self.graph:
            return {"entity_id": entity_id, "found": False, "neighbors": [], "edges": []}
        
        # BFS to find neighborhood
        visited = {entity_id}
        frontier = [entity_id]
        neighbors = []
        edges = []
        
        for depth in range(max_depth):
            next_frontier = []
            for node in frontier:
                # Outgoing edges
                for _, target, data in self.graph.out_edges(node, data=True):
                    edges.append({
                        "source": node,
                        "target": target,
                        "predicate": data.get("predicate", "UNKNOWN"),
                        "confidence": data.get("confidence", 1.0),
                    })
                    if target not in visited:
                        visited.add(target)
                        next_frontier.append(target)
                        neighbors.append({
                            "id": target,
                            "depth": depth + 1,
                            **dict(self.graph.nodes[target]),
                        })
                
                # Incoming edges
                for source, _, data in self.graph.in_edges(node, data=True):
                    edges.append({
                        "source": source,
                        "target": node,
                        "predicate": data.get("predicate", "UNKNOWN"),
                        "confidence": data.get("confidence", 1.0),
                    })
                    if source not in visited:
                        visited.add(source)
                        next_frontier.append(source)
                        neighbors.append({
                            "id": source,
                            "depth": depth + 1,
                            **dict(self.graph.nodes[source]),
                        })
            
            frontier = next_frontier
        
        return {
            "entity_id": entity_id,
            "found": True,
            "entity_data": dict(self.graph.nodes[entity_id]),
            "neighbors": neighbors,
            "edges": edges,
        }

    def find_paths_between_entities(
        self,
        source_id: str,
        target_id: str,
        max_paths: int = 3,
    ) -> List[List[Dict[str, Any]]]:
        """
        Find paths between two entities in the fact graph.
        Used by Rule Engine for transitiviy checks (K3).
        
        Returns list of paths, each path is a list of edge dicts.
        """
        if source_id not in self.graph or target_id not in self.graph:
            return []
        
        paths = []
        try:
            for path_nodes in nx.all_simple_paths(
                self.graph, source_id, target_id, cutoff=4
            ):
                path_edges = []
                for i in range(len(path_nodes) - 1):
                    edge_data = self.graph.get_edge_data(path_nodes[i], path_nodes[i + 1])
                    if edge_data:
                        path_edges.append({
                            "from": path_nodes[i],
                            "to": path_nodes[i + 1],
                            "predicate": edge_data.get("predicate", "UNKNOWN"),
                        })
                paths.append(path_edges)
                if len(paths) >= max_paths:
                    break
        except nx.NetworkXError:
            pass
        
        return paths
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics"""
        stats = {
            "num_papers": self.graph.number_of_nodes(),
            "num_citations": self.graph.number_of_edges(),
            "avg_citations_per_paper": 0,
            "density": 0,
            "is_connected": False
        }
        
        if stats["num_papers"] > 0:
            stats["avg_citations_per_paper"] = stats["num_citations"] / stats["num_papers"]
            stats["density"] = nx.density(self.graph)
            stats["is_connected"] = nx.is_weakly_connected(self.graph)
        
        return stats


# Example usage
if __name__ == "__main__":
    builder = KnowledgeGraphBuilder()
    
    # Add sample papers
    paper1 = PaperNode(
        paper_id="paper1",
        title="Attention is All You Need",
        year=2017,
        authors=["Vaswani et al."],
        keywords=["transformer", "attention", "NLP"],
        metadata={}
    )
    
    paper2 = PaperNode(
        paper_id="paper2",
        title="BERT",
        year=2018,
        authors=["Devlin et al."],
        keywords=["BERT", "transformer", "pretraining"],
        metadata={}
    )
    
    builder.add_paper(paper1)
    builder.add_paper(paper2)
    builder.add_citation(CitationEdge("paper2", "paper1"))  # BERT cites Transformer
    
    print(f"Graph stats: {builder.get_statistics()}")
