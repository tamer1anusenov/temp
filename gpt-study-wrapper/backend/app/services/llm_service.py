"""LLM service using litellm with streaming and fallback logic."""
import logging
import litellm
import asyncio
from typing import AsyncGenerator, Optional, List, Dict
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure litellm
litellm.drop_params = True


class LLMService:
    """Service for interacting with LLMs via litellm."""
    
    # System prompts for different analysis types
    SYSTEM_PROMPTS = {
        "comprehensive": """You are an expert academic tutor specializing in exam preparation. Analyze the provided past papers to identify:
1. Question formats (MCQ, essay, calculation, case study)
2. Topic frequency & mark distribution
3. Common traps, ambiguous wording, or recurring patterns
4. Mark scheme expectations (step-by-step vs final answer focus)

When answering:
- Always cite which paper/chunk you're referencing [PAGE X]
- Break solutions into logical steps
- Flag assumptions or missing context
- Use markdown formatting for clarity
- Output structured sections (use markdown tables/lists)
- Stay strictly academic, no fluff
- Prioritize accuracy over creativity""",
        
        "questions": """You are an expert exam question generator. Based on the provided past papers:
1. Identify the exact question format and style
2. Match the difficulty level and mark allocation
3. Generate similar practice questions with solutions
4. Reference the original paper for comparison

Format each question with:
- Question text (matching original style)
- Mark allocation
- Suggested answer structure
- Similar examples from provided papers""",
        
        "patterns": """You are an expert at identifying examination patterns. Analyze the provided papers for:
1. Recurring question topics
2. Question format distribution
3. Difficulty progression
4. Mark allocation patterns
5. Time management insights

Provide actionable study recommendations based on patterns found.""",
        
        "marks_distribution": """You are an expert at analyzing mark schemes. Based on the provided papers:
1. Analyze mark allocation by topic
2. Identify high-value question types
3. Determine weighting patterns
4. Recommend study priorities

Show results in tabular format for clarity."""
    }
    
    def __init__(self):
        """Initialize LLM service."""
        self.primary_model = settings.primary_model
        self.fallback_model = settings.fallback_model
        self.temperature = settings.temperature
        self.max_tokens = settings.max_tokens
    
    def get_system_prompt(self, analysis_type: str = "comprehensive") -> str:
        """Get the appropriate system prompt."""
        return self.SYSTEM_PROMPTS.get(analysis_type, self.SYSTEM_PROMPTS["comprehensive"])
    
    async def stream_response(
        self,
        prompt: str,
        system_prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response from the LLM with fallback logic.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            model: Optional model override
            temperature: Optional temperature override
            max_tokens: Optional max_tokens override
            
        Yields:
            Response tokens
        """
        model = model or self.primary_model
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens or self.max_tokens
        
        try:
            async for token in self._stream_with_model(
                prompt, system_prompt, model, temperature, max_tokens
            ):
                yield token
        
        except Exception as e:
            logger.warning(f"Primary model {model} failed: {e}. Trying fallback...")
            
            # Fallback to alternate model
            try:
                async for token in self._stream_with_model(
                    prompt, system_prompt, self.fallback_model, temperature, max_tokens
                ):
                    yield token
            except Exception as fallback_error:
                logger.error(f"Fallback model also failed: {fallback_error}")
                yield f"\n\n❌ Error: Both models unavailable. {str(fallback_error)}"
    
    async def _stream_with_model(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """Stream response using specific model."""
        loop = asyncio.get_event_loop()
        
        # Run in thread pool to avoid blocking
        async def _get_stream():
            return await loop.run_in_executor(
                None,
                lambda: litellm.completion(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    api_key=settings.openrouter_api_key
                )
            )
        
        response = await _get_stream()
        
        # Stream chunks
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def get_response(
        self,
        prompt: str,
        system_prompt: str,
        model: Optional[str] = None
    ) -> str:
        """Get complete response (non-streaming)."""
        full_response = ""
        async for token in self.stream_response(prompt, system_prompt, model):
            full_response += token
        return full_response
