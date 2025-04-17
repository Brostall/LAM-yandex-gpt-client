import json
import logging
import os
import requests
import aiohttp
import base64
from typing import Optional, Dict, Any, List
from .yandex_auth import get_service_account_token

class YandexGPT:
    def __init__(self, service_account_key_file: str, folder_id: str):
        """
        Инициализация клиента YandexGPT

        Args:
            service_account_key_file (str): путь к файлу с ключом сервисного аккаунта
            folder_id (str): идентификатор каталога в Яндекс Облаке
        """
        self.service_account_key_file = service_account_key_file
        self.folder_id = folder_id
        self.token = get_service_account_token(service_account_key_file)
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        self.vision_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        # Доступные модели
        self.models = {
            "lite": "yandexgpt-lite",    # Облегченная версия
            "full": "yandexgpt",         # Полная версия
            "text": "yandexgpt",         # Используем полную версию для текста
            "vision": "yandexgpt"        # Используем полную версию для изображений
        }

    async def generate_response(self, prompt: str, model: str = "full", image_path: str = None) -> dict:
        """
        Генерирует ответ от YandexGPT API
        
        Args:
            prompt (str): Текст запроса
            model (str): Название модели (по умолчанию "full" - полная версия)
            image_path (str): Путь к изображению (если есть)
            
        Returns:
            dict: Ответ от API
        """
        try:
            if model == "vision" and not image_path:
                raise ValueError("Image path is required for vision model")

            url = self.vision_url if model == "vision" else self.base_url
            
            # Базовый промпт для анализа текстовых сообщений
            base_prompt = """ПРАВИЛА АНАЛИЗА:

1. Структура данных:
   - Дата: формат день/месяц/год (30/11/24), если год не указан - текущий год, если дата не указана - дата отправки сообщения
   - Подразделение: определяется по справочнику
   - Операция: из списка разрешенных операций
   - Культура: из списка разрешенных культур
   - Площадь за день (га)
   - Площадь с начала операции (га)
   - Вал (ц): только при уборке урожая, кг делить на 100

2. Правила преобразования входных данных:

   ✓ Пример 1: "Пахота зяби под мн тр"
   Должно быть преобразовано в:
   - Операция: "Пахота зяби"
   - Культура: "Многолетние травы"
   
   ✓ Пример 2: "Диск сах св"
   Должно быть преобразовано в:
   - Операция: "Дискование"
   - Культура: "Сахарная свекла"
   
   ✓ Пример 3: "Предп культ под оз пш"
   Должно быть преобразовано в:
   - Операция: "Предпосевная культивация"
   - Культура: "Пшеница озимая товарная"

   ✓ Алгоритм преобразования:
   1. Определить тип операции:
      - Если есть "зяби" → "Пахота зяби"
      - Если начинается с "Диск" → "Дискование"
      - Если есть "культ" → "Культивация" или "Предпосевная культивация"
   
   2. Определить культуру:
      - Если есть "под" → взять культуру после "под"
      - Если есть сокращение культуры → преобразовать по справочнику
      - "мн тр" → "Многолетние травы"
      - "сах св" → "Сахарная свекла"
      - "оз пш" → "Пшеница озимая товарная"
   
   3. Обработать площади:
      - "По Пу X/Y" → ПУ = X, площадь = Y
      - "Отд N M/Z" → Отдел = N, участок = M, площадь = Z

3. Правила определения подразделения:
   ✓ Приоритет данных:
   1) По Подразделению (если указано)
   2) По ПУ (Производственному участку)
   3) По Отделению (если нет данных по ПУ)
   
   ✓ Соответствия названий:
   - "Рассвет" = "АОР"
   - "Восход" = "АОР"
   - "Мир" = "АОР"
   - "Юг" = "АОР" (часть АОР)

4. Правила обработки площадей:
   ✓ Если указано "x/y":
   - x = площадь за день
   - y = площадь с начала операции
   
   ✓ Если указано только число:
   - Это площадь за день
   - "С начала операции" можно не заполнять
   
   ✓ Если указан процент:
   - Не вычислять площадь из процента
   - Использовать только явно указанные числа
   
   ✓ Если "всего" не указано явно:
   - Можно взять только "за день"

5. Правила определения культур:
   ✓ Автоматические соответствия:
   - "Соя" = "Соя товарная"
   - "Пшеница озимая" = "Пшеница озимая товарная"
   - "Подсолнечник" = "Подсолнечник товарный"
   - "Кукуруза на зерно" = "Кукуруза товарная"
   - "к. сил." = "Кукуруза кормовая"
   - "ОП" = "Озимая пшеница"
   - "Пшеница" = "Пшеница озимая товарная" (если не указано иное)
   
   ✓ Правила распознавания сокращений:
   - "сах св" = "Сахарная свекла"
   - "мн тр" = "Многолетние травы"
   - "оз пш" = "Озимая пшеница"
   - "св" = "Свекла" (в контексте "сах св" = "Сахарная свекла")
   
   ✓ Правила обработки предлогов:
   - Предлог "под" не является частью названия культуры или операции
   - При наличии конструкции "под [культура]" - это указание целевой культуры
   - Игнорировать предлог "под" при формировании названия операции
   
   ✓ Специальные случаи:
   - "зябь" или "зяби" указывает на тип операции "Пахота зяби"
   - Если указано "под [культура]", это целевая культура для операции
   - При указании "прошлых лет" или "пр" после культуры, добавлять это к названию

6. Правила обработки операций:
   ✓ Соответствия:
   - "Сев" = "Посев"
   - "Химпрополка" = "Гербицидная обработка"
   - "Внесение противозлакового гербицида" = "Гербицидная обработка"
   - "Химобработка" = "Гербицидная обработка"
   - "Пахота зяби" = "Пахота"
   - "Первая культивация" = "Культивация"
   
   ✓ Сокращения операций:
   - "Диск" = "Дискование"
   - "Культ" = "Культивация"
   - "Предп культ" = "Предпосевная культивация"
   - "Хим" = "Химическая обработка"
   
   ✓ Правила формирования полного названия операции:
   - Операция + культура (если есть)
   - Игнорировать предлоги при формировании названия
   - При наличии "зяби" - это часть названия операции
   - Для предпосевной культивации указывать целевую культуру после "под"

   ✓ Правила обработки сокращений операций:
   - При наличии сокращения операции и культуры объединять их в одну операцию
   - Учитывать порядок слов при объединении (операция + культура)
   - Сохранять технологические номера операций (1-я, 2-я и т.д.)
   - Не включать предлог "под" в название операции

7. Формат вывода:
{
    "date": "дд.мм.гггг",
    "records": [
        {
            "subdivision": "название подразделения",
            "operation": "название операции",
            "culture": "название культуры",
            "area_per_day": число,
            "area_from_start": число или null,
            "harvest_centners": число или null
        },
        // ... дополнительные записи
    ]
}

ВАЖНО:
- Используйте только операции и культуры из справочника
- Не вычисляйте площади из процентов
- При отсутствии даты используйте текущую
- Вал в центнерах указывайте только при уборке урожая
- Игнорируйте операции не из списка разрешенных
- При неясности данных оставляйте поле null
- Не учитывайте информацию из скриншотов
- Не обрабатывайте информацию о подразделениях ниже уровня ПУ
- При обработке валов: кг делить на 100 для перевода в центнеры
- Неидентифицированные позиции отмечать желтым цветом
- Все данные должны быть в одном Excel файле
- Не использовать CSV формат

ПРАВИЛА ОБРАБОТКИ ДЛИННЫХ ОТЧЕТОВ:
- Если отчет слишком длинный, разбейте его на логические части
- Каждую часть обрабатывайте отдельно, сохраняя контекст
- При обработке следующей части учитывайте данные из предыдущей
- Если в разных частях отчета есть противоречия, используйте последнее упоминание
- При обработке длинных списков операций сохраняйте последовательность
- Если встречаются повторяющиеся операции, проверьте их на дубликаты

Проанализируйте предоставленный текст и выделите операции согласно этим правилам."""

            # Используем предоставленный промпт или базовый
            final_prompt = prompt.strip() if prompt and prompt.strip() else base_prompt

            if model == "vision":
                with open(image_path, "rb") as image_file:
                    image_content = base64.b64encode(image_file.read()).decode('utf-8')
                
                payload = {
                    "modelUri": f"gpt://{self.folder_id}/{self.models[model]}",
                    "completionOptions": {
                        "stream": False,
                        "temperature": 0.6,
                        "maxTokens": 8000
                    },
                    "messages": [{
                        "role": "user",
                        "text": final_prompt,
                        "attachments": [{
                            "content": image_content,
                            "mime_type": "image/jpeg"
                        }]
                    }]
                }
                
                logging.info(f"Отправляем запрос на анализ изображения с промптом длиной {len(final_prompt)} символов")
            else:
                payload = {
                    "modelUri": f"gpt://{self.folder_id}/{self.models[model]}",
                    "completionOptions": {
                        "stream": False,
                        "temperature": 0.6,
                        "maxTokens": 8000
                    },
                    "messages": [{
                        "role": "user",
                        "text": final_prompt
                    }]
                }

            logging.info(f"Sending request to {url}")
            logging.debug(f"Payload structure: {json.dumps({k: '...' if k == 'messages' else v for k, v in payload.items()})}")

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logging.info("Successfully received response from API")
                        return result
                    else:
                        error_text = await response.text()
                        logging.error(f"Error from API: {error_text}")
                        return {"error": f"API returned status code {response.status}: {error_text}"}
                        
        except Exception as e:
            logging.error(f"Error generating response: {str(e)}")
            return {"error": str(e)}

    def get_response_text(self, response: Dict[str, Any]) -> str:
        """
        Извлекает текст ответа из результата API
        """
        if "error" in response:
            logging.error(f"Ошибка в ответе API: {response['error']}")
            return f"Произошла ошибка: {response['error']}"
        
        try:
            logging.info(f"Обрабатываем ответ от YandexGPT: {json.dumps(response, ensure_ascii=False)[:200]}...")
            
            result = response.get("result", {})
            if not result:
                logging.error("В ответе отсутствует ключ 'result'")
                return "Не удалось получить ответ: отсутствует ключ 'result'"
                
            alternatives = result.get("alternatives", [])
            if not alternatives:
                logging.error("В ответе отсутствуют альтернативы")
                return "Не удалось получить ответ: отсутствуют альтернативы"
                
            message = alternatives[0].get("message", {})
            if not message:
                logging.error("В ответе отсутствует сообщение")
                return "Не удалось получить ответ: отсутствует сообщение"
                
            text = message.get("text", "")
            if not text:
                logging.error("В ответе отсутствует текст")
                return "Не удалось получить ответ: отсутствует текст"
                
            logging.info(f"Успешно получен ответ от YandexGPT длиной {len(text)} символов")
            return text
        except Exception as e:
            logging.error(f"Ошибка при обработке ответа: {str(e)}")
            return f"Ошибка при обработке ответа: {str(e)}"

