"""API routes for PDF analysis and chat."""
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pathlib import Path
import tempfile
from typing import AsyncGenerator
import asyncio

from app.models.schemas import AnalyzeRequest, StreamingResponse as StreamingResponseModel
from app.services.pdf_processor import PDFProcessor
from app.services.llm_service import LLMService
from app.cache.cache_service import CacheService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])

# Singleton instances
pdf_processor = PDFProcessor(
    chunk_size=settings.pdf_chunk_size,
    overlap=settings.pdf_chunk_overlap
)
llm_service = LLMService()
cache_service = CacheService(cache_dir=settings.cache_dir)

# In-memory session storage (use database in production)
_sessions = {}


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload and process a PDF file.
    
    Returns session ID for subsequent queries.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Check file size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    
    if size_mb > settings.pdf_max_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {settings.pdf_max_size_mb}MB"
        )
    
    try:
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        
        # Extract and chunk PDF
        chunks, metadata = await pdf_processor.extract_and_chunk(tmp_path)
        
        # Generate session ID
        import uuid
        session_id = str(uuid.uuid4())
        
        # Store session
        _sessions[session_id] = {
            "file_name": file.filename,
            "chunks": chunks,
            "metadata": metadata,
            "temp_path": str(tmp_path)
        }
        
        logger.info(f"Session {session_id} created with {len(chunks)} chunks")
        
        return {
            "session_id": session_id,
            "file_name": file.filename,
            "chunks": len(chunks),
            "metadata": metadata,
            "pages": metadata.get("page_count", 0)
        }
    
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{session_id}")
async def analyze_pdf(session_id: str, request: AnalyzeRequest):
    """Analyze PDF with optional streaming response."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _sessions[session_id]
    chunks = session["chunks"]
    metadata = session["metadata"]
    
    # Prepare context from chunks
    context = "\n\n---\n\n".join(chunks[:5])  # Use first 5 chunks for context
    
    # Build prompt with context
    full_prompt = f"""Based on the following exam papers:

{context}

---

User Question: {request.prompt}

Provide a comprehensive, structured response citing specific sections when relevant."""
    
    system_prompt = llm_service.get_system_prompt(request.analysis_type)
    
    # Check cache
    cache_key = metadata.get("content_hash", "")
    cached = await cache_service.get(
        cache_key,
        request.prompt,
        request.analysis_type,
        settings.cache_max_age_hours
    )
    
    if cached:
        return {
            "response": cached,
            "cached": True,
            "model": "cache"
        }
    
    # Get response and cache it
    response = await llm_service.get_response(full_prompt, system_prompt)
    await cache_service.set(cache_key, request.prompt, request.analysis_type, response)
    
    return {
        "response": response,
        "cached": False,
        "model": settings.primary_model
    }


@router.post("/analyze-stream/{session_id}")
async def analyze_stream(session_id: str, request: AnalyzeRequest):
    """Stream analysis response in real-time."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _sessions[session_id]
    chunks = session["chunks"]
    metadata = session["metadata"]
    
    # Prepare context
    context = "\n\n---\n\n".join(chunks[:5])
    
    full_prompt = f"""Based on the following exam papers:

{context}

---

User Question: {request.prompt}

Provide a comprehensive, structured response citing specific sections when relevant."""
    
    system_prompt = llm_service.get_system_prompt(request.analysis_type)
    
    # Check cache first
    cache_key = metadata.get("content_hash", "")
    cached = await cache_service.get(
        cache_key,
        request.prompt,
        request.analysis_type,
        settings.cache_max_age_hours
    )
    
    if cached:
        # Return cached response as stream
        async def cached_stream():
            yield cached
        
        return StreamingResponse(cached_stream(), media_type="text/plain")
    
    # Stream from LLM
    async def stream_generator() -> AsyncGenerator[str, None]:
        full_response = ""
        async for token in llm_service.stream_response(full_prompt, system_prompt):
            full_response += token
            yield token
        
        # Cache after streaming completes
        await cache_service.set(cache_key, request.prompt, request.analysis_type, full_response)
    
    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "model": settings.primary_model
    }
