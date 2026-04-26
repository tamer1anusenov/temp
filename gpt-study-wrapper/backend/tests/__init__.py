"""
Integration tests for GPT Study Wrapper API.
Run with: pytest backend/tests/
"""
import pytest
import asyncio
from pathlib import Path
import tempfile
from app.services.pdf_processor import PDFProcessor
from app.services.llm_service import LLMService
from app.cache.cache_service import CacheService


class TestPDFProcessor:
    """Test PDF processing functionality."""
    
    @pytest.fixture
    def processor(self):
        return PDFProcessor(chunk_size=1000, overlap=100)
    
    def test_chunk_text(self, processor):
        """Test text chunking."""
        text = "a" * 5000
        chunks = processor._chunk_text(text)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 1200 for chunk in chunks)  # Some overlap
    
    def test_metadata_extraction(self, processor):
        """Test metadata extraction (if PDF available)."""
        # Would need actual PDF file
        pass


class TestLLMService:
    """Test LLM service."""
    
    @pytest.fixture
    def llm_service(self):
        return LLMService()
    
    def test_system_prompts_exist(self, llm_service):
        """Test all system prompts are defined."""
        for analysis_type in ["comprehensive", "patterns", "questions", "marks_distribution"]:
            prompt = llm_service.get_system_prompt(analysis_type)
            assert prompt
            assert len(prompt) > 50
    
    def test_get_system_prompt_default(self, llm_service):
        """Test default system prompt."""
        prompt = llm_service.get_system_prompt("unknown")
        assert prompt  # Should return comprehensive as default


class TestCacheService:
    """Test caching functionality."""
    
    @pytest.fixture
    async def cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield CacheService(cache_dir=tmpdir)
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self, cache):
        """Test cache set and get."""
        await cache.set("hash1", "prompt1", "type1", "response1")
        result = await cache.get("hash1", "prompt1", "type1")
        assert result == "response1"
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        """Test cache miss."""
        result = await cache.get("missing", "prompt", "type")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
