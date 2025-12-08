from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
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
from .models import CustomUser, PurchasedService, Storage, StorageFile
from .serializers import (
    PurchasedServiceReadSerializer,
    RegisterSerializer, LoginSerializer, ProfileSerializer, 
    ChangePasswordSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
    SimpleChangePasswordSerializer, PurchasedServiceSerializer,
    UserCreateSerializer, UserListSerializer, GroupSerializer, LogoutSerializer,
    StorageSerializer, StorageCreateSerializer, StorageUpdateSerializer,
    StorageFileSerializer, StorageFileCreateSerializer,
    AdminPasswordRequestSerializer, AdminPasswordVerifySerializer,
    UserDetailSerializer, UserDetailWithPasswordSerializer,
    UserUpdateSerializer, UserPasswordUpdateSerializer
)
from apps.v1.documents.mixins import PaginationMixin
from .error_handlers import get_error_message
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from apps.v1.notification.models import Notification


class RegisterAPIView(APIView):
    """
    Регистрация нового пользователя
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Регистрация нового пользователя в системе",
        tags=['Accounts'],
        request_body=RegisterSerializer,
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
                
                # Создаем пользователя как неактивного до подтверждения email
                user.is_active = False
                user.is_email_verified = False
                
                # Генерируем токен для подтверждения email
                token = secrets.token_urlsafe(32)
                user.email_verification_token = token
                user.email_verification_token_expires = timezone.now() + timedelta(hours=24)  # 24 часа
                user.save()
                
                # Отправляем email с ссылкой для подтверждения
                url = "https://safecode-phi.vercel.app/"
                verification_url = f"{url}/accounts/verify-email/?token={token}"
                
                subject = 'Подтверждение регистрации - SafeCode CRM'
                message = f"""
Здравствуйте, {user.get_full_name()}!

Спасибо за регистрацию в SafeCode CRM.

Для завершения регистрации и активации вашего аккаунта, пожалуйста, подтвердите ваш email адрес, перейдя по следующей ссылке:

{verification_url}

Эта ссылка действительна в течение 24 часов.

Если вы не регистрировались в SafeCode CRM, просто проигнорируйте это сообщение.

