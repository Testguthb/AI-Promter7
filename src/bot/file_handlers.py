import os
import logging
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, Document, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from .states import ProcessingStates
from .commands import user_sessions
from src.config.settings import MAX_FILE_SIZE, SUPPORTED_FORMATS
from src.utils import FileProcessor
from src.ai_services import AIOrchestrator

logger = logging.getLogger(__name__)

file_handlers_router = Router()

file_processor = FileProcessor()
ai_orchestrator = AIOrchestrator()


@file_handlers_router.message(F.document, StateFilter(ProcessingStates.waiting_for_file))
async def handle_document(message: Message, state: FSMContext):
    """Handle document upload."""
    user_id = message.from_user.id
    document: Document = message.document
    
    if document.file_size > MAX_FILE_SIZE:
        await message.answer(f"❌ Файл занадто великий. Максимальний розмір: {MAX_FILE_SIZE // (1024*1024)} MB")
        return
    
    file_extension = os.path.splitext(document.file_name)[1].lower()
    if file_extension not in SUPPORTED_FORMATS:
        await message.answer(f"❌ Непідтримуваний формат файлу. Підтримувані формати: {', '.join(SUPPORTED_FORMATS)}")
        return
    
    try:
        progress_msg = await message.answer("⏳ Завантажую файл...")
        
        bot = message.bot
        file = await bot.get_file(document.file_id)
        file_path = f"/tmp/{document.file_name}"
        await bot.download_file(file.file_path, file_path)
        
        await progress_msg.edit_text("📄 Витягую текст з файлу...")
        text_content = await file_processor.extract_text_from_file(file_path)
        
        os.remove(file_path)
        
        if not text_content.strip():
            await progress_msg.edit_text("❌ Файл порожній або не містить читабельного тексту.")
            return
        
        user_sessions[user_id]["current_text"] = text_content
        user_sessions[user_id]["filename"] = document.file_name
        
        await progress_msg.edit_text(f"✅ Файл успішно оброблено!\n📊 Знайдено {len(text_content)} символів тексту.")
        
        from .template_handlers import show_ai_choice
        await show_ai_choice(message, state)
        
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        await message.answer(f"❌ Помилка обробки файлу: {str(e)}")


@file_handlers_router.message(F.text, StateFilter(ProcessingStates.waiting_for_prompt))
async def handle_custom_prompt(message: Message, state: FSMContext):
    """Handle custom prompt input."""
    user_id = message.from_user.id
    custom_prompt = message.text.strip()
    
    user_sessions[user_id]["custom_prompt"] = custom_prompt
    
    await message.answer(f"✅ Промт збережено: {custom_prompt[:100]}...")
    await generate_outline(message, state, user_id)


@file_handlers_router.message(F.document, StateFilter(ProcessingStates.waiting_for_prompt))
async def handle_custom_prompt_file(message: Message, state: FSMContext):
    """Handle custom prompt file upload."""
    user_id = message.from_user.id
    document: Document = message.document
    
    if document.file_size > MAX_FILE_SIZE:
        await message.answer(f"❌ Файл занадто великий. Максимальний розмір: {MAX_FILE_SIZE // (1024*1024)} MB")
        return
    
    file_extension = os.path.splitext(document.file_name)[1].lower()
    if file_extension not in ['.txt', '.docx']:
        await message.answer("❌ Непідтримуваний формат файлу. Підтримувані формати: .txt, .docx")
        return
    
    try:
        progress_msg = await message.answer("⏳ Завантажую файл з промтом...")
        
        bot = message.bot
        file = await bot.get_file(document.file_id)
        file_path = f"/tmp/{document.file_name}"
        await bot.download_file(file.file_path, file_path)
        
        await progress_msg.edit_text("📄 Читаю промт з файлу...")
        prompt_content = await file_processor.extract_text_from_file(file_path)
        
        os.remove(file_path)
        
        if not prompt_content.strip():
            await progress_msg.edit_text("❌ Файл порожній або не містить читабельного тексту.")
            return
        
        user_sessions[user_id]["custom_prompt"] = prompt_content.strip()
        
        await progress_msg.edit_text(
            f"✅ Промт успішно завантажено з файлу!\n"
            f"📊 Промт містить {len(prompt_content)} символів\n\n"
            f"**Промт:** {prompt_content[:200]}{'...' if len(prompt_content) > 200 else ''}"
        )
        
        await generate_outline(message, state, user_id)
        
    except Exception as e:
        logger.error(f"Error processing prompt file: {e}")
        await message.answer(f"❌ Помилка обробки файлу з промтом: {str(e)}")


@file_handlers_router.message(F.text, StateFilter(ProcessingStates.waiting_for_sonnet_prompt))
async def handle_sonnet_prompt(message: Message, state: FSMContext):
    """Handle Sonnet prompt input."""
    user_id = message.from_user.id
    sonnet_prompt = message.text.strip()
    
    user_sessions[user_id]["sonnet_prompt"] = sonnet_prompt
    
    await message.answer(f"✅ Промт для Sonnet збережено: {sonnet_prompt[:100]}...")
    await ask_volume_choice(message, state, user_id)


