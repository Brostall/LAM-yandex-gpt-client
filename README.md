# YandexGPT API Client

Простой и удобный клиент для работы с YandexGPT API.

## Возможности

- Поддержка моделей YandexGPT (lite и full версии)
- Автоматическое обновление IAM токенов
- Поддержка system prompt
- Удобный интерфейс для генерации текста

## Установка

1. Клонируйте репозиторий:
```bash
git clone [URL репозитория]
cd [имя папки]
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте переменные окружения:
```bash
# Windows PowerShell
$env:YANDEX_FOLDER_ID="ваш_folder_id"
$env:YANDEX_SA_KEY_FILE="путь/к/service-account-key.json"
```

## Использование

```python
from src.yandex_gpt import YandexGPT

# Создание экземпляра
gpt = YandexGPT('service-account-key.json', 'your_folder_id')

# Генерация ответа
result = gpt.generate_response(
    prompt="Ваш запрос",
    model="lite",  # или "full"
    temperature=0.7,
    system_prompt="Дополнительные инструкции для модели"
)

# Получение текста ответа
if result:
    print(gpt.get_response_text(result))
```

## Безопасность

- Не храните чувствительные данные (ключи, токены) в репозитории
- Используйте переменные окружения для конфиденциальной информации
- Храните `service-account-key.json` в безопасном месте

## Требования

- Python 3.7+
- requests
- PyJWT[crypto] 