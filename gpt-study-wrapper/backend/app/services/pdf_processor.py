"""PDF processing service."""
import logging
import fitz  # PyMuPDF
import hashlib
from pathlib import Path
from typing import List, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Service for extracting and chunking PDF content."""
    
    def __init__(self, chunk_size: int = 4000, overlap: int = 200):
        """
        Initialize PDF processor.
        
        Args:
            chunk_size: Size of each text chunk in characters
            overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    async def extract_and_chunk(self, pdf_path: Path) -> Tuple[List[str], dict]:
        """
        Extract text from PDF and split into chunks.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Tuple of (chunks list, metadata dict)
        """
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Run extraction in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        chunks, metadata = await loop.run_in_executor(
            self.executor,
            self._extract_sync,
            pdf_path
        )
        
        logger.info(f"Extracted {len(chunks)} chunks from PDF")
        return chunks, metadata
    
    def _extract_sync(self, pdf_path: Path) -> Tuple[List[str], dict]:
        """Synchronous PDF extraction (runs in thread pool)."""
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            page_count = len(doc)
            
            # Extract text with page markers for citation
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                # Add page marker for later citation
                full_text += f"\n[PAGE {page_num}]\n{text}\n"
            
            doc.close()
            
            # Chunk the text
            chunks = self._chunk_text(full_text)
            
            # Metadata
            metadata = {
                "page_count": page_count,
                "total_chars": len(full_text),
                "chunk_count": len(chunks),
                "content_hash": hashlib.md5(full_text.encode()).hexdigest()
            }
            
            return chunks, metadata
        
        except Exception as e:
            logger.error(f"Error extracting PDF: {e}")
            raise
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Full text to chunk
            
        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                if last_period > self.chunk_size * 0.8:  # Only if reasonable
                    end = start + last_period + 1
            
            chunks.append(text[start:end])
            start += self.chunk_size - self.overlap
        
        return chunks
    
    def extract_metadata(self, pdf_path: Path) -> dict:
        """Extract PDF metadata without processing full content."""
        try:
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            page_count = len(doc)
            doc.close()
            
            return {
                "title": metadata.get("title", "Unknown"),
                "author": metadata.get("author", "Unknown"),
                "pages": page_count,
                "file_size_mb": pdf_path.stat().st_size / (1024 * 1024)
            }
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {"error": str(e)}
