import os
import re
import logging
import random
from typing import List, Tuple, Optional
from pathlib import Path
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from .states import ProcessingStates
from .commands import user_sessions
from src.utils import FileProcessor

logger = logging.getLogger(__name__)

template_router = Router()


PROJECT_ROOT = Path(__file__).parent.parent.parent
GPT_TEMPLATES_DIR = str(PROJECT_ROOT / "gpt-prompt")
CLAUDE_TEMPLATES_DIR = str(PROJECT_ROOT / "claude-prompt")
SAMPLE_TEMPLATES_DIR = str(PROJECT_ROOT / "gpt-prompt" / "sample")
SHORT_STORY_DIR = str(PROJECT_ROOT / "short-story")
LONG_STORY_DIR = str(PROJECT_ROOT / "long-story")

GPT_FOLDERS = ["15к", "30к", "40к", "60к"]

logger.info(f"Template handler initialized with paths:")
logger.info(f"  PROJECT_ROOT: {PROJECT_ROOT}")
logger.info(f"  GPT_TEMPLATES_DIR: {GPT_TEMPLATES_DIR}")
logger.info(f"  CLAUDE_TEMPLATES_DIR: {CLAUDE_TEMPLATES_DIR}")
logger.info(f"  SHORT_STORY_DIR: {SHORT_STORY_DIR}")
logger.info(f"  LONG_STORY_DIR: {LONG_STORY_DIR}")


def get_template_files(directory: str) -> List[str]:
    """Get list of template files from directory."""
    try:
        logger.info(f"Looking for template files in directory: {directory}")
        if not os.path.exists(directory):
            logger.warning(f"Template directory does not exist: {directory}")
            return []
        files = [f for f in os.listdir(directory) if f.endswith(('.txt', '.docx'))]
        logger.info(f"Found {len(files)} template files in {directory}: {files}")
        return sorted(files)
    except Exception as e:
        logger.error(f"Error reading template directory {directory}: {e}")
        return []


def get_sample_files() -> List[str]:
    """Get list of sample files from sample directory."""
    try:
        logger.info(f"Looking for sample files in directory: {SAMPLE_TEMPLATES_DIR}")
        if not os.path.exists(SAMPLE_TEMPLATES_DIR):
            logger.warning(f"Sample directory does not exist: {SAMPLE_TEMPLATES_DIR}")
            return []
        files = [f for f in os.listdir(SAMPLE_TEMPLATES_DIR) if f.endswith(('.txt', '.docx'))]
        logger.info(f"Found {len(files)} sample files: {files}")
        return files
    except Exception as e:
        logger.error(f"Error reading sample directory {SAMPLE_TEMPLATES_DIR}: {e}")
        return []


async def select_random_sample() -> Optional[Tuple[str, str]]:
    """Select a random sample file and return its name and content."""
    try:
        sample_files = get_sample_files()
        if not sample_files:
            logger.warning("No sample files found")
            return None
        
        selected_file = random.choice(sample_files)
        sample_content = await read_template_file(SAMPLE_TEMPLATES_DIR, selected_file)
        
        if sample_content:
            logger.info(f"Selected random sample: {selected_file}")
            return selected_file, sample_content
        else:
            logger.error(f"Could not read sample file: {selected_file}")
            return None
            
    except Exception as e:
        logger.error(f"Error selecting random sample: {e}")
        return None


def create_story_txt_file(story_content: str, template_name: str, user_id: int) -> str:
    """Create a .txt file with the complete story content."""
    try:
        output_dir = Path("generated_stories")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_template_name = re.sub(r'[^\w\-_.]', '_', template_name)
        filename = f"{safe_template_name}_{user_id}_{timestamp}.txt"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(story_content)
        
        logger.info(f"Created story file: {filepath}")
        return str(filepath)
        
    except Exception as e:
        logger.error(f"Error creating story file: {e}")
        raise


async def read_template_file(directory: str, filename: str) -> Optional[str]:
    """Read template file content."""
    try:
        filepath = os.path.join(directory, filename)
        file_extension = os.path.splitext(filename)[1].lower()
        
        if file_extension == '.docx':
            return await FileProcessor.extract_text_from_file(filepath)
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        logger.error(f"Error reading template file {filepath}: {e}")
        return None


def extract_template_name(filename: str) -> str:
    """Extract display name from template filename."""
    name = filename.replace('.txt', '').replace('.docx', '').replace('_', ' ')
    return name.title()


def has_include_story_section(template_content: str) -> bool:
    """Check if template has INCLUDE IN STORY section."""
    return "INCLUDE IN STORY:" in template_content


