import os
import logging
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from urllib.parse import urlparse, parse_qs

class GoogleDriveUploader:
    def __init__(self, credentials_path: str = None):
        """
        Инициализация загрузчика Google Drive
        
        Args:
            credentials_path (str): путь к файлу с учетными данными (если используется)
        """
        self.SCOPES = ['https://www.googleapis.com/auth/drive.file']
        self.service = None
        
        try:
            # Если предоставлены учетные данные сервисного аккаунта
            if credentials_path and os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path, scopes=self.SCOPES)
                self.service = build('drive', 'v3', credentials=credentials)
            else:
                # Используем стандартную аутентификацию через OAuth
                from google_auth_oauthlib.flow import InstalledAppFlow
                from google.auth.transport.requests import Request
                import pickle
                
                creds = None
                # Проверяем наличие сохраненных токенов
                if os.path.exists('token.pickle'):
                    with open('token.pickle', 'rb') as token:
                        creds = pickle.load(token)
                
                # Если нет валидных учетных данных, запрашиваем их
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            'credentials.json', self.SCOPES)
                        creds = flow.run_local_server(port=0)
                    
                    # Сохраняем учетные данные для следующего запуска
                    with open('token.pickle', 'wb') as token:
                        pickle.dump(creds, token)
                
                self.service = build('drive', 'v3', credentials=creds)
                
        except Exception as e:
            logging.error(f"Ошибка при инициализации Google Drive API: {str(e)}")
            raise
    
    def get_folder_id_from_url(self, folder_url: str) -> str:
        """
        Извлекает ID папки из URL Google Drive
        
        Args:
            folder_url (str): URL папки Google Drive
            
        Returns:
            str: ID папки
        """
        try:
            # Обрабатываем разные форматы URL
            if 'folders' in folder_url:
                # Формат: https://drive.google.com/drive/folders/FOLDER_ID
                return folder_url.split('folders/')[-1].split('?')[0]
            elif 'id=' in folder_url:
                # Формат: https://drive.google.com/drive/folders?id=FOLDER_ID
                parsed = urlparse(folder_url)
                params = parse_qs(parsed.query)
                return params.get('id', [None])[0]
            else:
                # Предполагаем, что передан непосредственно ID папки
                return folder_url.strip()
        except Exception as e:
            logging.error(f"Ошибка при извлечении ID папки из URL: {str(e)}")
            return None
    
    def upload_file(self, file_path: str, folder_url: str) -> str:
        """
        Загружает файл в указанную папку Google Drive
        
        Args:
            file_path (str): путь к файлу для загрузки
            folder_url (str): URL или ID папки Google Drive
            
        Returns:
            str: ID загруженного файла или None в случае ошибки
        """
        try:
            if not os.path.exists(file_path):
                logging.error(f"Файл не найден: {file_path}")
                return None
            
            # Получаем ID папки из URL
            folder_id = self.get_folder_id_from_url(folder_url)
            if not folder_id:
                logging.error("Не удалось получить ID папки")
                return None
            
            # Подготавливаем метаданные файла
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': [folder_id]
            }
            
            # Создаем объект MediaFileUpload
            media = MediaFileUpload(
                file_path,
                resumable=True
            )
            
            # Загружаем файл
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            logging.info(f"Файл успешно загружен. ID: {file.get('id')}, Ссылка: {file.get('webViewLink')}")
            return file.get('id')
            
        except Exception as e:
            logging.error(f"Ошибка при загрузке файла: {str(e)}")
            return None
    
    def check_folder_access(self, folder_url: str) -> bool:
        """
        Проверяет доступ к папке Google Drive
        
        Args:
            folder_url (str): URL или ID папки
            
        Returns:
            bool: True если есть доступ, False в противном случае
        """
        try:
            folder_id = self.get_folder_id_from_url(folder_url)
            if not folder_id:
                return False
            
            # Пытаемся получить метаданные папки
            self.service.files().get(fileId=folder_id).execute()
            return True
            
        except Exception as e:
            logging.error(f"Ошибка при проверке доступа к папке: {str(e)}")
            return False 