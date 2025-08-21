import asyncio
import logging
from anthropic import AsyncAnthropic
from src.config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL
from .rate_limiter import claude_rate_limiter

logger = logging.getLogger(__name__)


class ClaudeService:
    """Service for interacting with Anthropic Claude Sonnet 4 API."""
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    
    async def _make_request_with_retry(self, request_func, max_retries: int = 3):
        """Make API request with exponential backoff retry logic."""
        for attempt in range(max_retries):
            try:
                # Apply rate limiting with token estimates
                await claude_rate_limiter.acquire(estimated_input_tokens=4000, estimated_output_tokens=2000)
                
                # Make the request
                return await request_func()
                
            except Exception as e:
                error_str = str(e)
                
                if "rate_limit_error" in error_str or "429" in error_str:
                    if attempt < max_retries - 1:
                        # Exponential backoff: 10, 30, 90 seconds for rate limits
                        wait_time = 10 * (3 ** attempt)
                        logger.warning(f"Rate limit hit, retrying in {wait_time} seconds (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Rate limit exceeded after {max_retries} attempts")
                        # Don't raise exception, let queue handle it
                        raise Exception(f"Rate limit exceeded after {max_retries} attempts. Will retry later.")
                
                # For other errors, retry with shorter delay
                elif attempt < max_retries - 1:
                    wait_time = 2 * (attempt + 1)
                    logger.warning(f"API error: {error_str}. Retrying in {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise e
        
        raise Exception("Max retries exceeded")
    
    async def process_outline(self, outline: str, target_length: int = 5000, 
                            sonnet_prompt: str = "", progress_callback=None) -> str:
        """Process outline into final text using Claude Sonnet 4."""
        
        user_prompt = f"""
        Please transform this outline into a complete, well-written text:
        
        {outline}
        
        Target length: approximately {target_length} characters.
        
        {f"Additional instructions: {sonnet_prompt}" if sonnet_prompt else ""}
        """
        
        async def make_request():
            if progress_callback:
                await progress_callback("Starting text generation...")
            
            response = await self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=64000,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            generated_text = response.content[0].text
            
            if progress_callback:
                await progress_callback("Text generation completed!")
            
            return generated_text
        
        try:
            return await self._make_request_with_retry(make_request)
        except Exception as e:
            logger.error(f"Error processing with Claude: {e}")
            raise Exception(f"Failed to process text: {str(e)}")
    
    async def process_with_length_control(self, outline: str, target_length: int = 5000,
                                        sonnet_prompt: str = "", progress_callback=None) -> str:
        """Process outline with iterative length control."""
        
        # First attempt
        result = await self.process_outline(outline, target_length, sonnet_prompt, progress_callback)
        current_length = len(result)
        
        # If length is significantly different, try to adjust
        if abs(current_length - target_length) > target_length * 0.3:  # 30% tolerance
            if progress_callback:
                await progress_callback(f"Adjusting text length... Current: {current_length}, Target: {target_length}")
            
            adjustment_prompt = f"""
            Please adjust the following text to be approximately {target_length} characters.
            Current length: {current_length} characters.
            
            {'Expand and add more detail if the text is too short.' if current_length < target_length else 'Condense and make more concise if the text is too long.'}
            
            Text to adjust:
            {result}
            """
            
            async def make_adjustment_request():
                response = await self.client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=64000,
                    temperature=0.7,
                    messages=[
                        {"role": "user", "content": adjustment_prompt}
                    ]
                )
                return response.content[0].text
            
            try:
                result = await self._make_request_with_retry(make_adjustment_request)
                
                if progress_callback:
                    await progress_callback(f"Length adjustment completed! Final length: {len(result)}")
                    
            except Exception as e:
                logger.warning(f"Failed to adjust length: {e}")
                # Return original result if adjustment fails
        
        return result