import asyncio
import os
import logging
from datetime import datetime
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaDocument
from aiogram.fsm.context import FSMContext

from .states import ProcessingStates
from .commands import user_sessions
from src.ai_services import AIOrchestrator

logger = logging.getLogger(__name__)

ai_orchestrator = AIOrchestrator()




async def start_automated_generation(message: Message, state: FSMContext, user_id: int):
    """Start the automated content generation process."""
    logger.info(f"🚀 Запуск автоматизованої генерації для користувача {user_id}")
    session = user_sessions[user_id]
    volume = session["target_volume"]
    multithread = session["multithread_mode"]
    
    logger.info(f"📊 Параметри: обсяг={volume}, багатопотоковий={multithread}")
    
    session["attempt_count"] = 0
    session["successful_attempts"] = 0
    session["valid_responses"] = 0
    session["invalid_responses"] = 0
    
    volume_mapping = {
        "15k": "15K",
        "30k": "30K",
        "40k": "40K", 
        "60k": "60K"
    }
    volume_text = volume_mapping.get(volume, volume.upper())
    mode_text = "багатопотоковому" if multithread else "стандартному"
    
    await message.answer(
        f"🚀 **Запуск автоматизованої генерації!**\n\n"
        f"📊 Цільовий обсяг: {volume_text} символів\n"
        f"🔄 Режим: {mode_text}\n\n"
        f"⏳ Починаю генерацію...",
        parse_mode="Markdown"
    )
    
    await process_with_automated_claude(message, state, user_id)


async def process_with_automated_claude(message: Message, state: FSMContext, user_id: int):
    """Automated processing with Claude Sonnet 4 with length control and file management."""
    try:
        session = user_sessions[user_id]
        outline = session["outline"]
        sonnet_prompt = session.get("sonnet_prompt", "")
        target_volume = session["target_volume"]
        multithread_mode = session["multithread_mode"]
        
        await state.set_state(ProcessingStates.processing)
        
        if target_volume == "15k":
            min_length, max_length = 15000, 20000
        elif target_volume == "30k":
            min_length, max_length = 28000, 34000
        elif target_volume == "40k":
            min_length, max_length = 40000, 50000
        else:  # 60k
            min_length, max_length = 56000, 68000
        
        progress_msg = await message.answer("🔄 Запуск автоматизованого процесу генерації...")
        
        # Use single request generation (removed multithread/concurrent mode)
        await process_single_request_generation(message, state, user_id, progress_msg, min_length, max_length)
            
    except Exception as e:
        logger.error(f"Error in automated processing: {e}")
        await message.answer(f"❌ Помилка під час обробки: {str(e)}")
        
        if user_id in user_sessions:
            del user_sessions[user_id]
        await state.clear()


async def process_single_request_generation(message: Message, state: FSMContext, user_id: int, 
                                         progress_msg: Message, min_length: int, max_length: int):
    """Single request generation process - one request at a time."""
    session = user_sessions[user_id]
    outline = session["outline"]
    sonnet_prompt = session.get("sonnet_prompt", "")
    
    found_valid = False
    max_attempts = 20  # Maximum attempts to prevent infinite loops
    
    while not found_valid and session["attempt_count"] < max_attempts:
        session["attempt_count"] += 1
        
        try:
            await progress_msg.edit_text(
                f"🔄 **Спроба {session['attempt_count']}/{max_attempts}**\n\n"
                f"📊 Цільовий діапазон: {min_length:,} - {max_length:,} символів\n"
                f"✅ Валідних відповідей: {session['valid_responses']}\n"
                f"❌ Невалідних відповідей: {session['invalid_responses']}"
            )
            
            result = await ai_orchestrator.claude_service.process_outline(
                outline,
                target_length=(min_length + max_length) // 2,
                sonnet_prompt=sonnet_prompt
            )
            
            found_valid = await save_generation_result(result, session, min_length, max_length, progress_msg)
            
            if not found_valid:
                await asyncio.sleep(1)  # Short delay before next attempt
            
        except Exception as e:
            logger.error(f"Error in generation attempt {session['attempt_count']}: {e}")
            await asyncio.sleep(3)  # Delay on error
            continue
    
    await finalize_generation(message, session, found_valid, max_attempts)





async def save_generation_result(result: str, session: dict, min_length: int, max_length: int, 
                               progress_msg: Message) -> bool:
    """Save generation result and return whether it's valid."""
    char_count = len(result)
    
    is_valid = min_length <= char_count <= max_length
    
    # Інкрементуємо лічильник успішних спроб (тільки для успішних генерацій)
    session["successful_attempts"] += 1
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds for uniqueness
    
    file_data = {
        "content": result,
        "char_count": char_count,
        "timestamp": timestamp,
        "attempt": session['attempt_count'],
        "successful_attempt": session['successful_attempts'],
        "min_length": min_length,
        "max_length": max_length
    }
    
    if is_valid:
        session["valid_responses"] += 1
        session["valid_files"].append(file_data)
        folder = "валідних"
    else:
        session["invalid_responses"] += 1
        session["invalid_files"].append(file_data)
        folder = "невалідних"
    
    status_emoji = "✅" if is_valid else "❌"
    status_text = "В ДІАПАЗОНІ" if is_valid else "ПОЗА ДІАПАЗОНОМ"
    
    await progress_msg.edit_text(
        f"{status_emoji} **Спроба {session['attempt_count']}: {status_text}**\n\n"
        f"📊 Символів: {char_count:,} (ціль: {min_length:,}-{max_length:,})\n"
        f"📁 Збережено в пам'яті ({folder})\n"
        f"✅ Валідних: {session['valid_responses']}\n"
        f"❌ Невалідних: {session['invalid_responses']}\n\n"
        f"{'🎉 ПРОЦЕС ЗАВЕРШЕНО!' if is_valid else '⏳ Продовжую генерацію...'}"
    )
    
    return is_valid





