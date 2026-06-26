"""
Document Processor for Research Papers

Handles PDF parsing, text extraction, chunking, and metadata extraction.
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import hashlib

try:
    from pypdf import PdfReader
except ImportError:
    raise ImportError("pypdf not installed. Run: pip install pypdf")

from loguru import logger


@dataclass
class DocumentChunk:
    """Represents a chunk of a document"""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    chunk_index: int
    total_chunks: int


@dataclass
class ProcessedDocument:
    """Represents a fully processed document"""
    doc_id: str
    title: str
    content: str
    chunks: List[DocumentChunk]
    metadata: Dict[str, Any]


class DocumentProcessor:
    """
    Processes research papers for RAG pipeline
    
    Features:
    - PDF text extraction
    - Intelligent text chunking with overlap
    - Metadata extraction (title, authors, abstract)
    - Text preprocessing and cleaning
    - Citation extraction
    """
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        min_chunk_length: int = 100,
        chunk_strategy: str = "sections"
    ):
        """
        Initialize document processor
        
        Args:
            chunk_size: Target size for text chunks (in characters)
            chunk_overlap: Overlap between chunks
            min_chunk_length: Minimum chunk length to keep
            chunk_strategy: "sections" (section-aware, default) or "fixed"
                (legacy sliding-window). Section-aware chunking tags each chunk
                with its source section (Introduction, Methods, Limitations, …),
                enabling section-targeted retrieval and better weakness grounding.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_length = min_chunk_length
        self.chunk_strategy = chunk_strategy
        
        logger.info(
            f"DocumentProcessor initialized (chunk_size={chunk_size}, "
            f"overlap={chunk_overlap}, strategy={chunk_strategy})"
        )
    
    def process_pdf(
        self,
        pdf_path: str,
        extract_metadata: bool = True
    ) -> ProcessedDocument:
        """
        Process a PDF file
        
        Args:
            pdf_path: Path to PDF file
            extract_metadata: Whether to extract metadata from content
            
        Returns:
            ProcessedDocument object
        """
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Extract text from PDF
        text = self._extract_text_from_pdf(pdf_path)
        
        # Generate document ID from file path
        doc_id = self._generate_doc_id(pdf_path)
        
        # Extract metadata
        metadata = {}
        title = Path(pdf_path).stem  # Default to filename
        
        if extract_metadata:
            metadata = self._extract_metadata(text)
            title = metadata.get('title', title)
        
        # Add file metadata
        metadata.update({
            'source': pdf_path,
            'file_name': Path(pdf_path).name,
            'doc_id': doc_id,
            'type': 'research_paper'
        })
        
        # Clean and preprocess text
        cleaned_text = self._clean_text(text)
        
        # Create chunks — section-aware by default, fixed-window as fallback.
        # Section detection runs on the RAW text because _clean_text collapses
        # the newlines that header detection relies on.
        if self.chunk_strategy == "sections":
            chunks = self._chunk_sections(text, doc_id, metadata)
            if not chunks:  # no detectable sections → fall back
                chunks = self._chunk_text(cleaned_text, doc_id, metadata)
        else:
            chunks = self._chunk_text(cleaned_text, doc_id, metadata)
        
        logger.info(f"Processed document: {title} ({len(chunks)} chunks)")
        
        return ProcessedDocument(
            doc_id=doc_id,
            title=title,
            content=cleaned_text,
            chunks=chunks,
            metadata=metadata
        )
    
    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            reader = PdfReader(pdf_path)
            text_parts = []
            
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
            
            full_text = "\n\n".join(text_parts)
            logger.info(f"Extracted {len(full_text)} characters from {len(reader.pages)} pages")
            
            return full_text
        except Exception as e:
            logger.error(f"Failed to read PDF {pdf_path}: {e}")
            raise
    
    def _extract_metadata(self, text: str) -> Dict[str, Any]:
        """
        Extract metadata from document text
        
        Extracts:
        - Title (first line or largest heading)
        - Abstract
        - Authors
        - Keywords
        - Year
        """
        metadata = {}
        
        # Extract title (usually first significant line)
        lines = text.split('\n')
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            if len(line) > 20 and len(line) < 200:
                metadata['title'] = line
                break
        
        # Extract abstract
        abstract_match = re.search(
            r'(?:Abstract|ABSTRACT)[\s:]*\n(.*?)(?:\n\n|\n[A-Z][a-z]+:)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        if abstract_match:
            metadata['abstract'] = abstract_match.group(1).strip()[:500]
        
        # Extract year
        year_match = re.search(r'\b(19|20)\d{2}\b', text[:2000])
        if year_match:
            metadata['year'] = int(year_match.group(0))
        
        # Extract keywords
        keywords_match = re.search(
            r'(?:Keywords|Index Terms)[\s:]*\n(.*?)(?:\n\n)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        if keywords_match:
            keywords_text = keywords_match.group(1).strip()
            keywords = [k.strip() for k in re.split(r'[,;]', keywords_text)]
            metadata['keywords'] = keywords[:10]
        
        # Extract authors (simple pattern)
        author_section = text[:1000]
        author_match = re.search(
            r'(?:Authors?|By)[\s:]*\n(.*?)(?:\n\n)',
            author_section,
            re.DOTALL | re.IGNORECASE
        )
        if author_match:
            authors_text = author_match.group(1).strip()
            # Simple comma/and separation
            authors = [a.strip() for a in re.split(r',| and ', authors_text)]
            metadata['authors'] = authors[:10]
        
        return metadata
    
    def _clean_text(self, text: str) -> str:
        """Clean and preprocess text"""
        # Remove multiple whitespaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers (common patterns)
        text = re.sub(r'\n\d+\n', '\n', text)
        
        # Remove common PDF artifacts
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Remove non-ASCII
        
        # Normalize line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove extra spaces
        text = text.strip()
        
        return text
    
    # Section keywords (English + Indonesian) used to recognise headers.
    _SECTION_KEYWORDS = [
        "abstract", "abstrak", "introduction", "pendahuluan", "background",
        "related work", "literature review", "tinjauan pustaka", "landasan teori",
        "method", "methods", "methodology", "metode", "metodologi",
        "materials and methods", "approach", "proposed", "model", "experiment",
        "experiments", "experimental", "eksperimen", "evaluation", "evaluasi",
        "result", "results", "hasil", "hasil dan pembahasan", "findings",
        "discussion", "pembahasan", "analysis", "analisis",
        "conclusion", "conclusions", "kesimpulan", "penutup",
        "limitation", "limitations", "keterbatasan", "future work",
        "acknowledgment", "acknowledgments", "acknowledgement",
        "references", "daftar pustaka", "bibliography", "appendix", "lampiran",
    ]

    def _detect_sections(self, text: str) -> List[Tuple[str, str]]:
        """
        Split a paper into (section_title, section_text) pairs.

        Recognises three common header shapes, line by line:
          - numbered: ``3 Model Architecture``, ``3.1 Results``, ``IV. Method``
          - keyword headers: a short line whose start matches a known section
            keyword (English or Indonesian)
          - ALL-CAPS headers: a short upper-case line (e.g. ``INTRODUCTION``)

        Returns an empty list when no headers are found, so the caller can fall
        back to fixed-window chunking.
        """
        lines = text.split("\n")
        # Header detectors
        numbered = re.compile(
            r"^\s*((\d{1,2}(\.\d{1,2})*)|([IVXLC]{1,5}))[\.\)]?\s+([A-Z][\w].{0,48})$"
        )
        keyword_re = re.compile(
            r"^\s*(\d{1,2}[\.\)]?\s+)?(" + "|".join(
                re.escape(k) for k in self._SECTION_KEYWORDS
            ) + r")\b", re.IGNORECASE
        )

        boundaries: List[Tuple[int, str]] = []  # (line_index, title)
        for i, raw in enumerate(lines):
            line = raw.strip()
            if not line or len(line) > 60:
                continue
            is_header = False
            if numbered.match(line):
                is_header = True
            elif keyword_re.match(line) and len(line.split()) <= 7:
                is_header = True
            elif (
                line.isupper() and 3 <= len(line) <= 40
                and any(c.isalpha() for c in line)
                and (" " in line.strip() or line.lower() in self._SECTION_KEYWORDS)
            ):
                # Multi-word ALL-CAPS (e.g. "RELATED WORK") or a known keyword;
                # excludes single-token caps noise like table labels "NERMNLI".
                is_header = True
            if is_header:
                boundaries.append((i, line))

        if len(boundaries) < 2:
            return []

        sections: List[Tuple[str, str]] = []
        for idx, (line_no, title) in enumerate(boundaries):
            end_line = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(lines)
            body = "\n".join(lines[line_no + 1:end_line]).strip()
            if body:
                sections.append((title, body))
        return sections

    def _chunk_sections(
        self,
        text: str,
        doc_id: str,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """
        Section-aware chunking.

        Splits the document into sections, then within each section emits
        sliding-window sub-chunks (so embeddings stay focused) — each tagged
        with its ``section`` title. Falls back to an empty list when no sections
        are detected so ``process_pdf`` can use fixed-window chunking instead.
        """
        sections = self._detect_sections(text)
        if not sections:
            return []

        chunks: List[DocumentChunk] = []
        chunk_index = 0
        stride = max(1, self.chunk_size - self.chunk_overlap)

        for section_title, raw_body in sections:
            # The section body comes from RAW text; normalise whitespace here so
            # chunks read cleanly while header detection still saw the newlines.
            body = re.sub(r"\s+", " ", raw_body).strip()
            start = 0
            blen = len(body)
            while start < blen:
                end = min(start + self.chunk_size, blen)
                piece = body[start:end]
                # Break on a sentence boundary near the end when possible.
                if end < blen:
                    last_period = piece.rfind(". ", max(0, len(piece) - 100))
                    if last_period > 0:
                        piece = piece[:last_period + 1]
                        end = start + last_period + 1
                if len(piece.strip()) >= self.min_chunk_length or (
                    not chunks and end >= blen
                ):
                    chunk_id = f"{doc_id}_chunk_{chunk_index}"
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        "chunk_id": chunk_id,
                        "chunk_index": chunk_index,
                        "section": section_title,
                    })
                    chunks.append(DocumentChunk(
                        chunk_id=chunk_id,
                        content=piece.strip(),
                        metadata=chunk_metadata,
                        chunk_index=chunk_index,
                        total_chunks=0,
                    ))
                    chunk_index += 1
                start += stride

        for chunk in chunks:
            chunk.total_chunks = len(chunks)
        return chunks

    def _chunk_text(
        self,
        text: str,
        doc_id: str,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """
        Split text into overlapping chunks
        
        Uses sliding window approach with overlap to maintain context.
        """
        chunks = []
        text_length = len(text)
        
        # Calculate number of chunks
        stride = self.chunk_size - self.chunk_overlap
        num_chunks = max(1, (text_length - self.chunk_overlap) // stride + 1)
        
        start = 0
        chunk_index = 0
        
        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            
            # Extract chunk
            chunk_text = text[start:end]
            
            # Try to break at sentence boundary
            if end < text_length:
                # Look for sentence ending within last 100 chars
                last_period = chunk_text.rfind('. ', max(0, len(chunk_text) - 100))
                if last_period > 0:
                    chunk_text = chunk_text[:last_period + 1]
                    end = start + last_period + 1
            
            # Skip very short chunks
            if len(chunk_text.strip()) < self.min_chunk_length:
                start += stride
                continue
            
            # Create chunk
            chunk_id = f"{doc_id}_chunk_{chunk_index}"
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                'chunk_id': chunk_id,
                'chunk_index': chunk_index,
                'start_char': start,
                'end_char': end
            })
            
            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                content=chunk_text.strip(),
                metadata=chunk_metadata,
                chunk_index=chunk_index,
                total_chunks=num_chunks
            ))
            
            chunk_index += 1
            start += stride
        
        # Update total chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)
        
        return chunks
    
    def _generate_doc_id(self, file_path: str) -> str:
        """Generate unique document ID from file path"""
        file_path_normalized = os.path.normpath(file_path)
        hash_object = hashlib.md5(file_path_normalized.encode())
        return hash_object.hexdigest()[:16]
    
    def process_directory(
        self,
        directory: str,
        recursive: bool = True,
        file_pattern: str = "*.pdf"
    ) -> List[ProcessedDocument]:
        """
        Process all PDF files in a directory
        
        Args:
            directory: Directory path
            recursive: Whether to process subdirectories
            file_pattern: File pattern to match
            
        Returns:
            List of ProcessedDocument objects
        """
        logger.info(f"Processing directory: {directory}")
        
        path = Path(directory)
        if recursive:
            pdf_files = list(path.rglob(file_pattern))
        else:
            pdf_files = list(path.glob(file_pattern))
        
        logger.info(f"Found {len(pdf_files)} PDF files")
        
        processed_docs = []
        for pdf_file in pdf_files:
            try:
                doc = self.process_pdf(str(pdf_file))
                processed_docs.append(doc)
            except Exception as e:
                logger.error(f"Failed to process {pdf_file}: {e}")
        
        logger.info(f"Successfully processed {len(processed_docs)} documents")
        return processed_docs
    
    def extract_citations(self, text: str) -> List[str]:
        """
        Extract citation references from text
        
        Args:
            text: Document text
            
        Returns:
            List of citation references
        """
        citations = []
        
        # Pattern 1: [1], [2], etc.
        numeric_citations = re.findall(r'\[(\d+)\]', text)
        citations.extend([f"[{c}]" for c in numeric_citations])
        
        # Pattern 2: (Author, Year)
        author_year_citations = re.findall(
            r'\(([A-Z][a-z]+(?:\s+et\s+al\.)?),?\s+(\d{4})\)',
            text
        )
        citations.extend([f"({a}, {y})" for a, y in author_year_citations])
        
        # Remove duplicates while preserving order
        unique_citations = []
        seen = set()
        for cit in citations:
            if cit not in seen:
                unique_citations.append(cit)
                seen.add(cit)
        
        return unique_citations[:50]  # Limit to 50 citations
    
    def extract_weakness_sections(self, full_text: str, max_chars: int = 4000) -> str:
        """
        Extract the parts of a paper where authors actually state weaknesses.

        Real, explicit limitations live in sections like *Limitations*,
        *Future Work*, *Threats to Validity*, *Discussion* and *Conclusion* —
        which sit at the END of a paper and are therefore missed when only the
        first N chunks (title/abstract/intro) are fed to an LLM. This method
        locates those sections and returns their text so weakness analysis can
        be grounded in evidence rather than guesswork.

        Strategy:
          - High-precision headers (limitation/future work/threats to validity)
            are captured wherever they occur.
          - Generic headers (conclusion/discussion) are only captured in the
            latter part of the document, to avoid matching an intro's
            "we discuss…" or "in conclusion" phrasing.
          - Falls back to the document tail when no headers are found.

        Args:
            full_text: The full cleaned paper text.
            max_chars: Maximum length of the returned context.

        Returns:
            Concatenated weakness-bearing sections (or the document tail).
        """
        if not full_text:
            return ""

        text = full_text
        lower = text.lower()
        n = len(text)
        latter_start = int(n * 0.4)

        precise = ["limitation", "future work", "future research",
                   "threats to validity", "shortcoming", "drawback"]
        generic = ["conclusion", "concluding remarks", "discussion"]

        windows: List[Tuple[int, str]] = []
        for kw in precise:
            for m in re.finditer(re.escape(kw), lower):
                start = m.start()
                windows.append((start, text[start:start + 1500]))
        for kw in generic:
            for m in re.finditer(re.escape(kw), lower):
                start = m.start()
                if start >= latter_start:  # only trust generic headers late in the doc
                    windows.append((start, text[start:start + 1200]))

        if not windows:
            # No recognizable sections — fall back to the tail of the paper,
            # where conclusions/limitations usually live.
            return text[-max_chars:].strip()

        # Merge in document order, skipping overlapping windows.
        windows.sort(key=lambda w: w[0])
        collected: List[str] = []
        consumed_until = -1
        total = 0
        for start, chunk in windows:
            if start < consumed_until:
                continue
            collected.append(chunk.strip())
            consumed_until = start + len(chunk)
            total += len(chunk)
            if total >= max_chars:
                break

        return "\n...\n".join(collected)[:max_chars].strip()

    def chunk_by_sections(
        self,
        text: str,
        doc_id: str,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """
        Alternative chunking strategy: split by document sections
        
        Args:
            text: Document text
            doc_id: Document ID
            metadata: Document metadata
            
        Returns:
            List of DocumentChunk objects
        """
        # Common section headers in research papers
        section_pattern = r'\n([A-Z][A-Z\s]+)\n'
        
        # Find section boundaries
        sections = re.split(section_pattern, text)
        
        chunks = []
        chunk_index = 0
        
        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                section_title = sections[i].strip()
                section_content = sections[i + 1].strip()
                
                if len(section_content) < self.min_chunk_length:
                    continue
                
                chunk_id = f"{doc_id}_section_{chunk_index}"
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    'chunk_id': chunk_id,
                    'section': section_title,
                    'chunk_index': chunk_index
                })
                
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    content=section_content,
                    metadata=chunk_metadata,
                    chunk_index=chunk_index,
                    total_chunks=0  # Will be updated later
                ))
                
                chunk_index += 1
        
        # Update total chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)
        
        return chunks


# Example usage
if __name__ == "__main__":
    processor = DocumentProcessor(chunk_size=512, chunk_overlap=50)
    
    # Process a single PDF
    # doc = processor.process_pdf("path/to/paper.pdf")
    # print(f"Document: {doc.title}")
    # print(f"Chunks: {len(doc.chunks)}")
    
    # Process directory
    # docs = processor.process_directory("./data/raw")
    # print(f"Processed {len(docs)} documents")
    
    print("DocumentProcessor ready for use")
