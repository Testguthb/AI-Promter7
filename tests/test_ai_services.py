import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

test_dir = Path(__file__).parent
src_dir = test_dir.parent / "src"
sys.path.insert(0, str(src_dir))

from src.ai_services import GPTService, ClaudeService, AIOrchestrator

class TestGPTService:
    """Test cases for GPTService class."""
    
    @pytest.fixture
    def gpt_service(self):
        """Create GPTService instance for testing."""
        return GPTService()
    
    @pytest.mark.asyncio
    async def test_generate_outline_success(self, gpt_service):
        """Test successful outline generation."""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test outline content"
        
        with patch.object(gpt_service.client.chat.completions, 'create', return_value=mock_response) as mock_create:
            result = await gpt_service.generate_outline("Test text", "Test prompt")
            
            assert result == "Test outline content"
            mock_create.assert_called_once()
            
            # Verify the call arguments
            call_args = mock_create.call_args
            assert call_args[1]['model'] == 'gpt-4.1'
            assert len(call_args[1]['messages']) == 2
            assert "Test text" in call_args[1]['messages'][1]['content']
            assert "Test prompt" in call_args[1]['messages'][1]['content']
    
    @pytest.mark.asyncio
    async def test_generate_outline_no_custom_prompt(self, gpt_service):
        """Test outline generation without custom prompt."""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test outline content"
        
        with patch.object(gpt_service.client.chat.completions, 'create', return_value=mock_response) as mock_create:
            result = await gpt_service.generate_outline("Test text")
            
            assert result == "Test outline content"
            call_args = mock_create.call_args
            assert "No additional instructions" in call_args[1]['messages'][1]['content']
    
    @pytest.mark.asyncio
    async def test_generate_outline_api_error(self, gpt_service):
        """Test error handling for API failures."""
        with patch.object(gpt_service.client.chat.completions, 'create', side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="Failed to generate outline"):
                await gpt_service.generate_outline("Test text")

class TestClaudeService:
    """Test cases for ClaudeService class."""
    
    @pytest.fixture
    def claude_service(self):
        """Create ClaudeService instance for testing."""
        return ClaudeService()
    
    @pytest.mark.asyncio
    async def test_process_outline_success(self, claude_service):
        """Test successful outline processing."""
        mock_response = MagicMock()
        mock_response.content[0].text = "Processed text content"
        
        with patch.object(claude_service.client.messages, 'create', return_value=mock_response) as mock_create:
            result = await claude_service.process_outline("Test outline", 1000)
            
            assert result == "Processed text content"
            mock_create.assert_called_once()
            
            # Verify the call arguments
            call_args = mock_create.call_args
            assert call_args[1]['model'] == 'claude-3-5-sonnet-20241022'
            assert call_args[1]['max_tokens'] == 8000
            assert "Test outline" in call_args[1]['messages'][0]['content']
            assert "1000 characters" in call_args[1]['system']
    
    @pytest.mark.asyncio
    async def test_process_outline_with_progress_callback(self, claude_service):
        """Test outline processing with progress callback."""
        mock_response = MagicMock()
        mock_response.content[0].text = "Processed text content"
        
        progress_callback = AsyncMock()
        
        with patch.object(claude_service.client.messages, 'create', return_value=mock_response):
            result = await claude_service.process_outline(
                "Test outline", 1000, progress_callback
            )
            
            assert result == "Processed text content"
            assert progress_callback.call_count == 2
            progress_callback.assert_any_call("Starting text generation...")
            progress_callback.assert_any_call("Text generation completed!")
    
    @pytest.mark.asyncio
    async def test_process_outline_api_error(self, claude_service):
        """Test error handling for API failures."""
        with patch.object(claude_service.client.messages, 'create', side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="Failed to process text"):
                await claude_service.process_outline("Test outline")
    
    @pytest.mark.asyncio
    async def test_process_with_length_control_no_adjustment(self, claude_service):
        """Test length control when no adjustment is needed."""
        mock_response = MagicMock()
        mock_response.content[0].text = "A" * 5000  # Exactly target length
        
        progress_callback = AsyncMock()
        
        with patch.object(claude_service.client.messages, 'create', return_value=mock_response):
            result = await claude_service.process_with_length_control(
                "Test outline", 5000, progress_callback
            )
            
            assert len(result) == 5000
            # Should not call adjustment
            assert progress_callback.call_count == 2
    
    @pytest.mark.asyncio
    async def test_process_with_length_control_with_adjustment(self, claude_service):
        """Test length control when adjustment is needed."""
        # First call returns text that's too short
        mock_response1 = MagicMock()
        mock_response1.content[0].text = "A" * 1000  # Too short
        
        # Second call (adjustment) returns better length
        mock_response2 = MagicMock()
        mock_response2.content[0].text = "B" * 4800  # Close to target
        
        progress_callback = AsyncMock()
        
        with patch.object(claude_service.client.messages, 'create', side_effect=[mock_response1, mock_response2]):
            result = await claude_service.process_with_length_control(
                "Test outline", 5000, progress_callback
            )
            
            assert len(result) == 4800
            assert progress_callback.call_count == 4  # 2 for initial + 2 for adjustment
    
    @pytest.mark.asyncio
    async def test_process_with_length_control_adjustment_fails(self, claude_service):
        """Test length control when adjustment fails."""
        mock_response1 = MagicMock()
        mock_response1.content[0].text = "A" * 1000  # Too short
        
        progress_callback = AsyncMock()
        
        with patch.object(claude_service.client.messages, 'create', side_effect=[
            mock_response1, 
            Exception("Adjustment failed")
        ]):
            result = await claude_service.process_with_length_control(
                "Test outline", 5000, progress_callback
            )
            
            # Should return original result when adjustment fails
            assert len(result) == 1000

