"""arXiv API client."""

import aiohttp
from typing import List
from loguru import logger

from .base import PaperMetadata


class ArXivAPI:
    """arXiv API client - No API key required"""
    
    BASE_URL = "http://export.arxiv.org/api/query"
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        start: int = 0
    ) -> List[PaperMetadata]:
        """
        Search arXiv papers
        
        Args:
            query: Search query (e.g., "machine learning", "ti:transformers")
            max_results: Maximum number of results
            start: Starting index for pagination
        
        Returns:
            List of paper metadata
        """
        params = {
            "search_query": query,
            "start": start,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        content = await response.text()
                        return self._parse_arxiv_response(content)
                    else:
                        logger.error(f"arXiv API error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"arXiv API request failed: {e}")
            return []
    
    def _parse_arxiv_response(self, xml_content: str) -> List[PaperMetadata]:
        """Parse arXiv XML response"""
        import xml.etree.ElementTree as ET
        
        papers = []
        root = ET.fromstring(xml_content)
        
        # Namespace for arXiv XML
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }
        
        for entry in root.findall('atom:entry', ns):
            try:
                paper_id = entry.find('atom:id', ns).text.split('/')[-1]
                title = entry.find('atom:title', ns).text.strip()
                abstract = entry.find('atom:summary', ns).text.strip()
                
                # Authors
                authors = [
                    author.find('atom:name', ns).text
                    for author in entry.findall('atom:author', ns)
                ]
                
                # Published date
                published = entry.find('atom:published', ns).text
                year = int(published.split('-')[0]) if published else None
                
                # Links
                pdf_url = None
                page_url = None
                for link in entry.findall('atom:link', ns):
                    if link.get('title') == 'pdf':
                        pdf_url = link.get('href')
                    elif link.get('rel') == 'alternate':
                        page_url = link.get('href')
                
                # Categories (keywords)
                keywords = [
                    cat.get('term')
                    for cat in entry.findall('atom:category', ns)
                ]
                
                papers.append(PaperMetadata(
                    paper_id=paper_id,
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    year=year,
                    journal="arXiv",
                    doi=None,
                    url=page_url,
                    pdf_url=pdf_url,
                    keywords=keywords,
                    source_api="arxiv"
                ))
            except Exception as e:
                logger.warning(f"Failed to parse arXiv entry: {e}")
                continue
        
        return papers