С уважением,
Команда SafeCode CRM
                """
                
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                    email_sent = True
                except Exception as mail_error:
                    print(f"Email error: {str(mail_error)}")
                    import logging
                    logging.error(f"Failed to send verification email to {user.email}: {str(mail_error)}")
                    email_sent = False
                
                return Response({
                    'success': True,
                    'message': 'Регистрация прошла успешно! На ваш email отправлено письмо с подтверждением. Пожалуйста, проверьте почту и подтвердите регистрацию.' if email_sent else 'Регистрация прошла успешно! Однако не удалось отправить email. Обратитесь к администратору.',
                    'data': {
                        'user': {
                            'id': user.id,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'email': user.email,
                            'phone_number': user.phone_number,
                            'id_organization': user.id_organization,
                            'is_email_verified': user.is_email_verified,
                            'groups': [{'id': g.id, 'name': g.name} for g in user.groups.all()],
                        },
                        'email_sent': email_sent,
                        'verification_token': token if settings.DEBUG and not email_sent else None,
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


class VerifyEmailAPIView(APIView):
    """
    Подтверждение email адреса пользователя
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Подтверждение email адреса пользователя по токену",
        tags=['Accounts'],
        manual_parameters=[
            openapi.Parameter(
                'token',
                openapi.IN_QUERY,
                description="Токен подтверждения email",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                'Email успешно подтвержден',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: openapi.Response('Неверный или истекший токен')
        }
    )
    def get(self, request):
        try:
            token = request.query_params.get('token')
            
            if not token:
                return Response({
                    'success': False,
                    'message': 'Токен не предоставлен'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                user = CustomUser.objects.get(email_verification_token=token)
            except CustomUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Неверный токен подтверждения'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Проверка истечения токена
            if user.email_verification_token_expires and user.email_verification_token_expires < timezone.now():
                return Response({
                    'success': False,
                    'message': 'Токен истек. Запросите новый токен подтверждения.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Активируем пользователя и подтверждаем email
            user.is_email_verified = True
            user.is_active = True
            user.email_verification_token = None
            user.email_verification_token_expires = None
            user.save()
            
            return Response({
                'success': True,
                'message': 'Email успешно подтвержден! Ваш аккаунт активирован. Теперь вы можете войти в систему.'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResendVerificationEmailAPIView(APIView):
    """
    Повторная отправка email для подтверждения
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Повторная отправка email для подтверждения регистрации",
        tags=['Accounts'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email адрес пользователя')
            }
        ),
        responses={
            200: openapi.Response('Email отправлен'),
            400: openapi.Response('Ошибка валидации'),
            404: openapi.Response('Пользователь не найден')
        }
    )
    def post(self, request):
        try:
            email = request.data.get('email')
            
            if not email:
                return Response({
                    'success': False,
                    'message': 'Email обязателен для заполнения'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                user = CustomUser.objects.get(email__iexact=email)
            except CustomUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Пользователь с таким email не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Если email уже подтвержден
            if user.is_email_verified:
                return Response({
                    'success': False,
                    'message': 'Email уже подтвержден'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Генерируем новый токен
            token = secrets.token_urlsafe(32)
            user.email_verification_token = token
            user.email_verification_token_expires = timezone.now() + timedelta(hours=24)
            user.save()
            
            # Отправляем email
            verification_url = f"{settings.BASE_URL}/api/v1/accounts/verify-email/?token={token}"
            
            subject = 'Подтверждение регистрации - SafeCode CRM'
            message = f"""
Здравствуйте, {user.get_full_name()}!

Вы запросили повторную отправку письма для подтверждения регистрации в SafeCode CRM.

Для завершения регистрации и активации вашего аккаунта, пожалуйста, подтвердите ваш email адрес, перейдя по следующей ссылке:

{verification_url}

Эта ссылка действительна в течение 24 часов.

Если вы не запрашивали это письмо, просто проигнорируйте это сообщение.

С уважением,
Команда SafeCode CRM
            """
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                email_sent = True
            except Exception as mail_error:
                print(f"Email error: {str(mail_error)}")
                import logging
                logging.error(f"Failed to send verification email to {user.email}: {str(mail_error)}")
                email_sent = False
            
            return Response({
                'success': True,
                'message': 'Письмо с подтверждением отправлено на ваш email' if email_sent else 'Не удалось отправить email. Обратитесь к администратору.',
                'email_sent': email_sent,
                'verification_token': token if settings.DEBUG and not email_sent else None,
            }, status=status.HTTP_200_OK)
            
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
        request_body=LoginSerializer,
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
            # Swagger UI dan kelgan data ni to'g'ri formatga o'tkazish
            data = request.data
            # Agar data dict ichida bo'lsa, uni to'g'ridan-to'g'ri olamiz
            if isinstance(data, dict) and 'data' in data:
                data = data['data']
            
            serializer = LoginSerializer(data=data)
            
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
        request_body=ChangePasswordSerializer,
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
        request_body=LogoutSerializer,
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
        request_body=ForgotPasswordSerializer,
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
        request_body=ResetPasswordSerializer,
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


class PurchasedServiceListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Список покупок услуг текущего пользователя (админ видит все)",
        tags=['Purchased Services'],
        responses={200: 'OK'},
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            user = request.user
            if user.groups.filter(name='Администратор').exists():
                qs = PurchasedService.objects.select_related('service', 'user').all()
            else:
                qs = PurchasedService.objects.select_related('service', 'user').filter(user=user)
            serializer = PurchasedServiceReadSerializer(qs, many=True, context={'request': request})
            return Response({'success': True, 'data': serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'success': False, 'message': get_error_message('server_error'), 'errors': {'detail': str(e)}}, status=500)

    @swagger_auto_schema(
        operation_description="Покупка услуги (только роль Заказчик)",
        tags=['Purchased Services'],
        request_body=PurchasedServiceSerializer,
        responses={201: 'Created', 400: 'Bad Request'},
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            user = request.user
            if not user.groups.filter(name='Заказчик').exists():
                return Response({'success': False, 'message': 'Только роль Заказчик может покупать услуги.'}, status=403)

            serializer = PurchasedServiceSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                purchase = serializer.save()

                # Notify admins about the purchase
                admin_group = Group.objects.filter(name='Администратор').first()
                if admin_group:
                    admin_users = CustomUser.objects.filter(groups=admin_group)
                    for admin in admin_users:
                        Notification.objects.create(
                            recipient=admin,
                            actor=user,
                            verb='service_purchased',
                            message=f"Пользователь {user.get_full_name()} приобрел услугу '{purchase.service.title}'.",
                            target=purchase,
                            category='service'
                        )
                        try:
                            send_mail(
                                'Новая покупка услуги',
                                f"Пользователь {user.get_full_name()} ({user.email}) приобрел услугу '{purchase.service.title}'.",
                                settings.DEFAULT_FROM_EMAIL,
                                [admin.email],
                                fail_silently=True,
                            )
                        except Exception:
                            pass

                return Response({'success': True, 'data': PurchasedServiceSerializer(purchase).data}, status=201)
            return Response({'success': False, 'message': get_error_message('validation_error'), 'errors': serializer.errors}, status=400)
        except Exception as e:
            return Response({'success': False, 'message': get_error_message('server_error'), 'errors': {'detail': str(e)}}, status=500)


class PurchasedServiceDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, user, pk):
        obj = PurchasedService.objects.select_related('service', 'user').filter(pk=pk).first()
        if not obj:
            return None, Response({'success': False, 'message': 'Объект не найден'}, status=404)
        if user.groups.filter(name='Администратор').exists() or obj.user_id == user.id:
            return obj, None
        return None, Response({'success': False, 'message': 'Доступ запрещен'}, status=403)

    @swagger_auto_schema(operation_description="Детали покупки услуги", tags=['Purchased Services'], security=[{'Bearer': []}])
    def get(self, request, pk):
        obj, err = self.get_object(request.user, pk)
        if err:
            return err
        serializer = PurchasedServiceReadSerializer(obj, context={'request': request})
        return Response({'success': True, 'data': serializer.data}, status=200)

    @swagger_auto_schema(operation_description="Обновить покупку (только владелец или админ)", tags=['Purchased Services'], request_body=PurchasedServiceSerializer, security=[{'Bearer': []}])
    def put(self, request, pk):
        obj, err = self.get_object(request.user, pk)
        if err:
            return err
        serializer = PurchasedServiceSerializer(obj, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True, 'data': serializer.data}, status=200)
        return Response({'success': False, 'message': get_error_message('validation_error'), 'errors': serializer.errors}, status=400)

    @swagger_auto_schema(operation_description="Удалить покупку (только владелец или админ)", tags=['Purchased Services'], security=[{'Bearer': []}])
    def delete(self, request, pk):
        obj, err = self.get_object(request.user, pk)
        if err:
            return err
        obj.delete()
        return Response({'success': True, 'message': 'Удалено'}, status=204)


class CreateUserAPIView(APIView):
    """
    Создание нового пользователя (POST)
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Создание нового пользователя в системе",
        tags=['Admin'],
        request_body=UserCreateSerializer,
        responses={
            201: openapi.Response(
                'Успешное создание пользователя',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            400: openapi.Response('Ошибка валидации данных'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            serializer = UserCreateSerializer(data=request.data)
            
            if serializer.is_valid():
                user = serializer.save()
                
                # Создаем пользователя как неактивного до подтверждения email
                user.is_active = False
                user.is_email_verified = False
                
                # Генерируем 6-значный код для подтверждения email
                import random
                verification_code = str(random.randint(100000, 999999))
                
                # Сохраняем код в email_verification_token (6 raqamli kod)
                user.email_verification_token = verification_code
                user.email_verification_token_expires = timezone.now() + timedelta(hours=24)  # 24 часа
                user.save()
                
                # Отправляем email с кодом
                subject = 'Код подтверждения регистрации - SafeCode CRM'
                message = f"""
Здравствуйте, {user.get_full_name()}!

Ваш код подтверждения регистрации: {verification_code}

Используйте этот код для подтверждения регистрации в SafeCode CRM. Код действителен в течение 24 часов.

Если вы не регистрировались в SafeCode CRM, просто проигнорируйте это сообщение.

С уважением,
Команда SafeCode CRM
                """
                
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                    email_sent = True
                except Exception as mail_error:
                    print(f"Email error: {str(mail_error)}")
                    import logging
                    logging.error(f"Failed to send verification email to {user.email}: {str(mail_error)}")
                    email_sent = False
                
                return Response({
                    'success': True,
                    'message': 'Пользователь создан успешно! На email отправлен код подтверждения. Пожалуйста, проверьте почту и подтвердите регистрацию.' if email_sent else 'Пользователь создан успешно! Однако не удалось отправить email. Обратитесь к администратору.',
                    'data': {
                        'id': user.id,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'email': user.email,
                        'phone_number': user.phone_number,
                        'created_at': user.created_at,
                        'last_login': user.last_login,
                        'is_email_verified': user.is_email_verified,
                        'is_active': user.is_active,
                        'groups': [{'id': g.id, 'name': g.name} for g in user.groups.all()],
                    },
                    'email_sent': email_sent,
                    'verification_code': verification_code if settings.DEBUG and not email_sent else None,
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


class ListUsersAPIView(PaginationMixin, APIView):
    """
    Получение списка всех пользователей (исключая суперпользователей) с пагинацией
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение списка всех пользователей (исключая суперпользователей) с пагинацией",
        tags=['Admin'],
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="Номер страницы", type=openapi.TYPE_INTEGER),
            openapi.Parameter('limit', openapi.IN_QUERY, description="Количество элементов на странице", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: openapi.Response(
                'Успешное получение списка пользователей',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        ),
                        'pagination': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            # Получаем всех пользователей, исключая суперпользователей
            users = CustomUser.objects.filter(is_superuser=False).exclude(groups__name__in=['Администратор']).order_by('-created_at')
            
            # Применяем пагинацию
            page_obj, paginator = self.paginate_queryset(users, request)
            serializer = UserListSerializer(page_obj.object_list, many=True)
            
            return self.get_paginated_response(page_obj, paginator, serializer.data, 'Список пользователей получен успешно')
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            

class GroupListAPIView(APIView):
    """
    Получение списка всех групп (ролей)
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение списка всех групп (ролей)",
        tags=['Admin'],
        responses={200: 'OK'},
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            groups = Group.objects.all()
            serializer = GroupSerializer(groups, many=True)
            return Response({'success': True, 'data': serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'success': False, 'message': get_error_message('server_error'), 'errors': {'detail': str(e)}}, status=500)


class UserDetailAPIView(APIView):
    """
    Получение детальной информации о пользователе по ID (без пароля)
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение детальной информации о пользователе по ID (без пароля)",
        tags=['Admin'],
        responses={
            200: openapi.Response(
                'Успешное получение информации о пользователе',
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            404: openapi.Response('Пользователь не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request, pk):
        try:
            user = CustomUser.objects.get(id=pk)
            serializer = UserDetailSerializer(user, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Информация о пользователе получена успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Пользователь не найден',
                'errors': {'detail': 'Пользователь с таким ID не существует.'}
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateUserAPIView(APIView):
    """
    Обновление информации о пользователе по ID
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @swagger_auto_schema(
        operation_description="Обновление информации о пользователе по ID",
        tags=['Admin'],
        request_body=UserUpdateSerializer,
        responses={
            200: openapi.Response(
                'Успешное обновление информации о пользователе',
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            400: openapi.Response('Ошибка валидации данных'),
            404: openapi.Response('Пользователь не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def put(self, request, pk):
        """
        Полное обновление пользователя (PUT)
        """
        return self._update(request, pk, partial=False)
    
    def patch(self, request, pk):
        """
        Частичное обновление пользователя (PATCH)
        """
        return self._update(request, pk, partial=True)
    
    def _update(self, request, pk, partial=False):
        try:
            user = CustomUser.objects.get(id=pk)
            serializer = UserUpdateSerializer(user, data=request.data, partial=partial, context={'request': request})
            
            if serializer.is_valid():
                serializer.save()
                updated_user = CustomUser.objects.get(id=pk)
                response_serializer = UserDetailSerializer(updated_user, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': 'Информация о пользователе обновлена успешно',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': get_error_message('validation_error'),
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Пользователь не найден',
                'errors': {'detail': 'Пользователь с таким ID не существует.'}
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteUserAPIView(APIView):
    """
    Удаление пользователя по ID
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Удаление пользователя по ID",
        tags=['Admin'],
        responses={
            200: openapi.Response(
                'Успешное удаление пользователя',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            404: openapi.Response('Пользователь не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def delete(self, request, pk):
        try:
            user = CustomUser.objects.get(id=pk)
            user_email = user.email
            user.delete()
            
            return Response({
                'success': True,
                'message': f'Пользователь {user_email} успешно удален'
            }, status=status.HTTP_200_OK)
            
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Пользователь не найден',
                'errors': {'detail': 'Пользователь с таким ID не существует.'}
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateUserPasswordAPIView(APIView):
    """
    Обновление пароля пользователя по ID
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Обновление пароля пользователя по ID",
        tags=['Admin'],
        request_body=UserPasswordUpdateSerializer,
        responses={
            200: openapi.Response(
                'Пароль пользователя успешно обновлен',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: openapi.Response('Ошибка валидации данных'),
            404: openapi.Response('Пользователь не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def put(self, request, pk):
        try:
            user = CustomUser.objects.get(id=pk)
            serializer = UserPasswordUpdateSerializer(data=request.data)
            
            if serializer.is_valid():
                new_password = serializer.validated_data['password']
                user.set_password(new_password)
                user.save()
                
                return Response({
                    'success': True,
                    'message': 'Пароль пользователя успешно обновлен'
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': get_error_message('validation_error'),
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Пользователь не найден',
                'errors': {'detail': 'Пользователь с таким ID не существует.'}
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminPasswordRequestAPIView(APIView):
    """
    Запрос SMS кода для администратора (для доступа к паролю пользователя)
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Запрос SMS кода для администратора. SMS код будет отправлен на email администратора.",
        tags=['Admin'],
        request_body=AdminPasswordRequestSerializer,
        responses={
            200: openapi.Response(
                'SMS код отправлен на email администратора',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'email_sent': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'sms_code': openapi.Schema(type=openapi.TYPE_STRING, description='SMS код (возвращается только если email не отправлен)'),
                        'email_error': openapi.Schema(type=openapi.TYPE_STRING, description='Ошибка отправки email (только если email не отправлен)'),
                    }
                )
            ),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            # Проверяем, что пользователь является администратором
            admin_user = request.user
            if not admin_user.groups.filter(name='Администратор').exists() and not admin_user.is_superuser:
                return Response({
                    'success': False,
                    'message': 'Доступ запрещен',
                    'errors': {'detail': 'Только администраторы могут запрашивать SMS код.'}
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Генерируем 6-значный SMS код
            import random
            sms_code = str(random.randint(100000, 999999))
            
            # Сохраняем SMS код в профиле администратора
            admin_user.admin_sms_code = sms_code
            admin_user.admin_sms_code_expires = timezone.now() + timedelta(minutes=10)  # 10 минут
            admin_user.save()
            
            # Отправляем SMS код на email администратора
            subject = 'SMS код для доступа к паролю пользователя - SafeCode CRM'
            message = f"""
Здравствуйте, {admin_user.get_full_name()}!

Ваш SMS код для доступа к паролю пользователя: {sms_code}

Используйте этот код для получения пароля пользователя. Код действителен в течение 10 минут.

Если вы не запрашивали этот код, проигнорируйте это сообщение.

С уважением,
Команда SafeCode CRM
            """
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [admin_user.email],
                    fail_silently=False,
                )
                email_sent = True
                email_error = None
            except Exception as mail_error:
                print(f"Email error: {str(mail_error)}")
                import logging
                logging.error(f"Failed to send SMS code email to {admin_user.email}: {str(mail_error)}")
                email_sent = False
                email_error = str(mail_error)
            
            response_data = {
                'success': True,
                'message': 'SMS код отправлен на ваш email. Проверьте почту.' if email_sent else 'SMS код создан, но email не отправлен',
                'email_sent': email_sent
            }
            
            # SMS код qaytariladi faqat email yuborish ishlamaganda
            if not email_sent:
                response_data['sms_code'] = sms_code
                response_data['email_error'] = email_error
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminPasswordVerifyAPIView(APIView):
    """
    Верификация SMS кода и получение пароля пользователя (hash)
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Верификация SMS кода и получение информации о пользователе (first_name, last_name, email, phone, password hash)",
        tags=['Admin'],
        request_body=AdminPasswordVerifySerializer,
        responses={
            200: openapi.Response(
                'Успешная верификация и получение данных пользователя',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            400: openapi.Response('Ошибка валидации данных'),
            401: openapi.Response('Требуется авторизация'),
            403: openapi.Response('Доступ запрещен')
        },
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            # Проверяем, что пользователь является администратором
            admin_user = request.user
            if not admin_user.groups.filter(name='Администратор').exists() and not admin_user.is_superuser:
                return Response({
                    'success': False,
                    'message': 'Доступ запрещен',
                    'errors': {'detail': 'Только администраторы могут получать пароли пользователей.'}
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = AdminPasswordVerifySerializer(data=request.data)
            
            if serializer.is_valid():
                user = serializer.validated_data['user']
                sms_code = serializer.validated_data['sms_code']
                
                # Проверяем, что SMS код принадлежит текущему администратору
                if not admin_user.admin_sms_code or admin_user.admin_sms_code != sms_code:
                    return Response({
                        'success': False,
                        'message': 'Неверный SMS код',
                        'errors': {'sms_code': 'SMS код не соответствует вашему запросу.'}
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Проверка истечения SMS кода
                if admin_user.admin_sms_code_expires and admin_user.admin_sms_code_expires < timezone.now():
                    return Response({
                        'success': False,
                        'message': 'SMS код истек',
                        'errors': {'sms_code': 'SMS код истек. Запросите новый.'}
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Очищаем SMS код после использования
                admin_user.admin_sms_code = None
                admin_user.admin_sms_code_expires = None
                admin_user.save()
                
                # Возвращаем полную информацию о пользователе с паролем (hash)
                serializer = UserDetailWithPasswordSerializer(user, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': 'Информация о пользователе получена успешно',
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


class VerifyUserEmailCodeAPIView(APIView):
    """
    Подтверждение email адреса пользователя по коду (для CreateUserAPIView)
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Подтверждение email адреса пользователя по коду. Код отправляется на email при создании пользователя администратором.",
        tags=['Admin'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'code'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email адрес пользователя'),
                'code': openapi.Schema(type=openapi.TYPE_STRING, description='6-значный код подтверждения'),
            }
        ),
        responses={
            200: openapi.Response(
                'Email успешно подтвержден',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'first_name': openapi.Schema(type=openapi.TYPE_STRING),
                                'last_name': openapi.Schema(type=openapi.TYPE_STRING),
                                'email': openapi.Schema(type=openapi.TYPE_STRING),
                                'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                                'groups': openapi.Schema(type=openapi.TYPE_ARRAY),
                            }
                        ),
                    }
                )
            ),
            400: openapi.Response('Неверный или истекший код')
        }
    )
    def post(self, request):
        try:
            email = request.data.get('email')
            code = request.data.get('code')
            
            if not email:
                return Response({
                    'success': False,
                    'message': 'Email обязателен для заполнения'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not code:
                return Response({
                    'success': False,
                    'message': 'Код обязателен для заполнения'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                user = CustomUser.objects.get(email__iexact=email)
            except CustomUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Пользователь с таким email не найден'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Проверка кода
            if not user.email_verification_token or user.email_verification_token != code:
                return Response({
                    'success': False,
                    'message': 'Неверный код подтверждения'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Проверка истечения кода
            if user.email_verification_token_expires and user.email_verification_token_expires < timezone.now():
                return Response({
                    'success': False,
                    'message': 'Код истек. Обратитесь к администратору для получения нового кода.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Активируем пользователя и подтверждаем email
            user.is_email_verified = True
            user.is_active = True
            user.email_verification_token = None
            user.email_verification_token_expires = None
            user.save()
            
            # Возвращаем полную информацию о пользователе
            return Response({
                'success': True,
                'message': 'Email успешно подтвержден! Ваш аккаунт активирован. Теперь вы можете войти в систему.',
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
                    'is_email_verified': user.is_email_verified,
                    'is_active': user.is_active,
                    'groups': [{'id': g.id, 'name': g.name} for g in user.groups.all()],
                    'created_at': user.created_at,
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)