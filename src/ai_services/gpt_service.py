import logging
from openai import AsyncOpenAI
from src.config.settings import OPENAI_API_KEY, GPT_MODEL

logger = logging.getLogger(__name__)


class GPTService:
    """Service for interacting with OpenAI GPT-4.1 API."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    async def generate_outline(self, text: str, custom_prompt: str = "", sample_content: str = "") -> str:
        """Generate structured outline from input text using GPT-4.1."""
        
        # Build user prompt with optional sample
        sample_section = ""
        if sample_content:
            sample_section = f"""
        
        EXAMPLE OF IDEAL OUTLINE FORMAT (use as reference for structure and quality):
        {sample_content}
        
        Use this example as a reference for the quality and format of your outline, but create a completely new outline based on the provided text.
        """
        
        user_prompt = f"""
        Original text to analyze:
        {text}
        
        Additional instructions: {custom_prompt if custom_prompt else "No additional instructions."}{sample_section}
        
        Please create a Perfect Outline based on this text.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=24000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating outline with GPT: {e}")
            raise Exception(f"Failed to generate outline: {str(e)}")