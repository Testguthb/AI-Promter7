import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.config.settings import TELEGRAM_BOT_TOKEN
from src.bot import (
    commands_router,
    file_handlers_router,
    callbacks_router,
    template_router,
    misc_router,
    queue_router
)

logger = logging.getLogger(__name__)


class TelegramApp:
    """Main application class for the Telegram Text Processor Bot."""
    
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        
        self._register_routers()
    
    def _register_routers(self):
        """Register all routers with the dispatcher."""
        self.dp.include_router(commands_router)
        self.dp.include_router(file_handlers_router)
        self.dp.include_router(callbacks_router)
        self.dp.include_router(template_router)
        self.dp.include_router(queue_router)
        self.dp.include_router(misc_router)
        
        logger.info("All routers registered successfully")
    
    async def start(self):
        """Start the bot."""
        from src.core.project_queue import project_queue
        from src.core.project_notifications import notification_service
        
        logger.info("Starting Telegram Text Processor Bot...")
        
        # Start project queue processor
        await project_queue.start_queue_processor()
        
        # Start notification service
        await notification_service.start_notification_service()
        
        await self.bot.delete_webhook(drop_pending_updates=True)
        
        await self.dp.start_polling(self.bot)
    
    async def stop(self):
        """Stop the bot gracefully."""
        from src.core.project_queue import project_queue
        from src.core.project_notifications import notification_service
        
        logger.info("Stopping bot...")
        
        # Stop services
        await project_queue.stop_queue_processor()
        await notification_service.stop_notification_service()
        
        await self.bot.session.close()
        await self.storage.close()


app = TelegramApp()