"""
Knowledge Graph Builder for Research Papers

Builds and manages knowledge graphs of research papers, citations, and relationships.
"""

from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
import networkx as nx
from collections import defaultdict

from loguru import logger


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
    Builds and manages knowledge graphs of research papers
    
    Features:
    - Paper relationship modeling
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
        
        # Extract and add citations (simplified)
        # In production, use proper citation parsing
        for doc in documents:
            doc_id = doc.get("doc_id", doc.get("id"))
            # Placeholder for citation extraction
            # citations = extract_citations(doc.get("content", ""))
            # for cited_id in citations:
            #     self.add_citation(CitationEdge(doc_id, cited_id))
        
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
