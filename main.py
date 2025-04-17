import logging
import os
import asyncio
from datetime import datetime, time
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram._message import Message
from src.config import TELEGRAM_BOT_TOKEN, ALLOWED_CHAT_IDS, YANDEX_FOLDER_ID, ADMIN_USER_IDS
from src.yandex_gpt import YandexGPT
from src.file_handler import FileHandler
from telegram import PhotoSize
import json

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация обработчика файлов
file_handler = FileHandler(team_name="LAM")

# Инициализация YandexGPT
gpt = YandexGPT('service-account-key.json', YANDEX_FOLDER_ID)

# Глобальная переменная для хранения чата для отправки отчетов
report_chat_id = None
# Переменная для хранения времени отправки отчетов
report_time = time(7, 0)  # По умолчанию 7:00
# Флаг статуса автоматической отправки отчетов
auto_report_enabled = False

def mask_token(text: str) -> str:
    """Маскирует токен бота в тексте для безопасного логирования"""
    if TELEGRAM_BOT_TOKEN in text:
        return text.replace(TELEGRAM_BOT_TOKEN, "***TOKEN***")
    return text

def is_allowed_chat(chat_id: int) -> bool:
    """Проверка, разрешен ли чат для работы бота"""
    return not ALLOWED_CHAT_IDS or chat_id in ALLOWED_CHAT_IDS

