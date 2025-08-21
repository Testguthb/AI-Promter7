import logging
import uuid
from datetime import datetime
from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext

from .commands import user_sessions
from .states import ProcessingStates
from src.core.project_queue import project_queue, ProjectTask, ProjectStatus

logger = logging.getLogger(__name__)

# Queue handlers router
queue_router = Router()


@queue_router.callback_query(lambda c: c.data == "start_new_processing")
async def start_new_processing_callback(callback: CallbackQuery, state: FSMContext):
    """Handle starting new processing."""
    await callback.answer()
    
    user_id = callback.from_user.id
    
    if user_id not in user_sessions:
        await callback.message.answer(
            "❌ Сесія не знайдена. Використайте /start для початку нової сесії."
        )
        return
    
    session = user_sessions[user_id]
    
    # Check if we have required data
    if not session.get("outline") or not session.get("target_volume"):
        await callback.message.answer(
            "❌ Недостатньо даних для нової обробки. Використайте /start для повного налаштування."
        )
        return
    
    # Show story type selection for new processing
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📚 Короткі історії", callback_data="queue_short_story"),
            InlineKeyboardButton(text="📖 Довгі історії", callback_data="queue_long_story")
        ],
        [
            InlineKeyboardButton(text="🔄 Використати поточні налаштування", callback_data="queue_current_settings")
        ]
    ])
    
    await callback.message.answer(
        "**🚀 Запуск нової обробки**\n\n"
        "Оберіть тип історій для нової обробки або використайте поточні налаштування:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@queue_router.callback_query(lambda c: c.data in ["queue_short_story", "queue_long_story", "queue_current_settings"])
async def handle_queue_story_selection(callback: CallbackQuery, state: FSMContext):
    """Handle story type selection for queue."""
    await callback.answer()
    
    user_id = callback.from_user.id
    session = user_sessions[user_id]
    
    if callback.data == "queue_short_story":
        # Load random short story
        await load_random_story(callback.message, user_id, "short")
    elif callback.data == "queue_long_story":
        # Load random long story
        await load_random_story(callback.message, user_id, "long")
    else:
        # Use current settings
        await add_project_to_queue(callback.message, user_id)


async def load_random_story(message: Message, user_id: int, story_type: str):
    """Load a random story and add to queue."""
    import os
    import random
    
    try:
        # Determine story directory
        story_dir = "/workspace/short-story" if story_type == "short" else "/workspace/long-story"
        
        # Get list of story files
        story_files = [f for f in os.listdir(story_dir) if f.endswith('.txt')]
        
        if not story_files:
            await message.answer(f"❌ Не знайдено файлів історій у директорії {story_type}")
            return
        
        # Select random story
        selected_file = random.choice(story_files)
        file_path = os.path.join(story_dir, selected_file)
        
        # Read story content
        with open(file_path, 'r', encoding='utf-8') as f:
            story_content = f.read().strip()
        
        # Update session with new story
        session = user_sessions[user_id]
        session["current_text"] = story_content
        
        await message.answer(
            f"📚 **Завантажено нову історію: {selected_file}**\n\n"
            f"📊 Розмір: {len(story_content):,} символів\n"
            f"🔄 Додаю до черги обробки...",
            parse_mode="Markdown"
        )
        
        # Add to queue
        await add_project_to_queue(message, user_id)
        
    except Exception as e:
        logger.error(f"Error loading random story: {e}")
        await message.answer(f"❌ Помилка завантаження історії: {str(e)}")


async def add_project_to_queue(message: Message, user_id: int):
    """Add a new project to the processing queue."""
    try:
        session = user_sessions[user_id]
        
        # Generate unique project ID
        project_id = f"project_{user_id}_{int(datetime.now().timestamp())}"
        
        # Get volume settings
        target_volume = session["target_volume"]
        if target_volume == "15k":
            min_length, max_length = 15000, 20000
        elif target_volume == "30k":
            min_length, max_length = 28000, 34000
        elif target_volume == "40k":
            min_length, max_length = 40000, 50000
        else:  # 60k
            min_length, max_length = 56000, 68000
        
        # Create project task
        task = ProjectTask(
            project_id=project_id,
            user_id=user_id,
            outline=session["outline"],
            sonnet_prompt=session.get("sonnet_prompt", ""),
            target_volume=target_volume,
            min_length=min_length,
            max_length=max_length
        )
        
        # Add to queue
        await project_queue.add_project(task)
        
        # Get queue stats
        stats = project_queue.get_queue_stats()
        
        await message.answer(
            f"✅ **Проект додано до черги!**\n\n"
            f"🆔 ID проекту: `{project_id}`\n"
            f"📊 Цільовий обсяг: {target_volume.upper()} ({min_length:,}-{max_length:,} символів)\n\n"
            f"📈 **Статистика черги:**\n"
            f"• В черзі: {stats['queued']}\n"
            f"• Обробляється: {stats['processing']}\n"
            f"• Завершено: {stats['completed']}\n"
            f"• Помилки: {stats['failed']}\n\n"
            f"🔄 Проект буде оброблений автоматично. Використайте кнопку 'Переглянути чергу' для відстеження статусу.",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error adding project to queue: {e}")
        await message.answer(f"❌ Помилка додавання проекту до черги: {str(e)}")


@queue_router.callback_query(lambda c: c.data == "view_queue")
async def view_queue_callback(callback: CallbackQuery):
    """Handle viewing queue status."""
    await callback.answer()
    
    user_id = callback.from_user.id
    
    # Get user projects
    user_projects = await project_queue.get_user_projects(user_id)
    
    if not user_projects:
        await callback.message.answer(
            "📋 У вас немає проектів у черзі.\n\n"
            "Використайте кнопку 'Запустити нову обробку' або /start для початку."
        )
        return
    
    # Sort projects by creation time
    user_projects.sort(key=lambda x: x.created_at, reverse=True)
    
    # Build status message
    status_text = "📊 **Ваші проекти:**\n\n"
    
    for i, project in enumerate(user_projects[:10], 1):  # Show last 10 projects
        status_emoji = {
            ProjectStatus.QUEUED: "⏳",
            ProjectStatus.PROCESSING: "🔄",
            ProjectStatus.COMPLETED: "✅",
            ProjectStatus.FAILED: "❌"
        }.get(project.status, "❓")
        
        status_text += f"{status_emoji} **Проект {i}** (`{project.project_id[-12:]}`)\n"
        status_text += f"   📅 {project.created_at.strftime('%H:%M:%S')}\n"
        status_text += f"   📊 {project.target_volume.upper()}\n"
        status_text += f"   🔄 Спроб: {project.attempt_count}\n"
        
        if project.status == ProjectStatus.COMPLETED:
            status_text += f"   ✅ Валідних: {project.valid_responses}\n"
        elif project.status == ProjectStatus.FAILED:
            status_text += f"   ❌ Помилка: {project.error_message[:50]}...\n"
        
        status_text += "\n"
    
    # Add queue stats
    stats = project_queue.get_queue_stats()
    status_text += f"📈 **Загальна статистика черги:**\n"
    status_text += f"• В черзі: {stats['queued']}\n"
    status_text += f"• Обробляється: {stats['processing']}\n"
    status_text += f"• Завершено: {stats['completed']}\n"
    status_text += f"• Помилки: {stats['failed']}"
    
    # Add refresh button
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Оновити", callback_data="view_queue"),
            InlineKeyboardButton(text="🚀 Нова обробка", callback_data="start_new_processing")
        ]
    ])
    
    await callback.message.answer(
        status_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@queue_router.callback_query(lambda c: c.data == "refresh_status")
async def refresh_status_callback(callback: CallbackQuery, state: FSMContext):
    """Handle refreshing status - same as /status command."""
    await callback.answer()
    
    # Import the status command function
    from .commands import status_command
    
    # Call the status command with callback message
    await status_command(callback.message, state)