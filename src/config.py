import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Конфигурация бота
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Не установлена переменная окружения TELEGRAM_BOT_TOKEN")

YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')
if not YANDEX_API_KEY:
    raise ValueError("Не установлена переменная окружения YANDEX_API_KEY")

# Yandex Cloud настройки
YANDEX_FOLDER_ID = os.getenv('YANDEX_FOLDER_ID')
if not YANDEX_FOLDER_ID:
    raise ValueError("Не установлена переменная окружения YANDEX_FOLDER_ID")

# Конфигурация базы данных
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///lam.db')

# Настройки приложения
def parse_chat_ids(chat_ids_str: str) -> list:
    """Парсит строку с ID чатов, учитывая отрицательные значения"""
    if not chat_ids_str:
        return []
    try:
        # Разделяем строку по запятой и преобразуем в целые числа
        return [int(chat_id.strip()) for chat_id in chat_ids_str.split(',') if chat_id.strip()]
    except ValueError as e:
        print(f"Ошибка при парсинге ID чатов: {e}")
        return []

ALLOWED_CHAT_IDS = parse_chat_ids(os.getenv('ALLOWED_CHAT_IDS', ''))
ADMIN_USER_IDS = parse_chat_ids(os.getenv('ADMIN_USER_IDS', ''))

# Настройки отчетов
REPORT_GENERATION_TIME = os.getenv('REPORT_GENERATION_TIME', '06:00')  # Время генерации отчета
REPORT_SEND_TO = os.getenv('REPORT_SEND_TO', '').split(',')  # Список получателей отчета

# Настройки API
API_TIMEOUT = int(os.getenv('API_TIMEOUT', '30'))  # Таймаут для API запросов в секундах 