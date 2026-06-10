#!/usr/bin/env python3
"""
Experiment Runner — Wizard Research System
Runs the Neuro-Symbolic Agentic pipeline on the benchmark dataset and collects
metrics, with ablation modes for hypothesis testing (H6, H7).

Modes:
    full             Complete pipeline: ingestion → fact extraction →
                     gap detection + rule engine validation → adversarial check
    no-rule-engine   Pipeline WITHOUT the symbolic validation layer (H7:
                     does the Rule Engine reduce false discoveries?)
    linear-baseline  Plain RAG+LLM single-prompt gap detection — no agentic
                     loop, no fact extraction, no rule engine (H6: does the
                     agentic/neuro-symbolic system outperform a linear pipeline?)

Usage:
    cd backend
    python experiments/run_experiment.py                              # full, default model
    python experiments/run_experiment.py --mode no-rule-engine
    python experiments/run_experiment.py --mode linear-baseline
    python experiments/run_experiment.py --model gpt-oss:latest --mode full
    python experiments/run_experiment.py --topics T1,T4 --fresh-db
"""

import argparse
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

# Setup paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

# Default Ollama model (overridable via OLLAMA_MODEL env var or --model flag)
if "OLLAMA_MODEL" not in os.environ:
    os.environ["OLLAMA_MODEL"] = "llama3.2:latest"

from app.utils.config_loader import get_config
from app.utils.document_processor import DocumentProcessor
from app.core.retrieval.vector_store import VectorStore, Document
from app.services.llm_service import GLMInterface, ModelConfig
from app.core.knowledge.fact_table import Entity, EntityType, Fact, FactTable, PredicateType
from app.core.knowledge.fact_extractor import FactExtractor
from app.core.validation.rule_engine import RuleEngine
from app.core.validation.relation_classifier import RelationClassifier
from app.core.knowledge_graph.graph_builder import KnowledgeGraphBuilder
from app.core.gap_detection.analyzer import GapAnalyzer

from loguru import logger

# --- Configuration ---
PAPERS_DIR = PROJECT_DIR / "research_papers"
MANIFEST_PATH = PAPERS_DIR / "papers_manifest.json"
RESULTS_DIR = BACKEND_DIR / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Fallback topics when no manifest exists
DEFAULT_TOPICS = {
    "T1": "deep learning architectures and optimization techniques",
    "T2": "computer vision object detection and image recognition",
    "T3": "natural language processing and attention mechanisms",
}


def load_topics(topic_filter=None, custom_topics=None):
    """Load topic queries from the dataset manifest (falls back to defaults).

    custom_topics: list of "KEY:query text" strings appended verbatim — used
    for negative-control topics that are deliberately absent from the corpus.
    """
    topics = DEFAULT_TOPICS
    if MANIFEST_PATH.exists():
        try:
            manifest = json.loads(MANIFEST_PATH.read_text())
            topics = manifest.get("topics", DEFAULT_TOPICS)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not read manifest: {e}")
    
    if topic_filter:
        wanted = {t.strip().upper() for t in topic_filter.split(",")}
        topics = {k: v for k, v in topics.items() if k.upper() in wanted}
        if not topics and not custom_topics:
            logger.error(f"No topics match filter '{topic_filter}'")
            sys.exit(1)
    
    for spec in custom_topics or []:
        if ":" in spec:
            key, query = spec.split(":", 1)
            topics[key.strip()] = query.strip()
        else:
            topics[f"TC{len(topics)}"] = spec.strip()
    
    return topics


