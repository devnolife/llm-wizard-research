"""
Fact Extractor - Extract SPO triples from research paper text

Uses LLM (Ollama) to extract entities and relations from unstructured
paper text, then constructs structured Fact (SPO triple) objects.

Process (revisi.md Section 9):
    1. Entity Extraction (LLM) → identify methods, concepts, findings, etc.
    2. Relation Extraction (LLM + Pattern Matching) → identify relations
    3. Triple Construction & Validation → form (S, P, O) + validate

References:
    - Ji, S., et al. (2021). A Survey on Knowledge Graphs
    - Bosselut, A., et al. (2019). COMET: Commonsense Transformers
    - revisi.md Section 9
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .fact_table import Entity, EntityType, Fact, FactTable, PredicateType


# ---------------------------------------------------------------------------
# Prompt templates for LLM-based extraction
# ---------------------------------------------------------------------------

ENTITY_EXTRACTION_PROMPT = """You are a scientific entity extraction system. Extract structured entities from the following research paper text.

For each entity, provide:
- name: the entity name
- type: one of [METHOD, CONCEPT, DOMAIN, FINDING, DATASET, METRIC, PAPER, CONSTRAINT]
- properties: relevant properties as key-value pairs

Definitions of entity types:
- METHOD: algorithms, techniques, approaches (e.g., "CNN", "Random Forest", "BERT")
- CONCEPT: theories, frameworks, ideas (e.g., "Transfer Learning", "Attention Mechanism")
- DOMAIN: application fields (e.g., "Medical Imaging", "NLP", "Education")
- FINDING: empirical results (e.g., "achieves 95% accuracy", "reduces latency by 30%")
- DATASET: datasets used (e.g., "ImageNet", "CIFAR-10", "BraTS")
- METRIC: evaluation metrics (e.g., "Accuracy", "F1-Score", "Dice Coefficient")
- PAPER: referenced papers (e.g., "ResNet (He et al., 2016)")
- CONSTRAINT: limitations, requirements (e.g., "requires GPU >16GB", "needs large labeled data")

TEXT:
{text}

Respond ONLY with a JSON array. Example:
[
  {{"name": "CNN", "type": "METHOD", "properties": {{"resource_requirement": "high", "scalability": "single_machine"}}}},
  {{"name": "Medical Image Segmentation", "type": "DOMAIN", "properties": {{"data_availability": "moderate"}}}},
  {{"name": "achieves 92.3% Dice coefficient", "type": "FINDING", "properties": {{"metric": "Dice", "value": "92.3%"}}}}
]

JSON:"""

RELATION_EXTRACTION_PROMPT = """You are a scientific relation extraction system. Given the following entities and the source text, extract relations between them.

Each relation must be one of:
- USES_METHOD: paper/study uses a method
- PROPOSES: paper proposes something new
- APPLIES_TO: method applied to a domain
- ACHIEVES: method achieves a finding/result
- REQUIRES_RESOURCE: method requires a resource/constraint
- REQUIRES_DATA: method requires specific data type
- IMPROVES: method A improves upon method B
- CONTRADICTS: finding A contradicts finding B
- EXTENDS: concept A extends concept B
- EVALUATED_ON: method evaluated on a dataset
- HAS_CONSTRAINT: domain has a constraint/limitation
- DISCUSSES: paper discusses a concept

ENTITIES:
{entities}

TEXT:
{text}

For each relation provide:
- subject: entity name (must be from the entities list)
- predicate: relation type (must be from the list above)
- object: entity name (must be from the entities list)
- confidence: float 0.0-1.0
- evidence: brief quote from text supporting this relation

Respond ONLY with a JSON array. Example:
[
  {{"subject": "CNN", "predicate": "APPLIES_TO", "object": "Medical Image Segmentation", "confidence": 0.95, "evidence": "using CNN for medical image segmentation"}},
  {{"subject": "CNN", "predicate": "ACHIEVES", "object": "92.3% Dice coefficient", "confidence": 0.9, "evidence": "achieves 92.3% Dice coefficient"}}
]

