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

RETRY_SUFFIX = """

IMPORTANT: Your previous response could not be parsed as JSON.
Respond with ONLY a valid JSON array starting with [ and ending with ].
No explanations, no markdown, no code fences."""


# Combined entity + relation extraction in a SINGLE LLM call (perf optimization).
# Halves LLM round-trips per paper vs. the 2-step (entities then relations) pipeline.
COMBINED_EXTRACTION_PROMPT = """You are a scientific knowledge extraction system. From the research paper text below, extract BOTH entities AND the relations between them in ONE pass.

ENTITY types: METHOD, CONCEPT, DOMAIN, FINDING, DATASET, METRIC, PAPER, CONSTRAINT
RELATION predicates: USES_METHOD, PROPOSES, APPLIES_TO, ACHIEVES, REQUIRES_RESOURCE, REQUIRES_DATA, IMPROVES, CONTRADICTS, EXTENDS, EVALUATED_ON, HAS_CONSTRAINT, DISCUSSES

Rules:
- Each relation's "subject" and "object" MUST be names present in your "entities" list.
- Keep entity names short and canonical.

TEXT:
{text}

Respond ONLY with a single JSON object (no markdown, no code fences), shaped exactly like:
{{
  "entities": [
    {{"name": "CNN", "type": "METHOD", "properties": {{"resource_requirement": "high"}}}},
    {{"name": "Medical Image Segmentation", "type": "DOMAIN", "properties": {{}}}}
  ],
  "relations": [
    {{"subject": "CNN", "predicate": "APPLIES_TO", "object": "Medical Image Segmentation", "confidence": 0.95, "evidence": "using CNN for medical image segmentation"}}
  ]
}}

JSON:"""

