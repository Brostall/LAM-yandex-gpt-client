# LAM Yandex GPT Client

Бот для анализа сообщений агрономов с использованием YandexGPT.

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/LAM-yandex-gpt-client.git
cd LAM-yandex-gpt-client
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` с вашими настройками:
```
TELEGRAM_BOT_TOKEN=your_bot_token
YANDEX_API_KEY=your_yandex_api_key
```

## Запуск

```bash
python main.py
```

## Тестирование

Для тестирования бота отправьте ему сообщение в одном из следующих форматов:

1. Простой формат:
```
10.03 день
Пахота зяби под мн тр
По Пу 26/488
Отд 12 26/221
```

2. Расширенный формат:
```
Предп культ под оз пш
По Пу 215/1015
Отд 12 128/317
Отд 16 123/529
```

3. Формат с дополнительной информацией:
```
10.03 день
2-я подкормка
По Пу 1749/2559
Работало 5 агрегатов
Осадки 2 мм
```

## Структура проекта

- `src/` - исходный код
  - `file_handler.py` - обработка файлов и парсинг сообщений
  - `config.py` - конфигурация
- `data/` - папка для сохранения данных
  - `messages/` - сохраненные сообщения
  - `excel/` - сгенерированные Excel-отчеты

## API

Бот поддерживает следующие команды:

- `/start` - начало работы
- `/help` - справка
- `/report` - сгенерировать Excel-отчет
- `/stats` - показать статистику

## Формат данных

Бот извлекает из сообщений следующую информацию:

1. Дата
2. Подразделение
3. Тип работы
4. Культура
5. Площадь (га)
6. Общая площадь
7. Остаток
8. Дополнительная информация (агрегаты, осадки)

## Тестовые примеры

```python
from src.file_handler import FileHandler

# Создаем экземпляр обработчика
handler = FileHandler("test_team")

# Тестируем парсинг сообщения
message = """10.03 день
Пахота зяби под мн тр
По Пу 26/488
Отд 12 26/221"""

result = handler.parse_message(message)
print(result)
```

## Поддержка

При возникновении проблем создайте issue в репозитории или свяжитесь с разработчиками. 