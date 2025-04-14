import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from src.config import BOT_TOKEN, ALLOWED_CHAT_IDS

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def mask_token(text: str) -> str:
    """Маскирует токен бота в тексте для безопасного логирования"""
    if BOT_TOKEN in text:
        return text.replace(BOT_TOKEN, "***TOKEN***")
    return text

def is_allowed_chat(chat_id: int) -> bool:
    """Проверка, разрешен ли чат для работы бота"""
    return not ALLOWED_CHAT_IDS or chat_id in ALLOWED_CHAT_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    if not is_allowed_chat(update.effective_chat.id):
        logger.warning(f"Попытка доступа из неразрешенного чата {update.effective_chat.id}")
        return
    
    user = update.effective_user
    await update.message.reply_text(
        f'Здравствуйте, {user.first_name}! 👋\n'
        f'Я бот для обработки отчетов агрономов.\n'
        f'Используйте /help для получения списка команд.'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    if not is_allowed_chat(update.effective_chat.id):
        logger.warning(f"Попытка доступа из неразрешенного чата {update.effective_chat.id}")
        return
    
    help_text = (
        'Доступные команды:\n'
        '/start - Начать работу с ботом\n'
        '/help - Показать это сообщение\n'
        '/status - Показать статус обработки отчетов\n\n'
        'Для отправки отчета просто отправьте сообщение в чат.'
    )
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик входящих сообщений"""
    if not is_allowed_chat(update.effective_chat.id):
        logger.warning(f"Попытка доступа из неразрешенного чата {update.effective_chat.id}")
        return
    
    try:
        message = update.message.text
        logger.info(f"Получено сообщение из чата {update.effective_chat.id}: {mask_token(message[:50])}...")
        
        # TODO: Добавить обработку сообщения через YandexGPT
        await update.message.reply_text(
            'Сообщение получено и будет обработано.\n'
            'Результаты обработки появятся в отчете.'
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await update.message.reply_text(
            'Произошла ошибка при обработке сообщения.\n'
            'Пожалуйста, попробуйте позже или обратитесь к администратору.'
        )

def main():
    """Основная функция запуска бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Добавляем обработчик сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота
    logger.info("Бот запущен")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 