if __name__ == "__main__":
    # Пример использования
    import os
    
    # Получаем необходимые параметры
    sa_key_file = os.getenv('YANDEX_SA_KEY_FILE', 'service-account-key.json')
    folder_id = os.getenv('YANDEX_FOLDER_ID')
    
    if not os.path.exists(sa_key_file):
        print(f"Ошибка: Файл с ключом сервисного аккаунта не найден: {sa_key_file}")
        exit(1)
    
    if not folder_id:
        print("Ошибка: Установите переменную окружения YANDEX_FOLDER_ID")
        exit(1)
    
    # Создаем экземпляр YandexGPT
    gpt = YandexGPT(sa_key_file, folder_id)
    
    # Примеры использования разных моделей
    prompts = [
        ("Напиши стихотвореие маяковского", "lite"),
        ("Объясни, что такое квантовая механика простыми словами", "full"),
        ("""Напиши функцию на Python для поиска простых чисел в диапазоне.
        Добавь комментарии и пример использования.""", "full")
    ]

    for prompt, model in prompts:
        print(f"\nЗапрос к модели {model}:")
        print("-" * 50)
        print(f"Промпт: {prompt}")
        try:
            result = gpt.generate_response(
                prompt=prompt,
                model=model,
                image_path="path_to_image.jpg" if model == "vision" else None
            )
            
            if result:
                print("\nОтвет:")
                print(gpt.get_response_text(result))
            else:
                print("Не удалось получить ответ от API")
        except Exception as e:
            print(f"Ошибка при выполнении запроса: {e}") 