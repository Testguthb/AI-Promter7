import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from .states import ProcessingStates

logger = logging.getLogger(__name__)

# Miscellaneous handlers router
misc_router = Router()


@misc_router.message()
async def handle_unknown(message: Message, state: FSMContext):
    """Handle unknown messages."""
    current_state = await state.get_state()
    
    if current_state == ProcessingStates.waiting_for_file:
        await message.answer("📄 Будь ласка, завантажте текстовий файл (.txt або .docx)")
    elif current_state == ProcessingStates.waiting_for_prompt:
        await message.answer("✏️ Введіть додатковий промт або натисніть 'Пропустити промт'")
    elif current_state == ProcessingStates.waiting_for_outline_approval:
        await message.answer("🤔 Будь ласка, підтвердьте або відхиліть outline, використовуючи кнопки")
    elif current_state == ProcessingStates.waiting_for_sonnet_prompt:
        await message.answer("✏️ Введіть промт для Claude Sonnet 4 або натисніть 'Пропустити промт'")
    elif current_state == ProcessingStates.waiting_for_volume_choice:
        await message.answer("📊 Оберіть цільовий обсяг (15K, 30K, 40K або 60K символів) використовуючи кнопки")

    elif current_state == ProcessingStates.processing:
        await message.answer("⏳ Зачекайте, йде автоматизована генерація контенту...")
    else:
        await message.answer("❓ Невідома команда. Використайте /help для довідки або /start для початку.")