def init_components(model_name=None, mode="full", fresh_db=False, use_nli=False):
    """Initialize pipeline components according to the experiment mode."""
    config = get_config()
    model_name = model_name or os.environ.get("OLLAMA_MODEL", config.llm.model_name)

    logger.info(f"Using LLM model: {model_name} | mode: {mode} | dedicated NLI: {use_nli}")

    # Use a separate collection for experiments
    vector_store = VectorStore(
        persist_directory=str(PROJECT_DIR / "chroma_db_experiment"),
        collection_name="experiment_papers",
        embedding_model=config.vector_db.embedding_model,
    )
    if fresh_db:
        try:
            vector_store.clear_collection()
            logger.info("Experiment vector store cleared (--fresh-db)")
        except Exception as e:
            logger.warning(f"Could not clear vector store: {e}")

    model_cfg = ModelConfig(
        model_name=model_name,
        base_url=config.llm.base_url,
        temperature=0.3,  # Lower for reproducibility
        max_tokens=2048,
    )
    llm = GLMInterface(model_cfg)

    fact_table = FactTable()
    fact_extractor = FactExtractor(llm_interface=llm)
    rule_engine = RuleEngine(fact_table=fact_table)

    nli_model = None
    if use_nli:
        from app.core.validation.nli_model import NLIModel
        nli_model = NLIModel()

    relation_classifier = RelationClassifier(llm_interface=llm, nli_model=nli_model)
    kg_builder = KnowledgeGraphBuilder()
    doc_processor = DocumentProcessor(chunk_size=512, chunk_overlap=50)

    # Ablation: no-rule-engine mode removes the symbolic validation layer (H7)
    analyzer_rule_engine = rule_engine if mode == "full" else None

    gap_analyzer = GapAnalyzer(
        vector_store=vector_store,
        knowledge_graph=kg_builder,
        llm_interface=llm,
        fact_table=fact_table,
        relation_classifier=relation_classifier,
        rule_engine=analyzer_rule_engine,
    )

    return {
        "vector_store": vector_store,
        "llm": llm,
        "fact_table": fact_table,
        "fact_extractor": fact_extractor,
        "rule_engine": rule_engine,
        "relation_classifier": relation_classifier,
        "kg_builder": kg_builder,
        "doc_processor": doc_processor,
        "gap_analyzer": gap_analyzer,
        "mode": mode,
        "model_name": model_name,
    }


