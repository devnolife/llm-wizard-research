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
        min_chunk_length: int = 100
    ):
        """
        Initialize document processor
        
        Args:
            chunk_size: Target size for text chunks (in characters)
            chunk_overlap: Overlap between chunks
            min_chunk_length: Minimum chunk length to keep
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_length = min_chunk_length
        
        logger.info(f"DocumentProcessor initialized (chunk_size={chunk_size}, overlap={chunk_overlap})")
    
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
        
        # Create chunks
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
