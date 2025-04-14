import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Конфигурация бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')

# Конфигурация базы данных
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///lam.db')

# Настройки приложения
ALLOWED_CHAT_IDS = list(map(int, os.getenv('ALLOWED_CHAT_IDS', '').split(','))) if os.getenv('ALLOWED_CHAT_IDS') else []
ADMIN_USER_IDS = list(map(int, os.getenv('ADMIN_USER_IDS', '').split(','))) if os.getenv('ADMIN_USER_IDS') else []

# Настройки отчетов
REPORT_GENERATION_TIME = os.getenv('REPORT_GENERATION_TIME', '06:00')  # Время генерации отчета
REPORT_SEND_TO = os.getenv('REPORT_SEND_TO', '').split(',')  # Список получателей отчета 