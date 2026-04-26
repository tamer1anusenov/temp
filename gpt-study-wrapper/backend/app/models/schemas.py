"""Pydantic models for request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional, List


class AnalyzeRequest(BaseModel):
    """Request model for PDF analysis."""
    prompt: str = Field(..., description="User's question or analysis request")
    analysis_type: Optional[str] = Field(
        "comprehensive",
        description="Type of analysis: comprehensive, questions, patterns, marks_distribution"
    )


class AnalysisResult(BaseModel):
    """Response model for analysis results."""
    request_id: str
    analysis_type: str
    content: str
    cached: bool = False
    model_used: str


class PaperAnalysis(BaseModel):
    """Detailed paper analysis structure."""
    question_formats: List[str]
    topic_frequency: dict
    mark_distribution: dict
    common_patterns: List[str]
    traps_and_ambiguities: List[str]
    mark_scheme_expectations: str
    recommendations: List[str]


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    timestamp: Optional[str] = None
    references: Optional[List[str]] = None


class StreamingResponse(BaseModel):
    """Response model for streaming endpoints."""
    chunk: str
    is_final: bool = False
    model_used: str
