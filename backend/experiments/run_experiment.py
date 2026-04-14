#!/usr/bin/env python3
"""
Experiment Runner — Wizard Research System
Runs the full Neuro-Symbolic Agentic pipeline on sample papers and collects metrics.

Usage:
    cd backend
    OLLAMA_MODEL=llama3.2:latest python experiments/run_experiment.py
"""

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

# Force Ollama model (override default glm-4.6:cloud)
if "OLLAMA_MODEL" not in os.environ:
    os.environ["OLLAMA_MODEL"] = "llama3.2:latest"

from app.utils.config_loader import get_config
from app.utils.document_processor import DocumentProcessor
from app.core.retrieval.vector_store import VectorStore, Document
from app.services.llm_service import GLMInterface, ModelConfig
from app.core.knowledge.fact_table import FactTable
from app.core.knowledge.fact_extractor import FactExtractor
from app.core.validation.rule_engine import RuleEngine
from app.core.validation.relation_classifier import RelationClassifier
from app.core.knowledge_graph.graph_builder import KnowledgeGraphBuilder
from app.core.gap_detection.analyzer import GapAnalyzer

from loguru import logger

# --- Configuration ---
PAPERS_DIR = PROJECT_DIR / "research_papers"
RESULTS_DIR = BACKEND_DIR / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

EXPERIMENT_TOPICS = [
    "deep learning architectures and optimization techniques",
    "computer vision object detection and image recognition",
    "natural language processing and attention mechanisms",
]


