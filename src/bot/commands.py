import logging
from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from .states import ProcessingStates

logger = logging.getLogger(__name__)

# Command handlers router
commands_router = Router()

# User sessions storage
user_sessions = {}


@commands_router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    """Handle /start command."""
    user_id = message.from_user.id
    user_sessions[user_id] = {
        "current_text": None,
        "outline": None,
        "custom_prompt": "",
        "sonnet_prompt": "",
        "target_volume": None,
        "multithread_mode": False,
        "attempt_count": 0,  # Загальна кількість спроб (включаючи exceptions)
        "successful_attempts": 0,  # Тільки успішні генерації (валідні + невалідні)
        "valid_responses": 0,
        "invalid_responses": 0,
        "progress_message": None,
        "valid_files": [],
        "invalid_files": [],
        "prompt_context": "initial"
    }
    
    welcome_text = """
🤖 **AI Workflow Automation System v2.0**

🚀 **Нові можливості:**
• **Черга проектів** - запускайте декілька обробок одночасно
• **Автоматичне керування лімітами** Claude Sonnet 4
• **Сповіщення** - отримуйте результати в реальному часі
• **Статистика** - відстежуйте всі свої проекти

**Повністю автоматизований процес:**
• **GPT-4.1** - для створення структурованого outline
• **Claude Sonnet 4** - для генерації з контролем довжини (1000 req/min)

**Процес:**
1. Завантажте файл → 2. Оберіть тип промту (шаблон або власний)
3. Налаштуйте параметри → 4. Підтвердьте outline
5. Оберіть обсяг → 6. Запустіть обробку
7. Додавайте нові проекти в чергу → 8. Отримуйте результати автоматично

Підтримувані формати: .txt, .docx | Макс. розмір: 10 MB
    """
    
    # Create keyboard with story type selection and manual upload option
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📚 Короткі історії", callback_data="select_short_story"),
            InlineKeyboardButton(text="📖 Довгі історії", callback_data="select_long_story")
        ],
        [
            InlineKeyboardButton(text="📄 Завантажити власний файл", callback_data="manual_upload")
        ]
    ])
    
    await message.answer(welcome_text, parse_mode="Markdown")
    await message.answer(
        "**Оберіть спосіб завантаження файлу:**\n\n"
        "• **Короткі історії** - випадковий вибір з колекції коротких історій\n"
        "• **Довгі історії** - випадковий вибір з колекції довгих історій\n"
        "• **Власний файл** - завантажте свій файл (.txt, .docx)",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    await state.set_state(ProcessingStates.waiting_for_file)


@commands_router.message(Command("help"))
async def help_command(message: Message):
    """Handle /help command."""
    help_text = """
**Доступні команди:**

/start - Почати роботу з ботом
/help - Показати це повідомлення
/cancel - Скасувати поточну операцію
/status - Показати статус паралельної обробки в реальному часі та активні потоки
/queue - Детальна інформація про чергу проектів

**🚀 Новий функціонал - Черга проектів:**
- **Множинні обробки** - запускайте декілька проектів одночасно
- **Автоматична черга** - система керує лімітами Claude Sonnet 4
- **Сповіщення** - отримуйте результати автоматично
- **Статистика** - відстежуйте всі свої проекти

**Процес роботи:**
1. **Завантаження файлу** - надішліть .txt або .docx файл
2. **Вибір промту** - оберіть GPT/Claude шаблон або введіть власний
3. **Налаштування шаблону** - для GPT можна змінити історію в шаблоні
4. **Генерація outline** - GPT-4.1 створить структурований план
5. **Підтвердження** - перевірте і підтвердьте outline
6. **Промт для Sonnet** - додайте інструкції для Claude (необов'язково)
7. **Вибір обсягу** - оберіть 15K (15-20K), 30K (28-34K), 40K (40-50K) або 60K (56-68K символів)
8. **Автоматична генерація** - один запит за раз з повним використанням лімітів
9. **Множинні проекти** - після завершення додавайте нові проекти в чергу
10. **Результати** - отримуйте файли автоматично після завершення

**🎯 Ліміти Claude Sonnet 4:**
- **1,000 запитів на хвилину**
- **450,000 вхідних токенів на хвилину**  
- **90,000 вихідних токенів на хвилину**

**🎯 Шаблони промтів:**
- **GPT шаблони** - готові промти з можливістю заміни історій
- **Claude шаблони** - спеціалізовані промти для генерації
- **Власні промти** - введіть власний текст для обробки

**Підтримка:**
- Формати файлів: .txt, .docx
- Максимальний розмір: 10 MB
- Без обмежень на кількість проектів
- Автоматичне керування чергою на основі API відповідей
    """
    
    await message.answer(help_text, parse_mode="Markdown")


@commands_router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    """Handle /cancel command."""
    user_id = message.from_user.id
    
    if user_id in user_sessions:
        session = user_sessions[user_id]
        
        # Send invalid files if any exist before cancelling
        if session.get("invalid_files"):
            from .processors import send_invalid_files
            await send_invalid_files(message, session)
        
        # Send cancellation message with statistics
        await message.answer(
            f"❌ **ГЕНЕРАЦІЯ СКАСОВАНА**\n\n"
            f"📊 **Статистика до моменту скасування:**\n"
            f"• Загальна кількість спроб: {session.get('attempt_count', 0)}\n"
            f"• Успішних генерацій: {session.get('successful_attempts', 0)}\n"
            f"• Валідних відповідей: {session.get('valid_responses', 0)}\n"
            f"• Невалідних відповідей: {session.get('invalid_responses', 0)}\n"
            f"• Паузи в API: {session.get('attempt_count', 0) - session.get('successful_attempts', 0)}\n\n"
            f"Використайте /start для нової генерації.",
            parse_mode="Markdown"
        )
        
        # Clean up session
        del user_sessions[user_id]
    else:
        # No active session
        await message.answer("❌ Операція скасована. Активних задач не знайдено. Використайте /start для початку.")
    
    await state.clear()


@commands_router.message(Command("status"))
async def status_command(message: Message, state: FSMContext):
    """Handle /status command - show real-time parallel processing statistics."""
    user_id = message.from_user.id
    current_state = await state.get_state()
    
    from src.core.project_queue import project_queue, ProjectStatus
    from datetime import datetime, timedelta
    
    # Get all processing information
    user_projects = await project_queue.get_user_projects(user_id)
    all_projects = list(project_queue.projects.values())
    
    # Build real-time status message
    status_info = "⚡ **СТАТУС ПАРАЛЕЛЬНОЇ ОБРОБКИ В РЕАЛЬНОМУ ЧАСІ**\n\n"
    
    # Get real-time processing statistics
    realtime_stats = project_queue.get_realtime_stats()
    processing_projects = [p for p in all_projects if p.status == ProjectStatus.PROCESSING]
    
    status_info += f"**🚀 Паралельна обробка Claude Sonnet 4:**\n"
    status_info += f"• 🔄 Активних потоків: **{realtime_stats['active_threads']}/{realtime_stats['max_concurrent']}**\n"
    
    if realtime_stats['active_threads'] > 0:
        status_info += f"• 📈 Загальна успішність: **{realtime_stats['total_success_rate']:.1f}%** ({realtime_stats['total_valid']}/{realtime_stats['total_attempts']} спроб)\n"
        status_info += f"• ⏱️ Середній час обробки: **{realtime_stats['avg_processing_time']/60:.1f} хв**\n"
        status_info += f"• ⚡ Середня швидкість: **{realtime_stats['avg_processing_speed']:.1f}** спроб/хв\n"
        status_info += f"• 🎯 Використання ресурсів: **{realtime_stats['resource_utilization']:.0f}%**\n"
    else:
        status_info += f"• 💤 Система в режимі очікування\n"
        
    status_info += "\n"
    
    # Show real-time processing details
    if processing_projects:
        status_info += f"**🔄 АКТИВНІ ПОТОКИ ОБРОБКИ ({len(processing_projects)}):**\n\n"
        for i, project in enumerate(processing_projects, 1):
            user_marker = "👤 (Ваш)" if project.user_id == user_id else "👥 (Інший користувач)"
            
            # Use real-time tracking data
            processing_minutes = project.total_processing_time / 60 if project.total_processing_time > 0 else 0
            current_success_rate = (project.valid_responses / project.attempt_count * 100) if project.attempt_count > 0 else 0
            
            # Show last attempt time if available
            last_attempt_info = ""
            if project.last_attempt_at:
                seconds_since_last = (datetime.now() - project.last_attempt_at).total_seconds()
                if seconds_since_last < 60:
                    last_attempt_info = f" (остання спроба {seconds_since_last:.0f}с тому)"
                else:
                    last_attempt_info = f" (остання спроба {seconds_since_last/60:.1f}хв тому)"
            
            status_info += f"**{i}.** `{project.project_id[-12:]}` {user_marker}\n"
            status_info += f"   ⏱️ Активний: **{processing_minutes:.1f} хв**{last_attempt_info}\n"
            status_info += f"   📊 Обсяг: {project.target_volume.upper()}\n"
            status_info += f"   🎯 Поточна успішність: **{current_success_rate:.1f}%**\n"
            status_info += f"   🔄 Спроб: {project.attempt_count} (✅ {project.valid_responses}, ❌ {project.invalid_responses})\n"
            status_info += f"   ⚡ Швидкість: **{project.current_processing_speed:.1f}** спроб/хв\n\n"
    
    # Show waiting projects (if any)
    queued_projects = [p for p in all_projects if p.status == ProjectStatus.QUEUED]
    if queued_projects:
        status_info += f"**⏳ ОЧІКУЮТЬ ПОЧАТКУ ОБРОБКИ ({len(queued_projects)}):**\n\n"
        for i, project in enumerate(queued_projects[:3], 1):  # Show only first 3
            user_marker = "👤 (Ваш)" if project.user_id == user_id else "👥 (Інший користувач)"
            wait_time = (datetime.now() - project.created_at).total_seconds() / 60
            status_info += f"**{i}.** `{project.project_id[-12:]}` {user_marker}\n"
            status_info += f"   ⏰ Очікує: **{wait_time:.1f} хв**\n"
            status_info += f"   📊 Обсяг: {project.target_volume.upper()}\n\n"
        
        if len(queued_projects) > 3:
            status_info += f"   ... та ще **{len(queued_projects) - 3}** проектів\n\n"
    
    # Show user's personal session info if exists
    if user_id in user_sessions:
        session = user_sessions[user_id]
        template_info = session.get('selected_template', {})
        template_name = template_info.get('filename', 'Не обрано')
        template_ai_type = template_info.get('ai_type', 'Не обрано')
        
        status_info += f"**👤 ВАША ПОТОЧНА СЕСІЯ:**\n\n"
        status_info += f"**Стан:** {current_state or 'Очікування'}\n"
        status_info += f"**Файл завантажено:** {'✅' if session.get('current_text') else '❌'}\n"
        status_info += f"**Outline готовий:** {'✅' if session.get('outline') else '❌'}\n"
        status_info += f"**Тип промту:** {template_ai_type.upper() if template_ai_type != 'Не обрано' else 'Власний/Не обрано'}\n"
        status_info += f"**Шаблон:** {template_name[:30]}{'...' if len(template_name) > 30 else ''}\n"
        status_info += f"**Цільовий обсяг:** {session.get('target_volume', 'Не обрано')}\n"
        
        if session.get('attempt_count', 0) > 0:
            status_info += f"**Статистика сесії:** {session.get('attempt_count', 0)} спроб, "
            status_info += f"{session.get('valid_responses', 0)} валідних\n"
        
        status_info += "\n"
    
    # Show user's projects with real-time performance
    if user_projects:
        recent_projects = sorted(user_projects, key=lambda x: x.created_at, reverse=True)[:5]
        status_info += f"**📋 ВАШІ ПРОЕКТИ ({len(user_projects)} всього):**\n\n"
        
        for i, project in enumerate(recent_projects, 1):
            status_emoji = {
                ProjectStatus.QUEUED: "⏳",
                ProjectStatus.PROCESSING: "🔄", 
                ProjectStatus.COMPLETED: "✅",
                ProjectStatus.FAILED: "❌"
            }.get(project.status, "❓")
            
            status_info += f"{status_emoji} **{i}.** `{project.project_id[-12:]}`"
            
            if project.status == ProjectStatus.PROCESSING:
                processing_time = (datetime.now() - project.created_at).total_seconds() / 60
                current_rate = (project.valid_responses / project.attempt_count * 100) if project.attempt_count > 0 else 0
                status_info += f" **АКТИВНИЙ** ({processing_time:.1f} хв, {current_rate:.0f}% успішність)\n"
            elif project.status == ProjectStatus.COMPLETED:
                total_time = (datetime.now() - project.created_at).total_seconds() / 60
                final_rate = (project.valid_responses / project.attempt_count * 100) if project.attempt_count > 0 else 0
                status_info += f" завершено ({total_time:.1f} хв, {final_rate:.0f}% успішність)\n"
            elif project.status == ProjectStatus.FAILED:
                failed_time = (datetime.now() - project.created_at).total_seconds() / 60
                status_info += f" помилка після {failed_time:.1f} хв\n"
            else:
                wait_time = (datetime.now() - project.created_at).total_seconds() / 60
                status_info += f" очікує {wait_time:.1f} хв\n"
            
            status_info += f"   📅 {project.created_at.strftime('%d.%m %H:%M:%S')}, 📊 {project.target_volume.upper()}\n"
            if project.attempt_count > 0:
                status_info += f"   📈 Спроби: {project.attempt_count}, Валідні: {project.valid_responses}\n"
            status_info += "\n"
    
    # Add action buttons focused on real-time monitoring
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Оновити в реальному часі", callback_data="refresh_status"),
            InlineKeyboardButton(text="📊 Детальна статистика", callback_data="view_detailed_stats")
        ],
        [
            InlineKeyboardButton(text="🚀 Нова обробка", callback_data="start_new_processing")
        ]
    ])
    
    await message.answer(status_info, reply_markup=keyboard, parse_mode="Markdown")


