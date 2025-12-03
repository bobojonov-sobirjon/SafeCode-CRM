import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import decode as jwt_decode
from django.conf import settings

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Подключение к WebSocket с аутентификацией через JWT токен
        """
        print(f"[DEBUG] ========== WebSocket CONNECT attempt ==========")
        print(f"[DEBUG] Scope: {self.scope}")
        print(f"[DEBUG] Channel name: {self.channel_name}")
        
        # Получаем токен из query string
        query_string = self.scope.get('query_string', b'').decode()
        print(f"[DEBUG] Query string: {query_string}")
        token = None
        
        # Парсим query string для получения токена
        if 'token=' in query_string:
            token = query_string.split('token=')[1].split('&')[0]
            print(f"[DEBUG] Token extracted: {token[:50]}..." if len(token) > 50 else f"[DEBUG] Token extracted: {token}")
        else:
            print(f"[DEBUG] ERROR: No token found in query string!")
        
        if not token:
            print(f"[DEBUG] ERROR: Token is None or empty, closing connection")
            await self.close()
            return
        
        # Проверяем токен и получаем пользователя
        try:
            print(f"[DEBUG] Attempting to get user from token...")
            user = await self.get_user_from_token(token)
            if user:
                print(f"[DEBUG] User authenticated: id={user.id}, email={user.email}")
                self.user = user
                self.room_group_name = f"user_{user.id}"
                print(f"[DEBUG] Room group name: {self.room_group_name}")
                
                # Присоединяемся к группе пользователя
                print(f"[DEBUG] Adding to channel layer group...")
                print(f"[DEBUG] Channel layer: {self.channel_layer}")
                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name
                )
                print(f"[DEBUG] Successfully added to group: {self.room_group_name}")
                
                print(f"[DEBUG] Accepting WebSocket connection...")
                await self.accept()
                print(f"[DEBUG] ========== WebSocket CONNECTED successfully ==========")
            else:
                print(f"[DEBUG] ERROR: User is None, closing connection")
                await self.close()
        except Exception as e:
            print(f"[DEBUG] ERROR in connect: {str(e)}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            await self.close()
    
    async def disconnect(self, close_code):
        """
        Отключение от WebSocket
        """
        print(f"[DEBUG] ========== WebSocket DISCONNECT ==========")
        print(f"[DEBUG] Close code: {close_code}")
        print(f"[DEBUG] Channel name: {self.channel_name}")
        if hasattr(self, 'room_group_name'):
            print(f"[DEBUG] Removing from group: {self.room_group_name}")
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            print(f"[DEBUG] Removed from group: {self.room_group_name}")
        else:
            print(f"[DEBUG] WARNING: room_group_name not found")
        if hasattr(self, 'user'):
            print(f"[DEBUG] User: id={self.user.id}, email={self.user.email}")
        print(f"[DEBUG] ========== WebSocket DISCONNECTED ==========")
    
    async def receive(self, text_data):
        """
        Получение сообщений от клиента
        """
        print(f"[DEBUG] ========== WebSocket RECEIVE ==========")
        print(f"[DEBUG] Received text_data: {text_data}")
        print(f"[DEBUG] Channel name: {self.channel_name}")
        if hasattr(self, 'user'):
            print(f"[DEBUG] User: id={self.user.id}, email={self.user.email}")
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            print(f"[DEBUG] Message type: {message_type}")
            print(f"[DEBUG] Full message: {text_data_json}")
            
            if message_type == 'ping':
                # Отправляем pong для поддержания соединения
                print(f"[DEBUG] Sending pong response...")
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }, ensure_ascii=False))
                print(f"[DEBUG] Pong sent successfully")
            else:
                print(f"[DEBUG] Unknown message type: {message_type}")
        except json.JSONDecodeError as e:
            print(f"[DEBUG] ERROR: JSON decode error: {str(e)}")
        except Exception as e:
            print(f"[DEBUG] ERROR in receive: {str(e)}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        print(f"[DEBUG] ========== WebSocket RECEIVE end ==========")
    
    async def notification_message(self, event):
        """
        Отправка уведомления клиенту
        """
        print(f"[DEBUG] ========== NOTIFICATION_MESSAGE received ==========")
        print(f"[DEBUG] Channel name: {self.channel_name}")
        if hasattr(self, 'user'):
            print(f"[DEBUG] User: id={self.user.id}, email={self.user.email}")
        print(f"[DEBUG] Full event: {event}")
        print(f"[DEBUG] Event type: {event.get('type')}")
        
        try:
            notification = event.get('notification')
            if not notification:
                print(f"[DEBUG] ERROR: No 'notification' key in event!")
                return
            
            print(f"[DEBUG] Notification data: {notification}")
            print(f"[DEBUG] Notification ID: {notification.get('id')}")
            print(f"[DEBUG] Notification message: {notification.get('message')}")
            
            # Отправляем уведомление через WebSocket
            message = json.dumps({
                'type': 'notification',
                'data': notification
            }, ensure_ascii=False)
            print(f"[DEBUG] Prepared message to send: {message}")
            print(f"[DEBUG] Attempting to send message to WebSocket client...")
            
            await self.send(text_data=message)
            print(f"[DEBUG] ========== NOTIFICATION_MESSAGE sent successfully ==========")
        except KeyError as e:
            print(f"[DEBUG] ERROR: KeyError in notification_message: {str(e)}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        except Exception as e:
            print(f"[DEBUG] ERROR in notification_message: {str(e)}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
    
    @database_sync_to_async
    def get_user_from_token(self, token):
        """
        Получение пользователя из JWT токена
        """
        print(f"[DEBUG] get_user_from_token called")
        try:
            # Декодируем токен
            print(f"[DEBUG] Validating token with UntypedToken...")
            UntypedToken(token)
            print(f"[DEBUG] Token validated, decoding...")
            decoded_data = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            print(f"[DEBUG] Token decoded successfully")
            user_id = decoded_data.get('user_id')
            print(f"[DEBUG] User ID from token: {user_id}")
            
            if user_id:
                try:
                    print(f"[DEBUG] Fetching user from database...")
                    user = User.objects.get(id=user_id, is_active=True)
                    print(f"[DEBUG] User found: id={user.id}, email={user.email}, is_active={user.is_active}")
                    return user
                except User.DoesNotExist:
                    print(f"[DEBUG] ERROR: User with id={user_id} does not exist")
                    return None
            else:
                print(f"[DEBUG] ERROR: No user_id in decoded token")
            return None
        except InvalidToken as e:
            print(f"[DEBUG] ERROR: InvalidToken - {str(e)}")
            return None
        except TokenError as e:
            print(f"[DEBUG] ERROR: TokenError - {str(e)}")
            return None
        except Exception as e:
            print(f"[DEBUG] ERROR: Exception in get_user_from_token - {str(e)}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return None