class TestAIOrchestrator:
    """Test cases for AIOrchestrator class."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create AIOrchestrator instance for testing."""
        return AIOrchestrator()
    
    @pytest.mark.asyncio
    async def test_process_text_workflow_success(self, orchestrator):
        """Test successful complete workflow."""
        # Mock GPT service
        with patch.object(orchestrator.gpt_service, 'generate_outline', return_value="Test outline") as mock_gpt:
            # Mock Claude service
            with patch.object(orchestrator.claude_service, 'process_with_length_control', return_value="Final text") as mock_claude:
                progress_callback = AsyncMock()
                
                result = await orchestrator.process_text_workflow(
                    "Test text", "Test prompt", 3000, progress_callback
                )
                
                assert result == {
                    "outline": "Test outline",
                    "final_text": "Final text",
                    "final_length": len("Final text")
                }
                
                mock_gpt.assert_called_once_with("Test text", "Test prompt")
                mock_claude.assert_called_once_with("Test outline", 3000, progress_callback)
                
                # Verify progress callbacks
                assert progress_callback.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_process_text_workflow_gpt_failure(self, orchestrator):
        """Test workflow failure at GPT stage."""
        with patch.object(orchestrator.gpt_service, 'generate_outline', side_effect=Exception("GPT Error")):
            with pytest.raises(Exception, match="Workflow failed"):
                await orchestrator.process_text_workflow("Test text")
    
    @pytest.mark.asyncio
    async def test_process_text_workflow_claude_failure(self, orchestrator):
        """Test workflow failure at Claude stage."""
        with patch.object(orchestrator.gpt_service, 'generate_outline', return_value="Test outline"):
            with patch.object(orchestrator.claude_service, 'process_with_length_control', side_effect=Exception("Claude Error")):
                with pytest.raises(Exception, match="Workflow failed"):
                    await orchestrator.process_text_workflow("Test text")
    
    @pytest.mark.asyncio
    async def test_process_text_workflow_default_parameters(self, orchestrator):
        """Test workflow with default parameters."""
        with patch.object(orchestrator.gpt_service, 'generate_outline', return_value="Test outline") as mock_gpt:
            with patch.object(orchestrator.claude_service, 'process_with_length_control', return_value="Final text") as mock_claude:
                
                result = await orchestrator.process_text_workflow("Test text")
                
                mock_gpt.assert_called_once_with("Test text", "")
                mock_claude.assert_called_once_with("Test outline", 5000, None)