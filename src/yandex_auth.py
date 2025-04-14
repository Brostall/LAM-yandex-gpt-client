import os
import json
import requests
import jwt  # Добавляем импорт JWT
from datetime import datetime, timedelta
from typing import Optional, Dict

def get_service_account_token(sa_key_file: str) -> Optional[Dict]:
    """
    Получает IAM токен используя ключ сервисного аккаунта
    """
    try:
        with open(sa_key_file, 'r') as f:
            sa_key = json.load(f)
        
        # Проверяем наличие необходимых полей
        required_fields = ['id', 'service_account_id', 'private_key']
        for field in required_fields:
            if field not in sa_key:
                print(f"Ошибка: В файле ключа нет поля {field}")
                return None
            
        # Создаем JWT
        now = datetime.utcnow()
        jwt_payload = {
            'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            'iss': sa_key['service_account_id'],
            'iat': now,
            'exp': now + timedelta(hours=1)
        }

        # Добавляем заголовок с kid
        jwt_headers = {
            'kid': sa_key['id']
        }

        # Подписываем JWT приватным ключом
        encoded_jwt = jwt.encode(
            jwt_payload,
            sa_key['private_key'],
            algorithm='PS256',
            headers=jwt_headers  # Добавляем заголовки
        )
            
        url = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
        payload = {
            "jwt": encoded_jwt
        }
        
        print(f"Отправляем запрос на получение токена...")
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            print(f"Ошибка {response.status_code}: {response.text}")
            return None
            
        return response.json()
    except json.JSONDecodeError as e:
        print(f"Ошибка при чтении JSON файла: {e}")
        return None
    except Exception as e:
        print(f"Неожиданная ошибка при получении токена: {e}")
        return None

if __name__ == "__main__":
    # Путь к файлу с ключом сервисного аккаунта
    sa_key_file = os.getenv('YANDEX_SA_KEY_FILE', 'service-account-key.json')
    
    if not os.path.exists(sa_key_file):
        print(f"Ошибка: Файл с ключом сервисного аккаунта не найден: {sa_key_file}")
        exit(1)
    
    result = get_service_account_token(sa_key_file)
    if result:
        print("IAM токен успешно получен:")
        print(result['iamToken'])
    else:
        print("Не удалось получить IAM токен") 