@commands_router.message(Command("queue"))
async def queue_command(message: Message):
    """Handle /queue command - show detailed queue information."""
    from src.core.project_queue import project_queue, ProjectStatus
    
    user_id = message.from_user.id
    
    # Get user projects
    user_projects = await project_queue.get_user_projects(user_id)
    queue_stats = project_queue.get_queue_stats()
    
    if not user_projects and queue_stats['total_projects'] == 0:
        await message.answer(
            "📋 **Черга проектів порожня**\n\n"
            "Використайте /start для запуску нової обробки.",
            parse_mode="Markdown"
        )
        return
    
    # Build detailed queue message
    queue_text = "📊 **ДЕТАЛЬНА ІНФОРМАЦІЯ ПРО ЧЕРГУ**\n\n"
    
    # Global stats
    queue_text += f"**🌐 Загальна статистика:**\n"
    queue_text += f"• В черзі: {queue_stats['queued']}\n"
    queue_text += f"• Обробляється: {queue_stats['processing']}\n"
    queue_text += f"• Завершено: {queue_stats['completed']}\n"
    queue_text += f"• Помилки: {queue_stats['failed']}\n"
    queue_text += f"• Всього проектів: {queue_stats['total_projects']}\n\n"
    
    if user_projects:
        # Sort projects by creation time
        user_projects.sort(key=lambda x: x.created_at, reverse=True)
        
        queue_text += f"**👤 Ваші проекти ({len(user_projects)}):**\n\n"
        
        for i, project in enumerate(user_projects[:15], 1):  # Show last 15 projects
            status_emoji = {
                ProjectStatus.QUEUED: "⏳",
                ProjectStatus.PROCESSING: "🔄",
                ProjectStatus.COMPLETED: "✅",
                ProjectStatus.FAILED: "❌"
            }.get(project.status, "❓")
            
            queue_text += f"{status_emoji} **{i}.** `{project.project_id[-12:]}`\n"
            queue_text += f"   📅 {project.created_at.strftime('%d.%m %H:%M:%S')}\n"
            queue_text += f"   📊 {project.target_volume.upper()}\n"
            queue_text += f"   🔄 Спроб: {project.attempt_count}"
            
            if project.status == ProjectStatus.PROCESSING:
                queue_text += f" (обробляється...)"
            elif project.status == ProjectStatus.COMPLETED:
                queue_text += f", ✅ Валідних: {project.valid_responses}"
            elif project.status == ProjectStatus.FAILED:
                queue_text += f", ❌ Помилка"
            
            queue_text += "\n\n"
    
    # Create keyboard with actions
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Оновити", callback_data="view_queue"),
            InlineKeyboardButton(text="🚀 Нова обробка", callback_data="start_new_processing")
        ]
    ])
    
    await message.answer(queue_text, reply_markup=keyboard, parse_mode="Markdown")