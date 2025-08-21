import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram import Bot
from aiogram.types import Message, Document, CallbackQuery, User, Chat
from aiogram.fsm.context import FSMContext

test_dir = Path(__file__).parent
src_dir = test_dir.parent / "src"
sys.path.insert(0, str(src_dir))

from src.bot.states import ProcessingStates
from src.bot.commands import start_command, help_command, cancel_command, status_command, user_sessions
from src.bot.file_handlers import handle_document, handle_custom_prompt
from src.bot.callbacks import skip_prompt, approve_outline, reject_outline
from src.bot.misc_handlers import handle_unknown

class TestBotHandlers:
    """Test cases for bot handlers."""
    
    @pytest.fixture
    def mock_message(self):
        """Create mock message for testing."""
        message = MagicMock(spec=Message)
        message.from_user = MagicMock(spec=User)
        message.from_user.id = 12345
        message.chat = MagicMock(spec=Chat)
        message.answer = AsyncMock()
        message.answer_document = AsyncMock()
        return message
    
    @pytest.fixture
    def mock_state(self):
        """Create mock FSM state for testing."""
        state = MagicMock(spec=FSMContext)
        state.set_state = AsyncMock()
        state.get_state = AsyncMock()
        state.clear = AsyncMock()
        return state
    
    @pytest.fixture
    def mock_callback_query(self):
        """Create mock callback query for testing."""
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = MagicMock(spec=User)
        callback.from_user.id = 12345
        callback.message = MagicMock(spec=Message)
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        return callback
    
    @pytest.fixture(autouse=True)
    def clear_user_sessions(self):
        """Clear user sessions before each test."""
        user_sessions.clear()
        yield
        user_sessions.clear()
    
    @pytest.mark.asyncio
    async def test_start_command(self, mock_message, mock_state):
        """Test /start command handler."""
        await start_command(mock_message, mock_state)
        
        # Verify user session is created
        assert 12345 in user_sessions
        session = user_sessions[12345]
        assert session["current_text"] is None
        assert session["outline"] is None
        assert session["custom_prompt"] == ""
        
        # Verify response and state
        mock_message.answer.assert_called_once()
        mock_state.set_state.assert_called_once_with(ProcessingStates.waiting_for_file)
        
        call_args = mock_message.answer.call_args
        assert "Telegram Bot для обробки текстів" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_help_command(self, mock_message):
        """Test /help command handler."""
        await help_command(mock_message)
        
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Доступні команди" in call_args[0][0]
        assert "/start" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_cancel_command(self, mock_message, mock_state):
        """Test /cancel command handler."""
        user_sessions[12345] = {"test": "data"}
        
        await cancel_command(mock_message, mock_state)
        
        # Verify session is cleared
        assert 12345 not in user_sessions
        mock_state.clear.assert_called_once()
        mock_message.answer.assert_called_once_with("❌ Операція скасована. Використайте /start для початку.")
    
    @pytest.mark.asyncio
    async def test_status_command_no_session(self, mock_message, mock_state):
        """Test /status command when no session exists."""
        mock_state.get_state.return_value = None
        
        await status_command(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Немає активної сесії" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_status_command_with_session(self, mock_message, mock_state):
        """Test /status command with active session."""
        user_sessions[12345] = {
            "current_text": "Some text",
            "outline": "Some outline",
            "custom_prompt": "Test prompt"
        }
        mock_state.get_state.return_value = ProcessingStates.waiting_for_file
        
        await status_command(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Поточний статус" in call_args[0][0]
        assert "✅" in call_args[0][0]  # File loaded
    
    @pytest.mark.asyncio
    async def test_handle_document_file_too_large(self, mock_message, mock_state):
        """Test document handler with file too large."""
        mock_document = MagicMock(spec=Document)
        mock_document.file_size = 20 * 1024 * 1024  # 20 MB (over limit)
        mock_document.file_name = "test.txt"
        mock_message.document = mock_document
        
        await handle_document(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "занадто великий" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_handle_document_unsupported_format(self, mock_message, mock_state):
        """Test document handler with unsupported format."""
        mock_document = MagicMock(spec=Document)
        mock_document.file_size = 1024
        mock_document.file_name = "test.pdf"
        mock_message.document = mock_document
        
        await handle_document(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Непідтримуваний формат" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_handle_document_success(self, mock_message, mock_state):
        """Test successful document handling."""
        mock_document = MagicMock(spec=Document)
        mock_document.file_size = 1024
        mock_document.file_name = "test.txt"
        mock_document.file_id = "test_file_id"
        mock_message.document = mock_document
        
        mock_file = MagicMock()
        mock_file.file_path = "/tmp/test.txt"
        
        with patch('bot.bot.get_file', return_value=mock_file) as mock_get_file:
            with patch('bot.bot.download_file') as mock_download:
                with patch('bot.file_processor.extract_text_from_file', return_value="Test content") as mock_extract:
                    with patch('os.remove') as mock_remove:
                        await handle_document(mock_message, mock_state)
        
        # Verify file processing
        mock_get_file.assert_called_once_with("test_file_id")
        mock_download.assert_called_once()
        mock_extract.assert_called_once()
        
        # Verify session update
        assert 12345 in user_sessions
        session = user_sessions[12345]
        assert session["current_text"] == "Test content"
        assert session["filename"] == "test.txt"
        
        # Verify state transition
        mock_state.set_state.assert_called_once_with(ProcessingStates.waiting_for_prompt)
    
    @pytest.mark.asyncio
    async def test_skip_prompt(self, mock_callback_query, mock_state):
        """Test skip prompt callback."""
        user_sessions[12345] = {"current_text": "Test content"}
        
        with patch('bot.generate_outline') as mock_generate:
            await skip_prompt(mock_callback_query, mock_state)
        
        mock_callback_query.answer.assert_called_once()
        mock_callback_query.message.edit_text.assert_called_once()
        
        # Verify custom prompt is set to empty
        assert user_sessions[12345]["custom_prompt"] == ""
        mock_generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_custom_prompt(self, mock_message, mock_state):
        """Test custom prompt handling."""
        mock_message.text = "Make it more formal"
        user_sessions[12345] = {"current_text": "Test content"}
        
        with patch('bot.generate_outline') as mock_generate:
            await handle_custom_prompt(mock_message, mock_state)
        
        # Verify prompt is saved
        assert user_sessions[12345]["custom_prompt"] == "Make it more formal"
        mock_message.answer.assert_called_once()
        mock_generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_approve_outline(self, mock_callback_query, mock_state):
        """Test outline approval callback."""
        user_sessions[12345] = {"outline": "Test outline"}
        
        with patch('bot.process_with_claude') as mock_process:
            await approve_outline(mock_callback_query, mock_state)
        
        mock_callback_query.answer.assert_called_once()
        mock_callback_query.message.edit_text.assert_called_once()
        mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reject_outline(self, mock_callback_query, mock_state):
        """Test outline rejection callback."""
        user_sessions[12345] = {"outline": "Test outline"}
        
        await reject_outline(mock_callback_query, mock_state)
        
        mock_callback_query.answer.assert_called_once()
        mock_callback_query.message.edit_text.assert_called_once()
        
        # Verify session is cleared
        assert 12345 not in user_sessions
        mock_state.set_state.assert_called_once_with(ProcessingStates.waiting_for_file)
    
    @pytest.mark.asyncio
    async def test_handle_unknown_waiting_for_file(self, mock_message, mock_state):
        """Test unknown message handler in waiting_for_file state."""
        mock_state.get_state.return_value = ProcessingStates.waiting_for_file
        
        await handle_unknown(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "завантажте текстовий файл" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_handle_unknown_no_state(self, mock_message, mock_state):
        """Test unknown message handler with no state."""
        mock_state.get_state.return_value = None
        
        await handle_unknown(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Невідома команда" in call_args[0][0]