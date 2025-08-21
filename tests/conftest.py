import pytest
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

test_dir = Path(__file__).parent
src_dir = test_dir.parent / "src"
sys.path.insert(0, str(src_dir))

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def mock_config():
    """Mock configuration to avoid loading real API keys during tests."""
    with patch.dict('sys.modules', {
        'src.config.settings': MagicMock(
            TELEGRAM_BOT_TOKEN="test_token",
            OPENAI_API_KEY="test_openai_key",
            ANTHROPIC_API_KEY="test_anthropic_key",
            MAX_FILE_SIZE=10 * 1024 * 1024,
            SUPPORTED_FORMATS=['.txt', '.docx'],
            GPT_MODEL="gpt-4.1",
            CLAUDE_MODEL="claude-3-5-sonnet-20241022"
        )
    }):
        yield

@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path

@pytest.fixture
def sample_text():
    """Provide sample text for testing."""
    return """This is a sample crazy story for testing.
    
It has multiple paragraphs with different content.
Some lines contain special characters: àáâãäåæçèéêë
And some contain numbers: 123456789

The story should be interesting enough to generate a good outline
and then be processed into a final text by the AI services.
"""

@pytest.fixture
def sample_outline():
    """Provide sample outline for testing."""
    return """# Perfect Outline

## I. Introduction
- Hook: Crazy situation setup
- Main character introduction
- Setting establishment

## II. Rising Action
- Initial conflict
- Character development
- Tension building

## III. Climax
- Peak of the story
- Major revelation or twist
- Highest tension point

## IV. Resolution
- Conflict resolution
- Character growth
- Story conclusion

## V. Themes
- Main themes explored
- Character arcs
- Message to audience
"""