def init_components():
    """Initialize all pipeline components."""
    config = get_config()

    logger.info(f"Using LLM model: {os.environ.get('OLLAMA_MODEL', config.llm.model_name)}")

    # Use a separate collection for experiments
    vector_store = VectorStore(
        persist_directory=str(PROJECT_DIR / "chroma_db_experiment"),
        collection_name="experiment_papers",
        embedding_model=config.vector_db.embedding_model,
    )

    model_cfg = ModelConfig(
        model_name=os.environ.get("OLLAMA_MODEL", config.llm.model_name),
        base_url=config.llm.base_url,
        temperature=0.3,  # Lower for reproducibility
        max_tokens=2048,
    )
    llm = GLMInterface(model_cfg)

    fact_table = FactTable()
    fact_extractor = FactExtractor(llm_interface=llm)
    rule_engine = RuleEngine(fact_table=fact_table)
    relation_classifier = RelationClassifier(llm_interface=llm)
    kg_builder = KnowledgeGraphBuilder()
    doc_processor = DocumentProcessor(chunk_size=512, chunk_overlap=50)

    gap_analyzer = GapAnalyzer(
        vector_store=vector_store,
        knowledge_graph=kg_builder,
        llm_interface=llm,
        fact_table=fact_table,
        relation_classifier=relation_classifier,
        rule_engine=rule_engine,
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

            # Sample facts from fact_table
            all_triples = getattr(fact_table, 'triples', [])
            paper_triples = [t for t in all_triples if getattr(t, 'source_id', '') == paper["filename"]]
            for triple in paper_triples[:5]:
                try:
                    fact_info["facts_sample"].append({
                        "subject": str(getattr(triple, 'subject', '')),
                        "predicate": str(getattr(triple, 'predicate', '')),
                        "object": str(getattr(triple, 'object_entity', getattr(triple, 'object', ''))),
                        "confidence": float(getattr(triple, 'confidence', 0.0)),
                    })
                except Exception:
                    fact_info["facts_sample"].append({"raw": str(triple)})

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
        ft = components["fact_table"]
        results["fact_table_stats"] = {
            "total_triples": len(ft.triples) if hasattr(ft, 'triples') else 0,
        }
    except Exception:
        results["fact_table_stats"] = {}

    logger.info(
        f"Phase 2 complete: {results['total_facts']} facts extracted "
        f"in {results['total_time']}s"
    )
    return results


def phase3_gap_detection(components):
    """Phase 3: Run gap detection for each topic."""
    logger.info("=" * 60)
    logger.info("PHASE 3: Gap Detection")
    logger.info("=" * 60)

    gap_analyzer = components["gap_analyzer"]
    vector_store = components["vector_store"]
    results = {"topics": []}
    start = time.time()

    for topic in EXPERIMENT_TOPICS:
        topic_start = time.time()
        logger.info(f"Analyzing topic: {topic}")

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

                topic_result["indicators"].append({
                    "type": ind_type,
                    "description": str(getattr(ind, 'description', ''))[:200],
                    "confidence": conf,
                    "adjusted_confidence": float(getattr(ind, 'adjusted_confidence', conf)),
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
                "error": str(e),
                "analysis_time": round(time.time() - topic_start, 2),
            })

    results["total_time"] = round(time.time() - start, 2)
    logger.info(f"Phase 3 complete in {results['total_time']}s")
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


def compile_results(phase1, phase2, phase3, phase4):
    """Compile all results into a single JSON report."""
    report = {
        "experiment_info": {
            "timestamp": datetime.now().isoformat(),
            "model": os.environ.get("OLLAMA_MODEL", "unknown"),
            "papers_dir": str(PAPERS_DIR),
            "topics": EXPERIMENT_TOPICS,
            "system": "Wizard Research — Neuro-Symbolic Agentic Gap Detection",
        },
        "phase1_ingestion": phase1,
        "phase2_fact_extraction": phase2,
        "phase3_gap_detection": phase3,
        "phase4_rule_engine": phase4,
        "overall_metrics": {},
    }

    # Compute overall metrics
    total_time = (
        phase1.get("total_time", 0)
        + phase2.get("total_time", 0)
        + phase3.get("total_time", 0)
        + phase4.get("total_time", 0)
    )

    total_indicators = sum(
        t.get("total_indicators", 0)
        for t in phase3.get("topics", [])
        if "error" not in t
    )

    all_confidences = []
    for t in phase3.get("topics", []):
        if "error" not in t:
            all_confidences.extend(t.get("confidence_scores", []))

    report["overall_metrics"] = {
        "total_pipeline_time_seconds": round(total_time, 2),
        "papers_processed": len([p for p in phase1.get("papers", []) if "error" not in p]),
        "total_chunks_ingested": phase1.get("total_chunks", 0),
        "total_facts_extracted": phase2.get("total_facts", 0),
        "total_gap_indicators": total_indicators,
        "topics_analyzed": len([t for t in phase3.get("topics", []) if "error" not in t]),
        "avg_confidence": round(sum(all_confidences) / len(all_confidences), 3) if all_confidences else 0,
        "rule_engine_pass_rate": phase4.get("summary", {}).get("pass_rate", 0),
        "rule_engine_reject_rate": phase4.get("summary", {}).get("reject_rate", 0),
    }

    return report


def main():
    logger.info("🧙 Wizard Research — Experiment Runner")
    logger.info(f"Model: {os.environ.get('OLLAMA_MODEL', 'default')}")
    logger.info(f"Papers: {PAPERS_DIR}")
    logger.info(f"Output: {RESULTS_DIR}")
    logger.info("")

    # Test Ollama connection
    import requests
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        target = os.environ.get("OLLAMA_MODEL", "")
        if target and target not in models:
            logger.warning(f"Model '{target}' not in available models: {models}")
        logger.info(f"Ollama OK — {len(models)} models available")
    except Exception as e:
        logger.error(f"Ollama not reachable: {e}")
        logger.error("Please start Ollama first: ollama serve")
        sys.exit(1)

    # Initialize components
    logger.info("Initializing pipeline components...")
    components = init_components()
    logger.info("Components ready.\n")

    # Run phases
    phase1_results = phase1_ingest_papers(components)
    phase2_results = phase2_fact_extraction(components, phase1_results["papers"])
    phase3_results = phase3_gap_detection(components)
    phase4_results = phase4_rule_engine_analysis(components, phase3_results)

    # Compile and save
    report = compile_results(phase1_results, phase2_results, phase3_results, phase4_results)

    output_file = RESULTS_DIR / "experiment_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    logger.info("")
    logger.info("=" * 60)
    logger.info("EXPERIMENT COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Results saved to: {output_file}")
    logger.info(f"Overall metrics:")
    for k, v in report["overall_metrics"].items():
        logger.info(f"  {k}: {v}")

    return report


if __name__ == "__main__":
    main()