COMBINED_RETRY_SUFFIX = """

IMPORTANT: Your previous response could not be parsed as JSON.
Respond with ONLY a valid JSON object starting with {{ and ending with }}.
No explanations, no markdown, no code fences."""


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
        
        # Fast path: extract entities AND relations in a SINGLE LLM call.
        # Falls back to the 2-call pipeline if the combined call yields nothing.
        entities, facts = self._extract_combined(text_chunk, paper_id, fact_table)
        if entities or facts:
            logger.info(
                f"Extracted {len(entities)} entities and {len(facts)} facts "
                f"from paper {paper_id} (combined call)"
            )
        else:
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

        # Collect valid papers first (skip empties), pre-creating the PAPER entity.
        valid_papers = []
        for paper in papers:
            paper_id = paper.get("doc_id", paper.get("id", str(uuid.uuid4())[:8]))
            content = paper.get("content", "")
            if not content:
                logger.warning(f"Skipping paper {paper_id}: no content")
                continue
            # Add the paper itself as an entity
            paper_title = paper.get("metadata", {}).get("title", "Unknown")
            fact_table.get_or_create_entity(
                name=paper_title,
                entity_type=EntityType.PAPER,
                source_paper=paper_id,
                properties=paper.get("metadata", {}),
            )
            valid_papers.append((paper_id, content))

        # PERF: extract papers concurrently. The slow part is the LLM call; the
        # FactTable is lock-protected so parallel writes are safe. Falls back to
        # sequential automatically when there's 0/1 paper.
        def _do(item):
            pid, content = item
            return self.extract_from_text(content, pid, fact_table)

        if len(valid_papers) > 1:
            from concurrent.futures import ThreadPoolExecutor
            import os as _os
            workers = max(1, min(len(valid_papers), int(_os.getenv("OLLAMA_NUM_PARALLEL", "4"))))
            per_paper_stats = [None] * len(valid_papers)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_do, vp): i for i, vp in enumerate(valid_papers)}
                for fut in futures:
                    idx = futures[fut]
                    try:
                        per_paper_stats[idx] = fut.result()
                    except Exception as e:
                        logger.error(f"Paper extraction failed: {e}")
                        per_paper_stats[idx] = {"entities_extracted": 0, "total_facts": 0}
        else:
            per_paper_stats = [_do(vp) for vp in valid_papers]

        for stats in per_paper_stats:
            if not stats:
                continue
            total_stats["papers_processed"] += 1
            total_stats["total_entities"] += stats.get("entities_extracted", 0)
            total_stats["total_facts"] += stats.get("total_facts", 0)
            total_stats["per_paper"].append(stats)
        
        logger.info(
            f"Extraction complete: {total_stats['papers_processed']} papers, "
            f"{total_stats['total_entities']} entities, "
            f"{total_stats['total_facts']} facts"
        )
        return total_stats

    # -----------------------------------------------------------------------
    # Combined entity + relation extraction (single LLM call)
    # -----------------------------------------------------------------------

    def _extract_combined(
        self,
        text: str,
        paper_id: str,
        fact_table: FactTable,
    ) -> Tuple[List[Entity], List[Fact]]:
        """
        Extract entities AND relations in ONE LLM call.

        Returns (entities, facts). Returns ([], []) on any failure so the caller
        can fall back to the slower 2-call pipeline.
        """
        if not self.llm:
            return [], []

        prompt = COMBINED_EXTRACTION_PROMPT.format(text=text)
        try:
            data = self._generate_json_object(
                prompt,
                system_prompt=(
                    "You are a precise scientific knowledge extractor. "
                    "Respond only with a single valid JSON object."
                ),
            )
        except Exception as e:
            logger.debug(f"Combined extraction call failed: {e}")
            return [], []

        if not isinstance(data, dict):
            return [], []

        entities_data = data.get("entities", [])
        relations_data = data.get("relations", [])
        if not entities_data:
            return [], []

        # Build entities
        entities: List[Entity] = []
        for item in entities_data:
            if not isinstance(item, dict):
                continue
            try:
                entity_type = EntityType(item.get("type", "CONCEPT"))
            except (ValueError, KeyError):
                entity_type = EntityType.CONCEPT
            try:
                entity = fact_table.get_or_create_entity(
                    name=item.get("name", "unknown"),
                    entity_type=entity_type,
                    source_paper=paper_id,
                    properties=item.get("properties", {}) or {},
                )
                entities.append(entity)
            except Exception as e:
                logger.debug(f"Skipping invalid entity: {e}")
                continue

        if not entities:
            return [], []

        # Build facts from relations
        facts: List[Fact] = []
        for item in relations_data:
            if not isinstance(item, dict):
                continue
            try:
                predicate = PredicateType(item.get("predicate", "DISCUSSES"))
                subject_entity = self._resolve_entity(item.get("subject", ""), entities)
                object_entity = self._resolve_entity(item.get("object", ""), entities)
                if not subject_entity or not object_entity:
                    continue
                fact = Fact(
                    subject_id=subject_entity.entity_id,
                    predicate=predicate,
                    object_id=object_entity.entity_id,
                    source=item.get("evidence", ""),
                    source_paper=paper_id,
                    confidence=float(item.get("confidence", 0.7)),
                    metadata={"extraction_method": "llm_combined"},
                )
                fact_table.add_fact(fact)
                facts.append(fact)
            except (ValueError, KeyError) as e:
                logger.debug(f"Skipping invalid relation: {e}")
                continue

        return entities, facts

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
            entities_data = self._generate_json(
                prompt,
                system_prompt="You are a precise scientific entity extractor. Respond only with a valid JSON array.",
            )
            
            if not entities_data:
                logger.warning("LLM entity extraction returned no parseable entities, using pattern fallback")
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
            relations_data = self._generate_json(
                prompt,
                system_prompt="You are a precise scientific relation extractor. Respond only with a valid JSON array.",
            )
            
            if not relations_data:
                logger.warning("LLM relation extraction returned no parseable relations")
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
                    if len(mentioned) >= 2 and mentioned[0].entity_id != mentioned[1].entity_id:
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
                    if len(findings) >= 2 and findings[0].entity_id != findings[1].entity_id:
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
                    if len(mentioned) >= 2 and mentioned[0].entity_id != mentioned[1].entity_id:
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

    def _generate_json(
        self,
        prompt: str,
        system_prompt: str,
        max_retries: int = 1,
    ) -> List[Any]:
        """
        Call the LLM expecting a JSON array response.
        
        Uses Ollama's structured output (format="json") when supported, and
        retries once with a stricter prompt if parsing fails.
        
        Returns:
            Parsed list (possibly empty if the LLM legitimately found nothing
            or all attempts failed).
        """
        attempt_prompt = prompt
        for attempt in range(max_retries + 1):
            # Some models (e.g. reasoning models like gpt-oss) return an empty
            # response when Ollama's structured output (format="json") is
            # enforced. Use JSON mode on the first attempt only and fall back
            # to an unconstrained call on retry.
            use_json_format = attempt == 0
            try:
                if use_json_format:
                    response = self.llm.generate(
                        attempt_prompt,
                        system_prompt=system_prompt,
                        temperature=0.1,
                        max_tokens=2048,
                        format="json",
                    )
                else:
                    response = self.llm.generate(
                        attempt_prompt,
                        system_prompt=system_prompt,
                        temperature=0.1,
                        max_tokens=2048,
                    )
            except TypeError:
                # LLM interface without `format` kwarg (e.g., custom mocks)
                response = self.llm.generate(
                    attempt_prompt,
                    system_prompt=system_prompt,
                    temperature=0.1,
                    max_tokens=2048,
                )
            
            parsed = self._parse_json_response(response)
            if parsed is not None:
                return parsed
            
            if attempt < max_retries:
                logger.warning(
                    f"JSON parse failed (attempt {attempt + 1}/{max_retries + 1}), "
                    "retrying without JSON mode and stricter prompt"
                )
                attempt_prompt = prompt + RETRY_SUFFIX
        
        logger.error("All JSON extraction attempts failed")
        return []

    def _generate_json_object(
        self,
        prompt: str,
        system_prompt: str,
        max_retries: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """
        Call the LLM expecting a JSON OBJECT response (e.g. {"entities": [...],
        "relations": [...]}). Retries once with a stricter prompt on parse
        failure. Returns None when nothing parseable was produced.
        """
        attempt_prompt = prompt
        for attempt in range(max_retries + 1):
            use_json_format = attempt == 0
            try:
                if use_json_format:
                    response = self.llm.generate(
                        attempt_prompt,
                        system_prompt=system_prompt,
                        temperature=0.1,
                        max_tokens=2048,
                        format="json",
                    )
                else:
                    response = self.llm.generate(
                        attempt_prompt,
                        system_prompt=system_prompt,
                        temperature=0.1,
                        max_tokens=2048,
                    )
            except TypeError:
                response = self.llm.generate(
                    attempt_prompt,
                    system_prompt=system_prompt,
                    temperature=0.1,
                    max_tokens=2048,
                )

            parsed = self._parse_json_object_response(response)
            if parsed is not None:
                return parsed

            if attempt < max_retries:
                logger.warning(
                    f"JSON object parse failed (attempt {attempt + 1}/"
                    f"{max_retries + 1}), retrying with stricter prompt"
                )
                attempt_prompt = prompt + COMBINED_RETRY_SUFFIX

        return None

    def _parse_json_object_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse a JSON object from an LLM response, tolerating fences/extra text."""
        if not response:
            return None
        try:
            parsed = json.loads(response)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass
        # Markdown code block
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if code_block_match:
            try:
                parsed = json.loads(code_block_match.group(1))
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                pass
        # Bare object
        obj_match = re.search(r'\{.*\}', response, re.DOTALL)
        if obj_match:
            try:
                parsed = json.loads(obj_match.group())
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                pass
        return None

    def _parse_json_response(self, response: str) -> Optional[List[Any]]:
        """
        Parse a JSON array from LLM response, handling common formatting issues.
        
        Returns:
            Parsed list, or None when no JSON could be recovered (signals retry).
        """
        parsed = None
        
        # Try direct parse first
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            # Try extracting from markdown code block (most specific)
            code_block_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response, re.DOTALL)
            if code_block_match:
                try:
                    parsed = json.loads(code_block_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Try extracting bare JSON array
            if parsed is None:
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        pass
        
        if parsed is None:
            # Last resort: salvage complete objects from a TRUNCATED array
            # (common when the LLM hits its max_tokens limit mid-response)
            salvaged = self._salvage_truncated_array(response)
            if salvaged:
                logger.warning(
                    f"Salvaged {len(salvaged)} complete objects from truncated JSON response"
                )
                return salvaged
            logger.warning(f"Failed to parse JSON from LLM response: {response[:200]}...")
            return None
        
        # Ollama JSON mode often wraps arrays in an object, e.g. {"entities": [...]}
        if isinstance(parsed, dict):
            for value in parsed.values():
                if isinstance(value, list):
                    return value
            # Single JSON object → treat as a one-element array
            return [parsed]
        
        if isinstance(parsed, list):
            return parsed
        
        return None

    @staticmethod
    def _salvage_truncated_array(text: str) -> Optional[List[Any]]:
        """
        Recover complete JSON objects from a truncated array response.
        
        Scans from the first '[' and collects every brace-balanced top-level
        object, ignoring the trailing incomplete one.
        """
        start = text.find("[")
        if start == -1:
            return None
        
        objects = []
        depth = 0
        obj_start = None
        in_string = False
        escaped = False
        
        for i in range(start, len(text)):
            ch = text[i]
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                if depth == 0:
                    obj_start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and obj_start is not None:
                    try:
                        objects.append(json.loads(text[obj_start:i + 1]))
                    except json.JSONDecodeError:
                        pass
                    obj_start = None
        
        return objects or None

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
        """Find which entities are mentioned in a text snippet (deduplicated)."""
        mentioned = []
        seen_ids = set()
        text_lower = text.lower()
        
        for entity in entities:
            if entity.entity_id in seen_ids:
                continue
            if entity.name.lower() in text_lower:
                mentioned.append(entity)
                seen_ids.add(entity.entity_id)
        
        return mentioned

    def _split_sentences(self, text: str) -> List[str]:
        """Simple sentence splitter."""
        # Split on period, question mark, exclamation mark followed by space or end
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 20]
