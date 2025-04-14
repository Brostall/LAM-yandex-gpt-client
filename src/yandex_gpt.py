import json
import requests
from typing import Optional, Dict, Any, List
from yandex_auth import get_service_account_token

class YandexGPT:
    # Доступные модели
    MODELS = {
        "lite": "yandexgpt-lite",  # Облегченная версия
        "full": "yandexgpt"        # Полная версия
    }

    def __init__(self, sa_key_file: str, folder_id: str):
        """
        Инициализация клиента YandexGPT

        Args:
            sa_key_file (str): путь к файлу с ключом сервисного аккаунта
            folder_id (str): идентификатор каталога в Яндекс Облаке
        """
        self.sa_key_file = sa_key_file
        self.folder_id = folder_id
        self.api_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        self._update_token()
    
    def _update_token(self) -> None:
        """Обновляет IAM токен"""
        result = get_service_account_token(self.sa_key_file)
        if not result:
            raise Exception("Не удалось получить IAM токен")
        self.headers = {
            "Authorization": f"Bearer {result['iamToken']}",
            "Content-Type": "application/json"
        }

    def generate_response(
        self,
        prompt: str,
        model: str = "lite",
        temperature: float = 0.6,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Генерирует ответ используя YandexGPT API

        Args:
            prompt (str): текст запроса
            model (str): модель для генерации (lite/full)
            temperature (float): температура генерации (0.0 - 1.0)
            max_tokens (int): максимальное количество токенов в ответе
            system_prompt (Optional[str]): системный промпт для настройки поведения модели

        Returns:
            Optional[Dict[str, Any]]: ответ от API или None в случае ошибки
        """
        # Проверяем корректность модели
        if model not in self.MODELS:
            raise ValueError(f"Неизвестная модель: {model}. Доступные модели: {', '.join(self.MODELS.keys())}")

        # Формируем сообщения
        messages = []
        if system_prompt:
            messages.append({"role": "system", "text": system_prompt})
        messages.append({"role": "user", "text": prompt})

        data = {
            "modelUri": f"gpt://{self.folder_id}/{self.MODELS[model]}",
            "completionOptions": {
                "stream": False,
                "temperature": temperature,
                "maxTokens": max_tokens
            },
            "messages": messages
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=data
            )
            
            # Если токен истёк, обновляем его и пробуем снова
            if response.status_code == 401:
                self._update_token()
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=data
                )
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к YandexGPT API: {e}")
            return None

    def get_response_text(self, response: Dict[str, Any]) -> str:
        """
        Извлекает текст ответа из response

        Args:
            response (Dict[str, Any]): ответ от API

        Returns:
            str: текст ответа или сообщение об ошибке
        """
        return response.get('result', {}).get('alternatives', [{}])[0].get('message', {}).get('text', 'Нет ответа')

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
        ("Напиши короткое стихотворение о весне", "lite"),
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
                temperature=0.7,
                system_prompt="Ты - полезный ассистент, который дает четкие и понятные ответы."
            )
            
            if result:
                print("\nОтвет:")
                print(gpt.get_response_text(result))
            else:
                print("Не удалось получить ответ от API")
        except Exception as e:
            print(f"Ошибка при выполнении запроса: {e}") 