async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверяет, является ли пользователь администратором бота"""
    user_id = update.effective_user.id
    if not ADMIN_USER_IDS or user_id not in ADMIN_USER_IDS:
        await update.message.reply_text(
            "❌ У вас нет прав администратора для выполнения этой команды."
        )
        logger.warning(f"Попытка доступа к административной команде от пользователя {update.effective_user.username} (ID: {user_id})")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    if not is_allowed_chat(update.effective_chat.id):
        logger.warning(f"Попытка доступа из неразрешенного чата {update.effective_chat.id}")
        return
    
    await update.message.reply_text(
        "Привет! Я бот для обработки сообщений от агрономов. "
        "Я буду сохранять все сообщения, анализировать их с помощью YandexGPT и сохранять в Excel.\n\n"
        "📝 ВАЖНО: После каждого полученного сообщения я автоматически обновляю Excel-таблицу!\n\n"
        "Доступные команды:\n"
        "/help - показать эту справку\n"
        "/export - экспортировать данные в Excel в формате для агрономов\n"
        "/stats - показать статистику обработанных сообщений\n"
        "/schedule - настроить автоматическую отправку отчетов"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет справку о командах бота"""
    if not is_allowed_chat(update.effective_chat.id):
        logger.warning(f"Попытка доступа из неразрешенного чата {update.effective_chat.id}")
        return
        
    help_text = (
        "🤖 Я - бот для обработки сельскохозяйственных данных!\n\n"
        "📝 *Как пользоваться:*\n"
        "1. Просто напишите мне сообщение с данными в свободной форме\n"
        "2. Я проанализирую его с помощью ИИ и добавлю в базу данных\n"
        "3. Вы можете скачать отчет Excel в любой момент\n\n"
        "🔍 *Формат сообщений:*\n"
        "• Укажите тип работы (Пахота, Дискование и т.д.)\n"
        "• Данные ПУ в формате: `По Пу 123/456`\n"
        "• Данные отделов: `Отд 12 123/456`\n\n"
        "📊 *Команды:*\n"
        "/start - Запуск бота\n"
        "/help - Показать эту справку\n"
        "/export - Экспортировать данные в Excel\n"
        "/stats - Показать статистику обработанных сообщений\n"
        "/schedule - Настроить автоматическую отправку отчетов\n"
        "/reset - Очистить все данные и начать с чистого листа (только для админов)\n\n"
        "📱 Бот разработан командой Lenin Agro Monitor"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /export"""
    if not is_allowed_chat(update.effective_chat.id):
        logger.warning(f"Попытка доступа из неразрешенного чата {update.effective_chat.id}")
        return
    
    await update.message.reply_text("Экспортирую данные в Excel в стандартном формате для отчетности...")
    
    try:
        # Обновляем Excel файл
        excel_path = file_handler.update_excel()
        
        # Отправляем файл пользователю
        await update.message.reply_document(
            document=open(excel_path, 'rb'),
            caption=(
                "Данные успешно экспортированы в Excel. Таблица содержит колонки: "
                "Дата, Подразделение, Операция, Культура, За день (га), С начала операции (га), Вал за день (ц), Вал с начала (ц).\n\n"
                "⚠️ ПРИМЕЧАНИЕ: Ячейки с желтой подсветкой содержат данные, которые не удалось точно идентифицировать."
            )
        )
        
        logger.info(f"Данные экспортированы в файл: {excel_path}")
        
    except Exception as e:
        logger.error(f"Ошибка при экспорте данных: {e}")
        await update.message.reply_text(f"Произошла ошибка при экспорте данных: {str(e)}")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /stats"""
    if not is_allowed_chat(update.effective_chat.id):
        logger.warning(f"Попытка доступа из неразрешенного чата {update.effective_chat.id}")
        return
    
    try:
        # Получаем статистику
        stats = file_handler.get_statistics()
        
        # Формируем сообщение со статистикой
        total_messages = stats["total_messages"]
        senders_info = "\n".join([f"- {sender}: {count} сообщений" for sender, count in stats["senders"].items()])
        
        last_excel_info = ""
        if "last_excel" in stats and stats["last_excel"]:
            last_excel_info = (
                f"\n\n📊 Последний Excel-файл:\n"
                f"Путь: {stats['last_excel']}"
            )
            if "last_excel_modified" in stats:
                last_excel_info += f"\nПоследнее обновление: {stats['last_excel_modified']}"
        
        stats_message = (
            f"📊 Статистика обработанных сообщений:\n\n"
            f"Всего обработано: {total_messages} сообщений\n\n"
            f"По отправителям:\n{senders_info}\n\n"
            f"Сообщения сохранены в директории: {file_handler.messages_path}{last_excel_info}"
        )
        
        # Добавляем кнопку для экспорта в Excel
        keyboard = [
            [InlineKeyboardButton("Экспортировать в Excel", callback_data="export_excel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(stats_message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await update.message.reply_text(f"Произошла ошибка при получении статистики: {str(e)}")

async def schedule_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /schedule"""
    if not is_allowed_chat(update.effective_chat.id):
        logger.warning(f"Попытка доступа из неразрешенного чата {update.effective_chat.id}")
        return
    
    global report_chat_id, auto_report_enabled
    
    # Сохраняем ID чата для отправки отчетов
    report_chat_id = update.effective_chat.id
    
    # Создаем клавиатуру с настройками времени
    keyboard = [
        [
            InlineKeyboardButton("6:00", callback_data="schedule_time_6"),
            InlineKeyboardButton("7:00", callback_data="schedule_time_7"),
            InlineKeyboardButton("8:00", callback_data="schedule_time_8")
        ],
        [
            InlineKeyboardButton("Включить автоотправку", callback_data="schedule_enable"),
            InlineKeyboardButton("Выключить автоотправку", callback_data="schedule_disable")
        ],
        [
            InlineKeyboardButton("Отправить отчет сейчас", callback_data="send_report_now")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status = "включена" if auto_report_enabled else "выключена"
    
    await update.message.reply_text(
        f"Настройка автоматической отправки отчетов.\n\n"
        f"Текущее время отправки: {report_time.hour}:00\n"
        f"Статус автоотправки: {status}\n"
        f"Выберите новое время или настройки:",
        reply_markup=reply_markup
    )

async def send_scheduled_report():
    """Отправляет запланированный отчет"""
    global report_chat_id
    
    if not report_chat_id or not auto_report_enabled:
        logger.info("Автоматическая отправка отчетов отключена или не настроена")
        return
    
    try:
        # Обновляем Excel файл
        excel_path = file_handler.update_excel()
        
        # Отправляем файл в указанный чат
        await context.bot.send_document(
            chat_id=report_chat_id,
            document=open(excel_path, 'rb'),
            caption=f"Автоматический отчет за {datetime.now().strftime('%d.%m.%Y')}"
        )
        
        logger.info(f"Автоматический отчет отправлен в чат {report_chat_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке автоматического отчета: {e}")
        if report_chat_id:
            await context.bot.send_message(
                chat_id=report_chat_id,
                text=f"Ошибка при отправке автоматического отчета: {str(e)}"
            )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    global report_time, auto_report_enabled
    
    if query.data == "export_excel":
        await query.edit_message_text(text="Экспортирую данные в Excel в стандартном формате...")
        
        try:
            # Обновляем Excel файл
            excel_path = file_handler.update_excel()
            
            # Отправляем файл пользователю
            await query.message.reply_document(
                document=open(excel_path, 'rb'),
                caption="Данные успешно экспортированы в Excel в стандартном формате АОР. Ячейки с желтой подсветкой содержат данные, которые не удалось точно идентифицировать."
            )
            
            await query.edit_message_text(text="Данные успешно экспортированы в Excel")
            logger.info(f"Данные экспортированы в файл: {excel_path}")
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте данных: {e}")
            await query.edit_message_text(text=f"Произошла ошибка при экспорте данных: {str(e)}")
    
    elif query.data.startswith("schedule_time_"):
        # Устанавливаем время отправки отчетов
        hour = int(query.data.split("_")[-1])
        report_time = time(hour, 0)
        
        status = "включена" if auto_report_enabled else "выключена"
        await query.edit_message_text(
            f"Время отправки отчетов установлено на {hour}:00\n"
            f"Статус автоотправки: {status}"
        )
    
    elif query.data == "schedule_enable":
        # Включаем автоматическую отправку отчетов
        auto_report_enabled = True
        await query.edit_message_text(
            f"Автоматическая отправка отчетов включена.\n"
            f"Время отправки: {report_time.hour}:00"
        )
    
    elif query.data == "schedule_disable":
        # Выключаем автоматическую отправку отчетов
        auto_report_enabled = False
        await query.edit_message_text(
            f"Автоматическая отправка отчетов выключена."
        )
    
    elif query.data == "send_report_now":
        # Отправляем отчет немедленно
        await query.edit_message_text(text="Отправляю отчет...")
        
        try:
            # Обновляем Excel файл
            excel_path = file_handler.update_excel()
            
            # Отправляем файл пользователю
            await query.message.reply_document(
                document=open(excel_path, 'rb'),
                caption=f"Отчет за {datetime.now().strftime('%d.%m.%Y')}"
            )
            
            await query.edit_message_text(text="Отчет успешно отправлен")
            logger.info(f"Отчет отправлен вручную")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке отчета: {e}")
            await query.edit_message_text(text=f"Произошла ошибка при отправке отчета: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    if not is_allowed_chat(update.effective_chat.id):
        logger.warning(f"Попытка доступа из неразрешенного чата {update.effective_chat.id}")
        return
    
    try:
        # Получаем информацию о сообщении
        message = update.message
        sender_name = message.from_user.first_name or "Unknown"
        message_text = message.text
        
        logger.info(f"Получено сообщение от {sender_name}: {mask_token(message_text[:50])}...")
        
        # Отправляем сообщение "обрабатываю..."
        process_message = await message.reply_text("🔄 Обрабатываю сообщение с помощью YandexGPT и обновляю Excel-таблицу...")
        
        # Сохраняем сообщение в файл и одновременно анализируем его с YandexGPT
        file_path, extracted_data = await file_handler.save_message(sender_name, message_text, gpt)
        logger.info(f"Сообщение сохранено в файл: {file_path}")
        
        # Удаляем сообщение "обрабатываю..."
        await process_message.delete()
        
        # Формируем ответ с извлеченными данными
        response = "✅ Сообщение получено, обработано YandexGPT и добавлено в Excel-таблицу\n\n"
        
        if "error" in extracted_data:
            # Используем обычный анализ, если YandexGPT не справился
            extracted_data = file_handler.parse_message(message_text)
            response += "⚠️ Анализ с помощью YandexGPT не удался, использую базовый анализ.\n\n"
        
        if "operations" in extracted_data and extracted_data["operations"]:
            response += f"📋 YandexGPT обнаружил {len(extracted_data['operations'])} операций:\n\n"
            
            for i, operation in enumerate(extracted_data["operations"], 1):
                response += f"🔹 Операция #{i}:\n"
                
                if "work_type" in operation and operation["work_type"]:
                    response += f"  🚜 Тип работы: {operation['work_type']}\n"
                    
                if "operation" in operation and operation["operation"]:
                    response += f"  📝 Операция: {operation['operation']}\n"
                    
                if "culture_from" in operation and operation["culture_from"]:
                    response += f"  🌱 Исходная культура: {operation['culture_from']}\n"
                    
                if "culture_to" in operation and operation["culture_to"]:
                    response += f"  🌾 Целевая культура: {operation['culture_to']}\n"
                    
                if "department" in operation and operation["department"]:
                    response += f"  🏢 Отдел: {operation['department']}\n"
                    
                if "department_number" in operation and "department_area" in operation:
                    if operation["department_number"] and operation["department_area"]:
                        response += f"  📊 Номер/площадь отдела: {operation['department_number']}/{operation['department_area']}\n"
                    
                if "pu_number" in operation and "pu_area" in operation:
                    if operation["pu_number"] and operation["pu_area"]:
                        response += f"  🔢 ПУ номер/площадь: {operation['pu_number']}/{operation['pu_area']}\n"
                
                response += "\n"
                
            if "corrections" in extracted_data and extracted_data["corrections"]:
                response += f"\n⚠️ Исправления: {extracted_data['corrections']}\n"
        
        elif extracted_data:
            response += "📋 Извлеченные данные:\n"
            
            if "work_type" in extracted_data and extracted_data["work_type"]:
                response += f"🚜 Тип работы: {extracted_data['work_type']}\n"
                
            if "culture_from" in extracted_data and extracted_data["culture_from"]:
                response += f"🌱 Исходная культура: {extracted_data['culture_from']}\n"
                
            if "culture_to" in extracted_data and extracted_data["culture_to"]:
                response += f"🌾 Целевая культура: {extracted_data['culture_to']}\n"
                
            if "department" in extracted_data and extracted_data["department"]:
                response += f"🏢 Отдел: {extracted_data['department']}\n"
                
            if "department_number" in extracted_data and "department_area" in extracted_data:
                if extracted_data["department_number"] and extracted_data["department_area"]:
                    response += f"📊 Номер/площадь отдела: {extracted_data['department_number']}/{extracted_data['department_area']}\n"
                
            if "pu_number" in extracted_data and "pu_area" in extracted_data:
                if extracted_data["pu_number"] and extracted_data["pu_area"]:
                    response += f"🔢 ПУ номер/площадь: {extracted_data['pu_number']}/{extracted_data['pu_area']}\n"
                    
            if "corrections" in extracted_data and extracted_data["corrections"]:
                response += f"\n⚠️ Исправления: {extracted_data['corrections']}\n"
                
        else:
            response += "⚠️ Не удалось извлечь структурированные данные из сообщения.\n"
        
        # Добавляем сообщение о том, что Excel-файл обновлен автоматически
        response += "\n📊 Excel-таблица автоматически обновлена с использованием анализа YandexGPT!"
        
        # Добавляем кнопку для экспорта в Excel
        keyboard = [
            [InlineKeyboardButton("Скачать текущий Excel-файл", callback_data="export_excel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем подтверждение
        await message.reply_text(response, reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await message.reply_text(f"Произошла ошибка при обработке сообщения: {str(e)}")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сбрасывает все данные бота и начинает с чистого листа"""
    if not await check_admin(update, context):
        return
    
    try:
        # Очищаем кэш анализа и историю
        result = file_handler.clear_cache_and_history()
        
        # Удаляем все Excel файлы
        excel_dir = os.path.join("data", "excel")
        excel_files_count = 0
        if os.path.exists(excel_dir):
            for file_name in os.listdir(excel_dir):
                if file_name.endswith(".xlsx"):
                    os.remove(os.path.join(excel_dir, file_name))
                    excel_files_count += 1
        
        # Удаляем все файлы сообщений
        messages_dir = file_handler.messages_path
        messages_files_count = 0
        if os.path.exists(messages_dir):
            for file_name in os.listdir(messages_dir):
                if file_name.endswith(".docx"):
                    os.remove(os.path.join(messages_dir, file_name))
                    messages_files_count += 1
        
        # Отправляем сообщение об успешном сбросе
        await update.message.reply_text(
            f"✅ Бот успешно сброшен!\n\n"
            f"🗑️ Удалено:\n"
            f"- {excel_files_count} Excel файлов\n"
            f"- {messages_files_count} файлов сообщений\n"
            f"- Кэш анализа и статистика\n\n"
            f"Теперь анализ будет начат с чистого листа."
        )
        logging.info(f"Бот сброшен пользователем {update.effective_user.username}. Удалено {excel_files_count} Excel файлов и {messages_files_count} файлов сообщений.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при сбросе бота: {str(e)}")
        logging.error(f"Ошибка при сбросе бота: {str(e)}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает входящие фотографии"""
    try:
        # Проверяем разрешен ли чат
        if not is_allowed_chat(update.effective_chat.id):
            logger.warning(f"Попытка доступа из неразрешенного чата {update.effective_chat.id}")
            await update.message.reply_text("Извините, у вас нет доступа к этому боту.")
            return

        # Получаем информацию о фото
        photo = update.message.photo[-1]  # Берем самую большую версию фото
        sender_name = update.effective_user.full_name
        
        # Создаем директорию для фотографий, если её нет
        os.makedirs("data/photos", exist_ok=True)
        
        # Формируем имя файла
        file_name = f"{sender_name}_{datetime.now().strftime('%d%m%Y_%H%M%S')}.jpg"
        file_path = f"data/photos/{file_name}"
        
        # Скачиваем фото
        photo_file = await context.bot.get_file(photo.file_id)
        await photo_file.download_to_drive(file_path)
        
        # Отправляем сообщение о начале обработки
        process_message = await update.message.reply_text("🔄 Анализирую фотографию с помощью YandexGPT...")
        
        try:
            # Анализируем фото с помощью YandexGPT
            result = await gpt.generate_response(
                prompt="""Проанализируй таблицу на фотографии и извлеки следующую информацию:
1. Название подразделения и дату (из заголовка таблицы)
2. Список операций с их показателями
3. Площади обработки за день и общие площади

Верни результат в формате JSON:
{
    "subdivision": "название подразделения",
    "date": "дата",
    "operations": [
        {
            "operation": "название операции",
            "area_per_day": "площадь за день",
            "total_area": "общая площадь"
        }
    ]
}""",
                model="vision",
                image_path=file_path
            )
            
            # Получаем текст ответа
            response_text = gpt.get_response_text(result)
            
            # Парсим JSON ответ
            try:
                analysis_data = json.loads(response_text)
            except json.JSONDecodeError:
                # Если не удалось распарсить JSON, используем базовый анализ
                analysis_data = {
                    "work_type": "Не удалось определить",
                    "operation": "Не удалось определить",
                    "notes": response_text
                }
            
            # Обновляем Excel с данными из фото
            excel_path = file_handler.update_excel()
            
            # Формируем ответ пользователю
            response = "✅ Фотография проанализирована и данные добавлены в отчет!\n\n"
            
            if "work_type" in analysis_data and analysis_data["work_type"]:
                response += f"🚜 Тип работы: {analysis_data['work_type']}\n"
            if "operation" in analysis_data and analysis_data["operation"]:
                response += f"📝 Операция: {analysis_data['operation']}\n"
            if "culture_to" in analysis_data and analysis_data["culture_to"]:
                response += f"🌾 Культура: {analysis_data['culture_to']}\n"
            if "pu_number" in analysis_data and analysis_data["pu_number"]:
                response += f"🔢 ПУ: {analysis_data['pu_number']}/{analysis_data.get('pu_area', '')}\n"
            if "department" in analysis_data and analysis_data["department"]:
                response += f"🏢 Отдел: {analysis_data['department']} {analysis_data.get('department_number', '')}/{analysis_data.get('department_area', '')}\n"
            if "quality" in analysis_data and analysis_data["quality"]:
                response += f"⭐ Качество работы: {analysis_data['quality']}\n"
            if "field_condition" in analysis_data and analysis_data["field_condition"]:
                response += f"🌱 Состояние поля: {analysis_data['field_condition']}\n"
            if "issues" in analysis_data and analysis_data["issues"]:
                response += f"⚠️ Проблемы: {analysis_data['issues']}\n"
            
            # Отправляем ответ
            await process_message.edit_text(response)
            
            logging.info(f"Фотография проанализирована: {file_path}")
            
        except Exception as e:
            logging.error(f"Ошибка при анализе фотографии: {e}")
            await process_message.edit_text(f"❌ Произошла ошибка при анализе фотографии: {str(e)}")
        
    except Exception as e:
        logging.error(f"Ошибка при обработке фотографии: {e}")
        await update.message.reply_text("Произошла ошибка при обработке фотографии.")

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает ID текущего чата"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    await update.message.reply_text(
        f"ID этого чата: {chat_id}\n"
        f"Ваш ID пользователя: {user_id}"
    )

async def process_message(message: Message):
    """
    Обрабатывает входящие сообщения
    """
    try:
        chat_id = message.chat.id
        if chat_id not in ALLOWED_CHAT_IDS:
            await message.reply("У вас нет доступа к этому боту.")
            return

        # Получаем информацию о пользователе
        user_info = f"{message.from_user.full_name} ({message.from_user.id})"
        logging.info(f"Получено сообщение от {user_info}")

        photo_path = None
        message_text = message.text

        # Обработка фотографии если есть
        if message.photo:
            # Получаем самую большую версию фото
            photo = message.photo[-1]
            
            # Создаем директорию для фото если её нет
            photos_dir = os.path.join("data", "photos")
            os.makedirs(photos_dir, exist_ok=True)
            
            # Формируем имя файла из даты и ID фото
            photo_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{photo.file_id}.jpg"
            photo_path = os.path.join(photos_dir, photo_filename)
            
            # Скачиваем фото
            await photo.download(destination_file=photo_path)
            logging.info(f"Фото сохранено: {photo_path}")
            
            # Сохраняем информацию о фото
            caption = message.caption or ""
            file_handler.save_photo_info(
                date=datetime.now(),
                sender=user_info,
                file_path=photo_path,
                caption=caption
            )
            
            message_text = caption

        # Сохраняем сообщение в файл
        save_message_to_file(message_text, user_info)
        
        # Анализируем сообщение
        analysis_result = await file_handler.analyze_message(message_text, photo_path)
        
        if "error" in analysis_result:
            error_message = f"Ошибка при анализе: {analysis_result['error']}"
            logging.error(error_message)
            await message.reply(error_message)
            return
            
        # Формируем ответное сообщение
        response = "✅ Сообщение обработано\n\n"
        response += "📝 Результат анализа:\n"
        
        if analysis_result.get("work_type"):
            response += f"Тип работы: {analysis_result['work_type']}\n"
        if analysis_result.get("operation"):
            response += f"Операция: {analysis_result['operation']}\n"
        if analysis_result.get("culture_from"):
            response += f"Исходная культура: {analysis_result['culture_from']}\n"
        if analysis_result.get("culture_to"):
            response += f"Целевая культура: {analysis_result['culture_to']}\n"
        if analysis_result.get("pu_number"):
            response += f"Номер поля: {analysis_result['pu_number']}\n"
        if analysis_result.get("pu_area"):
            response += f"Площадь: {analysis_result['pu_area']} га\n"
        if analysis_result.get("department"):
            response += f"Отделение: {analysis_result['department']}\n"
        if analysis_result.get("quality"):
            response += f"Качество работы: {analysis_result['quality']}\n"
        if analysis_result.get("field_condition"):
            response += f"Состояние поля: {analysis_result['field_condition']}\n"
        if analysis_result.get("issues"):
            response += f"Проблемы: {analysis_result['issues']}\n"
            
        await message.reply(response)
        
    except Exception as e:
        error_message = f"Ошибка при обработке сообщения: {str(e)}"
        logging.error(error_message)
        await message.reply(error_message)

def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("export", export_data))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("schedule", schedule_reports))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("chatid", get_chat_id))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Запускаем бота
    logger.info("Бот запущен")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 