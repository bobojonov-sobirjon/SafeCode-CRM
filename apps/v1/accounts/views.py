from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import secrets
from .models import CustomUser
from .serializers import (
    RegisterSerializer, LoginSerializer, ProfileSerializer, 
    ChangePasswordSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
    SimpleChangePasswordSerializer
)
from .error_handlers import get_error_message


class RegisterAPIView(APIView):
    """
    Регистрация нового пользователя
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Регистрация нового пользователя в системе",
        tags=['Accounts'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='Имя пользователя'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Фамилия пользователя'),
                'id_organization': openapi.Schema(type=openapi.TYPE_STRING, description='ID организации'),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Номер телефона'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description='Email адрес'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description='Пароль'),
                'password_confirm': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description='Подтверждение пароля'),
                'groups': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER),
                    description='Список ID групп (ролей) пользователя. Пример: [1, 2, 3]'
                ),
            },
            required=['first_name', 'last_name', 'id_organization', 'phone_number', 'email', 'password', 'password_confirm']
        ),
        responses={
            201: openapi.Response(
                'Успешная регистрация',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            400: openapi.Response('Ошибка валидации данных')
        }
    )
    def post(self, request):
        try:
            serializer = RegisterSerializer(data=request.data)
            
            if serializer.is_valid():
                user = serializer.save()
                
                # Создаем JWT токены
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'success': True,
                    'message': 'Регистрация прошла успешно!',
                    'data': {
                        'user': {
                            'id': user.id,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'email': user.email,
                            'phone_number': user.phone_number,
                            'id_organization': user.id_organization,
                            'groups': [{'id': g.id, 'name': g.name} for g in user.groups.all()],
                        },
                        'tokens': {
                            'refresh': str(refresh),
                            'access': str(refresh.access_token),
                        }
                    }
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'success': False,
                'message': get_error_message('validation_error'),
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginAPIView(APIView):
    """
    Вход в систему
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Вход пользователя в систему по email или номеру телефона",
        tags=['Accounts'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'identifier': openapi.Schema(type=openapi.TYPE_STRING, description='Email или номер телефона'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description='Пароль'),
            },
            required=['identifier', 'password']
        ),
        responses={
            200: openapi.Response(
                'Успешный вход',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            400: openapi.Response('Ошибка входа в систему')
        }
    )
    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            
            if serializer.is_valid():
                user = serializer.validated_data['user']
                
                # Создаем JWT токены
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'success': True,
                    'message': 'Вход выполнен успешно!',
                    'data': {
                        'user': {
                            'id': user.id,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'email': user.email,
                            'phone_number': user.phone_number,
                            'id_organization': user.id_organization,
                            'groups': [{'id': g.id, 'name': g.name} for g in user.groups.all()],
                        },
                        'tokens': {
                            'refresh': str(refresh),
                            'access': str(refresh.access_token),
                        }
                    }
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': get_error_message('invalid_credentials'),
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfileAPIView(APIView):
    """
    Получение и обновление профиля пользователя
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение профиля текущего пользователя",
        tags=['Profile'],
        responses={
            200: openapi.Response(
                'Успешное получение профиля',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            user = request.user
            serializer = ProfileSerializer(user)
            
            return Response({
                'success': True,
                'message': 'Профиль получен успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Обновление профиля текущего пользователя",
        tags=['Profile'],
        request_body=ProfileSerializer,
        responses={
            200: openapi.Response(
                'Успешное обновление профиля',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            400: openapi.Response('Ошибка валидации данных'            ),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def put(self, request):
        try:
            user = request.user
            serializer = ProfileSerializer(user, data=request.data)
            
            if serializer.is_valid():
                serializer.save()
                
                return Response({
                    'success': True,
                    'message': 'Профиль обновлен успешно',
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': get_error_message('validation_error'),
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Частичное обновление профиля текущего пользователя",
        tags=['Profile'],
        request_body=ProfileSerializer,
        responses={
            200: openapi.Response(
                'Успешное обновление профиля',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            400: openapi.Response('Ошибка валидации данных'            ),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def patch(self, request):
        try:
            user = request.user
            serializer = ProfileSerializer(user, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                
                return Response({
                    'success': True,
                    'message': 'Профиль обновлен успешно',
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': get_error_message('validation_error'),
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChangePasswordAPIView(APIView):
    """
    Смена пароля пользователя
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Смена пароля текущего пользователя",
        tags=['Profile'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'old_password': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description='Текущий пароль'),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description='Новый пароль'),
                'new_password_confirm': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description='Подтверждение нового пароля'),
            },
            required=['old_password', 'new_password', 'new_password_confirm']
        ),
        responses={
            200: openapi.Response('Успешная смена пароля'),
            400: openapi.Response('Ошибка валидации данных'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
            
            if serializer.is_valid():
                user = request.user
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                
                return Response({
                    'success': True,
                    'message': 'Пароль изменен успешно'
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': get_error_message('validation_error'),
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutAPIView(APIView):
    """
    Выход из системы
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Выход пользователя из системы",
        tags=['Accounts'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'refresh_token': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh токен'),
            },
            required=['refresh_token']
        ),
        responses={
            200: openapi.Response('Успешный выход'),
            400: openapi.Response('Ошибка при выходе'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'success': True,
                'message': 'Выход выполнен успешно'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)


class UserInfoAPIView(APIView):
    """
    Получение информации о текущем пользователе
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение информации о текущем пользователе",
        tags=['Profile'],
        responses={
            200: openapi.Response(
                'Успешное получение информации',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            user = request.user
            
            return Response({
                    'success': True,
                    'message': 'Информация о пользователе получена успешно',
                    'data': {
                        'id': user.id,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'email': user.email,
                        'phone_number': user.phone_number,
                        'id_organization': user.id_organization,
                        'date_of_birth': user.date_of_birth,
                        'address': user.address,
                        'city': user.city,
                        'street': user.street,
                        'house': user.house,
                        'apartment': user.apartment,
                        'postal_index': user.postal_index,
                        'email_newsletter': user.email_newsletter,
                        'special_offers_notifications': user.special_offers_notifications,
                        'avatar': user.avatar.url if user.avatar else None,
                        'is_active': user.is_active,
                        'date_joined': user.date_joined,
                    }
                }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ForgotPasswordAPIView(APIView):
    """
    Запрос на восстановление пароля
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Запрос на восстановление пароля. На email будет отправлен токен для сброса пароля.",
        tags=['Accounts'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description='Email адрес'),
            },
            required=['email']
        ),
        responses={
            200: openapi.Response('Email с токеном отправлен'),
            400: openapi.Response('Ошибка валидации данных'),
            404: openapi.Response('Пользователь не найден')
        }
    )
    def post(self, request):
        try:
            serializer = ForgotPasswordSerializer(data=request.data)
            
            if serializer.is_valid():
                email = serializer.validated_data['email']
                user = CustomUser.objects.get(email__iexact=email)
                
                # Генерируем токен
                token = secrets.token_urlsafe(32)
                
                # Сохраняем токен и время истечения (1 час)
                user.reset_token = token
                user.reset_token_expires = timezone.now() + timedelta(hours=1)
                user.save()
                
                # Отправляем email
                subject = 'Восстановление пароля - SafeCode CRM'
                message = f"""
Здравствуйте, {user.get_full_name()}!

Вы запросили сброс пароля для вашего аккаунта в SafeCode CRM.

Ваш токен для сброса пароля: {token}

Используйте этот токен для сброса пароля. Токен действителен в течение 1 часа.

Если вы не запрашивали сброс пароля, просто проигнорируйте это сообщение.

С уважением,
Команда SafeCode CRM
                """
                
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False,
                    )
                    email_sent = True
                    email_error = None
                except Exception as mail_error:
                    # Если не удалось отправить email, логируем ошибку но продолжаем
                    print(f"Email error: {str(mail_error)}")
                    import logging
                    logging.error(f"Failed to send password reset email to {email}: {str(mail_error)}")
                    email_sent = False
                    email_error = str(mail_error)
                
                # Возвращаем ответ
                response_data = {
                    'success': True,
                    'message': 'Токен для сброса пароля отправлен на ваш email. Проверьте почту.' if email_sent else 'Токен создан, но email не отправлен',
                    'email_sent': email_sent
                }
                
                # В режиме разработки (DEBUG=True) показываем токен
                if settings.DEBUG:
                    response_data['reset_token'] = token
                    response_data['debug_message'] = 'В режиме разработки токен показывается здесь'
                
                if not email_sent:
                    response_data['email_error'] = email_error
                
                return Response(response_data, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': get_error_message('validation_error'),
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResetPasswordAPIView(APIView):
    """
    Сброс пароля с использованием токена
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Сброс пароля с использованием токена, полученного по email",
        tags=['Accounts'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'token': openapi.Schema(type=openapi.TYPE_STRING, description='Токен для сброса пароля'),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description='Новый пароль'),
                'new_password_confirm': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description='Подтверждение нового пароля'),
            },
            required=['token', 'new_password', 'new_password_confirm']
        ),
        responses={
            200: openapi.Response('Пароль успешно изменен'),
            400: openapi.Response('Ошибка валидации данных'),
            401: openapi.Response('Токен неверный или истек')
        }
    )
    def post(self, request):
        try:
            serializer = ResetPasswordSerializer(data=request.data)
            
            if serializer.is_valid():
                user = serializer.validated_data['user']
                new_password = serializer.validated_data['new_password']
                
                # Меняем пароль
                user.set_password(new_password)
                
                # Очищаем токен
                user.reset_token = None
                user.reset_token_expires = None
                user.save()
                
                # Отправляем уведомление на email
                subject = 'Пароль изменен - SafeCode CRM'
                message = f"""
Здравствуйте, {user.get_full_name()}!

Ваш пароль для аккаунта в SafeCode CRM был успешно изменен.

Если вы не меняли пароль, немедленно свяжитесь с нами.

С уважением,
Команда SafeCode CRM
                """
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                
                return Response({
                    'success': True,
                    'message': 'Пароль успешно изменен'
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': get_error_message('validation_error'),
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SimpleChangePasswordAPIView(APIView):
    """
    Простая смена пароля (без старого пароля)
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Простая смена пароля для авторизованного пользователя (без подтверждения старого пароля)",
        tags=['Profile'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'new_password': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description='Новый пароль'),
                'new_password_confirm': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description='Подтверждение нового пароля'),
            },
            required=['new_password', 'new_password_confirm']
        ),
        responses={
            200: openapi.Response('Пароль успешно изменен'),
            400: openapi.Response('Ошибка валидации данных'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            serializer = SimpleChangePasswordSerializer(data=request.data)
            
            if serializer.is_valid():
                user = request.user
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                
                # Отправляем уведомление на email
                subject = 'Пароль изменен - SafeCode CRM'
                message = f"""
Здравствуйте, {user.get_full_name()}!

Ваш пароль для аккаунта в SafeCode CRM был успешно изменен.

Если вы не меняли пароль, немедленно свяжитесь с нами.

С уважением,
Команда SafeCode CRM
                """
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                
                return Response({
                    'success': True,
                    'message': 'Пароль успешно изменен'
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': get_error_message('validation_error'),
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """
    Тестовый endpoint для отправки email
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Тестовая отправка email",
        tags=['Test'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description='Email адрес'),
            },
            required=['email']
        ),
        responses={
            200: openapi.Response('Email отправлен'),
        }
    )
    def post(self, request):
        try:
            email = request.data.get('email')
            
            # Отправляем тестовый email
            subject = 'Test Email - SafeCode CRM'
            message = 'This is a test email from SafeCode CRM'
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            return Response({
                'success': True,
                'message': f'Test email sent to {email}'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Email error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetRolesAPIView(APIView):
    """
    Получение списка всех ролей (групп)
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Получение списка всех доступных ролей (групп) в системе",
        tags=['Accounts'],
        responses={
            200: openapi.Response(
                'Успешное получение списка ролей',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                }
                            )
                        ),
                    }
                )
            )
        }
    )
    def get(self, request):
        try:
            # Получаем все группы кроме "Администратор"
            groups = Group.objects.exclude(name='Администратор').order_by('name')
            
            roles_data = [{'id': group.id, 'name': group.name} for group in groups]
            
            return Response({
                'success': True,
                'message': 'Список ролей получен успешно',
                'data': roles_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)