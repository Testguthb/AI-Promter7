import os
import aiofiles
from docx import Document
from typing import Optional
import logging
import random

logger = logging.getLogger(__name__)


class FileProcessor:
    """Handles file processing for text extraction."""
    
    @staticmethod
    async def extract_text_from_file(file_path: str) -> str:
        """Extract text from uploaded file based on its extension."""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.txt':
            return await FileProcessor._extract_from_txt(file_path)
        elif file_extension == '.docx':
            return await FileProcessor._extract_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    
    @staticmethod
    async def _extract_from_txt(file_path: str) -> str:
        """Extract text from .txt file."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                content = await file.read()
            return content.strip()
        except UnicodeDecodeError:
            # Try with different encoding
            async with aiofiles.open(file_path, 'r', encoding='cp1251') as file:
                content = await file.read()
            return content.strip()
    
    @staticmethod
    async def _extract_from_docx(file_path: str) -> str:
        """Extract text from .docx file."""
        try:
            doc = Document(file_path)
            text_content = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text.strip())
            
            return '\n\n'.join(text_content)
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            raise ValueError(f"Failed to process DOCX file: {str(e)}")
    
    @staticmethod
    async def save_text_to_file(text: str, filename: str) -> str:
        """Save text content to file and return file path."""
        file_path = f"/tmp/{filename}"
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as file:
            await file.write(text)
        
        return file_path
    
    @staticmethod
    def validate_file(file_path: str, max_size: int) -> bool:
        """Validate file size and format."""
        if not os.path.exists(file_path):
            return False
        
        file_size = os.path.getsize(file_path)
        if file_size > max_size:
            return False
        
        file_extension = os.path.splitext(file_path)[1].lower()
        from src.config.settings import SUPPORTED_FORMATS
        return file_extension in SUPPORTED_FORMATS
    
    @staticmethod
    def get_random_story_file(story_type: str) -> Optional[tuple[str, str]]:
        """
        Get a random story file from the specified folder.
        
        Args:
            story_type: 'short' or 'long'
            
        Returns:
            Tuple of (file_path, filename) or None if no files found
        """
        from src.bot.template_handlers import SHORT_STORY_DIR, LONG_STORY_DIR
        
        if story_type == 'short':
            folder_path = SHORT_STORY_DIR
        elif story_type == 'long':
            folder_path = LONG_STORY_DIR
        else:
            logger.error(f"Invalid story type: {story_type}. Must be 'short' or 'long'")
            return None
        
        if not os.path.exists(folder_path):
            logger.error(f"Story folder not found: {folder_path}")
            return None
        
        # Get all supported files from the folder
        from src.config.settings import SUPPORTED_FORMATS
        story_files = []
        
        try:
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    file_extension = os.path.splitext(filename)[1].lower()
                    if file_extension in SUPPORTED_FORMATS:
                        story_files.append((file_path, filename))
            
            if not story_files:
                logger.warning(f"No supported files found in {folder_path}")
                return None
            
            # Return random file
            return random.choice(story_files)
            
        except Exception as e:
            logger.error(f"Error reading story folder {folder_path}: {e}")
            return None