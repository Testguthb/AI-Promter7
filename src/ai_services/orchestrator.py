import logging
from typing import Dict
from .gpt_service import GPTService
from .claude_service import ClaudeService

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """Orchestrates the workflow between GPT and Claude services."""
    
    def __init__(self):
        self.gpt_service = GPTService()
        self.claude_service = ClaudeService()
    
    async def generate_gpt_outline(self, text: str, custom_prompt: str = "", sample_content: str = "") -> str:
        """Generate outline using GPT service."""
        try:
            return await self.gpt_service.generate_outline(text, custom_prompt, sample_content)
        except Exception as e:
            logger.error(f"Error generating GPT outline: {e}")
            raise Exception(f"Failed to generate GPT outline: {str(e)}")
    
    async def process_text_workflow(self, text: str, custom_prompt: str = "", 
                                  target_length: int = 5000, sonnet_prompt: str = "", progress_callback=None) -> Dict[str, str]:
        """Complete workflow: GPT outline -> Claude processing."""
        
        try:
            # Step 1: Generate outline with GPT
            if progress_callback:
                await progress_callback("Generating outline with GPT-4.1...")
            
            outline = await self.gpt_service.generate_outline(text, custom_prompt)
            
            if progress_callback:
                await progress_callback("Outline generated successfully!")
            
            # Step 2: Process with Claude
            if progress_callback:
                await progress_callback("Processing text with Claude Sonnet 4...")
            
            final_text = await self.claude_service.process_with_length_control(
                outline, target_length, sonnet_prompt, progress_callback
            )
            
            return {
                "outline": outline,
                "final_text": final_text,
                "final_length": len(final_text)
            }
            
        except Exception as e:
            logger.error(f"Error in AI workflow: {e}")
            raise Exception(f"Workflow failed: {str(e)}")