JSON:"""


# ---------------------------------------------------------------------------
# Linguistic markers for pattern-based relation detection
# (revisi.md Section 6 - Penanda Linguistik)
# ---------------------------------------------------------------------------

CAUSAL_MARKERS = [
    "causes", "leads to", "results in", "because", "therefore",
    "consequently", "due to", "effect of", "contributes to",
    "enables", "prevents", "inhibits", "increases", "decreases",
    "improves", "enhances", "reduces", "facilitates",
]

CONTRADICTION_MARKERS = [
    "however", "contradicts", "in contrast", "whereas",
    "on the other hand", "inconsistent with", "conflicts with",
    "contrary to", "disputes", "challenges", "but",
    "despite", "nevertheless", "although", "while",
]

EXTENSION_MARKERS = [
    "extends", "builds upon", "based on", "inspired by",
    "modification of", "variant of", "generalization of",
    "adaptation of", "improvement over", "evolution of",
]


# ---------------------------------------------------------------------------
# FactExtractor
# ---------------------------------------------------------------------------

class FactExtractor:
    """
    Extracts SPO triples from research paper text using LLM + pattern matching.
    
    Pipeline:
        Text → [Entity Extraction] → [Relation Extraction] → [Triple Construction]
        
    The extracted facts populate the FactTable, which feeds the Rule Engine
    and Knowledge Graph.
    """

    def __init__(self, llm_interface=None):
        """
        Initialize FactExtractor.
        
        Args:
            llm_interface: GLMInterface instance for LLM-based extraction
        """
        self.llm = llm_interface
        logger.info("FactExtractor initialized")

    def extract_from_text(
        self,
        text: str,
        paper_id: str,
        fact_table: FactTable,
        max_text_length: int = 3000,
    ) -> Dict[str, Any]:
        """
        Full extraction pipeline: text → entities → relations → facts.
        
        Args:
            text: Paper text content
            paper_id: Unique paper identifier
            fact_table: FactTable to populate with extracted facts
            max_text_length: Maximum text length to send to LLM
            
        Returns:
            Dict with extraction statistics
        """
        logger.info(f"Extracting facts from paper: {paper_id}")
        
        # Truncate text if needed
        text_chunk = text[:max_text_length]
        
        # Step 1: Extract entities
        entities = self._extract_entities(text_chunk, paper_id, fact_table)
        logger.info(f"Extracted {len(entities)} entities from paper {paper_id}")
        
        # Step 2: Extract relations  
        facts = self._extract_relations(text_chunk, entities, paper_id, fact_table)
        logger.info(f"Extracted {len(facts)} facts from paper {paper_id}")
        
        # Step 3: Pattern-based relation detection (supplement LLM)
        pattern_facts = self._extract_pattern_relations(text_chunk, entities, paper_id, fact_table)
        logger.info(f"Extracted {len(pattern_facts)} pattern-based facts from paper {paper_id}")
        
        return {
            "paper_id": paper_id,
            "entities_extracted": len(entities),
            "llm_facts_extracted": len(facts),
            "pattern_facts_extracted": len(pattern_facts),
            "total_facts": len(facts) + len(pattern_facts),
        }

    def extract_from_papers(
        self,
        papers: List[Dict[str, Any]],
        fact_table: FactTable,
    ) -> Dict[str, Any]:
        """
        Extract facts from multiple papers.
        
        Args:
            papers: List of paper dicts with 'content', 'metadata', 'doc_id'
            fact_table: FactTable to populate
            
        Returns:
            Aggregate extraction statistics
        """
        total_stats = {
            "papers_processed": 0,
            "total_entities": 0,
            "total_facts": 0,
            "per_paper": [],
        }
        
        for paper in papers:
            paper_id = paper.get("doc_id", paper.get("id", str(uuid.uuid4())[:8]))
            content = paper.get("content", "")
            
            if not content:
                logger.warning(f"Skipping paper {paper_id}: no content")
                continue
            
            # Add the paper itself as an entity
            paper_title = paper.get("metadata", {}).get("title", "Unknown")
            paper_entity = fact_table.get_or_create_entity(
                name=paper_title,
                entity_type=EntityType.PAPER,
                source_paper=paper_id,
                properties=paper.get("metadata", {}),
            )
            
            stats = self.extract_from_text(content, paper_id, fact_table)
            total_stats["papers_processed"] += 1
            total_stats["total_entities"] += stats["entities_extracted"]
            total_stats["total_facts"] += stats["total_facts"]
            total_stats["per_paper"].append(stats)
        
        logger.info(
            f"Extraction complete: {total_stats['papers_processed']} papers, "
            f"{total_stats['total_entities']} entities, "
            f"{total_stats['total_facts']} facts"
        )
        return total_stats

    # -----------------------------------------------------------------------
    # Step 1: Entity Extraction
    # -----------------------------------------------------------------------

    def _extract_entities(
        self,
        text: str,
        paper_id: str,
        fact_table: FactTable,
    ) -> List[Entity]:
        """Extract entities from text using LLM."""
        if not self.llm:
            logger.warning("No LLM available, using pattern-based entity extraction")
            return self._extract_entities_pattern(text, paper_id, fact_table)

        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)
        
        try:
            response = self.llm.generate(
                prompt,
                system_prompt="You are a precise scientific entity extractor. Respond only with valid JSON.",
                temperature=0.1,
                max_tokens=2048,
            )
            
            # Parse JSON from LLM response
            entities_data = self._parse_json_response(response)
            
            if not isinstance(entities_data, list):
                logger.warning("LLM returned non-list response for entities")
                return self._extract_entities_pattern(text, paper_id, fact_table)
            
            entities = []
            for item in entities_data:
                try:
                    entity_type = EntityType(item.get("type", "CONCEPT"))
                    entity = fact_table.get_or_create_entity(
                        name=item.get("name", "unknown"),
                        entity_type=entity_type,
                        source_paper=paper_id,
                        properties=item.get("properties", {}),
                    )
                    entities.append(entity)
                except (ValueError, KeyError) as e:
                    logger.debug(f"Skipping invalid entity: {e}")
                    continue
            
            return entities
            
        except Exception as e:
            logger.error(f"LLM entity extraction failed: {e}")
            return self._extract_entities_pattern(text, paper_id, fact_table)

    def _extract_entities_pattern(
        self,
        text: str,
        paper_id: str,
        fact_table: FactTable,
    ) -> List[Entity]:
        """Fallback pattern-based entity extraction when LLM is unavailable."""
        entities = []
        text_lower = text.lower()
        
        # Simple pattern matching for common entity types
        # Method detection
        method_patterns = [
            r'\b(CNN|RNN|LSTM|GRU|BERT|GPT|Transformer|ResNet|VGG|GAN)\b',
            r'\b([A-Z][a-z]*(?:Net|Model|Network))\b',
            r'\b(random forest|decision tree|support vector machine|neural network)\b',
        ]
        for pattern in method_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                name = match.group(1).strip()
                if len(name) > 2:
                    entity = fact_table.get_or_create_entity(
                        name=name, entity_type=EntityType.METHOD, source_paper=paper_id
                    )
                    entities.append(entity)
        
        # Dataset detection
        dataset_patterns = [
            r'\b(ImageNet|CIFAR-\d+|MNIST|COCO|BraTS|GLUE|SQuAD|WikiText)\b',
        ]
        for pattern in dataset_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entity = fact_table.get_or_create_entity(
                    name=match.group(1), entity_type=EntityType.DATASET, source_paper=paper_id
                )
                entities.append(entity)
        
        # Metric detection
        metric_patterns = [
            r'\b(accuracy|precision|recall|F1[- ]score|AUC|ROC|Dice|IoU|BLEU|ROUGE)\b',
        ]
        for pattern in metric_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entity = fact_table.get_or_create_entity(
                    name=match.group(1), entity_type=EntityType.METRIC, source_paper=paper_id
                )
                entities.append(entity)
        
        # Finding detection (percentage results)
        finding_pattern = r'(?:achiev|obtain|reach|report)(?:es|ed|ing)?\s+(?:an?\s+)?(\d+\.?\d*\s*%)'
        for match in re.finditer(finding_pattern, text, re.IGNORECASE):
            entity = fact_table.get_or_create_entity(
                name=f"Result: {match.group(1)}", entity_type=EntityType.FINDING, source_paper=paper_id
            )
            entities.append(entity)
        
        return entities

    # -----------------------------------------------------------------------
    # Step 2: Relation Extraction (LLM)
    # -----------------------------------------------------------------------

    def _extract_relations(
        self,
        text: str,
        entities: List[Entity],
        paper_id: str,
        fact_table: FactTable,
    ) -> List[Fact]:
        """Extract relations between entities using LLM."""
        if not self.llm or not entities:
            return []

        # Format entities for prompt
        entities_str = "\n".join([
            f"- {e.name} (type: {e.entity_type.value})"
            for e in entities
        ])
        
        prompt = RELATION_EXTRACTION_PROMPT.format(
            entities=entities_str,
            text=text,
        )
        
        try:
            response = self.llm.generate(
                prompt,
                system_prompt="You are a precise scientific relation extractor. Respond only with valid JSON.",
                temperature=0.1,
                max_tokens=2048,
            )
            
            relations_data = self._parse_json_response(response)
            
            if not isinstance(relations_data, list):
                logger.warning("LLM returned non-list response for relations")
                return []
            
            facts = []
            for item in relations_data:
                try:
                    predicate = PredicateType(item.get("predicate", "DISCUSSES"))
                    
                    # Resolve entity IDs
                    subject_name = item.get("subject", "")
                    object_name = item.get("object", "")
                    
                    subject_entity = self._resolve_entity(subject_name, entities)
                    object_entity = self._resolve_entity(object_name, entities)
                    
                    if not subject_entity or not object_entity:
                        continue
                    
                    fact = Fact(
                        subject_id=subject_entity.entity_id,
                        predicate=predicate,
                        object_id=object_entity.entity_id,
                        source=item.get("evidence", ""),
                        source_paper=paper_id,
                        confidence=float(item.get("confidence", 0.7)),
                        metadata={"extraction_method": "llm"},
                    )
                    fact_table.add_fact(fact)
                    facts.append(fact)
                    
                except (ValueError, KeyError) as e:
                    logger.debug(f"Skipping invalid relation: {e}")
                    continue
            
            return facts
            
        except Exception as e:
            logger.error(f"LLM relation extraction failed: {e}")
            return []

    # -----------------------------------------------------------------------
    # Step 3: Pattern-based Relation Detection (supplement)
    # -----------------------------------------------------------------------

    def _extract_pattern_relations(
        self,
        text: str,
        entities: List[Entity],
        paper_id: str,
        fact_table: FactTable,
    ) -> List[Fact]:
        """
        Detect relations using linguistic markers (revisi.md Section 6).
        Supplements LLM extraction with pattern-based detection.
        """
        facts = []
        text_lower = text.lower()
        sentences = self._split_sentences(text)
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Check for causal markers
            for marker in CAUSAL_MARKERS:
                if marker in sentence_lower:
                    # Try to find entities in this sentence
                    mentioned = self._find_entities_in_text(sentence, entities)
                    if len(mentioned) >= 2:
                        fact = Fact(
                            subject_id=mentioned[0].entity_id,
                            predicate=PredicateType.IMPROVES if marker in ["improves", "enhances", "increases"] 
                                     else PredicateType.APPLIES_TO,
                            object_id=mentioned[1].entity_id,
                            source=sentence[:100],
                            source_paper=paper_id,
                            confidence=0.6,
                            metadata={
                                "extraction_method": "pattern",
                                "marker": marker,
                                "marker_type": "causal",
                            },
                        )
                        fact_table.add_fact(fact)
                        facts.append(fact)
                    break  # One marker per sentence
            
            # Check for contradiction markers
            for marker in CONTRADICTION_MARKERS:
                if marker in sentence_lower:
                    mentioned = self._find_entities_in_text(sentence, entities)
                    findings = [e for e in mentioned if e.entity_type == EntityType.FINDING]
                    if len(findings) >= 2:
                        fact = Fact(
                            subject_id=findings[0].entity_id,
                            predicate=PredicateType.CONTRADICTS,
                            object_id=findings[1].entity_id,
                            source=sentence[:100],
                            source_paper=paper_id,
                            confidence=0.5,  # Lower confidence for pattern-based
                            metadata={
                                "extraction_method": "pattern",
                                "marker": marker,
                                "marker_type": "contradiction",
                            },
                        )
                        fact_table.add_fact(fact)
                        facts.append(fact)
                    break
            
            # Check for extension markers
            for marker in EXTENSION_MARKERS:
                if marker in sentence_lower:
                    mentioned = self._find_entities_in_text(sentence, entities)
                    if len(mentioned) >= 2:
                        fact = Fact(
                            subject_id=mentioned[0].entity_id,
                            predicate=PredicateType.EXTENDS,
                            object_id=mentioned[1].entity_id,
                            source=sentence[:100],
                            source_paper=paper_id,
                            confidence=0.6,
                            metadata={
                                "extraction_method": "pattern",
                                "marker": marker,
                                "marker_type": "extension",
                            },
                        )
                        fact_table.add_fact(fact)
                        facts.append(fact)
                    break
        
        return facts

    # -----------------------------------------------------------------------
    # Utility methods
    # -----------------------------------------------------------------------

    def _parse_json_response(self, response: str) -> Any:
        """Parse JSON from LLM response, handling common formatting issues."""
        # Try direct parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try extracting JSON array from response
        # LLM sometimes wraps JSON in markdown code blocks
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try extracting from code block
        code_block_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response, re.DOTALL)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                pass
        
        logger.warning(f"Failed to parse JSON from LLM response: {response[:200]}...")
        return []

    def _resolve_entity(
        self, name: str, entities: List[Entity]
    ) -> Optional[Entity]:
        """Find entity by name (fuzzy match)."""
        if not name:
            return None
        
        name_lower = name.lower().strip()
        
        # Exact match
        for entity in entities:
            if entity.name.lower() == name_lower:
                return entity
        
        # Partial match
        for entity in entities:
            if name_lower in entity.name.lower() or entity.name.lower() in name_lower:
                return entity
        
        return None

    def _find_entities_in_text(
        self, text: str, entities: List[Entity]
    ) -> List[Entity]:
        """Find which entities are mentioned in a text snippet."""
        mentioned = []
        text_lower = text.lower()
        
        for entity in entities:
            if entity.name.lower() in text_lower:
                mentioned.append(entity)
        
        return mentioned

    def _split_sentences(self, text: str) -> List[str]:
        """Simple sentence splitter."""
        # Split on period, question mark, exclamation mark followed by space or end
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 20]