def replace_story_in_template(template_content: str, new_story: str) -> str:
    """Replace the story part in INCLUDE IN STORY section."""
    if "INCLUDE IN STORY:" not in template_content:
        return template_content
    
    start_marker = "INCLUDE IN STORY:"
    end_marker = "Outline Length"
    
    start_idx = template_content.find(start_marker)
    if start_idx == -1:
        return template_content
    
    line_end = template_content.find('\n', start_idx)
    if line_end == -1:
        return template_content
    
    end_idx = template_content.find(end_marker)
    if end_idx == -1:
        end_idx = len(template_content)
    
    before = template_content[:line_end + 1]
    after = template_content[end_idx:]
    
    return before + "\n\n" + new_story + "\n\n\n" + after


async def show_ai_choice(message: Message, state: FSMContext, context: str = "initial"):
    """Show AI choice menu (GPT or Claude)."""
    
    if context == "sonnet_prompt":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Claude Шаблони", callback_data="ai_choice_claude")],
            [InlineKeyboardButton(text="✏️ Власний промт", callback_data="ai_choice_custom")]
        ])
        
        text = (
            "🎯 **Оберіть тип промту для Claude Sonnet:**\n\n"
            "• **Claude Шаблони** - готові шаблони для Claude\n"
            "• **Власний промт** - введіть власний текст промту\n\n"
            "Що бажаєте використати?"
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 GPT Шаблони", callback_data="ai_choice_gpt")],
            [InlineKeyboardButton(text="✏️ Власний промт", callback_data="ai_choice_custom")]
        ])
        
        text = (
            "🎯 **Оберіть тип промту:**\n\n"
            "• **GPT Шаблони** - готові шаблони для GPT з можливістю зміни історії\n"
            "• **Власний промт** - введіть власний текст промту\n\n"
            "Що бажаєте використати?"
        )
    
    await message.answer(
        text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    await state.set_state(ProcessingStates.waiting_for_ai_choice)


async def show_gpt_folder_choice(message: Message, state: FSMContext):
    """Show GPT folder choice menu."""
    user_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]["selected_ai_type"] = "gpt"
    
    keyboard_buttons = []
    for folder in GPT_FOLDERS:
        callback_data = f"gpt_folder_{folder}"
        keyboard_buttons.append([InlineKeyboardButton(text=f"📁 {folder}", callback_data=callback_data)])
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_ai_choice")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.answer(
        "🤖 **GPT Шаблони**\n\n"
        "📁 Оберіть папку за кількістю символів:\n\n"
        "• **15к** - короткі історії\n"
        "• **30к** - середні історії\n"
        "• **40к** - розширені історії\n"
        "• **60к** - довгі історії\n\n"
        "Яку папку бажаєте переглянути?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    await state.set_state(ProcessingStates.waiting_for_gpt_folder_choice)


async def show_template_choice(message: Message, state: FSMContext, ai_type: str, folder: str = None):
    """Show template choice menu for selected AI type and folder."""
    user_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]["selected_ai_type"] = ai_type
    
    if ai_type == "gpt" and folder:
        folder_path = os.path.join(GPT_TEMPLATES_DIR, folder)
        templates = get_template_files(folder_path)
        title = f"🤖 **GPT Шаблони - {folder}**"
        user_sessions[user_id]["selected_folder"] = folder
    elif ai_type == "gpt":
        # For GPT without folder (shouldn't happen with new system, but fallback)
        templates = get_template_files(GPT_TEMPLATES_DIR)
        title = "🤖 **GPT Шаблони**"
    else:  # claude
        templates = get_template_files(CLAUDE_TEMPLATES_DIR)
        title = "🧠 **Claude Шаблони**"
    
    if not templates:
        await message.answer(
            f"❌ Не знайдено шаблонів в папці {folder if folder else ai_type.upper()}.\n"
            f"Додайте файли .txt в відповідну папку.",
            parse_mode="Markdown"
        )
        return
    
    keyboard_buttons = []
    for template in templates:
        display_name = extract_template_name(template)
        callback_data = f"template_{ai_type}_{folder}_{template}" if folder else f"template_{ai_type}_{template}"
        keyboard_buttons.append([InlineKeyboardButton(text=display_name, callback_data=callback_data)])
    
    if ai_type == "gpt" and folder:
        keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад до папок", callback_data="back_to_gpt_folders")])
    else:
        keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_ai_choice")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.answer(
        f"{title}\n\n"
        f"📁 Знайдено {len(templates)} шаблон(ів).\n"
        f"Оберіть шаблон для використання:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    await state.set_state(ProcessingStates.waiting_for_template_choice)


