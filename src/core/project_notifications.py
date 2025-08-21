import asyncio
import logging
import os
from datetime import datetime
from typing import Dict

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from .project_queue import project_queue, ProjectStatus
from src.config.settings import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)


class ProjectNotificationService:
    """Service to notify users about completed projects."""
    
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self._notification_task = None
        self._notified_projects = set()
    
    async def start_notification_service(self):
        """Start the notification service."""
        if self._notification_task is None or self._notification_task.done():
            self._notification_task = asyncio.create_task(self._notification_loop())
            logger.info("Project notification service started")
    
    async def stop_notification_service(self):
        """Stop the notification service."""
        if self._notification_task and not self._notification_task.done():
            self._notification_task.cancel()
            try:
                await self._notification_task
            except asyncio.CancelledError:
                pass
            logger.info("Project notification service stopped")
    
    async def _notification_loop(self):
        """Main notification loop."""
        while True:
            try:
                await self._check_and_notify_completed_projects()
                await asyncio.sleep(5)  # Check every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in notification loop: {e}")
                await asyncio.sleep(10)
    
    async def _check_and_notify_completed_projects(self):
        """Check for completed projects and notify users."""
        # Get all projects
        for project_id, project in project_queue.projects.items():
            if (project.status == ProjectStatus.COMPLETED and 
                project_id not in self._notified_projects):
                
                await self._notify_project_completed(project)
                self._notified_projects.add(project_id)
            
            elif (project.status == ProjectStatus.FAILED and 
                  project_id not in self._notified_projects):
                
                await self._notify_project_failed(project)
                self._notified_projects.add(project_id)
    
    async def _notify_project_completed(self, project):
        """Notify user about completed project."""
        try:
            if project.valid_files:
                latest_valid = project.valid_files[-1]
                char_count = latest_valid["char_count"]
                
                # Create temporary file
                temp_filename = f"project_result_{project.project_id}_{latest_valid['timestamp']}.txt"
                temp_path = f"/tmp/{temp_filename}"
                
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(latest_valid["content"])
                
                final_file = FSInputFile(temp_path)
                
                # Create keyboard for next actions
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="🚀 Запустити нову обробку", callback_data="start_new_processing")
                    ],
                    [
                        InlineKeyboardButton(text="📊 Переглянути чергу", callback_data="view_queue")
                    ]
                ])
                
                await self.bot.send_document(
                    chat_id=project.user_id,
                    document=final_file,
                    caption=f"🎉 **ПРОЕКТ ЗАВЕРШЕНО!**\n\n"
                           f"🆔 ID: `{project.project_id[-12:]}`\n"
                           f"📊 **Статистика:**\n"
                           f"• Загальна кількість спроб: {project.attempt_count}\n"
                           f"• Успішних генерацій: {project.successful_attempts}\n"
                           f"• Валідних відповідей: {project.valid_responses}\n"
                           f"• Невалідних відповідей: {project.invalid_responses}\n"
                           f"• Фінальна довжина: {char_count:,} символів\n\n"
                           f"⏱️ Час обробки: {(datetime.now() - project.created_at).total_seconds():.1f} сек",
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                
                # Clean up temp file
                os.remove(temp_path)
                
                # Send invalid files if any
                if project.invalid_files:
                    await self._send_project_invalid_files(project)
                
                logger.info(f"Notified user {project.user_id} about completed project {project.project_id}")
            
        except Exception as e:
            logger.error(f"Error notifying user about completed project {project.project_id}: {e}")
    
    async def _notify_project_failed(self, project):
        """Notify user about failed project."""
        try:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 Спробувати знову", callback_data="start_new_processing")
                ],
                [
                    InlineKeyboardButton(text="📊 Переглянути чергу", callback_data="view_queue")
                ]
            ])
            
            await self.bot.send_message(
                chat_id=project.user_id,
                text=f"❌ **ПРОЕКТ НЕ ВДАВСЯ**\n\n"
                     f"🆔 ID: `{project.project_id[-12:]}`\n"
                     f"📊 **Статистика:**\n"
                     f"• Загальна кількість спроб: {project.attempt_count}\n"
                     f"• Успішних генерацій: {project.successful_attempts}\n"
                     f"• Валідних відповідей: {project.valid_responses}\n"
                     f"• Невалідних відповідей: {project.invalid_responses}\n\n"
                     f"❌ Помилка: {project.error_message}\n\n"
                     f"⏱️ Час спроб: {(datetime.now() - project.created_at).total_seconds():.1f} сек",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Send invalid files if any
            if project.invalid_files:
                await self._send_project_invalid_files(project)
            
            logger.info(f"Notified user {project.user_id} about failed project {project.project_id}")
            
        except Exception as e:
            logger.error(f"Error notifying user about failed project {project.project_id}: {e}")
    
    async def _send_project_invalid_files(self, project):
        """Send invalid files from a project to the user."""
        if not project.invalid_files:
            return
        
        try:
            temp_files = []
            
            for i, file_data in enumerate(project.invalid_files, 1):
                header = f"""# НЕВАЛІДНА ВІДПОВІДЬ #{i} - ПРОЕКТ {project.project_id[-12:]}
# Цільовий діапазон: {file_data['min_length']:,} - {file_data['max_length']:,}
# Час генерації: {datetime.fromtimestamp(int(file_data['timestamp'][:10])).strftime('%Y-%m-%d %H:%M:%S')}

"""
                
                temp_filename = f"invalid_{project.project_id}_{i}_{file_data['timestamp']}.txt"
                temp_path = f"/tmp/{temp_filename}"
                
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(header + file_data['content'])
                
                temp_files.append(temp_path)
            
            # Send files in batches
            batch_size = 5
            for i in range(0, len(temp_files), batch_size):
                batch = temp_files[i:i+batch_size]
                
                if len(batch) == 1:
                    await self.bot.send_document(
                        chat_id=project.user_id,
                        document=FSInputFile(batch[0]),
                        caption=f"❌ **НЕВАЛІДНА ВІДПОВІДЬ** - Проект `{project.project_id[-12:]}`"
                    )
                else:
                    # Send files individually instead of media group for better compatibility
                    for j, file_path in enumerate(batch):
                        if j == 0:
                            await self.bot.send_document(
                                chat_id=project.user_id,
                                document=FSInputFile(file_path),
                                caption=f"❌ **НЕВАЛІДНІ ВІДПОВІДІ** - Проект `{project.project_id[-12:]}` (частина {i//batch_size + 1})"
                            )
                        else:
                            await self.bot.send_document(
                                chat_id=project.user_id,
                                document=FSInputFile(file_path)
                            )
                
                await asyncio.sleep(1)  # Delay between batches
            
            # Clean up temp files
            for temp_path in temp_files:
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.error(f"Error removing temp file {temp_path}: {e}")
                    
        except Exception as e:
            logger.error(f"Error sending invalid files for project {project.project_id}: {e}")


# Global notification service instance
notification_service = ProjectNotificationService()