@file_handlers_router.message(F.document, StateFilter(ProcessingStates.waiting_for_sonnet_prompt))
async def handle_sonnet_prompt_file(message: Message, state: FSMContext):
    """Handle Sonnet prompt file upload."""
    user_id = message.from_user.id
    document: Document = message.document
    
    if document.file_size > MAX_FILE_SIZE:
        await message.answer(f"❌ Файл занадто великий. Максимальний розмір: {MAX_FILE_SIZE // (1024*1024)} MB")
        return
    
    file_extension = os.path.splitext(document.file_name)[1].lower()
    if file_extension not in ['.txt', '.docx']:
        await message.answer("❌ Непідтримуваний формат файлу. Підтримувані формати: .txt, .docx")
        return
    
    try:
        progress_msg = await message.answer("⏳ Завантажую файл з промтом для Sonnet...")
        
        bot = message.bot
        file = await bot.get_file(document.file_id)
        file_path = f"/tmp/{document.file_name}"
        await bot.download_file(file.file_path, file_path)
        
        await progress_msg.edit_text("📄 Читаю промт з файлу...")
        prompt_content = await file_processor.extract_text_from_file(file_path)
        
        os.remove(file_path)
        
        if not prompt_content.strip():
            await progress_msg.edit_text("❌ Файл порожній або не містить читабельного тексту.")
            return
        
        user_sessions[user_id]["sonnet_prompt"] = prompt_content.strip()
        
        await progress_msg.edit_text(
            f"✅ Промт для Sonnet успішно завантажено з файлу!\n"
            f"📊 Промт містить {len(prompt_content)} символів\n\n"
            f"**Промт:** {prompt_content[:200]}{'...' if len(prompt_content) > 200 else ''}"
        )
        
        await ask_volume_choice(message, state, user_id)
        
    except Exception as e:
        logger.error(f"Error processing Sonnet prompt file: {e}")
        await message.answer(f"❌ Помилка обробки файлу з промтом для Sonnet: {str(e)}")


async def generate_outline(message: Message, state: FSMContext, user_id: int):
    """Generate outline using GPT-4.1."""
    try:
        session = user_sessions[user_id]
        text = session["current_text"]
        custom_prompt = session["custom_prompt"]
        
        sample_content = ""
        if "selected_template" in session and session["selected_template"]:
            sample_content = session["selected_template"].get("sample_content", "")
        
        progress_msg = await message.answer("🧠 Генерую outline за допомогою GPT-4.1...")
        user_sessions[user_id]["progress_message"] = progress_msg
        
        outline = await ai_orchestrator.gpt_service.generate_outline(text, custom_prompt, sample_content)
        session["outline"] = outline
        
        await progress_msg.edit_text("✅ Outline успішно згенеровано!")
        
        outline_filename = f"outline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        outline_path = await file_processor.save_text_to_file(outline, outline_filename)
        
        outline_file = FSInputFile(outline_path)
        await message.answer_document(
            outline_file,
            caption="📋 **Perfect Outline згенеровано!**\n\nПерегляньте outline і підтвердьте, чи підходить він для подальшої обробки.",
            parse_mode="Markdown"
        )
        
        os.remove(outline_path)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Так, підходить", callback_data="approve_outline"),
                InlineKeyboardButton(text="❌ Ні, не підходить", callback_data="reject_outline")
            ],
            [
                InlineKeyboardButton(text="🔄 Перегенерувати ще раз", callback_data="regenerate_outline")
            ]
        ])
        
        await message.answer(
            "🤔 **Чи підходить цей outline?**\n\n"
            "✅ **Так** - переходимо до обробки через Claude Sonnet 4\n"
            "❌ **Ні** - завантажте новий файл для початку\n"
            "🔄 **Перегенерувати** - створити новий outline з тими самими параметрами",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        await state.set_state(ProcessingStates.waiting_for_outline_approval)
        
    except Exception as e:
        logger.error(f"Error generating outline: {e}")
        await message.answer(f"❌ Помилка генерації outline: {str(e)}")


async def ask_volume_choice(message: Message, state: FSMContext, user_id: int):
    """Ask user to choose target volume."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 15K символів", callback_data="volume_15k"),
            InlineKeyboardButton(text="📊 30K символів", callback_data="volume_30k")
        ],
        [
            InlineKeyboardButton(text="📊 40K символів", callback_data="volume_40k"),
            InlineKeyboardButton(text="📊 60K символів", callback_data="volume_60k")
        ]
    ])
    
    await message.answer(
        "🎯 **Оберіть цільовий обсяг для генерації:**\n\n"
        "• **15K** - Цільовий діапазон: 15,000 - 20,000 символів\n"
        "• **30K** - Цільовий діапазон: 28,000 - 34,000 символів\n"
        "• **40K** - Цільовий діапазон: 40,000 - 50,000 символів\n"
        "• **60K** - Цільовий діапазон: 56,000 - 68,000 символів\n\n"
        "Система буде генерувати текст поки не отримає відповідь у вибраному діапазоні.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    await state.set_state(ProcessingStates.waiting_for_volume_choice)