async def handle_template_selection(callback: CallbackQuery, state: FSMContext, ai_type: str, template_filename: str, folder: str = None):
    """Handle template selection."""
    user_id = callback.from_user.id
    
    if ai_type == "gpt" and folder:
        directory = os.path.join(GPT_TEMPLATES_DIR, folder)
    elif ai_type == "gpt":
        directory = GPT_TEMPLATES_DIR
    else:
        directory = CLAUDE_TEMPLATES_DIR
    
    template_content = await read_template_file(directory, template_filename)
    
    if not template_content:
        await callback.answer("❌ Помилка читання шаблону", show_alert=True)
        return
    
    selected_sample = None
    sample_content = None
    if ai_type == "gpt":
        sample_result = await select_random_sample()
        if sample_result:
            selected_sample, sample_content = sample_result
            logger.info(f"Selected sample for user {user_id}: {selected_sample}")
    
    user_sessions[user_id]["selected_template"] = {
        "ai_type": ai_type,
        "filename": template_filename,
        "folder": folder,
        "content": template_content,
        "original_content": template_content,
        "selected_sample": selected_sample,
        "sample_content": sample_content
    }
    
    display_name = extract_template_name(template_filename)
    await callback.answer()
    
    if ai_type == "gpt" and has_include_story_section(template_content):
        # GPT template with story section - ask if user wants to change it
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Так", callback_data="change_story_yes")],
            [InlineKeyboardButton(text="❌ Ні", callback_data="change_story_no")]
        ])
        
        sample_info = f"\n🎲 **Семпл використаний як зразок:** {selected_sample}" if selected_sample else ""
        
        await callback.message.edit_text(
            f"📋 **Обрано шаблон:** {display_name}\n"
            f"📁 **Папка:** {folder}\n"
            f"🔍 Цей шаблон містить секцію 'INCLUDE IN STORY:' з готовою історією.{sample_info}\n\n"
            f"**Змінити Include Story?**",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        await state.set_state(ProcessingStates.waiting_for_story_change_confirmation)
    else:
        # Claude template or GPT without story section - use directly
        await finalize_template_selection(callback.message, state, user_id)


async def request_new_story_text(message: Message, state: FSMContext):
    """Request new story text from user."""
    await message.answer(
        "✏️ **Введіть новий текст для заміни в Include In Story**\n\n"
        "Просто напишіть текст, який має замінити поточний вміст в секції 'INCLUDE IN STORY:'.\n\n"
        "Наприклад: 'Я працював програмістом у великій компанії, але одного дня мене звільнили без попередження. Тоді я вирішив створити власний стартап.'\n\n"
        "Надішліть ваш текст повідомленням:",
        parse_mode="Markdown"
    )
    
    await state.set_state(ProcessingStates.waiting_for_new_story_text)


async def replace_story_text(message: Message, state: FSMContext, new_story_text: str):
    """Replace story text in template."""
    user_id = message.from_user.id
    
    try:
        processing_msg = await message.answer("🔄 Замінюю текст в Include In Story...")
        
        user_sessions[user_id]["new_story_text"] = new_story_text.strip()
        
        template_info = user_sessions[user_id]["selected_template"]
        updated_template = replace_story_in_template(template_info["content"], new_story_text.strip())
        user_sessions[user_id]["selected_template"]["content"] = updated_template
        
        await processing_msg.delete()
        
        await show_final_template_confirmation(message, state, user_id, new_story_text.strip())
        
    except Exception as e:
        logger.error(f"Error replacing story text: {e}")
        await message.answer(f"❌ Помилка заміни тексту: {str(e)}")


async def show_final_template_confirmation(message: Message, state: FSMContext, user_id: int, story_text: str):
    """Show final template confirmation with new story text and send txt file."""
    template_info = user_sessions[user_id]["selected_template"]
    display_name = extract_template_name(template_info["filename"])
    
    complete_story = template_info["content"]
    
    story_preview = story_text[:150] + "..." if len(story_text) > 150 else story_text
    
    try:
        filepath = create_story_txt_file(complete_story, display_name, user_id)
        document = FSInputFile(filepath)
        
        await message.answer_document(
            document=document,
            caption=f"📋 **Готовий шаблон:** {display_name}\n\n"
                   f"🎯 **Новий текст Include In Story:**\n"
                   f"_{story_preview}_\n\n"
                   f"📄 **Повний файл з оновленою історією прикріплено вище**",
            parse_mode="Markdown"
        )
        
        try:
            os.remove(filepath)
            logger.info(f"Cleaned up temporary file: {filepath}")
        except Exception as cleanup_error:
            logger.warning(f"Could not clean up file {filepath}: {cleanup_error}")
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Так, підходить", callback_data="confirm_final_template")],
            [InlineKeyboardButton(text="🔄 Змінити текст історії", callback_data="change_story_text")],
            [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_template")]
        ])
        
        await message.answer(
            "**Чи підходить цей варіант?**",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error creating story file: {e}")
        await message.answer("❌ Помилка при створенні файлу. Показую текст у повідомленні:")
        
        # Truncate template for display (Telegram message limit is ~4096 chars)
        max_display_length = 3000  # Leave room for other text
        if len(complete_story) > max_display_length:
            template_preview = complete_story[:max_display_length] + "\n\n... (шаблон обрізано для перегляду)"
        else:
            template_preview = complete_story
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Так, підходить", callback_data="confirm_final_template")],
            [InlineKeyboardButton(text="🔄 Змінити текст історії", callback_data="change_story_text")],
            [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_template")]
        ])
        
        await message.answer(
            f"📋 **Готовий шаблон:** {display_name}\n\n"
            f"🎯 **Новий текст Include In Story:**\n"
            f"_{story_preview}_\n\n"
            f"📖 **Повний шаблон з новою історією:**\n"
            f"```\n{template_preview}\n```\n\n"
            f"**Чи підходить цей варіант?**",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    await state.set_state(ProcessingStates.waiting_for_final_template_confirmation)



async def finalize_template_selection(message: Message, state: FSMContext, user_id: int):
    """Finalize template selection and proceed to next step based on context."""
    template_info = user_sessions[user_id]["selected_template"]
    context = user_sessions[user_id].get("prompt_context", "initial")
    
    display_name = extract_template_name(template_info["filename"])
    
    if context == "sonnet_prompt":
        user_sessions[user_id]["sonnet_prompt"] = template_info["content"]
        
        await message.answer(
            f"✅ **Claude шаблон готовий до використання!**\n\n"
            f"📋 **Обраний шаблон:** {display_name}\n"
            f"🧠 **Тип:** Claude Sonnet\n\n"
            f"⏳ Переходжу до вибору обсягу...",
            parse_mode="Markdown"
        )
        
        from .file_handlers import ask_volume_choice
        await ask_volume_choice(message, state, user_id)
    else:
        user_sessions[user_id]["custom_prompt"] = template_info["content"]
        
        sample_info = ""
        if template_info.get("selected_sample"):
            sample_info = f"\n🎲 **Вибраний семпл:** {template_info['selected_sample']}"
        
        await message.answer(
            f"✅ **Шаблон готовий до використання!**\n\n"
            f"📋 **Обраний шаблон:** {display_name}\n"
            f"🤖 **Тип:** {template_info['ai_type'].upper()}{sample_info}\n\n"
            f"⏳ Переходжу до генерації outline...",
            parse_mode="Markdown"
        )
        
        from .file_handlers import generate_outline
        await generate_outline(message, state, user_id)



@template_router.callback_query(StateFilter(ProcessingStates.waiting_for_ai_choice))
async def handle_ai_choice(callback: CallbackQuery, state: FSMContext):
    """Handle AI type choice."""
    await callback.answer()
    
    user_id = callback.from_user.id
    
    if callback.data == "ai_choice_gpt":
        await show_gpt_folder_choice(callback.message, state)
    elif callback.data == "ai_choice_claude":
        await show_template_choice(callback.message, state, "claude")
    elif callback.data == "ai_choice_custom":
        context = user_sessions[user_id].get("prompt_context", "initial")
        
        if context == "sonnet_prompt":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏩ Пропустити промт для Sonnet", callback_data="skip_sonnet_prompt")]
            ])
            
            await callback.message.edit_text(
                "✏️ **Введіть ваш власний промт для Claude Sonnet 4:**\n\n"
                "Цей промт буде використаний для обробки outline через Claude Sonnet 4.\n\n"
                "Наприклад: 'Зробити текст більш емоційним та детальним' або 'Додати діалоги між персонажами'\n\n"
                "Ви можете:\n"
                "• 💬 Написати промт повідомленням\n"
                "• 📁 Завантажити файл .txt або .docx з промтом\n\n"
                "Або натисніть 'Пропустити промт' для продовження без додаткових інструкцій.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await state.set_state(ProcessingStates.waiting_for_sonnet_prompt)
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏩ Пропустити промт", callback_data="skip_prompt")]
            ])
            
            await callback.message.edit_text(
                "✏️ **Введіть ваш власний промт:**\n\n"
                "Наприклад: 'Зробити текст більш формальним' або 'Додати більше деталей про персонажів'\n\n"
                "Ви можете:\n"
                "• 💬 Написати промт повідомленням\n"
                "• 📁 Завантажити файл .txt або .docx з промтом\n\n"
                "Або натисніть 'Пропустити промт' для продовження без додаткових інструкцій.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await state.set_state(ProcessingStates.waiting_for_prompt)


@template_router.callback_query(StateFilter(ProcessingStates.waiting_for_gpt_folder_choice))
async def handle_gpt_folder_choice(callback: CallbackQuery, state: FSMContext):
    """Handle GPT folder choice."""
    await callback.answer()
    
    if callback.data == "back_to_ai_choice":
        user_id = callback.from_user.id
        context = user_sessions[user_id].get("prompt_context", "initial")
        await show_ai_choice(callback.message, state, context=context)
        return
    
    if callback.data.startswith("gpt_folder_"):
        folder = callback.data.replace("gpt_folder_", "")
        await show_template_choice(callback.message, state, "gpt", folder)


@template_router.callback_query(StateFilter(ProcessingStates.waiting_for_template_choice))
async def handle_template_choice(callback: CallbackQuery, state: FSMContext):
    """Handle template choice."""
    await callback.answer()
    
    if callback.data == "back_to_ai_choice":
        user_id = callback.from_user.id
        context = user_sessions[user_id].get("prompt_context", "initial")
        await show_ai_choice(callback.message, state, context=context)
        return
    elif callback.data == "back_to_gpt_folders":
        await show_gpt_folder_choice(callback.message, state)
        return
    
    if callback.data.startswith("template_"):
        parts = callback.data.split("_")
        if len(parts) >= 4:  # template_gpt_folder_filename
            ai_type = parts[1]
            folder = parts[2]
            template_filename = "_".join(parts[3:])  # Handle filenames with underscores
            await handle_template_selection(callback, state, ai_type, template_filename, folder)
        elif len(parts) >= 3:  # template_claude_filename or old format
            ai_type = parts[1]
            template_filename = "_".join(parts[2:])  # Handle filenames with underscores
            await handle_template_selection(callback, state, ai_type, template_filename)


@template_router.callback_query(StateFilter(ProcessingStates.waiting_for_story_change_confirmation))
async def handle_story_change_confirmation(callback: CallbackQuery, state: FSMContext):
    """Handle story change confirmation."""
    await callback.answer()
    
    user_id = callback.from_user.id
    
    if callback.data == "change_story_yes":
        await request_new_story_text(callback.message, state)
    elif callback.data == "change_story_no":
        await callback.message.edit_text("✅ Використовую шаблон без змін...")
        await finalize_template_selection(callback.message, state, user_id)


@template_router.callback_query(StateFilter(ProcessingStates.waiting_for_final_template_confirmation))
async def handle_final_template_confirmation(callback: CallbackQuery, state: FSMContext):
    """Handle final template confirmation."""
    await callback.answer()
    
    user_id = callback.from_user.id
    
    if callback.data == "confirm_final_template":
        await callback.message.edit_text("✅ Шаблон підтверджено!")
        await finalize_template_selection(callback.message, state, user_id)
    elif callback.data == "change_story_text":
        await request_new_story_text(callback.message, state)
    elif callback.data == "cancel_template":
        await callback.message.edit_text("❌ Вибір шаблону скасовано.")
        context = user_sessions[user_id].get("prompt_context", "initial")
        await show_ai_choice(callback.message, state, context=context)


@template_router.message(StateFilter(ProcessingStates.waiting_for_new_story_text))
async def handle_new_story_text(message: Message, state: FSMContext):
    """Handle new story text input."""
    story_text = message.text.strip()
    
    if not story_text:
        await message.answer("❌ Текст не може бути порожнім. Спробуйте ще раз.")
        return
    
    await replace_story_text(message, state, story_text)


@template_router.callback_query(F.data == "skip_sonnet_prompt", StateFilter(ProcessingStates.waiting_for_sonnet_prompt))
async def skip_sonnet_prompt_template(callback: CallbackQuery, state: FSMContext):
    """Handle skip Sonnet prompt button from template workflow."""
    await callback.answer()
    await callback.message.edit_text("⏩ Промт для Sonnet пропущено.")
    
    user_id = callback.from_user.id
    user_sessions[user_id]["sonnet_prompt"] = ""
    
    from .file_handlers import ask_volume_choice
    await ask_volume_choice(callback.message, state, user_id)