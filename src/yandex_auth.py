import os
import json
import requests
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

def get_service_account_token(sa_key_file: str) -> Optional[str]:
    """
    Получает IAM токен с помощью ключа сервисного аккаунта
    
    Args:
        sa_key_file (str): путь к файлу с ключом сервисного аккаунта
        
    Returns:
        Optional[str]: IAM токен или None в случае ошибки
    """
    try:
        with open(sa_key_file, 'r') as f:
            sa_key = json.load(f)
            
        # Загружаем приватный ключ
        private_key = serialization.load_pem_private_key(
            sa_key['private_key'].encode(),
            password=None,
            backend=default_backend()
        )
            
        now = datetime.utcnow()
        payload = {
            'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            'iss': sa_key['service_account_id'],
            'iat': now,
            'exp': now + timedelta(hours=1)
        }

        # Подписываем JWT используя закрытый ключ
        encoded_jwt = jwt.encode(
            payload,
            private_key,
            algorithm='PS256',
            headers={'kid': sa_key['id']}
        )
            
        url = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
        response = requests.post(url, json={"jwt": encoded_jwt})
        response.raise_for_status()
        
        result = response.json()
        if 'iamToken' in result:
            logging.info("IAM токен успешно получен")
            return result['iamToken']
        else:
            logging.error(f"Ошибка в ответе IAM API: {result}")
            return None
            
    except FileNotFoundError:
        logging.error(f"Файл с ключом сервисного аккаунта не найден: {sa_key_file}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Ошибка при чтении файла с ключом сервисного аккаунта")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе к IAM API: {e}")
        return None
    except Exception as e:
        logging.error(f"Неожиданная ошибка при получении IAM токена: {e}")
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
        print(result)
    else:
        print("Не удалось получить IAM токен") 