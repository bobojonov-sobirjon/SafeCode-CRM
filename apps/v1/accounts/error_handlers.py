from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.core.exceptions import ValidationError as DjangoValidationError


def custom_exception_handler(exc, context):
    """
    Кастомный обработчик исключений с русскими сообщениями
    """
    # Получаем стандартный ответ от DRF
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response_data = {
            'success': False,
            'message': 'Произошла ошибка',
            'errors': {}
        }
        
        # Обработка различных типов ошибок
        if isinstance(exc, Http404):
            custom_response_data['message'] = 'Запрашиваемый ресурс не найден'
            custom_response_data['errors'] = {'detail': 'Страница не найдена'}
            
        elif isinstance(exc, PermissionDenied):
            custom_response_data['message'] = 'У вас нет прав для выполнения этого действия'
            custom_response_data['errors'] = {'detail': 'Доступ запрещен'}
            
        elif isinstance(exc, IntegrityError):
            custom_response_data['message'] = 'Ошибка целостности данных'
            custom_response_data['errors'] = {'detail': 'Нарушение целостности данных'}
            
        elif isinstance(exc, DjangoValidationError):
            custom_response_data['message'] = 'Ошибка валидации данных'
            custom_response_data['errors'] = {'detail': str(exc)}
            
        else:
            # Для остальных ошибок используем стандартные сообщения
            if hasattr(response, 'data'):
                custom_response_data['errors'] = response.data
                
                # Специальная обработка для ошибок валидации
                if isinstance(response.data, dict):
                    if 'non_field_errors' in response.data:
                        custom_response_data['message'] = 'Ошибка валидации данных'
                    elif 'detail' in response.data:
                        custom_response_data['message'] = response.data['detail']
                    else:
                        custom_response_data['message'] = 'Ошибка валидации полей'
        
        response.data = custom_response_data
    
    return response


def get_error_message(error_code):
    """
    Получение русских сообщений об ошибках по коду
    """
    error_messages = {
        'invalid_credentials': 'Неверные учетные данные',
        'user_not_found': 'Пользователь не найден',
        'email_exists': 'Пользователь с таким email уже существует',
        'phone_exists': 'Пользователь с таким номером телефона уже существует',
        'password_mismatch': 'Пароли не совпадают',
        'weak_password': 'Пароль слишком слабый',
        'account_disabled': 'Аккаунт деактивирован',
        'token_expired': 'Токен истек',
        'token_invalid': 'Недействительный токен',
        'permission_denied': 'Доступ запрещен',
        'validation_error': 'Ошибка валидации данных',
        'server_error': 'Внутренняя ошибка сервера',
    }
    
    return error_messages.get(error_code, 'Неизвестная ошибка')
