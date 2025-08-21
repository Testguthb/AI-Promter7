import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from .states import ProcessingStates
from .commands import user_sessions
from .file_handlers import generate_outline, ask_volume_choice
from .processors import start_automated_generation
from src.utils import FileProcessor

logger = logging.getLogger(__name__)

# Callback handlers router
callbacks_router = Router()


@callbacks_router.callback_query(F.data == "skip_prompt", StateFilter(ProcessingStates.waiting_for_prompt))
async def skip_prompt(callback: CallbackQuery, state: FSMContext):
    """Handle skip prompt button."""
    await callback.answer()
    await callback.message.edit_text("⏩ Промт пропущено. Переходжу до генерації outline...")
    
    user_id = callback.from_user.id
    user_sessions[user_id]["custom_prompt"] = ""
    
    await generate_outline(callback.message, state, user_id)


@callbacks_router.callback_query(F.data == "approve_outline", StateFilter(ProcessingStates.waiting_for_outline_approval))
async def approve_outline(callback: CallbackQuery, state: FSMContext):
    """Handle outline approval."""
    await callback.answer()
    await callback.message.edit_text("✅ Outline підтверджено!")
    
    user_id = callback.from_user.id
    
    # Set context for Sonnet prompt and show AI choice
    from .commands import user_sessions
    user_sessions[user_id]["prompt_context"] = "sonnet_prompt"
    
    from .template_handlers import show_ai_choice
    await show_ai_choice(callback.message, state, context="sonnet_prompt")


@callbacks_router.callback_query(F.data == "reject_outline", StateFilter(ProcessingStates.waiting_for_outline_approval))
async def reject_outline(callback: CallbackQuery, state: FSMContext):
    """Handle outline rejection."""
    await callback.answer()
    await callback.message.edit_text("❌ Outline відхилено. Завантажте новий файл для початку.")
    
    user_id = callback.from_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await state.set_state(ProcessingStates.waiting_for_file)


@callbacks_router.callback_query(F.data == "regenerate_outline", StateFilter(ProcessingStates.waiting_for_outline_approval))
async def regenerate_outline(callback: CallbackQuery, state: FSMContext):
    """Handle outline regeneration."""
    await callback.answer()
    await callback.message.edit_text("🔄 Перегенеровую outline з тими самими параметрами...")
    
    user_id = callback.from_user.id
    
    # Regenerate outline with the same parameters
    await generate_outline(callback.message, state, user_id)


@callbacks_router.callback_query(F.data == "skip_sonnet_prompt", StateFilter(ProcessingStates.waiting_for_sonnet_prompt))
async def skip_sonnet_prompt(callback: CallbackQuery, state: FSMContext):
    """Handle skip Sonnet prompt button."""
    await callback.answer()
    await callback.message.edit_text("⏩ Промт для Sonnet пропущено.")
    
    user_id = callback.from_user.id
    user_sessions[user_id]["sonnet_prompt"] = ""
    
    await ask_volume_choice(callback.message, state, user_id)


@callbacks_router.callback_query(F.data.startswith("volume_"), StateFilter(ProcessingStates.waiting_for_volume_choice))
async def handle_volume_choice(callback: CallbackQuery, state: FSMContext):
    """Handle volume choice."""
    await callback.answer()
    
    user_id = callback.from_user.id
    volume = callback.data.split("_")[1]  # "15k", "30k", "40k", or "60k"
    
    user_sessions[user_id]["target_volume"] = volume
    
    volume_mapping = {
        "15k": "15K символів",
        "30k": "30K символів", 
        "40k": "40K символів",
        "60k": "60K символів"
    }
    volume_text = volume_mapping.get(volume, f"{volume.upper()} символів")
    await callback.message.edit_text(f"✅ Обрано обсяг: {volume_text}")
    
    # Automatically enable multithread mode
    user_sessions[user_id]["multithread_mode"] = True
    
    await start_automated_generation(callback.message, state, user_id)


@callbacks_router.callback_query(F.data == "select_short_story", StateFilter(ProcessingStates.waiting_for_file))
async def select_short_story(callback: CallbackQuery, state: FSMContext):
    """Handle short story selection."""
    await callback.answer()
    user_id = callback.from_user.id
    
    progress_msg = await callback.message.edit_text("🎲 Обираю випадкову коротку історію...")
    
    file_processor = FileProcessor()
    story_result = file_processor.get_random_story_file("short")
    
    if not story_result:
        await progress_msg.edit_text(
            "❌ Не вдалося знайти файли коротких історій.\n"
            "Спробуйте завантажити власний файл."
        )
        return
    
    file_path, filename = story_result
    
    try:
        await progress_msg.edit_text(f"📄 Витягую текст з файлу: **{filename}**...")
        text_content = await file_processor.extract_text_from_file(file_path)
        
        if not text_content.strip():
            await progress_msg.edit_text("❌ Обраний файл порожній або не містить читабельного тексту.")
            return
        
        user_sessions[user_id]["current_text"] = text_content
        user_sessions[user_id]["filename"] = filename
        
        await progress_msg.edit_text(
            f"✅ **Обрано файл:** {filename}\n"
            f"📊 Знайдено {len(text_content)} символів тексту."
        )
        
        from .template_handlers import show_ai_choice
        await show_ai_choice(callback.message, state)
        
    except Exception as e:
        logger.error(f"Error processing random short story: {e}")
        await progress_msg.edit_text(f"❌ Помилка обробки файлу: {str(e)}")


@callbacks_router.callback_query(F.data == "select_long_story", StateFilter(ProcessingStates.waiting_for_file))
async def select_long_story(callback: CallbackQuery, state: FSMContext):
    """Handle long story selection."""
    await callback.answer()
    user_id = callback.from_user.id
    
    progress_msg = await callback.message.edit_text("🎲 Обираю випадкову довгу історію...")
    
    file_processor = FileProcessor()
    story_result = file_processor.get_random_story_file("long")
    
    if not story_result:
        await progress_msg.edit_text(
            "❌ Не вдалося знайти файли довгих історій.\n"
            "Спробуйте завантажити власний файл."
        )
        return
    
    file_path, filename = story_result
    
    try:
        await progress_msg.edit_text(f"📄 Витягую текст з файлу: **{filename}**...")
        text_content = await file_processor.extract_text_from_file(file_path)
        
        if not text_content.strip():
            await progress_msg.edit_text("❌ Обраний файл порожній або не містить читабельного тексту.")
            return
        
        user_sessions[user_id]["current_text"] = text_content
        user_sessions[user_id]["filename"] = filename
        
        await progress_msg.edit_text(
            f"✅ **Обрано файл:** {filename}\n"
            f"📊 Знайдено {len(text_content)} символів тексту."
        )
        
        from .template_handlers import show_ai_choice
        await show_ai_choice(callback.message, state)
        
    except Exception as e:
        logger.error(f"Error processing random long story: {e}")
        await progress_msg.edit_text(f"❌ Помилка обробки файлу: {str(e)}")


@callbacks_router.callback_query(F.data == "manual_upload", StateFilter(ProcessingStates.waiting_for_file))
async def manual_upload(callback: CallbackQuery, state: FSMContext):
    """Handle manual file upload selection."""
    await callback.answer()
    
    await callback.message.edit_text(
        "📄 **Завантажте файл для початку!**\n\n"
        "Підтримувані формати: .txt, .docx\n"
        "Максимальний розмір: 10 MB\n\n"
        "Просто надішліть файл у цей чат."
    )
    
    # State remains ProcessingStates.waiting_for_file for manual upload