def phase1_ingest_papers(components):
    """Phase 1: Extract text from PDFs and ingest into vector store."""
    logger.info("=" * 60)
    logger.info("PHASE 1: Paper Ingestion")
    logger.info("=" * 60)

    doc_processor = components["doc_processor"]
    vector_store = components["vector_store"]
    results = {"papers": [], "total_chunks": 0, "total_chars": 0}
    start = time.time()

    pdf_files = sorted(PAPERS_DIR.glob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files")

    for pdf_path in pdf_files:
        paper_start = time.time()
        logger.info(f"Processing: {pdf_path.name}")

        try:
            processed = doc_processor.process_pdf(str(pdf_path))
            paper_info = {
                "filename": pdf_path.name,
                "title": processed.title,
                "num_chunks": len(processed.chunks),
                "content_length": len(processed.content),
                "metadata": {k: str(v) for k, v in processed.metadata.items()},
            }

            # Add chunks to vector store
            chunk_ids = []
            for chunk in processed.chunks:
                doc_id = vector_store.add_document(
                    content=chunk.content,
                    metadata={
                        "source": pdf_path.name,
                        "title": processed.title,
                        "chunk_index": chunk.chunk_index,
                        "total_chunks": chunk.total_chunks,
                        **{k: str(v) for k, v in processed.metadata.items()},
                    },
                )
                chunk_ids.append(doc_id)

            paper_info["chunk_ids"] = chunk_ids
            paper_info["processing_time"] = round(time.time() - paper_start, 2)
            results["papers"].append(paper_info)
            results["total_chunks"] += len(processed.chunks)
            results["total_chars"] += len(processed.content)

            logger.info(
                f"  ✓ {processed.title}: {len(processed.chunks)} chunks, "
                f"{len(processed.content)} chars ({paper_info['processing_time']}s)"
            )
        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")
            results["papers"].append({
                "filename": pdf_path.name,
                "error": str(e),
            })

    results["total_time"] = round(time.time() - start, 2)
    results["vector_store_count"] = vector_store.count()
    logger.info(
        f"Phase 1 complete: {results['total_chunks']} chunks ingested "
        f"in {results['total_time']}s"
    )
    return results


def phase2_fact_extraction(components, papers_data):
    """Phase 2: Extract SPO facts from paper content."""
    logger.info("=" * 60)
    logger.info("PHASE 2: Fact Extraction")
    logger.info("=" * 60)

    fact_extractor = components["fact_extractor"]
    fact_table = components["fact_table"]
    results = {"papers": [], "total_facts": 0}
    start = time.time()

    for paper in papers_data:
        if "error" in paper:
            continue

        paper_start = time.time()
        title = paper.get("title", paper["filename"])
        logger.info(f"Extracting facts from: {title}")

        # Use first 3000 chars for extraction (LLM context limit)
        vs = components["vector_store"]
        search_results = vs.search(query=title, top_k=5)
        content = "\n".join([r.document.content for r in search_results])[:3000]

        try:
            extraction_result = fact_extractor.extract_from_text(
                text=content,
                paper_id=paper["filename"],
                fact_table=fact_table,
                max_text_length=3000,
            )

            num_facts = extraction_result.get("total_facts", 0) if isinstance(extraction_result, dict) else 0
            fact_info = {
                "paper": title,
                "num_facts": num_facts,
                "extraction_stats": extraction_result if isinstance(extraction_result, dict) else {},
                "facts_sample": [],
                "extraction_time": round(time.time() - paper_start, 2),
            }

            # Sample facts from fact_table (resolve entity names for readability)
            paper_facts = fact_table.get_facts_for_paper(paper["filename"])
            for fact in paper_facts[:5]:
                subj = fact_table.get_entity(fact.subject_id)
                obj = fact_table.get_entity(fact.object_id)
                fact_info["facts_sample"].append({
                    "subject": subj.name if subj else fact.subject_id,
                    "predicate": fact.predicate.value,
                    "object": obj.name if obj else fact.object_id,
                    "confidence": float(fact.confidence),
                })

            results["total_facts"] += num_facts

            results["papers"].append(fact_info)
            logger.info(
                f"  ✓ {title}: {fact_info['num_facts']} facts "
                f"({fact_info['extraction_time']}s)"
            )
        except Exception as e:
            logger.error(f"  ✗ Fact extraction failed for {title}: {e}")
            results["papers"].append({
                "paper": title,
                "error": str(e),
                "extraction_time": round(time.time() - paper_start, 2),
            })

    results["total_time"] = round(time.time() - start, 2)

    # Fact table stats
    try:
        results["fact_table_stats"] = components["fact_table"].get_statistics()
    except Exception:
        results["fact_table_stats"] = {}

    # Full fact dump (entity names resolved) — feeds the SPO precision
    # annotation tooling (annotate_facts.py)
    all_facts = []
    for fact in fact_table.query():
        subj = fact_table.get_entity(fact.subject_id)
        obj = fact_table.get_entity(fact.object_id)
        all_facts.append({
            "fact_id": fact.fact_id,
            "subject": subj.name if subj else fact.subject_id,
            "subject_type": subj.entity_type.value if subj else "?",
            "predicate": fact.predicate.value,
            "object": obj.name if obj else fact.object_id,
            "object_type": obj.entity_type.value if obj else "?",
            "confidence": float(fact.confidence),
            "source_paper": fact.source_paper,
            "evidence": fact.source[:200],
            "extraction_method": fact.metadata.get("extraction_method", "llm"),
        })
    results["all_facts"] = all_facts

    logger.info(
        f"Phase 2 complete: {results['total_facts']} facts extracted "
        f"in {results['total_time']}s"
    )
    return results


def phase3_gap_detection(components, topics):
    """Phase 3: Run gap detection for each topic."""
    logger.info("=" * 60)
    logger.info("PHASE 3: Gap Detection")
    logger.info("=" * 60)

    gap_analyzer = components["gap_analyzer"]
    vector_store = components["vector_store"]
    results = {"topics": []}
    start = time.time()

    for topic_key, topic in topics.items():
        topic_start = time.time()
        logger.info(f"Analyzing topic [{topic_key}]: {topic}")

        # Retrieve relevant papers
        search_results = vector_store.search(query=topic, top_k=10)
        papers_for_analysis = [
            {
                "content": r.document.content,
                "metadata": r.document.metadata,
                "id": r.document.id,
            }
            for r in search_results
        ]

        logger.info(f"  Retrieved {len(papers_for_analysis)} relevant chunks")

        try:
            indicators = gap_analyzer.analyze_gaps(
                topic=topic,
                papers=papers_for_analysis,
                depth="standard",
            )

            topic_result = {
                "topic": topic,
                "topic_key": topic_key,
                "num_papers_retrieved": len(papers_for_analysis),
                "total_indicators": len(indicators),
                "indicators": [],
                "distribution": {
                    "FRAGMENTATION": 0,
                    "INCONSISTENCY": 0,
                    "INCOMPLETENESS": 0,
                },
                "verdicts": {
                    "PASS": 0,
                    "FLAG": 0,
                    "REJECT": 0,
                    "NONE": 0,
                },
                "confidence_scores": [],
                "analysis_time": 0,
            }

            for ind in indicators:
                ind_type = str(getattr(ind, 'indicator_type', getattr(ind, 'gap_type', 'UNKNOWN')))
                # Normalize type name
                for t in ["FRAGMENTATION", "INCONSISTENCY", "INCOMPLETENESS"]:
                    if t in ind_type.upper():
                        topic_result["distribution"][t] += 1
                        break

                verdict = str(getattr(ind, 'rule_engine_verdict', 'NONE'))
                for v in ["PASS", "FLAG", "REJECT"]:
                    if v in verdict.upper():
                        topic_result["verdicts"][v] += 1
                        break
                else:
                    topic_result["verdicts"]["NONE"] += 1

                conf = float(getattr(ind, 'confidence', 0.0))
                topic_result["confidence_scores"].append(conf)

                # adjusted_confidence is None when the Rule Engine is disabled
                # (no-rule-engine ablation) — fall back to raw confidence
                adj = getattr(ind, 'adjusted_confidence', None)
                topic_result["indicators"].append({
                    "type": ind_type,
                    "description": str(getattr(ind, 'description', ''))[:200],
                    "confidence": conf,
                    "adjusted_confidence": float(adj) if adj is not None else conf,
                    "verdict": verdict,
                    "requires_human_validation": bool(getattr(ind, 'requires_human_validation', True)),
                    "evidence_count": len(getattr(ind, 'evidence', [])),
                    "suggested_directions": [str(d) for d in getattr(ind, 'suggested_directions', [])],
                })

            topic_result["analysis_time"] = round(time.time() - topic_start, 2)

            if topic_result["confidence_scores"]:
                scores = topic_result["confidence_scores"]
                topic_result["avg_confidence"] = round(sum(scores) / len(scores), 3)
                topic_result["max_confidence"] = round(max(scores), 3)
                topic_result["min_confidence"] = round(min(scores), 3)
            else:
                topic_result["avg_confidence"] = 0.0

            results["topics"].append(topic_result)
            logger.info(
                f"  ✓ {len(indicators)} indicators found "
                f"(F:{topic_result['distribution']['FRAGMENTATION']} "
                f"I:{topic_result['distribution']['INCONSISTENCY']} "
                f"C:{topic_result['distribution']['INCOMPLETENESS']}) "
                f"in {topic_result['analysis_time']}s"
            )

        except Exception as e:
            logger.error(f"  ✗ Gap detection failed for '{topic}': {e}")
            import traceback
            traceback.print_exc()
            results["topics"].append({
                "topic": topic,
                "topic_key": topic_key,
                "error": str(e),
                "analysis_time": round(time.time() - topic_start, 2),
            })

    results["total_time"] = round(time.time() - start, 2)
    logger.info(f"Phase 3 complete in {results['total_time']}s")
    return results


LINEAR_BASELINE_PROMPT = """You are a research gap detection system. Based on the following excerpts from research papers about "{topic}", identify research gaps.

PAPER EXCERPTS:
{context}

Identify up to 5 research gaps. For each gap provide:
- type: one of [FRAGMENTATION, INCONSISTENCY, INCOMPLETENESS]
- description: clear description of the gap
- confidence: float 0.0-1.0

Respond ONLY with a JSON array. Example:
[
  {{"type": "INCOMPLETENESS", "description": "No study evaluates X under Y conditions", "confidence": 0.7}}
]

JSON:"""


def phase3_linear_baseline(components, topics):
    """
    Phase 3 (linear-baseline mode): plain RAG+LLM single-prompt gap detection.

    No agentic loop, no 3-indicator analysis, no fact base, no rule engine —
    this is the conventional pipeline the thesis compares against (H6).
    """
    logger.info("=" * 60)
    logger.info("PHASE 3 (LINEAR BASELINE): Single-prompt RAG+LLM Gap Detection")
    logger.info("=" * 60)

    llm = components["llm"]
    vector_store = components["vector_store"]
    fact_extractor = components["fact_extractor"]  # reuse its JSON parser
    results = {"topics": []}
    start = time.time()

    for topic_key, topic in topics.items():
        topic_start = time.time()
        logger.info(f"Analyzing topic [{topic_key}]: {topic}")

        search_results = vector_store.search(query=topic, top_k=10)
        context = "\n---\n".join(r.document.content for r in search_results)[:6000]

        topic_result = {
            "topic": topic,
            "topic_key": topic_key,
            "num_papers_retrieved": len(search_results),
            "total_indicators": 0,
            "indicators": [],
            "distribution": {"FRAGMENTATION": 0, "INCONSISTENCY": 0, "INCOMPLETENESS": 0},
            "verdicts": {"PASS": 0, "FLAG": 0, "REJECT": 0, "NONE": 0},
            "confidence_scores": [],
        }

        try:
            response = llm.generate(
                LINEAR_BASELINE_PROMPT.format(topic=topic, context=context),
                system_prompt="You are a research gap detector. Respond only with a valid JSON array.",
                temperature=0.3,
                max_tokens=2048,
                format="json",
            )
            gaps = fact_extractor._parse_json_response(response) or []

            for gap in gaps[:5]:
                if not isinstance(gap, dict):
                    continue
                gap_type = str(gap.get("type", "UNKNOWN")).upper()
                conf = float(gap.get("confidence", 0.5))
                if gap_type in topic_result["distribution"]:
                    topic_result["distribution"][gap_type] += 1
                topic_result["confidence_scores"].append(conf)
                # Baseline has no rule engine → verdict NONE
                topic_result["verdicts"]["NONE"] += 1
                topic_result["indicators"].append({
                    "type": gap_type,
                    "description": str(gap.get("description", ""))[:200],
                    "confidence": conf,
                    "adjusted_confidence": conf,
                    "verdict": "NONE",
                    "requires_human_validation": True,
                    "evidence_count": 0,
                    "suggested_directions": [],
                })

            topic_result["total_indicators"] = len(topic_result["indicators"])
            scores = topic_result["confidence_scores"]
            topic_result["avg_confidence"] = round(sum(scores) / len(scores), 3) if scores else 0.0
            topic_result["analysis_time"] = round(time.time() - topic_start, 2)
            results["topics"].append(topic_result)
            logger.info(
                f"  ✓ {topic_result['total_indicators']} gaps from single prompt "
                f"({topic_result['analysis_time']}s)"
            )
        except Exception as e:
            logger.error(f"  ✗ Baseline failed for '{topic}': {e}")
            results["topics"].append({
                "topic": topic,
                "topic_key": topic_key,
                "error": str(e),
                "analysis_time": round(time.time() - topic_start, 2),
            })

    results["total_time"] = round(time.time() - start, 2)
    logger.info(f"Phase 3 (linear baseline) complete in {results['total_time']}s")
    return results


def phase4_rule_engine_analysis(components, gap_results):
    """Phase 4: Detailed rule engine analysis."""
    logger.info("=" * 60)
    logger.info("PHASE 4: Rule Engine Analysis")
    logger.info("=" * 60)

    rule_engine = components["rule_engine"]
    results = {"summary": {}, "rules_triggered": []}
    start = time.time()

    total_pass = total_flag = total_reject = 0

    for topic_data in gap_results.get("topics", []):
        if "error" in topic_data:
            continue
        for v, count in topic_data.get("verdicts", {}).items():
            if v == "PASS":
                total_pass += count
            elif v == "FLAG":
                total_flag += count
            elif v == "REJECT":
                total_reject += count

    total = total_pass + total_flag + total_reject
    results["summary"] = {
        "total_evaluated": total,
        "passed": total_pass,
        "flagged": total_flag,
        "rejected": total_reject,
        "pass_rate": round(total_pass / total * 100, 1) if total > 0 else 0,
        "flag_rate": round(total_flag / total * 100, 1) if total > 0 else 0,
        "reject_rate": round(total_reject / total * 100, 1) if total > 0 else 0,
    }

    results["total_time"] = round(time.time() - start, 2)
    logger.info(f"Rule Engine Summary: {results['summary']}")
    return results


# ---------------------------------------------------------------------------
# Phase 5: Adversarial validation of the Rule Engine
# ---------------------------------------------------------------------------

ADVERSARIAL_CASES = [
    {
        "case_id": "ADV-F1",
        "rule_tested": "F1 (Resource Compatibility)",
        "expected_verdict": "REJECT",
        "claim": {
            "type": "recommendation",
            "description": "Deploy a large GPT-4-scale language model directly on edge devices",
            "method": "adv_large_llm",
            "domain": "adv_edge_deployment",
            "confidence": 0.9,
        },
    },
    {
        "case_id": "ADV-F2",
        "rule_tested": "F2 (Data Compatibility)",
        "expected_verdict": "FLAG",
        "claim": {
            "type": "recommendation",
            "description": "Apply fully supervised transformer training to rare disease imaging",
            "method": "adv_supervised_transformer",
            "domain": "adv_rare_disease_imaging",
            "confidence": 0.8,
        },
    },
    {
        "case_id": "ADV-F3",
        "rule_tested": "F3 (Scale Compatibility)",
        "expected_verdict": "REJECT",
        "claim": {
            "type": "recommendation",
            "description": "Use the in-memory single-node algorithm for distributed large-scale cluster processing of big data",
            "method": "adv_inmemory_algo",
            "domain": "adv_bigdata_processing",
            "confidence": 0.85,
        },
    },
    {
        "case_id": "ADV-K1",
        "rule_tested": "K1 (Internal Contradiction)",
        "expected_verdict": "FLAG",
        "claim": {
            "type": "gap_indicator",
            "description": "Both findings hold simultaneously despite reporting opposite results",
            "findings": ["adv_finding_x", "adv_finding_y"],
            "confidence": 0.75,
        },
    },
    {
        "case_id": "ADV-C1",
        "rule_tested": "C1 (Causal Evidence)",
        "expected_verdict": "FLAG",
        "claim": {
            "type": "gap_indicator",
            "description": "Method P causally improves outcome Q across the literature",
            "findings": ["adv_finding_p", "adv_finding_q"],
            "confidence": 0.8,
        },
    },
    {
        "case_id": "ADV-PASS",
        "rule_tested": "Control (no violations)",
        "expected_verdict": "PASS",
        "claim": {
            "type": "gap_indicator",
            "description": "Literature lacks systematic comparison of normalization strategies",
            "confidence": 0.7,
        },
    },
]


def _build_adversarial_fact_table() -> FactTable:
    """
    Build an ISOLATED FactTable seeded with facts that must trigger
    specific rules. Isolation prevents contaminating the main experiment.
    """
    ft = FactTable()

    entities = [
        Entity("adv_large_llm", EntityType.METHOD, "Large LLM (GPT-4 scale)",
               properties={"resource_requirement": "high"}),
        Entity("adv_edge_deployment", EntityType.DOMAIN, "Edge Deployment",
               properties={"constraint": "low_resource"}),
        Entity("adv_supervised_transformer", EntityType.METHOD, "Supervised Transformer"),
        Entity("adv_rare_disease_imaging", EntityType.DOMAIN, "Rare Disease Imaging"),
        Entity("adv_inmemory_algo", EntityType.METHOD, "In-Memory Single-Node Algorithm"),
        Entity("adv_bigdata_processing", EntityType.DOMAIN, "Big Data Processing"),
        Entity("adv_finding_x", EntityType.FINDING, "Dropout improves generalization"),
        Entity("adv_finding_y", EntityType.FINDING, "Dropout degrades generalization"),
        Entity("adv_finding_p", EntityType.FINDING, "Method P applied"),
        Entity("adv_finding_q", EntityType.FINDING, "Outcome Q improved"),
    ]
    for e in entities:
        ft.add_entity(e)

    facts = [
        # F1: high-resource method × low-resource domain
        Fact(fact_id="advf1a", subject_id="adv_large_llm",
             predicate=PredicateType.REQUIRES_RESOURCE,
             object_id="high_end_gpu_cluster", source="adversarial",
             source_paper="adv", confidence=0.95),
        Fact(fact_id="advf1b", subject_id="adv_edge_deployment",
             predicate=PredicateType.HAS_CONSTRAINT,
             object_id="low_resource_edge_device", source="adversarial",
             source_paper="adv", confidence=0.95),
        # F2: large labeled data × scarce data domain
        Fact(fact_id="advf2a", subject_id="adv_supervised_transformer",
             predicate=PredicateType.REQUIRES_DATA,
             object_id="large_labeled_dataset", source="adversarial",
             source_paper="adv", confidence=0.9),
        Fact(fact_id="advf2b", subject_id="adv_rare_disease_imaging",
             predicate=PredicateType.HAS_CONSTRAINT,
             object_id="scarce_annotated_data", source="adversarial",
             source_paper="adv", confidence=0.9),
        # F3: single-machine method (description mentions distributed scale)
        Fact(fact_id="advf3a", subject_id="adv_inmemory_algo",
             predicate=PredicateType.REQUIRES_RESOURCE,
             object_id="single_machine_memory", source="adversarial",
             source_paper="adv", confidence=0.9),
        # K1: contradicting findings inside one claim
        Fact(fact_id="advk1a", subject_id="adv_finding_x",
             predicate=PredicateType.CONTRADICTS,
             object_id="adv_finding_y", source="adversarial",
             source_paper="adv", confidence=0.85),
        # C1: causal link supported by only ONE source
        Fact(fact_id="advc1a", subject_id="adv_finding_p",
             predicate=PredicateType.IMPROVES,
             object_id="adv_finding_q", source="adversarial",
             source_paper="adv", confidence=0.8),
    ]
    for f in facts:
        ft.add_fact(f)

    return ft


def phase5_adversarial_validation():
    """
    Phase 5: Prove the Rule Engine actually discriminates.

    Injects claims that are designed to violate specific rules (plus a clean
    control claim) into an isolated FactTable, then checks whether the engine
    returns the expected verdicts. This addresses the examiner's concern that
    a 100% PASS rate demonstrates nothing.
    """
    logger.info("=" * 60)
    logger.info("PHASE 5: Adversarial Rule Engine Validation")
    logger.info("=" * 60)

    start = time.time()
    ft = _build_adversarial_fact_table()
    engine = RuleEngine(fact_table=ft)

    results = {"cases": [], "summary": {}}
    correct = 0

    for case in ADVERSARIAL_CASES:
        report = engine.validate(case["claim"])
        actual = report.overall_verdict
        expected = case["expected_verdict"]
        match = actual == expected
        correct += match

        triggered = [
            {"rule": r.rule.rule_id, "verdict": r.verdict, "reason": r.reason[:150]}
            for r in report.results
            if r.verdict in ("FLAG", "REJECT")
        ]

        results["cases"].append({
            "case_id": case["case_id"],
            "rule_tested": case["rule_tested"],
            "description": case["claim"]["description"],
            "expected_verdict": expected,
            "actual_verdict": actual,
            "match": match,
            "original_confidence": report.original_confidence,
            "adjusted_confidence": report.adjusted_confidence,
            "rules_triggered": triggered,
        })

        status = "✓" if match else "✗"
        logger.info(f"  {status} {case['case_id']}: expected {expected}, got {actual}")

    total = len(ADVERSARIAL_CASES)
    results["summary"] = {
        "total_cases": total,
        "correct_verdicts": correct,
        "accuracy": round(correct / total * 100, 1) if total else 0,
    }
    results["total_time"] = round(time.time() - start, 2)
    logger.info(
        f"Phase 5 complete: {correct}/{total} expected verdicts "
        f"({results['summary']['accuracy']}%)"
    )
    return results


def compile_results(phase1, phase2, phase3, phase4, phase5, mode, model_name, topics):
    """Compile all results into a single JSON report."""
    report = {
        "experiment_info": {
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "mode": mode,
            "papers_dir": str(PAPERS_DIR),
            "topics": topics,
            "system": "Wizard Research — Neuro-Symbolic Agentic Gap Detection",
        },
        "phase1_ingestion": phase1,
        "phase2_fact_extraction": phase2,
        "phase3_gap_detection": phase3,
        "phase4_rule_engine": phase4,
        "phase5_adversarial": phase5,
        "overall_metrics": {},
    }

    # Compute overall metrics
    total_time = sum(
        p.get("total_time", 0)
        for p in (phase1, phase2, phase3, phase4, phase5)
        if p
    )

    total_indicators = sum(
        t.get("total_indicators", 0)
        for t in phase3.get("topics", [])
        if "error" not in t
    )

    all_confidences = []
    all_adjusted = []
    for t in phase3.get("topics", []):
        if "error" not in t:
            all_confidences.extend(t.get("confidence_scores", []))
            all_adjusted.extend(
                i.get("adjusted_confidence", i.get("confidence", 0))
                for i in t.get("indicators", [])
            )

    summary4 = (phase4 or {}).get("summary", {})
    flag_rate = summary4.get("flag_rate", 0)
    reject_rate = summary4.get("reject_rate", 0)

    report["overall_metrics"] = {
        "total_pipeline_time_seconds": round(total_time, 2),
        "papers_processed": len([p for p in phase1.get("papers", []) if "error" not in p]),
        "total_chunks_ingested": phase1.get("total_chunks", 0),
        "total_facts_extracted": phase2.get("total_facts", 0),
        "total_gap_indicators": total_indicators,
        "topics_analyzed": len([t for t in phase3.get("topics", []) if "error" not in t]),
        "avg_confidence": round(sum(all_confidences) / len(all_confidences), 3) if all_confidences else 0,
        "avg_adjusted_confidence": round(sum(all_adjusted) / len(all_adjusted), 3) if all_adjusted else 0,
        "rule_engine_pass_rate": summary4.get("pass_rate", 0),
        "rule_engine_flag_rate": flag_rate,
        "rule_engine_reject_rate": reject_rate,
        # RERR (Rule Engine Rejection Rate) — share of LLM output not passed cleanly
        "rule_engine_rejection_rate_RERR": round(flag_rate + reject_rate, 1),
        "adversarial_accuracy": (phase5 or {}).get("summary", {}).get("accuracy"),
    }

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Wizard Research experiment runner (with ablation modes)"
    )
    parser.add_argument(
        "--model", default=None,
        help="Ollama model name (default: OLLAMA_MODEL env or config)",
    )
    parser.add_argument(
        "--mode", default="full",
        choices=["full", "no-rule-engine", "linear-baseline"],
        help="Experiment mode: full pipeline, ablation without rule engine (H7), or linear RAG+LLM baseline (H6)",
    )
    parser.add_argument(
        "--topics", default=None,
        help="Comma-separated topic keys to run (e.g. T1,T4). Default: all from manifest",
    )
    parser.add_argument(
        "--custom-topic", action="append", default=None,
        help='Extra topic as "KEY:query" — e.g. negative control: '
             '--custom-topic "TC:quantum biology in marine ecosystems"',
    )
    parser.add_argument(
        "--output", default=None,
        help="Output JSON filename (default: experiment_<mode>_<model>.json)",
    )
    parser.add_argument(
        "--fresh-db", action="store_true",
        help="Clear the experiment vector store before ingestion",
    )
    parser.add_argument(
        "--skip-ingest", action="store_true",
        help="Skip Phase 1 (reuse already-ingested chunks)",
    )
    parser.add_argument(
        "--nli", action="store_true",
        help="Enable the dedicated NLI cross-encoder model (independent contradiction signal)",
    )
    args = parser.parse_args()

    model_name = args.model or os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
    topics = load_topics(args.topics, custom_topics=args.custom_topic)

    logger.info("🧙 Wizard Research — Experiment Runner")
    logger.info(f"Model : {model_name}")
    logger.info(f"Mode  : {args.mode}")
    logger.info(f"Topics: {list(topics.keys())}")
    logger.info(f"Papers: {PAPERS_DIR}")
    logger.info(f"Output: {RESULTS_DIR}")
    logger.info("")

    # Test Ollama connection
    import requests
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        if model_name not in models:
            logger.warning(f"Model '{model_name}' not in available models: {models}")
        logger.info(f"Ollama OK — {len(models)} models available")
    except Exception as e:
        logger.error(f"Ollama not reachable: {e}")
        logger.error("Please start Ollama first: ollama serve")
        sys.exit(1)

    # Initialize components
    logger.info("Initializing pipeline components...")
    components = init_components(
        model_name=model_name, mode=args.mode, fresh_db=args.fresh_db,
        use_nli=args.nli,
    )
    logger.info("Components ready.\n")

    # --- Phase 1: ingestion (shared by all modes) ---
    if args.skip_ingest:
        logger.info("PHASE 1 skipped (--skip-ingest); reusing existing chunks")
        existing = components["vector_store"].count()
        if existing == 0:
            logger.error("--skip-ingest used but the experiment vector store is empty. "
                         "Run once without --skip-ingest first.")
            sys.exit(1)
        # Phase 2 still needs the paper list — rebuild it from the manifest
        papers_list = []
        if MANIFEST_PATH.exists():
            manifest = json.loads(MANIFEST_PATH.read_text())
            papers_list = [
                {"filename": p["file"], "title": p["title"]}
                for p in manifest.get("papers", [])
                if (PAPERS_DIR / p["file"]).exists()
            ]
        else:
            papers_list = [{"filename": f.name, "title": f.stem} for f in sorted(PAPERS_DIR.glob("*.pdf"))]
        phase1_results = {
            "papers": papers_list, "total_chunks": 0, "total_chars": 0,
            "total_time": 0, "skipped": True,
            "vector_store_count": existing,
        }
        logger.info(f"Reusing {existing} chunks; {len(papers_list)} papers from manifest")
    else:
        phase1_results = phase1_ingest_papers(components)

    # --- Phase 2: fact extraction (not used by the linear baseline) ---
    if args.mode == "linear-baseline":
        logger.info("PHASE 2 skipped (linear baseline has no fact base)")
        phase2_results = {"papers": [], "total_facts": 0, "total_time": 0, "skipped": True}
    else:
        phase2_results = phase2_fact_extraction(components, phase1_results["papers"])

    # --- Phase 3: gap detection (mode-dependent) ---
    if args.mode == "linear-baseline":
        phase3_results = phase3_linear_baseline(components, topics)
    else:
        phase3_results = phase3_gap_detection(components, topics)

    # --- Phase 4: rule engine aggregation (full mode only) ---
    if args.mode == "full":
        phase4_results = phase4_rule_engine_analysis(components, phase3_results)
    else:
        logger.info(f"PHASE 4 skipped (mode={args.mode})")
        phase4_results = {"summary": {}, "total_time": 0, "skipped": True}

    # --- Phase 5: adversarial rule engine validation (full mode only) ---
    if args.mode == "full":
        phase5_results = phase5_adversarial_validation()
    else:
        phase5_results = {"summary": {}, "total_time": 0, "skipped": True}

    # Compile and save
    report = compile_results(
        phase1_results, phase2_results, phase3_results,
        phase4_results, phase5_results,
        mode=args.mode, model_name=model_name, topics=topics,
    )

    model_slug = model_name.replace(":", "_").replace("/", "_")
    output_name = args.output or f"experiment_{args.mode}_{model_slug}.json"
    output_file = RESULTS_DIR / output_name
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    logger.info("")
    logger.info("=" * 60)
    logger.info("EXPERIMENT COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Results saved to: {output_file}")
    logger.info("Overall metrics:")
    for k, v in report["overall_metrics"].items():
        logger.info(f"  {k}: {v}")

    return report


if __name__ == "__main__":
    main()