async def send_invalid_files(message: Message, session: dict):
    """Send all invalid files as separate files in one message to Telegram."""
    if not session["invalid_files"]:
        return
    
    temp_files = []
    input_files = []
    
    try:
        for i, file_data in enumerate(session["invalid_files"], 1):
            header = f"""# НЕВАЛІДНА ВІДПОВІДЬ #{i}
# Цільовий діапазон: {file_data['min_length']:,} - {file_data['max_length']:,}
# Час генерації: {datetime.fromtimestamp(int(file_data['timestamp'][:10])).strftime('%Y-%m-%d %H:%M:%S')}

"""
            
            temp_filename = f"invalid_response_{i}_{file_data['timestamp']}.txt"
            temp_path = f"/tmp/{temp_filename}"
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(header + file_data['content'])
            
            temp_files.append(temp_path)
            input_files.append(FSInputFile(temp_path))
        
        if len(input_files) == 1:
            await message.answer_document(
                input_files[0],
                caption=f"❌ **НЕВАЛІДНА ВІДПОВІДЬ**\n\n"
                       f"📊 Кількість символів: {session['invalid_files'][0]['char_count']:,}\n"
                       f"📄 Спроба #{session['invalid_files'][0]['attempt']}",
                parse_mode="Markdown"
            )
        else:
            batch_size = 10
            total_files = len(input_files)
            total_batches = (total_files + batch_size - 1) // batch_size  # Ceiling division
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, total_files)
                batch_files = input_files[start_idx:end_idx]
                
                media_group = []
                for i, input_file in enumerate(batch_files):
                    if batch_num == 0 and i == 0:
                        caption_text = f"❌ **НЕВАЛІДНІ ВІДПОВІДІ**\n\n"
                        caption_text += f"📊 Всього невалідних відповідей: {len(session['invalid_files'])}\n"
                        if total_batches > 1:
                            caption_text += f"📦 Частина {batch_num + 1} з {total_batches}\n"
                        caption_text += f"📄 Кожна відповідь в окремому файлі"
                        
                        media_group.append(InputMediaDocument(
                            media=input_file,
                            caption=caption_text,
                            parse_mode="Markdown"
                        ))
                    elif i == 0 and batch_num > 0:
                        media_group.append(InputMediaDocument(
                            media=input_file,
                            caption=f"📦 **Частина {batch_num + 1} з {total_batches}**",
                            parse_mode="Markdown"
                        ))
                    else:
                        media_group.append(InputMediaDocument(media=input_file))
                
                await message.answer_media_group(media_group)
                
                if batch_num < total_batches - 1:  # Don't delay after the last batch
                    await asyncio.sleep(1)
    
    finally:
        for temp_path in temp_files:
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.error(f"Error removing temp file {temp_path}: {e}")


async def finalize_generation(message: Message, session: dict, found_valid: bool, max_attempts: int):
    """Finalize the generation process and send results to user."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    user_id = message.chat.id
    
    if found_valid:
        if session["valid_files"]:
            latest_valid = session["valid_files"][-1]
            char_count = latest_valid["char_count"]
            
            temp_filename = f"final_result_{latest_valid['timestamp']}.txt"
            temp_path = f"/tmp/{temp_filename}"
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(latest_valid["content"])
            
            final_file = FSInputFile(temp_path)
            await message.answer_document(
                final_file,
                caption=f"🎉 **АВТОМАТИЗОВАНА ГЕНЕРАЦІЯ ЗАВЕРШЕНА!**\n\n"
                       f"📊 **Статистика:**\n"
                       f"• Загальна кількість спроб: {session['attempt_count']}\n"
                       f"• Успішних генерацій: {session['successful_attempts']}\n"
                       f"• Валідних відповідей: {session['valid_responses']}\n"
                       f"• Невалідних відповідей: {session['invalid_responses']}\n"
                       f"• Паузи в API: {session['attempt_count'] - session['successful_attempts']}\n"
                       f"• Фінальна довжина: {char_count:,} символів\n\n",
                parse_mode="Markdown"
            )
            
            os.remove(temp_path)
            
            await send_invalid_files(message, session)
        else:
            await message.answer("⚠️ Валідний файл не знайдено, хоча процес завершився успішно.")
    else:
        await message.answer(
            f"⚠️ **Досягнуто максимум спроб ({max_attempts})**\n\n"
            f"📊 **Статистика:**\n"
            f"• Загальна кількість спроб: {session['attempt_count']}\n"
            f"• Успішних генерацій: {session['successful_attempts']}\n"
            f"• Валідних відповідей: {session['valid_responses']}\n"
            f"• Невалідних відповідей: {session['invalid_responses']}\n"
            f"• Паузи в API: {session['attempt_count'] - session['successful_attempts']}\n\n",
            parse_mode="Markdown"
        )
        
        await send_invalid_files(message, session)
    
    # Add button for new processing after completion
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Запустити нову обробку", callback_data="start_new_processing")
        ],
        [
            InlineKeyboardButton(text="📊 Переглянути чергу", callback_data="view_queue")
        ]
    ])
    
    await message.answer(
        "**🔄 Що робити далі?**\n\n"
        "• **Запустити нову обробку** - додати новий проект в чергу\n"
        "• **Переглянути чергу** - подивитися статус всіх проектів\n"
        "• Використайте /start для повного перезапуску",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    # Don't delete session yet - keep it for potential new processing
    # if user_id in user_sessions:
    #     del user_sessions[user_id]