import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import decode as jwt_decode
from django.conf import settings

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Подключение к WebSocket с аутентификацией через JWT токен
        """
        # Получаем токен из query string
        query_string = self.scope.get('query_string', b'').decode()
        token = None
        
        # Парсим query string для получения токена
        if 'token=' in query_string:
            token = query_string.split('token=')[1].split('&')[0]
        
        if not token:
            await self.close()
            return
        
        # Проверяем токен и получаем пользователя
        try:
            user = await self.get_user_from_token(token)
            if user:
                self.user = user
                self.room_group_name = f"user_{user.id}"
                
                # Присоединяемся к группе пользователя
                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name
                )
                
                await self.accept()
            else:
                await self.close()
        except Exception as e:
            await self.close()
    
    async def disconnect(self, close_code):
        """
        Отключение от WebSocket
        """
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """
        Получение сообщений от клиента
        """
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'ping':
                # Отправляем pong для поддержания соединения
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }, ensure_ascii=False))
        except json.JSONDecodeError:
            pass
    
    async def notification_message(self, event):
        """
        Отправка уведомления клиенту
        """
        notification = event['notification']
        
        # Отправляем уведомление через WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': notification
        }, ensure_ascii=False))
    
    @database_sync_to_async
    def get_user_from_token(self, token):
        """
        Получение пользователя из JWT токена
        """
        try:
            # Декодируем токен
            UntypedToken(token)
            decoded_data = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = decoded_data.get('user_id')
            
            if user_id:
                try:
                    user = User.objects.get(id=user_id, is_active=True)
                    return user
                except User.DoesNotExist:
                    return None
            return None
        except (InvalidToken, TokenError, Exception) as e:
            return None

